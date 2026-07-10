import { useEffect, useMemo, useState } from "react";
import type { EvolutionResult, HierarchyDatum, InterventionResult, SearchResultItem, SimulationResult, TwinInterventionScenario } from "./types";
import { InfoTooltip } from "./Help";
import type { TooltipHelp } from "./helpContent";
import { MetricCard, SimulatorPanel } from "./SimulatorUI";
import { ForceGraph } from "./components/visualizations/ForceGraph";
import { TimelineChart, type TimelineSeries } from "./components/visualizations/TimelineChart";
import { CirclePackingChart } from "./components/visualizations/CirclePackingChart";

const interventionTypes = ["Drug", "Gene therapy", "CRISPR", "Immune therapy", "Lifestyle", "Environmental"];
const deliveryModes = ["oral", "IV", "local", "gene delivery", "cell therapy", "lifestyle/environmental", "unknown/none"];
const timings = ["early", "mid", "late", "continuous", "pulse"];

const interventionHelp = {
  baseline: {
    summary: "Shows the baseline biological state that the intervention model compares against.",
    details: ["The baseline can come from BioScale, Evolution, or Patient Digital Twin context.", "Every intervention result is a research simulation and not treatment advice."],
    examples: [],
  },
  builder: {
    summary: "Builds a proposed intervention with drug evidence when available and simulator assumptions when evidence is missing.",
    details: ["Drug search checks the local ChEMBL/RxNorm-backed adapter and fills known targets and mechanism when available.", "Strength, specificity, toxicity, resistance, exposure, and tissue penetration jointly determine the modeled probability of biological change."],
    examples: [],
  },
  evidence: {
    summary: "Shows which evidence source informed the selected intervention.",
    details: ["ChEMBL and RxNorm fields are used when a matching drug is known locally or through the adapter.", "CIViC, DrugBank, and PharmGKB are represented as source slots so missing evidence remains explicit."],
    examples: [],
  },
  modifiedBiology: {
    summary: "Shows how the proposed intervention changes target, pathway, cell, clone, and ecosystem variables.",
    details: ["Green means a metric increased after intervention; red means it decreased.", "Whether an increase is good depends on the metric: apoptosis and immune clearance increasing can be beneficial, while proliferation, ecosystem risk, and off-target cost increasing can be concerning."],
    examples: [],
  },
  mechanism: {
    summary: "Maps the modeled causal chain from intervention to target, pathway, cell state, clone response, and tissue ecosystem.",
    details: ["Nodes are computed from the current run.", "Edges show the rule-based propagation used by this research simulator."],
    examples: [],
  },
  timeline: {
    summary: "Tracks how the intervention changes simulated biological state over time.",
    details: ["Use the toggles to compare affected population, normal population, immune clearance, inflammation, dominant clone fraction, pathway disruption, and ecosystem risk.", "These are normalized simulator probabilities, not clinical forecasts."],
    examples: [],
  },
  ecosystem: {
    summary: "Compares the affected body site before and after the intervention.",
    details: ["The site is inferred from disease and patient-context text when no anatomical database match is available.", "The before/after body map is a labeled teaching model of the affected tissue environment."],
    examples: [],
  },
  report: {
    summary: "Explains the modeled outcome, assumptions, and validation needed before any real-world interpretation.",
    details: ["The report is intentionally framed as research simulation only.", "Validation needs include drug-target evidence, exposure-response data, tissue penetration, biomarkers, clone tracking, and toxicity data."],
    examples: [],
  },
};

const fieldHelp: Record<string, TooltipHelp> = {
  type: { title: "Intervention type", summary: "The class of perturbation being simulated, such as a drug, CRISPR edit, immune therapy, lifestyle change, or environmental change.", details: ["Different types use different deterministic effect multipliers in the simulator."], examples: [] },
  target: { title: "Target", summary: "The biological target the intervention is modeled to act on.", details: ["For drugs, this is filled from known targets when evidence is available. Otherwise it can be the selected gene, pathway, dominant clone, or all mutated cells."], examples: [] },
  strength: { title: "Strength", summary: "The normalized probability that the intervention meaningfully affects its target in this simulation.", details: ["Strength is not a dose. It is multiplied by specificity, exposure, tissue penetration, route, timing, and target match."], examples: [] },
  delivery: { title: "Delivery mode", summary: "How the intervention reaches the body or tissue in this model.", details: ["Delivery changes effective exposure. IV and local delivery usually preserve more modeled exposure than unknown delivery."], examples: [] },
  timing: { title: "Timing", summary: "When the intervention is applied relative to disease progression.", details: ["Early and continuous timing usually improve modeled impact; late or pulse timing can reduce it."], examples: [] },
  duration: { title: "Duration / cycles", summary: "How long the modeled intervention is applied.", details: ["The backend currently stores this as context and keeps it available for future cycle-specific modeling."], examples: [] },
  specificity: { title: "Specificity", summary: "How selectively the intervention hits the intended target.", details: ["Higher specificity lowers off-target biological cost. Lower specificity increases stress or ecosystem tradeoffs."], examples: [] },
  toxicity: { title: "Toxicity / cost", summary: "The modeled biological burden caused by the intervention itself.", details: ["Higher toxicity can increase stress, inflammation, and ecosystem risk even if the target effect is strong."], examples: [] },
  resistance: { title: "Resistance pressure", summary: "The probability that clone escape, pathway bypass, or adaptation reduces intervention effect.", details: ["Resistance pressure is combined with clone fitness and dominant clone fraction."], examples: [] },
  combination: { title: "Combination partner", summary: "An optional second intervention or context modifier.", details: ["This is passed into the model context and evidence report; it does not represent a recommendation."], examples: [] },
  exposure: { title: "Adherence / exposure", summary: "The modeled fraction of the intended intervention exposure that actually reaches the system.", details: ["Lower exposure reduces effective intervention strength."], examples: [] },
  penetration: { title: "Tissue penetration", summary: "How well the intervention reaches the affected tissue.", details: ["Low tissue penetration weakens the modeled target effect even when strength is high."], examples: [] },
  severity: { title: "Baseline severity", summary: "How burdened the modeled state is before intervention.", details: ["Higher baseline severity increases biological cost sensitivity and uncertainty."], examples: [] },
};

type DrugOption = SearchResultItem & {
  meta: SearchResultItem["meta"] & {
    molecule_id?: string;
    known_targets?: string[];
    mechanism?: string;
    clinical_status?: string;
    evidence_level?: string;
    synonyms?: string[];
  };
};

function typeFromScenario(scenario: TwinInterventionScenario | null) {
  const categories = scenario?.suggested_intervention_categories ?? [];
  if (categories.some((item) => item.toLowerCase().includes("immune"))) return "Immune therapy";
  if (categories.some((item) => item.toLowerCase().includes("gene"))) return "Gene therapy";
  if (categories.some((item) => item.toLowerCase().includes("lifestyle") || item.toLowerCase().includes("nutritional"))) return "Lifestyle";
  if (categories.some((item) => item.toLowerCase().includes("targeted") || item.toLowerCase().includes("drug"))) return "Drug";
  return interventionTypes[0];
}

function clamp01(value: number) {
  return Math.max(0, Math.min(1, value));
}

function averagePathwayActivity(baseline: SimulationResult | null) {
  const nodes = baseline?.pathway_result.nodes ?? [];
  if (!nodes.length) return 0.5;
  return nodes.reduce((sum, node) => sum + node.activity, 0) / nodes.length;
}

function genericTrajectory(baseline: SimulationResult | null, scenario: TwinInterventionScenario | null) {
  if (baseline?.population_result.trajectory?.length) return baseline.population_result.trajectory;
  const seed = Math.max(0.05, scenario?.confidence_score ?? 0.35);
  return Array.from({ length: 7 }, (_, index) => ({ step: index * 10, mutated_fraction: clamp01(seed * (0.35 + index * 0.1)) }));
}

function firstKnownTarget(option: DrugOption | null) {
  return option?.meta.known_targets?.[0] || option?.meta.molecule_id || "";
}

function formatSigned(delta: number) {
  const sign = delta > 0 ? "+" : "";
  return `${sign}${(delta * 100).toFixed(1)}%`;
}

function timelineSeries(output: InterventionResult): TimelineSeries[] {
  const point = (key: keyof InterventionResult["timeline"][number]) => output.timeline.map((item) => ({ step: item.step, value: Number(item[key] ?? 0) }));
  return [
    { id: "before", label: "Affected population before", values: point("before") },
    { id: "after", label: "Affected population after", values: point("after") },
    { id: "normal", label: "Normal/homeostatic population", values: point("normal_population") },
    { id: "immune", label: "Immune clearance", values: point("immune_clearance") },
    { id: "inflammation", label: "Inflammation", values: point("inflammation") },
    { id: "clone", label: "Dominant clone fraction", values: point("dominant_clone_fraction") },
    { id: "pathway", label: "Pathway disruption", values: point("pathway_disruption") },
    { id: "risk", label: "Ecosystem risk", values: point("ecosystem_risk") },
  ];
}

function buildMetricCards(output: InterventionResult) {
  const metrics = output.before_after_metrics ?? [];
  return metrics.map((metric) => ({
    ...metric,
    help: {
      title: metric.label,
      summary: `If this occurs, there is a probability that ${metric.label} will ${metric.direction} by ${(metric.magnitude * 100).toFixed(1)}%.`,
      details: [
        `Before: ${(metric.before * 100).toFixed(1)}%. After: ${(metric.after * 100).toFixed(1)}%. Delta: ${formatSigned(metric.delta)}.`,
        metric.explanation,
        `Rule: ${metric.formula_rule}. Provenance: ${metric.provenance}.`,
      ],
      examples: [],
    } satisfies TooltipHelp,
  }));
}

function BodyComparison({ model }: { model: NonNullable<InterventionResult["ecosystem_before_after"]> }) {
  const [zoomed, setZoomed] = useState(false);
  const beforeRisk = model.before.children?.[0]?.value ?? 0;
  const afterRisk = model.after.children?.[0]?.value ?? 0;
  const delta = Number(afterRisk) - Number(beforeRisk);
  return (
    <div className={`bodyComparisonPanel ${zoomed ? "zoomed" : ""}`}>
      <div className="bodyComparisonControls">
        <div>
          <strong>{model.site}</strong>
          <span>{model.status} · {formatSigned(delta)} risk shift</span>
        </div>
        <button type="button" onClick={() => setZoomed((current) => !current)}>{zoomed ? "Reset zoom" : "Zoom affected site"}</button>
      </div>
      <svg className="bodyComparisonSvg" viewBox="0 0 760 330" role="img" aria-label={`Before and after body-site map for ${model.site}`}>
        <defs>
          <radialGradient id="siteGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={delta <= 0 ? "#9bcfb6" : "#efb1a9"} stopOpacity="0.9" />
            <stop offset="100%" stopColor={delta <= 0 ? "#237457" : "#b63f3f"} stopOpacity="0.18" />
          </radialGradient>
        </defs>
        {["Before", "After"].map((label, index) => {
          const x = index === 0 ? 190 : 570;
          const risk = index === 0 ? beforeRisk : afterRisk;
          const color = index === 0 ? "#64746f" : delta <= 0 ? "#237457" : "#b63f3f";
          return (
            <g key={label} transform={`translate(${x}, 0) scale(${zoomed && index === 1 ? 1.18 : 1}) translate(${zoomed && index === 1 ? -30 : 0}, 0)`}>
              <text x="0" y="28" textAnchor="middle" className="bodyTextTitle">{label}</text>
              <circle cx="0" cy="65" r="32" className="bodyComparisonOutline" />
              <path d="M -58 122 C -45 92 45 92 58 122 L 42 246 C 34 282 -34 282 -42 246 Z" className="bodyComparisonOutline" />
              <path d="M -58 136 L -102 206" className="bodyComparisonLimb" />
              <path d="M 58 136 L 102 206" className="bodyComparisonLimb" />
              <path d="M -27 270 L -43 322" className="bodyComparisonLimb" />
              <path d="M 27 270 L 43 322" className="bodyComparisonLimb" />
              <circle cx="10" cy="162" r={30 + Number(risk) * 24} fill="url(#siteGlow)" stroke={color} strokeWidth="3" />
              <text x="10" y="158" textAnchor="middle" className="bodySiteLabel">{model.site}</text>
              <text x="10" y="176" textAnchor="middle" className="bodySiteValue">{(Number(risk) * 100).toFixed(0)}%</text>
              <line x1="48" y1="158" x2="138" y2="128" stroke={color} strokeWidth="2" />
              <foreignObject x="138" y="92" width="170" height="90">
                <div className="bodyCallout">
                  <strong>{model.site}</strong>
                  <span>{index === 0 ? "baseline risk" : "post-intervention risk"} {(Number(risk) * 100).toFixed(1)}%</span>
                </div>
              </foreignObject>
            </g>
          );
        })}
      </svg>
      <p>{model.description}</p>
    </div>
  );
}

function EvidencePanel({ evidence }: { evidence: InterventionResult["evidence_summary"] | null }) {
  if (!evidence) return <p className="muted">No intervention evidence has been selected yet.</p>;
  return (
    <div className="evidenceSummaryGrid">
      <div><span>Drug</span><strong>{evidence.drug || "Not selected"}</strong></div>
      <div><span>Normalized</span><strong>{evidence.normalized_drug || "Unavailable"}</strong></div>
      <div><span>Targets</span><strong>{evidence.known_targets?.join(", ") || "No known target loaded"}</strong></div>
      <div><span>Status</span><strong>{evidence.clinical_status || "Unknown"}</strong></div>
      <div><span>Evidence level</span><strong>{evidence.evidence_level || "Simulator assumption"}</strong></div>
      <div><span>Sources</span><strong>{evidence.sources?.filter(Boolean).join(", ") || "Fallback / unavailable"}</strong></div>
      <p className="wideEvidence">{evidence.mechanism || "No mechanism loaded; the simulator will use a generic mechanism-based rule."}</p>
    </div>
  );
}

export function InterventionSimulator({ apiBase, baseline, evolution, scenario, onResult }: { apiBase: string; baseline: SimulationResult | null; evolution: EvolutionResult | null; scenario?: TwinInterventionScenario | null; onResult?: (result: InterventionResult | null) => void }) {
  const [type, setType] = useState(typeFromScenario(scenario ?? null));
  const [strength, setStrength] = useState(0.5);
  const [target, setTarget] = useState(scenario?.relevant_genes?.[0] ?? scenario?.relevant_pathways?.[0] ?? "selected gene/protein");
  const [drugQuery, setDrugQuery] = useState(scenario?.suggested_drug_options?.[0] ?? "");
  const [drugResults, setDrugResults] = useState<DrugOption[]>([]);
  const [selectedDrug, setSelectedDrug] = useState<DrugOption | null>(null);
  const [drugEvidence, setDrugEvidence] = useState<InterventionResult["evidence_summary"] | null>(null);
  const [deliveryMode, setDeliveryMode] = useState("unknown/none");
  const [timing, setTiming] = useState("continuous");
  const [durationCycles, setDurationCycles] = useState(3);
  const [specificity, setSpecificity] = useState(0.7);
  const [toxicityCost, setToxicityCost] = useState(0.18);
  const [resistancePressure, setResistancePressure] = useState(0.25);
  const [combinationPartner, setCombinationPartner] = useState("none");
  const [adherenceExposure, setAdherenceExposure] = useState(0.85);
  const [tissuePenetration, setTissuePenetration] = useState(0.72);
  const [baselineSeverity, setBaselineSeverity] = useState(0.5);
  const [output, setOutput] = useState<InterventionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [drugLoading, setDrugLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const genericBaseline = useMemo(() => {
    const dominantShare = evolution ? Math.max(...Object.values(evolution.summary.final_clone_fractions), 0.35) : undefined;
    const dominantClone = evolution?.clones.find((clone) => clone.clone_name === evolution.summary.dominant_clone) ?? evolution?.clones[0];
    return {
      disease: scenario?.selected_disease ?? baseline?.simulation_input.disease_name ?? "selected disease",
      diseaseCategory: scenario?.disease_category ?? "",
      symptoms: scenario?.matching_symptoms ?? [],
      gene: scenario?.relevant_genes?.[0] ?? baseline?.simulation_input.gene_symbol ?? "unknown",
      mutation: baseline?.simulation_input.mutation ?? "unknown",
      protein: baseline?.protein_effect.protein_name ?? "",
      pathway: scenario?.relevant_pathways?.[0] ?? baseline?.pathway_result.label ?? "selected pathway",
      mutatedFraction: baseline?.population_result.final_mutated_fraction ?? Math.max(0.05, scenario?.confidence_score ?? 0.35),
      ecosystemRisk: baseline?.ecosystem_result.ecosystem_risk_score ?? scenario?.confidence_score ?? 0.35,
      proliferation: baseline?.cell_phenotype.proliferation_rate ?? 0.5,
      apoptosis: baseline?.cell_phenotype.apoptosis_rate ?? 0.45,
      repair: baseline?.cell_phenotype.repair_capacity ?? 0.5,
      immune: baseline?.ecosystem_result.immune_clearance ?? 0.5,
      inflammation: baseline?.ecosystem_result.inflammation ?? baseline?.cell_phenotype.inflammatory_signal ?? 0.45,
      stress: baseline?.cell_phenotype.stress_level ?? 0.45,
      pathwayActivity: averagePathwayActivity(baseline),
      pathwayDisruption: baseline?.protein_effect.loss_of_function_score ?? baseline?.cell_phenotype.pathway_disruption_score ?? 0.5,
      cloneFitness: dominantClone?.fitness_score ?? 0.5,
      dominantCloneFraction: dominantShare ?? baseline?.population_result.final_mutated_fraction ?? 0.35,
      trajectory: genericTrajectory(baseline, scenario ?? null),
    };
  }, [baseline, evolution, scenario]);

  useEffect(() => {
    setOutput(null);
    onResult?.(null);
    setType(typeFromScenario(scenario ?? null));
    setTarget(scenario?.relevant_genes?.[0] ?? scenario?.relevant_pathways?.[0] ?? baseline?.simulation_input.gene_symbol ?? "selected gene/protein");
    setDrugQuery(scenario?.suggested_drug_options?.[0] ?? "");
    setDrugResults([]);
    setSelectedDrug(null);
    setDrugEvidence(null);
  }, [baseline, scenario]);

  const targetOptions = useMemo(() => {
    const values = new Set<string>(["selected gene/protein", genericBaseline.gene, genericBaseline.pathway, "dominant clone", "all mutated cells"]);
    drugResults.forEach((drug) => drug.meta.known_targets?.forEach((item) => values.add(item)));
    selectedDrug?.meta.known_targets?.forEach((item) => values.add(item));
    return Array.from(values).filter(Boolean);
  }, [drugResults, genericBaseline.gene, genericBaseline.pathway, selectedDrug]);

  async function searchDrugs() {
    if (!drugQuery.trim()) return;
    setDrugLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}/api/search/drugs?q=${encodeURIComponent(drugQuery.trim())}&target=${encodeURIComponent(genericBaseline.gene)}&limit=8`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Drug search failed");
      setDrugResults((payload.results ?? []) as DrugOption[]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Drug search failed");
    } finally {
      setDrugLoading(false);
    }
  }

  async function chooseDrug(option: DrugOption) {
    setSelectedDrug(option);
    setDrugQuery(option.label);
    const knownTarget = firstKnownTarget(option);
    if (knownTarget) setTarget(knownTarget);
    setType("Drug");
    try {
      const response = await fetch(`${apiBase}/api/drug/evidence?drug=${encodeURIComponent(option.label)}&gene=${encodeURIComponent(genericBaseline.gene)}&mutation=${encodeURIComponent(genericBaseline.mutation)}`);
      const payload = await response.json();
      if (response.ok) setDrugEvidence(payload);
    } catch {
      setDrugEvidence({
        drug: option.label,
        normalized_drug: option.label,
        mechanism: option.meta.mechanism,
        known_targets: option.meta.known_targets ?? [],
        clinical_status: option.meta.clinical_status,
        evidence_level: option.meta.evidence_level,
        available: false,
      });
    }
  }

  function requestPayload() {
    return {
      disease: genericBaseline.disease,
      disease_category: genericBaseline.diseaseCategory,
      symptoms: genericBaseline.symptoms,
      gene: genericBaseline.gene,
      mutation: genericBaseline.mutation,
      intervention_type: type,
      drug_name: selectedDrug?.label ?? (type === "Drug" ? drugQuery.trim() : ""),
      selected_drug: selectedDrug ? { id: selectedDrug.id, name: selectedDrug.label, ...selectedDrug.meta } : null,
      strength,
      target,
      delivery_mode: deliveryMode,
      timing,
      duration_cycles: durationCycles,
      specificity,
      toxicity_cost: toxicityCost,
      resistance_pressure: resistancePressure,
      combination_partner: combinationPartner,
      adherence_exposure: adherenceExposure,
      tissue_penetration: tissuePenetration,
      baseline_severity: baselineSeverity,
      alpha_fold_context: {
        protein: genericBaseline.protein,
        alphafold_available: baseline?.simulation_input.alphafold_available ?? false,
        confidence_label: baseline?.simulation_input.alphafold_confidence_label ?? "not loaded",
      },
      patient_context: scenario ?? {},
      intervention_scenario: scenario ?? {},
      baseline_mutated_fraction: genericBaseline.mutatedFraction,
      baseline_ecosystem_risk: genericBaseline.ecosystemRisk,
      proliferation: genericBaseline.proliferation,
      apoptosis: genericBaseline.apoptosis,
      repair_capacity: genericBaseline.repair,
      immune_clearance: genericBaseline.immune,
      inflammation: genericBaseline.inflammation,
      stress_response: genericBaseline.stress,
      pathway_activity: genericBaseline.pathwayActivity,
      pathway_disruption: genericBaseline.pathwayDisruption,
      clone_fitness: genericBaseline.cloneFitness,
      dominant_clone_fraction: genericBaseline.dominantCloneFraction,
      normal_population_fraction: clamp01(1 - genericBaseline.mutatedFraction),
      baseline_timeline: genericBaseline.trajectory,
      evolution_clones: evolution?.clones ?? [],
    };
  }

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}/api/intervention/simulate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(requestPayload()) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Intervention simulation failed");
      setOutput(payload);
      onResult?.(payload);
      setDrugEvidence(payload.evidence_summary ?? drugEvidence);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Intervention simulation failed");
    } finally {
      setLoading(false);
    }
  }

  const beforeAfterCards = output ? buildMetricCards(output) : [];
  const evidence = output?.evidence_summary ?? drugEvidence;
  const ecosystemModel = output?.ecosystem_before_after;
  const pathwayBefore = output?.pathway_before_after?.before ?? {};
  const pathwayAfter = output?.pathway_before_after?.after ?? {};
  const cellBefore = output?.cell_before_after?.before ?? {};
  const cellAfter = output?.cell_before_after?.after ?? {};

  return (
    <div className="grid secondarySimulator interventionResearch">
      <SimulatorPanel title="Intervention Baseline" eyebrow="Shared simulator context" help={interventionHelp.baseline}>
        <div className="contextStrip">
          <span>Disease <b>{genericBaseline.disease}</b></span>
          <span>Gene <b>{genericBaseline.gene}</b></span>
          <span>Mutation <b>{genericBaseline.mutation}</b></span>
          <span>Pathway <b>{genericBaseline.pathway}</b></span>
        </div>
        {scenario && <div className="modelNote"><strong>Loaded from Patient Digital Twin</strong><p>{scenario.selected_disease} · {scenario.disease_category} · confidence {(scenario.confidence_score * 100).toFixed(0)}%. {scenario.note}</p><p>Suggested simulation categories: {scenario.suggested_intervention_categories.join(", ") || "Generic mechanism-based intervention"}</p></div>}
        {!baseline && <p className="researchDisclaimer">No BioScale baseline is available, so this uses a generic mechanism-based intervention baseline from the Patient Digital Twin scenario. This is not treatment advice.</p>}
        <div className="metricGrid">
          <MetricCard label="Baseline mutated fraction" value={genericBaseline.mutatedFraction} before={0.02} context="The modeled affected population fraction before intervention." />
          <MetricCard label="Baseline ecosystem risk" value={genericBaseline.ecosystemRisk} before={0.5} context="The modeled tissue ecosystem risk before intervention." />
          <MetricCard label="Clone fitness" value={genericBaseline.cloneFitness} before={0.5} context="The dominant clone's modeled ability to persist before intervention." />
          <MetricCard label="Pathway disruption" value={genericBaseline.pathwayDisruption} before={0.5} context="The upstream pathway burden carried into intervention modeling." />
        </div>
      </SimulatorPanel>

      <SimulatorPanel title="Intervention Builder" eyebrow="Drug evidence + model inputs" help={interventionHelp.builder}>
        <div className="drugSearchPanel">
          <label>
            <span>Drug search <InfoTooltip label="Drug search" help={{ title: "Drug search", summary: "Search for a drug or compound name to load known targets and mechanism when evidence exists.", details: ["The simulator can still run without a drug match, but the evidence panel will clearly say the model is using assumptions."], examples: [] }} /></span>
            <div className="drugSearchRow">
              <input value={drugQuery} onChange={(event) => setDrugQuery(event.target.value)} placeholder="Search ChEMBL/RxNorm, e.g. imatinib" />
              <button type="button" onClick={() => void searchDrugs()} disabled={drugLoading}>{drugLoading ? "Searching..." : "Search drugs"}</button>
            </div>
          </label>
          {drugResults.length > 0 && <div className="drugResultList">
            {drugResults.map((drug) => (
              <button key={drug.id} type="button" className={selectedDrug?.id === drug.id ? "drugResultCard selected" : "drugResultCard"} onClick={() => void chooseDrug(drug)}>
                <strong>{drug.label}</strong>
                <span>{drug.meta.molecule_id || drug.id} · {drug.source}</span>
                <p>{drug.meta.mechanism || drug.description || "Mechanism not loaded."}</p>
                <small>Targets: {drug.meta.known_targets?.join(", ") || "unknown"}</small>
              </button>
            ))}
          </div>}
        </div>

        <div className="interventionControls">
          <label><span>Type <InfoTooltip label="Type" help={fieldHelp.type} /></span><select value={type} onChange={(event) => setType(event.target.value)}>{interventionTypes.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label><span>Target <InfoTooltip label="Target" help={fieldHelp.target} /></span><select value={target} onChange={(event) => setTarget(event.target.value)}>{targetOptions.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="simSlider"><span>Strength <InfoTooltip label="Strength" help={fieldHelp.strength} /><strong>{strength.toFixed(2)}</strong></span><input type="range" min="0" max="1" step="0.01" value={strength} onChange={(event) => setStrength(Number(event.target.value))} /></label>
        </div>

        <details className="advancedIntervention">
          <summary>Advanced intervention inputs</summary>
          <div className="advancedInterventionGrid">
            <label><span>Delivery mode <InfoTooltip label="Delivery mode" help={fieldHelp.delivery} /></span><select value={deliveryMode} onChange={(event) => setDeliveryMode(event.target.value)}>{deliveryModes.map((item) => <option key={item}>{item}</option>)}</select></label>
            <label><span>Timing <InfoTooltip label="Timing" help={fieldHelp.timing} /></span><select value={timing} onChange={(event) => setTiming(event.target.value)}>{timings.map((item) => <option key={item}>{item}</option>)}</select></label>
            <label><span>Duration / cycles <InfoTooltip label="Duration" help={fieldHelp.duration} /></span><input type="number" min="1" max="52" value={durationCycles} onChange={(event) => setDurationCycles(Number(event.target.value))} /></label>
            <label className="simSlider"><span>Specificity <InfoTooltip label="Specificity" help={fieldHelp.specificity} /><strong>{specificity.toFixed(2)}</strong></span><input type="range" min="0" max="1" step="0.01" value={specificity} onChange={(event) => setSpecificity(Number(event.target.value))} /></label>
            <label className="simSlider"><span>Toxicity / cost <InfoTooltip label="Toxicity" help={fieldHelp.toxicity} /><strong>{toxicityCost.toFixed(2)}</strong></span><input type="range" min="0" max="1" step="0.01" value={toxicityCost} onChange={(event) => setToxicityCost(Number(event.target.value))} /></label>
            <label className="simSlider"><span>Resistance pressure <InfoTooltip label="Resistance" help={fieldHelp.resistance} /><strong>{resistancePressure.toFixed(2)}</strong></span><input type="range" min="0" max="1" step="0.01" value={resistancePressure} onChange={(event) => setResistancePressure(Number(event.target.value))} /></label>
            <label><span>Combination partner <InfoTooltip label="Combination partner" help={fieldHelp.combination} /></span><input value={combinationPartner} onChange={(event) => setCombinationPartner(event.target.value)} /></label>
            <label className="simSlider"><span>Adherence / exposure <InfoTooltip label="Exposure" help={fieldHelp.exposure} /><strong>{adherenceExposure.toFixed(2)}</strong></span><input type="range" min="0" max="1" step="0.01" value={adherenceExposure} onChange={(event) => setAdherenceExposure(Number(event.target.value))} /></label>
            <label className="simSlider"><span>Tissue penetration <InfoTooltip label="Tissue penetration" help={fieldHelp.penetration} /><strong>{tissuePenetration.toFixed(2)}</strong></span><input type="range" min="0" max="1" step="0.01" value={tissuePenetration} onChange={(event) => setTissuePenetration(Number(event.target.value))} /></label>
            <label className="simSlider"><span>Baseline severity <InfoTooltip label="Baseline severity" help={fieldHelp.severity} /><strong>{baselineSeverity.toFixed(2)}</strong></span><input type="range" min="0" max="1" step="0.01" value={baselineSeverity} onChange={(event) => setBaselineSeverity(Number(event.target.value))} /></label>
          </div>
        </details>
        <button className="primaryAction" onClick={() => void run()} disabled={loading}>{loading ? "Simulating intervention..." : "Run intervention simulation"}</button>
        {error && <p className="error">{error}</p>}
        <p className="researchDisclaimer">Research simulation only — not treatment advice.</p>
      </SimulatorPanel>

      <SimulatorPanel title="Intervention Evidence" eyebrow="Drug target and mechanism" help={interventionHelp.evidence}>
        <EvidencePanel evidence={evidence ?? null} />
      </SimulatorPanel>

      {!output ? <div className="emptyState wideEmpty">Choose an intervention and run the simulation to see before/after biology, causal graphs, and tissue impact.</div> : <>
        <SimulatorPanel title="Modified Biology" eyebrow="Before / after model" help={interventionHelp.modifiedBiology}>
          <div className="beforeAfterMetricGrid">
            {beforeAfterCards.map((metric) => (
              <article key={metric.label} className={`metricChangeCard ${metric.direction}`}>
                <div className="metricChangeHeader">
                  <strong>{metric.label}<InfoTooltip label={metric.label} help={metric.help} /></strong>
                  <span>{metric.direction} {formatSigned(metric.delta)}</span>
                </div>
                <div className="metricChangeBars">
                  <span>Before <b>{metric.before.toFixed(2)}</b></span><div className="barOuter"><div className="barInner neutralBar" style={{ width: `${clamp01(metric.before) * 100}%` }} /></div>
                  <span>After <b>{metric.after.toFixed(2)}</b></span><div className="barOuter"><div className={`barInner ${metric.direction === "decreased" ? "decreased" : "increased"}`} style={{ width: `${clamp01(metric.after) * 100}%` }} /></div>
                </div>
                <p>{metric.explanation}</p>
                <small>{metric.provenance}</small>
              </article>
            ))}
          </div>
        </SimulatorPanel>

        <SimulatorPanel title="Mechanism Causal Graph" eyebrow="Intervention -> tissue outcome" help={interventionHelp.mechanism}>
          <ForceGraph nodes={output.mechanism_graph?.nodes ?? []} links={output.mechanism_graph?.links ?? []} title="Modeled causal mechanism" description="Drag nodes or hover edges to inspect the deterministic propagation rule." />
        </SimulatorPanel>

        <SimulatorPanel title="Pathway and Cell Before / After" eyebrow="Mechanism-level visuals" help={interventionHelp.modifiedBiology}>
          <div className="interventionVisualGrid">
            <div>
              <h3>Pathway state</h3>
              <div className="metricGrid">
                <MetricCard label="Target activity after" value={Number(pathwayAfter.activity ?? 0)} before={Number(pathwayBefore.activity ?? 0.5)} context="Target activity after intervention." />
                <MetricCard label="Pathway disruption after" value={Number(pathwayAfter.disruption ?? 0)} before={Number(pathwayBefore.disruption ?? 0.5)} context="Pathway disruption after intervention." />
              </div>
            </div>
            <div>
              <h3>Cell phenotype state</h3>
              <div className="metricGrid">
                <MetricCard label="Proliferation" value={Number(cellAfter.proliferation ?? 0)} before={Number(cellBefore.proliferation ?? 0.5)} context="Cell division pressure after intervention." />
                <MetricCard label="Apoptosis/death" value={Number(cellAfter.apoptosis ?? 0)} before={Number(cellBefore.apoptosis ?? 0.5)} context="Affected-cell removal pressure after intervention." />
                <MetricCard label="Repair/homeostasis" value={Number(cellAfter.repair ?? 0)} before={Number(cellBefore.repair ?? 0.5)} context="Homeostatic repair state after intervention." />
                <MetricCard label="Stress/inflammation" value={Number(((cellAfter.stress ?? 0) + (cellAfter.inflammation ?? 0)) / 2)} before={Number(((cellBefore.stress ?? 0.5) + (cellBefore.inflammation ?? 0.5)) / 2)} context="Average stress and inflammation after intervention." />
              </div>
            </div>
          </div>
        </SimulatorPanel>

        <SimulatorPanel title="Intervention Timeline" eyebrow="Population, clone, immune, and ecosystem state" help={interventionHelp.timeline}>
          <TimelineChart series={timelineSeries(output)} title="Before and after intervention trajectory" yLabel="normalized probability" />
          {output.clone_response.length > 0 && <div className="cloneResponse"><strong>Clone response</strong>{output.clone_response.map((clone) => <span key={clone.clone}>{clone.clone}: {(clone.suppression * 100).toFixed(0)}% suppression{clone.fitness_after !== undefined ? ` · fitness ${clone.fitness_after.toFixed(2)}` : ""}</span>)}</div>}
        </SimulatorPanel>

        <SimulatorPanel title="Ecosystem Body Impact" eyebrow="Affected region before / after" help={interventionHelp.ecosystem}>
          {ecosystemModel && <BodyComparison model={ecosystemModel} />}
          <div className="interventionVisualGrid">
            <CirclePackingChart data={ecosystemModel?.before ?? { name: "Before intervention", children: [] } as HierarchyDatum} title="Before intervention tissue ecosystem" description="Circle size follows baseline local tissue risk." />
            <CirclePackingChart data={ecosystemModel?.after ?? { name: "After intervention", children: [] } as HierarchyDatum} title="After intervention tissue ecosystem" description="Circle size follows post-intervention local tissue risk and tradeoff." />
          </div>
        </SimulatorPanel>

        <SimulatorPanel title="Outcome Report" eyebrow={`Outcome: ${output.outcome}`} help={interventionHelp.report}>
          <div className="metricGrid">
            <MetricCard label="Model confidence" value={output.confidence} before={0.5} context="Confidence reflects evidence availability plus upstream BioScale and Evolution context." />
            <MetricCard label="Effective exposure" value={output.comparison.effective_exposure ?? 0} before={0.5} context="Strength after route, timing, specificity, exposure, tissue penetration, and target match." />
            <MetricCard label="Net effect" value={output.comparison.net_effect ?? 0} before={0.5} context="Effective exposure after resistance and toxicity penalties." />
            <MetricCard label="Mutated fraction change" value={`${output.comparison.percent_change.toFixed(1)}%`} context="Relative percent difference between baseline and post-intervention affected fraction." />
          </div>
          <p className="panelExplanation">{output.explanation}</p>
          <p className="reportText">{output.report}</p>
          <details className="rawEvidence">
            <summary>Student explanation</summary>
            <div className="studentTermGrid">
              {Object.entries(output.student_explanation ?? {}).map(([term, description]) => <div key={term}><strong>{term.replaceAll("_", " ")}</strong><span>{description}</span></div>)}
            </div>
          </details>
          <details className="rawEvidence">
            <summary>Validation needed</summary>
            <ul className="validationList">{(output.validation_needs ?? []).map((item) => <li key={item}>{item}</li>)}</ul>
          </details>
          <p className="researchDisclaimer">{output.disclaimer}</p>
        </SimulatorPanel>
      </>}
    </div>
  );
}
