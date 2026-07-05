from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from app.services.utils import clamp, round4


class EvolutionRequest(BaseModel):
    disease: str
    gene: str
    mutation: str
    steps: int = Field(default=60, ge=5, le=300)
    initial_population: int = Field(default=10000, ge=100, le=1000000)
    starting_mutated_fraction: float = Field(default=0.02, ge=0.001, le=0.95)
    mutation_rate: float = Field(default=0.04, ge=0.0, le=1.0)
    immune_pressure: float = Field(default=0.55, ge=0.0, le=1.0)
    nutrient_level: float = Field(default=0.75, ge=0.0, le=1.0)
    stress_level: float = Field(default=0.35, ge=0.0, le=1.0)
    protein_activity: float = Field(default=0.5, ge=0.0, le=1.0)
    protein_stability: float = Field(default=0.5, ge=0.0, le=1.0)
    repair_capacity: float = Field(default=0.5, ge=0.0, le=1.0)


class CloneState(BaseModel):
    name: str
    parent: str | None
    mutations: List[str]
    growth_rate: float
    death_rate: float
    repair_ability: float
    stress_resistance: float
    immune_evasion: float
    fitness_score: float


class CloneTimelinePoint(BaseModel):
    step: int
    clone_a: float
    clone_b: float
    clone_c: float


class EvolutionSummary(BaseModel):
    dominant_clone: str
    final_clone_fractions: dict[str, float]
    diversity_score: float
    clonal_expansion: bool
    explanation: str


class EvolutionResult(BaseModel):
    clones: List[CloneState]
    timeline: List[CloneTimelinePoint]
    tree: dict[str, List[str]]
    summary: EvolutionSummary
    disclaimer: str = "Simplified research simulation, not a clinical prediction."


def _clone(
    name: str,
    parent: str | None,
    mutations: List[str],
    activity: float,
    repair: float,
    immune: float,
    nutrients: float,
    stress: float,
    adaptation: float,
) -> CloneState:
    growth = clamp(0.18 + 0.38 * activity + 0.22 * nutrients + adaptation)
    death = clamp(0.12 + 0.30 * immune + 0.18 * stress - adaptation * 0.35)
    repair_ability = clamp(repair - adaptation * 0.18)
    stress_resistance = clamp(0.28 + repair * 0.24 + adaptation * 1.8)
    immune_evasion = clamp(0.16 + (1.0 - activity) * 0.18 + adaptation * 1.5)
    fitness = clamp(
        0.46 * growth
        + 0.18 * stress_resistance
        + 0.18 * immune_evasion
        + 0.10 * repair_ability
        + 0.08 * (1.0 - death)
    )
    return CloneState(
        name=name,
        parent=parent,
        mutations=mutations,
        growth_rate=round4(growth),
        death_rate=round4(death),
        repair_ability=round4(repair_ability),
        stress_resistance=round4(stress_resistance),
        immune_evasion=round4(immune_evasion),
        fitness_score=round4(fitness),
    )


def simulate_evolution(req: EvolutionRequest) -> EvolutionResult:
    adaptation = req.mutation_rate * (0.08 + req.stress_level * 0.12)
    clones = [
        _clone("Clone A", None, [f"{req.gene} {req.mutation}"], req.protein_activity, req.repair_capacity,
               req.immune_pressure, req.nutrient_level, req.stress_level, 0.0),
        _clone("Clone B", "Clone A", [f"{req.gene} {req.mutation}", "stress-adaptation event"],
               clamp(req.protein_activity + adaptation), req.repair_capacity, req.immune_pressure,
               req.nutrient_level, req.stress_level, adaptation),
        _clone("Clone C", "Clone A", [f"{req.gene} {req.mutation}", "immune-evasion event"],
               clamp(req.protein_activity + adaptation * 0.6), req.repair_capacity, req.immune_pressure,
               req.nutrient_level, req.stress_level, adaptation * 1.2),
    ]

    populations = [req.initial_population * req.starting_mutated_fraction, 0.0, 0.0]
    timeline: List[CloneTimelinePoint] = []
    sample_every = max(1, req.steps // 30)
    for step in range(req.steps + 1):
        total = max(sum(populations), 1.0)
        fractions = [value / total for value in populations]
        if step % sample_every == 0 or step == req.steps:
            timeline.append(CloneTimelinePoint(
                step=step,
                clone_a=round4(fractions[0]),
                clone_b=round4(fractions[1]),
                clone_c=round4(fractions[2]),
            ))
        if step == req.steps:
            break
        emergence = populations[0] * req.mutation_rate * 0.006
        populations[0] = max(0.0, populations[0] * (1.0 + (clones[0].fitness_score - 0.45) * 0.045) - emergence * 2)
        populations[1] = max(0.0, populations[1] * (1.0 + (clones[1].fitness_score - 0.45) * 0.045) + emergence)
        populations[2] = max(0.0, populations[2] * (1.0 + (clones[2].fitness_score - 0.45) * 0.045) + emergence)

    final = timeline[-1]
    final_fractions = {"Clone A": final.clone_a, "Clone B": final.clone_b, "Clone C": final.clone_c}
    dominant = max(final_fractions, key=final_fractions.get)
    diversity = round4(clamp(1.0 - max(final_fractions.values())))
    expanded = sum(populations) > req.initial_population * req.starting_mutated_fraction * 1.05
    explanation = (
        f"{dominant} became dominant because its modeled fitness best matched the current immune, nutrient, and stress "
        f"conditions. {'The mutated population expanded.' if expanded else 'Selection pressure limited net expansion.'}"
    )
    return EvolutionResult(
        clones=clones,
        timeline=timeline,
        tree={"Clone A": ["Clone B", "Clone C"]},
        summary=EvolutionSummary(
            dominant_clone=dominant,
            final_clone_fractions=final_fractions,
            diversity_score=diversity,
            clonal_expansion=expanded,
            explanation=explanation,
        ),
    )
