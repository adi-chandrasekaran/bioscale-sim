from __future__ import annotations

from app.models import CellPhenotypeResult, EcosystemResult, PopulationResult, SimulationRequest
from app.services.utils import clamp, round4


def simulate_ecosystem(cell: CellPhenotypeResult, population: PopulationResult, req: SimulationRequest) -> EcosystemResult:
    final_fraction = population.final_mutated_fraction
    immune_clearance = clamp(req.immune_pressure * (1.0 - cell.secretion_signal * 0.45) * (1.0 - final_fraction * 0.25))
    inflammation = clamp(cell.inflammatory_signal * 0.65 + final_fraction * 0.35)
    nutrient_stress = clamp((1.0 - req.nutrient_level) * 0.55 + final_fraction * 0.45)
    tumor_like_burden = clamp(final_fraction * 0.65 + population.clonal_expansion_score * 0.35)
    ecosystem_risk = clamp(
        tumor_like_burden * 0.38
        + (1.0 - immune_clearance) * 0.22
        + inflammation * 0.22
        + nutrient_stress * 0.18
    )

    explanation = (
        "The ecosystem layer places the simulated cell population into a larger biological environment. Immune pressure, "
        "nutrient availability, inflammation, and mutated-cell burden are combined to estimate whether the ecosystem "
        "looks controlled or disease-promoting. This is intentionally simplified but shows how population outputs can "
        "be connected to tissue-environment variables."
    )

    return EcosystemResult(
        tumor_like_burden=round4(tumor_like_burden),
        immune_clearance=round4(immune_clearance),
        inflammation=round4(inflammation),
        nutrient_stress=round4(nutrient_stress),
        ecosystem_risk_score=round4(ecosystem_risk),
        explanation=explanation,
        computed_from_gene=cell.computed_from_gene,
        computed_from_pathway=cell.computed_from_pathway,
        computed_from_protein_activity=cell.computed_from_protein_activity,
    )
