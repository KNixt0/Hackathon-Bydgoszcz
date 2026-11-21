import type { Graph, GraphNode, GraphNodeType } from "../types/incident";

export interface PositionedNode extends GraphNode {
  x: number;
  y: number;
  /** index of the layout column, left to right */
  col: number;
}

export interface GraphLayout {
  nodes: PositionedNode[];
  width: number;
  height: number;
}

/** Left-to-right reading order: who controls → companies → intermediaries → who publishes → the material. */
const COLUMN: Record<GraphNodeType, number> = {
  person: 0,
  company: 1,
  pr_agency: 2,
  advisor: 3,
  influencer: 3,
  ad: 4,
};

export const NODE_W = 164;
export const NODE_H = 46;
const COL_GAP = 104;
const ROW_GAP = 30;
const PAD = 20;
/** Vertical room above and below the nodes for edges that arc over skipped columns. */
export const PAD_Y = 52;

/**
 * Simple layered layout: one column per node type, rows ordered by the barycentre
 * of already placed neighbours so that related nodes sit close and edges cross less.
 */
export function layoutGraph(graph: Graph): GraphLayout {
  const used = [...new Set(graph.nodes.map((n) => COLUMN[n.type]))].sort((a, b) => a - b);
  const colIndex = new Map(used.map((c, i) => [c, i]));
  const columns: GraphNode[][] = used.map(() => []);
  for (const n of graph.nodes) columns[colIndex.get(COLUMN[n.type]) ?? 0]?.push(n);

  const neighbours = new Map<string, string[]>();
  for (const e of graph.edges) {
    neighbours.set(e.source, [...(neighbours.get(e.source) ?? []), e.target]);
    neighbours.set(e.target, [...(neighbours.get(e.target) ?? []), e.source]);
  }

  const row = new Map<string, number>();
  columns.forEach((col, ci) => {
    if (ci > 0) {
      const bary = (n: GraphNode) => {
        const rows = (neighbours.get(n.id) ?? []).map((id) => row.get(id)).filter((r): r is number => r !== undefined);
        return rows.length ? rows.reduce((a, b) => a + b, 0) / rows.length : Number.MAX_SAFE_INTEGER;
      };
      col.sort((a, b) => bary(a) - bary(b));
    }
    col.forEach((n, ri) => row.set(n.id, ri));
  });

  const maxRows = Math.max(1, ...columns.map((c) => c.length));
  const height = PAD_Y * 2 + maxRows * NODE_H + (maxRows - 1) * ROW_GAP;
  const width = PAD * 2 + columns.length * NODE_W + Math.max(0, columns.length - 1) * COL_GAP;

  const nodes: PositionedNode[] = [];
  columns.forEach((col, ci) => {
    const colHeight = col.length * NODE_H + (col.length - 1) * ROW_GAP;
    const top = (height - colHeight) / 2;
    col.forEach((n, ri) => {
      nodes.push({ ...n, col: ci, x: PAD + ci * (NODE_W + COL_GAP), y: top + ri * (NODE_H + ROW_GAP) });
    });
  });
  return { nodes, width: Math.max(width, 2 * PAD + NODE_W), height };
}

/** Edge keys ("a→b", order-independent) that lie on a flagged path. */
export function pathEdgeKeys(nodeIds: string[]): Set<string> {
  const keys = new Set<string>();
  for (let i = 0; i < nodeIds.length - 1; i += 1) {
    const a = nodeIds[i];
    const b = nodeIds[i + 1];
    if (a !== undefined && b !== undefined) keys.add(edgeKey(a, b));
  }
  return keys;
}

export function edgeKey(a: string, b: string): string {
  return a < b ? `${a}|${b}` : `${b}|${a}`;
}
