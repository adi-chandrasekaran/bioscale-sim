from __future__ import annotations

from typing import Dict

from app.models import CellPhenotypeResult, PathwayResult
from app.services.utils import clamp, round4


def simulate_cell(pathway: PathwayResult) -> CellPhenotypeResult:
    nodes: Dict[str, float] = {node.id: node.activity for node in pathway.nodes}

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

    explanation = (
        "The cell layer converts pathway activity into phenotype variables. Low DNA repair and low cell-cycle arrest "
        "increase genomic instability. Low apoptosis lets damaged cells survive. High proliferation signal makes the "
        "cell more likely to divide. These variables become growth/death rules in the population simulator."
    )

    return CellPhenotypeResult(
        proliferation_rate=round4(proliferation_rate),
        apoptosis_rate=round4(apoptosis_rate),
        repair_capacity=round4(repair_capacity),
        stress_level=round4(stress_level),
        inflammatory_signal=round4(inflammatory_signal),
        genomic_instability=round4(genomic_instability),
        secretion_signal=round4(secretion_signal),
        explanation=explanation,
    )
