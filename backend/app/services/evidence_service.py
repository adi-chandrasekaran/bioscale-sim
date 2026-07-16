from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.adapters.clinvar import safe_fetch_variant_evidence
from app.adapters.cancer_variants import safe_fetch_cancer_variant_context
from app.adapters.alphafold import safe_get_structure_status
from app.adapters.hgnc import safe_fetch_gene_identity
from app.adapters.open_targets import safe_fetch_disease_targets_by_id, safe_search_genes
from app.adapters.reactome import safe_fetch_pathway_evidence
from app.adapters.uniprot import safe_fetch_protein_evidence
from app.adapters.normalizer import (
    amino_acid_change_text,
    embedded_gene_symbol_from_variant_query,
    infer_disease_context_from_name,
    infer_variant_type_from_notation,
    normalize_gene_symbol,
    parse_hgvs_protein,
)
from app.adapters.summarizer import (
    build_card_summaries,
    is_placeholder_definition,
    known_gene_function,
    limit_sentences,
    summarize_gene_association,
    summarize_mutation,
    summarize_pathway,
    summarize_protein_function,
    summarize_functional_impact,
    summarize_disease_fallback,
    summarize_gene_fallback,
    summarize_pathway_fallback,
    summarize_protein_fallback,
    summarize_variant_fallback,
    strip_citations,
)
from app.models import (
    CandidateGene,
    DiseaseDiscoveryResult,
    MutationResult,
    NormalizedEvidence,
    PathwayResult,
    ProteinEffectResult,
    ProvenanceEntry,
)
from app.services.disease_discovery import discover_candidate_genes
from app.services.kb_builder import LOCAL_DISEASE_KEY, build_simulation_kb
from app.services.mutation_engine import interpret_mutation
from app.services.pathway_simulator import simulate_pathway
from app.services.protein_effect import predict_protein_effect

EVIDENCE_UNAVAILABLE_MSG = (
    "External evidence unavailable for this field; using fallback or simulator assumption."
)
INVALID_COMBINATION_MSG = "invalid combination"


def _prov(category: str, source: str, detail: Optional[str] = None) -> ProvenanceEntry:
    return ProvenanceEntry(category=category, source=source, detail=detail)


def _source_status(payload: Dict[str, Any], available_key: str = "available") -> str:
    if payload.get(available_key):
        return "available"
    error = str(payload.get("error") or payload.get("error_message") or "")
    if "No UniProt accession" in error or "could be resolved" in error or payload.get("resolution_source") == "input_unresolved":
        return "input_unresolved"
    if "404" in error or "not found" in error.lower() or "No AlphaFold prediction" in error:
        return "checked_not_found"
    if error:
        return "api_unreachable"
    return "checked_not_found"


def _audit(source_name: str, payload: Dict[str, Any], evidence_type: str, queried: Any = None, resolved: Any = None, available_key: str = "available") -> Dict[str, Any]:
    status = _source_status(payload, available_key)
    return {
        "source_name": source_name,
        "status": status,
        "reason": payload.get("error") or payload.get("error_message") or payload.get("notes") or ("record found" if status == "available" else "checked source and no matching public record was found"),
        "queried_identifier": queried,
        "resolved_identifier": resolved,
        "evidence_type": evidence_type,
    }


def _build_local_fallback_pipeline(
    local_kb: Dict[str, Any],
    disease_id: str,
    disease_name: str,
    gene_symbol: str,
    mutation_notation: str,
    pathway_id: Optional[str],
    pathway_name: Optional[str],
) -> Tuple[DiseaseDiscoveryResult, MutationResult, ProteinEffectResult, PathwayResult, NormalizedEvidence, bool, Optional[str]]:
    disease_key = "cancer" if "cancer" in local_kb.get("diseases", {}) else LOCAL_DISEASE_KEY
    local_disease = local_kb.get("diseases", {}).get(disease_key, {})
    kb = build_simulation_kb(
        local_kb,
        disease_id,
        disease_name,
        local_disease.get("description"),
        gene_symbol,
        mutation_notation,
        {},
        {},
        {},
        {},
        pathway_id,
        pathway_name,
    )

    evidence = NormalizedEvidence(
        disease={"id": disease_id, "name": local_disease.get("label", disease_name)},
        gene={"symbol": gene_symbol},
        variant={"notation": mutation_notation},
        protein={"accession": kb.get("genes", {}).get(gene_symbol, {}).get("protein_id")},
        pathways=[],
        sources=["Local fallback"],
        summaries={},
        external_evidence_available=False,
        evidence_notice=EVIDENCE_UNAVAILABLE_MSG,
        source_status={
            "Open Targets": "model_inferred_from_source",
            "ClinVar": "model_inferred_from_source",
            "UniProt": "model_inferred_from_source",
            "Reactome": "model_inferred_from_source",
            "AlphaFold DB": "input_unresolved",
        },
        source_audit=[],
    )

    discovery = discover_candidate_genes(kb, disease_key)
    mutation = interpret_mutation(kb, gene_symbol, mutation_notation)
    protein = predict_protein_effect(kb, mutation)
    pathway = simulate_pathway(kb, protein)

    discovery = _build_discovery(discovery, evidence, gene_symbol)
    mutation = _build_mutation(mutation, evidence)
    protein = _build_protein(protein, evidence, mutation)
    pathway = _build_pathway(pathway, evidence, pathway_id, pathway_name)
    return discovery, mutation, protein, pathway, evidence, False, evidence.evidence_notice


def fetch_normalized_evidence(
    disease_id: str,
    disease_name: str,
    gene_symbol: str,
    mutation_notation: str,
    local_kb: Dict[str, Any],
    pathway_id: Optional[str] = None,
    pathway_name: Optional[str] = None,
    protein_accession: Optional[str] = None,
) -> NormalizedEvidence:
    symbol = normalize_gene_symbol(gene_symbol)
    parsed = parse_hgvs_protein(mutation_notation)
    position = parsed["position"] if parsed else None

    open_targets = safe_fetch_disease_targets_by_id(disease_id, limit=10)
    clinvar = safe_fetch_variant_evidence(symbol, mutation_notation)
    cancer_variant = safe_fetch_cancer_variant_context(symbol, mutation_notation)
    hgnc = safe_fetch_gene_identity(symbol)
    uniprot = safe_fetch_protein_evidence(symbol, local_kb, mutation_position=position, requested_accession=protein_accession)
    alphafold = safe_get_structure_status(uniprot.get("accession") or "", position=position)
    reactome = safe_fetch_pathway_evidence(symbol, local_kb)
    source_status = {
        "Open Targets": _source_status(open_targets),
        "ClinVar": _source_status(clinvar),
        "UniProt": _source_status(uniprot),
        "Reactome": _source_status(reactome),
        "AlphaFold DB": "available" if alphafold.get("alphafold_available") else _source_status(alphafold, "alphafold_available"),
    }
    if not alphafold.get("alphafold_available") and alphafold.get("structure_source") in {"rcsb_pdb", "uniprot_feature_map"}:
        source_status[alphafold.get("structure_source_label") or "Structure fallback"] = "procured_from_secondary_source"

    source_audit = [
        _audit("Open Targets", open_targets, "disease_gene_ranking", disease_id, open_targets.get("disease_id")),
        _audit("ClinVar", clinvar, "variant_classification", f"{symbol} {mutation_notation}", clinvar.get("clinvar_ids")),
        _audit("CIViC", cancer_variant, "cancer_variant_context", f"{symbol} {mutation_notation}", [r.get("id") for r in cancer_variant.get("records", [])]),
        _audit("HGNC", hgnc, "gene_identity", symbol, hgnc.get("hgnc_id")),
        _audit("UniProt", uniprot, "protein_function", symbol, uniprot.get("accession")),
        _audit("Reactome", reactome, "pathway_context", symbol, [p.get("stId") for p in reactome.get("pathways", [])[:3]]),
        _audit(alphafold.get("structure_source_label") or "AlphaFold DB", alphafold, "structure_context", uniprot.get("accession"), alphafold.get("uniprot_accession"), "alphafold_available"),
    ]

    assoc_score = 0.0
    for row in open_targets.get("candidates", []):
        if row.get("symbol") == symbol:
            assoc_score = float(row.get("score") or 0.0)
            break

    sources: List[str] = []
    if open_targets.get("available"):
        sources.append("Open Targets")
    if clinvar.get("available"):
        sources.append("ClinVar")
    if uniprot.get("available"):
        sources.append("UniProt")
    if alphafold.get("alphafold_available"):
        sources.append("AlphaFold DB")
    if reactome.get("available"):
        sources.append("Reactome")
    if not sources:
        sources.append("Local fallback")

    pathways = reactome.get("pathways", [])
    if pathway_id:
        selected = next((p for p in pathways if p.get("stId") == pathway_id), None)
        if selected:
            pathways = [selected] + [p for p in pathways if p.get("stId") != pathway_id]
        elif pathway_name:
            pathways = [{"stId": pathway_id, "displayName": pathway_name}] + pathways

    protein_summary = summarize_protein_function(uniprot.get("function_raw"), uniprot.get("protein_name"))

    evidence_dict = {
        "disease": {
            "id": disease_id,
            "name": open_targets.get("disease_name") or disease_name,
            "description": strip_citations(open_targets.get("disease_description") or "")[:400]
            or summarize_disease_fallback(disease_name),
            "context": infer_disease_context_from_name(disease_name),
        },
        "gene": {
            "symbol": symbol,
            "resolved_gene_symbol": uniprot.get("gene_name") or symbol,
            "name": next((c.get("name") for c in open_targets.get("candidates", []) if c.get("symbol") == symbol), None) or hgnc.get("name") or symbol,
            "association_score": assoc_score,
            "ensembl_id": next((c.get("ensembl_id") for c in open_targets.get("candidates", []) if c.get("symbol") == symbol), None) or hgnc.get("ensembl_id") or uniprot.get("ensembl_id"),
            "hgnc_id": hgnc.get("hgnc_id"),
            "summary": summarize_gene_fallback(symbol, disease_name),
        },
        "variant": {
            "notation": mutation_notation,
            "variant_type": clinvar.get("variant_type") or (infer_variant_type_from_notation(mutation_notation) if mutation_notation else ("missense" if parsed else "unknown")),
            "amino_acid_change": clinvar.get("amino_acid_change") or amino_acid_change_text(mutation_notation),
            "clinvar_classification": clinvar.get("clinvar_classification"),
            "clinvar_ids": clinvar.get("clinvar_ids", []),
            "rsid": clinvar.get("rsid"),
            "phenotypes": clinvar.get("phenotypes", []),
            "clinvar_available": clinvar.get("available", False),
            "cancer_variant_context": cancer_variant.get("records", []),
            "cancer_variant_available": cancer_variant.get("available", False),
            "summary": summarize_variant_fallback(symbol, mutation_notation, clinvar.get("variant_type") or infer_variant_type_from_notation(mutation_notation)),
        },
        "protein": {
            "name": uniprot.get("protein_name") or symbol,
            "accession": uniprot.get("accession"),
            "resolution_source": uniprot.get("resolution_source"),
            "function_raw": uniprot.get("function_raw"),
            "function_summary": protein_summary or summarize_protein_fallback(uniprot.get("protein_name") or symbol, symbol),
            "domain_hit": uniprot.get("domain_hit"),
            "alphafold": alphafold,
            "alphafold_available": alphafold.get("alphafold_available", False),
            "structure_source": alphafold.get("structure_source"),
            "structure_source_label": alphafold.get("structure_source_label"),
            "structure_status_reason": alphafold.get("structure_status_reason"),
            "structure_view_model": alphafold.get("structure_view_model"),
            "alphafold_confidence_label": alphafold.get("confidence_label"),
            "sequence_length": uniprot.get("sequence_length"),
            "domains": uniprot.get("domains", []),
            "summary": protein_summary or summarize_protein_fallback(uniprot.get("protein_name") or symbol, symbol),
        },
        "pathways": pathways,
        "sources": sources,
        "summary": summarize_pathway_fallback(symbol) if not pathways else None,
    }

    summaries = build_card_summaries(evidence_dict)
    any_available = any([open_targets.get("available"), clinvar.get("available"), uniprot.get("available"), reactome.get("available")])

    return NormalizedEvidence(
        disease=evidence_dict["disease"],
        gene=evidence_dict["gene"],
        variant=evidence_dict["variant"],
        protein=evidence_dict["protein"],
        pathways=pathways,
        sources=sources,
        summaries=summaries,
        external_evidence_available=any_available,
        evidence_notice=None if any_available else EVIDENCE_UNAVAILABLE_MSG,
        source_status=source_status,
        source_audit=source_audit,
        raw={
            "open_targets": open_targets,
            "clinvar": {k: v for k, v in clinvar.items() if k != "raw"},
            "civic": cancer_variant,
            "hgnc": hgnc,
            "alphafold": alphafold,
            "uniprot": {k: v for k, v in uniprot.items() if k != "raw_entry"},
            "reactome": reactome,
        },
    )


def _build_discovery(
    discovery: DiseaseDiscoveryResult,
    evidence: NormalizedEvidence,
    gene_symbol: str,
) -> DiseaseDiscoveryResult:
    ot = evidence.raw.get("open_targets", {})
    disease_name = evidence.disease.get("name") or discovery.label
    candidates: List[CandidateGene] = []
    local_candidates = {candidate.symbol: candidate for candidate in discovery.candidates}

    def enrich_candidate(symbol: str, name: Optional[str], summary: str, local_candidate: Optional[CandidateGene]) -> Dict[str, Any]:
        uni = safe_fetch_protein_evidence(symbol)
        ot_target = safe_search_genes(symbol, limit=1)
        hgnc_identity = safe_fetch_gene_identity(symbol)
        function_summary = None
        protein_name = None
        function_source = None
        status_reason = None
        if uni.get("available"):
            protein_name = uni.get("protein_name")
            uni_summary = summarize_protein_function(uni.get("function_raw"), protein_name)
            if uni.get("function_raw") and not is_placeholder_definition(uni_summary):
                function_summary = uni_summary
                function_source = "UniProt"
                status_reason = f"Resolved {symbol} to UniProt accession {uni.get('accession')}."
        if not function_summary and ot_target.get("available") and ot_target.get("results"):
            target_description = ot_target["results"][0].get("description")
            if target_description and not is_placeholder_definition(target_description):
                function_summary = limit_sentences(target_description, 2)
                function_source = "Open Targets target description"
                status_reason = "UniProt function text was unavailable, so Open Targets target description was used."
        if not function_summary and hgnc_identity.get("available"):
            hgnc_summary = hgnc_identity.get("summary") or hgnc_identity.get("name")
            if hgnc_summary and not is_placeholder_definition(hgnc_summary):
                function_summary = limit_sentences(f"{symbol} is {hgnc_summary}.", 2)
                function_source = "HGNC"
                status_reason = "UniProt/Open Targets function text was unavailable, so HGNC gene identity was used."
        if not function_summary:
            known_function = known_gene_function(symbol)
            local_text = (
                local_candidate.function_summary
                if local_candidate and local_candidate.function_summary
                else ""
            )
            if is_placeholder_definition(local_text):
                local_text = ""
            if is_placeholder_definition(summary):
                summary = ""
            function_summary = (
                known_function
                if known_function
                else local_text
                if local_text
                else summary
            )
            if not function_summary:
                function_summary = f"{symbol} is included in the disease-gene ranking for {disease_name}, but no concise public gene-function summary was retrieved."
            function_source = "Curated gene function" if known_function else "Open Targets association"
            status_reason = "Used curated gene function text after public function lookups did not return a stronger description."
        if is_placeholder_definition(function_summary):
            known_function = known_gene_function(symbol)
            function_summary = known_function or f"{symbol} is included in the disease-gene ranking for {disease_name}, but no concise public gene-function summary was retrieved."
            function_source = "Curated gene function" if known_function else "Model-inferred gene context"
            status_reason = "Removed placeholder text and used the strongest available gene-function fallback."
        association = summarize_gene_association(symbol, name or symbol, 0.0, disease_name)
        return {
            "gene_name": name or hgnc_identity.get("name") or (local_candidate.gene_name if local_candidate else None) or symbol,
            "protein_name": protein_name or name or hgnc_identity.get("name") or (local_candidate.protein_name if local_candidate else None),
            "summary": limit_sentences(function_summary, 2),
            "function_summary": function_summary,
            "disease_association_summary": association if not summary else summary,
            "function_source": function_source,
            "function_status_reason": status_reason,
        }

    if ot.get("available"):
        seen: set[str] = set()
        for row in ot.get("candidates", [])[:10]:
            symbol = row["symbol"]
            score = float(row.get("score") or 0.0)
            summary = summarize_gene_association(symbol, row.get("name") or symbol, score, disease_name)
            local_candidate = local_candidates.get(symbol)
            enriched = enrich_candidate(symbol, row.get("name"), summary, local_candidate)
            candidates.append(
                CandidateGene(
                    symbol=symbol,
                    score=score,
                    reasons=[
                        summary,
                        *(
                            local_candidate.reasons[:2]
                            if local_candidate and local_candidate.reasons
                            else []
                        ),
                    ],
                    **enriched,
                    source="Open Targets",
                    provenance={
                        "score": _prov("external_database", "Open Targets"),
                        "summary": _prov("external_database" if enriched["function_source"] == "UniProt" else "local_curated", enriched["function_source"] or "Open Targets"),
                        "function_summary": _prov("external_database" if enriched["function_source"] == "UniProt" else "local_curated", enriched["function_source"] or "Open Targets"),
                    },
                )
            )
            seen.add(symbol)
        if len(candidates) < 10:
            for candidate in discovery.candidates:
                if candidate.symbol in seen:
                    continue
                enriched = enrich_candidate(candidate.symbol, candidate.gene_name or candidate.symbol, candidate.summary or candidate.function_summary or "", candidate)
                candidates.append(
                    candidate.model_copy(
                        update={
                            **enriched,
                            "source": candidate.source or "Local fallback",
                            "provenance": candidate.provenance or {"score": _prov("local_curated", "Local fallback")},
                        }
                    )
                )
                seen.add(candidate.symbol)
                if len(candidates) >= 10:
                    break
    else:
        candidates = []
        for c in discovery.candidates[:10]:
            enriched = enrich_candidate(c.symbol, c.gene_name or c.symbol, c.summary or c.function_summary or "", c)
            candidates.append(
                c.model_copy(
                    update={
                        **enriched,
                        "source": "Local fallback",
                        "provenance": c.provenance or {"score": _prov("local_curated", "Local fallback")},
                    }
                )
            )

    selected = next((c for c in candidates if c.symbol == gene_symbol), candidates[0] if candidates else None)
    if selected is None:
        selected = CandidateGene(symbol=gene_symbol, score=0.5, reasons=[f"User-selected gene {gene_symbol}"], source="User selection")

    return discovery.model_copy(
        update={
            "disease_id": evidence.disease.get("id"),
            "label": disease_name,
            "summary": evidence.summaries.get("disease"),
            "candidates": candidates,
            "external_evidence_available": ot.get("available", False),
            "evidence_notice": None if ot.get("available") else evidence.evidence_notice,
            "provenance": {
                "label": _prov("external_database" if ot.get("available") else "local_curated", "Open Targets" if ot.get("available") else "Local fallback"),
                "candidates": _prov("external_database" if ot.get("available") else "local_curated", "Open Targets" if ot.get("available") else "Local fallback"),
            },
            "raw_evidence": {"open_targets": ot},
        }
    )


def _build_mutation(mutation: MutationResult, evidence: NormalizedEvidence) -> MutationResult:
    variant = evidence.variant
    clin = evidence.raw.get("clinvar", {})
    summary = evidence.summaries.get("mutation") or summarize_mutation(
        mutation.gene,
        mutation.mutation,
        variant.get("variant_type") or mutation.kind,
        variant.get("amino_acid_change"),
        variant.get("clinvar_classification"),
        bool(variant.get("clinvar_available")),
    )

    provenance = {
        "kind": _prov("external_database" if clin.get("available") else "computed_model", "ClinVar" if clin.get("available") else "HGVS parser"),
        "clinvar_classification": _prov("external_database", "ClinVar") if variant.get("clinvar_classification") else _prov("computed_model", "HGVS parser"),
        "activity_multiplier": _prov("simulator_assumption", "Simulator model"),
        "stability_multiplier": _prov("simulator_assumption", "Simulator model"),
        "binding_multiplier": _prov("simulator_assumption", "Simulator model"),
    }

    return mutation.model_copy(
        update={
            "amino_acid_change": variant.get("amino_acid_change"),
            "clinvar_classification": variant.get("clinvar_classification"),
            "phenotypes": variant.get("phenotypes", []),
            "kind": variant.get("variant_type") or mutation.kind,
            "summary": summary,
            "biological_interpretation": limit_sentences(mutation.biological_interpretation, 3),
            "dna_rna_protein_explanation": limit_sentences(mutation.dna_rna_protein_explanation, 3),
            "source": "ClinVar" if clin.get("available") else "HGVS parser + Local fallback",
            "external_evidence_available": clin.get("available", False),
            "evidence_notice": None if clin.get("available") else evidence.evidence_notice,
            "provenance": provenance,
            "raw_evidence": {"clinvar": clin},
        }
    )


def _build_protein(protein: ProteinEffectResult, evidence: NormalizedEvidence, mutation: MutationResult) -> ProteinEffectResult:
    uni = evidence.raw.get("uniprot", {})
    protein_info = evidence.protein
    functional = summarize_functional_impact(
        mutation.gene,
        protein_info.get("domain_hit"),
        evidence.variant.get("clinvar_classification"),
        protein.activity,
    )

    provenance = {
        "protein_name": _prov("external_database" if uni.get("available") else "local_curated", "UniProt" if uni.get("available") else "Local fallback"),
        "function_summary": _prov("external_database" if uni.get("available") else "local_curated", "UniProt" if uni.get("available") else "Local fallback"),
        "activity": _prov("simulator_assumption", "Simulator model"),
        "stability": _prov("simulator_assumption", "Simulator model"),
        "binding": _prov("simulator_assumption", "Simulator model"),
        "loss_of_function_score": _prov("computed_model", "Simulator model"),
        "structural_impact_placeholder": _prov(
            "external_database" if protein_info.get("structure_source") not in {None, "none_found"} else "missing_evidence",
            protein_info.get("structure_source_label") or "Structure source",
        ),
    }
    structure_label = protein_info.get("structure_source_label") or "No public structure record found after checks"
    structure_reason = protein_info.get("structure_status_reason") or ""

    return protein.model_copy(
        update={
            "protein_name": protein_info.get("name") or protein.protein_name,
            "protein_id": protein_info.get("accession") or protein.protein_id,
            "function_summary": protein_info.get("function_summary"),
            "mutation_location": f"Position {mutation.position}" if mutation.position else None,
            "domain_hit": protein_info.get("domain_hit") or (protein.affected_domains[0] if protein.affected_domains else mutation.domain),
            "functional_impact_summary": functional,
            "structural_impact_placeholder": (
                f"AlphaFold structure available; confidence near selected residue is {protein_info.get('alphafold_confidence_label') or 'unknown'}."
                if protein_info.get("alphafold_available")
                else f"Structure context source: {structure_label}. {structure_reason}".strip()
            ),
            "summary": protein_info.get("function_summary") or protein_info.get("summary"),
            "explanation": limit_sentences(protein.explanation, 3),
            "source": "UniProt + Simulator" if uni.get("available") else "Local fallback + Simulator",
            "external_evidence_available": uni.get("available", False),
            "evidence_notice": None if uni.get("available") else evidence.evidence_notice,
            "provenance": provenance,
            "raw_evidence": {
                "uniprot": {k: v for k, v in uni.items() if k not in {"raw_entry"}},
                "alphafold": evidence.raw.get("alphafold", {}),
            },
        }
    )


def _build_pathway(pathway: PathwayResult, evidence: NormalizedEvidence, pathway_id: Optional[str], pathway_name: Optional[str]) -> PathwayResult:
    react = evidence.raw.get("reactome", {})
    pathways = evidence.pathways
    selected = pathways[0] if pathways else {}
    summary = evidence.summaries.get("pathway")
    if not summary and selected:
        summary = summarize_pathway(
            selected.get("displayName") or pathway.label,
            selected.get("stId") or pathway_id or "",
            evidence.gene.get("symbol") or "",
        )

    return pathway.model_copy(
        update={
            "reactome_pathways": pathways,
            "reactome_participants": react.get("participants", []),
            "selected_pathway_id": pathway.selected_pathway_id or pathway_id or selected.get("stId"),
            "selected_pathway_name": pathway.selected_pathway_name or pathway_name or selected.get("displayName"),
            "summary": limit_sentences(summary or pathway.description, 3),
            "description": limit_sentences(pathway.description, 3),
            "explanation": limit_sentences(pathway.explanation, 3),
            "simulation_model_note": pathway.simulation_model_note,
            "source": pathway.selected_pathway_source or "Simulator model",
            "external_evidence_available": react.get("available", False),
            "evidence_notice": None if react.get("available") else evidence.evidence_notice,
            "computed_from_gene": pathway.selected_gene,
            "computed_from_pathway": pathway.selected_pathway_name or pathway.label,
            "computed_from_protein_activity": str(
                pathway.node_activities.get(pathway.selected_gene or "", 0.5)
            ),
            "provenance": {
                "reactome_pathways": _prov("external_database" if react.get("available") else "local_curated", "Reactome"),
                "nodes": _prov("computed_model", "Pathway simulator"),
                "edges": _prov("simulator_assumption", "Dynamic pathway model"),
                "disrupted_processes": _prov("computed_model", "Pathway simulator"),
            },
            "raw_evidence": {"reactome": react},
        }
    )


def run_searchable_pipeline(
    local_kb: Dict[str, Any],
    disease_id: str,
    disease_name: str,
    gene_symbol: str,
    mutation_notation: str,
    use_external_evidence: bool = True,
    pathway_id: Optional[str] = None,
    pathway_name: Optional[str] = None,
    protein_accession: Optional[str] = None,
) -> Tuple[DiseaseDiscoveryResult, MutationResult, ProteinEffectResult, PathwayResult, NormalizedEvidence, bool, Optional[str]]:
    symbol = normalize_gene_symbol(gene_symbol)
    embedded_gene = embedded_gene_symbol_from_variant_query(mutation_notation)
    if embedded_gene and embedded_gene != symbol:
        raise ValueError(INVALID_COMBINATION_MSG)

    if use_external_evidence:
        evidence = fetch_normalized_evidence(
            disease_id, disease_name, symbol, mutation_notation, local_kb, pathway_id, pathway_name, protein_accession
        )
        kb = build_simulation_kb(
            local_kb,
            disease_id,
            disease_name,
            evidence.disease.get("description"),
            symbol,
            mutation_notation,
            evidence.raw.get("open_targets", {}),
            evidence.raw.get("clinvar", {}),
            evidence.raw.get("uniprot", {}),
            evidence.raw.get("reactome", {}),
            pathway_id,
            pathway_name,
        )
    else:
        return _build_local_fallback_pipeline(
            local_kb,
            disease_id,
            disease_name,
            symbol,
            mutation_notation,
            pathway_id,
            pathway_name,
        )

    discovery = discover_candidate_genes(kb, LOCAL_DISEASE_KEY)
    mutation = interpret_mutation(kb, symbol, mutation_notation)
    protein = predict_protein_effect(kb, mutation)
    pathway = simulate_pathway(kb, protein)

    discovery = _build_discovery(discovery, evidence, symbol)
    mutation = _build_mutation(mutation, evidence)
    protein = _build_protein(protein, evidence, mutation)
    pathway = _build_pathway(pathway, evidence, pathway_id, pathway_name)

    return (
        discovery,
        mutation,
        protein,
        pathway,
        evidence,
        evidence.external_evidence_available,
        evidence.evidence_notice,
    )

# Backward-compatible alias
run_phase1_pipeline = run_searchable_pipeline
