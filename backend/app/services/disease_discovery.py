from __future__ import annotations

from typing import Any, Dict, List

from app.adapters.summarizer import is_placeholder_definition, known_gene_function
from app.models import CandidateGene, DiseaseDiscoveryResult


def discover_candidate_genes(kb: Dict[str, Any], disease_key: str) -> DiseaseDiscoveryResult:
    if disease_key not in kb["diseases"]:
        raise ValueError(f"Unknown disease '{disease_key}'. Available: {list(kb['diseases'].keys())}")

    disease = kb["diseases"][disease_key]
    candidates: List[CandidateGene] = []

    for symbol in disease["known_genes"]:
        gene = kb["genes"].get(symbol, {})
        base_score = disease.get("candidate_gene_weights", {}).get(symbol, 0.5)
        interaction_bonus = min(len(gene.get("interactions", [])) * 0.03, 0.15)
        pathway_bonus = min(len(gene.get("pathways", [])) * 0.04, 0.12)
        score = min(base_score + interaction_bonus + pathway_bonus, 1.0)

        reasons = []
        if gene.get("pathways"):
            reasons.append(f"Participates in {', '.join(gene['pathways'])}")
        if gene.get("interactions"):
            reasons.append(f"Interacts with {', '.join(gene['interactions'][:4])}")
        if gene.get("expressed_in"):
            reasons.append(f"Expressed in {', '.join(gene['expressed_in'][:3])}")
        if symbol in disease.get("candidate_gene_weights", {}):
            reasons.append(f"Prior curated teaching data links {symbol} to {disease['label']} biology")

        known_function = known_gene_function(symbol)
        summary = known_function or gene.get("function_summary") or gene.get("name")
        if is_placeholder_definition(summary):
            summary = known_function or gene.get("name") or f"{symbol} is included in the ranked disease-gene evidence for this run."
        if not summary and reasons:
            summary = reasons[0]

        candidates.append(
            CandidateGene(
                symbol=symbol,
                score=round(score, 4),
                reasons=reasons,
                pathways=gene.get("pathways", []),
                interactions=gene.get("interactions", []),
                summary=summary,
                function_summary=known_function or (None if is_placeholder_definition(gene.get("function_summary")) else gene.get("function_summary")),
            )
        )

    candidates.sort(key=lambda c: c.score, reverse=True)
    return DiseaseDiscoveryResult(
        disease=disease_key,
        label=disease["label"],
        affected_cell_context=disease["affected_cell_context"],
        candidates=candidates,
    )
