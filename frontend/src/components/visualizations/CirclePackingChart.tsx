import { useEffect, useRef } from "react";
import * as d3 from "d3";

export type CirclePackingDatum = {
  name: string;
  value?: number;
  type?: string;
  description?: string;
  children?: CirclePackingDatum[];
};

function cssVar(name: string, fallback: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

export function CirclePackingChart({
  data,
  title,
  description,
  height = 360,
}: {
  data: CirclePackingDatum;
  title?: string;
  description?: string;
  height?: number;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const wrap = wrapRef.current;
    const svgEl = svgRef.current;
    const tooltipEl = tooltipRef.current;
    if (!wrap || !svgEl || !tooltipEl) return;
    const width = Math.max(520, wrap.clientWidth || 720);
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${width} ${height}`);
    const muted = cssVar("--muted-text", "#64746f");
    if (!data.children?.length) {
      svg.append("text").attr("x", width / 2).attr("y", height / 2).attr("text-anchor", "middle").attr("fill", muted).text("No composition data available.");
      return;
    }
    const text = cssVar("--text", "#12201d");
    const accent = cssVar("--accent", "#237457");
    const danger = cssVar("--danger", "#b63f3f");
    const warning = cssVar("--warning", "#8a641d");
    const node = cssVar("--graph-node", "#dff3e9");
    const root = d3.hierarchy<CirclePackingDatum>(data).sum((d) => Math.max(0.01, Number(d.value ?? 0))).sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
    const pack = d3.pack<CirclePackingDatum>().size([width, height]).padding(8);
    const packed = pack(root);
    const color = d3.scaleOrdinal([accent, danger, warning, "#5986c7", node]);
    const tooltip = d3.select(tooltipEl);
    const show = (event: PointerEvent, d: d3.HierarchyCircularNode<CirclePackingDatum>) => {
      const rect = wrap.getBoundingClientRect();
      const raw = d.data as { name: string; value?: number; type?: string; description?: string };
      tooltip.html(`<strong>${raw.name}</strong><span>${raw.type || "component"} · ${((raw.value ?? 0) * 100).toFixed(1)}%</span><p>${raw.description || "Composition component."}</p>`).classed("visible", true).style("left", `${event.clientX - rect.left + 12}px`).style("top", `${event.clientY - rect.top + 12}px`);
    };
    const circles = svg.append("g").selectAll("g").data(packed.descendants().filter((d) => d.depth > 0)).join("g").attr("transform", (d) => `translate(${d.x},${d.y})`).on("pointerenter", (event, d) => show(event, d)).on("pointermove", (event, d) => show(event, d)).on("pointerleave", () => tooltip.classed("visible", false));
    circles.append("circle").attr("r", (d) => d.r).attr("fill", (_d, i) => color(String(i))).attr("opacity", 0.28).attr("stroke", (_d, i) => color(String(i))).attr("stroke-width", 2);
    circles.append("text").attr("text-anchor", "middle").attr("dy", -2).attr("fill", text).attr("font-size", (d) => Math.max(8, Math.min(13, d.r / 5))).attr("font-weight", 900).text((d) => d.r > 18 ? d.data.name : "");
    circles.append("text").attr("text-anchor", "middle").attr("dy", 14).attr("fill", muted).attr("font-size", 10).attr("font-weight", 800).text((d) => d.r > 18 && "value" in d.data ? `${(Number(d.data.value) * 100).toFixed(1)}%` : "");
    svg.append("text").attr("x", 18).attr("y", 26).attr("fill", text).attr("font-size", 14).attr("font-weight", 900).text(data.name);
  }, [data, height]);
  return <div className="d3ChartWrap" ref={wrapRef}>
    {(title || description) && <div className="d3ChartHeader"><div>{title && <h3>{title}</h3>}{description && <p className="muted">{description}</p>}</div></div>}
    <svg ref={svgRef} className="d3Svg" role="img" aria-label="Circle packing chart" />
    <div ref={tooltipRef} className="d3Tooltip" />
  </div>;
}
