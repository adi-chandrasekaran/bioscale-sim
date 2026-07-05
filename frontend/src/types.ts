export type ProvenanceCategory =
  | "external_database"
  | "local_curated"
  | "simulator_assumption"
  | "computed_model";

export type ProvenanceEntry = {
  category: ProvenanceCategory;
  source: string;
  detail?: string;
};

export type SearchResultItem = {
  id: string;
  label: string;
  subtitle?: string;
  source: string;
  meta: Record<string, unknown>;
};

export type SearchResponse = {
  query: string;
  source: string;
  available: boolean;
  results: SearchResultItem[];
  error?: string;
};

export type SelectedEntity = {
  id: string;
  label: string;
  meta?: Record<string, unknown>;
};

export type SimulationRequest = {
  disease_id: string;
  disease_name?: string;
  gene: string;
  mutation: string;
  pathway_id?: string;
  pathway_name?: string;
  steps: number;
  initial_mutated_fraction: number;
  initial_population: number;
  immune_pressure: number;
  nutrient_level: number;
  use_external_evidence: boolean;
};

export type CandidateGene = {
  symbol: string;
  score: number;
  reasons: string[];
  pathways: string[];
  interactions: string[];
  source: string;
  summary?: string;
  function_summary?: string;
  provenance: Record<string, ProvenanceEntry>;
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

export type NormalizedEvidence = {
  disease: Record<string, unknown>;
  gene: Record<string, unknown>;
  variant: Record<string, unknown>;
  protein: Record<string, unknown>;
  pathways: Record<string, unknown>[];
  sources: string[];
  summaries: Record<string, string>;
  external_evidence_available: boolean;
  evidence_notice?: string;
  raw: Record<string, unknown>;
};

export type SimulationInputSummary = {
  disease_name: string;
  disease_id: string;
  gene_symbol: string;
  gene_id?: string;
  mutation: string;
  protein_accession?: string;
  pathway_name?: string;
  pathway_id?: string;
  pathway_source?: string;
};

export type SimulationResult = {
  request: SimulationRequest;
  simulation_input: SimulationInputSummary;
  disease_discovery: {
    disease: string;
    disease_id?: string;
    label: string;
    affected_cell_context: string;
    candidates: CandidateGene[];
    summary?: string;
    external_evidence_available: boolean;
    evidence_notice?: string;
    provenance: Record<string, ProvenanceEntry>;
    raw_evidence: Record<string, unknown>;
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
    amino_acid_change?: string;
    clinvar_classification?: string;
    phenotypes: string[];
    source: string;
    summary?: string;
    external_evidence_available: boolean;
    evidence_notice?: string;
    provenance: Record<string, ProvenanceEntry>;
    raw_evidence: Record<string, unknown>;
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
    function_summary?: string;
    mutation_location?: string;
    domain_hit?: string;
    structural_impact_placeholder: string;
    functional_impact_summary?: string;
    source: string;
    summary?: string;
    external_evidence_available: boolean;
    evidence_notice?: string;
    provenance: Record<string, ProvenanceEntry>;
    raw_evidence: Record<string, unknown>;
  };
  pathway_result: {
    pathway_id: string;
    label: string;
    description: string;
    nodes: NodeState[];
    edges: Edge[];
    disrupted_processes: string[];
    explanation: string;
    selected_gene?: string;
    selected_protein?: string;
    selected_pathway_name?: string;
    selected_pathway_source?: string;
    selected_pathway_id?: string;
    is_generic_fallback?: boolean;
    node_activities?: Record<string, number>;
    baseline_activities?: Record<string, number>;
    changed_nodes?: string[];
    reactome_pathways: Record<string, unknown>[];
    reactome_participants: Record<string, unknown>[];
    simulation_model_note: string;
    source: string;
    summary?: string;
    external_evidence_available: boolean;
    evidence_notice?: string;
    provenance: Record<string, ProvenanceEntry>;
    raw_evidence: Record<string, unknown>;
    computed_from_gene?: string;
    computed_from_pathway?: string;
    computed_from_protein_activity?: string;
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
    mapping_mode?: string;
    pathway_disruption_score?: number;
    functional_loss_score?: number;
    computed_from_gene?: string;
    computed_from_pathway?: string;
    computed_from_protein_activity?: string;
    source: string;
    provenance: Record<string, ProvenanceEntry>;
  };
  population_result: {
    trajectory: PopulationPoint[];
    final_mutated_fraction: number;
    clonal_expansion_score: number;
    explanation: string;
    computed_from_gene?: string;
    computed_from_pathway?: string;
    computed_from_protein_activity?: string;
    source: string;
    provenance: Record<string, ProvenanceEntry>;
  };
  ecosystem_result: {
    tumor_like_burden: number;
    immune_clearance: number;
    inflammation: number;
    nutrient_stress: number;
    ecosystem_risk_score: number;
    explanation: string;
    computed_from_gene?: string;
    computed_from_pathway?: string;
    computed_from_protein_activity?: string;
    source: string;
    provenance: Record<string, ProvenanceEntry>;
  };
  research_summary: string;
  external_evidence_available: boolean;
  evidence_notice?: string;
  disclaimer: string;
  evidence?: NormalizedEvidence;
};

export type EvolutionClone = {
  name: string;
  parent: string | null;
  mutations: string[];
  growth_rate: number;
  death_rate: number;
  repair_ability: number;
  stress_resistance: number;
  immune_evasion: number;
  fitness_score: number;
};

export type EvolutionResult = {
  clones: EvolutionClone[];
  timeline: Array<{ step: number; clone_a: number; clone_b: number; clone_c: number }>;
  tree: Record<string, string[]>;
  summary: {
    dominant_clone: string;
    final_clone_fractions: Record<string, number>;
    diversity_score: number;
    clonal_expansion: boolean;
    explanation: string;
  };
  disclaimer: string;
};

export type InterventionResult = {
  modified_biology: Record<string, number>;
  comparison: {
    baseline_mutated_fraction: number;
    post_intervention_mutated_fraction: number;
    baseline_ecosystem_risk: number;
    post_intervention_ecosystem_risk: number;
    percent_change: number;
  };
  timeline: Array<{ step: number; before: number; after: number }>;
  clone_response: Array<{ clone: string; suppression: number }>;
  explanation: string;
  report: string;
  outcome: "helped" | "little effect" | "resistance risk";
  disclaimer: string;
};
