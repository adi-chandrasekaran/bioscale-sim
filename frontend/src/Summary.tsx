import { useState } from "react";

type RawEvidenceProps = {
  title?: string;
  data: Record<string, unknown> | unknown;
};

export function RawEvidence({ title = "View raw evidence", data }: RawEvidenceProps) {
  const [open, setOpen] = useState(false);
  if (!data || (typeof data === "object" && Object.keys(data as object).length === 0)) return null;

  return (
    <details className="rawEvidence" open={open} onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary>{title}</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

type ConciseSummaryProps = {
  text?: string;
  className?: string;
};

export function ConciseSummary({ text, className = "conciseSummary" }: ConciseSummaryProps) {
  if (!text) return null;
  return <p className={className}>{text}</p>;
}
