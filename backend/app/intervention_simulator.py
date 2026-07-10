from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.services.intervention_evidence_service import fetch_intervention_evidence
from app.services.utils import clamp, round4


InterventionType = Literal[
    "Drug", "Gene therapy", "CRISPR", "Immune therapy", "Lifestyle", "Environmental"
]
DeliveryMode = Literal["oral", "IV", "local", "gene delivery", "cell therapy", "lifestyle/environmental", "unknown/none"]
Timing = Literal["early", "mid", "late", "continuous", "pulse"]


class InterventionRequest(BaseModel):
    disease: str
    gene: str = ""
    mutation: str = ""
    disease_category: str = ""
    symptoms: list[str] = Field(default_factory=list)
    intervention_type: InterventionType = "Drug"
    drug_name: Optional[str] = None
    selected_drug: Optional[dict[str, Any]] = None
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    target: str
    delivery_mode: DeliveryMode = "unknown/none"
    timing: Timing = "continuous"
    duration_cycles: int = Field(default=3, ge=1, le=52)
    specificity: float = Field(default=0.7, ge=0.0, le=1.0)
    toxicity_cost: float = Field(default=0.18, ge=0.0, le=1.0)
    resistance_pressure: float = Field(default=0.25, ge=0.0, le=1.0)
    combination_partner: str = "none"
    adherence_exposure: float = Field(default=0.85, ge=0.0, le=1.0)
    tissue_penetration: float = Field(default=0.72, ge=0.0, le=1.0)
    baseline_severity: float = Field(default=0.5, ge=0.0, le=1.0)
    alpha_fold_context: dict[str, Any] = Field(default_factory=dict)
    patient_context: dict[str, Any] = Field(default_factory=dict)
    intervention_scenario: dict[str, Any] = Field(default_factory=dict)
    baseline_mutated_fraction: float = Field(default=0.35, ge=0.0, le=1.0)
    baseline_ecosystem_risk: float = Field(default=0.5, ge=0.0, le=1.0)
    proliferation: float = Field(default=0.5, ge=0.0, le=1.0)
    apoptosis: float = Field(default=0.45, ge=0.0, le=1.0)
    repair_capacity: float = Field(default=0.5, ge=0.0, le=1.0)
    immune_clearance: float = Field(default=0.5, ge=0.0, le=1.0)
    inflammation: float = Field(default=0.45, ge=0.0, le=1.0)
    stress_response: float = Field(default=0.45, ge=0.0, le=1.0)
    pathway_activity: float = Field(default=0.5, ge=0.0, le=1.0)
    pathway_disruption: float = Field(default=0.5, ge=0.0, le=1.0)
    clone_fitness: float = Field(default=0.5, ge=0.0, le=1.0)
    dominant_clone_fraction: float = Field(default=0.35, ge=0.0, le=1.0)
    normal_population_fraction: float = Field(default=0.65, ge=0.0, le=1.0)
    baseline_timeline: list[dict[str, Any]] = Field(default_factory=list)
    evolution_clones: list[dict[str, Any]] = Field(default_factory=list)


class InterventionResult(BaseModel):
    modified_biology: dict[str, float]
    comparison: dict[str, float]
    timeline: list[dict[str, float | int]]
    clone_response: list[dict[str, float | str]]
    before_after_metrics: list[dict[str, Any]]
    mechanism_graph: dict[str, Any]
    pathway_before_after: dict[str, Any]
    cell_before_after: dict[str, Any]
    clone_timeline_before_after: list[dict[str, Any]]
    ecosystem_before_after: dict[str, Any]
    evidence_summary: dict[str, Any]
    student_explanation: dict[str, Any]
    validation_needs: list[str]
    explanation: str
    report: str
    outcome: Literal["helped", "little effect", "resistance risk"]
    confidence: float
    provenance: str = "Deterministic research-grade intervention simulator"
    disclaimer: str = "Research simulation only — not treatment advice."


def _type_multiplier(kind: str) -> float:
    return {
        "Drug": 0.82,
        "Gene therapy": 0.74,
        "CRISPR": 0.88,
        "Immune therapy": 0.76,
        "Lifestyle": 0.42,
        "Environmental": 0.38,
    }.get(kind, 0.5)


def _timing_multiplier(timing: str) -> float:
    return {"early": 1.08, "mid": 1.0, "late": 0.78, "continuous": 1.04, "pulse": 0.86}.get(timing, 1.0)


def _route_multiplier(route: str) -> float:
    return {"oral": 0.82, "IV": 0.94, "local": 0.9, "gene delivery": 0.82, "cell therapy": 0.78, "lifestyle/environmental": 0.62, "unknown/none": 0.72}.get(route, 0.72)


def _metric(label: str, before: float, after: float, rule: str, provenance: str, explanation: str) -> dict[str, Any]:
    delta = round4(after - before)
    return {
        "label": label,
        "before": round4(before),
        "after": round4(after),
        "delta": delta,
        "direction": "increased" if delta > 0 else "decreased" if delta < 0 else "unchanged",
        "magnitude": round4(abs(delta)),
        "formula_rule": rule,
        "provenance": provenance,
        "explanation": explanation,
    }


def _body_model(req: InterventionRequest, before_risk: float, after_risk: float, inflammation_before: float, inflammation_after: float) -> dict[str, Any]:
    site = "affected tissue"
    text = req.disease.lower()
    if any(term in text for term in ["liver", "hepatic", "hepatitis"]):
        site = "liver"
    elif any(term in text for term in ["lung", "asthma", "respiratory"]):
        site = "lungs"
    elif any(term in text for term in ["breast"]):
        site = "breast tissue"
    elif any(term in text for term in ["colon", "bowel", "gastro"]):
        site = "intestine"
    elif any(term in text for term in ["heart", "coronary", "cardio"]):
        site = "heart"
    before = {
        "name": "Before intervention",
        "children": [
            {"name": site, "value": round4(before_risk), "type": "primary site", "description": f"Baseline modeled ecosystem risk in {site}."},
            {"name": "inflammation", "value": round4(inflammation_before), "type": "microenvironment", "description": "Baseline inflammatory pressure."},
            {"name": "immune clearance", "value": round4(req.immune_clearance), "type": "immune", "description": "Baseline immune clearance capacity."},
        ],
    }
    after = {
        "name": "After intervention",
        "children": [
            {"name": site, "value": round4(after_risk), "type": "primary site", "description": f"Post-intervention modeled ecosystem risk in {site}."},
            {"name": "inflammation", "value": round4(inflammation_after), "type": "microenvironment", "description": "Post-intervention inflammatory pressure."},
            {"name": "off-target cost", "value": round4(req.toxicity_cost * (1.0 - req.specificity)), "type": "tradeoff", "description": "Modeled biological cost from toxicity and low specificity."},
        ],
    }
    change = after_risk - before_risk
    return {
        "site": site,
        "before": before,
        "after": after,
        "status": "improved" if change < -0.03 else "worsened" if change > 0.03 else "little changed",
        "description": f"The anatomical ecosystem model compares {site} before and after intervention. Risk changed from {before_risk:.2f} to {after_risk:.2f}, so the modeled tissue state {('improved' if change < -0.03 else 'worsened' if change > 0.03 else 'changed only slightly')}.",
    }


def simulate_intervention(req: InterventionRequest) -> InterventionResult:
    drug = req.drug_name or (req.selected_drug or {}).get("name") or ""
    evidence = fetch_intervention_evidence(drug, req.gene, req.mutation) if drug else {
        "drug": "",
        "normalized_drug": "",
        "available": False,
        "source_summaries": [],
        "mechanism": "Non-drug or generic mechanism-based intervention.",
        "known_targets": [],
        "clinical_status": "not applicable",
        "evidence_level": "simulator assumption",
        "pharmacodynamics": {},
        "raw": {},
    }
    provenance = "ChEMBL/RxNorm/CIViC context" if evidence.get("known_targets") else "simulator assumption"
    target_match = 1.0 if req.target and (req.target == req.gene or req.target in evidence.get("known_targets", [])) else 0.72
    effective_exposure = clamp(req.strength * req.specificity * req.adherence_exposure * req.tissue_penetration * _route_multiplier(req.delivery_mode) * _timing_multiplier(req.timing) * _type_multiplier(req.intervention_type) * target_match)
    resistance_drag = clamp(req.resistance_pressure * (0.35 + req.clone_fitness * 0.35 + req.dominant_clone_fraction * 0.30))
    toxicity_drag = clamp(req.toxicity_cost * (1.0 - req.specificity) * (0.45 + req.baseline_severity * 0.35))
    net_effect = clamp(effective_exposure * (1.0 - resistance_drag * 0.55) - toxicity_drag * 0.45)

    target_activity = clamp(req.pathway_activity * (1.0 - net_effect * 0.55))
    pathway_disruption = clamp(req.pathway_disruption * (1.0 - net_effect * 0.48) + toxicity_drag * 0.12)
    proliferation = clamp(req.proliferation * (1.0 - net_effect * 0.58))
    apoptosis = clamp(req.apoptosis + (1.0 - req.apoptosis) * net_effect * 0.42)
    repair = clamp(req.repair_capacity + (1.0 - req.repair_capacity) * net_effect * (0.35 if req.intervention_type in {"Gene therapy", "Lifestyle", "Environmental"} else 0.18) - toxicity_drag * 0.10)
    inflammation = clamp(req.inflammation * (1.0 - net_effect * 0.30) + toxicity_drag * 0.22)
    stress_response = clamp(req.stress_response * (1.0 - net_effect * 0.24) + toxicity_drag * 0.30)
    immune = clamp(req.immune_clearance + (1.0 - req.immune_clearance) * net_effect * (0.62 if req.intervention_type == "Immune therapy" else 0.22) - toxicity_drag * 0.08)
    clone_fitness = clamp(req.clone_fitness * (1.0 - net_effect * 0.36) + resistance_drag * 0.28)
    affected_fraction = clamp(req.baseline_mutated_fraction * (1.0 - net_effect * 1.20) + resistance_drag * 0.12)
    ecosystem_risk = clamp(req.baseline_ecosystem_risk * (1.0 - net_effect * 0.75) + toxicity_drag * 0.20 + resistance_drag * 0.08)
    off_target_cost = clamp(toxicity_drag + (1.0 - req.specificity) * 0.22)
    uncertainty = clamp(0.72 - (0.18 if evidence.get("available") else 0.0) + req.resistance_pressure * 0.12 + (1.0 - req.specificity) * 0.10)
    confidence = clamp(1.0 - uncertainty + (0.08 if req.baseline_timeline else 0.0) + (0.06 if req.evolution_clones else 0.0))

    pressure = clamp((req.proliferation - proliferation) * 0.22 + (apoptosis - req.apoptosis) * 0.18 + (immune - req.immune_clearance) * 0.18 + (req.pathway_disruption - pathway_disruption) * 0.18 + (req.baseline_ecosystem_risk - ecosystem_risk) * 0.24)
    percent_change = 0.0 if req.baseline_mutated_fraction == 0 else (affected_fraction - req.baseline_mutated_fraction) / req.baseline_mutated_fraction * 100.0

    timeline: list[dict[str, float | int]] = []
    source = req.baseline_timeline or [{"step": step, "mutated_fraction": req.baseline_mutated_fraction} for step in range(0, 61, 10)]
    max_step = max((int(point.get("step", 0)) for point in source), default=1) or 1
    for point in source[::max(1, len(source) // 36)]:
        step = int(point.get("step", 0))
        before = float(point.get("mutated_fraction", req.baseline_mutated_fraction))
        progress = step / max_step
        effect_at_step = net_effect * progress if req.timing != "early" else net_effect * min(1.0, progress + 0.25)
        after = clamp(before * (1.0 - effect_at_step * 1.20) + resistance_drag * 0.05 * progress)
        timeline.append({
            "step": step,
            "before": round4(before),
            "after": round4(after),
            "affected_population": round4(after),
            "normal_population": round4(clamp(1.0 - after)),
            "immune_clearance": round4(clamp(req.immune_clearance + (immune - req.immune_clearance) * progress)),
            "inflammation": round4(clamp(req.inflammation + (inflammation - req.inflammation) * progress)),
            "dominant_clone_fraction": round4(clamp(req.dominant_clone_fraction + (clone_fitness - req.clone_fitness) * 0.5 * progress)),
            "pathway_disruption": round4(clamp(req.pathway_disruption + (pathway_disruption - req.pathway_disruption) * progress)),
            "ecosystem_risk": round4(clamp(req.baseline_ecosystem_risk + (ecosystem_risk - req.baseline_ecosystem_risk) * progress)),
        })

    clone_response = []
    resistance = resistance_drag > 0.28
    for clone in req.evolution_clones:
        fitness = float(clone.get("fitness_score", 0.5))
        evasion = float(clone.get("immune_evasion", 0.0))
        response = clamp(net_effect * (1.0 - evasion * 0.42) - max(0.0, fitness - 0.68) * 0.35 - req.resistance_pressure * 0.12)
        resistance = resistance or response < net_effect * 0.35
        clone_response.append({"clone": str(clone.get("clone_name") or clone.get("name") or "Clone"), "suppression": round4(response), "fitness_after": round4(clamp(fitness - response * 0.25 + req.resistance_pressure * 0.08))})

    before_after = [
        _metric("Target activity", req.pathway_activity, target_activity, "pathway_activity * (1 - net_effect * 0.55)", provenance, f"{req.target} activity is reduced according to exposure, specificity, tissue penetration, and timing."),
        _metric("Pathway disruption", req.pathway_disruption, pathway_disruption, "pathway_disruption * (1 - net_effect * 0.48) + toxicity_drag * 0.12", provenance, "Pathway disruption falls when target modulation works, but biological cost can add residual disruption."),
        _metric("Proliferation", req.proliferation, proliferation, "proliferation * (1 - net_effect * 0.58)", "computed model", "Lower proliferation means the modeled affected population divides less."),
        _metric("Apoptosis/death response", req.apoptosis, apoptosis, "apoptosis + remaining_apoptosis * net_effect * 0.42", "computed model", "Higher apoptosis/death response means more affected cells are removed in the model."),
        _metric("Repair/homeostasis", req.repair_capacity, repair, "repair + remaining_repair * intervention_modifier - toxicity", "computed model", "Repair/homeostasis can improve for restoration interventions and fall with off-target cost."),
        _metric("Inflammatory signaling", req.inflammation, inflammation, "inflammation * (1 - net_effect * 0.30) + toxicity_drag * 0.22", "computed model", "Inflammation decreases with effective intervention but can rise with biological cost."),
        _metric("Stress response", req.stress_response, stress_response, "stress * (1 - net_effect * 0.24) + toxicity_drag * 0.30", "computed model", "Stress response tracks intervention benefit and off-target burden."),
        _metric("Immune clearance", req.immune_clearance, immune, "immune + remaining_immune * net_effect * type_modifier - toxicity", "computed model", "Immune clearance changes based on intervention type and cost."),
        _metric("Clone fitness", req.clone_fitness, clone_fitness, "clone_fitness * (1 - net_effect * 0.36) + resistance_drag * 0.28", "computed model", "Resistance pressure can preserve or increase relative clone fitness."),
        _metric("Affected population fraction", req.baseline_mutated_fraction, affected_fraction, "baseline_fraction * (1 - net_effect * 1.20) + resistance_drag * 0.12", "computed model", "Affected fraction is the modeled disease-like population burden."),
        _metric("Tissue/ecosystem risk", req.baseline_ecosystem_risk, ecosystem_risk, "ecosystem_risk * (1 - net_effect * 0.75) + toxicity/resistance", "computed model", "Ecosystem risk combines affected population, inflammation, immune state, and biological tradeoffs."),
        _metric("Off-target biological cost", 0.0, off_target_cost, "toxicity_cost * (1 - specificity) adjusted by severity", "simulator assumption", "Off-target cost rises with toxicity and low selectivity."),
        _metric("Uncertainty", 0.5, uncertainty, "base uncertainty adjusted by missing evidence, specificity, and resistance", "computed model", "Uncertainty remains high when evidence is missing or failure modes are strong."),
    ]

    mechanism_graph = {
        "nodes": [
            {"id": "intervention", "label": drug or req.intervention_type, "type": req.intervention_type, "value": req.strength, "source": provenance, "description": evidence.get("mechanism")},
            {"id": "target", "label": req.target, "type": "target", "value": target_activity, "source": provenance, "description": "Selected target from current context or drug evidence."},
            {"id": "pathway", "label": "Pathway modulation", "type": "pathway", "value": pathway_disruption, "source": "computed model", "description": "Pathway disruption after intervention."},
            {"id": "cell", "label": "Cell state", "type": "cell phenotype", "value": proliferation, "source": "computed model", "description": "Proliferation, apoptosis, repair, and stress response."},
            {"id": "clone", "label": "Clone/population", "type": "population", "value": affected_fraction, "source": "computed model", "description": "Affected fraction and clone fitness."},
            {"id": "ecosystem", "label": "Tissue ecosystem", "type": "ecosystem", "value": ecosystem_risk, "source": "computed model", "description": "Tissue risk after tradeoffs."},
        ],
        "links": [
            {"source": "intervention", "target": "target", "relation": "acts on", "weight": effective_exposure},
            {"source": "target", "target": "pathway", "relation": "modulates", "weight": net_effect},
            {"source": "pathway", "target": "cell", "relation": "changes", "weight": pressure},
            {"source": "cell", "target": "clone", "relation": "selects", "weight": 1.0 - resistance_drag},
            {"source": "clone", "target": "ecosystem", "relation": "alters", "weight": ecosystem_risk},
        ],
    }
    pathway_before_after = {"before": {"activity": round4(req.pathway_activity), "disruption": round4(req.pathway_disruption)}, "after": {"activity": round4(target_activity), "disruption": round4(pathway_disruption)}}
    cell_before_after = {"before": {"proliferation": req.proliferation, "apoptosis": req.apoptosis, "repair": req.repair_capacity, "immune": req.immune_clearance, "inflammation": req.inflammation, "stress": req.stress_response}, "after": {"proliferation": round4(proliferation), "apoptosis": round4(apoptosis), "repair": round4(repair), "immune": round4(immune), "inflammation": round4(inflammation), "stress": round4(stress_response)}}
    ecosystem_before_after = _body_model(req, req.baseline_ecosystem_risk, ecosystem_risk, req.inflammation, inflammation)

    outcome: Literal["helped", "little effect", "resistance risk"]
    if resistance:
        outcome = "resistance risk"
    elif pressure >= 0.06 and ecosystem_risk < req.baseline_ecosystem_risk:
        outcome = "helped"
    else:
        outcome = "little effect"
    explanation = (
        f"{drug or req.intervention_type} was modeled as a {req.intervention_type.lower()} acting on {req.target} with strength {req.strength:.2f}, "
        f"{req.delivery_mode} delivery, {req.timing} timing, specificity {req.specificity:.2f}, toxicity {req.toxicity_cost:.2f}, tissue penetration {req.tissue_penetration:.2f}, "
        f"and resistance pressure {req.resistance_pressure:.2f}. Effective exposure was {effective_exposure:.2f}; net effect after resistance/toxicity was {net_effect:.2f}."
    )
    report = (
        f"The model changes target activity from {req.pathway_activity:.2f} to {target_activity:.2f}, pathway disruption from {req.pathway_disruption:.2f} to {pathway_disruption:.2f}, "
        f"affected population fraction from {req.baseline_mutated_fraction:.2f} to {affected_fraction:.2f}, and ecosystem risk from {req.baseline_ecosystem_risk:.2f} to {ecosystem_risk:.2f}. "
        f"Modeled tradeoffs include off-target biological cost {off_target_cost:.2f} and resistance drag {resistance_drag:.2f}. "
        f"Validation would require dose-response data, pharmacodynamic measurements, tissue exposure, longitudinal biomarkers, and clone tracking."
    )
    return InterventionResult(
        modified_biology={
            "target_activity": round4(target_activity),
            "pathway_disruption": round4(pathway_disruption),
            "proliferation": round4(proliferation),
            "apoptosis": round4(apoptosis),
            "repair_capacity": round4(repair),
            "inflammatory_signal": round4(inflammation),
            "stress_response": round4(stress_response),
            "immune_clearance": round4(immune),
            "clone_fitness": round4(clone_fitness),
            "resistance_pressure": round4(resistance_drag),
            "affected_population_fraction": round4(affected_fraction),
            "ecosystem_risk": round4(ecosystem_risk),
            "off_target_biological_cost": round4(off_target_cost),
            "uncertainty": round4(uncertainty),
            "pathway_activity": round4(target_activity),
        },
        comparison={
            "baseline_mutated_fraction": round4(req.baseline_mutated_fraction),
            "post_intervention_mutated_fraction": round4(affected_fraction),
            "baseline_ecosystem_risk": round4(req.baseline_ecosystem_risk),
            "post_intervention_ecosystem_risk": round4(ecosystem_risk),
            "percent_change": round4(percent_change),
            "net_effect": round4(net_effect),
            "effective_exposure": round4(effective_exposure),
        },
        timeline=timeline,
        clone_response=clone_response,
        before_after_metrics=before_after,
        mechanism_graph=mechanism_graph,
        pathway_before_after=pathway_before_after,
        cell_before_after=cell_before_after,
        clone_timeline_before_after=timeline,
        ecosystem_before_after=ecosystem_before_after,
        evidence_summary={
            "drug": drug,
            "normalized_drug": evidence.get("normalized_drug"),
            "mechanism": evidence.get("mechanism"),
            "known_targets": evidence.get("known_targets", []),
            "clinical_status": evidence.get("clinical_status"),
            "evidence_level": evidence.get("evidence_level"),
            "pharmacodynamics": evidence.get("pharmacodynamics", {}),
            "sources": [source.get("source") for source in evidence.get("source_summaries", [])],
            "available": evidence.get("available", False),
            "raw": evidence.get("raw", {}),
        },
        student_explanation={
            "mechanism_of_action": "Mechanism of action means how an intervention is expected to change a biological target or pathway.",
            "pharmacodynamics": "IC50/EC50/Kd describe concentration-response properties when measured; this simulator strength is not a patient dose.",
            "specificity": "Specificity reduces off-target biological cost when high.",
            "toxicity": "Toxicity is modeled as biological cost that can worsen stress or ecosystem risk.",
            "resistance": "Resistance pressure captures failure modes such as clone escape or pathway bypass.",
            "tissue_penetration": "Tissue penetration controls how much of the abstract effect reaches the affected tissue.",
        },
        validation_needs=["verified drug-target evidence", "IC50/EC50/Kd or exposure-response data", "tissue penetration or bioavailability data", "longitudinal biomarkers", "clone/evolution tracking", "safety/toxicity measurements"],
        explanation=explanation,
        report=report,
        outcome=outcome,
        confidence=round4(confidence),
    )
