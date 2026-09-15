import { useEffect, useMemo, useRef, useState } from "react";
import type { ArchitectureGraph } from "../types";

interface LayoutNode {
  id: string;
  label: string;
  kind: string;
  x: number;
  y: number;
}

export function ArchitectureCanvas({ graph }: { graph: ArchitectureGraph }) {
  const [query, setQuery] = useState("");
  const [showInternal, setShowInternal] = useState(true);
  const [showExternal, setShowExternal] = useState(true);
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 40, y: 40 });
  const drag = useRef<{ x: number; y: number } | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const filteredNodes = useMemo(
    () =>
      graph.nodes.filter((node) => {
        if (node.kind === "external") return showExternal;
        return showInternal;
      }),
    [graph.nodes, showExternal, showInternal],
  );

  const visibleIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);
  const highlighted = query.trim().toLowerCase();

  const layout = useMemo(() => {
    const internals = filteredNodes.filter((n) => n.kind !== "external");
    const externals = filteredNodes.filter((n) => n.kind === "external");
    const positioned: LayoutNode[] = [];
    const cols = Math.max(1, Math.ceil(Math.sqrt(internals.length || 1)));
    internals.forEach((node, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      positioned.push({ id: node.id, label: node.label, kind: node.kind, x: 80 + col * 220, y: 80 + row * 110 });
    });
    externals.forEach((node, i) => {
      positioned.push({
        id: node.id,
        label: node.label,
        kind: node.kind,
        x: 80 + (cols + 1) * 220,
        y: 80 + i * 70,
      });
    });
    return positioned;
  }, [filteredNodes]);

  const byId = useMemo(() => new Map(layout.map((n) => [n.id, n])), [layout]);
  const edges = graph.edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target));

  const fit = () => {
    if (!layout.length || !svgRef.current) {
      setScale(1);
      setPan({ x: 40, y: 40 });
      return;
    }
    const xs = layout.map((n) => n.x);
    const ys = layout.map((n) => n.y);
    const minX = Math.min(...xs) - 40;
    const minY = Math.min(...ys) - 40;
    const maxX = Math.max(...xs) + 180;
    const maxY = Math.max(...ys) + 60;
    const width = svgRef.current.clientWidth || 800;
    const height = svgRef.current.clientHeight || 500;
    const nextScale = Math.min(1.4, Math.max(0.25, Math.min(width / (maxX - minX), height / (maxY - minY))));
    setScale(nextScale);
    setPan({ x: -minX * nextScale + 20, y: -minY * nextScale + 20 });
  };

  useEffect(() => {
    fit();
  }, [graph]);

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 bg-slate-50 px-3 py-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search nodes"
          className="h-8 w-48 rounded-md border border-slate-200 bg-white px-2 text-sm"
        />
        <label className="flex items-center gap-1 text-xs text-slate-600">
          <input type="checkbox" checked={showInternal} onChange={(e) => setShowInternal(e.target.checked)} />
          Internal files
        </label>
        <label className="flex items-center gap-1 text-xs text-slate-600">
          <input type="checkbox" checked={showExternal} onChange={(e) => setShowExternal(e.target.checked)} />
          External imports
        </label>
        <div className="ml-auto flex gap-2">
          <button type="button" className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs" onClick={() => setScale((s) => Math.min(2, s * 1.15))}>
            Zoom in
          </button>
          <button type="button" className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs" onClick={() => setScale((s) => Math.max(0.2, s / 1.15))}>
            Zoom out
          </button>
          <button type="button" className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs" onClick={fit}>
            Fit
          </button>
        </div>
      </div>
      <svg
        ref={svgRef}
        className="h-[560px] w-full cursor-grab bg-slate-50"
        onWheel={(e) => {
          e.preventDefault();
          const delta = e.deltaY < 0 ? 1.08 : 0.92;
          setScale((s) => Math.min(2.5, Math.max(0.2, s * delta)));
        }}
        onMouseDown={(e) => {
          drag.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
        }}
        onMouseMove={(e) => {
          if (!drag.current) return;
          setPan({ x: e.clientX - drag.current.x, y: e.clientY - drag.current.y });
        }}
        onMouseUp={() => {
          drag.current = null;
        }}
        onMouseLeave={() => {
          drag.current = null;
        }}
      >
        <g transform={`translate(${pan.x} ${pan.y}) scale(${scale})`}>
          {edges.map((edge, i) => {
            const a = byId.get(edge.source);
            const b = byId.get(edge.target);
            if (!a || !b) return null;
            return (
              <line
                key={`${edge.source}-${edge.target}-${i}`}
                x1={a.x + 70}
                y1={a.y + 16}
                x2={b.x + 70}
                y2={b.y + 16}
                stroke={edge.kind === "external_import" ? "#93c5fd" : "#94a3b8"}
                strokeWidth={1}
              />
            );
          })}
          {layout.map((node) => {
            const match = highlighted && node.label.toLowerCase().includes(highlighted);
            const dim = Boolean(highlighted) && !match;
            return (
              <g key={node.id} opacity={dim ? 0.25 : 1}>
                <rect
                  x={node.x}
                  y={node.y}
                  width={160}
                  height={32}
                  rx={6}
                  fill={node.kind === "external" ? "#eff6ff" : "#ffffff"}
                  stroke={match ? "#2563eb" : "#e2e8f0"}
                />
                <title>{node.label}</title>
                <text x={node.x + 8} y={node.y + 20} fontSize={11} fill="#334155">
                  {node.label.length > 24 ? `${node.label.slice(0, 22)}…` : node.label}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      <div className="border-t border-slate-200 px-3 py-2 text-xs text-slate-500">
        {graph.internal_nodes} internal files · {graph.external_nodes} external modules · {graph.edges.length} edges from parsed imports
      </div>
    </div>
  );
}
