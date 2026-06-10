from __future__ import annotations

from typing import Any, Dict, List

from app.models import PathwayEdge, PathwayNodeState, PathwayResult, ProteinEffectResult
from app.services.utils import clamp, round4


def simulate_pathway(kb: Dict[str, Any], protein_effect: ProteinEffectResult, iterations: int = 8) -> PathwayResult:
    gene = kb["genes"][protein_effect.gene]
    pathway_id = gene.get("pathways", ["p53_damage_response"])[0]
    pathway = kb["pathways"][pathway_id]

    # Start at baseline node activities.
    baseline = {node_id: meta["baseline"] for node_id, meta in pathway["nodes"].items()}
    activity = dict(baseline)

    # Inject protein perturbation from mutation/protein layer.
    if protein_effect.gene in activity:
        activity[protein_effect.gene] = clamp(activity[protein_effect.gene] * protein_effect.activity)

    # Propagate through pathway network. This is deliberately interpretable, not pretending to be full biophysics.
    edges = pathway["edges"]
    for _ in range(iterations):
        next_activity = dict(activity)
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            weight = float(edge["weight"])
            signal_delta = (activity[source] - baseline[source]) * weight
            if edge["relation"] == "activates":
                next_activity[target] = clamp(next_activity[target] + signal_delta)
            elif edge["relation"] == "inhibits":
                next_activity[target] = clamp(next_activity[target] - signal_delta)
        # Keep the mutated protein anchored to the predicted loss-of-function value.
        if protein_effect.gene in next_activity:
            next_activity[protein_effect.gene] = clamp(baseline[protein_effect.gene] * protein_effect.activity)
        activity = next_activity

    node_states: List[PathwayNodeState] = []
    disrupted: List[str] = []
    for node_id, meta in pathway["nodes"].items():
        delta = activity[node_id] - baseline[node_id]
        node_states.append(
            PathwayNodeState(
                id=node_id,
                type=meta["type"],
                baseline=round4(baseline[node_id]),
                activity=round4(activity[node_id]),
                delta=round4(delta),
            )
        )
        if abs(delta) >= 0.12 and meta["type"] == "process":
            direction = "increased" if delta > 0 else "decreased"
            disrupted.append(f"{node_id} {direction}")

    pathway_edges = [PathwayEdge(**edge) for edge in edges]
    explanation = (
        f"The pathway layer placed the altered {protein_effect.gene} protein into {pathway['label']}. "
        "The reduced protein activity was propagated through activation and inhibition edges. "
        "The strongest downstream changes are reported as disrupted cellular processes."
    )

    return PathwayResult(
        pathway_id=pathway_id,
        label=pathway["label"],
        description=pathway["description"],
        nodes=node_states,
        edges=pathway_edges,
        disrupted_processes=disrupted,
        explanation=explanation,
    )
