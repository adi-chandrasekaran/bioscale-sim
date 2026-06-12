import { useEffect, useRef } from "react";
import * as d3 from "d3";
import type { Edge, NodeState } from "./types";

const WIDTH = 960;
const HEIGHT = 280;
const NODE_RADIUS = 30;

const POSITIONS: Record<string, { x: number; y: number }> = {
  DNA_DAMAGE: { x: 80, y: 150 },
  ATM: { x: 220, y: 150 },
  TP53: { x: 360, y: 150 },
  MDM2: { x: 360, y: 55 },
  CDKN1A: { x: 520, y: 85 },
  BAX: { x: 520, y: 210 },
  DNA_REPAIR: { x: 520, y: 150 },
  CELL_CYCLE_ARREST: { x: 700, y: 85 },
  APOPTOSIS: { x: 700, y: 210 },
  PROLIFERATION_SIGNAL: { x: 870, y: 150 },
};

function fmt(value: number) {
  return Number.isFinite(value) ? value.toFixed(2) : "—";
}

function trimLink(
  source: { x: number; y: number },
  target: { x: number; y: number },
  radius: number,
  arrowGap = 10,
) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const dist = Math.hypot(dx, dy) || 1;
  const ux = dx / dist;
  const uy = dy / dist;
  return {
    x1: source.x + ux * radius,
    y1: source.y + uy * radius,
    x2: target.x - ux * (radius + arrowGap),
    y2: target.y - uy * (radius + arrowGap),
  };
}

type LayoutNode = NodeState & { x: number; y: number };
type LayoutEdge = Edge & { x1: number; y1: number; x2: number; y2: number; key: string };

function buildLayout(nodes: NodeState[], edges: Edge[]): { layoutNodes: LayoutNode[]; layoutEdges: LayoutEdge[] } {
  const layoutNodes: LayoutNode[] = nodes.map((node) => {
    const pos = POSITIONS[node.id] ?? { x: 50, y: 50 };
    return { ...node, x: pos.x, y: pos.y };
  });
  const nodeById = Object.fromEntries(layoutNodes.map((n) => [n.id, n]));

  const layoutEdges: LayoutEdge[] = edges
    .map((edge) => {
      const source = nodeById[edge.source];
      const target = nodeById[edge.target];
      if (!source || !target) return null;
      const { x1, y1, x2, y2 } = trimLink(source, target, NODE_RADIUS);
      return { ...edge, x1, y1, x2, y2, key: `${edge.source}-${edge.target}` };
    })
    .filter((edge): edge is LayoutEdge => edge !== null);

  return { layoutNodes, layoutEdges };
}

function appendMarkers(defs: d3.Selection<SVGDefsElement, unknown, null, undefined>) {
  const activate = defs
    .append("marker")
    .attr("id", "pathway-arrow-activate")
    .attr("viewBox", "0 -3 8 6")
    .attr("refX", 7)
    .attr("refY", 0)
    .attr("markerWidth", 8)
    .attr("markerHeight", 8)
    .attr("orient", "auto");
  activate.append("path").attr("d", "M0,-3L8,0L0,3").attr("fill", "#237457");

  const inhibit = defs
    .append("marker")
    .attr("id", "pathway-arrow-inhibit")
    .attr("viewBox", "0 -3 8 6")
    .attr("refX", 7)
    .attr("refY", 0)
    .attr("markerWidth", 8)
    .attr("markerHeight", 8)
    .attr("orient", "auto");
  inhibit.append("path").attr("d", "M0,-3L8,0L0,3").attr("fill", "#9c4d4d");
}

function nodeTooltipHtml(node: LayoutNode) {
  const deltaSign = node.delta > 0 ? "+" : "";
  const trend =
    node.delta < -0.1 ? '<span class="pathwayTooltipTrend down">down</span>'
    : node.delta > 0.1 ? '<span class="pathwayTooltipTrend up">up</span>'
    : '<span class="pathwayTooltipTrend neutral">stable</span>';

  return `
    <strong>${node.id.replaceAll("_", " ")}</strong>
    <span class="pathwayTooltipType">${node.type.replaceAll("_", " ")}</span>
    <dl>
      <div><dt>Activity</dt><dd>${fmt(node.activity)}</dd></div>
      <div><dt>Baseline</dt><dd>${fmt(node.baseline)}</dd></div>
      <div><dt>Change</dt><dd>${deltaSign}${fmt(node.delta)} ${trend}</dd></div>
    </dl>
  `;
}

function edgeTooltipHtml(edge: LayoutEdge) {
  const verb = edge.relation === "inhibits" ? "inhibits" : "activates";
  return `
    <strong>${edge.source.replaceAll("_", " ")} → ${edge.target.replaceAll("_", " ")}</strong>
    <span class="pathwayTooltipType">${verb} · weight ${fmt(edge.weight)}</span>
    <p class="pathwayTooltipHint">Click to pin this interaction</p>
  `;
}

export function PathwayGraph({ nodes, edges }: { nodes: NodeState[]; edges: Edge[] }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wrapEl = wrapRef.current;
    const svgEl = svgRef.current;
    const tooltipEl = tooltipRef.current;
    if (!wrapEl || !svgEl || !tooltipEl) return;

    const { layoutNodes, layoutEdges } = buildLayout(nodes, edges);
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${WIDTH} ${HEIGHT}`);

    let hoveredNodeId: string | null = null;
    let hoveredEdgeKey: string | null = null;
    let selectedNodeId: string | null = null;
    let selectedEdgeKey: string | null = null;

    const tooltip = d3.select(tooltipEl);

    function hideTooltip() {
      tooltip.classed("visible", false);
    }

    function showTooltip(html: string, event: PointerEvent) {
      const rect = wrapEl!.getBoundingClientRect();
      tooltip
        .html(html)
        .classed("visible", true)
        .style("left", `${event.clientX - rect.left + 14}px`)
        .style("top", `${event.clientY - rect.top - 10}px`);
    }

    function neighborsOf(nodeId: string) {
      const neighborIds = new Set<string>([nodeId]);
      const edgeKeys = new Set<string>();
      for (const edge of layoutEdges) {
        if (edge.source === nodeId || edge.target === nodeId) {
          neighborIds.add(edge.source);
          neighborIds.add(edge.target);
          edgeKeys.add(edge.key);
        }
      }
      return { neighborIds, edgeKeys };
    }

    function endpointsOf(edgeKey: string) {
      const edge = layoutEdges.find((e) => e.key === edgeKey);
      if (!edge) return { nodeIds: new Set<string>(), edgeKeys: new Set<string>() };
      return {
        nodeIds: new Set([edge.source, edge.target]),
        edgeKeys: new Set([edge.key]),
      };
    }

    function applyFocus() {
      const focusNodeId = hoveredNodeId ?? selectedNodeId;
      const focusEdgeKey = hoveredEdgeKey ?? selectedEdgeKey;

      let activeNodeIds: Set<string> | null = null;
      let activeEdgeKeys: Set<string> | null = null;

      if (focusEdgeKey) {
        const { nodeIds, edgeKeys } = endpointsOf(focusEdgeKey);
        activeNodeIds = nodeIds;
        activeEdgeKeys = edgeKeys;
      } else if (focusNodeId) {
        const { neighborIds, edgeKeys } = neighborsOf(focusNodeId);
        activeNodeIds = neighborIds;
        activeEdgeKeys = edgeKeys;
      }

      const hasFocus = activeNodeIds !== null;

      nodeSelection
        .classed("dimmed", (d) => hasFocus && !activeNodeIds!.has(d.id))
        .classed("highlighted", (d) => hasFocus && activeNodeIds!.has(d.id))
        .classed("selected", (d) => d.id === selectedNodeId)
        .attr("transform", (d) => {
          const scale =
            d.id === hoveredNodeId ? 1.1
            : d.id === selectedNodeId ? 1.06
            : 1;
          return `translate(${d.x},${d.y}) scale(${scale})`;
        });

      edgeSelection
        .classed("dimmed", (d) => hasFocus && !activeEdgeKeys!.has(d.key))
        .classed("highlighted", (d) => hasFocus && activeEdgeKeys!.has(d.key))
        .classed("selected", (d) => d.key === selectedEdgeKey)
        .attr("stroke-width", (d) => {
          const base = 2 + d.weight * 2;
          if (d.key === hoveredEdgeKey || d.key === selectedEdgeKey) return base + 2;
          if (hasFocus && activeEdgeKeys!.has(d.key)) return base + 1;
          return base;
        });
    }

    function clearSelection() {
      selectedNodeId = null;
      selectedEdgeKey = null;
      hideTooltip();
      applyFocus();
    }

    const defs = svg.append("defs");
    appendMarkers(defs);

    svg
      .append("rect")
      .attr("class", "pathwayBackground")
      .attr("width", WIDTH)
      .attr("height", HEIGHT)
      .attr("fill", "transparent")
      .on("click", clearSelection);

    const edgeGroup = svg.append("g").attr("class", "edges");

    const edgeSelection = edgeGroup
      .selectAll<SVGGElement, LayoutEdge>("g.pathway-edge")
      .data(layoutEdges, (d) => d.key)
      .join("g")
      .attr("class", "pathway-edge")
      .style("cursor", "pointer");

    edgeSelection
      .append("line")
      .attr("class", (d) => (d.relation === "inhibits" ? "edge inhibit edge-visible" : "edge activate edge-visible"))
      .attr("x1", (d) => d.x1)
      .attr("y1", (d) => d.y1)
      .attr("x2", (d) => d.x2)
      .attr("y2", (d) => d.y2)
      .attr("stroke-width", (d) => 2 + d.weight * 2)
      .attr("marker-end", (d) =>
        d.relation === "inhibits" ? "url(#pathway-arrow-inhibit)" : "url(#pathway-arrow-activate)",
      )
      .attr("pointer-events", "none");

    edgeSelection
      .append("line")
      .attr("class", "edge-hit")
      .attr("x1", (d) => d.x1)
      .attr("y1", (d) => d.y1)
      .attr("x2", (d) => d.x2)
      .attr("y2", (d) => d.y2)
      .on("pointerenter", function (event, d) {
        hoveredEdgeKey = d.key;
        hoveredNodeId = null;
        showTooltip(edgeTooltipHtml(d), event);
        applyFocus();
      })
      .on("pointermove", function (event, d) {
        showTooltip(edgeTooltipHtml(d), event);
      })
      .on("pointerleave", () => {
        hoveredEdgeKey = null;
        if (!selectedEdgeKey && !selectedNodeId) hideTooltip();
        applyFocus();
      })
      .on("click", (event, d) => {
        event.stopPropagation();
        selectedEdgeKey = selectedEdgeKey === d.key ? null : d.key;
        selectedNodeId = null;
        applyFocus();
      });

    const nodeGroup = svg.append("g").attr("class", "nodes");

    const nodeSelection = nodeGroup
      .selectAll<SVGGElement, LayoutNode>("g.pathway-node")
      .data(layoutNodes, (d) => d.id)
      .join("g")
      .attr("class", "pathway-node")
      .attr("transform", (d) => `translate(${d.x},${d.y})`)
      .style("cursor", "pointer");

    nodeSelection
      .append("circle")
      .attr("r", NODE_RADIUS)
      .attr("class", "nodeCircle")
      .attr("opacity", (d) => 0.45 + Math.max(0.1, Math.min(1, d.activity)) * 0.55);

    nodeSelection
      .append("circle")
      .attr("r", NODE_RADIUS + 6)
      .attr("class", "nodeHit")
      .attr("fill", "transparent")
      .on("pointerenter", function (event, d) {
        hoveredNodeId = d.id;
        hoveredEdgeKey = null;
        showTooltip(nodeTooltipHtml(d), event);
        applyFocus();
      })
      .on("pointermove", function (event, d) {
        showTooltip(nodeTooltipHtml(d), event);
      })
      .on("pointerleave", () => {
        hoveredNodeId = null;
        if (!selectedNodeId && !selectedEdgeKey) hideTooltip();
        applyFocus();
      })
      .on("click", (event, d) => {
        event.stopPropagation();
        selectedNodeId = selectedNodeId === d.id ? null : d.id;
        selectedEdgeKey = null;
        applyFocus();
      });

    nodeSelection.each(function (d) {
      const g = d3.select(this);
      g.append("text")
        .attr("text-anchor", "middle")
        .attr("y", -4)
        .attr("class", "nodeLabel")
        .attr("pointer-events", "none")
        .text(d.id.replaceAll("_", " "));

      g.append("text")
        .attr("text-anchor", "middle")
        .attr("y", 13)
        .attr("class", "nodeValue")
        .attr("pointer-events", "none")
        .text(fmt(d.activity));

      if (d.delta < -0.1) {
        g.append("text")
          .attr("text-anchor", "middle")
          .attr("y", 46)
          .attr("class", "downText")
          .attr("pointer-events", "none")
          .text("down");
      } else if (d.delta > 0.1) {
        g.append("text")
          .attr("text-anchor", "middle")
          .attr("y", 46)
          .attr("class", "upText")
          .attr("pointer-events", "none")
          .text("up");
      }
    });

    return () => {
      hideTooltip();
    };
  }, [nodes, edges]);

  return (
    <div className="pathwayGraphWrap" ref={wrapRef}>
      <svg
        ref={svgRef}
        className="pathwaySvg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Interactive pathway graph. Hover or click nodes and edges for details."
      />
      <div className="pathwayTooltip" ref={tooltipRef} aria-hidden="true" />
    </div>
  );
}
