export type Catalog = {
  diseases: { key: string; label: string; description: string }[];
  genes: { symbol: string; name: string; mutations: string[] }[];
  pathways: { key: string; label: string; description: string }[];
};

export type SimulationRequest = {
  disease: string;
  gene: string;
  mutation: string;
  steps: number;
  initial_mutated_fraction: number;
  initial_population: number;
  immune_pressure: number;
  nutrient_level: number;
};

export type CandidateGene = {
  symbol: string;
  score: number;
  reasons: string[];
  pathways: string[];
  interactions: string[];
};

export type NodeState = {
  id: string;
  type: string;
  baseline: number;
  activity: number;
  delta: number;
};

export type Edge = {
  source: string;
  target: string;
  relation: string;
  weight: number;
};

export type PopulationPoint = {
  step: number;
  normal_cells: number;
  mutated_cells: number;
  mutated_fraction: number;
};

export type SimulationResult = {
  request: SimulationRequest;
  disease_discovery: {
    disease: string;
    label: string;
    affected_cell_context: string;
    candidates: CandidateGene[];
  };
  selected_candidate: CandidateGene;
  mutation_result: {
    gene: string;
    mutation: string;
    kind: string;
    position: number | null;
    domain: string;
    dna_rna_protein_explanation: string;
    biological_interpretation: string;
    activity_multiplier: number;
    stability_multiplier: number;
    binding_multiplier: number;
    confidence: number;
  };
  protein_effect: {
    gene: string;
    protein_name: string;
    protein_id: string;
    mutation: string;
    activity: number;
    stability: number;
    binding: number;
    loss_of_function_score: number;
    affected_domains: string[];
    explanation: string;
  };
  pathway_result: {
    pathway_id: string;
    label: string;
    description: string;
    nodes: NodeState[];
    edges: Edge[];
    disrupted_processes: string[];
    explanation: string;
  };
  cell_phenotype: {
    proliferation_rate: number;
    apoptosis_rate: number;
    repair_capacity: number;
    stress_level: number;
    inflammatory_signal: number;
    genomic_instability: number;
    secretion_signal: number;
    explanation: string;
  };
  population_result: {
    trajectory: PopulationPoint[];
    final_mutated_fraction: number;
    clonal_expansion_score: number;
    explanation: string;
  };
  ecosystem_result: {
    tumor_like_burden: number;
    immune_clearance: number;
    inflammation: number;
    nutrient_stress: number;
    ecosystem_risk_score: number;
    explanation: string;
  };
  research_summary: string;
};
