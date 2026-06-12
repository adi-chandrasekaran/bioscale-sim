import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import type { Catalog, SimulationRequest, SimulationResult, PopulationPoint } from "./types";
import { PathwayGraph } from "./PathwayGraph";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

const defaultRequest: SimulationRequest = {
  disease: "cancer",
  gene: "TP53",
  mutation: "p.R175H",
  steps: 60,
  initial_mutated_fraction: 0.02,
  initial_population: 10000,
  immune_pressure: 0.55,
  nutrient_level: 0.75,
};

function fmt(value: number) {
  return Number.isFinite(value) ? value.toFixed(2) : "—";
}

function Pipeline() {
  const steps = ["Disease", "Gene", "Mutation", "Protein", "Pathway", "Cell", "Population", "Ecosystem"];
  return (
    <div className="pipeline">
      {steps.map((step, index) => (
        <React.Fragment key={step}>
          <div className="pipeStep">{step}</div>
          {index < steps.length - 1 && <div className="pipeArrow">↓</div>}
        </React.Fragment>
      ))}
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="scoreBar">
      <div className="scoreHeader">
        <span>{label}</span>
        <strong>{fmt(value)}</strong>
      </div>
      <div className="barOuter"><div className="barInner" style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} /></div>
    </div>
  );
}

function PopulationChart({ points }: { points: PopulationPoint[] }) {
  const width = 760;
  const height = 220;
  const padding = 35;
  const maxStep = Math.max(...points.map((p) => p.step), 1);
  const polyline = points.map((p) => {
    const x = padding + (p.step / maxStep) * (width - padding * 2);
    const y = height - padding - p.mutated_fraction * (height - padding * 2);
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg className="chartSvg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Mutated fraction over time">
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className="axis" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} className="axis" />
      <polyline points={polyline} fill="none" className="chartLine" />
      <text x={padding} y={20} className="axisLabel">Mutated fraction</text>
      <text x={width - 120} y={height - 8} className="axisLabel">time steps</text>
    </svg>
  );
}

function LayerCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [request, setRequest] = useState<SimulationRequest>(defaultRequest);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/catalog`)
      .then((res) => res.json())
      .then(setCatalog)
      .catch(() => setError("Could not reach backend. Start FastAPI on port 8000."));
  }, []);

  const selectedGene = useMemo(() => catalog?.genes.find((g) => g.symbol === request.gene), [catalog, request.gene]);

  async function runSimulation() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? "Simulation failed");
      setResult(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (catalog) runSimulation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalog]);

  function update<K extends keyof SimulationRequest>(key: K, value: SimulationRequest[K]) {
    setRequest((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <main>
      <header className="hero">
        <div>
          <p className="eyebrow">Computational biology MVP</p>
          <h1>BioScale Simulator</h1>
          <p className="subtitle">
            A modular research demo that propagates a disease-associated mutation from DNA-level change to protein effect, pathway disruption, cell behavior, population expansion, and ecosystem risk.
          </p>
        </div>
        <Pipeline />
      </header>

      <section className="controlPanel">
        <div className="field">
          <label>Disease</label>
          <select value={request.disease} onChange={(e) => update("disease", e.target.value)}>
            {catalog?.diseases.map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Gene</label>
          <select value={request.gene} onChange={(e) => {
            const gene = catalog?.genes.find((g) => g.symbol === e.target.value);
            setRequest((prev) => ({ ...prev, gene: e.target.value, mutation: gene?.mutations[0] ?? prev.mutation }));
          }}>
            {catalog?.genes.filter((g) => g.mutations.length > 0).map((g) => <option key={g.symbol} value={g.symbol}>{g.symbol} — {g.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Mutation</label>
          <select value={request.mutation} onChange={(e) => update("mutation", e.target.value)}>
            {selectedGene?.mutations.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <div className="field compact">
          <label>Steps</label>
          <input type="number" min="5" max="300" value={request.steps} onChange={(e) => update("steps", Number(e.target.value))} />
        </div>
        <button onClick={runSimulation} disabled={loading}>{loading ? "Running..." : "Run simulation"}</button>
      </section>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="grid">
          <LayerCard title="1. Disease discovery → candidate gene">
            <p>{result.disease_discovery.label}</p>
            <p className="muted">Context: {result.disease_discovery.affected_cell_context}</p>
            <div className="candidateList">
              {result.disease_discovery.candidates.slice(0, 5).map((c) => (
                <div key={c.symbol} className={c.symbol === result.selected_candidate.symbol ? "candidate selected" : "candidate"}>
                  <strong>{c.symbol}</strong><span>{fmt(c.score)}</span>
                </div>
              ))}
            </div>
          </LayerCard>

          <LayerCard title="2. Mutation engine">
            <p><strong>{result.mutation_result.gene} {result.mutation_result.mutation}</strong> — {result.mutation_result.kind}</p>
            <p>{result.mutation_result.dna_rna_protein_explanation}</p>
            <p className="muted">{result.mutation_result.biological_interpretation}</p>
          </LayerCard>

          <LayerCard title="3. Protein effect">
            <p>{result.protein_effect.protein_name} ({result.protein_effect.protein_id})</p>
            <ScoreBar label="Remaining activity" value={result.protein_effect.activity} />
            <ScoreBar label="Remaining stability" value={result.protein_effect.stability} />
            <ScoreBar label="Remaining binding" value={result.protein_effect.binding} />
            <ScoreBar label="Loss-of-function score" value={result.protein_effect.loss_of_function_score} />
            <p className="muted">Affected domain: {result.protein_effect.affected_domains.join(", ")}</p>
          </LayerCard>

          <LayerCard title="4. Pathway simulator">
            <p>{result.pathway_result.label}</p>
            <PathwayGraph nodes={result.pathway_result.nodes} edges={result.pathway_result.edges} />
            <p className="muted">Disrupted: {result.pathway_result.disrupted_processes.length ? result.pathway_result.disrupted_processes.join("; ") : "No major process disruption in this run."}</p>
          </LayerCard>

          <LayerCard title="5. Cell phenotype">
            <div className="twoCols">
              <ScoreBar label="Proliferation" value={result.cell_phenotype.proliferation_rate} />
              <ScoreBar label="Apoptosis" value={result.cell_phenotype.apoptosis_rate} />
              <ScoreBar label="Repair capacity" value={result.cell_phenotype.repair_capacity} />
              <ScoreBar label="Genomic instability" value={result.cell_phenotype.genomic_instability} />
            </div>
            <p>{result.cell_phenotype.explanation}</p>
          </LayerCard>

          <LayerCard title="6. Population dynamics">
            <PopulationChart points={result.population_result.trajectory} />
            <ScoreBar label="Final mutated fraction" value={result.population_result.final_mutated_fraction} />
            <ScoreBar label="Clonal expansion score" value={result.population_result.clonal_expansion_score} />
            <p>{result.population_result.explanation}</p>
          </LayerCard>

          <LayerCard title="7. Ecosystem behavior">
            <div className="twoCols">
              <ScoreBar label="Tumor-like burden" value={result.ecosystem_result.tumor_like_burden} />
              <ScoreBar label="Immune clearance" value={result.ecosystem_result.immune_clearance} />
              <ScoreBar label="Inflammation" value={result.ecosystem_result.inflammation} />
              <ScoreBar label="Ecosystem risk" value={result.ecosystem_result.ecosystem_risk_score} />
            </div>
            <p>{result.ecosystem_result.explanation}</p>
          </LayerCard>

          <LayerCard title="Research summary">
            <p className="summary">{result.research_summary}</p>
            <p className="muted">This MVP is a simplified educational/research framework, not a clinical predictor or wet-lab validation system.</p>
          </LayerCard>
        </div>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
