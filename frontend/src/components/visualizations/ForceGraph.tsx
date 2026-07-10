import { useEffect, useRef } from "react";
import * as d3 from "d3";

export type ForceGraphNode = {
  id: string;
  label: string;
  type?: string;
  value?: number;
  source?: string;
  description?: string;
};

export type ForceGraphLink = {
  source: string;
  target: string;
  relation?: string;
  weight?: number;
  sourceType?: string;
  description?: string;
};

type SimNode = ForceGraphNode & d3.SimulationNodeDatum;
type SimLink = d3.SimulationLinkDatum<SimNode> & ForceGraphLink;

function themeColor(name: string, fallback: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

function linkEndpointLabel(endpoint: string | SimNode) {
  return typeof endpoint === "string" ? endpoint : endpoint.label || endpoint.id;
}

export function ForceGraph({
  nodes,
  links,
  selectedNodeId,
  title,
  description,
  height = 360,
}: {
  nodes: ForceGraphNode[];
  links: ForceGraphLink[];
  selectedNodeId?: string;
  title?: string;
  description?: string;
  height?: number;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const svgEl = svgRef.current;
    const wrapEl = wrapRef.current;
    const tooltipEl = tooltipRef.current;
    if (!svgEl || !wrapEl || !tooltipEl) return;

    const width = Math.max(620, wrapEl.clientWidth || 760);
    const text = themeColor("--text", "#12201d");
    const muted = themeColor("--muted-text", "#64746f");
    const accent = themeColor("--accent", "#237457");
    const border = themeColor("--border", "#dce9df");
    const danger = themeColor("--danger", "#b63f3f");
    const nodeFill = themeColor("--graph-node", "#dff3e9");
    const panel = themeColor("--panel-bg", "#ffffff");

    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${width} ${height}`);

    if (!nodes.length) {
      svg.append("text").attr("x", width / 2).attr("y", height / 2).attr("text-anchor", "middle").attr("fill", muted).text("No graph data available.");
      return;
    }

    const simNodes: SimNode[] = nodes.map((node) => ({ ...node }));
    const simLinks: SimLink[] = links.map((link) => ({ ...link }));
    const linked = new Set(simLinks.flatMap((link) => [String(link.source), String(link.target)]));

    const tooltip = d3.select(tooltipEl);
    const showTooltip = (event: PointerEvent, html: string) => {
      const rect = wrapEl.getBoundingClientRect();
      tooltip.html(html).classed("visible", true).style("left", `${event.clientX - rect.left + 12}px`).style("top", `${event.clientY - rect.top + 12}px`);
    };
    const hideTooltip = () => tooltip.classed("visible", false);

    const linkGroup = svg.append("g");
    const nodeGroup = svg.append("g");
    const labelGroup = svg.append("g");

    let simulation: d3.Simulation<SimNode, SimLink>;

    const linkSelection = linkGroup.selectAll("line")
      .data(simLinks)
      .join("line")
      .attr("stroke", (d) => d.relation === "inhibits" ? danger : accent)
      .attr("stroke-width", (d) => 1.5 + (d.weight ?? 0.5) * 3)
      .attr("stroke-opacity", 0.55)
      .on("pointerenter", (event, d) => showTooltip(event, `<strong>${linkEndpointLabel(d.source as string | SimNode)} → ${linkEndpointLabel(d.target as string | SimNode)}</strong><span>${d.relation || "connected"} · weight ${(d.weight ?? 0).toFixed(2)}</span><p>${d.description || "This edge propagates activity from one pathway step to the next."}</p>`))
      .on("pointermove", (event, d) => showTooltip(event, `<strong>${linkEndpointLabel(d.source as string | SimNode)} → ${linkEndpointLabel(d.target as string | SimNode)}</strong><span>${d.relation || "connected"} · weight ${(d.weight ?? 0).toFixed(2)}</span><p>${d.description || "This edge propagates activity from one pathway step to the next."}</p>`))
      .on("pointerleave", hideTooltip);

    const dragBehavior = d3.drag<SVGCircleElement, SimNode>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = d.x;
        d.fy = d.y;
      });

    const nodeSelection = nodeGroup.selectAll<SVGCircleElement, SimNode>("circle")
      .data(simNodes)
      .join("circle")
      .attr("r", (d) => 16 + Math.max(0.1, d.value ?? 0.5) * 16)
      .attr("fill", (d) => linked.has(d.id) ? nodeFill : panel)
      .attr("stroke", accent)
      .attr("stroke-width", (d) => d.id === selectedNodeId ? 4 : 2)
      .call(dragBehavior)
      .on("pointerenter", (event, d) => showTooltip(event, `<strong>${d.label}</strong><span>${d.type || "node"} · ${d.source || "computed model"}</span><p>${d.description || "No description available."}</p>`))
      .on("pointermove", (event, d) => showTooltip(event, `<strong>${d.label}</strong><span>${d.type || "node"} · ${d.source || "computed model"}</span><p>${d.description || "No description available."}</p>`))
      .on("pointerleave", hideTooltip);

    const labelSelection = labelGroup.selectAll("text")
      .data(simNodes)
      .join("text")
      .text((d) => d.label)
      .attr("text-anchor", "middle")
      .attr("dy", 4)
      .attr("fill", text)
      .attr("font-size", 11)
      .attr("font-weight", 900)
      .style("pointer-events", "none");

    const relationSelection = labelGroup.selectAll("text.relation")
      .data(simLinks)
      .join("text")
      .attr("class", "relation")
      .text((d) => d.relation || "")
      .attr("fill", muted)
      .attr("font-size", 10)
      .attr("font-weight", 800)
      .style("pointer-events", "none");

    simulation = d3.forceSimulation(simNodes)
      .force("link", d3.forceLink<SimNode, SimLink>(simLinks).id((d) => d.id).distance(145).strength((d) => Math.max(0.2, d.weight ?? 0.5)))
      .force("charge", d3.forceManyBody().strength(-420))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide<SimNode>().radius((d) => 34 + Math.max(0.1, d.value ?? 0.5) * 16));

    svg.append("rect").attr("x", 1).attr("y", 1).attr("width", width - 2).attr("height", height - 2).attr("rx", 18).attr("fill", "none").attr("stroke", border);

    simulation.on("tick", () => {
      linkSelection
        .attr("x1", (d) => (d.source as SimNode).x ?? 0)
        .attr("y1", (d) => (d.source as SimNode).y ?? 0)
        .attr("x2", (d) => (d.target as SimNode).x ?? 0)
        .attr("y2", (d) => (d.target as SimNode).y ?? 0);
      nodeSelection.attr("cx", (d) => d.x ?? 0).attr("cy", (d) => d.y ?? 0);
      labelSelection.attr("x", (d) => d.x ?? 0).attr("y", (d) => d.y ?? 0);
      relationSelection
        .attr("x", (d) => (((d.source as SimNode).x ?? 0) + ((d.target as SimNode).x ?? 0)) / 2)
        .attr("y", (d) => (((d.source as SimNode).y ?? 0) + ((d.target as SimNode).y ?? 0)) / 2);
    });

    return () => {
      simulation.stop();
    };
  }, [nodes, links, selectedNodeId, height]);

  return <div className="d3ChartWrap" ref={wrapRef}>
    {(title || description) && <div className="d3ChartHeader"><div>{title && <h3>{title}</h3>}{description && <p className="muted">{description}</p>}</div></div>}
    <svg ref={svgRef} className="d3Svg" role="img" aria-label="Force-directed biological graph" />
    <div ref={tooltipRef} className="d3Tooltip" />
  </div>;
}
