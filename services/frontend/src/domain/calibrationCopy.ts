import type { Confusion } from "./calibration";
import { pl } from "./plural";

/** A piece of a sentence; `b` marks the numbers shown in bold. */
export interface Seg {
  t: string;
  b?: boolean;
}

const num = (n: number): Seg => ({ t: String(n), b: true });
const txt = (t: string): Seg => ({ t });
export const segText = (segs: Seg[]) => segs.map((s) => s.t).join("");

const checked = (n: number) => (n === 1 ? "sprawdzonej sprawy" : "sprawdzonych spraw");

function missed(fn: number): Seg[] {
  if (fn === 0) return [txt("Żadne naruszenie nie zostaje przeoczone.")];
  return [num(fn), txt(` ${pl(fn, "naruszenie zostaje przeoczone", "naruszenia zostają przeoczone", "naruszeń zostaje przeoczonych")}.`)];
}

/** The live calibration sentence (DESIGN.md 5.3) with correct Polish plural forms. */
export function flagSentence(threshold: number, c: Confusion): Seg[] {
  const n = c.tp + c.fp + c.fn + c.tn;
  const flagged = c.tp + c.fp;
  if (flagged === 0) {
    return [txt("Przy progu "), num(threshold), txt(" system nie oznacza żadnej z "), num(n), txt(` ${checked(n)}. `), ...missed(c.fn)];
  }
  return [
    txt("Przy progu "), num(threshold), txt(" system oznacza "), num(flagged), txt(" z "), num(n), txt(` ${checked(n)}. W tym `),
    num(c.tp), txt(` ${pl(c.tp, "rzeczywiste naruszenie", "rzeczywiste naruszenia", "rzeczywistych naruszeń")} i `),
    num(c.fp), txt(` ${pl(c.fp, "fałszywy alarm", "fałszywe alarmy", "fałszywych alarmów")}. `),
    ...missed(c.fn),
  ];
}

/** Without a labelled set: what the threshold does to the live queue, and why errors cannot be counted. */
export function queueOnlySentence(threshold: number, flagged: number, total: number): Seg[] {
  return [
    txt("Przy progu "), num(threshold), txt(" system oznacza "), num(flagged), txt(" z "), num(total),
    txt(` ${total === 1 ? "sprawy" : "spraw"} w kolejce. Nie wiemy, ile z nich to pomyłki, bo brak ocenionych spraw.`),
  ];
}

/** "z 22 zgodnych spraw", "z 1 zgodnej sprawy" */
export const ofCompliant = (n: number) => (n === 1 ? "z 1 zgodnej sprawy" : `z ${n} zgodnych spraw`);
/** "z 23 naruszeń", "z 1 naruszenia" */
export const ofViolations = (n: number) => (n === 1 ? "z 1 naruszenia" : `z ${n} naruszeń`);
/** "19 z 21 alertów to rzeczywiste naruszenia" */
export const precisionFraction = (tp: number, flagged: number) =>
  `${tp} z ${flagged} ${flagged === 1 ? "alertu" : "alertów"} to ${tp === 1 ? "rzeczywiste naruszenie" : "rzeczywiste naruszenia"}`;
/** "wykryto 19 z 23 naruszeń" */
export const recallFraction = (tp: number, violations: number) => `wykryto ${tp} ${ofViolations(violations)}`;
