from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


ProvenanceCategory = Literal[
    "external_database",
    "local_curated",
    "simulator_assumption",
    "computed_model",
    "missing_evidence",
]


class ProvenanceEntry(BaseModel):
    category: ProvenanceCategory
    source: str
    detail: Optional[str] = None


class SearchResultItem(BaseModel):
    id: str
    label: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    synonyms: List[str] = Field(default_factory=list)
    normalized_mapping: Dict[str, Any] = Field(default_factory=dict)
    source: str = "Open Targets"
    meta: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    source: str
    available: bool
    results: List[SearchResultItem] = Field(default_factory=list)
    error: Optional[str] = None


class AIChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AIChatRequest(BaseModel):
    question: str = Field(min_length=1)
    history: List[AIChatTurn] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


class AIChatResponse(BaseModel):
    answer: str
    provider: str = "fallback"
    model: Optional[str] = None


class AIStatusResponse(BaseModel):
    configured: bool
    provider: str
    model: Optional[str] = None
    message: str


class SimulationRequest(BaseModel):
    disease_id: str = Field(default="EFO_0000311", description="Open Targets disease ID (EFO/MONDO)")
    disease_name: Optional[str] = Field(default="cancer", description="Human-readable disease label")
    gene: str = Field(default="TP53", description="Gene symbol")
    mutation: str = Field(default="p.R175H", description="Variant notation")
    pathway_id: Optional[str] = Field(default=None, description="Optional Reactome pathway stId")
    pathway_name: Optional[str] = Field(default=None, description="Optional Reactome pathway label")
    steps: int = Field(default=60, ge=5, le=300)
    initial_mutated_fraction: float = Field(default=0.02, ge=0.001, le=0.95)
    initial_population: int = Field(default=10000, ge=100, le=1000000)
    immune_pressure: float = Field(default=0.55, ge=0.0, le=1.0)
    nutrient_level: float = Field(default=0.75, ge=0.0, le=1.0)
    stochastic_seed: int = Field(default=7)
    use_external_evidence: bool = Field(default=True)
    # Legacy compatibility
    disease: Optional[str] = Field(default=None, description="Deprecated local disease key")


class CandidateGene(BaseModel):
    symbol: str
    score: float
    reasons: List[str]
    pathways: List[str] = Field(default_factory=list)
    interactions: List[str] = Field(default_factory=list)
    source: str = "Open Targets"
    summary: Optional[str] = None
    function_summary: Optional[str] = None
    provenance: Dict[str, ProvenanceEntry] = Field(default_factory=dict)


class DiseaseDiscoveryResult(BaseModel):
    disease: str
    disease_id: Optional[str] = None
    label: str
    affected_cell_context: str
    candidates: List[CandidateGene]
    summary: Optional[str] = None
    external_evidence_available: bool = False
    evidence_notice: Optional[str] = None
    provenance: Dict[str, ProvenanceEntry] = Field(default_factory=dict)
    raw_evidence: Dict[str, Any] = Field(default_factory=dict)


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
    amino_acid_change: Optional[str] = None
    clinvar_classification: Optional[str] = None
    phenotypes: List[str] = Field(default_factory=list)
    source: str = "ClinVar"
    summary: Optional[str] = None
    external_evidence_available: bool = False
    evidence_notice: Optional[str] = None
    provenance: Dict[str, ProvenanceEntry] = Field(default_factory=dict)
    raw_evidence: Dict[str, Any] = Field(default_factory=dict)


class ProteinEffectResult(BaseModel):
    gene: str
    protein_name: str
    protein_id: Optional[str] = None
    mutation: str
    activity: float
    stability: float
    binding: float
    loss_of_function_score: float
    affected_domains: List[str]
    explanation: str
    function_summary: Optional[str] = None
    mutation_location: Optional[str] = None
    domain_hit: Optional[str] = None
    structural_impact_placeholder: str = "AlphaFold structure context is checked when a UniProt accession is available."
    functional_impact_summary: Optional[str] = None
    source: str = "UniProt"
    summary: Optional[str] = None
    external_evidence_available: bool = False
    evidence_notice: Optional[str] = None
    provenance: Dict[str, ProvenanceEntry] = Field(default_factory=dict)
    raw_evidence: Dict[str, Any] = Field(default_factory=dict)


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
    selected_gene: Optional[str] = None
    selected_protein: Optional[str] = None
    selected_pathway_name: Optional[str] = None
    selected_pathway_source: Optional[str] = None
    selected_pathway_id: Optional[str] = None
    is_generic_fallback: bool = False
    node_activities: Dict[str, float] = Field(default_factory=dict)
    baseline_activities: Dict[str, float] = Field(default_factory=dict)
    changed_nodes: List[str] = Field(default_factory=list)
    reactome_pathways: List[Dict[str, Any]] = Field(default_factory=list)
    reactome_participants: List[Dict[str, Any]] = Field(default_factory=list)
    simulation_model_note: str = "Graph propagation uses simplified simulator assumptions."
    source: str = "Reactome + Simulator"
    summary: Optional[str] = None
    external_evidence_available: bool = False
    evidence_notice: Optional[str] = None
    provenance: Dict[str, ProvenanceEntry] = Field(default_factory=dict)
    raw_evidence: Dict[str, Any] = Field(default_factory=dict)
    computed_from_gene: Optional[str] = None
    computed_from_pathway: Optional[str] = None
    computed_from_protein_activity: Optional[str] = None


class CellPhenotypeResult(BaseModel):
    proliferation_rate: float
    apoptosis_rate: float
    repair_capacity: float
    stress_level: float
    inflammatory_signal: float
    genomic_instability: float
    secretion_signal: float
    explanation: str
    mapping_mode: str = "generic_pathway_traits"
    pathway_disruption_score: Optional[float] = None
    functional_loss_score: Optional[float] = None
    stress_signal: Optional[float] = None
    survival_signal: Optional[float] = None
    proliferation_signal: Optional[float] = None
    repair_or_homeostasis_capacity: Optional[float] = None
    computed_from_gene: Optional[str] = None
    computed_from_pathway: Optional[str] = None
    computed_from_protein_activity: Optional[str] = None
    source: str = "Cell simulator"
    provenance: Dict[str, ProvenanceEntry] = Field(default_factory=dict)
    trait_details: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


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
    computed_from_gene: Optional[str] = None
    computed_from_pathway: Optional[str] = None
    computed_from_protein_activity: Optional[str] = None
    source: str = "Population simulator"
    provenance: Dict[str, ProvenanceEntry] = Field(default_factory=dict)


class EcosystemResult(BaseModel):
    tumor_like_burden: float
    immune_clearance: float
    inflammation: float
    nutrient_stress: float
    ecosystem_risk_score: float
    explanation: str
    computed_from_gene: Optional[str] = None
    computed_from_pathway: Optional[str] = None
    computed_from_protein_activity: Optional[str] = None
    source: str = "Ecosystem simulator"
    provenance: Dict[str, ProvenanceEntry] = Field(default_factory=dict)
    ecosystem_hierarchy: Dict[str, Any] = Field(default_factory=dict)


class SimulationInputSummary(BaseModel):
    disease_name: str
    disease_id: str
    gene_symbol: str
    gene_id: Optional[str] = None
    uniprot_accession: Optional[str] = None
    protein_name: Optional[str] = None
    mutation: str
    hgvs_notation: Optional[str] = None
    clinvar_variation_id: Optional[str] = None
    rsid: Optional[str] = None
    protein_accession: Optional[str] = None
    alphafold_available: bool = False
    alphafold_confidence_label: Optional[str] = None
    pathway_name: Optional[str] = None
    pathway_id: Optional[str] = None
    pathway_source: Optional[str] = None
    data_source_status: Dict[str, str] = Field(default_factory=dict)


class NormalizedEvidence(BaseModel):
    disease: Dict[str, Any] = Field(default_factory=dict)
    gene: Dict[str, Any] = Field(default_factory=dict)
    variant: Dict[str, Any] = Field(default_factory=dict)
    protein: Dict[str, Any] = Field(default_factory=dict)
    pathways: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    summaries: Dict[str, str] = Field(default_factory=dict)
    external_evidence_available: bool = False
    evidence_notice: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    request: SimulationRequest
    simulation_input: SimulationInputSummary
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
    external_evidence_available: bool = False
    evidence_notice: Optional[str] = None
    disclaimer: str = "Research prototype only, not a diagnostic tool."
    evidence: Optional[NormalizedEvidence] = None
    reasoning: Optional[Dict[str, Any]] = None
