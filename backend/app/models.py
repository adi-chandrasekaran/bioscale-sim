from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    disease: str = Field(default="cancer", description="Disease key from the local knowledge base")
    gene: Optional[str] = Field(default="TP53", description="Gene symbol to simulate")
    mutation: Optional[str] = Field(default="p.R175H", description="Mutation notation for the selected gene")
    steps: int = Field(default=60, ge=5, le=300, description="Population/ecosystem simulation steps")
    initial_mutated_fraction: float = Field(default=0.02, ge=0.001, le=0.95)
    initial_population: int = Field(default=10000, ge=100, le=1000000)
    immune_pressure: float = Field(default=0.55, ge=0.0, le=1.0)
    nutrient_level: float = Field(default=0.75, ge=0.0, le=1.0)
    stochastic_seed: int = Field(default=7)


class CandidateGene(BaseModel):
    symbol: str
    score: float
    reasons: List[str]
    pathways: List[str]
    interactions: List[str]


class DiseaseDiscoveryResult(BaseModel):
    disease: str
    label: str
    affected_cell_context: str
    candidates: List[CandidateGene]


class MutationResult(BaseModel):
    gene: str
    mutation: str
    kind: str
    position: Optional[int]
    domain: str
    dna_rna_protein_explanation: str
    biological_interpretation: str
    activity_multiplier: float
    stability_multiplier: float
    binding_multiplier: float
    confidence: float


class ProteinEffectResult(BaseModel):
    gene: str
    protein_name: str
    protein_id: str
    mutation: str
    activity: float
    stability: float
    binding: float
    loss_of_function_score: float
    affected_domains: List[str]
    explanation: str


class PathwayNodeState(BaseModel):
    id: str
    type: str
    baseline: float
    activity: float
    delta: float


class PathwayEdge(BaseModel):
    source: str
    target: str
    relation: str
    weight: float


class PathwayResult(BaseModel):
    pathway_id: str
    label: str
    description: str
    nodes: List[PathwayNodeState]
    edges: List[PathwayEdge]
    disrupted_processes: List[str]
    explanation: str


class CellPhenotypeResult(BaseModel):
    proliferation_rate: float
    apoptosis_rate: float
    repair_capacity: float
    stress_level: float
    inflammatory_signal: float
    genomic_instability: float
    secretion_signal: float
    explanation: str


class PopulationPoint(BaseModel):
    step: int
    normal_cells: int
    mutated_cells: int
    mutated_fraction: float


class PopulationResult(BaseModel):
    trajectory: List[PopulationPoint]
    final_mutated_fraction: float
    clonal_expansion_score: float
    explanation: str


class EcosystemResult(BaseModel):
    tumor_like_burden: float
    immune_clearance: float
    inflammation: float
    nutrient_stress: float
    ecosystem_risk_score: float
    explanation: str


class SimulationResult(BaseModel):
    request: SimulationRequest
    disease_discovery: DiseaseDiscoveryResult
    selected_candidate: CandidateGene
    mutation_result: MutationResult
    protein_effect: ProteinEffectResult
    pathway_result: PathwayResult
    cell_phenotype: CellPhenotypeResult
    population_result: PopulationResult
    ecosystem_result: EcosystemResult
    research_summary: str
    citations: List[Dict[str, Any]] = []
