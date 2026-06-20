from __future__ import annotations

from typing import Any, Dict, List

from app.models import PathwayEdge, PathwayNodeState, PathwayResult, ProteinEffectResult
from app.services.utils import clamp, round4


def _get_active_pathway(kb: Dict[str, Any], gene_symbol: str) -> tuple[str, Dict[str, Any]]:
    gene = kb["genes"][gene_symbol]
    pathway_key = gene.get("active_pathway_key") or gene.get("pathways", [None])[0]
    if not pathway_key or pathway_key not in kb.get("pathways", {}):
        raise ValueError(f"No active pathway configured for gene '{gene_symbol}'.")
    return pathway_key, kb["pathways"][pathway_key]


def simulate_pathway(kb: Dict[str, Any], protein_effect: ProteinEffectResult, iterations: int = 8) -> PathwayResult:
    gene_symbol = protein_effect.gene
    pathway_id, pathway = _get_active_pathway(kb, gene_symbol)
    gene_meta = kb["genes"][gene_symbol]

    baseline = {node_id: meta["baseline"] for node_id, meta in pathway["nodes"].items()}
    activity = dict(baseline)

    perturbation_node = gene_symbol if gene_symbol in activity else gene_symbol
    if perturbation_node in activity:
        activity[perturbation_node] = clamp(baseline[perturbation_node] * protein_effect.activity)

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
        if perturbation_node in next_activity:
            next_activity[perturbation_node] = clamp(baseline[perturbation_node] * protein_effect.activity)
        activity = next_activity

    node_states: List[PathwayNodeState] = []
    disrupted: List[str] = []
    changed_nodes: List[str] = []
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
        if abs(delta) >= 0.08:
            changed_nodes.append(node_id)
        if abs(delta) >= 0.12 and meta["type"] in {"process", "pathway"}:
            direction = "increased" if delta > 0 else "decreased"
            disrupted.append(f"{node_id} {direction}")

    pathway_edges = [PathwayEdge(**edge) for edge in edges]
    source_label = pathway.get("selected_pathway_source", "Simulator model")
    is_generic = pathway.get("is_generic_fallback", False)

    explanation = (
        f"Pathway simulation perturbed {gene_symbol} ({gene_meta.get('protein_id') or 'unknown'}) "
        f"using protein activity={protein_effect.activity:.2f}. "
        f"Signal propagated through {pathway['label']}. "
        f"Changed nodes: {', '.join(changed_nodes) or 'none'}."
    )

    return PathwayResult(
        pathway_id=pathway_id,
        label=pathway["label"],
        description=pathway["description"],
        nodes=node_states,
        edges=pathway_edges,
        disrupted_processes=disrupted,
        explanation=explanation,
        selected_gene=gene_symbol,
        selected_protein=gene_meta.get("protein_id"),
        selected_pathway_name=pathway.get("selected_pathway_name") or pathway["label"],
        selected_pathway_source=source_label,
        selected_pathway_id=pathway.get("selected_pathway_id"),
        is_generic_fallback=is_generic,
        node_activities={k: round4(v) for k, v in activity.items()},
        baseline_activities={k: round4(v) for k, v in baseline.items()},
        changed_nodes=changed_nodes,
        simulation_model_note=(
            "Generic simulator pathway generated from selected gene evidence; edge weights are model assumptions."
            if is_generic
            else "Reactome provides pathway membership evidence; edge weights and propagation are simulator assumptions."
        ),
    )
