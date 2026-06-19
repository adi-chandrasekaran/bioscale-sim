from __future__ import annotations

import math
from typing import List

from app.models import CellPhenotypeResult, PopulationPoint, PopulationResult, SimulationRequest
from app.services.utils import clamp, round4


def simulate_population(cell: CellPhenotypeResult, req: SimulationRequest) -> PopulationResult:
    normal = int(req.initial_population * (1.0 - req.initial_mutated_fraction))
    mutated = max(1, int(req.initial_population * req.initial_mutated_fraction))
    carrying_capacity = req.initial_population * 12

    trajectory: List[PopulationPoint] = []

    # Mutated cells use phenotype-derived rules. Normal cells use conservative default rules.
    mutated_growth = 0.018 + cell.proliferation_rate * 0.060 + cell.genomic_instability * 0.020
    mutated_death = 0.012 + cell.apoptosis_rate * 0.030
    normal_growth = 0.030
    normal_death = 0.018

    # If apoptosis is low, mutated effective death decreases further.
    apoptosis_escape = clamp(1.0 - cell.apoptosis_rate)
    mutated_death *= 1.0 - (0.55 * apoptosis_escape)

    for step in range(req.steps + 1):
        total = max(normal + mutated, 1)
        trajectory.append(
            PopulationPoint(
                step=step,
                normal_cells=int(round(normal)),
                mutated_cells=int(round(mutated)),
                mutated_fraction=round4(mutated / total),
            )
        )

        crowding = total / carrying_capacity
        normal_next = normal + normal * (normal_growth * (1 - crowding) - normal_death)
        mutated_next = mutated + mutated * (mutated_growth * (1 - crowding) - mutated_death)

        # Keep numbers sane and nonnegative.
        normal = max(0, normal_next)
        mutated = max(0, mutated_next)

    final_fraction = trajectory[-1].mutated_fraction
    clonal_expansion_score = round4(clamp((final_fraction - req.initial_mutated_fraction) / max(1e-6, 1.0 - req.initial_mutated_fraction)))

    explanation = (
        "The population layer turns one-cell phenotype into many-cell dynamics. Mutated cells receive a growth rate, "
        "death rate, and apoptosis-escape modifier from the cell simulator. The model then tracks whether the mutated "
        "clone remains rare or expands over time."
    )

    return PopulationResult(
        trajectory=trajectory,
        final_mutated_fraction=round4(final_fraction),
        clonal_expansion_score=clonal_expansion_score,
        explanation=explanation,
        computed_from_gene=cell.computed_from_gene,
        computed_from_pathway=cell.computed_from_pathway,
        computed_from_protein_activity=cell.computed_from_protein_activity,
    )
