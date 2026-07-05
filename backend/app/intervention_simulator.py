from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.utils import clamp, round4


InterventionType = Literal[
    "Growth inhibitor", "Apoptosis activator", "Immune booster", "Repair enhancer", "Generic targeted therapy"
]


class InterventionRequest(BaseModel):
    disease: str
    gene: str
    mutation: str
    intervention_type: InterventionType
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    target: str
    baseline_mutated_fraction: float = Field(ge=0.0, le=1.0)
    baseline_ecosystem_risk: float = Field(ge=0.0, le=1.0)
    proliferation: float = Field(ge=0.0, le=1.0)
    apoptosis: float = Field(ge=0.0, le=1.0)
    repair_capacity: float = Field(ge=0.0, le=1.0)
    immune_clearance: float = Field(ge=0.0, le=1.0)
    baseline_timeline: list[dict[str, Any]] = Field(default_factory=list)
    evolution_clones: list[dict[str, Any]] = Field(default_factory=list)


class InterventionResult(BaseModel):
    modified_biology: dict[str, float]
    comparison: dict[str, float]
    timeline: list[dict[str, float | int]]
    clone_response: list[dict[str, float | str]]
    explanation: str
    report: str
    outcome: Literal["helped", "little effect", "resistance risk"]
    disclaimer: str = "Simplified research simulation, not treatment advice."


def simulate_intervention(req: InterventionRequest) -> InterventionResult:
    effect = req.strength
    proliferation, apoptosis = req.proliferation, req.apoptosis
    repair, immune = req.repair_capacity, req.immune_clearance
    if req.intervention_type == "Growth inhibitor":
        proliferation = clamp(proliferation * (1.0 - 0.72 * effect))
    elif req.intervention_type == "Apoptosis activator":
        apoptosis = clamp(apoptosis + (1.0 - apoptosis) * 0.72 * effect)
    elif req.intervention_type == "Immune booster":
        immune = clamp(immune + (1.0 - immune) * 0.68 * effect)
    elif req.intervention_type == "Repair enhancer":
        repair = clamp(repair + (1.0 - repair) * 0.62 * effect)
    else:
        proliferation = clamp(proliferation * (1.0 - 0.42 * effect))
        apoptosis = clamp(apoptosis + (1.0 - apoptosis) * 0.30 * effect)
        immune = clamp(immune + (1.0 - immune) * 0.24 * effect)

    pressure = clamp((req.proliferation - proliferation) * 0.40 + (apoptosis - req.apoptosis) * 0.28
                     + (immune - req.immune_clearance) * 0.22 + (repair - req.repair_capacity) * 0.10)
    post_fraction = clamp(req.baseline_mutated_fraction * (1.0 - pressure * 1.35))
    post_risk = clamp(req.baseline_ecosystem_risk * (1.0 - pressure) - (immune - req.immune_clearance) * 0.16)
    percent_change = 0.0 if req.baseline_mutated_fraction == 0 else (
        (post_fraction - req.baseline_mutated_fraction) / req.baseline_mutated_fraction * 100.0
    )

    timeline: list[dict[str, float | int]] = []
    source = req.baseline_timeline or [{"step": step, "mutated_fraction": req.baseline_mutated_fraction} for step in range(0, 61, 10)]
    max_step = max((int(point.get("step", 0)) for point in source), default=1) or 1
    for point in source[::max(1, len(source) // 30)]:
        step = int(point.get("step", 0))
        before = float(point.get("mutated_fraction", req.baseline_mutated_fraction))
        progress = step / max_step
        after = clamp(before * (1.0 - pressure * 1.35 * progress))
        timeline.append({"step": step, "before": round4(before), "after": round4(after)})

    clone_response = []
    resistance = False
    for clone in req.evolution_clones:
        fitness = float(clone.get("fitness_score", 0.5))
        evasion = float(clone.get("immune_evasion", 0.0))
        response = clamp(pressure * (1.0 - evasion * 0.45) - max(0.0, fitness - 0.72) * 0.35)
        resistance = resistance or response < pressure * 0.45
        clone_response.append({"clone": str(clone.get("name", "Clone")), "suppression": round4(response)})

    outcome: Literal["helped", "little effect", "resistance risk"]
    if resistance and req.evolution_clones:
        outcome = "resistance risk"
    elif pressure >= 0.08:
        outcome = "helped"
    else:
        outcome = "little effect"
    explanation = (
        f"This {req.intervention_type.lower()} changes the modeled biology at {req.target}. "
        f"The combined effect changes mutated-cell expansion by {percent_change:.1f}%."
    )
    report = (
        f"The intervention {outcome}. Post-intervention mutated fraction is {post_fraction:.2f} and ecosystem risk is "
        f"{post_risk:.2f}." + (" A fitter clone may be comparatively resistant." if resistance else "")
    )
    return InterventionResult(
        modified_biology={
            "proliferation": round4(proliferation), "apoptosis": round4(apoptosis),
            "repair_capacity": round4(repair), "immune_clearance": round4(immune),
            "ecosystem_risk": round4(post_risk),
        },
        comparison={
            "baseline_mutated_fraction": round4(req.baseline_mutated_fraction),
            "post_intervention_mutated_fraction": round4(post_fraction),
            "baseline_ecosystem_risk": round4(req.baseline_ecosystem_risk),
            "post_intervention_ecosystem_risk": round4(post_risk),
            "percent_change": round4(percent_change),
        },
        timeline=timeline,
        clone_response=clone_response,
        explanation=explanation,
        report=report,
        outcome=outcome,
    )
