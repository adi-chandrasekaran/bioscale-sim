from __future__ import annotations

from typing import Any, Dict, List

from app.models import MutationResult, ProteinEffectResult
from app.services.utils import clamp, round4


def predict_protein_effect(kb: Dict[str, Any], mutation: MutationResult) -> ProteinEffectResult:
    gene = kb["genes"][mutation.gene]
    affected_domains: List[str] = []
    for domain in gene.get("domains", []):
        if mutation.position and domain["start"] <= mutation.position <= domain["end"]:
            affected_domains.append(domain["name"])
    if not affected_domains:
        affected_domains = [mutation.domain]

    activity = clamp(mutation.activity_multiplier)
    stability = clamp(mutation.stability_multiplier)
    binding = clamp(mutation.binding_multiplier)
    loss_of_function_score = round4(1.0 - ((activity * 0.45) + (stability * 0.20) + (binding * 0.35)))

    explanation = (
        f"The mutation is converted into three protein-level parameters: activity={activity:.2f}, "
        f"stability={stability:.2f}, and binding={binding:.2f}. These values summarize how much normal "
        f"protein function remains. The combined loss-of-function score is {loss_of_function_score:.2f}; "
        "this structured output is passed into the pathway simulator as a reduced activity for the affected protein."
    )

    return ProteinEffectResult(
        gene=mutation.gene,
        protein_name=gene["name"],
        protein_id=gene.get("protein_id") or f"unknown:{mutation.gene}",
        mutation=mutation.mutation,
        activity=round4(activity),
        stability=round4(stability),
        binding=round4(binding),
        loss_of_function_score=loss_of_function_score,
        affected_domains=affected_domains,
        explanation=explanation,
    )
