from __future__ import annotations

from typing import Dict

from app.models import CellPhenotypeResult, PathwayResult, ProvenanceEntry
from app.services.utils import clamp, round4

P53_PROCESS_NODES = {"DNA_REPAIR", "APOPTOSIS", "CELL_CYCLE_ARREST", "PROLIFERATION_SIGNAL"}


def _prov(category: str, source: str) -> ProvenanceEntry:
    return ProvenanceEntry(category=category, source=source)


def _trait(label: str, score: float, confidence: float, provenance: str, explanation: str) -> dict:
    return {
        "label": label,
        "score": round4(score),
        "confidence": round4(confidence),
        "provenance": provenance,
        "explanation": explanation,
    }


def simulate_cell(pathway: PathwayResult) -> CellPhenotypeResult:
    nodes: Dict[str, float] = {node.id: node.activity for node in pathway.nodes}
    deltas: Dict[str, float] = {node.id: node.delta for node in pathway.nodes}
    has_p53_nodes = any(node_id in nodes for node_id in P53_PROCESS_NODES)

    computed_from = {
        "gene": pathway.selected_gene or "unknown",
        "pathway": pathway.selected_pathway_name or pathway.label,
        "protein_activity": str(nodes.get(pathway.selected_gene or "", 0.5)),
    }

    if has_p53_nodes:
        dna_repair = nodes.get("DNA_REPAIR", 0.5)
        arrest = nodes.get("CELL_CYCLE_ARREST", 0.5)
        apoptosis = nodes.get("APOPTOSIS", 0.4)
        proliferation_signal = nodes.get("PROLIFERATION_SIGNAL", 0.5)
        dna_damage = nodes.get("DNA_DAMAGE", 0.3)

        repair_capacity = clamp(dna_repair)
        apoptosis_rate = clamp(apoptosis * 0.85 + dna_damage * 0.15)
        proliferation_rate = clamp(proliferation_signal * 0.70 + (1.0 - arrest) * 0.30)
        stress_level = clamp(dna_damage * 0.55 + (1.0 - repair_capacity) * 0.45)
        genomic_instability = clamp((1.0 - repair_capacity) * 0.55 + proliferation_rate * 0.30 + (1.0 - arrest) * 0.15)
        inflammatory_signal = clamp(stress_level * 0.55 + genomic_instability * 0.30 + (1.0 - apoptosis_rate) * 0.15)
        secretion_signal = clamp(inflammatory_signal * 0.6 + stress_level * 0.4)
        pathway_disruption_score = clamp(sum(abs(value) for value in deltas.values()) / max(len(deltas), 1))
        functional_loss_score = clamp(1.0 - nodes.get(pathway.selected_gene or "", 0.5))
        stress_signal = stress_level
        survival_signal = clamp((1.0 - apoptosis_rate) * 0.55 + proliferation_rate * 0.45)
        proliferation_signal = proliferation_rate
        repair_or_homeostasis_capacity = repair_capacity

        explanation = (
            f"Cell phenotype derived from p53-specific pathway nodes for {pathway.selected_gene}. "
            "Repair, arrest, apoptosis, and proliferation signals mapped to cell traits."
        )
        mapping_mode = "p53_specific_nodes"
    else:
        gene = pathway.selected_gene or ""
        gene_activity = nodes.get(gene, 0.5)
        functional_1 = nodes.get("FUNCTIONAL_PROCESS_1", 0.5)
        functional_2 = nodes.get("FUNCTIONAL_PROCESS_2", 0.5)
        cell_outcome = nodes.get("CELL_OUTCOME", 0.42)
        input_signal = nodes.get("INPUT_SIGNAL", nodes.get("DISEASE_CONTEXT", 0.35))

        process_deltas = [abs(deltas.get(n, 0.0)) for n in nodes if n in {"FUNCTIONAL_PROCESS_1", "FUNCTIONAL_PROCESS_2", "CELL_OUTCOME", "ASSOCIATED_PATHWAY"}]
        pathway_disruption_score = clamp(sum(process_deltas) / max(len(process_deltas), 1))
        functional_loss_score = clamp(1.0 - gene_activity)
        stress_signal = clamp(input_signal)
        survival_signal = clamp(cell_outcome)
        proliferation_signal = clamp(cell_outcome * (1.0 - functional_loss_score * 0.35) + functional_1 * 0.25)
        repair_or_homeostasis_capacity = clamp((functional_1 + functional_2) / 2.0)

        repair_capacity = repair_or_homeostasis_capacity
        apoptosis_rate = clamp((1.0 - survival_signal) * 0.65 + functional_loss_score * 0.25)
        proliferation_rate = proliferation_signal
        stress_level = stress_signal
        genomic_instability = clamp(pathway_disruption_score * 0.55 + functional_loss_score * 0.35)
        inflammatory_signal = clamp(stress_signal * 0.50 + pathway_disruption_score * 0.35)
        secretion_signal = clamp(inflammatory_signal * 0.55 + stress_signal * 0.30)

        explanation = (
            f"Cell phenotype mapped from generic pathway output for {gene} via "
            "pathway_disruption_score, functional_loss_score, stress/survival/proliferation signals."
        )
        mapping_mode = "generic_pathway_traits"

    survival_advantage = clamp(proliferation_rate * 0.42 + (1.0 - apoptosis_rate) * 0.33 + stress_level * 0.15 + (1.0 - repair_capacity) * 0.10)
    vulnerability = clamp(apoptosis_rate * 0.35 + (1.0 - stress_level) * 0.20 + repair_capacity * 0.25 + (1.0 - proliferation_rate) * 0.20)
    overall_cell_state_risk = clamp(
        proliferation_rate * 0.22
        + genomic_instability * 0.25
        + (1.0 - apoptosis_rate) * 0.18
        + (1.0 - repair_capacity) * 0.18
        + inflammatory_signal * 0.17
    )
    confidence_base = clamp(
        0.48
        + (0.12 if pathway.external_evidence_available else 0.0)
        + min(len(pathway.nodes), 8) * 0.025
        + min(len(pathway.changed_nodes), 6) * 0.015
    )
    cell_context = "tumor-like growth pressure" if "cancer" in f"{pathway.label} {pathway.description}".lower() else "affected cell behavior"
    trait_details = {
        "proliferation": _trait(
            "Proliferation",
            proliferation_rate,
            confidence_base,
            "computed_model: Cell simulator",
            f"Computed from pathway survival/proliferation output; higher values mean stronger {cell_context}.",
        ),
        "apoptosis": _trait(
            "Apoptosis/death response",
            apoptosis_rate,
            confidence_base,
            "computed_model: Cell simulator",
            "Computed from death-response pathway activity and stress; higher values mean altered cells are more likely to be removed.",
        ),
        "repair_capacity": _trait(
            "Repair/homeostasis capacity",
            repair_capacity,
            confidence_base,
            "computed_model: Cell simulator",
            "Computed from DNA repair or generic homeostasis pathway activity; lower values mean less ability to restore normal cell state.",
        ),
        "stress_response": _trait(
            "Stress response",
            stress_level,
            confidence_base,
            "computed_model: Cell simulator",
            "Computed from damage, pathway disruption, and reduced repair; higher values mean the cell is modeled as more stressed.",
        ),
        "inflammation_signal": _trait(
            "Inflammation signal",
            inflammatory_signal,
            confidence_base,
            "computed_model: Cell simulator",
            "Computed from stress and instability outputs; higher values mean stronger modeled inflammatory signaling.",
        ),
        "genomic_instability": _trait(
            "Genomic instability",
            genomic_instability,
            confidence_base,
            "computed_model: Cell simulator",
            "Computed from low repair, altered checkpoint behavior, and proliferation pressure.",
        ),
        "survival_advantage": _trait(
            "Survival advantage",
            survival_advantage,
            confidence_base,
            "computed_model: Cell simulator",
            "Computed from proliferation, low death response, stress tolerance, and reduced repair constraints.",
        ),
        "vulnerability": _trait(
            "Vulnerability",
            vulnerability,
            confidence_base,
            "computed_model: Cell simulator",
            "Computed from death response, preserved repair, lower stress, and lower proliferation; higher values mean more targetable or fragile cell behavior.",
        ),
        "overall_cell_state_risk": _trait(
            "Overall cell-state risk",
            overall_cell_state_risk,
            confidence_base,
            "computed_model: Cell simulator",
            "Integrated score combining proliferation, instability, survival, repair loss, and inflammatory signaling.",
        ),
    }

    return CellPhenotypeResult(
        proliferation_rate=round4(proliferation_rate),
        apoptosis_rate=round4(apoptosis_rate),
        repair_capacity=round4(repair_capacity),
        stress_level=round4(stress_level),
        inflammatory_signal=round4(inflammatory_signal),
        genomic_instability=round4(genomic_instability),
        secretion_signal=round4(secretion_signal),
        explanation=explanation,
        mapping_mode=mapping_mode,
        pathway_disruption_score=round4(pathway_disruption_score) if not has_p53_nodes else None,
        functional_loss_score=round4(functional_loss_score) if not has_p53_nodes else None,
        stress_signal=round4(stress_signal) if not has_p53_nodes else None,
        survival_signal=round4(survival_signal) if not has_p53_nodes else None,
        proliferation_signal=round4(proliferation_signal) if not has_p53_nodes else None,
        repair_or_homeostasis_capacity=round4(repair_or_homeostasis_capacity) if not has_p53_nodes else None,
        computed_from_gene=computed_from["gene"],
        computed_from_pathway=computed_from["pathway"],
        computed_from_protein_activity=computed_from["protein_activity"],
        provenance={
            "proliferation_rate": _prov("computed_model", "Cell simulator"),
            "apoptosis_rate": _prov("computed_model", "Cell simulator"),
            "repair_capacity": _prov("computed_model", "Cell simulator"),
            "genomic_instability": _prov("computed_model", "Cell simulator"),
            "overall_cell_state_risk": _prov("computed_model", "Cell simulator"),
        },
        trait_details=trait_details,
    )
