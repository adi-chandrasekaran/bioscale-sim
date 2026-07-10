from __future__ import annotations

from typing import Any

from app.models import SimulationResult


def _confidence(result: SimulationResult, layer: str) -> float:
    external = 0.12 if result.external_evidence_available else 0.0
    mutation = result.mutation_result.confidence * 0.35
    layer_weight = {"mutation": 0.42, "protein": 0.36, "pathway": 0.30, "cell": 0.26, "population": 0.22, "ecosystem": 0.20}[layer]
    return round(min(0.95, 0.25 + external + mutation + layer_weight), 2)


def build_reasoning(result: SimulationResult) -> dict[str, Any]:
    mutation = result.mutation_result
    protein = result.protein_effect
    pathway = result.pathway_result
    cell = result.cell_phenotype
    population = result.population_result
    ecosystem = result.ecosystem_result

    domain = protein.domain_hit or mutation.domain or "a functionally relevant protein region"
    primary_process = pathway.disrupted_processes[0] if pathway.disrupted_processes else pathway.label
    steps = [
        {
            "layer": "Mutation",
            "evidence": f"{mutation.gene} {mutation.mutation} is interpreted as {mutation.kind} ({mutation.source}).",
            "reasoning": (
                f"The mutation layer first parses the notation, classifies the variant as {mutation.kind}, and maps it to "
                f"{domain}. The simulator then converts this into activity, stability, and binding multipliers. "
                f"The activity multiplier is {mutation.activity_multiplier:.2f}, so downstream protein activity is scaled before pathway propagation."
            ),
            "consequence": f"The encoded {protein.protein_name} enters the model with altered molecular function rather than being treated as a normal protein.",
            "confidence": _confidence(result, "mutation"),
            "provenance": mutation.source,
        },
        {
            "layer": "Protein",
            "evidence": f"Modeled activity={protein.activity:.2f}, stability={protein.stability:.2f}, binding={protein.binding:.2f}.",
            "reasoning": (
                f"The protein layer combines remaining activity ({protein.activity:.2f}), stability ({protein.stability:.2f}), "
                f"and binding ({protein.binding:.2f}) with the affected region {domain}. Lower remaining function increases the loss-of-function score "
                f"and changes how {protein.gene} can regulate downstream pathway partners."
            ),
            "consequence": f"Signal propagation through {pathway.label} is altered before the cell-level phenotype is computed.",
            "confidence": _confidence(result, "protein"),
            "provenance": protein.source,
        },
        {
            "layer": "Pathway",
            "evidence": f"{len(pathway.changed_nodes)} modeled nodes changed; key process: {primary_process}.",
            "reasoning": (
                "The pathway layer treats nodes as biological steps and edges as activating or inhibitory relationships. "
                "It starts from the selected gene/protein effect, propagates the activity change through weighted edges, and records which pathway nodes move up or down."
            ),
            "consequence": "Repair, survival, proliferation, stress, or homeostasis signals reaching the cell are rebalanced.",
            "confidence": _confidence(result, "pathway"),
            "provenance": pathway.source,
        },
        {
            "layer": "Cell",
            "evidence": f"Repair={cell.repair_capacity:.2f}, proliferation={cell.proliferation_rate:.2f}, apoptosis={cell.apoptosis_rate:.2f}, instability={cell.genomic_instability:.2f}.",
            "reasoning": (
                f"The cell layer maps pathway outputs into proliferation ({cell.proliferation_rate:.2f}), apoptosis/death response ({cell.apoptosis_rate:.2f}), "
                f"repair/homeostasis ({cell.repair_capacity:.2f}), stress, inflammation, and genomic instability. "
                "These traits are deterministic model outputs with provenance from the pathway and protein layers."
            ),
            "consequence": "The altered cell state changes its ability to persist, repair damage, die appropriately, and reproduce.",
            "confidence": _confidence(result, "cell"),
            "provenance": cell.source,
        },
        {
            "layer": "Population",
            "evidence": f"Final mutated fraction={population.final_mutated_fraction:.2f}; expansion score={population.clonal_expansion_score:.2f}.",
            "reasoning": (
                "The population layer repeatedly applies the cell phenotype over the requested number of steps. "
                "Higher proliferation and lower apoptosis increase expansion; stronger repair or immune removal limits expansion."
            ),
            "consequence": "The burden of altered cells changes the surrounding tissue environment.",
            "confidence": _confidence(result, "population"),
            "provenance": population.source,
        },
        {
            "layer": "Ecosystem",
            "evidence": f"Burden={ecosystem.tumor_like_burden:.2f}, inflammation={ecosystem.inflammation:.2f}, immune clearance={ecosystem.immune_clearance:.2f}.",
            "reasoning": (
                "The ecosystem layer combines the final altered-cell burden with immune clearance, inflammation, and nutrient stress. "
                "It estimates whether the surrounding tissue environment looks controlled or disease-promoting for this run."
            ),
            "consequence": f"The modeled ecosystem risk reaches {ecosystem.ecosystem_risk_score:.2f}.",
            "confidence": _confidence(result, "ecosystem"),
            "provenance": ecosystem.source,
        },
    ]
    return {
        "steps": steps,
        "causal_graph": {
            "nodes": [{"id": step["layer"], "label": step["layer"], "confidence": step["confidence"]} for step in steps],
            "edges": [{"source": steps[i]["layer"], "target": steps[i + 1]["layer"], "label": steps[i]["consequence"]} for i in range(len(steps) - 1)],
        },
        "summary": " → ".join(step["layer"] for step in steps),
    }
