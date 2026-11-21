import { ChevronRight, TriangleAlert, Waypoints } from "lucide-react";
import { useMemo, useState } from "react";
import { edgeKey, layoutGraph, NODE_H, NODE_W, pathEdgeKeys, type PositionedNode } from "../../domain/graphLayout";
import { EDGE_TYPE_LABEL, NODE_TYPE_LABEL } from "../../domain/labels";
import type { Graph, GraphEdge } from "../../types/incident";
import { Mark } from "../ui/Mark";
import { EmptyState } from "../ui/States";

const clip = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

interface EdgeGeometry {
  d: string;
  lx: number;
  ly: number;
}

function geometry(a: PositionedNode, b: PositionedNode, offset: number): EdgeGeometry {
  const span = b.col - a.col;
  if (span === 0) {
    // Same column: loop out to the right.
    const x = a.x + NODE_W;
    const y1 = a.y + NODE_H / 2;
    const y2 = b.y + NODE_H / 2;
    const bulge = 38 + offset;
    return { d: `M ${x} ${y1} C ${x + bulge} ${y1}, ${x + bulge} ${y2}, ${x} ${y2}`, lx: x + bulge * 0.75 + 4, ly: (y1 + y2) / 2 + 3 };
  }
  if (Math.abs(span) > 1) {
    // Skips a column: arc over the top (left to right) or under the bottom (right to left) so it never runs behind a node.
    const over = span > 0;
    const x1 = a.x + NODE_W / 2;
    const x2 = b.x + NODE_W / 2;
    const y1 = over ? a.y : a.y + NODE_H;
    const y2 = over ? b.y : b.y + NODE_H;
    const reach = 46 + offset;
    const cy = over ? Math.min(y1, y2) - reach : Math.max(y1, y2) + reach;
    const apex = over ? Math.min(y1, y2) - reach * 0.75 : Math.max(y1, y2) + reach * 0.75;
    return { d: `M ${x1} ${y1} C ${x1} ${cy}, ${x2} ${cy}, ${x2} ${y2}`, lx: (x1 + x2) / 2, ly: over ? apex - 5 : apex + 13 };
  }
  const forward = span > 0;
  const x1 = forward ? a.x + NODE_W : a.x;
  const x2 = forward ? b.x : b.x + NODE_W;
  const y1 = a.y + NODE_H / 2 + offset;
  const y2 = b.y + NODE_H / 2 + offset;
  const mx = (x1 + x2) / 2;
  return { d: `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`, lx: mx, ly: (y1 + y2) / 2 - 5 };
}

interface Props {
  graph: Graph;
}

/** Block 2a: who is connected to whom. Flagged paths are drawn in red; hover or select a node for details. */
export function RelationshipGraph({ graph }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [activePath, setActivePath] = useState<number | null>(graph.flagged_paths.length > 0 ? 0 : null);

  const layout = useMemo(() => layoutGraph(graph), [graph]);
  const byId = useMemo(() => new Map(layout.nodes.map((n) => [n.id, n])), [layout]);

  const path = activePath !== null ? graph.flagged_paths[activePath] : undefined;
  const pathNodes = useMemo(() => new Set(path?.node_ids ?? []), [path]);
  const pathEdges = useMemo(() => pathEdgeKeys(path?.node_ids ?? []), [path]);
  const flaggedNodes = useMemo(() => new Set(graph.flagged_paths.flatMap((p) => p.node_ids)), [graph.flagged_paths]);

  if (graph.nodes.length === 0) {
    return (
      <EmptyState
        title="Brak danych o powiązaniach"
        text="Dla tego materiału nie zebrano relacji kapitałowych ani osobowych (KRS, CRBR, umowy). Graf pojawi się po uzupełnieniu kontekstu."
      />
    );
  }

  const focus = hovered ?? selected;
  const focusEdges = focus ? graph.edges.filter((e) => e.source === focus || e.target === focus) : [];
  const focusNeighbours = new Set(focusEdges.flatMap((e) => [e.source, e.target]));
  const selectedNode = selected ? byId.get(selected) : undefined;
  const selectedEdges = selected ? graph.edges.filter((e) => e.source === selected || e.target === selected) : [];

  // Parallel edges between the same pair are spread vertically.
  const pairCount = new Map<string, number>();
  const edges = graph.edges
    .map((e, i) => {
      const a = byId.get(e.source);
      const b = byId.get(e.target);
      if (!a || !b) return null;
      const key = edgeKey(e.source, e.target);
      const n = pairCount.get(key) ?? 0;
      pairCount.set(key, n + 1);
      const onPath = pathEdges.has(key);
      const dim = focus ? !(e.source === focus || e.target === focus) : false;
      return { e, i, onPath, dim, geo: geometry(a, b, n * 14) };
    })
    .filter((x): x is { e: GraphEdge; i: number; onPath: boolean; dim: boolean; geo: EdgeGeometry } => x !== null);

  const label = (id: string) => byId.get(id)?.label ?? id;

  return (
    <div className="graph">
      <div className="graph__canvas">
        <svg style={{ width: "100%", maxWidth: layout.width, minWidth: Math.min(layout.width, 640) }} viewBox={`0 0 ${layout.width} ${layout.height}`} role="group" aria-label="Graf powiązań między podmiotami">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--ink-2)" />
            </marker>
            <marker id="arrow-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--m-red)" />
            </marker>
          </defs>
          <g aria-hidden="true">
            {edges.map(({ e, i, onPath, dim, geo }) => (
              <path
                key={`e-${i}`}
                d={geo.d}
                className={`gedge${e.suspicious ? " gedge--suspicious" : ""}${onPath ? " gedge--path" : ""}${dim ? " gedge--dim" : ""}`}
                markerEnd={e.suspicious || onPath ? "url(#arrow-red)" : "url(#arrow)"}
              />
            ))}
            {edges.map(({ e, i, onPath, dim, geo }) => (
              <text
                key={`l-${i}`} x={geo.lx} y={geo.ly} textAnchor="middle"
                className={`gedge__label${e.suspicious || onPath ? " gedge__label--suspicious" : ""}${dim ? " gedge__label--dim" : ""}`}
              >
                {clip(e.label || EDGE_TYPE_LABEL[e.type] || "", 26)}
              </text>
            ))}
          </g>
          {layout.nodes.map((n) => {
            const flagged = pathNodes.has(n.id) || (activePath === null && flaggedNodes.has(n.id));
            const dim = focus ? !focusNeighbours.has(n.id) && n.id !== focus : false;
            return (
              <g
                key={n.id}
                className={`gnode${flagged ? " gnode--flagged" : ""}${selected === n.id ? " gnode--selected" : ""}${dim ? " gnode--dim" : ""}`}
                transform={`translate(${n.x}, ${n.y})`}
                role="button"
                tabIndex={0}
                aria-pressed={selected === n.id}
                aria-label={`${NODE_TYPE_LABEL[n.type] ?? "Węzeł"}: ${n.label}${flaggedNodes.has(n.id) ? ", na oznaczonej ścieżce" : ""}`}
                onClick={() => setSelected(selected === n.id ? null : n.id)}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter" || ev.key === " ") {
                    ev.preventDefault();
                    setSelected(selected === n.id ? null : n.id);
                  }
                }}
                onMouseEnter={() => setHovered(n.id)}
                onMouseLeave={() => setHovered(null)}
                onFocus={() => setHovered(n.id)}
                onBlur={() => setHovered(null)}
              >
                <rect width={NODE_W} height={NODE_H} />
                {flagged && <rect className="gnode__flag" x={0} y={0} width={16} height={16} />}
                {flagged && <text className="gnode__flag-t" x={8} y={12} textAnchor="middle">!</text>}
                <text x={flagged ? 22 : 12} y={18} className="gnode__type">{NODE_TYPE_LABEL[n.type] ?? n.type}</text>
                <text x={12} y={35} className="gnode__label">{clip(n.label, 23)}</text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="graph__side">
        <div className="graph__main">
        {selectedNode ? (
          <div data-testid="node-details">
            <p className="muted" style={{ fontSize: "var(--fs-14)" }}>{NODE_TYPE_LABEL[selectedNode.type] ?? selectedNode.type}</p>
            <h3 className="subhead" style={{ marginBottom: 8 }}>{selectedNode.label}</h3>
            {flaggedNodes.has(selectedNode.id) && <p style={{ marginBottom: 8 }}><Mark tone="red" icon={TriangleAlert}>Na oznaczonej ścieżce</Mark></p>}
            {selectedNode.meta && Object.keys(selectedNode.meta).length > 0 && (
              <dl className="kv kv--compact" style={{ marginBottom: 16 }}>
                {Object.entries(selectedNode.meta).map(([k, v]) => (
                  <div key={k} style={{ display: "contents" }}><dt>{k}</dt><dd>{typeof v === "number" ? v.toLocaleString("pl-PL") : v}</dd></div>
                ))}
              </dl>
            )}
            <p className="subhead">Relacje ({selectedEdges.length})</p>
            <ul style={{ display: "grid", gap: 4 }}>
              {selectedEdges.map((e, i) => (
                <li key={i} style={{ fontSize: "var(--fs-14)" }}>
                  {label(e.source)} <ChevronRight size={11} aria-hidden="true" style={{ verticalAlign: -1 }} /> {label(e.target)}
                  <span className="muted">: {e.label || EDGE_TYPE_LABEL[e.type]}</span>
                  {e.suspicious && <span style={{ color: "var(--c-red)", fontWeight: 700 }}> (podejrzane)</span>}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <>
            {graph.flagged_paths.length > 0 ? (
              <div style={{ display: "grid", gap: 8 }}>
                <p className="subhead" style={{ marginBottom: 0 }}>Oznaczone ścieżki ({graph.flagged_paths.length})</p>
                <div className="graph__paths">
                {graph.flagged_paths.map((p, i) => (
                  <button key={i} type="button" className="path-card" aria-pressed={activePath === i} onClick={() => setActivePath(activePath === i ? null : i)}>
                    <span className="path-card__title"><Waypoints aria-hidden="true" />Ścieżka {i + 1}</span>
                    <span className="path-card__chain">
                      {p.node_ids.map((id, j) => (
                        <span key={`${id}-${j}`} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                          {j > 0 && <ChevronRight aria-hidden="true" />}
                          <strong>{label(id)}</strong>
                        </span>
                      ))}
                    </span>
                    <span>{p.description}</span>
                  </button>
                ))}
                </div>
              </div>
            ) : (
              <p className="muted">Silnik nie oznaczył żadnej ścieżki powiązań jako podejrzanej.</p>
            )}
            <p className="muted" style={{ fontSize: "var(--fs-14)" }}>Wybierz węzeł (kliknij albo Enter), aby zobaczyć szczegóły i jego relacje.</p>
          </>
        )}
        </div>
        <div className="graph__legend" aria-hidden="true">
          <span><i />relacja: linia ciągła 1 px</span>
          <span><i className="sus" />relacja podejrzana: linia przerywana</span>
          <span><i className="path" />oznaczona ścieżka: linia gruba</span>
          <span><b className="graph__legend-flag">!</b>węzeł na oznaczonej ścieżce</span>
        </div>
      </div>
    </div>
  );
}
