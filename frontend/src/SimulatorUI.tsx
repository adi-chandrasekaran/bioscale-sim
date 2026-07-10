import React from "react";
import { InfoTooltip, PanelHelpAccordion } from "./Help";
import type { PanelHelp, TooltipHelp } from "./helpContent";

export type SimulatorTab = "bioscale" | "evolution" | "digital-twin" | "intervention";

export function TabSwitcher({ value, onChange }: { value: SimulatorTab; onChange: (tab: SimulatorTab) => void }) {
  const tabs: Array<[SimulatorTab, string]> = [
    ["bioscale", "BioScale Simulator"],
    ["evolution", "Evolution Simulator"],
    ["digital-twin", "Patient Digital Twin"],
    ["intervention", "Intervention Simulator"],
  ];
  return (
    <nav className="simulatorTabs" aria-label="Simulator modes">
      {tabs.map(([id, label]) => (
        <button key={id} type="button" className={value === id ? "active" : ""} aria-current={value === id ? "page" : undefined} onClick={() => onChange(id)}>
          {label}
        </button>
      ))}
    </nav>
  );
}

export function SimulatorPanel({ title, eyebrow, children, className = "", help }: { title: string; eyebrow?: string; children: React.ReactNode; className?: string; help?: PanelHelp }) {
  return (
    <section className={`card simulatorPanel wide ${className}`.trim()}>
      <div className="simulatorPanelHeader">
        <div>
          {eyebrow && <p className="eyebrow panelEyebrow">{eyebrow}</p>}
          <h2>{title}</h2>
        </div>
        {help && <PanelHelpAccordion help={help} />}
      </div>
      {children}
    </section>
  );
}

function clamp01(value: number) {
  return Math.max(0, Math.min(1, value));
}

function formatPercent(value: number) {
  return `${Math.abs(value * 100).toFixed(0)}%`;
}

function buildMetricTooltip(label: string, value: number | string, before?: number, context?: string): TooltipHelp {
  const numeric = typeof value === "number" ? value : null;
  if (numeric === null) {
    return {
      title: label,
      summary: context ? `${label}: ${String(value)}. ${context}` : `${label}: ${String(value)}.`,
      details: [],
      examples: [],
    };
  }
  const baseline = before ?? 0.5;
  const delta = numeric - baseline;
  const direction = delta >= 0 ? "increase" : "decrease";
  const probabilityLine = `If this occurs, there is a probability that ${label} will ${direction} by ${formatPercent(delta)}.`;
  return {
    title: label,
    summary: probabilityLine,
    details: [
      `Current modeled probability is ${(numeric * 100).toFixed(0)}%.`,
      `Reference value is ${(baseline * 100).toFixed(0)}%.`,
      context ?? "This is a normalized simulator probability, not a clinical prediction.",
    ],
    examples: [],
  };
}

export function MetricCard({ label, value, before, help, context }: { label: string; value: number | string; before?: number; help?: TooltipHelp; context?: string }) {
  const numeric = typeof value === "number" ? value : null;
  const delta = numeric !== null ? numeric - (before ?? 0.5) : 0;
  const directionClass = numeric === null ? "" : delta < 0 ? "decreased" : "increased";
  const tooltip = help ?? buildMetricTooltip(label, value, before, context);
  return (
    <div className="metricCard">
      <span className="metricCardLabel">{label}<InfoTooltip label={label} help={tooltip} /></span>
      <strong>{numeric === null ? value : numeric.toFixed(2)}</strong>
      {before !== undefined && numeric !== null && <small>Before {before.toFixed(2)} · {delta >= 0 ? "increased" : "decreased"} by {formatPercent(delta)}</small>}
      {numeric !== null && numeric >= 0 && numeric <= 1 && <div className="barOuter"><div className={`barInner ${directionClass}`} style={{ width: `${clamp01(numeric) * 100}%` }} /></div>}
    </div>
  );
}

export function MiniLineChart({ series, ariaLabel }: { series: Array<{ name: string; color: string; points: Array<{ x: number; y: number }> }>; ariaLabel: string }) {
  const width = 800, height = 250, pad = 34;
  const maxX = Math.max(1, ...series.flatMap((item) => item.points.map((point) => point.x)));
  const path = (points: Array<{ x: number; y: number }>) => points.map((point) => `${pad + point.x / maxX * (width - pad * 2)},${height - pad - Math.max(0, Math.min(1, point.y)) * (height - pad * 2)}`).join(" ");
  return (
    <div className="miniChartWrap">
      <svg className="miniLineChart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} className="axis" />
        <line x1={pad} y1={pad} x2={pad} y2={height - pad} className="axis" />
        {series.map((item) => <polyline key={item.name} points={path(item.points)} fill="none" stroke={item.color} strokeWidth="5" strokeLinejoin="round" />)}
      </svg>
      <div className="chartLegend">{series.map((item) => <span key={item.name}><i style={{ background: item.color }} />{item.name}</span>)}</div>
    </div>
  );
}

export function CloneBadge({ name, fitness }: { name: string; fitness: number }) {
  return <span className="cloneBadge"><b>{name}</b> fitness {fitness.toFixed(2)}</span>;
}
