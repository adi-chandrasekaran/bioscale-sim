from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.utils import clamp, round4


def _round_percent(value: float) -> float:
    return round4(max(0.0, min(1.0, value)))


class EvolutionRequest(BaseModel):
    disease: str
    gene: str
    mutation: str
    disease_category: Optional[str] = None
    protein_effect: Dict[str, Any] = Field(default_factory=dict)
    alphafold_context: Dict[str, Any] = Field(default_factory=dict)
    pathway_graph: Dict[str, Any] = Field(default_factory=dict)
    pathway_node_activity: Dict[str, float] = Field(default_factory=dict)
    cell_phenotype: Dict[str, Any] = Field(default_factory=dict)
    population_state: Dict[str, Any] = Field(default_factory=dict)
    patient_context_optional: Dict[str, Any] = Field(default_factory=dict)
    steps: int = Field(default=60, ge=5, le=300)
    max_clone_count: int = Field(default=6, ge=3, le=20)
    initial_population: int = Field(default=10000, ge=100, le=1000000)
    starting_affected_fraction: Optional[float] = Field(default=None, ge=0.001, le=0.95)
    starting_mutated_fraction: float = Field(default=0.02, ge=0.001, le=0.95)
    mutation_rate: float = Field(default=0.04, ge=0.0, le=1.0)
    immune_pressure: float = Field(default=0.55, ge=0.0, le=1.0)
    nutrient_level: float = Field(default=0.75, ge=0.0, le=1.0)
    stress_level: float = Field(default=0.35, ge=0.0, le=1.0)
    dna_damage_pressure: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    protein_activity: float = Field(default=0.5, ge=0.0, le=1.0)
    protein_stability: float = Field(default=0.5, ge=0.0, le=1.0)
    repair_capacity: float = Field(default=0.5, ge=0.0, le=1.0)


class CloneState(BaseModel):
    clone_id: str
    clone_name: str
    parent_clone_id: Optional[str] = None
    generation_order: int
    generation_step: int
    inherited_mutations: List[str]
    new_mutation_or_development: str
    evidence_basis: str
    database_sources_used: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    growth_rate: float
    death_rate: float
    repair_capacity: float
    immune_evasion: float
    stress_resistance: float
    nutrient_efficiency: float
    pathway_disruption: float
    fitness_score: float
    starting_share: float
    final_share: float = 0.0
    peak_share: float = 0.0
    whether_it_expanded: bool = False
    whether_it_declined: bool = False
    why_it_emerged: str
    why_it_expanded_or_declined: str = ""
    biological_interpretation: str
    confidence_score: float
    provenance_labels: List[str] = Field(default_factory=list)
    # Backwards-compatible fields used by the existing frontend.
    name: str
    parent: Optional[str] = None
    mutations: List[str] = Field(default_factory=list)
    repair_ability: float


class CloneTimelinePoint(BaseModel):
    step: int
    clone_a: float = 0.0
    clone_b: float = 0.0
    clone_c: float = 0.0
    clone_fractions: Dict[str, float] = Field(default_factory=dict)
    clone_populations: Dict[str, int] = Field(default_factory=dict)
    major_events: List[str] = Field(default_factory=list)


class EvolutionSummary(BaseModel):
    dominant_clone: str
    final_clone_fractions: Dict[str, float]
    diversity_score: float
    clonal_expansion: bool
    explanation: str


class EvolutionResult(BaseModel):
    clones: List[CloneState]
    timeline: List[CloneTimelinePoint]
    tree: Dict[str, List[str]]
    clone_tree: Dict[str, Any] = Field(default_factory=dict)
    clone_composition: Dict[str, Any] = Field(default_factory=dict)
    final_composition: Dict[str, Any] = Field(default_factory=dict)
    major_events: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_summary: Dict[str, Any] = Field(default_factory=dict)
    model_assumptions: List[str] = Field(default_factory=list)
    uncertainty_summary: str
    student_explanation: str
    summary: EvolutionSummary
    confidence: float
    provenance: str = "Evidence-guided deterministic clone trajectory model"
    disclaimer: str = "These are evidence-guided simulated clone trajectories, not confirmed future clones."


DEVELOPMENT_LABELS = {
    "growth_advantage": "growth-advantage development",
    "apoptosis_escape": "apoptosis-escape development",
    "repair_loss": "repair-loss / genomic-instability development",
    "immune_evasion": "immune-evasion development",
    "stress_resistance": "stress-resistance development",
    "nutrient_efficiency": "nutrient-efficiency development",
    "pathway_bypass": "pathway-bypass development",
    "inflammatory_adaptation": "inflammatory-adaptation development",
}


def _is_cancer_context(req: EvolutionRequest) -> bool:
    text = f"{req.disease} {req.disease_category or ''}".lower()
    return any(term in text for term in ["cancer", "tumor", "tumour", "carcinoma", "sarcoma", "leukemia", "lymphoma", "melanoma"])


def _numeric(payload: Dict[str, Any], key: str, fallback: float) -> float:
    value = payload.get(key)
    return clamp(float(value)) if isinstance(value, (int, float)) else fallback


def _source_list(req: EvolutionRequest) -> List[str]:
    sources: List[str] = []
    if req.protein_effect.get("source") or req.protein_effect.get("protein_id"):
        sources.append("UniProt")
    if req.alphafold_context.get("alphafold_available"):
        sources.append("AlphaFold DB")
    if req.pathway_graph.get("source") or req.pathway_node_activity:
        sources.append("Reactome")
    if req.cell_phenotype:
        sources.append("BioScale cell phenotype model")
    if req.population_state:
        sources.append("BioScale population model")
    if _is_cancer_context(req):
        # These remain explicit stubs unless an upstream adapter returns evidence.
        if req.protein_effect.get("civic_evidence"):
            sources.append("CIViC")
        if req.protein_effect.get("cbioportal_evidence"):
            sources.append("cBioPortal")
        if req.protein_effect.get("gdc_evidence"):
            sources.append("GDC")
    return sources


def _development_scores(req: EvolutionRequest) -> Dict[str, float]:
    cell = req.cell_phenotype
    protein = req.protein_effect
    proliferation = _numeric(cell, "proliferation_rate", _numeric(cell, "proliferation", 0.5))
    apoptosis = _numeric(cell, "apoptosis_rate", _numeric(cell, "apoptosis", 0.45))
    repair = _numeric(cell, "repair_capacity", req.repair_capacity)
    instability = _numeric(cell, "genomic_instability", clamp(1.0 - repair))
    inflammation = _numeric(cell, "inflammatory_signal", 0.45)
    pathway_disruption = _numeric(cell, "pathway_disruption_score", _numeric(protein, "loss_of_function_score", 0.5))
    dna_damage = req.dna_damage_pressure if req.dna_damage_pressure is not None else clamp((1.0 - req.protein_stability) * 0.55 + (1.0 - repair) * 0.45)
    nutrient_stress = clamp(1.0 - req.nutrient_level)
    return {
        "growth_advantage": clamp(proliferation * 0.55 + req.nutrient_level * 0.25 + req.protein_activity * 0.20),
        "apoptosis_escape": clamp((1.0 - apoptosis) * 0.65 + pathway_disruption * 0.25 + proliferation * 0.10),
        "repair_loss": clamp(dna_damage * 0.42 + (1.0 - repair) * 0.38 + instability * 0.20),
        "immune_evasion": clamp(req.immune_pressure * 0.62 + inflammation * 0.18 + pathway_disruption * 0.20),
        "stress_resistance": clamp(req.stress_level * 0.58 + dna_damage * 0.22 + instability * 0.20),
        "nutrient_efficiency": clamp(nutrient_stress * 0.62 + proliferation * 0.23 + req.stress_level * 0.15),
        "pathway_bypass": clamp(pathway_disruption * 0.68 + (1.0 - req.protein_activity) * 0.22 + proliferation * 0.10),
        "inflammatory_adaptation": clamp(inflammation * 0.58 + req.immune_pressure * 0.20 + req.stress_level * 0.22),
    }


def _ordered_developments(req: EvolutionRequest) -> List[tuple[str, float]]:
    scores = _development_scores(req)
    preferred = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    # Keep deterministic variety after the highest-scoring pressures.
    return preferred


def _clone_name(index: int) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if index < len(letters):
        return f"Clone {letters[index]}"
    return f"Clone {index + 1}"


def _clone_id(index: int) -> str:
    letters = "abcdefghijklmnopqrstuvwxyz"
    if index < len(letters):
        return f"clone_{letters[index]}"
    return f"clone_{index + 1}"


def _confidence(req: EvolutionRequest, sources: List[str], generation_order: int) -> float:
    evidence = min(len([s for s in sources if not s.startswith("BioScale")]), 4) * 0.06
    model_context = 0.08 if req.cell_phenotype else 0.0
    pathway_context = 0.06 if req.pathway_graph or req.pathway_node_activity else 0.0
    return _round_percent(0.46 + evidence + model_context + pathway_context - generation_order * 0.015)


def _make_clone(req: EvolutionRequest, index: int, parent: Optional[CloneState], development_key: str, pressure_score: float, sources: List[str]) -> CloneState:
    name = _clone_name(index)
    clone_id = _clone_id(index)
    generation_step = 0 if index == 0 else max(1, round(req.steps * index / max(req.max_clone_count, 1)))
    inherited = [f"{req.gene} {req.mutation}"] if parent is None else list(parent.inherited_mutations)
    development = "founding selected mutation" if parent is None else DEVELOPMENT_LABELS[development_key]
    mutation_pressure = clamp(req.mutation_rate + pressure_score * 0.08)
    repair = _numeric(req.cell_phenotype, "repair_capacity", req.repair_capacity)
    pathway_disruption = _numeric(req.cell_phenotype, "pathway_disruption_score", _numeric(req.protein_effect, "loss_of_function_score", 0.5))
    growth = clamp(0.20 + req.protein_activity * 0.26 + req.nutrient_level * 0.20 + (pressure_score if development_key == "growth_advantage" else 0.0) * 0.24 + mutation_pressure * 0.16)
    death = clamp(0.48 - (pressure_score if development_key == "apoptosis_escape" else 0.0) * 0.18 + req.immune_pressure * 0.15 + req.stress_level * 0.10)
    repair_capacity = clamp(repair - (pressure_score if development_key == "repair_loss" else 0.0) * 0.28 - index * 0.01)
    immune_evasion = clamp(0.14 + (pressure_score if development_key == "immune_evasion" else req.immune_pressure * 0.30) + pathway_disruption * 0.12)
    stress_resistance = clamp(0.20 + req.stress_level * 0.32 + (pressure_score if development_key == "stress_resistance" else 0.0) * 0.38)
    nutrient_efficiency = clamp(0.22 + req.nutrient_level * 0.22 + (pressure_score if development_key == "nutrient_efficiency" else 0.0) * 0.42)
    if development_key == "pathway_bypass":
        pathway_disruption = clamp(pathway_disruption + pressure_score * 0.22)
    if development_key == "inflammatory_adaptation":
        stress_resistance = clamp(stress_resistance + pressure_score * 0.16)
        immune_evasion = clamp(immune_evasion + pressure_score * 0.12)
    fitness = clamp(
        growth * 0.28
        + (1.0 - death) * 0.20
        + immune_evasion * 0.16
        + stress_resistance * 0.13
        + nutrient_efficiency * 0.13
        + (1.0 - repair_capacity) * 0.05
        + pathway_disruption * 0.05
    )
    missing = []
    if not sources:
        missing.append("No direct database evidence found; clone generated by model logic from upstream pathway/cell-state outputs.")
    if _is_cancer_context(req):
        missing.extend(["Longitudinal sequencing", "Single-cell clone tracking", "Direct cBioPortal/GDC/CIViC recurrence support not available in this run"])
    else:
        missing.extend(["Longitudinal affected-tissue sequencing", "Single-cell lineage data"])
    why = (
        f"{name} {'is the founding clone initialized with' if parent is None else f'emerged from {parent.clone_name} at step {generation_step} after'} "
        f"{req.gene} {req.mutation}. "
        f"The selected development was {development} because the deterministic pressure score for this category was {pressure_score:.2f}."
    )
    interpretation = (
        f"{name} represents a simulated genetically related cell population, not a confirmed future clone. "
        f"It carries {', '.join(inherited)} and is modeled with fitness {fitness:.2f} under immune pressure {req.immune_pressure:.2f}, "
        f"nutrient level {req.nutrient_level:.2f}, stress {req.stress_level:.2f}, and pathway disruption {pathway_disruption:.2f}."
    )
    evidence_basis = (
        f"Database/context used: {', '.join(sources)}."
        if sources
        else "No direct database evidence found; this clone was generated by model logic from upstream pathway/cell-state outputs."
    )
    return CloneState(
        clone_id=clone_id,
        clone_name=name,
        parent_clone_id=parent.clone_id if parent else None,
        generation_order=index,
        generation_step=generation_step,
        inherited_mutations=inherited,
        new_mutation_or_development=development,
        evidence_basis=evidence_basis,
        database_sources_used=sources,
        missing_evidence=missing,
        growth_rate=round4(growth),
        death_rate=round4(death),
        repair_capacity=round4(repair_capacity),
        immune_evasion=round4(immune_evasion),
        stress_resistance=round4(stress_resistance),
        nutrient_efficiency=round4(nutrient_efficiency),
        pathway_disruption=round4(pathway_disruption),
        fitness_score=round4(fitness),
        starting_share=round4(req.starting_affected_fraction or req.starting_mutated_fraction) if parent is None else 0.0,
        why_it_emerged=why,
        biological_interpretation=interpretation,
        confidence_score=_confidence(req, sources, index),
        provenance_labels=sources or ["simulator_assumption"],
        name=name,
        parent=parent.clone_name if parent else None,
        mutations=inherited + ([development] if parent else []),
        repair_ability=round4(repair_capacity),
    )


def _event(step: int, event_type: str, clone_id: str, clone_name: str, description: str) -> Dict[str, Any]:
    return {
        "step": step,
        "event_type": event_type,
        "clone_id": clone_id,
        "clone_name": clone_name,
        "description": description,
    }


def _build_tree(clones: List[CloneState], final_fractions: Dict[str, float]) -> Dict[str, Any]:
    by_parent: Dict[Optional[str], List[CloneState]] = {}
    for clone in clones:
        by_parent.setdefault(clone.parent_clone_id, []).append(clone)

    def node(clone: CloneState) -> Dict[str, Any]:
        return {
            "id": clone.clone_id,
            "name": clone.clone_name,
            "type": clone.new_mutation_or_development,
            "value": final_fractions.get(clone.clone_name, 0.0),
            "description": clone.biological_interpretation,
            "final_share": clone.final_share,
            "peak_share": clone.peak_share,
            "generation_step": clone.generation_step,
            "fitness_score": clone.fitness_score,
            "details": clone.model_dump(),
            "children": [node(child) for child in sorted(by_parent.get(clone.clone_id, []), key=lambda item: item.generation_order)],
        }

    root = next((clone for clone in clones if clone.parent_clone_id is None), clones[0])
    return node(root)


def _simulate_populations(req: EvolutionRequest, clones: List[CloneState]) -> tuple[List[CloneTimelinePoint], List[Dict[str, Any]]]:
    starting_fraction = req.starting_affected_fraction or req.starting_mutated_fraction
    populations = {clone.clone_id: 0.0 for clone in clones}
    populations[clones[0].clone_id] = req.initial_population * starting_fraction
    sample_every = max(1, req.steps // 40)
    timeline: List[CloneTimelinePoint] = []
    events: List[Dict[str, Any]] = [_event(0, "founding_clone_initialized", clones[0].clone_id, clones[0].clone_name, f"{clones[0].clone_name} initialized with {req.gene} {req.mutation}.")]
    events_by_step: Dict[int, List[str]] = {0: [events[0]["description"]]}

    for clone in clones[1:]:
        description = f"{clone.clone_name} emerged from {clone.parent or 'founding clone'} with {clone.new_mutation_or_development}."
        events.append(_event(clone.generation_step, "clone_emerged", clone.clone_id, clone.clone_name, description))
        events_by_step.setdefault(clone.generation_step, []).append(description)

    for step in range(req.steps + 1):
        for clone in clones[1:]:
            if step == clone.generation_step:
                parent_pop = populations.get(clone.parent_clone_id or clones[0].clone_id, 0.0)
                seed = max(1.0, parent_pop * req.mutation_rate * (0.004 + clone.pathway_disruption * 0.002))
                populations[clone.clone_id] = max(populations[clone.clone_id], seed)
                populations[clone.parent_clone_id or clones[0].clone_id] = max(0.0, parent_pop - seed)

        total = max(sum(populations.values()), 1.0)
        fractions = {clone.clone_id: round4(populations[clone.clone_id] / total) for clone in clones}
        if step % sample_every == 0 or step == req.steps or step in events_by_step:
            timeline.append(CloneTimelinePoint(
                step=step,
                clone_a=fractions.get("clone_a", 0.0),
                clone_b=fractions.get("clone_b", 0.0),
                clone_c=fractions.get("clone_c", 0.0),
                clone_fractions={clone.clone_name: fractions[clone.clone_id] for clone in clones},
                clone_populations={clone.clone_name: int(round(populations[clone.clone_id])) for clone in clones},
                major_events=events_by_step.get(step, []),
            ))

        if step == req.steps:
            break

        for clone in clones:
            pop = populations[clone.clone_id]
            if pop <= 0:
                continue
            selection = (clone.fitness_score - 0.48) * 0.075
            pressure_loss = req.immune_pressure * (1.0 - clone.immune_evasion) * 0.012 + req.stress_level * (1.0 - clone.stress_resistance) * 0.008
            nutrient_bonus = clone.nutrient_efficiency * req.nutrient_level * 0.010
            populations[clone.clone_id] = max(0.0, pop * (1.0 + selection + nutrient_bonus - pressure_loss))

    final_point = timeline[-1]
    for clone in clones:
        values = [point.clone_fractions.get(clone.clone_name, 0.0) for point in timeline]
        clone.final_share = final_point.clone_fractions.get(clone.clone_name, 0.0)
        clone.peak_share = round4(max(values or [0.0]))
        clone.whether_it_expanded = clone.final_share > clone.starting_share + 0.005
        clone.whether_it_declined = clone.final_share < max(clone.starting_share, 0.001) - 0.005
        trend = "expanded" if clone.whether_it_expanded else "declined" if clone.whether_it_declined else "remained small or stable"
        clone.why_it_expanded_or_declined = (
            f"{clone.clone_name} {trend} because its fitness score ({clone.fitness_score:.2f}) was evaluated against immune pressure "
            f"{req.immune_pressure:.2f}, nutrient level {req.nutrient_level:.2f}, stress {req.stress_level:.2f}, repair capacity {clone.repair_capacity:.2f}, "
            f"and immune evasion {clone.immune_evasion:.2f}. Final share was {clone.final_share * 100:.1f}% and peak share was {clone.peak_share * 100:.1f}%."
        )
        if clone.parent_clone_id:
            event_type = "clone_expanded" if clone.whether_it_expanded else "clone_declined" if clone.whether_it_declined else "clone_remained_minor"
            events.append(_event(req.steps, event_type, clone.clone_id, clone.clone_name, clone.why_it_expanded_or_declined))
        if clone.parent_clone_id and req.immune_pressure > 0.65 and clone.immune_evasion < 0.45:
            events.append(_event(req.steps, "immune_pressure_selection", clone.clone_id, clone.clone_name, f"Immune pressure selected against {clone.clone_name} because immune evasion remained {clone.immune_evasion:.2f}."))
        if clone.parent_clone_id and req.nutrient_level < 0.45 and clone.nutrient_efficiency > 0.55:
            events.append(_event(req.steps, "nutrient_stress_selection", clone.clone_id, clone.clone_name, f"Nutrient stress favored {clone.clone_name} because nutrient efficiency reached {clone.nutrient_efficiency:.2f}."))

    dominant = max(clones, key=lambda clone: clone.final_share)
    description = f"{dominant.clone_name} became dominant with {dominant.final_share * 100:.1f}% final share."
    events.append(_event(req.steps, "dominant_clone", dominant.clone_id, dominant.clone_name, description))
    final_point.major_events.append(description)
    return timeline, events


def simulate_evolution(req: EvolutionRequest) -> EvolutionResult:
    sources = _source_list(req)
    developments = _ordered_developments(req)
    clones: List[CloneState] = []
    founding = _make_clone(req, 0, None, "growth_advantage", developments[0][1], sources)
    clones.append(founding)
    target_count = max(3, min(req.max_clone_count, 20))
    for index in range(1, target_count):
        key, score = developments[(index - 1) % len(developments)]
        parent = clones[0] if index <= 2 else max(clones[:index], key=lambda clone: clone.fitness_score + clone.final_share * 0.2)
        clones.append(_make_clone(req, index, parent, key, score, sources))

    timeline, events = _simulate_populations(req, clones)
    final_fractions = {clone.clone_name: clone.final_share for clone in clones}
    total_final = sum(final_fractions.values()) or 1.0
    final_fractions = {name: round4(value / total_final) for name, value in final_fractions.items()}
    for clone in clones:
        clone.final_share = final_fractions[clone.clone_name]

    dominant = max(final_fractions, key=final_fractions.get)
    diversity = round4(clamp(1.0 - max(final_fractions.values())))
    expanded = any(clone.whether_it_expanded for clone in clones)
    tree = {}
    for clone in clones:
        if clone.parent:
            tree.setdefault(clone.parent, []).append(clone.clone_name)
    clone_tree = _build_tree(clones, final_fractions)
    clone_composition = {
        "name": "Final clone composition",
        "type": "composition",
        "children": [
            {
                "id": clone.clone_id,
                "name": clone.clone_name,
                "type": clone.new_mutation_or_development,
                "value": final_fractions[clone.clone_name],
                "description": f"{clone.clone_name}: {final_fractions[clone.clone_name] * 100:.1f}% final share. {clone.why_it_expanded_or_declined}",
                "details": clone.model_dump(),
            }
            for clone in clones
        ],
    }
    evidence_summary = {
        "sources_used": sources,
        "database_evidence": [source for source in sources if not source.startswith("BioScale")],
        "simulator_context": [source for source in sources if source.startswith("BioScale")],
        "missing_evidence": sorted({item for clone in clones for item in clone.missing_evidence}),
    }
    assumptions = [
        "Clone trajectories are deterministic simulated hypotheses, not confirmed future clones.",
        "Additional clone emergence is estimated from mutation rate, genomic instability, pathway disruption, population size, and selection pressures.",
        "Fitness combines growth, death resistance, repair/homeostasis, immune evasion, stress resistance, nutrient efficiency, and pathway disruption.",
        "No clone is treated as real without longitudinal sequencing or single-cell lineage evidence.",
    ]
    uncertainty = (
        "These are evidence-guided simulated clone trajectories, not confirmed future clones. Validation would require longitudinal sequencing, "
        "single-cell sequencing, repeated affected-tissue samples, and disease-specific cohort data."
    )
    student = (
        f"The model starts with {clones[0].clone_name}, a founding clone carrying {req.gene} {req.mutation}. "
        f"It then creates child clones when the modeled mutation pressure, pathway disruption, repair loss, immune pressure, nutrient state, and stress state make emergence plausible. "
        f"{dominant} has the largest final share in this run, but this is a hypothesis generated from evidence and assumptions, not a prediction of what must happen."
    )
    return EvolutionResult(
        clones=clones,
        timeline=timeline,
        tree=tree,
        clone_tree=clone_tree,
        clone_composition=clone_composition,
        final_composition=clone_composition,
        major_events=events,
        evidence_summary=evidence_summary,
        model_assumptions=assumptions,
        uncertainty_summary=uncertainty,
        student_explanation=student,
        summary=EvolutionSummary(
            dominant_clone=dominant,
            final_clone_fractions=final_fractions,
            diversity_score=diversity,
            clonal_expansion=expanded,
            explanation=f"{dominant} became dominant because its modeled fitness best matched the current selection pressures. {uncertainty}",
        ),
        confidence=_confidence(req, sources, 0),
    )
