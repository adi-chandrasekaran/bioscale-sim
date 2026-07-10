import { useEffect, useId, useMemo, useRef, useState } from "react";

declare global {
  interface Window {
    $3Dmol?: {
      createViewer: (element: HTMLElement, options: Record<string, unknown>) => {
        addModel: (data: string, format: string) => void;
        setStyle: (selection: Record<string, unknown>, style: Record<string, unknown>) => void;
        addStyle: (selection: Record<string, unknown>, style: Record<string, unknown>) => void;
        addResLabels: (selection: Record<string, unknown>, options: Record<string, unknown>) => void;
        zoomTo: (selection?: Record<string, unknown>) => void;
        render: () => void;
        clear: () => void;
      };
    };
  }
}

type AlphaFoldSummary = {
  source: string;
  uniprot_accession: string;
  alphafold_available: boolean;
  pdb_url: string;
  cif_url: string;
  mmcif_url: string;
  pae_url: string;
  mutation_position: number | null;
  residue_confidence: number | null;
  global_confidence: number | null;
  confidence_label: string;
  summary: string;
  message: string;
  error?: string | null;
};

function formatConfidence(value: number | null | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(1) : "unknown";
}

function load3Dmol() {
  if (window.$3Dmol) return Promise.resolve();
  return new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>("script[data-bioscale-3dmol]");
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("3Dmol failed to load")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://3Dmol.csb.pitt.edu/build/3Dmol-min.js";
    script.async = true;
    script.dataset.bioscale3dmol = "true";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("3Dmol failed to load"));
    document.head.appendChild(script);
  });
}

function StructureViewer({
  pdbUrl,
  mode,
  position,
}: {
  pdbUrl: string;
  mode: "before" | "after";
  position?: number | null;
}) {
  const id = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState("Loading interactive structure viewer...");

  useEffect(() => {
    const element = containerRef.current;
    if (!element || !pdbUrl) return;
    let cancelled = false;
    element.innerHTML = "";
    setStatus("Loading interactive structure viewer...");
    Promise.all([load3Dmol(), fetch(pdbUrl).then((response) => {
      if (!response.ok) throw new Error("AlphaFold PDB file could not be loaded");
      return response.text();
    })])
      .then(([, pdbText]) => {
        if (cancelled || !window.$3Dmol || !element) return;
        element.innerHTML = "";
        const viewer = window.$3Dmol.createViewer(element, { backgroundColor: "white" });
        viewer.addModel(pdbText, "pdb");
        viewer.setStyle({}, { cartoon: { color: "spectrum" } });
        if (mode === "after" && position) {
          viewer.addStyle({ resi: position }, { stick: { color: "crimson", radius: 0.35 }, sphere: { color: "crimson", radius: 0.7 } });
          viewer.addResLabels({ resi: position }, { font: "Arial", fontSize: 14, fontColor: "black", backgroundColor: "white" });
          viewer.zoomTo({ resi: position });
        } else {
          viewer.zoomTo();
        }
        viewer.render();
        setStatus(mode === "after" && position ? `Mutation residue ${position} highlighted.` : "Wild-type AlphaFold structure loaded.");
      })
      .catch((reason) => {
        if (!cancelled) setStatus(reason instanceof Error ? reason.message : "Structure viewer failed to load.");
      });
    return () => {
      cancelled = true;
      if (element) element.innerHTML = "";
    };
  }, [mode, pdbUrl, position]);

  return (
    <div className="proteinModelPane">
      <div id={id} ref={containerRef} className="proteinModelViewer" />
      <p className="muted">{status}</p>
    </div>
  );
}

export function ProteinStructurePanel({
  apiBase,
  uniprotAccession,
  position,
  proteinName,
  mutation,
}: {
  apiBase: string;
  uniprotAccession?: string | null;
  position?: number | null;
  proteinName?: string;
  mutation?: string;
}) {
  const [summary, setSummary] = useState<AlphaFoldSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestUrl = useMemo(() => {
    const accession = (uniprotAccession || "").trim();
    if (!accession) return "";
    const params = new URLSearchParams({ uniprot_accession: accession });
    if (position && position > 0) params.set("position", String(position));
    return `${apiBase}/api/structure/alphafold?${params.toString()}`;
  }, [apiBase, position, uniprotAccession]);

  useEffect(() => {
    if (!requestUrl) {
      setSummary(null);
      setError(null);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetch(requestUrl, { signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail ?? "AlphaFold request failed");
        return payload as AlphaFoldSummary;
      })
      .then((payload) => setSummary(payload))
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "AlphaFold request failed");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [requestUrl]);

  if (!uniprotAccession) {
    return (
      <div className="structurePanel">
        <h3>AlphaFold structure context</h3>
        <p>No UniProt accession was available for this protein, so AlphaFold cannot be queried for this run.</p>
      </div>
    );
  }

  return (
    <div className="structurePanel">
      <div className="structurePanelHeader">
        <div>
          <span className="eyebrow">AlphaFold structure context</span>
          <h3>{proteinName || uniprotAccession}</h3>
        </div>
        <span className={summary?.alphafold_available ? "sourceStatus available" : "sourceStatus unavailable"}>
          {loading ? "Checking AlphaFold" : summary?.alphafold_available ? "AlphaFold available" : "AlphaFold unavailable"}
        </span>
      </div>
      {mutation && <p className="muted">Variant being mapped: <strong>{mutation}</strong>{position ? ` at protein position ${position}` : ""}</p>}
      {loading && <p className="muted">Checking AlphaFold DB for {uniprotAccession}...</p>}
      {error && <p className="error compactError">{error}</p>}
      {summary && (
        <>
          <p>{summary.summary}</p>
          <div className="structureMetricGrid">
            <div><span>Accession</span><strong>{summary.uniprot_accession}</strong></div>
            <div><span>Position</span><strong>{summary.mutation_position ?? "unknown"}</strong></div>
            <div><span>Confidence</span><strong>{summary.confidence_label}</strong></div>
            <div><span>Residue pLDDT</span><strong>{formatConfidence(summary.residue_confidence)}</strong></div>
            <div><span>Global pLDDT</span><strong>{formatConfidence(summary.global_confidence)}</strong></div>
          </div>
          {summary.alphafold_available ? (
            <div className="proteinStructureGrid">
              <section>
                <h4>Before mutation</h4>
                <p className="muted">Native AlphaFold prediction for the selected UniProt accession.</p>
                <StructureViewer pdbUrl={summary.pdb_url} mode="before" position={summary.mutation_position} />
              </section>
              <section>
                <h4>After mutation impact map</h4>
                <p className="muted">Same AlphaFold structure with the typed mutation residue highlighted. This is not a fabricated mutant AlphaFold prediction.</p>
                <StructureViewer pdbUrl={summary.pdb_url} mode="after" position={summary.mutation_position} />
              </section>
              <div className="structureLinks">
                <a href={summary.pdb_url} target="_blank" rel="noreferrer">Open PDB</a>
                <a href={summary.mmcif_url || summary.cif_url} target="_blank" rel="noreferrer">Open mmCIF</a>
                <a href={summary.pae_url} target="_blank" rel="noreferrer">Open PAE</a>
              </div>
            </div>
          ) : (
            <p className="muted">{summary.message}</p>
          )}
        </>
      )}
    </div>
  );
}
