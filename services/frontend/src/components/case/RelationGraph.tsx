import { EDGE_TYPE_LABEL, NODE_TYPE_LABEL } from "../../domain/labels";
import { edgeKey, layoutGraph, NODE_H, NODE_W, pathEdgeKeys } from "../../domain/graphLayout";
import type { Graph } from "../../types/incident";

const clip = (s: string, n = 24) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

export function RelationGraph({ graph }: { graph: Graph }) {
  const layout = layoutGraph(graph);
  const pos = new Map(layout.nodes.map((n) => [n.id, n]));
  const flaggedNodes = new Set(graph.flagged_paths.flatMap((p) => p.node_ids));
  const flaggedEdges = new Set(graph.flagged_paths.flatMap((p) => [...pathEdgeKeys(p.node_ids)]));
  return (
    <div className="graph">
      <div className="graph__scroll">
        <svg width={layout.width} height={layout.height} viewBox={`0 0 ${layout.width} ${layout.height}`} role="img"
          aria-label={`Graf powiązań: ${graph.nodes.length} podmiotów, ${graph.edges.length} relacji, ${graph.flagged_paths.length} podejrzanych ścieżek`}>
          <defs>
            <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0 0 8 4 0 8z" fill="context-stroke" />
            </marker>
          </defs>
          {graph.edges.map((e, i) => {
            const a = pos.get(e.source);
            const b = pos.get(e.target);
            if (!a || !b) return null;
            const flagged = flaggedEdges.has(edgeKey(e.source, e.target));
            const hot = e.suspicious || flagged;
            const forward = a.x <= b.x;
            const x1 = forward ? a.x + NODE_W : a.x;
            const x2 = forward ? b.x : b.x + NODE_W;
            const y1 = a.y + NODE_H / 2;
            const y2 = b.y + NODE_H / 2;
            const mx = (x1 + x2) / 2;
            return (
              <g key={`${e.source}-${e.target}-${i}`}>
                <path d={`M${x1} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2} ${y2}`} fill="none"
                  className={`graph__edge${hot ? " graph__edge--hot" : ""}${flagged ? " graph__edge--path" : ""}`}
                  stroke={hot ? "var(--red)" : "var(--line-strong)"} markerEnd="url(#arrow)">
                  <title>{`${EDGE_TYPE_LABEL[e.type]}: ${e.label}`}</title>
                </path>
              </g>
            );
          })}
          {layout.nodes.map((n) => (
            <g key={n.id} transform={`translate(${n.x} ${n.y})`} className={`graph__node graph__node--${n.type}${flaggedNodes.has(n.id) ? " graph__node--hot" : ""}`}>
              <rect width={NODE_W} height={NODE_H} rx={8} />
              <text x={10} y={19} className="graph__type">{NODE_TYPE_LABEL[n.type]}</text>
              <text x={10} y={36} className="graph__label">{clip(n.label)}</text>
              <title>{`${NODE_TYPE_LABEL[n.type]}: ${n.label}`}</title>
            </g>
          ))}
        </svg>
      </div>
      {graph.flagged_paths.length > 0 && (
        <div className="graph__paths">
          <h3 className="subhead">Podejrzane ścieżki powiązań</h3>
          <ul>
            {graph.flagged_paths.map((p, i) => (
              <li key={i} className="pathcard">
                <span className="pathcard__chain">
                  {p.node_ids.map((id, j) => (
                    <span key={`${id}-${j}`}>{j > 0 && <span className="pathcard__arrow" aria-hidden="true"> → </span>}<strong>{pos.get(id)?.label ?? id}</strong></span>
                  ))}
                </span>
                <span className="muted">{p.description}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <h3 className="subhead">Relacje</h3>
      <ul className="edgelist">
        {graph.edges.map((e, i) => (
          <li key={i} className={e.suspicious ? "edgelist__hot" : undefined}>
            <span>{pos.get(e.source)?.label ?? e.source}</span>
            <span className="muted"> — {EDGE_TYPE_LABEL[e.type]}{e.label ? ` (${e.label})` : ""} → </span>
            <span>{pos.get(e.target)?.label ?? e.target}</span>
            {e.suspicious && <span className="rs rs--fail">podejrzane</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
