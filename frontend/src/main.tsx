import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import type { HierarchyDatum, PopulationPoint, SelectedEntity, SimulationRequest, SimulationResult } from "./types";
import { PathwayGraph } from "./PathwayGraph";
import { AutocompleteSearch } from "./AutocompleteSearch";
import { CardSourceHeader, ProvenanceBadge, ProvenanceRow } from "./ProvenanceBadge";
import { ConciseSummary, RawEvidence } from "./Summary";
import { PanelHelpAccordion, InfoTooltip } from "./Help";
import { AskAIPanel } from "./AskAI";
import {
  buildDefinitionHelp,
  buildFieldHelp,
  help,
  type TooltipHelp,
} from "./helpContent";
import {
  CardTabBar,
  CellPhenotypeVisual,
  EcosystemVisual,
  PopulationDynamicsVisual,
  type CardViewMode,
} from "./SimulationVisuals";
import { TabSwitcher } from "./SimulatorUI";
import { EvolutionSimulator } from "./EvolutionSimulator";
import { InterventionSimulator } from "./InterventionSimulator";
import { SimulationProvider, useSimulationContext } from "./SimulationContext";
import { PatientDigitalTwin } from "./PatientDigitalTwin";
import { ReasoningPanel } from "./ReasoningPanel";
import { CirclePackingChart } from "./components/visualizations/CirclePackingChart";
import { ProteinStructurePanel } from "./components/ProteinStructurePanel";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

class AppErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: Error | null }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error("App crashed", error);
  }

  render() {
    if (this.state.error) {
      return (
        <main>
          <div className="errorBoundary">
            <strong>The simulator crashed while rendering.</strong>
            <p>{this.state.error.message}</p>
            <pre>{this.state.error.stack}</pre>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}

function fmt(value: number) {
  return Number.isFinite(value) ? value.toFixed(2) : "—";
}

function fallbackEcosystemHierarchy(result: SimulationResult): HierarchyDatum {
  return {
    name: `${result.simulation_input.disease_name} ecosystem`,
    type: "ecosystem",
    description: "Fallback visual hierarchy derived from the ecosystem scores.",
    children: [
      { name: "Tumor-like burden", value: Math.max(result.ecosystem_result.tumor_like_burden, 0.04), type: "population", description: "Modeled burden from the altered population." },
      { name: "Immune clearance", value: Math.max(result.ecosystem_result.immune_clearance, 0.04), type: "immune", description: "Modeled immune containment." },
      { name: "Inflammation", value: Math.max(result.ecosystem_result.inflammation, 0.04), type: "inflammation", description: "Modeled inflammatory signaling." },
      { name: "Nutrient stress", value: Math.max(result.ecosystem_result.nutrient_stress, 0.04), type: "nutrient", description: "Modeled local nutrient stress." },
    ],
  };
}

function candidateDefinition(candidate: SimulationResult["disease_discovery"]["candidates"][number], diseaseName?: string) {
  const base = candidate.function_summary || candidate.summary || candidate.reasons?.[0] || `${candidate.symbol} is a gene included in this disease-linked candidate list.`;
  const diseaseLine = diseaseName ? `In this run, it is being evaluated in the context of ${diseaseName}.` : "";
  return [base, diseaseLine].filter(Boolean).join(" ");
}

function canonicalGeneSymbol(entity: SelectedEntity | null) {
  if (!entity) return "";
  const metaSymbol = typeof entity.meta?.symbol === "string" ? entity.meta.symbol : "";
  return (metaSymbol || entity.label || entity.id || "").trim();
}

function canonicalMutationNotation(entity: SelectedEntity | null) {
  if (!entity) return "";
  const metaNotation = typeof entity.meta?.notation === "string" ? entity.meta.notation : "";
  return (metaNotation || entity.label || entity.id || "").trim();
}

function normalizeGeneSelection(entity: SelectedEntity | null) {
  if (!entity) return null;
  const symbol = canonicalGeneSymbol(entity);
  return {
    id: symbol,
    label: symbol,
    meta: {
      ...entity.meta,
      symbol,
    },
  };
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
  help,
  reference,
}: {
  label: string;
  value: number;
  provenance?: SimulationResult["protein_effect"]["provenance"][string];
  help?: TooltipHelp;
  reference?: number;
}) {
  const baseline = reference ?? (label.toLowerCase().startsWith("remaining") ? 1 : 0.5);
  const delta = value - baseline;
  const direction = delta >= 0 ? "increase" : "decrease";
  const tooltip = help ?? {
    title: label,
    summary: `If this occurs, there is a probability that ${label} will ${direction} by ${Math.abs(delta * 100).toFixed(0)}%.`,
    details: [
      `Current modeled probability is ${(value * 100).toFixed(0)}%.`,
      `Reference value is ${(baseline * 100).toFixed(0)}%.`,
      `${label} is computed from the current disease, gene, mutation, protein, pathway, and downstream simulator outputs for this run.`,
    ],
    examples: [],
  };
  const directionClass = delta < 0 ? "decreased" : "increased";
  return (
    <div className="scoreBar">
      <div className="scoreHeader">
        <span className="scoreHeaderLabel">
          {label}
          <InfoTooltip label={label} help={tooltip} />
        </span>
        <div className="scoreHeaderRight">
          <strong>{fmt(value)}</strong>
          {provenance && <ProvenanceBadge entry={provenance} compact />}
        </div>
      </div>
      <div className="barOuter"><div className={`barInner ${directionClass}`} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} /></div>
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

function LayerCard({
  title,
  children,
  className = "",
  footer,
  helpKey,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
  footer?: string;
  helpKey?: keyof typeof help.panels;
}) {
  return (
    <section className={`card ${className}`.trim()}>
      <div className="cardTitleRow">
        <h2>{title}</h2>
        {helpKey && <PanelHelpAccordion help={help.panels[helpKey]} />}
      </div>
      {children}
      {footer && <p className="cardFooter">{footer}</p>}
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
  const dataSourceRows = Object.entries(input.data_source_status ?? {});
  return (
    <section className="simulationInputPanel">
      <div className="cardTitleRow">
        <h3>Current Biological Context</h3>
        <PanelHelpAccordion help={help.panels.simulationInput} />
      </div>
      <div className="simInputGrid">
        <div><span>Disease</span><strong>{input.disease_name}</strong><em>{input.disease_id}</em></div>
        <div><span>Gene</span><strong>{input.gene_symbol}</strong><em>{input.gene_id || "—"}</em></div>
        <div><span>Mutation</span><strong>{input.mutation}</strong><em>{input.clinvar_variation_id ? `ClinVar ${input.clinvar_variation_id}` : input.rsid || "No ClinVar/rsID match"}</em></div>
        <div><span>Protein</span><strong>{input.protein_name || input.protein_accession || "—"}</strong><em>{input.uniprot_accession || input.protein_accession || "—"}</em></div>
        <div><span>AlphaFold</span><strong>{input.alphafold_available ? "Available" : "Unavailable"}</strong><em>{input.alphafold_confidence_label || "confidence unknown"}</em></div>
        <div><span>Pathway</span><strong>{input.pathway_name || "—"}</strong><em>{input.pathway_id || "—"}</em></div>
        <div><span>Pathway source</span><strong>{input.pathway_source || "—"}</strong></div>
      </div>
      {dataSourceRows.length > 0 && (
        <div className="sourceStatusGrid" aria-label="Database source status">
          {dataSourceRows.map(([source, status]) => (
            <span key={source} className={status === "available" ? "sourceStatus available" : "sourceStatus unavailable"}>
              {source}: {status}
            </span>
          ))}
        </div>
      )}
      <div className="meaningGrid">
        <div>
          <strong>What this means biologically</strong>
          <p>This is the shared disease, gene, mutation, protein, structure, and pathway context used by every simulator tab.</p>
        </div>
        <div>
          <strong>How this was computed</strong>
          <p>Identifiers are normalized from search selections and database adapters; missing evidence is marked unavailable instead of guessed.</p>
        </div>
      </div>
    </section>
  );
}

function CandidateGeneCard({
  candidate,
  active,
  diseaseName,
  onSelect,
}: {
  candidate: SimulationResult["disease_discovery"]["candidates"][number];
  active: boolean;
  diseaseName?: string;
  onSelect: () => void;
}) {
  const definition = candidateDefinition(candidate, diseaseName);
  return (
    <button
      type="button"
      className={active ? "candidate selected clickable" : "candidate clickable"}
      onClick={onSelect}
    >
      <div className="candidateMain">
        <strong>{candidate.symbol}</strong>
      </div>
      <div className="candidateHoverBubble" aria-hidden="true">
        <strong>{candidate.symbol}</strong>
        <p>{definition}</p>
        <p>Model ranking score for this disease context: {fmt(candidate.score)}.</p>
      </div>
      <ProvenanceBadge entry={candidate.provenance.score ?? { category: "external_database", source: candidate.source }} compact />
    </button>
  );
}

function LearningPanel({ result }: { result: SimulationResult }) {
  const assumptions = [
    "Activity, stability, binding, pathway propagation, population growth, and ecosystem risk are simulator assumptions or computed model outputs.",
    "AlphaFold is used only as structural context; it does not prove pathogenicity.",
    "External database gaps are shown as unavailable instead of being filled with fake evidence.",
  ];
  const validation = [
    "clinical-grade variant curation",
    "validated disease cohorts",
    "bench or literature support for pathway effects",
    "expert clinical review before any diagnostic use",
  ];
  return (
    <LayerCard title="Research Student Learning Panel" className="wide" footer="This panel explains the run in teaching language and separates evidence from model assumptions.">
      <div className="learningGrid">
        <div><span>What is this gene?</span><p>{result.selected_candidate.function_summary || result.selected_candidate.summary || `${result.simulation_input.gene_symbol} is the selected gene for this run.`} In this simulation it is treated as the molecular starting point that connects the disease search result to the mutation, protein, pathway, cell, population, and ecosystem layers.</p></div>
        <div><span>What is this mutation?</span><p>{result.mutation_result.summary || `${result.mutation_result.mutation} is interpreted as ${result.mutation_result.kind}.`} The simulator converts that variant class into activity, stability, and binding multipliers so the mutation can affect downstream biology.</p></div>
        <div><span>What is this protein/domain?</span><p>{result.protein_effect.function_summary || result.protein_effect.summary || `${result.protein_effect.protein_name} is the selected protein.`} {result.protein_effect.domain_hit ? `The mutation maps to ${result.protein_effect.domain_hit}, so the model treats that region as the affected functional context.` : "No specific domain hit was available, so the model uses the mutation-level functional effect."}</p></div>
        <div><span>What is this pathway?</span><p>{result.pathway_result.summary || result.pathway_result.description || "The pathway layer propagates the protein effect through connected biological steps."} Nodes in the pathway represent biological steps; edges represent modeled activation or inhibition between those steps.</p></div>
        <div><span>What did the cell model conclude?</span><p>Proliferation {fmt(result.cell_phenotype.proliferation_rate)}, apoptosis {fmt(result.cell_phenotype.apoptosis_rate)}, repair {fmt(result.cell_phenotype.repair_capacity)}, and genomic instability {fmt(result.cell_phenotype.genomic_instability)} are combined to describe the altered cell state.</p></div>
        <div><span>What did the tissue model conclude?</span><p>The final mutated fraction is {fmt(result.population_result.final_mutated_fraction)} and ecosystem risk is {fmt(result.ecosystem_result.ecosystem_risk_score)}. These are computed simulator outputs that show how altered cells may affect the local tissue environment.</p></div>
        <div><span>What is being assumed?</span><ul>{assumptions.map((item) => <li key={item}>{item}</li>)}</ul></div>
        <div><span>What would need validation?</span><ul>{validation.map((item) => <li key={item}>{item}</li>)}</ul></div>
      </div>
    </LayerCard>
  );
}

function App() {
  const { activeTab, setActiveTab, disease, setDisease, gene, setGene, variant, setVariant, pathway, setPathway,
    protein, setProtein, setSharedContext, steps, setSteps, useExternal, setUseExternal, result, setResult,
    evolutionResult, setEvolutionResult, setPersonalizedResult, interventionScenario, setInterventionScenario, setInterventionResult } = useSimulationContext();
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = window.localStorage.getItem("bioscale-theme");
    return saved === "dark" ? "dark" : "light";
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestControllerRef = useRef<AbortController | null>(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [cardViews, setCardViews] = useState<Record<"protein" | "cell" | "population" | "ecosystem", CardViewMode>>({
    protein: "summary",
    cell: "summary",
    population: "summary",
    ecosystem: "summary",
  });

  const activeGene = canonicalGeneSymbol(gene);
  const diseaseEvidenceSummary =
    typeof result?.disease_discovery?.summary === "string"
      ? result.disease_discovery.summary
      : typeof result?.evidence?.disease?.description === "string"
        ? result.evidence.disease.description
        : undefined;
  const geneEvidenceSummary =
    typeof result?.selected_candidate?.function_summary === "string"
      ? result.selected_candidate.function_summary
      : typeof result?.selected_candidate?.summary === "string"
        ? result.selected_candidate.summary
        : typeof result?.protein_effect?.function_summary === "string"
          ? result.protein_effect.function_summary
          : typeof result?.evidence?.gene?.summary === "string"
            ? result.evidence.gene.summary
            : undefined;
  const pathwayEvidenceDescription =
    typeof result?.pathway_result?.description === "string" ? result.pathway_result.description : undefined;
  const pathwayGeneSummary =
    typeof result?.protein_effect.function_summary === "string"
      ? result.protein_effect.function_summary
      : typeof result?.evidence?.gene?.summary === "string"
        ? result.evidence.gene.summary
        : undefined;
  const ecosystemHierarchy = result?.ecosystem_result.ecosystem_hierarchy ?? (result ? fallbackEcosystemHierarchy(result) : undefined);
  const ready = Boolean(disease && activeGene && variant);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("bioscale-theme", theme);
  }, [theme]);

  useEffect(() => {
    setSharedContext((current) => ({
      ...current,
      diseaseName: disease?.label || "",
      diseaseId: disease?.id || "",
      geneSymbol: activeGene,
      ensemblGeneId: typeof gene?.meta?.ensembl_id === "string" ? gene.meta.ensembl_id : current.ensemblGeneId,
      mutation: canonicalMutationNotation(variant),
      hgvsNotation: canonicalMutationNotation(variant),
      clinvarVariationId: typeof variant?.meta?.clinvar_id === "string" ? variant.meta.clinvar_id : current.clinvarVariationId,
      rsid: typeof variant?.meta?.rsid === "string" ? variant.meta.rsid : current.rsid,
      uniprotAccession: typeof protein?.meta?.accession === "string" ? protein.meta.accession : current.uniprotAccession,
      proteinName: protein?.label || current.proteinName,
      reactomePathwayId: pathway?.id || "",
      pathwayName: pathway?.label || "",
    }));
  }, [activeGene, disease?.id, disease?.label, gene?.meta, pathway?.id, pathway?.label, protein?.label, protein?.meta, setSharedContext, variant]);

  const runSimulation = useCallback(async () => {
    if (!disease || !gene || !variant || !activeGene) {
      setLoading(false);
      setResult(null);
      setError("Search for and select a disease, gene, and mutation to begin.");
      return;
    }
    const geneSymbol = activeGene;
    const mutationNotation = canonicalMutationNotation(variant);
    requestControllerRef.current?.abort();
    const controller = new AbortController();
    requestControllerRef.current = controller;
    setCardViews({ protein: "summary", cell: "summary", population: "summary", ecosystem: "summary" });
    setLoading(true);
    setError(null);
    setResult(null);
    const request: SimulationRequest = {
      disease_id: disease.id,
      disease_name: disease.label,
      gene: geneSymbol,
      mutation: mutationNotation,
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
        signal: controller.signal,
      });
      const json = await res.json();
      if (controller.signal.aborted) return;
      if (!res.ok) throw new Error(json.detail ?? "Simulation failed");
      setResult(json);
      setSharedContext((current) => ({
        ...current,
        diseaseName: json.simulation_input?.disease_name || disease.label,
        diseaseId: json.simulation_input?.disease_id || disease.id,
        geneSymbol: json.simulation_input?.gene_symbol || geneSymbol,
        ensemblGeneId: json.simulation_input?.gene_id || "",
        uniprotAccession: json.simulation_input?.uniprot_accession || json.protein_effect?.protein_id || "",
        proteinName: json.simulation_input?.protein_name || json.protein_effect?.protein_name || "",
        mutation: json.simulation_input?.mutation || mutationNotation,
        hgvsNotation: json.simulation_input?.hgvs_notation || mutationNotation,
        clinvarVariationId: json.simulation_input?.clinvar_variation_id || "",
        rsid: json.simulation_input?.rsid || "",
        reactomePathwayId: json.simulation_input?.pathway_id || "",
        pathwayName: json.simulation_input?.pathway_name || "",
      }));
      if (json.protein_effect?.protein_id) {
        setProtein({ id: json.protein_effect.protein_id, label: json.protein_effect.protein_name, meta: { accession: json.protein_effect.protein_id } });
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      if (requestControllerRef.current === controller) {
        setLoading(false);
      }
    }
  }, [activeGene, disease, gene, variant, pathway?.id, pathway?.label, steps, useExternal, setSharedContext]);

  useEffect(() => {
    setError(null);
    if (!ready) {
      setResult(null);
      setLoading(false);
      requestControllerRef.current?.abort();
      return;
    }
    setResult(null);
    const timer = window.setTimeout(() => {
      void runSimulation();
    }, 250);
    return () => window.clearTimeout(timer);
  }, [ready, disease?.id, disease?.label, gene?.id, gene?.label, variant?.id, variant?.label, pathway?.id, pathway?.label, steps, useExternal, runSimulation]);

  useEffect(() => () => {
    requestControllerRef.current?.abort();
  }, []);

  return (
    <main>
      <button className="themeToggle" type="button" onClick={() => setTheme((current) => current === "dark" ? "light" : "dark")} aria-label="Toggle light and dark mode">
        {theme === "dark" ? "Light mode" : "Dark mode"}
      </button>
      <header className="hero">
        <div>
          <p className="eyebrow">Database-backed biology simulator</p>
          <h1>BioScale Platform</h1>
          <p className="subtitle">
            Search diseases, genes, and mutations like a research search engine. External databases provide biological evidence; the simulator converts selected evidence into simplified model assumptions and computed outputs.
          </p>
          <div className="heroLinks" aria-label="Project links">
            <a href="https://github.com/adi-chandrasekaran/bioscale-sim" target="_blank" rel="noreferrer">
              View on GitHub
            </a>
          </div>
          <p className="evidenceModelBanner">
            <strong>Evidence vs Model:</strong> External databases provide biological evidence. The simulator converts selected evidence into simplified model assumptions and computed outputs. Research prototype only, not a diagnostic tool.
          </p>
        </div>
        <Pipeline />
      </header>

      <TabSwitcher value={activeTab} onChange={setActiveTab} />

      <section className="searchPanel">
        <AutocompleteSearch
          label="Disease"
          help={buildFieldHelp("disease", { diseaseName: disease?.label, diseaseSummary: diseaseEvidenceSummary })}
          placeholder="e.g. breast cancer, Alzheimer, cystic fibrosis"
          endpoint="/api/search/diseases"
          value={disease}
          onChange={(item) => { setDisease(item); }}
          initialQuery="cancer"
          allowFreeText
        />
        <AutocompleteSearch
          label="Gene"
          help={buildFieldHelp("gene", { geneSymbol: activeGene, geneSummary: geneEvidenceSummary, diseaseName: disease?.label, diseaseSummary: diseaseEvidenceSummary })}
          placeholder="e.g. TP53, BRCA1, KRAS"
          endpoint="/api/search/genes"
          value={gene}
          onChange={(g) => { setGene(normalizeGeneSelection(g)); setProtein(null); }}
          initialQuery="TP53"
          allowFreeText
        />
        <AutocompleteSearch
          label="Mutation / variant"
          help={buildFieldHelp("mutation", { geneSymbol: activeGene, mutationNotation: canonicalMutationNotation(variant), mutationSummary: result?.mutation_result?.summary, diseaseName: disease?.label })}
          placeholder="e.g. p.R175H, V600E, rs121913343"
          endpoint="/api/search/variants"
          extraParams={activeGene ? { gene: activeGene } : {}}
          value={variant}
          onChange={(v) => { setVariant(v); }}
          initialQuery="p.R175H"
          disabled={!gene}
          allowFreeText
        />
        <AutocompleteSearch
          label="Pathway (optional)"
          help={buildFieldHelp("pathway", { pathwayName: pathway?.label, pathwaySummary: pathwayEvidenceDescription, selectedPathwayId: pathway?.id, pathwayDescription: pathwayEvidenceDescription })}
          placeholder="Filter Reactome pathways for selected gene"
          endpoint="/api/search/pathways"
          extraParams={activeGene ? { gene: activeGene } : {}}
          value={pathway}
          onChange={(p) => { setPathway(p); }}
          disabled={!gene}
          allowFreeText
        />
        <AutocompleteSearch
          key={`protein-${activeGene}`}
          label="Protein (optional)"
          placeholder="Search UniProt proteins"
          endpoint="/api/search/proteins"
          value={protein}
          onChange={setProtein}
          initialQuery={activeGene}
          disabled={!gene}
          allowFreeText
        />
        <div className="field compact">
          <div className="fieldLabelRow">
            <label>Steps</label>
            <InfoTooltip label="Steps" help={buildFieldHelp("steps", { value: steps })} />
          </div>
          <input type="number" min="5" max="300" value={steps} onChange={(e) => setSteps(Number(e.target.value))} />
        </div>
        <div className="field compact">
          <div className="fieldLabelRow">
            <label htmlFor="use-external-databases">Use external databases</label>
            <InfoTooltip label="Use external databases" help={buildFieldHelp("useExternalDatabases")} />
          </div>
          <label className="toggleField">
            <input id="use-external-databases" type="checkbox" checked={useExternal} onChange={(e) => setUseExternal(e.target.checked)} />
            Use external databases
          </label>
        </div>
        <button onClick={() => void runSimulation()} disabled={loading || !ready}>
          {loading ? "Running…" : "Run simulation"}
        </button>
      </section>

      {activeTab === "bioscale" && !ready && !result && (
        <div className="emptyState">Search for a disease, gene, or mutation to begin.</div>
      )}

      {error && <div className="error">{error}</div>}

      {activeTab === "bioscale" && result && (
        <div className="grid">
          <SimulationInputPanel input={result.simulation_input} />
          <LayerCard title="1. Disease discovery → candidate gene" helpKey="diseaseDiscovery" footer="This card ranks disease-linked genes and explains which evidence supports the leading candidate.">
            <CardSourceHeader
              source={result.disease_discovery.external_evidence_available ? "Open Targets" : "Local fallback"}
              externalAvailable={result.disease_discovery.external_evidence_available}
              notice={result.disease_discovery.evidence_notice}
            />
            <ConciseSummary text={result.disease_discovery.summary} />
            <ProvenanceRow label="Disease" value={result.disease_discovery.label} provenance={result.disease_discovery.provenance.label} />
            <div className="candidateList">
              {result.disease_discovery.candidates.slice(0, 10).map((c) => (
                <CandidateGeneCard
                  key={c.symbol}
                  candidate={c}
                  active={c.symbol === activeGene}
                  diseaseName={result.simulation_input.disease_name}
                  onSelect={() => {
                    setGene(normalizeGeneSelection({ id: c.symbol, label: c.symbol, meta: { symbol: c.symbol } }));
                    setProtein(null);
                  }}
                />
              ))}
            </div>
            <RawEvidence data={result.disease_discovery.raw_evidence} />
          </LayerCard>

          <LayerCard title="2. Mutation engine" helpKey="mutationEngine" footer="This card interprets the chosen variant and translates it into a mutation type the simulator can use.">
            <CardSourceHeader source={result.mutation_result.source} externalAvailable={result.mutation_result.external_evidence_available} notice={result.mutation_result.evidence_notice} />
            <ConciseSummary text={result.mutation_result.summary} />
            <ProvenanceRow
              label="Variant"
              value={<><strong>{result.mutation_result.gene} {result.mutation_result.mutation}</strong> — {result.mutation_result.kind}</>}
              provenance={result.mutation_result.provenance.kind}
                help={buildDefinitionHelp("variant", {
                geneSymbol: result.mutation_result.gene,
                mutationNotation: result.mutation_result.mutation,
                mutationKind: result.mutation_result.kind,
                mutationSummary: result.mutation_result.summary,
              })}
            />
            {result.mutation_result.amino_acid_change && (
              <ProvenanceRow
                label="Amino acid change"
                value={result.mutation_result.amino_acid_change}
                provenance={result.mutation_result.provenance.clinvar_classification}
                help={buildDefinitionHelp("aminoAcidChange", {
                  aminoAcidChange: result.mutation_result.amino_acid_change,
                  mutationNotation: result.mutation_result.mutation,
                })}
              />
            )}
            {result.mutation_result.clinvar_classification && (
              <ProvenanceRow
                label="ClinVar classification"
                value={result.mutation_result.clinvar_classification}
                provenance={result.mutation_result.provenance.clinvar_classification}
                help={buildDefinitionHelp("clinvarClassification", {
                  clinvarClassification: result.mutation_result.clinvar_classification,
                })}
              />
            )}
            {result.mutation_result.phenotypes.length > 0 && (
              <ProvenanceRow label="Linked phenotypes" value={result.mutation_result.phenotypes.join("; ")} />
            )}
            <RawEvidence data={result.mutation_result.raw_evidence} />
          </LayerCard>

          <LayerCard title="3. Protein effect" className="wide" helpKey="proteinEffect" footer="This card estimates how strongly the mutation changes protein activity, stability, and binding.">
            <CardTabBar value={cardViews.protein} onChange={(value) => setCardViews((current) => ({ ...current, protein: value }))} visualLabel="AlphaFold" />
            {cardViews.protein === "summary" ? (
              <>
                <CardSourceHeader source={result.protein_effect.source} externalAvailable={result.protein_effect.external_evidence_available} notice={result.protein_effect.evidence_notice} />
                <ConciseSummary text={result.protein_effect.summary || result.protein_effect.function_summary} />
                <ProvenanceRow
                  label="Protein"
                  value={`${result.protein_effect.protein_name} (${result.protein_effect.protein_id})`}
                  provenance={result.protein_effect.provenance.protein_name}
                  help={buildDefinitionHelp("protein", {
                    proteinName: result.protein_effect.protein_name,
                    proteinSummary: result.protein_effect.function_summary,
                  })}
                />
                {result.protein_effect.mutation_location && <ProvenanceRow label="Mutation location" value={result.protein_effect.mutation_location} />}
                {result.protein_effect.domain_hit && (
                  <ProvenanceRow
                    label="Domain hit"
                    value={result.protein_effect.domain_hit}
                    provenance={result.protein_effect.provenance.function_summary}
                    help={buildDefinitionHelp("domainHit", { domainHit: result.protein_effect.domain_hit })}
                  />
                )}
                <ProvenanceRow label="Structural impact" value={result.protein_effect.structural_impact_placeholder} provenance={result.protein_effect.provenance.structural_impact_placeholder} />
                <ProteinStructurePanel
                  apiBase={API_BASE}
                  uniprotAccession={result.simulation_input.uniprot_accession || result.protein_effect.protein_id}
                  position={result.mutation_result.position}
                  proteinName={result.protein_effect.protein_name}
                  mutation={result.mutation_result.mutation}
                />
                <ConciseSummary text={result.protein_effect.functional_impact_summary} />
                <ScoreBar label="Remaining activity" value={result.protein_effect.activity} provenance={result.protein_effect.provenance.activity} />
                <ScoreBar label="Remaining stability" value={result.protein_effect.stability} provenance={result.protein_effect.provenance.stability} />
                <ScoreBar label="Remaining binding" value={result.protein_effect.binding} provenance={result.protein_effect.provenance.binding} />
                <ScoreBar label="Loss-of-function score" value={result.protein_effect.loss_of_function_score} provenance={result.protein_effect.provenance.loss_of_function_score} />
                <RawEvidence data={result.protein_effect.raw_evidence} />
              </>
            ) : (
              <ProteinStructurePanel
                apiBase={API_BASE}
                uniprotAccession={result.simulation_input.uniprot_accession || result.protein_effect.protein_id}
                position={result.mutation_result.position}
                proteinName={result.protein_effect.protein_name}
                mutation={result.mutation_result.mutation}
              />
            )}
          </LayerCard>

          <LayerCard title="4. Pathway simulator" className="wide" helpKey="pathwaySimulator" footer="This card propagates the gene effect through a pathway graph and marks the processes that shift.">
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
              <ProvenanceRow
                label="Selected Reactome pathway"
                value={`${result.pathway_result.selected_pathway_name} (${result.pathway_result.selected_pathway_id})`}
                provenance={result.pathway_result.provenance.reactome_pathways}
                help={buildDefinitionHelp("selectedReactomePathway", {
                  selectedPathwayName: result.pathway_result.selected_pathway_name,
                  selectedPathwayId: result.pathway_result.selected_pathway_id,
                  pathwayDescription: result.pathway_result.description,
                })}
              />
            )}
            <p className="muted modelNote">{result.pathway_result.simulation_model_note}</p>
            <PathwayGraph
              nodes={result.pathway_result.nodes}
              edges={result.pathway_result.edges}
              selectedGene={result.pathway_result.selected_gene}
              selectedPathwayName={result.pathway_result.selected_pathway_name}
              pathwayDescription={result.pathway_result.description}
              selectedGeneSummary={pathwayGeneSummary}
            />
            <ProvenanceRow label="Disrupted processes" value={result.pathway_result.disrupted_processes.length ? result.pathway_result.disrupted_processes.join("; ") : "No major disruption."} provenance={result.pathway_result.provenance.disrupted_processes} />
            <RawEvidence data={result.pathway_result.raw_evidence} />
          </LayerCard>

          <LayerCard title="5. Cell phenotype" className="wide" helpKey="cellPhenotype" footer="This card turns pathway disruption into cell-level behavior such as proliferation, repair, and apoptosis.">
            <CardTabBar value={cardViews.cell} onChange={(value) => setCardViews((current) => ({ ...current, cell: value }))} visualLabel="Model" />
            {cardViews.cell === "summary" ? (
              <>
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
              </>
            ) : (
              <CellPhenotypeVisual cell={result.cell_phenotype} diseaseName={result.simulation_input.disease_name} />
            )}
          </LayerCard>

          <LayerCard title="6. Population dynamics" className="wide" helpKey="populationDynamics" footer="This card projects whether the altered cell state stays rare or expands across a population.">
            <CardTabBar value={cardViews.population} onChange={(value) => setCardViews((current) => ({ ...current, population: value }))} visualLabel="Model" />
            {cardViews.population === "summary" ? (
              <>
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
              </>
            ) : (
              <PopulationDynamicsVisual population={result.population_result} active={cardViews.population === "visual"} />
            )}
          </LayerCard>

          <LayerCard title="7. Ecosystem behavior" className="wide" helpKey="ecosystemBehavior" footer="This card combines cell behavior with immune and tissue context to estimate overall ecosystem risk.">
            <CardTabBar value={cardViews.ecosystem} onChange={(value) => setCardViews((current) => ({ ...current, ecosystem: value }))} visualLabel="Model" />
            {cardViews.ecosystem === "summary" ? (
              <>
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
              </>
            ) : (
              ecosystemHierarchy ? (
                <CirclePackingChart
                  data={ecosystemHierarchy}
                  title={`${result.simulation_input.disease_name} ecosystem map`}
                  description="Circle size follows the run-specific modeled contribution of each local ecosystem factor."
                />
              ) : (
                <EcosystemVisual ecosystem={result.ecosystem_result} diseaseName={result.simulation_input.disease_name} />
              )
            )}
          </LayerCard>

          <LayerCard title="Research summary" className="wide" helpKey="researchSummary" footer="This card compresses the full run into a single readable summary for quick review.">
            <ConciseSummary text={result.research_summary} />
            {result.evidence_notice && <p className="evidenceNotice">{result.evidence_notice}</p>}
            <p className="muted">{result.disclaimer}</p>
            <RawEvidence title="View full normalized evidence" data={result.evidence?.raw ?? {}} />
          </LayerCard>
          {result.reasoning && <ReasoningPanel reasoning={result.reasoning} />}
          <LearningPanel result={result} />
        </div>
      )}
      {activeTab === "evolution" && <EvolutionSimulator apiBase={API_BASE} result={result} disease={disease?.label ?? ""} gene={activeGene} mutation={canonicalMutationNotation(variant)} steps={steps} onResult={setEvolutionResult} />}
      {activeTab === "digital-twin" && <PatientDigitalTwin apiBase={API_BASE} baseline={result} disease={disease?.label ?? ""} gene={activeGene} mutation={canonicalMutationNotation(variant)} protein={protein?.label ?? result?.protein_effect.protein_name ?? ""} pathway={pathway?.label ?? result?.pathway_result.label ?? ""} onResult={setPersonalizedResult} onInterventionScenario={(scenario) => { setInterventionScenario(scenario); setActiveTab("intervention"); }} />}
      {activeTab === "intervention" && <InterventionSimulator apiBase={API_BASE} baseline={result} evolution={evolutionResult} scenario={interventionScenario} onResult={setInterventionResult} />}
      <p className="globalDisclaimer">Research prototype only, not a diagnostic tool or treatment recommendation.</p>
      <AskAIPanel open={aiOpen} onOpenChange={setAiOpen} result={result} />
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <AppErrorBoundary>
    <SimulationProvider><App /></SimulationProvider>
  </AppErrorBoundary>,
);
