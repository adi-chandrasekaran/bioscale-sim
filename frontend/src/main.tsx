import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import type { PopulationPoint, SelectedEntity, SimulationRequest, SimulationResult } from "./types";
import { PathwayGraph } from "./PathwayGraph";
import { AutocompleteSearch } from "./AutocompleteSearch";
import { CardSourceHeader, ProvenanceBadge, ProvenanceRow } from "./ProvenanceBadge";
import { ConciseSummary, RawEvidence } from "./Summary";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

const DEFAULT_DISEASE: SelectedEntity = { id: "EFO_0000311", label: "cancer" };
const DEFAULT_GENE: SelectedEntity = { id: "TP53", label: "TP53" };
const DEFAULT_VARIANT: SelectedEntity = { id: "p.R175H", label: "p.R175H", meta: { notation: "p.R175H" } };

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

function ScoreBar({
  label,
  value,
  provenance,
}: {
  label: string;
  value: number;
  provenance?: SimulationResult["protein_effect"]["provenance"][string];
}) {
  return (
    <div className="scoreBar">
      <div className="scoreHeader">
        <span>{label}</span>
        <div className="scoreHeaderRight">
          <strong>{fmt(value)}</strong>
          {provenance && <ProvenanceBadge entry={provenance} compact />}
        </div>
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

function ComputedFromLine({ gene, pathway, proteinActivity }: { gene?: string; pathway?: string; proteinActivity?: string }) {
  return (
    <div className="computedFromBlock">
      {gene && <p className="computedFromLine">Computed from selected gene: <strong>{gene}</strong></p>}
      {pathway && <p className="computedFromLine">Computed from selected pathway: <strong>{pathway}</strong></p>}
      {proteinActivity && <p className="computedFromLine">Computed from protein activity: <strong>{proteinActivity}</strong></p>}
    </div>
  );
}

function SimulationInputPanel({ input }: { input: SimulationResult["simulation_input"] }) {
  return (
    <section className="simulationInputPanel">
      <h3>Current simulation input</h3>
      <div className="simInputGrid">
        <div><span>Disease</span><strong>{input.disease_name}</strong><em>{input.disease_id}</em></div>
        <div><span>Gene</span><strong>{input.gene_symbol}</strong><em>{input.gene_id || "—"}</em></div>
        <div><span>Mutation</span><strong>{input.mutation}</strong></div>
        <div><span>Protein</span><strong>{input.protein_accession || "—"}</strong></div>
        <div><span>Pathway</span><strong>{input.pathway_name || "—"}</strong><em>{input.pathway_id || "—"}</em></div>
        <div><span>Pathway source</span><strong>{input.pathway_source || "—"}</strong></div>
      </div>
    </section>
  );
}

function App() {
  const [disease, setDisease] = useState<SelectedEntity | null>(DEFAULT_DISEASE);
  const [gene, setGene] = useState<SelectedEntity | null>(DEFAULT_GENE);
  const [variant, setVariant] = useState<SelectedEntity | null>(DEFAULT_VARIANT);
  const [pathway, setPathway] = useState<SelectedEntity | null>(null);
  const [steps, setSteps] = useState(60);
  const [useExternal, setUseExternal] = useState(true);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedGeneOverride, setSelectedGeneOverride] = useState<string | null>(null);

  const activeGene = selectedGeneOverride ?? gene?.label ?? gene?.id ?? "";

  function resetSimulationState() {
    setResult(null);
    setError(null);
    setSelectedGeneOverride(null);
  }

  useEffect(() => {
    resetSimulationState();
  }, [disease?.id, gene?.id, variant?.id, pathway?.id]);

  async function runSimulation(geneOverride?: string) {
    if (!disease || !gene || !variant) {
      setError("Search for and select a disease, gene, and mutation to begin.");
      return;
    }
    const geneSymbol = geneOverride ?? gene.id ?? gene.label;
    setLoading(true);
    setError(null);
    const request: SimulationRequest = {
      disease_id: disease.id,
      disease_name: disease.label,
      gene: geneSymbol,
      mutation: (variant.meta?.notation as string) || variant.label,
      pathway_id: pathway?.id,
      pathway_name: pathway?.label,
      steps,
      initial_mutated_fraction: 0.02,
      initial_population: 10000,
      immune_pressure: 0.55,
      nutrient_level: 0.75,
      use_external_evidence: useExternal,
    };
    try {
      const res = await fetch(`${API_BASE}/api/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? "Simulation failed");
      setResult(json);
      setSelectedGeneOverride(geneSymbol);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  }

  const ready = Boolean(disease && gene && variant);

  return (
    <main>
      <header className="hero">
        <div>
          <p className="eyebrow">Database-backed biology simulator</p>
          <h1>BioScale Simulator</h1>
          <p className="subtitle">
            Search diseases, genes, and mutations like a research search engine. External databases provide biological evidence; the simulator converts selected evidence into simplified model assumptions and computed outputs.
          </p>
          <p className="evidenceModelBanner">
            <strong>Evidence vs Model:</strong> External databases provide biological evidence. The simulator converts selected evidence into simplified model assumptions and computed outputs. Research prototype only, not a diagnostic tool.
          </p>
        </div>
        <Pipeline />
      </header>

      <section className="searchPanel">
        <AutocompleteSearch
          label="Disease"
          placeholder="e.g. breast cancer, Alzheimer, cystic fibrosis"
          endpoint="/api/search/diseases"
          value={disease}
          onChange={(item) => { setDisease(item); resetSimulationState(); }}
          initialQuery="cancer"
        />
        <AutocompleteSearch
          label="Gene"
          placeholder="e.g. TP53, BRCA1, KRAS"
          endpoint="/api/search/genes"
          value={gene}
          onChange={(g) => { setGene(g); resetSimulationState(); }}
          initialQuery="TP53"
        />
        <AutocompleteSearch
          label="Mutation / variant"
          placeholder="e.g. p.R175H, V600E, rs121913343"
          endpoint="/api/search/variants"
          extraParams={gene ? { gene: gene.id || gene.label } : {}}
          value={variant}
          onChange={(v) => { setVariant(v); resetSimulationState(); }}
          initialQuery="p.R175H"
          disabled={!gene}
        />
        <AutocompleteSearch
          label="Pathway (optional)"
          placeholder="Filter Reactome pathways for selected gene"
          endpoint="/api/search/pathways"
          extraParams={gene ? { gene: gene.id || gene.label } : {}}
          value={pathway}
          onChange={(p) => { setPathway(p); resetSimulationState(); }}
          disabled={!gene}
        />
        <div className="field compact">
          <label>Steps</label>
          <input type="number" min="5" max="300" value={steps} onChange={(e) => setSteps(Number(e.target.value))} />
        </div>
        <label className="toggleField">
          <input type="checkbox" checked={useExternal} onChange={(e) => setUseExternal(e.target.checked)} />
          Use external databases
        </label>
        <button onClick={() => runSimulation()} disabled={loading || !ready}>
          {loading ? "Running…" : "Run simulation"}
        </button>
      </section>

      {!ready && !result && (
        <div className="emptyState">Search for a disease, gene, or mutation to begin.</div>
      )}

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="grid">
          <SimulationInputPanel input={result.simulation_input} />
          <LayerCard title="1. Disease discovery → candidate gene">
            <CardSourceHeader
              source={result.disease_discovery.external_evidence_available ? "Open Targets" : "Local fallback"}
              externalAvailable={result.disease_discovery.external_evidence_available}
              notice={result.disease_discovery.evidence_notice}
            />
            <ConciseSummary text={result.disease_discovery.summary} />
            <ProvenanceRow label="Disease" value={result.disease_discovery.label} provenance={result.disease_discovery.provenance.label} />
            <div className="candidateList">
              {result.disease_discovery.candidates.slice(0, 10).map((c) => (
                <button
                  key={c.symbol}
                  type="button"
                  className={c.symbol === activeGene ? "candidate selected clickable" : "candidate clickable"}
                  onClick={() => {
                    setSelectedGeneOverride(c.symbol);
                    setGene({ id: c.symbol, label: c.symbol });
                    runSimulation(c.symbol);
                  }}
                >
                  <div className="candidateMain">
                    <strong>{c.symbol}</strong>
                    <span>{fmt(c.score)}</span>
                  </div>
                  <ConciseSummary text={c.summary || c.reasons[0]} className="candidateSummary" />
                  <ProvenanceBadge entry={c.provenance.score ?? { category: "external_database", source: c.source }} compact />
                </button>
              ))}
            </div>
            <RawEvidence data={result.disease_discovery.raw_evidence} />
          </LayerCard>

          <LayerCard title="2. Mutation engine">
            <CardSourceHeader source={result.mutation_result.source} externalAvailable={result.mutation_result.external_evidence_available} notice={result.mutation_result.evidence_notice} />
            <ConciseSummary text={result.mutation_result.summary} />
            <ProvenanceRow label="Variant" value={<><strong>{result.mutation_result.gene} {result.mutation_result.mutation}</strong> — {result.mutation_result.kind}</>} provenance={result.mutation_result.provenance.kind} />
            {result.mutation_result.amino_acid_change && (
              <ProvenanceRow label="Amino acid change" value={result.mutation_result.amino_acid_change} provenance={result.mutation_result.provenance.clinvar_classification} />
            )}
            {result.mutation_result.clinvar_classification && (
              <ProvenanceRow label="ClinVar classification" value={result.mutation_result.clinvar_classification} provenance={result.mutation_result.provenance.clinvar_classification} />
            )}
            {result.mutation_result.phenotypes.length > 0 && (
              <ProvenanceRow label="Linked phenotypes" value={result.mutation_result.phenotypes.join("; ")} />
            )}
            <RawEvidence data={result.mutation_result.raw_evidence} />
          </LayerCard>

          <LayerCard title="3. Protein effect">
            <CardSourceHeader source={result.protein_effect.source} externalAvailable={result.protein_effect.external_evidence_available} notice={result.protein_effect.evidence_notice} />
            <ConciseSummary text={result.protein_effect.summary || result.protein_effect.function_summary} />
            <ProvenanceRow label="Protein" value={`${result.protein_effect.protein_name} (${result.protein_effect.protein_id})`} provenance={result.protein_effect.provenance.protein_name} />
            {result.protein_effect.mutation_location && <ProvenanceRow label="Mutation location" value={result.protein_effect.mutation_location} />}
            {result.protein_effect.domain_hit && <ProvenanceRow label="Domain hit" value={result.protein_effect.domain_hit} provenance={result.protein_effect.provenance.function_summary} />}
            <ProvenanceRow label="Structural impact" value={result.protein_effect.structural_impact_placeholder} provenance={result.protein_effect.provenance.structural_impact_placeholder} />
            <ConciseSummary text={result.protein_effect.functional_impact_summary} />
            <ScoreBar label="Remaining activity" value={result.protein_effect.activity} provenance={result.protein_effect.provenance.activity} />
            <ScoreBar label="Remaining stability" value={result.protein_effect.stability} provenance={result.protein_effect.provenance.stability} />
            <ScoreBar label="Remaining binding" value={result.protein_effect.binding} provenance={result.protein_effect.provenance.binding} />
            <ScoreBar label="Loss-of-function score" value={result.protein_effect.loss_of_function_score} provenance={result.protein_effect.provenance.loss_of_function_score} />
            <RawEvidence data={result.protein_effect.raw_evidence} />
          </LayerCard>

          <LayerCard title="4. Pathway simulator">
            <CardSourceHeader source={result.pathway_result.source} externalAvailable={result.pathway_result.external_evidence_available} notice={result.pathway_result.evidence_notice} />
            {result.pathway_result.is_generic_fallback && (
              <p className="evidenceNotice">Generic simulator pathway generated from selected gene evidence; edge weights are model assumptions.</p>
            )}
            <ConciseSummary text={result.pathway_result.summary} />
            <ComputedFromLine
              gene={result.pathway_result.computed_from_gene}
              pathway={result.pathway_result.computed_from_pathway}
              proteinActivity={result.pathway_result.computed_from_protein_activity}
            />
            {result.pathway_result.selected_pathway_name && (
              <ProvenanceRow label="Selected Reactome pathway" value={`${result.pathway_result.selected_pathway_name} (${result.pathway_result.selected_pathway_id})`} provenance={result.pathway_result.provenance.reactome_pathways} />
            )}
            <p className="muted modelNote">{result.pathway_result.simulation_model_note}</p>
            <PathwayGraph nodes={result.pathway_result.nodes} edges={result.pathway_result.edges} />
            <ProvenanceRow label="Disrupted processes" value={result.pathway_result.disrupted_processes.length ? result.pathway_result.disrupted_processes.join("; ") : "No major disruption."} provenance={result.pathway_result.provenance.disrupted_processes} />
            <RawEvidence data={result.pathway_result.raw_evidence} />
          </LayerCard>

          <LayerCard title="5. Cell phenotype">
            <CardSourceHeader source={result.cell_phenotype.source} />
            <ComputedFromLine
              gene={result.cell_phenotype.computed_from_gene}
              pathway={result.cell_phenotype.computed_from_pathway}
              proteinActivity={result.cell_phenotype.computed_from_protein_activity}
            />
            <div className="twoCols">
              <ScoreBar label="Proliferation" value={result.cell_phenotype.proliferation_rate} />
              <ScoreBar label="Apoptosis" value={result.cell_phenotype.apoptosis_rate} />
              <ScoreBar label="Repair capacity" value={result.cell_phenotype.repair_capacity} />
              <ScoreBar label="Genomic instability" value={result.cell_phenotype.genomic_instability} />
            </div>
            <ConciseSummary text={result.cell_phenotype.explanation} />
            <ProvenanceBadge category="computed_model" source="Cell simulator" />
          </LayerCard>

          <LayerCard title="6. Population dynamics">
            <CardSourceHeader source={result.population_result.source} />
            <ComputedFromLine
              gene={result.population_result.computed_from_gene}
              pathway={result.population_result.computed_from_pathway}
              proteinActivity={result.population_result.computed_from_protein_activity}
            />
            <PopulationChart points={result.population_result.trajectory} />
            <ScoreBar label="Final mutated fraction" value={result.population_result.final_mutated_fraction} />
            <ScoreBar label="Clonal expansion score" value={result.population_result.clonal_expansion_score} />
            <ConciseSummary text={result.population_result.explanation} />
            <ProvenanceBadge category="computed_model" source="Population simulator" />
          </LayerCard>

          <LayerCard title="7. Ecosystem behavior">
            <CardSourceHeader source={result.ecosystem_result.source} />
            <ComputedFromLine
              gene={result.ecosystem_result.computed_from_gene}
              pathway={result.ecosystem_result.computed_from_pathway}
              proteinActivity={result.ecosystem_result.computed_from_protein_activity}
            />
            <div className="twoCols">
              <ScoreBar label="Tumor-like burden" value={result.ecosystem_result.tumor_like_burden} />
              <ScoreBar label="Immune clearance" value={result.ecosystem_result.immune_clearance} />
              <ScoreBar label="Inflammation" value={result.ecosystem_result.inflammation} />
              <ScoreBar label="Ecosystem risk" value={result.ecosystem_result.ecosystem_risk_score} />
            </div>
            <ConciseSummary text={result.ecosystem_result.explanation} />
            <ProvenanceBadge category="computed_model" source="Ecosystem simulator" />
          </LayerCard>

          <LayerCard title="Research summary">
            <ConciseSummary text={result.research_summary} />
            {result.evidence_notice && <p className="evidenceNotice">{result.evidence_notice}</p>}
            <p className="muted">{result.disclaimer}</p>
            <RawEvidence title="View full normalized evidence" data={result.evidence?.raw ?? {}} />
          </LayerCard>
        </div>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
