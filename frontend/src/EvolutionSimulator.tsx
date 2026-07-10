import { useEffect, useMemo, useState } from "react";
import type { EvolutionClone, EvolutionResult, EvolutionTimelinePoint, SimulationResult } from "./types";
import { CloneBadge, MetricCard, SimulatorPanel } from "./SimulatorUI";
import { TimelineChart, type TimelineSeries } from "./components/visualizations/TimelineChart";
import { CloneTree } from "./components/visualizations/CloneTree";
import { CirclePackingChart } from "./components/visualizations/CirclePackingChart";

type Setup = {
  initialPopulation: number;
  startingFraction: number;
  mutationRate: number;
  immunePressure: number;
  nutrientLevel: number;
  stressLevel: number;
  maxCloneCount: number;
};

const initialSetup: Setup = {
  initialPopulation: 10000,
  startingFraction: 0.02,
  mutationRate: 0.04,
  immunePressure: 0.55,
  nutrientLevel: 0.75,
  stressLevel: 0.35,
  maxCloneCount: 6,
};

const evolutionHelp = {
  setup: {
    summary: "Configures an evidence-guided clone trajectory model. These are simulated clone hypotheses, not confirmed future clones.",
    details: [
      "A clone is a genetically related cell population descended from an earlier population.",
      "Clones can gain additional mutations or biological developments over time, such as immune evasion, repair loss, or nutrient efficiency.",
      "Clone emergence is estimated from mutation rate, genomic instability, pathway disruption, population size, and selection pressures.",
      "The model cannot know the future with certainty; longitudinal sequencing or single-cell lineage data would be needed to validate real clone behavior.",
      "Database evidence is used when available; otherwise the output is labeled as a simulator assumption.",
    ],
    examples: [],
  },
  clones: {
    summary: "Shows every generated clone, its parent, inherited biology, new development, final share, and clone-specific reasoning.",
    details: [
      "Every clone shown here is model-generated unless longitudinal sequencing confirms it.",
      "Green/red metric bars show whether the current value is above or below the reference value used by the model.",
    ],
    examples: [],
  },
  selection: {
    summary: "Shows environmental pressures that select for or against clones.",
    details: [
      "High immune pressure favors immune-evasive clones.",
      "High nutrient stress favors nutrient-efficiency clones.",
      "High stress and low repair favor stress-resistance or repair-loss clone hypotheses.",
    ],
    examples: [],
  },
  timeline: {
    summary: "Shows every clone fraction over time. All clones are visible by default and can be toggled on or off.",
    details: [
      "Thin or low lines still represent valid simulated clones; they are not hidden by default.",
      "Hover points to inspect step, clone fraction, population size, and major events.",
    ],
    examples: [],
  },
  tree: {
    summary: "Shows the actual parent-child order of clone development from the backend model.",
    details: [
      "Clone A is the founding clone. Child clones are placed under their parent and ordered by generation step.",
      "Hover for full clone details; click a node to focus the matching clone card.",
    ],
    examples: [],
  },
  composition: {
    summary: "Shows the final modeled clone mix with percentages printed directly on the clone circles.",
    details: [
      "Circle area follows final modeled clone share.",
      "Very small clones are still included by default; hover a circle to read its exact final share and reasoning.",
    ],
    examples: [],
  },
  events: {
    summary: "Lists major modeled evolution events such as clone emergence, selection, dominance, or decline.",
    details: ["Events are model explanations, not observed clinical events."],
    examples: [],
  },
  certainty: {
    summary: "Explains model limits and what evidence would be needed to validate clone predictions.",
    details: [
      "The simulator generates plausible trajectories from current biological inputs.",
      "Exact real clone forecasts require longitudinal tissue sampling, single-cell sequencing, or patient cohort data.",
    ],
    examples: [],
  },
};

function Slider({
  label,
  value,
  min = 0,
  max = 1,
  step = 0.01,
  onChange,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="simSlider">
      <span>{label}<strong>{value.toLocaleString()}</strong></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

function fmt(value: number) {
  return Number.isFinite(value) ? value.toFixed(2) : "—";
}

function inferDiseaseCategory(disease: string) {
  const text = disease.toLowerCase();
  return text.includes("cancer") || text.includes("tumor") || text.includes("tumour") || text.includes("carcinoma") ? "cancer" : "general";
}

function cloneIdFromName(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function timelineSeries(evolution: EvolutionResult): TimelineSeries[] {
  return evolution.clones.map((clone) => ({
    id: clone.clone_id || cloneIdFromName(clone.name),
    label: clone.clone_name || clone.name,
    description: clone.new_mutation_or_development,
    values: evolution.timeline.map((point: EvolutionTimelinePoint) => ({
      step: point.step,
      value: point.clone_fractions?.[clone.clone_name || clone.name] ?? point.clone_fractions?.[clone.name] ?? 0,
      population: point.clone_populations?.[clone.clone_name || clone.name] ?? point.clone_populations?.[clone.name],
      event: point.major_events?.join(" "),
    })),
  }));
}

function compositionData(evolution: EvolutionResult) {
  return evolution.final_composition ?? evolution.clone_composition ?? {
    name: "Final clone composition",
    type: "composition",
    children: evolution.clones.map((clone) => ({
      id: clone.clone_id,
      name: clone.clone_name || clone.name,
      type: clone.new_mutation_or_development,
      value: clone.final_share ?? evolution.summary.final_clone_fractions[clone.name] ?? 0,
      description: clone.why_it_expanded_or_declined,
      details: clone,
    })),
  };
}

function treeData(evolution: EvolutionResult) {
  return evolution.clone_tree ?? {
    id: evolution.clones[0]?.clone_id,
    name: evolution.clones[0]?.clone_name || "Clone A",
    value: evolution.clones[0]?.final_share ?? 0,
    details: evolution.clones[0],
    children: evolution.clones.filter((clone) => clone.parent_clone_id === evolution.clones[0]?.clone_id).map((clone) => ({
      id: clone.clone_id,
      name: clone.clone_name,
      value: clone.final_share,
      description: clone.biological_interpretation,
      details: clone,
    })),
  };
}

function CloneReasoning({ clone }: { clone: EvolutionClone }) {
  return (
    <div className="cloneReasoning">
      <strong>Clone-specific reasoning</strong>
      <p>{clone.why_it_emerged}</p>
      <p>{clone.why_it_expanded_or_declined}</p>
      <p>{clone.biological_interpretation}</p>
      <p><b>Evidence basis:</b> {clone.evidence_basis}</p>
      {clone.missing_evidence.length > 0 && <p><b>Missing evidence:</b> {clone.missing_evidence.join("; ")}</p>}
    </div>
  );
}

export function EvolutionSimulator({
  apiBase,
  result,
  disease,
  gene,
  mutation,
  steps,
  onResult,
}: {
  apiBase: string;
  result: SimulationResult | null;
  disease: string;
  gene: string;
  mutation: string;
  steps: number;
  onResult: (result: EvolutionResult | null) => void;
}) {
  const [setup, setSetup] = useState<Setup>(initialSetup);
  const [evolution, setEvolution] = useState<EvolutionResult | null>(null);
  const [selectedCloneId, setSelectedCloneId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (key: keyof Setup, value: number) => setSetup((current) => ({ ...current, [key]: value }));

  useEffect(() => {
    if (!selectedCloneId) return;
    document.getElementById(`clone-card-${selectedCloneId}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [selectedCloneId]);

  async function run() {
    if (!disease || !gene || !mutation) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}/api/evolution/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          disease,
          disease_category: inferDiseaseCategory(disease),
          gene,
          mutation,
          steps,
          max_clone_count: setup.maxCloneCount,
          initial_population: setup.initialPopulation,
          starting_affected_fraction: setup.startingFraction,
          starting_mutated_fraction: setup.startingFraction,
          mutation_rate: setup.mutationRate,
          immune_pressure: setup.immunePressure,
          nutrient_level: setup.nutrientLevel,
          stress_level: setup.stressLevel,
          dna_damage_pressure: 1 - (result?.protein_effect.stability ?? 0.5),
          protein_activity: result?.protein_effect.activity ?? 0.5,
          protein_stability: result?.protein_effect.stability ?? 0.5,
          repair_capacity: result?.cell_phenotype.repair_capacity ?? 0.5,
          protein_effect: result?.protein_effect ?? {},
          alphafold_context: {
            alphafold_available: result?.simulation_input.alphafold_available,
            confidence_label: result?.simulation_input.alphafold_confidence_label,
            uniprot_accession: result?.simulation_input.uniprot_accession,
          },
          pathway_graph: result?.pathway_result ?? {},
          pathway_node_activity: result?.pathway_result.node_activities ?? {},
          cell_phenotype: result?.cell_phenotype ?? {},
          population_state: result?.population_result ?? {},
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Evolution simulation failed");
      setEvolution(payload);
      setSelectedCloneId(payload.clones?.[0]?.clone_id ?? null);
      onResult(payload);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Evolution simulation failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setEvolution(null);
    setSelectedCloneId(null);
    onResult(null);
  }, [disease, gene, mutation, steps, setup.maxCloneCount]);

  const series = useMemo(() => (evolution ? timelineSeries(evolution) : []), [evolution]);

  return (
    <div className="grid secondarySimulator">
      <SimulatorPanel title="Evolution Setup" eyebrow="Clone evolution inputs" help={evolutionHelp.setup}>
        <div className="contextStrip">
          <span>Disease <b>{disease || "Not selected"}</b></span>
          <span>Gene <b>{gene || "Not selected"}</b></span>
          <span>Mutation <b>{mutation || "Not selected"}</b></span>
          <span>Steps <b>{steps}</b></span>
        </div>
        <p className="panelExplanation">
          These are evidence-guided simulated clone trajectories, not confirmed future clones. A clone is a genetically related cell population descended from an earlier population.
        </p>
        <div className="sliderGrid">
          <Slider label="Max simulated clones" min={3} max={20} step={1} value={setup.maxCloneCount} onChange={(v) => set("maxCloneCount", v)} />
          <Slider label="Initial population size" min={100} max={100000} step={100} value={setup.initialPopulation} onChange={(v) => set("initialPopulation", v)} />
          <Slider label="Starting affected fraction" value={setup.startingFraction} onChange={(v) => set("startingFraction", v)} />
          <Slider label="Mutation pressure" value={setup.mutationRate} onChange={(v) => set("mutationRate", v)} />
          <Slider label="Immune pressure" value={setup.immunePressure} onChange={(v) => set("immunePressure", v)} />
          <Slider label="Nutrient level" value={setup.nutrientLevel} onChange={(v) => set("nutrientLevel", v)} />
          <Slider label="Stress level" value={setup.stressLevel} onChange={(v) => set("stressLevel", v)} />
        </div>
        <button className="primaryAction" onClick={() => void run()} disabled={loading || !disease || !gene || !mutation}>
          {loading ? "Computing evolution..." : "Run evolution simulation"}
        </button>
        {error && <p className="error">{error}</p>}
      </SimulatorPanel>

      {!evolution ? <div className="emptyState wideEmpty">Set the selection pressures, then run the evolution simulation.</div> : <>
        <SimulatorPanel title="Clone Overview" eyebrow="Evidence-guided clone hypotheses" help={evolutionHelp.clones}>
          <div className="cloneGrid">
            {evolution.clones.map((clone) => {
              const reference = clone.parent_clone_id ? evolution.clones.find((candidate) => candidate.clone_id === clone.parent_clone_id) : null;
              const selected = selectedCloneId === clone.clone_id;
              return (
                <article id={`clone-card-${clone.clone_id}`} className={selected ? "cloneCard selectedCloneCard" : "cloneCard"} key={clone.clone_id}>
                  <CloneBadge name={clone.clone_name || clone.name} fitness={clone.fitness_score} />
                  <p><b>Parent:</b> {clone.parent || "Founding clone"} · <b>Generation step:</b> {clone.generation_step}</p>
                  <p><b>Inherited:</b> {clone.inherited_mutations.join(" · ")}</p>
                  <p><b>New development:</b> {clone.new_mutation_or_development}</p>
                  <div className="miniMetricGrid">
                    <MetricCard label="Final share" value={clone.final_share} before={clone.starting_share} context={`${clone.clone_name} final share is the modeled fraction of the affected clone population at the end of the simulation.`} />
                    <MetricCard label="Fitness score" value={clone.fitness_score} before={reference?.fitness_score ?? 0.5} context="Fitness combines growth, death resistance, immune evasion, stress resistance, nutrient efficiency, repair state, and pathway disruption." />
                    <MetricCard label="Growth advantage" value={clone.growth_rate} before={reference?.growth_rate ?? 0.5} context={`${clone.clone_name} growth advantage is the modeled probability that this clone keeps dividing under current nutrient and protein-activity conditions.`} />
                    <MetricCard label="Survival/death resistance" value={1 - clone.death_rate} before={reference ? 1 - reference.death_rate : 0.5} context="Survival/death resistance is one minus the modeled death/removal rate." />
                    <MetricCard label="Repair/homeostasis capacity" value={clone.repair_capacity ?? clone.repair_ability} before={reference?.repair_capacity ?? result?.cell_phenotype.repair_capacity ?? 0.5} context="Repair/homeostasis capacity is the modeled ability to correct damage or preserve normal state." />
                    <MetricCard label="Immune evasion" value={clone.immune_evasion} before={reference?.immune_evasion ?? 0.5} context="Immune evasion is the modeled probability that this clone avoids immune clearance." />
                    <MetricCard label="Stress/nutrient adaptation" value={(clone.stress_resistance + clone.nutrient_efficiency) / 2} before={reference ? (reference.stress_resistance + reference.nutrient_efficiency) / 2 : 0.5} context="Stress/nutrient adaptation averages stress resistance and nutrient efficiency for the current environment." />
                    <MetricCard label="Confidence" value={clone.confidence_score} before={0.5} context="Confidence reflects available evidence plus how directly the clone is connected to upstream BioScale outputs." />
                  </div>
                  <CloneReasoning clone={clone} />
                </article>
              );
            })}
          </div>
        </SimulatorPanel>

        <SimulatorPanel title="Selection Pressures" eyebrow="Environment" help={evolutionHelp.selection}>
          <div className="metricGrid">
            <MetricCard label="Immune pressure" value={setup.immunePressure} before={0.5} context="Immune pressure favors immune-evasive clones and selects against clones that remain visible to immune clearance." />
            <MetricCard label="Nutrients" value={setup.nutrientLevel} before={0.5} context="Nutrient level supports clone growth; low nutrients make nutrient-efficiency developments more plausible." />
            <MetricCard label="Stress" value={setup.stressLevel} before={0.5} context="Stress favors stress-resistant clones and can limit less adapted clones." />
            <MetricCard label="DNA damage pressure" value={1 - (result?.protein_effect.stability ?? 0.5)} before={0.5} context="DNA damage pressure is inferred from reduced protein stability and cell repair capacity in the BioScale baseline." />
          </div>
          <p className="panelExplanation">Clones with traits that produce higher fitness under these conditions expand; weaker or poorly adapted clones shrink or remain minor.</p>
        </SimulatorPanel>

        <SimulatorPanel title="Clone Fraction Timeline" eyebrow="All clones over time" help={evolutionHelp.timeline}>
          <TimelineChart series={series} title="Clone fraction over time" yLabel="fraction" />
        </SimulatorPanel>

        <SimulatorPanel title="Evolution Tree" eyebrow="Parent-child clone order" help={evolutionHelp.tree}>
          <CloneTree data={treeData(evolution)} title={`${gene} ${mutation} clone lineage`} onSelect={setSelectedCloneId} />
        </SimulatorPanel>

        <SimulatorPanel title="Final Clone Composition" eyebrow="D3 clone map" help={evolutionHelp.composition}>
          <CirclePackingChart data={compositionData(evolution)} title="Final clone composition" description="Circle area follows final modeled clone share; percentages are shown directly on circles where space allows." />
        </SimulatorPanel>

        <SimulatorPanel title="Evolution Events" eyebrow="Modeled event log" help={evolutionHelp.events}>
          <ol className="evolutionEvents">
            {(evolution.major_events ?? []).map((event) => (
              <li key={`${event.step}-${event.clone_id}-${event.event_type}`}>
                <span>Step {event.step}</span>
                <strong>{event.clone_name}</strong>
                <p>{event.description}</p>
              </li>
            ))}
          </ol>
        </SimulatorPanel>

        <SimulatorPanel title="Evidence and Assumptions" eyebrow="Database awareness">
          <div className="evidenceAssumptionGrid">
            <div>
              <h3>Evidence used</h3>
              <p>{evolution.evidence_summary?.sources_used?.length ? evolution.evidence_summary.sources_used.join(", ") : "No direct database evidence found; clone generation used upstream model logic."}</p>
            </div>
            <div>
              <h3>Model assumptions</h3>
              <ul>{(evolution.model_assumptions ?? []).map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
          <details className="rawEvidence">
            <summary>View missing evidence and raw evolution context</summary>
            <pre>{JSON.stringify(evolution.evidence_summary ?? {}, null, 2)}</pre>
          </details>
        </SimulatorPanel>

        <SimulatorPanel title="Model Certainty and Limitations" eyebrow="Scientific framing" help={evolutionHelp.certainty}>
          <p className="panelExplanation">{evolution.student_explanation}</p>
          <p className="researchDisclaimer">{evolution.uncertainty_summary}</p>
          <div className="metricGrid">
            <MetricCard label="Dominant clone" value={evolution.summary.dominant_clone} context="Dominant clone is the modeled lineage with the largest final share." />
            <MetricCard label="Diversity score" value={evolution.summary.diversity_score} before={0.5} context="Diversity score is the probability that the final clone population is split across several clones rather than one clone." />
            <MetricCard label="Model confidence" value={evolution.confidence} before={0.5} context="Model confidence reflects current evidence availability and upstream BioScale context." />
          </div>
          <p className="modelProvenance">Provenance: {evolution.provenance}</p>
          <p className="researchDisclaimer">{evolution.disclaimer}</p>
        </SimulatorPanel>
      </>}
    </div>
  );
}
