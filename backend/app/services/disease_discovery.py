from __future__ import annotations

from typing import Any, Dict, List

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
            reasons.append("Listed as disease-relevant in the local demo knowledge base")

        candidates.append(
            CandidateGene(
                symbol=symbol,
                score=round(score, 4),
                reasons=reasons,
                pathways=gene.get("pathways", []),
                interactions=gene.get("interactions", []),
            )
        )

    candidates.sort(key=lambda c: c.score, reverse=True)
    return DiseaseDiscoveryResult(
        disease=disease_key,
        label=disease["label"],
        affected_cell_context=disease["affected_cell_context"],
        candidates=candidates,
    )
