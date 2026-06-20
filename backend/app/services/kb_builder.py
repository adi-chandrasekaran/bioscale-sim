from __future__ import annotations

import copy
from typing import Any, Dict, Optional

from app.adapters.normalizer import (
    amino_acid_change_text,
    infer_multipliers_from_classification,
    normalize_gene_symbol,
    parse_hgvs_protein,
)
from app.adapters.summarizer import summarize_protein_function, strip_citations
from app.services.pathway_builder import build_dynamic_pathway

LOCAL_DISEASE_KEY = "selected_disease"


def build_simulation_kb(
    local_kb: Dict[str, Any],
    disease_id: str,
    disease_name: str,
    disease_description: Optional[str],
    gene_symbol: str,
    mutation_notation: str,
    open_targets: Dict[str, Any],
    clinvar: Dict[str, Any],
    uniprot: Dict[str, Any],
    reactome: Dict[str, Any],
    pathway_id: Optional[str] = None,
    pathway_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a runtime knowledge base from database evidence with local fallback."""
    kb = copy.deepcopy(local_kb)
    symbol = normalize_gene_symbol(gene_symbol)
    parsed = parse_hgvs_protein(mutation_notation)
    local_diseases = local_kb.get("diseases", {})
    disease_lookup_text = f"{disease_id} {disease_name or ''}".lower()
    fallback_key = next((key for key in local_diseases if key in disease_lookup_text), LOCAL_DISEASE_KEY)
    base_local_disease = copy.deepcopy(local_diseases.get(fallback_key, local_diseases.get(LOCAL_DISEASE_KEY, {})))

    disease = kb.setdefault("diseases", {}).setdefault(LOCAL_DISEASE_KEY, {})
    disease.update(
        {
            "label": disease_name or disease_id,
            "description": strip_citations(disease_description or "")[:400] or f"Selected disease {disease_name}.",
            "affected_cell_context": "database-selected disease context",
            "known_genes": list(base_local_disease.get("known_genes", [])),
            "candidate_gene_weights": dict(base_local_disease.get("candidate_gene_weights", {})),
        }
    )

    candidates = open_targets.get("candidates", [])
    if candidates:
        merged_known_genes: list[str] = []
        merged_weights = dict(base_local_disease.get("candidate_gene_weights", {}))
        for candidate in candidates:
            candidate_symbol = candidate["symbol"]
            if candidate_symbol not in merged_known_genes:
                merged_known_genes.append(candidate_symbol)
            merged_weights[candidate_symbol] = candidate.get("score", merged_weights.get(candidate_symbol, 0.5))
        for local_symbol in base_local_disease.get("known_genes", []):
            if local_symbol not in merged_known_genes:
                merged_known_genes.append(local_symbol)
            merged_weights.setdefault(local_symbol, base_local_disease.get("candidate_gene_weights", {}).get(local_symbol, 0.5))
        disease["known_genes"] = merged_known_genes[:10]
        disease["candidate_gene_weights"] = {symbol_: merged_weights[symbol_] for symbol_ in disease["known_genes"]}
    elif not disease["known_genes"] and symbol:
        disease["known_genes"] = [symbol]
        disease["candidate_gene_weights"] = {symbol: 0.75}

    local_gene = local_kb.get("genes", {}).get(symbol, {})
    protein_id = uniprot.get("accession") or local_gene.get("protein_id") or f"unknown:{symbol}"
    gene_entry = kb.setdefault("genes", {}).setdefault(symbol, {})

    if uniprot.get("available"):
        gene_entry.update(
            {
                "name": uniprot.get("protein_name") or local_gene.get("name") or symbol,
                "function_summary": summarize_protein_function(uniprot.get("function_raw"), uniprot.get("protein_name")),
                "protein_id": protein_id,
                "domains": uniprot.get("domains") or local_gene.get("domains", []),
                "interactions": local_gene.get("interactions", []),
                "expressed_in": local_gene.get("expressed_in", ["human tissues"]),
            }
        )
    else:
        gene_entry.update(local_gene or {"name": symbol, "domains": [], "protein_id": protein_id})

    pathway_key, pathway_dict, pathway_source = build_dynamic_pathway(
        symbol,
        protein_id,
        disease_name or disease_id,
        reactome=reactome,
        pathway_id=pathway_id,
        pathway_name=pathway_name,
        local_kb=local_kb,
    )
    kb.setdefault("pathways", {})[pathway_key] = pathway_dict
    gene_entry["active_pathway_key"] = pathway_key
    gene_entry["pathways"] = [pathway_key]
    gene_entry["selected_pathway_source"] = pathway_source
    if reactome.get("available"):
        gene_entry["reactome_pathway_ids"] = [p.get("stId") for p in reactome.get("pathways", []) if p.get("stId")]
    if pathway_id:
        gene_entry["selected_reactome_pathway_id"] = pathway_id
        gene_entry["selected_reactome_pathway_name"] = pathway_name

    local_mut = local_kb.get("mutations", {}).get(symbol, {}).get(mutation_notation)
    if local_mut:
        mut_entry = copy.deepcopy(local_mut)
    else:
        classification = clinvar.get("clinvar_classification")
        multipliers = infer_multipliers_from_classification(classification)
        domain_hit = uniprot.get("domain_hit") or "unknown domain"
        mut_entry = {
            "notation": mutation_notation,
            "kind": clinvar.get("variant_type") or ("missense" if parsed else "variant"),
            "position": parsed["position"] if parsed else None,
            "from_aa": parsed["from_aa"] if parsed else None,
            "to_aa": parsed["to_aa"] if parsed else None,
            "domain": domain_hit,
            "biological_interpretation": (
                f"Database-backed variant {mutation_notation} in {symbol}. "
                f"Simulator multipliers were inferred from available evidence."
            ),
            **multipliers,
        }

    if clinvar.get("available"):
        if clinvar.get("clinvar_classification"):
            mut_entry["clinvar_classification"] = clinvar["clinvar_classification"]
        if clinvar.get("phenotypes"):
            mut_entry["phenotypes"] = clinvar["phenotypes"]
        if clinvar.get("variant_type") and clinvar["variant_type"] != "unknown":
            mut_entry["kind"] = clinvar["variant_type"]

    if parsed:
        mut_entry.setdefault("position", parsed["position"])
        mut_entry.setdefault("from_aa", parsed["from_aa"])
        mut_entry.setdefault("to_aa", parsed["to_aa"])
        mut_entry.setdefault("notation", parsed["notation"])
        aa = amino_acid_change_text(parsed["notation"])
        if aa:
            mut_entry["biological_interpretation"] = (
                f"{symbol} variant {parsed['notation']} ({aa}) mapped for simulation. "
                + mut_entry.get("biological_interpretation", "")
            )[:500]

    kb.setdefault("mutations", {}).setdefault(symbol, {})[mutation_notation] = mut_entry
    return kb
