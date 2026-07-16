export type ProvenanceCategory =
  | "external_database"
  | "local_curated"
  | "simulator_assumption"
  | "computed_model"
  | "missing_evidence";

export type ProvenanceEntry = {
  category: ProvenanceCategory;
  source: string;
  detail?: string;
};

export type HierarchyDatum = {
  name: string;
  value?: number;
  type?: string;
  description?: string;
  children?: HierarchyDatum[];
};

export type SearchResultItem = {
  id: string;
  label: string;
  subtitle?: string;
  description?: string;
  synonyms?: string[];
  normalized_mapping?: Record<string, unknown>;
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
  protein_accession?: string;
  protein_name?: string;
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
  gene_name?: string;
  protein_name?: string;
  summary?: string;
  function_summary?: string;
  disease_association_summary?: string;
  function_source?: string;
  function_status_reason?: string;
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
  source_audit?: Array<Record<string, unknown>>;
};

export type SimulationInputSummary = {
  disease_name: string;
  disease_id: string;
  gene_symbol: string;
  resolved_gene_symbol?: string;
  gene_id?: string;
  ensembl_id?: string;
  uniprot_accession?: string;
  resolution_source?: string;
  protein_name?: string;
  mutation: string;
  hgvs_notation?: string;
  clinvar_variation_id?: string;
  rsid?: string;
  protein_accession?: string;
  alphafold_available?: boolean;
  alphafold_confidence_label?: string;
  structure_source?: "alphafold" | "rcsb_pdb" | "pdbe" | "uniprot_feature_map" | "none_found";
  structure_source_label?: string;
  structure_status_reason?: string;
  pathway_name?: string;
  pathway_id?: string;
  pathway_source?: string;
  data_source_status?: Record<string, string>;
  source_status?: Record<string, string>;
  source_audit?: Array<Record<string, unknown>>;
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
    trait_details?: Record<string, {
      label: string;
      score: number;
      confidence: number;
      provenance: string;
      explanation: string;
    }>;
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
    ecosystem_hierarchy?: HierarchyDatum;
  };
  research_summary: string;
  external_evidence_available: boolean;
  evidence_notice?: string;
  disclaimer: string;
  evidence?: NormalizedEvidence;
  reasoning?: BiologicalReasoning;
};

export type BiologicalReasoning = {
  steps: Array<{ layer: string; evidence: string; reasoning: string; consequence: string; confidence: number; provenance: string }>;
  causal_graph: { nodes: Array<{ id: string; label: string; confidence: number }>; edges: Array<{ source: string; target: string; label: string }> };
  summary: string;
};

export type DigitalTwinResult = {
  mode?: "known" | "unknown";
  patient_profile: Record<string, unknown>;
  normalized_symptoms?: Array<{ id: string; label: string; raw: string; source: string }>;
  safety_warnings?: string[];
  disease_risk_profile: Array<{ name: string; score: number; provenance: string }>;
  differential_diagnosis?: DifferentialDiseaseRow[];
  graph?: { nodes: Array<{ id: string; label: string; type?: string; value?: number; source?: string; description?: string }>; links: Array<{ source: string; target: string; relation?: string; weight?: number; description?: string }> };
  category_distribution?: HierarchyDatum;
  known_disease_panels?: Record<string, string>;
  intervention_scenarios?: TwinInterventionScenario[];
  mutation_interpretation: Record<string, unknown>;
  protein_effects: Record<string, unknown>;
  pathway_effects: Array<Record<string, unknown>>;
  cell_state: Record<string, number>;
  population_behaviour: Record<string, number>;
  predicted_biological_state: { overall_risk: number; status: string };
  affected_systems: string[];
  potential_mechanisms: string[];
  missing_data?: string[];
  confidence: number;
  evidence: Array<{ source: string; category: string; detail: string }>;
  reasoning: string[];
  disclaimer: string;
};

export type DifferentialDiseaseRow = {
  rank: number;
  disease: string;
  disease_category: string;
  real_world_causes_mechanism: string;
  matching_symptoms: string[];
  missing_or_unconfirmed_key_symptoms: string[];
  patient_risk_factors_that_support_it: string[];
  evidence_sources: string[];
  confidence: number;
  why_ranked_here: string;
  genes?: string[];
  pathways?: string[];
  intervention_categories?: string[];
  suggested_drug_options?: string[];
  intervention_note?: string;
};

export type TwinInterventionScenario = {
  selected_disease: string;
  disease_category: string;
  matching_symptoms: string[];
  suspected_mechanisms: string[];
  relevant_genes: string[];
  relevant_pathways: string[];
  evidence_sources: string[];
  confidence_score: number;
  suggested_intervention_categories: string[];
  suggested_drug_options: string[];
  note: string;
};

export type EvolutionClone = {
  clone_id: string;
  clone_name: string;
  parent_clone_id: string | null;
  generation_order: number;
  generation_step: number;
  inherited_mutations: string[];
  new_mutation_or_development: string;
  evidence_basis: string;
  database_sources_used: string[];
  missing_evidence: string[];
  name: string;
  parent: string | null;
  mutations: string[];
  growth_rate: number;
  death_rate: number;
  repair_capacity: number;
  repair_ability: number;
  stress_resistance: number;
  immune_evasion: number;
  nutrient_efficiency: number;
  pathway_disruption: number;
  fitness_score: number;
  starting_share: number;
  final_share: number;
  peak_share: number;
  whether_it_expanded: boolean;
  whether_it_declined: boolean;
  why_it_emerged: string;
  why_it_expanded_or_declined: string;
  biological_interpretation: string;
  confidence_score: number;
  provenance_labels: string[];
};

export type EvolutionTimelinePoint = {
  step: number;
  clone_a: number;
  clone_b: number;
  clone_c: number;
  clone_fractions?: Record<string, number>;
  clone_populations?: Record<string, number>;
  major_events?: string[];
};

export type EvolutionEvent = {
  step: number;
  event_type: string;
  clone_id: string;
  clone_name: string;
  description: string;
};

export type EvolutionResult = {
  clones: EvolutionClone[];
  timeline: EvolutionTimelinePoint[];
  tree: Record<string, string[]>;
  clone_tree?: HierarchyDatum;
  clone_composition?: HierarchyDatum;
  final_composition?: HierarchyDatum;
  major_events?: EvolutionEvent[];
  evidence_summary?: {
    sources_used?: string[];
    database_evidence?: string[];
    simulator_context?: string[];
    missing_evidence?: string[];
  };
  model_assumptions?: string[];
  uncertainty_summary?: string;
  student_explanation?: string;
  summary: {
    dominant_clone: string;
    final_clone_fractions: Record<string, number>;
    diversity_score: number;
    clonal_expansion: boolean;
    explanation: string;
  };
  disclaimer: string;
  confidence: number;
  provenance: string;
};

export type InterventionResult = {
  modified_biology: Record<string, number>;
  comparison: {
    baseline_mutated_fraction: number;
    post_intervention_mutated_fraction: number;
    baseline_ecosystem_risk: number;
    post_intervention_ecosystem_risk: number;
    percent_change: number;
    net_effect?: number;
    effective_exposure?: number;
  };
  timeline: Array<{
    step: number;
    before: number;
    after: number;
    affected_population?: number;
    normal_population?: number;
    immune_clearance?: number;
    inflammation?: number;
    dominant_clone_fraction?: number;
    pathway_disruption?: number;
    ecosystem_risk?: number;
  }>;
  clone_response: Array<{ clone: string; suppression: number; fitness_after?: number }>;
  before_after_metrics?: Array<{
    metric_id?: string;
    label: string;
    before: number;
    after: number;
    delta: number;
    direction: "increased" | "decreased" | "unchanged";
    magnitude: number;
    semantic_effect?: "beneficial" | "harmful" | "neutral";
    semantic_explanation?: string;
    semantic_confidence?: number;
    desirability_direction?: "lower_is_beneficial" | "higher_is_beneficial" | "context_dependent" | "no_material_change";
    evidence_basis?: string;
    formula_rule: string;
    provenance: string;
    explanation: string;
  }>;
  mechanism_graph?: {
    nodes: Array<{ id: string; label: string; type?: string; value?: number; source?: string; description?: string }>;
    links: Array<{ source: string; target: string; relation?: string; weight?: number; description?: string }>;
  };
  pathway_before_after?: { before: Record<string, number>; after: Record<string, number> };
  cell_before_after?: { before: Record<string, number>; after: Record<string, number> };
  clone_timeline_before_after?: InterventionResult["timeline"];
  ecosystem_before_after?: {
    site: string;
    before: HierarchyDatum;
    after: HierarchyDatum;
    status: string;
    description: string;
  };
  evidence_summary?: {
    drug?: string;
    normalized_drug?: string;
    mechanism?: string;
    known_targets?: string[];
    clinical_status?: string;
    evidence_level?: string;
    pharmacodynamics?: Record<string, unknown>;
    sources?: string[];
    available?: boolean;
    raw?: Record<string, unknown>;
  };
  student_explanation?: Record<string, string>;
  validation_needs?: string[];
  explanation: string;
  report: string;
  outcome: "helped" | "little effect" | "resistance risk";
  disclaimer: string;
  confidence: number;
  provenance: string;
};
