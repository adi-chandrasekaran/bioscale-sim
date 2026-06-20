from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.adapters.clinvar import safe_fetch_variant_evidence
from app.adapters.open_targets import safe_fetch_disease_targets_by_id
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
) -> NormalizedEvidence:
    symbol = normalize_gene_symbol(gene_symbol)
    parsed = parse_hgvs_protein(mutation_notation)
    position = parsed["position"] if parsed else None

    open_targets = safe_fetch_disease_targets_by_id(disease_id, limit=10)
    clinvar = safe_fetch_variant_evidence(symbol, mutation_notation)
    uniprot = safe_fetch_protein_evidence(symbol, local_kb, mutation_position=position)
    reactome = safe_fetch_pathway_evidence(symbol, local_kb)

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
            "name": next((c.get("name") for c in open_targets.get("candidates", []) if c.get("symbol") == symbol), symbol),
            "association_score": assoc_score,
            "ensembl_id": next((c.get("ensembl_id") for c in open_targets.get("candidates", []) if c.get("symbol") == symbol), None),
            "summary": summarize_gene_fallback(symbol, disease_name),
        },
        "variant": {
            "notation": mutation_notation,
            "variant_type": clinvar.get("variant_type") or (infer_variant_type_from_notation(mutation_notation) if mutation_notation else ("missense" if parsed else "unknown")),
            "amino_acid_change": clinvar.get("amino_acid_change") or amino_acid_change_text(mutation_notation),
            "clinvar_classification": clinvar.get("clinvar_classification"),
            "phenotypes": clinvar.get("phenotypes", []),
            "clinvar_available": clinvar.get("available", False),
            "summary": summarize_variant_fallback(symbol, mutation_notation, clinvar.get("variant_type") or infer_variant_type_from_notation(mutation_notation)),
        },
        "protein": {
            "name": uniprot.get("protein_name") or symbol,
            "accession": uniprot.get("accession"),
            "function_raw": uniprot.get("function_raw"),
            "function_summary": protein_summary or summarize_protein_fallback(uniprot.get("protein_name") or symbol, symbol),
            "domain_hit": uniprot.get("domain_hit"),
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
        raw={
            "open_targets": open_targets,
            "clinvar": {k: v for k, v in clinvar.items() if k != "raw"},
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

    if ot.get("available"):
        for row in ot.get("candidates", [])[:10]:
            symbol = row["symbol"]
            score = float(row.get("score") or 0.0)
            summary = summarize_gene_association(symbol, row.get("name") or symbol, score, disease_name)
            candidates.append(
                CandidateGene(
                    symbol=symbol,
                    score=score,
                    reasons=[summary],
                    summary=limit_sentences(summary, 2),
                    source="Open Targets",
                    provenance={
                        "score": _prov("external_database", "Open Targets"),
                        "summary": _prov("external_database", "Open Targets"),
                    },
                )
            )
    else:
        candidates = [
            c.model_copy(
                update={
                    "summary": limit_sentences(c.reasons[0] if c.reasons else f"{c.symbol} candidate", 2),
                    "source": "Local fallback",
                    "provenance": {"score": _prov("local_curated", "Local fallback")},
                }
            )
            for c in discovery.candidates[:10]
        ]

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
        "structural_impact_placeholder": _prov("simulator_assumption", "AlphaFold TODO"),
    }

    return protein.model_copy(
        update={
            "protein_name": protein_info.get("name") or protein.protein_name,
            "protein_id": protein_info.get("accession") or protein.protein_id,
            "function_summary": protein_info.get("function_summary"),
            "mutation_location": f"Position {mutation.position}" if mutation.position else None,
            "domain_hit": protein_info.get("domain_hit") or (protein.affected_domains[0] if protein.affected_domains else mutation.domain),
            "functional_impact_summary": functional,
            "summary": protein_info.get("function_summary") or protein_info.get("summary"),
            "explanation": limit_sentences(protein.explanation, 3),
            "source": "UniProt + Simulator" if uni.get("available") else "Local fallback + Simulator",
            "external_evidence_available": uni.get("available", False),
            "evidence_notice": None if uni.get("available") else evidence.evidence_notice,
            "provenance": provenance,
            "raw_evidence": {"uniprot": {k: v for k, v in uni.items() if k not in {"raw_entry"}}},
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
) -> Tuple[DiseaseDiscoveryResult, MutationResult, ProteinEffectResult, PathwayResult, NormalizedEvidence, bool, Optional[str]]:
    symbol = normalize_gene_symbol(gene_symbol)
    embedded_gene = embedded_gene_symbol_from_variant_query(mutation_notation)
    if embedded_gene and embedded_gene != symbol:
        raise ValueError(INVALID_COMBINATION_MSG)

    if use_external_evidence:
        evidence = fetch_normalized_evidence(
            disease_id, disease_name, symbol, mutation_notation, local_kb, pathway_id, pathway_name
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
