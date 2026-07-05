import { useEffect, useState } from "react";
import type { EvolutionResult, InterventionResult, SimulationResult } from "./types";
import { MetricCard, MiniLineChart, SimulatorPanel } from "./SimulatorUI";

const interventionTypes = ["Growth inhibitor", "Apoptosis activator", "Immune booster", "Repair enhancer", "Generic targeted therapy"];

export function InterventionSimulator({ apiBase, baseline, evolution }: { apiBase: string; baseline: SimulationResult | null; evolution: EvolutionResult | null }) {
  const [type, setType] = useState(interventionTypes[0]);
  const [strength, setStrength] = useState(0.5);
  const [target, setTarget] = useState("selected gene/protein");
  const [output, setOutput] = useState<InterventionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { setOutput(null); }, [baseline]);
  if (!baseline) return <div className="grid secondarySimulator"><SimulatorPanel title="Baseline Scenario" eyebrow="Intervention prerequisite"><div className="baselineMissing"><strong>Run the BioScale Simulator first to use its baseline output.</strong><p>The intervention model compares a modified system against protein, cell, population, and ecosystem values from Tab 1.</p></div></SimulatorPanel></div>;

  async function run() {
    if (!baseline) return;
    setLoading(true); setError(null);
    try {
      const response = await fetch(`${apiBase}/api/intervention`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        disease: baseline.simulation_input.disease_name, gene: baseline.simulation_input.gene_symbol, mutation: baseline.simulation_input.mutation,
        intervention_type: type, strength, target,
        baseline_mutated_fraction: baseline.population_result.final_mutated_fraction,
        baseline_ecosystem_risk: baseline.ecosystem_result.ecosystem_risk_score,
        proliferation: baseline.cell_phenotype.proliferation_rate, apoptosis: baseline.cell_phenotype.apoptosis_rate,
        repair_capacity: baseline.cell_phenotype.repair_capacity, immune_clearance: baseline.ecosystem_result.immune_clearance,
        baseline_timeline: baseline.population_result.trajectory, evolution_clones: evolution?.clones ?? [],
      }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Intervention simulation failed");
      setOutput(payload);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Intervention simulation failed"); }
    finally { setLoading(false); }
  }
  const biology = baseline.cell_phenotype;
  const ecosystem = baseline.ecosystem_result;
  return <div className="grid secondarySimulator">
    <SimulatorPanel title="Baseline Scenario" eyebrow="BioScale reference">
      <div className="contextStrip"><span>Disease <b>{baseline.simulation_input.disease_name}</b></span><span>Gene <b>{baseline.simulation_input.gene_symbol}</b></span><span>Mutation <b>{baseline.simulation_input.mutation}</b></span></div>
      <div className="metricGrid"><MetricCard label="Baseline mutated fraction" value={baseline.population_result.final_mutated_fraction} /><MetricCard label="Baseline ecosystem risk" value={ecosystem.ecosystem_risk_score} /></div>
    </SimulatorPanel>
    <SimulatorPanel title="Intervention Selection" eyebrow="External perturbation">
      <div className="interventionControls"><label><span>Intervention type</span><select value={type} onChange={(event) => setType(event.target.value)}>{interventionTypes.map((item) => <option key={item}>{item}</option>)}</select></label><label><span>Target</span><select value={target} onChange={(event) => setTarget(event.target.value)}><option>selected gene/protein</option><option>selected pathway</option><option>dominant clone</option><option>all mutated cells</option></select></label><label className="simSlider"><span>Strength<strong>{strength.toFixed(2)}</strong></span><input type="range" min="0" max="1" step="0.01" value={strength} onChange={(event) => setStrength(Number(event.target.value))} /></label></div>
      <button className="primaryAction" onClick={() => void run()} disabled={loading}>{loading ? "Applying intervention…" : "Apply intervention"}</button>{error && <p className="error">{error}</p>}
    </SimulatorPanel>
    {!output ? <div className="emptyState wideEmpty">Choose an intervention, strength, and target to compute a comparison.</div> : <>
      <SimulatorPanel title="Modified Biology" eyebrow="Computed simulator output"><div className="metricGrid"><MetricCard label="Proliferation" value={output.modified_biology.proliferation} before={biology.proliferation_rate} /><MetricCard label="Apoptosis / death" value={output.modified_biology.apoptosis} before={biology.apoptosis_rate} /><MetricCard label="Repair capacity" value={output.modified_biology.repair_capacity} before={biology.repair_capacity} /><MetricCard label="Immune clearance" value={output.modified_biology.immune_clearance} before={ecosystem.immune_clearance} /><MetricCard label="Ecosystem risk" value={output.modified_biology.ecosystem_risk} before={ecosystem.ecosystem_risk_score} /></div></SimulatorPanel>
      <SimulatorPanel title="Post-Intervention Timeline" eyebrow="Before and after">
        <MiniLineChart ariaLabel="Mutated fraction before and after intervention" series={[{ name: "Baseline", color: "#64746f", points: output.timeline.map((p) => ({ x: p.step, y: p.before })) }, { name: "Post-intervention", color: "#237457", points: output.timeline.map((p) => ({ x: p.step, y: p.after })) }]} />
        {output.clone_response.length > 0 && <div className="cloneResponse"><strong>Clone response</strong>{output.clone_response.map((clone) => <span key={clone.clone}>{clone.clone}: {(clone.suppression * 100).toFixed(0)}% modeled suppression</span>)}</div>}
      </SimulatorPanel>
      <SimulatorPanel title="Outcome Comparison" eyebrow="Computed change"><div className="metricGrid"><MetricCard label="Baseline mutated fraction" value={output.comparison.baseline_mutated_fraction} /><MetricCard label="Post-intervention mutated fraction" value={output.comparison.post_intervention_mutated_fraction} /><MetricCard label="Baseline ecosystem risk" value={output.comparison.baseline_ecosystem_risk} /><MetricCard label="Post-intervention ecosystem risk" value={output.comparison.post_intervention_ecosystem_risk} /><MetricCard label="Mutated fraction change" value={`${output.comparison.percent_change.toFixed(1)}%`} /></div><p className="panelExplanation">{output.explanation}</p></SimulatorPanel>
      <SimulatorPanel title="Intervention Report" eyebrow={`Outcome: ${output.outcome}`}><p className="reportText">{output.report}</p><p className="researchDisclaimer">{output.disclaimer}</p></SimulatorPanel>
    </>}
  </div>;
}
