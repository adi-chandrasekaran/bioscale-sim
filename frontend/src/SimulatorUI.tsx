import React from "react";

export type SimulatorTab = "bioscale" | "evolution" | "intervention";

export function TabSwitcher({ value, onChange }: { value: SimulatorTab; onChange: (tab: SimulatorTab) => void }) {
  const tabs: Array<[SimulatorTab, string]> = [
    ["bioscale", "BioScale Simulator"],
    ["evolution", "Evolution Simulator"],
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

export function SimulatorPanel({ title, eyebrow, children, className = "" }: { title: string; eyebrow?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`card simulatorPanel wide ${className}`.trim()}>
      {eyebrow && <p className="eyebrow panelEyebrow">{eyebrow}</p>}
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export function MetricCard({ label, value, before }: { label: string; value: number | string; before?: number }) {
  const numeric = typeof value === "number" ? value : null;
  return (
    <div className="metricCard">
      <span>{label}</span>
      <strong>{numeric === null ? value : numeric.toFixed(2)}</strong>
      {before !== undefined && numeric !== null && <small>Before {before.toFixed(2)} · change {(numeric - before).toFixed(2)}</small>}
      {numeric !== null && numeric >= 0 && numeric <= 1 && <div className="barOuter"><div className="barInner" style={{ width: `${numeric * 100}%` }} /></div>}
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
