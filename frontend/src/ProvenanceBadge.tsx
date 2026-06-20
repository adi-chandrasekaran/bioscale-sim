import type { ReactNode } from "react";
import type { ProvenanceCategory, ProvenanceEntry } from "./types";
import { InfoTooltip } from "./Help";
import type { TooltipHelp } from "./helpContent";

const CATEGORY_LABELS: Record<ProvenanceCategory, string> = {
  external_database: "External database evidence",
  local_curated: "Local curated knowledge",
  simulator_assumption: "Simulator assumption",
  computed_model: "Computed model output",
};

const CATEGORY_SHORT: Record<ProvenanceCategory, string> = {
  external_database: "External DB",
  local_curated: "Local KB",
  simulator_assumption: "Assumption",
  computed_model: "Computed",
};

type ProvenanceBadgeProps = {
  entry?: ProvenanceEntry;
  category?: ProvenanceCategory;
  source?: string;
  detail?: string;
  compact?: boolean;
};

export function ProvenanceBadge({ entry, category, source, detail, compact = false }: ProvenanceBadgeProps) {
  const cat = entry?.category ?? category;
  const src = entry?.source ?? source ?? "Unknown";
  const note = entry?.detail ?? detail;
  if (!cat) return null;

  return (
    <span
      className={`provenanceBadge provenance-${cat}${compact ? " compact" : ""}`}
      title={note ? `${CATEGORY_LABELS[cat]} — ${src}. ${note}` : `${CATEGORY_LABELS[cat]} — ${src}`}
    >
      <span className="provenanceCategory">{compact ? CATEGORY_SHORT[cat] : CATEGORY_LABELS[cat]}</span>
      <span className="provenanceSource">{src}</span>
    </span>
  );
}

type ProvenanceRowProps = {
  label: string;
  value: ReactNode;
  provenance?: ProvenanceEntry;
  help?: TooltipHelp;
};

export function ProvenanceRow({ label, value, provenance, help }: ProvenanceRowProps) {
  return (
    <div className="provenanceRow">
      <div className="provenanceRowMain">
        <span className="provenanceRowLabel">
          {label}
          {help && <InfoTooltip label={label} help={help} />}
        </span>
        <span className="provenanceRowValue">{value}</span>
      </div>
      {provenance && <ProvenanceBadge entry={provenance} compact />}
    </div>
  );
}

type CardSourceHeaderProps = {
  source: string;
  externalAvailable?: boolean;
  notice?: string;
};

export function CardSourceHeader({ source, externalAvailable, notice }: CardSourceHeaderProps) {
  return (
    <div className="cardSourceHeader">
      <ProvenanceBadge
        category={externalAvailable ? "external_database" : "local_curated"}
        source={source}
      />
      {notice && <p className="evidenceNotice">{notice}</p>}
    </div>
  );
}
