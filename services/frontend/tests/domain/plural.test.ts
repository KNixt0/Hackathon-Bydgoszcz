import { describe, expect, it } from "vitest";
import { flagSentence, ofCompliant, ofViolations, precisionFraction, queueOnlySentence, recallFraction, segText } from "../../src/domain/calibrationCopy";
import { listPl, pl, plN } from "../../src/domain/plural";

const forms = (n: number) => pl(n, "sprawa", "sprawy", "spraw");

describe("pl: Polish plural forms", () => {
  it("1 takes the singular", () => expect(forms(1)).toBe("sprawa"));
  it.each([2, 3, 4, 22, 23, 24, 32, 102, 1004])("%i takes the 'few' form", (n) => expect(forms(n)).toBe("sprawy"));
  it.each([0, 5, 6, 9, 10, 11, 12, 13, 14, 15, 19, 20, 21, 25, 100, 111, 112, 114, 1000])("%i takes the 'many' form", (n) => expect(forms(n)).toBe("spraw"));
  it("uses the absolute integer part of negative and fractional counts", () => {
    expect(forms(-3)).toBe("sprawy");
    expect(forms(2.7)).toBe("sprawy");
  });
  it("plN prefixes the count", () => expect(plN(5, "alarm", "alarmy", "alarmów")).toBe("5 alarmów"));
  it("listPl joins with 'i' before the last item", () => {
    expect(listPl([])).toBe("");
    expect(listPl(["3"])).toBe("3");
    expect(listPl(["3", "7"])).toBe("3 i 7");
    expect(listPl(["3", "7", "12", "14"])).toBe("3, 7, 12 i 14");
  });
});

describe("calibration sentence", () => {
  const c = (tp: number, fp: number, fn: number, tn: number) => ({ tp, fp, fn, tn });

  it("matches the worked example from the spec (threshold 20, 45 cases)", () => {
    expect(segText(flagSentence(20, c(19, 2, 4, 20)))).toBe(
      "Przy progu 20 system oznacza 21 z 45 sprawdzonych spraw. W tym 19 rzeczywistych naruszeń i 2 fałszywe alarmy. 4 naruszenia zostają przeoczone.",
    );
  });

  it("uses the singular for one of each", () => {
    expect(segText(flagSentence(35, c(1, 1, 1, 2)))).toBe(
      "Przy progu 35 system oznacza 2 z 5 sprawdzonych spraw. W tym 1 rzeczywiste naruszenie i 1 fałszywy alarm. 1 naruszenie zostaje przeoczone.",
    );
  });

  it("uses the 'few' forms for 2–4 and the 'many' forms for 5+ and 12–14", () => {
    expect(segText(flagSentence(50, c(3, 4, 12, 3)))).toBe(
      "Przy progu 50 system oznacza 7 z 22 sprawdzonych spraw. W tym 3 rzeczywiste naruszenia i 4 fałszywe alarmy. 12 naruszeń zostaje przeoczonych.",
    );
    expect(segText(flagSentence(10, c(22, 13, 0, 1)))).toBe(
      "Przy progu 10 system oznacza 35 z 36 sprawdzonych spraw. W tym 22 rzeczywiste naruszenia i 13 fałszywych alarmów. Żadne naruszenie nie zostaje przeoczone.",
    );
  });

  it("says nothing is flagged when the threshold is above every score", () => {
    expect(segText(flagSentence(100, c(0, 0, 5, 3)))).toBe("Przy progu 100 system nie oznacza żadnej z 8 sprawdzonych spraw. 5 naruszeń zostaje przeoczonych.");
    expect(segText(flagSentence(100, c(0, 0, 1, 0)))).toBe("Przy progu 100 system nie oznacza żadnej z 1 sprawdzonej sprawy. 1 naruszenie zostaje przeoczone.");
  });

  it("marks only the numbers as bold", () => {
    const bold = flagSentence(20, c(19, 2, 4, 20)).filter((s) => s.b).map((s) => s.t);
    expect(bold).toEqual(["20", "21", "45", "19", "2", "4"]);
  });

  it("without labelled cases talks about the queue", () => {
    expect(segText(queueOnlySentence(20, 16, 30))).toBe("Przy progu 20 system oznacza 16 z 30 spraw w kolejce. Nie wiemy, ile z nich to pomyłki, bo brak ocenionych spraw.");
  });

  it("fractions under the counts and the secondary figures", () => {
    expect(ofCompliant(22)).toBe("z 22 zgodnych spraw");
    expect(ofCompliant(1)).toBe("z 1 zgodnej sprawy");
    expect(ofViolations(23)).toBe("z 23 naruszeń");
    expect(ofViolations(1)).toBe("z 1 naruszenia");
    expect(precisionFraction(19, 21)).toBe("19 z 21 alertów to rzeczywiste naruszenia");
    expect(precisionFraction(1, 1)).toBe("1 z 1 alertu to rzeczywiste naruszenie");
    expect(recallFraction(19, 23)).toBe("wykryto 19 z 23 naruszeń");
  });
});
