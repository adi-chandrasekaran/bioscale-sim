import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";

export type TimelineSeries = {
  id: string;
  label: string;
  values: Array<{ step: number; value: number; population?: number; event?: string }>;
  description?: string;
};

function cssVar(name: string, fallback: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

export function TimelineChart({
  series,
  title,
  yLabel,
  height = 280,
}: {
  series: TimelineSeries[];
  title?: string;
  yLabel?: string;
  height?: number;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [hiddenIds, setHiddenIds] = useState<Set<string>>(() => new Set());
  const visibleSeries = useMemo(() => series.filter((item) => !hiddenIds.has(item.id)), [hiddenIds, series]);
  useEffect(() => {
    const wrap = wrapRef.current;
    const svgEl = svgRef.current;
    const tooltipEl = tooltipRef.current;
    if (!wrap || !svgEl || !tooltipEl) return;
    const width = Math.max(620, wrap.clientWidth || 760);
    const margin = { top: 24, right: 24, bottom: 38, left: 46 };
    const text = cssVar("--text", "#12201d");
    const muted = cssVar("--muted-text", "#64746f");
    const border = cssVar("--border", "#dce9df");
    const colors = [cssVar("--accent", "#237457"), "#d18b3f", cssVar("--danger", "#b63f3f"), "#5986c7"];
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${width} ${height}`);
    if (!visibleSeries.length || visibleSeries.every((item) => item.values.length === 0)) {
      svg.append("text").attr("x", width / 2).attr("y", height / 2).attr("text-anchor", "middle").attr("fill", muted).text("No timeline data available.");
      return;
    }
    const all = visibleSeries.flatMap((item) => item.values);
    const x = d3.scaleLinear().domain(d3.extent(all, (d) => d.step) as [number, number]).nice().range([margin.left, width - margin.right]);
    const y = d3.scaleLinear().domain([0, Math.max(1, d3.max(all, (d) => d.value) ?? 1)]).nice().range([height - margin.bottom, margin.top]);
    const line = d3.line<{ step: number; value: number }>().x((d) => x(d.step)).y((d) => y(d.value)).curve(d3.curveMonotoneX);
    const tooltip = d3.select(tooltipEl);
    const show = (event: PointerEvent, label: string, point: { step: number; value: number; population?: number; event?: string }) => {
      const rect = wrap.getBoundingClientRect();
      tooltip.html(`<strong>${label}</strong><span>step ${point.step} · ${(point.value * 100).toFixed(1)}%</span><p>${point.population !== undefined ? `Population size: ${point.population.toLocaleString()}. ` : ""}${point.event || "No major event at this sampled step."}</p>`).classed("visible", true).style("left", `${event.clientX - rect.left + 12}px`).style("top", `${event.clientY - rect.top + 12}px`);
    };
    svg.append("g").attr("transform", `translate(0,${height - margin.bottom})`).call(d3.axisBottom(x).ticks(6)).call((g) => g.selectAll("text").attr("fill", muted)).call((g) => g.selectAll("path,line").attr("stroke", border));
    svg.append("g").attr("transform", `translate(${margin.left},0)`).call(d3.axisLeft(y).ticks(5).tickFormat((d) => `${Number(d) * 100}%`)).call((g) => g.selectAll("text").attr("fill", muted)).call((g) => g.selectAll("path,line").attr("stroke", border));
    visibleSeries.forEach((item, index) => {
      const color = colors[index % colors.length];
      svg.append("path").datum(item.values).attr("fill", "none").attr("stroke", color).attr("stroke-width", 4).attr("d", line);
      svg.selectAll(`circle.${item.id}`).data(item.values).join("circle").attr("r", 4).attr("fill", color).attr("cx", (d) => x(d.step)).attr("cy", (d) => y(d.value)).on("pointerenter", (event, d) => show(event, item.label, d)).on("pointermove", (event, d) => show(event, item.label, d)).on("pointerleave", () => tooltip.classed("visible", false));
      svg.append("text").attr("x", width - margin.right - 110).attr("y", margin.top + index * 18).attr("fill", text).attr("font-size", 12).attr("font-weight", 800).text(item.label);
      svg.append("circle").attr("cx", width - margin.right - 124).attr("cy", margin.top + index * 18 - 4).attr("r", 5).attr("fill", color);
      const last = item.values[item.values.length - 1];
      if (last) {
        svg.append("text")
          .attr("x", Math.min(width - margin.right - 6, x(last.step) + 8))
          .attr("y", y(last.value))
          .attr("fill", color)
          .attr("font-size", 11)
          .attr("font-weight", 900)
          .text(`${(last.value * 100).toFixed(1)}%`);
      }
    });
    if (yLabel) {
      svg.append("text").attr("x", 12).attr("y", 18).attr("fill", muted).attr("font-size", 11).attr("font-weight", 900).text(yLabel);
    }
  }, [visibleSeries, yLabel, height]);
  return <div className="d3ChartWrap" ref={wrapRef}>
    {title && <div className="d3ChartHeader"><div><h3>{title}</h3></div></div>}
    <div className="timelineToggleList" aria-label="Clone timeline toggles">
      {series.map((item) => {
        const final = item.values[item.values.length - 1]?.value ?? 0;
        const hidden = hiddenIds.has(item.id);
        return (
          <button
            key={item.id}
            type="button"
            className={hidden ? "timelineToggle off" : "timelineToggle"}
            onClick={() => setHiddenIds((current) => {
              const next = new Set(current);
              if (next.has(item.id)) next.delete(item.id);
              else next.add(item.id);
              return next;
            })}
          >
            {item.label} <span>{(final * 100).toFixed(1)}%</span>
          </button>
        );
      })}
    </div>
    <svg ref={svgRef} className="d3Svg" role="img" aria-label="Timeline chart" />
    <div ref={tooltipRef} className="d3Tooltip" />
  </div>;
}
