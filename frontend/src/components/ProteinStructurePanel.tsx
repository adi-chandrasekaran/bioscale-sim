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
  normal_residue?: string | null;
  mutant_residue?: string | null;
  domain_hit?: string | null;
  error_message?: string | null;
  pdb_proxy_url?: string;
  error?: string | null;
};

function formatConfidence(value: number | null | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(1) : "unknown";
}

async function load3Dmol() {
  if (window.$3Dmol) return window.$3Dmol;
  await import("3dmol");
  if (!window.$3Dmol) throw new Error("3Dmol could not initialize in this browser.");
  return window.$3Dmol;
}

function StructureViewer({
  apiBase,
  pdbUrl,
  pdbProxyUrl,
  mode,
  position,
}: {
  apiBase: string;
  pdbUrl: string;
  pdbProxyUrl?: string;
  mode: "before" | "after";
  position?: number | null;
}) {
  const id = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState("Loading interactive structure viewer...");
  const [debug, setDebug] = useState({
    finalPdbUrl: pdbUrl,
    directUrlWorked: false,
    backendProxyUsed: false,
    atomsLoaded: 0,
    residuesLoaded: 0,
    selectedResidueFound: false,
    selectedResiduePlddt: null as number | null,
    errorMessage: "",
  });
  const [interactiveReady, setInteractiveReady] = useState(false);

  useEffect(() => {
    const element = containerRef.current;
    if (!element || !pdbUrl) return;
    let cancelled = false;
    element.replaceChildren();
    setInteractiveReady(false);
    setStatus("Loading interactive structure viewer...");
    const proxyUrl = pdbProxyUrl?.startsWith("http") ? pdbProxyUrl : `${apiBase}${pdbProxyUrl || `/api/structure/alphafold/pdb?uniprot_accession=`}`;
    fetch(proxyUrl)
      .then((response) => {
        if (!response.ok) throw new Error("AlphaFold PDB file could not be loaded through backend proxy");
        return response.text();
      })
      .then(async (pdbText) => {
        if (cancelled || !element) return;
        const atoms = pdbText.split("\n").filter((line) => line.startsWith("ATOM  "));
        const residues = new Set(atoms.map((line) => line.slice(22, 26).trim()).filter(Boolean));
        const selectedResidueFound = Boolean(position && atoms.some((line) => Number.parseInt(line.slice(22, 26).trim(), 10) === position));
        const selectedResidueAtoms = position ? atoms.filter((line) => Number.parseInt(line.slice(22, 26).trim(), 10) === position) : [];
        const selectedResiduePlddt = selectedResidueAtoms.length
          ? selectedResidueAtoms.reduce((sum, line) => sum + Number.parseFloat(line.slice(60, 66).trim()), 0) / selectedResidueAtoms.length
          : null;
        setDebug({
          finalPdbUrl: pdbUrl,
          directUrlWorked: false,
          backendProxyUsed: true,
          atomsLoaded: atoms.length,
          residuesLoaded: residues.size,
          selectedResidueFound,
          selectedResiduePlddt: selectedResiduePlddt !== null && Number.isFinite(selectedResiduePlddt) ? selectedResiduePlddt : null,
          errorMessage: "",
        });
        const threeDmol = await load3Dmol();
        if (cancelled || !element) return;
        element.replaceChildren();
        const viewer = threeDmol.createViewer(element, { backgroundColor: "white" });
        viewer.addModel(pdbText, "pdb");
        viewer.setStyle({}, { cartoon: { color: "#8fbfa8" } });
        if (mode === "after" && position) {
          viewer.addStyle({ resi: position }, { stick: { color: "crimson", radius: 0.45 }, sphere: { color: "crimson", radius: 0.95 } });
          viewer.addResLabels({ resi: position }, { font: "Arial", fontSize: 14, fontColor: "black", backgroundColor: "white" });
          viewer.zoomTo({ resi: position });
        } else {
          viewer.zoomTo();
        }
        viewer.render();
        setInteractiveReady(true);
        setStatus(mode === "after" && position ? `Mutation residue ${position} highlighted.` : "Wild-type AlphaFold structure loaded.");
      })
      .catch((reason) => {
        if (!cancelled) {
          const message = reason instanceof Error ? reason.message : "Structure viewer failed to load.";
          setStatus(message);
          setDebug((current) => ({ ...current, backendProxyUsed: true, errorMessage: message }));
          setInteractiveReady(false);
        }
      });
    return () => {
      cancelled = true;
      if (element) element.replaceChildren();
    };
  }, [apiBase, mode, pdbProxyUrl, pdbUrl, position]);

  return (
    <div className="proteinModelPane">
      <div className={`proteinModelViewport${interactiveReady ? " ready" : ""}`}>
        <div id={id} ref={containerRef} className="proteinModelViewer" />
        {!interactiveReady && <div className="proteinModelLoading">{status}</div>}
      </div>
      <p className="muted">{status}</p>
      <details className="structureDebug">
        <summary>Structure debug</summary>
        <dl>
          <div><dt>PDB URL</dt><dd>{debug.finalPdbUrl}</dd></div>
          <div><dt>Direct URL load</dt><dd>{debug.directUrlWorked ? "worked" : "not used"}</dd></div>
          <div><dt>Backend proxy</dt><dd>{debug.backendProxyUsed ? "used" : "not used"}</dd></div>
          <div><dt>Atoms / residues</dt><dd>{debug.atomsLoaded} / {debug.residuesLoaded}</dd></div>
          <div><dt>Selected residue found</dt><dd>{debug.selectedResidueFound ? "yes" : "no"}</dd></div>
          <div><dt>Selected residue pLDDT</dt><dd>{debug.selectedResiduePlddt === null ? "unavailable" : debug.selectedResiduePlddt.toFixed(1)}</dd></div>
          {debug.errorMessage && <div><dt>Error</dt><dd>{debug.errorMessage}</dd></div>}
        </dl>
      </details>
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
    if (mutation) params.set("mutation", mutation);
    return `${apiBase}/api/structure/alphafold?${params.toString()}`;
  }, [apiBase, mutation, position, uniprotAccession]);

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
            <div><span>Residue change</span><strong>{summary.normal_residue && summary.mutant_residue ? `${summary.normal_residue}→${summary.mutant_residue}` : "not parsed"}</strong></div>
            <div><span>Domain hit</span><strong>{summary.domain_hit || "not mapped"}</strong></div>
          </div>
          {summary.alphafold_available ? (
            <div className="proteinStructureSingle">
              <section>
                <div className="proteinStructureSingleHeader">
                  <div>
                    <h4>AlphaFold reference structure</h4>
                    <p className="muted">
                      Native AlphaFold structure for {summary.uniprot_accession}
                      {summary.mutation_position ? ` with residue ${summary.mutation_position} highlighted` : ""}.
                      This maps the typed variant onto the reference model; it is not a fabricated mutant prediction.
                    </p>
                  </div>
                  {summary.normal_residue && summary.mutant_residue && (
                    <span className="sourceStatus available">{summary.normal_residue}→{summary.mutant_residue}</span>
                  )}
                </div>
                <StructureViewer apiBase={apiBase} pdbUrl={summary.pdb_url} pdbProxyUrl={summary.pdb_proxy_url} mode="after" position={summary.mutation_position} />
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
