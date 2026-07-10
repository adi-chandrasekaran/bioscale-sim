import { useEffect, useRef } from "react";
import * as d3 from "d3";

export type CloneTreeNode = {
  id?: string;
  name: string;
  value?: number;
  type?: string;
  description?: string;
  mutations?: string[];
  fitness?: number;
  population?: number;
  final_share?: number;
  peak_share?: number;
  generation_step?: number;
  fitness_score?: number;
  details?: Record<string, any>;
  children?: CloneTreeNode[];
};

function cssVar(name: string, fallback: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

export function CloneTree({ data, title, onSelect, height = 420 }: { data: CloneTreeNode | null; title?: string; onSelect?: (cloneId: string) => void; height?: number }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const wrap = wrapRef.current;
    const svgEl = svgRef.current;
    const tooltipEl = tooltipRef.current;
    if (!wrap || !svgEl || !tooltipEl) return;
    const width = Math.max(620, wrap.clientWidth || 760);
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${width} ${height}`);
    const muted = cssVar("--muted-text", "#64746f");
    if (!data) {
      svg.append("text").attr("x", width / 2).attr("y", height / 2).attr("text-anchor", "middle").attr("fill", muted).text("No clone tree available.");
      return;
    }
    const text = cssVar("--text", "#12201d");
    const accent = cssVar("--accent", "#237457");
    const border = cssVar("--border", "#dce9df");
    const graphNode = cssVar("--graph-node", "#dff3e9");
    const hierarchy = d3.hierarchy(data);
    const tree = d3.tree<CloneTreeNode>().size([width - 120, height - 110]);
    const pointRoot = tree(hierarchy);
    const tooltip = d3.select(tooltipEl);
    const show = (event: PointerEvent, d: d3.HierarchyPointNode<CloneTreeNode>) => {
      const rect = wrap.getBoundingClientRect();
      const details = d.data.details ?? {};
      const fitnessValue = d.data.fitness_score ?? d.data.fitness ?? details.fitness_score;
      const finalShare = d.data.final_share ?? d.data.value ?? details.final_share;
      const peakShare = d.data.peak_share ?? details.peak_share;
      const fitness = typeof fitnessValue === "number" ? `fitness ${fitnessValue.toFixed(2)}` : typeof d.data.value === "number" ? `${(d.data.value * 100).toFixed(1)}% final share` : "fitness unknown";
      const population = typeof d.data.population === "number" ? ` · population ${Math.round(d.data.population).toLocaleString()}` : "";
      const detail = d.data.description || details.biological_interpretation || d.data.mutations?.join(" · ") || d.data.type || "Clone lineage node.";
      tooltip.html(`
        <strong>${d.data.name}</strong>
        <span>${fitness}${population}</span>
        <p>${detail}</p>
        <p>Parent: ${details.parent || details.parent_clone_id || "founding clone"} · Step ${d.data.generation_step ?? details.generation_step ?? 0}</p>
        <p>Development: ${details.new_mutation_or_development || d.data.type || "not specified"}</p>
        <p>Final ${(Number(finalShare ?? 0) * 100).toFixed(1)}% · Peak ${(Number(peakShare ?? finalShare ?? 0) * 100).toFixed(1)}% · Confidence ${(Number(details.confidence_score ?? 0) * 100).toFixed(0)}%</p>
        <p>${details.why_it_emerged || ""}</p>
        <p>${details.why_it_expanded_or_declined || ""}</p>
      `).classed("visible", true).style("left", `${event.clientX - rect.left + 12}px`).style("top", `${event.clientY - rect.top + 12}px`);
    };
    svg.append("g").attr("transform", "translate(60,40)").selectAll("path").data(pointRoot.links()).join("path").attr("fill", "none").attr("stroke", border).attr("stroke-width", 3).attr("d", d3.linkVertical<d3.HierarchyPointLink<CloneTreeNode>, d3.HierarchyPointNode<CloneTreeNode>>().x((d) => d.x).y((d) => d.y));
    const node = svg.append("g").attr("transform", "translate(60,40)").selectAll("g").data(pointRoot.descendants()).join("g").attr("transform", (d) => `translate(${d.x},${d.y})`).style("cursor", "pointer").on("pointerenter", (event, d) => show(event, d)).on("pointermove", (event, d) => show(event, d)).on("pointerleave", () => tooltip.classed("visible", false)).on("click", (_event, d) => {
      const id = d.data.id || d.data.details?.clone_id;
      if (id && onSelect) onSelect(String(id));
    });
    node.append("circle").attr("r", (d) => 18 + (d.data.fitness ?? d.data.value ?? 0.35) * 16).attr("fill", graphNode).attr("stroke", accent).attr("stroke-width", 2);
    node.append("text").attr("text-anchor", "middle").attr("dy", 4).attr("fill", text).attr("font-size", 11).attr("font-weight", 900).text((d) => d.data.name);
    node.append("text").attr("text-anchor", "middle").attr("dy", 30).attr("fill", muted).attr("font-size", 10).attr("font-weight", 800).text((d) => `${((d.data.final_share ?? d.data.value ?? 0) * 100).toFixed(1)}%`);
  }, [data, height, onSelect]);
  return <div className="d3ChartWrap" ref={wrapRef}>
    {title && <div className="d3ChartHeader"><div><h3>{title}</h3></div></div>}
    <svg ref={svgRef} className="d3Svg" role="img" aria-label="Clone tree" />
    <div ref={tooltipRef} className="d3Tooltip" />
  </div>;
}
