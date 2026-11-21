import { describe, expect, it } from "vitest";
import { resolveSpan } from "../../src/components/case/SourceText";
import { edgeKey, layoutGraph, pathEdgeKeys } from "../../src/domain/graphLayout";
import { calibrationSet, greenCase, orangeCase, redCase } from "../fixtures/data.mjs";

const RULE_IDS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12a", "12b", "13", "14", "15", "16", "17", "18"];

describe.each([["orange", orangeCase], ["green", greenCase], ["red", redCase]])("fixture %s follows the incident contract", (_name, inc) => {
  it("has the 19 rule rows in attachment order", () => {
    expect(inc.rules.map((r) => r.id)).toEqual(RULE_IDS);
  });
  it("quotes are exact substrings at their span", () => {
    for (const ev of inc.evidence.filter((e) => e.kind === "quote")) {
      expect(ev.span).toBeDefined();
      expect(inc.source.text.slice(ev.span?.start, ev.span?.end)).toBe(ev.quote);
    }
  });
  it("every evidence id resolves", () => {
    const ids = new Set(inc.evidence.map((e) => e.id));
    const used = [
      ...inc.rules.flatMap((r) => r.evidence_ids),
      ...inc.debate.claims.flatMap((c) => c.evidence_ids),
      ...inc.module_results.flatMap((m) => m.findings.flatMap((f) => f.evidence_ids)),
    ];
    expect(used.filter((id) => !ids.has(id))).toEqual([]);
  });
  it("compliance score is 100 minus risk", () => {
    expect(inc.compliance_score).toBe(100 - inc.risk_score);
  });
});

it("the calibration set has about 30 labelled items of both classes", () => {
  expect(calibrationSet.items.length).toBeGreaterThanOrEqual(30);
  expect(new Set(calibrationSet.items.map((i) => i.ground_truth))).toEqual(new Set(["violation", "ok"]));
});

describe("resolveSpan", () => {
  const text = "Ala ma kota, a kot ma Alę.";
  it("uses valid offsets", () => expect(resolveSpan(text, { start: 7, end: 11 }, "kota")).toEqual({ start: 7, end: 11 }));
  it("falls back to searching the quote when offsets are wrong", () => expect(resolveSpan(text, { start: 0, end: 3 }, "kota")).toEqual({ start: 7, end: 11 }));
  it("rejects out-of-range offsets", () => expect(resolveSpan(text, { start: 20, end: 99 })).toBeNull());
  it("returns null when the quote is not in the text", () => expect(resolveSpan(text, undefined, "pies")).toBeNull());
});

describe("layoutGraph", () => {
  it("places every node once, inside the canvas, without overlaps in a column", () => {
    const layout = layoutGraph(orangeCase.graph);
    expect(layout.nodes).toHaveLength(orangeCase.graph.nodes.length);
    const seen = new Set<string>();
    for (const n of layout.nodes) {
      expect(n.x).toBeGreaterThanOrEqual(0);
      expect(n.y).toBeGreaterThanOrEqual(0);
      expect(n.x).toBeLessThan(layout.width);
      expect(n.y).toBeLessThan(layout.height);
      const key = `${n.x}:${n.y}`;
      expect(seen.has(key)).toBe(false);
      seen.add(key);
    }
  });
  it("handles an empty graph", () => {
    expect(layoutGraph({ nodes: [], edges: [], flagged_paths: [] }).nodes).toEqual([]);
  });
  it("derives order-independent edge keys for a flagged path", () => {
    const keys = pathEdgeKeys(["a", "b", "c"]);
    expect(keys.has(edgeKey("b", "a"))).toBe(true);
    expect(keys.has(edgeKey("c", "b"))).toBe(true);
    expect(keys.has(edgeKey("a", "c"))).toBe(false);
  });
});
