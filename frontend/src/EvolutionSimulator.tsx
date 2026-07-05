import { useEffect, useState } from "react";
import type { EvolutionResult, SimulationResult } from "./types";
import { CloneBadge, MetricCard, MiniLineChart, SimulatorPanel } from "./SimulatorUI";

type Setup = { initialPopulation: number; startingFraction: number; mutationRate: number; immunePressure: number; nutrientLevel: number; stressLevel: number };
const initialSetup: Setup = { initialPopulation: 10000, startingFraction: 0.02, mutationRate: 0.04, immunePressure: 0.55, nutrientLevel: 0.75, stressLevel: 0.35 };

function Slider({ label, value, min = 0, max = 1, step = 0.01, onChange }: { label: string; value: number; min?: number; max?: number; step?: number; onChange: (value: number) => void }) {
  return <label className="simSlider"><span>{label}<strong>{value.toLocaleString()}</strong></span><input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

export function EvolutionSimulator({ apiBase, result, disease, gene, mutation, steps, onResult }: { apiBase: string; result: SimulationResult | null; disease: string; gene: string; mutation: string; steps: number; onResult: (result: EvolutionResult | null) => void }) {
  const [setup, setSetup] = useState<Setup>(initialSetup);
  const [evolution, setEvolution] = useState<EvolutionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (key: keyof Setup, value: number) => setSetup((current) => ({ ...current, [key]: value }));
  async function run() {
    if (!disease || !gene || !mutation) return;
    setLoading(true); setError(null);
    try {
      const response = await fetch(`${apiBase}/api/evolution`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        disease, gene, mutation, steps, initial_population: setup.initialPopulation, starting_mutated_fraction: setup.startingFraction,
        mutation_rate: setup.mutationRate, immune_pressure: setup.immunePressure, nutrient_level: setup.nutrientLevel, stress_level: setup.stressLevel,
        protein_activity: result?.protein_effect.activity ?? 0.5, protein_stability: result?.protein_effect.stability ?? 0.5,
        repair_capacity: result?.cell_phenotype.repair_capacity ?? 0.5,
      }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Evolution simulation failed");
      setEvolution(payload); onResult(payload);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Evolution simulation failed"); }
    finally { setLoading(false); }
  }
  useEffect(() => { setEvolution(null); onResult(null); }, [disease, gene, mutation, steps]);
  return <div className="grid secondarySimulator">
    <SimulatorPanel title="Evolution Setup" eyebrow="Clone evolution inputs">
      <div className="contextStrip"><span>Disease <b>{disease || "Not selected"}</b></span><span>Gene <b>{gene || "Not selected"}</b></span><span>Mutation <b>{mutation || "Not selected"}</b></span><span>Steps <b>{steps}</b></span></div>
      <div className="sliderGrid">
        <Slider label="Initial population size" min={100} max={100000} step={100} value={setup.initialPopulation} onChange={(v) => set("initialPopulation", v)} />
        <Slider label="Starting mutated fraction" value={setup.startingFraction} onChange={(v) => set("startingFraction", v)} />
        <Slider label="Mutation rate" value={setup.mutationRate} onChange={(v) => set("mutationRate", v)} />
        <Slider label="Immune pressure" value={setup.immunePressure} onChange={(v) => set("immunePressure", v)} />
        <Slider label="Nutrient level" value={setup.nutrientLevel} onChange={(v) => set("nutrientLevel", v)} />
        <Slider label="Stress level" value={setup.stressLevel} onChange={(v) => set("stressLevel", v)} />
      </div>
      <button className="primaryAction" onClick={() => void run()} disabled={loading || !disease || !gene || !mutation}>{loading ? "Computing evolution…" : "Run evolution simulation"}</button>
      {error && <p className="error">{error}</p>}
    </SimulatorPanel>
    {!evolution ? <div className="emptyState wideEmpty">Set the selection pressures, then run the evolution simulation.</div> : <>
      <SimulatorPanel title="Clone Overview" eyebrow="Computed clone traits">
        <div className="cloneGrid">{evolution.clones.map((clone) => <article className="cloneCard" key={clone.name}><CloneBadge name={clone.name} fitness={clone.fitness_score} /><p><b>Parent:</b> {clone.parent ?? "Starting clone"}</p><p><b>Mutations:</b> {clone.mutations.join(" · ")}</p><div className="miniMetricGrid"><MetricCard label="Growth" value={clone.growth_rate} /><MetricCard label="Death" value={clone.death_rate} /><MetricCard label="Repair" value={clone.repair_ability} /><MetricCard label="Stress resistance" value={clone.stress_resistance} /><MetricCard label="Immune evasion" value={clone.immune_evasion} /></div></article>)}</div>
      </SimulatorPanel>
      <SimulatorPanel title="Selection Pressures" eyebrow="Environment">
        <div className="metricGrid"><MetricCard label="Immune pressure" value={setup.immunePressure} /><MetricCard label="Nutrients" value={setup.nutrientLevel} /><MetricCard label="Stress" value={setup.stressLevel} /><MetricCard label="DNA damage pressure" value={1 - (result?.protein_effect.stability ?? 0.5)} /></div><p className="panelExplanation">Clones with traits that produce higher fitness under these conditions expand, while weaker clones shrink.</p>
      </SimulatorPanel>
      <SimulatorPanel title="Clone Population Timeline" eyebrow="Computed simulator output">
        <MiniLineChart ariaLabel="Clone fractions over time" series={[{ name: "Clone A", color: "#237457", points: evolution.timeline.map((p) => ({ x: p.step, y: p.clone_a })) }, { name: "Clone B", color: "#d18b3f", points: evolution.timeline.map((p) => ({ x: p.step, y: p.clone_b })) }, { name: "Clone C", color: "#a34f58", points: evolution.timeline.map((p) => ({ x: p.step, y: p.clone_c })) }]} />
      </SimulatorPanel>
      <SimulatorPanel title="Evolution Tree" eyebrow="Lineage model"><div className="evolutionTree"><div className="treeParent">Clone A<small>{gene} {mutation}</small></div><div className="treeStem" /><div className="treeChildren"><div>Clone B<small>stress-adapted child</small></div><div>Clone C<small>immune-evasive child</small></div></div></div></SimulatorPanel>
      <SimulatorPanel title="Evolution Summary" eyebrow="Outcome"><div className="metricGrid"><MetricCard label="Dominant clone" value={evolution.summary.dominant_clone} /><MetricCard label="Diversity score" value={evolution.summary.diversity_score} /><MetricCard label="Clonal expansion" value={evolution.summary.clonal_expansion ? "Occurred" : "Limited"} />{Object.entries(evolution.summary.final_clone_fractions).map(([name, value]) => <MetricCard key={name} label={`${name} final fraction`} value={value} />)}</div><p className="panelExplanation">{evolution.summary.explanation}</p><p className="researchDisclaimer">{evolution.disclaimer}</p></SimulatorPanel>
    </>}
  </div>;
}
