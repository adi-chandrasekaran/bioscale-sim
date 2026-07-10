import { useMemo, useState } from "react";
import type { DifferentialDiseaseRow, DigitalTwinResult, SimulationResult, TwinInterventionScenario } from "./types";
import { MetricCard, SimulatorPanel } from "./SimulatorUI";
import { ProvenanceBadge } from "./ProvenanceBadge";
import { ForceGraph } from "./components/visualizations/ForceGraph";
import { CirclePackingChart } from "./components/visualizations/CirclePackingChart";

type Mode = "known" | "unknown";
type Profile = {
  age: number; sex: string; ethnicity: string; weight: number; height: number; symptoms: string;
  conditions: string; family: string; diagnoses: string; smoking: string; alcohol: number; exercise: number; diet: number;
  medications: string; genes: string; mutations: string; variants: string; crp: number; glucose: number;
};

const initial: Profile = {
  age: 40, sex: "unspecified", ethnicity: "", weight: 70, height: 170, symptoms: "fatigue, fever",
  conditions: "", family: "", diagnoses: "", smoking: "never", alcohol: 0, exercise: 150, diet: 0.65,
  medications: "", genes: "", mutations: "", variants: "", crp: 0, glucose: 0,
};

const list = (value: string) => value.split(",").map((item) => item.trim()).filter(Boolean);

const twinHelp = {
  profile: {
    summary: "Builds a patient-specific model from symptoms, history, labs, variants, and optional BioScale context.",
    details: [
      "Known disease mode personalizes a diagnosis that is already known.",
      "Unknown illness mode ranks possible diseases from symptoms and risk factors without requiring disease, gene, or mutation inputs.",
      "This is a research prototype, not a diagnostic or triage system.",
    ],
    examples: [],
  },
  differential: {
    summary: "Ranks possible diseases using deterministic evidence-weighted scoring.",
    details: [
      "Scores combine symptom overlap, HPO-style phenotype match, age/sex fit, family history, labs, variant support, and penalties for missing key features.",
      "The + button loads a simulation scenario into the Intervention tab; it does not recommend treatment.",
    ],
    examples: [],
  },
  known: {
    summary: "Explains how this patient-specific version of a known disease may differ from a textbook description.",
    details: [
      "The model uses symptoms, labs, family history, lifestyle, variants, BioScale outputs, pathway burden, and missing-data notes.",
      "It personalizes mechanism and uncertainty; it does not re-diagnose the disease.",
    ],
    examples: [],
  },
  graph: {
    summary: "Links raw symptoms to HPO-style phenotype terms, candidate diseases, genes, pathways, and tissues.",
    details: ["This graph is educational and uses local fallback mappings when live ontology/database adapters are unavailable."],
    examples: [],
  },
  reasoning: {
    summary: "Shows evidence sources, local fallback assumptions, limitations, and safety warnings.",
    details: ["Raw evidence is collapsible so the main page stays readable.", "Emergency red flags are shown separately because the simulator cannot rule out urgent conditions."],
    examples: [],
  },
};

function fieldPayload(profile: Profile, disease: string, gene: string, mutation: string, protein: string, pathway: string, baseline: SimulationResult | null, mode: Mode) {
  return {
    mode,
    disease: mode === "known" ? disease : "",
    gene: mode === "known" ? gene : "",
    mutation: mode === "known" ? mutation : "",
    protein,
    pathway,
    symptoms: profile.symptoms,
    age: profile.age,
    sex: profile.sex,
    ethnicity: profile.ethnicity || null,
    ancestry: profile.ethnicity || null,
    weight_kg: profile.weight,
    height_cm: profile.height,
    medical_conditions: list(profile.conditions),
    family_history: list(profile.family),
    known_diagnoses: list(profile.diagnoses),
    smoking: profile.smoking,
    alcohol_units_week: profile.alcohol,
    exercise_minutes_week: profile.exercise,
    diet_quality: profile.diet,
    medications: list(profile.medications),
    genes: [gene, ...list(profile.genes)].filter(Boolean),
    mutations: [mutation, ...list(profile.mutations)].filter(Boolean),
    variants: list(profile.variants),
    laboratory_values: { crp: profile.crp, glucose: profile.glucose },
    baseline: baseline ? {
      ecosystem_risk: baseline.ecosystem_result.ecosystem_risk_score,
      mutated_fraction: baseline.population_result.final_mutated_fraction,
      protein_activity: baseline.protein_effect.activity,
      repair_capacity: baseline.cell_phenotype.repair_capacity,
      proliferation: baseline.cell_phenotype.proliferation_rate,
      immune_clearance: baseline.ecosystem_result.immune_clearance,
    } : {},
  };
}

function scenarioFromRow(row: DifferentialDiseaseRow): TwinInterventionScenario {
  return {
    selected_disease: row.disease,
    disease_category: row.disease_category,
    matching_symptoms: row.matching_symptoms ?? [],
    suspected_mechanisms: [row.real_world_causes_mechanism],
    relevant_genes: row.genes ?? [],
    relevant_pathways: row.pathways ?? [],
    evidence_sources: row.evidence_sources ?? [],
    confidence_score: row.confidence,
    suggested_intervention_categories: row.intervention_categories ?? ["Generic mechanism-based intervention"],
    suggested_drug_options: row.suggested_drug_options ?? [],
    note: row.intervention_note ?? "Simulation categories only; not treatment advice.",
  };
}

function ScenarioButton({ row, onLoad }: { row: DifferentialDiseaseRow; onLoad: (scenario: TwinInterventionScenario) => void }) {
  const categories = row.intervention_categories?.length ? row.intervention_categories : ["Generic mechanism-based intervention"];
  return (
    <span className="scenarioButtonWrap">
      <button type="button" className="scenarioAddButton" aria-label={`Load ${row.disease} into Intervention Simulator`} onClick={() => onLoad(scenarioFromRow(row))}>+</button>
      <span className="scenarioPopover" role="tooltip">
        <strong>Simulation intervention categories</strong>
        {categories.map((category) => <span key={category}>{category}</span>)}
        <em>{row.intervention_note ?? "These are simulation categories, not treatment advice."}</em>
      </span>
    </span>
  );
}

function DifferentialTable({ rows, onLoad }: { rows: DifferentialDiseaseRow[]; onLoad: (scenario: TwinInterventionScenario) => void }) {
  return (
    <div className="twinTableWrap">
      <table className="twinRiskTable">
        <thead>
          <tr>
            <th>Rank</th><th>Disease</th><th>Disease Category</th><th>Real-World Causes / Mechanism</th>
            <th>Matching Symptoms</th><th>Missing / Unconfirmed Key Symptoms</th><th>Patient Risk Factors</th>
            <th>Evidence Sources</th><th>Confidence</th><th>Why Ranked Here</th><th>Test Interventions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.rank}-${row.disease}`}>
              <td>{row.rank}</td>
              <td><strong>{row.disease}</strong></td>
              <td>{row.disease_category}</td>
              <td>{row.real_world_causes_mechanism}</td>
              <td>{row.matching_symptoms.join(", ") || "No direct symptom match"}</td>
              <td>{row.missing_or_unconfirmed_key_symptoms.join(", ")}</td>
              <td>{row.patient_risk_factors_that_support_it.join(", ")}</td>
              <td>{row.evidence_sources.join(", ")}</td>
              <td>{Math.round(row.confidence * 100)}%</td>
              <td>{row.why_ranked_here}</td>
              <td><ScenarioButton row={row} onLoad={onLoad} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PatientDigitalTwin({
  apiBase,
  baseline,
  disease,
  gene,
  mutation,
  protein,
  pathway,
  onResult,
  onInterventionScenario,
}: {
  apiBase: string;
  baseline: SimulationResult | null;
  disease: string;
  gene: string;
  mutation: string;
  protein: string;
  pathway: string;
  onResult?: (result: DigitalTwinResult | null) => void;
  onInterventionScenario?: (scenario: TwinInterventionScenario) => void;
}) {
  const [mode, setMode] = useState<Mode>("known");
  const [profile, setProfile] = useState<Profile>(initial);
  const [output, setOutput] = useState<DigitalTwinResult | null>(null);
  const [loadedMessage, setLoadedMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const update = (key: keyof Profile, value: string | number) => setProfile((current) => ({ ...current, [key]: value }));
  const rows = useMemo(() => output?.differential_diagnosis ?? [], [output]);

  async function run() {
    if (!profile.symptoms.trim()) {
      setError("Symptoms are required for the Patient Digital Twin.");
      return;
    }
    setLoading(true); setError(null); setLoadedMessage(null);
    try {
      const endpoint = mode === "known" ? "/api/patient-digital-twin/known-disease-model" : "/api/patient-digital-twin/rank-diseases";
      const response = await fetch(`${apiBase}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fieldPayload(profile, disease, gene, mutation, protein, pathway, baseline, mode)),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Patient digital twin simulation failed");
      setOutput(payload);
      onResult?.(payload);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Patient digital twin simulation failed");
    } finally {
      setLoading(false);
    }
  }

  function loadScenario(scenario: TwinInterventionScenario) {
    onInterventionScenario?.(scenario);
    setLoadedMessage(`Loaded ${scenario.selected_disease} into Intervention Simulator`);
  }

  return <div className="grid secondarySimulator digitalTwin">
    <SimulatorPanel title="Patient Digital Twin" eyebrow="Patient-specific biological modeling" help={twinHelp.profile}>
      <div className="modeSelector" aria-label="Patient digital twin mode">
        <button type="button" className={mode === "known" ? "active" : ""} onClick={() => setMode("known")}>Known disease</button>
        <button type="button" className={mode === "unknown" ? "active" : ""} onClick={() => setMode("unknown")}>Unknown illness</button>
      </div>
      <p className="panelExplanation">
        {mode === "known"
          ? "Known disease mode personalizes a diagnosis you already know. It models severity, mechanism, pathway burden, progression risk, and intervention-response hypotheses."
          : "Unknown illness mode does not require disease, gene, or mutation. It ranks possible diseases from symptoms, history, labs, family history, medications, lifestyle, and variants."}
      </p>
      <div className="contextStrip"><span>Disease <b>{mode === "known" ? disease || "Known diagnosis" : "Not required"}</b></span><span>Gene <b>{mode === "known" ? gene || "Optional" : "Optional"}</b></span><span>Mutation <b>{mode === "known" ? mutation || "Optional" : "Optional"}</b></span><span>Protein <b>{protein || "Optional"}</b></span></div>
      <div className="profileGrid">
        <label className="wideField">Symptoms (required)<textarea value={profile.symptoms} placeholder="e.g. fatigue, fever, rash, joint pain" onChange={(e) => update("symptoms", e.target.value)} /></label>
        <label>Age<input type="number" value={profile.age} onChange={(e) => update("age", Number(e.target.value))} /></label>
        <label>Sex<select value={profile.sex} onChange={(e) => update("sex", e.target.value)}><option>unspecified</option><option>female</option><option>male</option><option>intersex</option></select></label>
        <label>Ancestry / ethnicity (optional)<input value={profile.ethnicity} onChange={(e) => update("ethnicity", e.target.value)} /></label>
        <label>Weight (kg)<input type="number" value={profile.weight} onChange={(e) => update("weight", Number(e.target.value))} /></label>
        <label>Height (cm)<input type="number" value={profile.height} onChange={(e) => update("height", Number(e.target.value))} /></label>
        <label>Smoking<select value={profile.smoking} onChange={(e) => update("smoking", e.target.value)}><option>never</option><option>former</option><option>current</option></select></label>
        <label>Known diagnoses<input placeholder="comma-separated" value={profile.diagnoses} onChange={(e) => update("diagnoses", e.target.value)} /></label>
        <label>Family history<input placeholder="comma-separated" value={profile.family} onChange={(e) => update("family", e.target.value)} /></label>
        <label>Medications<input placeholder="comma-separated" value={profile.medications} onChange={(e) => update("medications", e.target.value)} /></label>
        <label>Known conditions<input placeholder="comma-separated" value={profile.conditions} onChange={(e) => update("conditions", e.target.value)} /></label>
        <label>Exercise minutes / week<input type="number" value={profile.exercise} onChange={(e) => update("exercise", Number(e.target.value))} /></label>
        <label>Diet quality (0-1)<input type="number" min="0" max="1" step="0.05" value={profile.diet} onChange={(e) => update("diet", Number(e.target.value))} /></label>
        <label>Alcohol units / week<input type="number" value={profile.alcohol} onChange={(e) => update("alcohol", Number(e.target.value))} /></label>
        <label>Genes / variants<input placeholder="e.g. BRCA1, CFTR" value={profile.genes} onChange={(e) => update("genes", e.target.value)} /></label>
        <label>Mutations<input placeholder="comma-separated" value={profile.mutations} onChange={(e) => update("mutations", e.target.value)} /></label>
        <label>Genetic variants optional<input placeholder="rsID, HGVS, VCF notes" value={profile.variants} onChange={(e) => update("variants", e.target.value)} /></label>
        <label>CRP optional<input type="number" value={profile.crp} onChange={(e) => update("crp", Number(e.target.value))} /></label>
        <label>Glucose optional<input type="number" value={profile.glucose} onChange={(e) => update("glucose", Number(e.target.value))} /></label>
      </div>
      <button className="primaryAction" onClick={() => void run()} disabled={loading}>{loading ? "Building twin..." : mode === "known" ? "Build known-disease twin" : "Rank possible diseases"}</button>
      {error && <p className="error">{error}</p>}
    </SimulatorPanel>

    {!output ? <div className="emptyState wideEmpty">Enter symptoms and profile context to generate a patient digital twin.</div> : <>
      {output.safety_warnings?.length ? <SimulatorPanel title="Safety Notice" eyebrow="Urgent-care warning" help={twinHelp.reasoning}>
        {output.safety_warnings.map((warning) => <p className="errorBoundary" key={warning}>{warning}</p>)}
        <p className="researchDisclaimer">This simulator cannot safely rule out urgent illness. Seek qualified medical evaluation for emergency symptoms.</p>
      </SimulatorPanel> : null}

      {mode === "known" && <SimulatorPanel title="Known Disease Model" eyebrow="Patient-specific mechanism" help={twinHelp.known}>
        <div className="knownPanelGrid">
          {Object.entries(output.known_disease_panels ?? {}).map(([title, text]) => <article key={title}><h3>{title}</h3><p>{text}</p></article>)}
        </div>
      </SimulatorPanel>}

      <SimulatorPanel title={mode === "known" ? "Known Disease Intervention Scenario" : "Top-20 Disease Risk Profile"} eyebrow={mode === "known" ? "Transferable simulation scenario" : "Differential disease ranking"} help={twinHelp.differential}>
        {rows.length ? <DifferentialTable rows={rows} onLoad={loadScenario} /> : <p className="panelExplanation">No ranked diseases returned.</p>}
        {loadedMessage && <p className="successNotice">{loadedMessage}</p>}
      </SimulatorPanel>

      <SimulatorPanel title="Phenotype and Disease Graph" eyebrow="D3 biological links" help={twinHelp.graph}>
        <ForceGraph nodes={output.graph?.nodes ?? []} links={output.graph?.links ?? []} title="Symptoms -> phenotypes -> diseases -> genes/pathways" description="HPO terms are phenotype labels used to connect symptoms to disease biology." />
        <p className="panelExplanation">HPO terms are standardized phenotype descriptions. Differential diagnosis means a ranked list of possible explanations, not a final diagnosis.</p>
      </SimulatorPanel>

      <SimulatorPanel title="Disease Category Distribution" eyebrow="D3 category view" help={twinHelp.graph}>
        <CirclePackingChart data={output.category_distribution ?? { name: "Disease categories", children: [] }} title="Candidate category distribution" description="Circle size follows confidence weight by disease category." />
      </SimulatorPanel>

      <SimulatorPanel title="Patient-Specific Readouts" eyebrow="Digital twin state" help={twinHelp.known}>
        <div className="metricGrid">
          <MetricCard label="Overall modeled pressure" value={output.predicted_biological_state.overall_risk} before={baseline?.ecosystem_result.ecosystem_risk_score ?? 0.5} context="This combines patient profile, symptoms, BioScale baseline when available, labs, and risk modifiers." />
          <MetricCard label="Model confidence" value={output.confidence} before={0.5} context="Confidence reflects how much structured evidence was available for this run." />
          <MetricCard label="Symptom terms" value={output.normalized_symptoms?.length ?? 0} context="Number of raw symptoms normalized into HPO-style phenotype terms." />
          <MetricCard label="State" value={output.predicted_biological_state.status} context="Readable state assigned to the modeled patient-specific pressure." />
        </div>
      </SimulatorPanel>

      <SimulatorPanel title="Evidence, Missing Data, and Reasoning" eyebrow="Transparent educational notes" help={twinHelp.reasoning}>
        <div className="systemTags">{(output.normalized_symptoms ?? []).map((item) => <span key={`${item.id}-${item.raw}`}>{item.label} <small>{item.id}</small></span>)}</div>
        <ol className="twinReasoning">{output.reasoning.map((reason) => <li key={reason}>{reason}</li>)}</ol>
        {output.missing_data?.length ? <div className="modelNote"><strong>Data that would improve the twin</strong><p>{output.missing_data.join("; ")}</p></div> : null}
        <details className="rawEvidence">
          <summary>View evidence sources</summary>
          <div className="evidenceList">{output.evidence.map((item) => <div key={`${item.source}-${item.category}-${item.detail}`}><ProvenanceBadge category={item.category === "computed" ? "computed_model" : item.category === "local fallback" ? "local_curated" : item.category === "missing evidence" ? "missing_evidence" : "simulator_assumption"} source={item.source} /><span>{item.detail}</span></div>)}</div>
        </details>
        <p className="researchDisclaimer">{output.disclaimer}</p>
      </SimulatorPanel>
    </>}
  </div>;
}
