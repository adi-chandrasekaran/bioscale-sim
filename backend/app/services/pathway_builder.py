from __future__ import annotations

import copy
import re
from typing import Any, Dict, Optional, Tuple

P53_DEMO_GENE = "TP53"
P53_PATHWAY_KEY = "p53_damage_response"
P53_RELATED_PATTERN = re.compile(r"p53|tp53|dna damage", re.IGNORECASE)


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").upper() or "PATHWAY"


def is_p53_demo_pathway(
    gene_symbol: str,
    pathway_id: Optional[str] = None,
    pathway_name: Optional[str] = None,
) -> bool:
    """Use curated p53 teaching graph only for TP53 without an explicit non-p53 Reactome selection."""
    if gene_symbol.upper() != P53_DEMO_GENE:
        return False
    if pathway_id or pathway_name:
        combined = f"{pathway_id or ''} {pathway_name or ''}"
        if pathway_name and not P53_RELATED_PATTERN.search(combined):
            return False
    return True


def build_dynamic_pathway(
    gene_symbol: str,
    protein_id: Optional[str],
    disease_name: str,
    reactome: Optional[Dict[str, Any]] = None,
    pathway_id: Optional[str] = None,
    pathway_name: Optional[str] = None,
    local_kb: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any], str]:
    """
    Return (pathway_key, pathway_dict, source_label).
    Never returns p53_damage_response unless is_p53_demo_pathway is True.
    """
    symbol = gene_symbol.upper()
    local_kb = local_kb or {}

    if is_p53_demo_pathway(symbol, pathway_id, pathway_name) and P53_PATHWAY_KEY in local_kb.get("pathways", {}):
        pathway = copy.deepcopy(local_kb["pathways"][P53_PATHWAY_KEY])
        return P53_PATHWAY_KEY, pathway, "Local curated p53 demo model"

    selected_pathway_name = pathway_name
    selected_pathway_id = pathway_id
    source = "Generic simulator model"

    reactome = reactome or {}
    pathways = reactome.get("pathways", [])
    if not selected_pathway_id and pathways:
        primary = pathways[0]
        selected_pathway_id = primary.get("stId")
        selected_pathway_name = primary.get("displayName")
        source = "Reactome membership + simulator model"

    if pathway_id and pathway_name:
        selected_pathway_id = pathway_id
        selected_pathway_name = pathway_name
        source = "Reactome selected pathway + simulator model"

    associated_label = selected_pathway_name or f"{symbol} associated pathway"
    pathway_key = _slug(f"dynamic_{symbol}_{selected_pathway_id or associated_label}")

    nodes = {
        "INPUT_SIGNAL": {"type": "stress", "baseline": 0.35},
        "DISEASE_CONTEXT": {"type": "context", "baseline": 0.40},
        symbol: {"type": "protein", "baseline": 0.70},
        "ASSOCIATED_PATHWAY": {"type": "pathway", "baseline": 0.55},
        "FUNCTIONAL_PROCESS_1": {"type": "process", "baseline": 0.50},
        "FUNCTIONAL_PROCESS_2": {"type": "process", "baseline": 0.45},
        "CELL_OUTCOME": {"type": "process", "baseline": 0.42},
    }
    edges = [
        {"source": "INPUT_SIGNAL", "target": symbol, "relation": "activates", "weight": 0.70},
        {"source": "DISEASE_CONTEXT", "target": symbol, "relation": "activates", "weight": 0.55},
        {"source": symbol, "target": "ASSOCIATED_PATHWAY", "relation": "activates", "weight": 0.80},
        {"source": "ASSOCIATED_PATHWAY", "target": "FUNCTIONAL_PROCESS_1", "relation": "activates", "weight": 0.75},
        {"source": symbol, "target": "FUNCTIONAL_PROCESS_2", "relation": "activates", "weight": 0.65},
        {"source": "FUNCTIONAL_PROCESS_1", "target": "CELL_OUTCOME", "relation": "activates", "weight": 0.70},
        {"source": "FUNCTIONAL_PROCESS_2", "target": "CELL_OUTCOME", "relation": "activates", "weight": 0.60},
    ]

    if source.startswith("Generic"):
        description = (
            f"Generic simulator pathway generated from selected gene {symbol} evidence; "
            "edge weights are model assumptions."
        )
    else:
        description = (
            f"Dynamic pathway centered on {symbol} ({protein_id or 'unknown accession'}) "
            f"with Reactome pathway evidence: {associated_label}. "
            "Edge directions and weights are simulator assumptions."
        )

    pathway = {
        "label": associated_label if source != "Generic simulator model" else f"{symbol} generic simulator pathway",
        "description": description,
        "nodes": nodes,
        "edges": edges,
        "selected_gene": symbol,
        "selected_protein": protein_id,
        "selected_pathway_id": selected_pathway_id,
        "selected_pathway_name": selected_pathway_name,
        "selected_pathway_source": source,
        "is_generic_fallback": source.startswith("Generic"),
        "disease_context": disease_name,
    }
    return pathway_key, pathway, source
