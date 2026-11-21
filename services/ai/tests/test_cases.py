"""The three demo cases, the calibration set and the contract invariants on real samples."""

from __future__ import annotations

import json
import time

import pytest
from conftest import SAMPLES

from app.rules import RULE_ORDER
from app.scoring import risk_level

CASES = {p.stem.split("-")[0]: p for p in sorted((SAMPLES / "cases").glob("*.json"))}
EVAL = sorted((SAMPLES / "eval").glob("*.json"))
ALL = [*CASES.values(), *EVAL]


def failed(analysis) -> list[str]:
    return [r.id for r in analysis.rules if r.status == "fail"]


def codes(analysis) -> set[str]:
    return {f.code for m in analysis.module_results for f in m.findings}


# ---------------------------------------------------------------- demo cases
def test_case1_green(analyze_sample):
    a = analyze_sample(CASES["case1"])
    assert a.risk_level == "green" and abs(a.compliance_score - 92) <= 3
    assert a.demo_case == "case1" and a.synthetic is True
    assert failed(a) == [] and {1, 2} <= set(a.modules) and a.primary_module == 1
    assert a.entities.investment_firm.name == "XTB S.A."
    listed = {c.registry for c in a.registry_checks if c.status == "listed"}
    assert {"knf_investment_firms", "knf_brokerage_houses", "uknf_cooperation_notice"} <= listed
    assert a.graph.flagged_paths == [] and a.forensics.anomalies == []
    assert a.forensics.accounts.share_younger_14d == 0
    # only verifiable facts about the real firm: no invented KRS data or figures
    f = a.financials
    assert (f.krs, f.incorporated_on, f.age_months, f.share_capital_pln, f.statements, f.flags) == (
        None,
        None,
        None,
        None,
        [],
        [],
    )
    assert a.recommendation.action == "none" and a.debate.arguments_for == []
    assert len(a.debate.arguments_against) >= 4


def test_case2_orange(analyze_sample):
    a = analyze_sample(CASES["case2"])
    assert a.risk_level == "orange" and abs(a.compliance_score - 52) <= 3
    assert failed(a) == ["2", "4", "6", "7", "12a", "18"]
    assert a.recommendation.action == "explain" and a.recommendation.label == "Postępowanie wyjaśniające"
    assert a.financials.age_months == 11 and a.financials.share_capital_pln == 5000
    assert "Brak pełnego sprawozdania finansowego" in a.financials.flags
    path = a.graph.flagged_paths[0]
    labels = [next(n.label for n in a.graph.nodes if n.id == i) for i in path.node_ids]
    assert labels == [
        "Kormoran Fikcyjny Go sp. z o.o.",
        "Dom Maklerski Kormoran Fikcyjny S.A.",
        "Jan Wymyślony",
        "Agencja PR Bajka Media sp. z o.o.",
        "Zmyślony Inwestor Tomek",
    ]
    kirp = next(c for c in a.registry_checks if c.registry == "kirp_legal_advisers")
    assert kirp.status == "inactive" and kirp.detail == "Nie wykonuje zawodu"
    assert {x.type for x in a.forensics.anomalies} >= {"opinion_spike", "fresh_account_cluster", "name_pattern_cluster"}
    # the debate holds real counter-arguments, and they changed the outcome
    against = {c.id: c for c in a.debate.claims if c.stance == "against"}
    assert len(a.debate.arguments_against) >= 2 and set(a.debate.arguments_against) == set(against)
    assert any("figuruje w rejestrze" in c.text for c in against.values())
    assert sum(c.verdict == "weakened" for c in a.debate.claims) >= 5
    assert {"PR_CONFLICT_PATH", "DISGUISED_AD", "LEGAL_ADVISER_INACTIVE"} <= codes(a)


def test_case3_red(analyze_sample):
    a = analyze_sample(CASES["case3"])
    assert a.risk_level == "red" and abs(a.compliance_score - 11) <= 3
    assert a.primary_module == 3 and a.demo_case == "case3" and a.recommendation.action == "escalate"
    assert {
        "ADVISORY_PHRASE",
        "PORTFOLIO_MANAGEMENT",
        "GUARANTEED_RETURN",
        "REGISTRY_NOT_LISTED",
        "BRAND_IMPERSONATION",
        "FAKE_LICENCE",
        "FOREIGN_SHELL",
    } <= codes(a)
    firm_registers = {
        "knf_investment_firms",
        "knf_banks_brokerage",
        "knf_brokerage_houses",
        "knf_foreign_branches",
        "knf_foreign_cross_border",
    }
    firm_checks = [c for c in a.registry_checks if c.registry in firm_registers]
    assert len(firm_checks) == 5 and all(c.status == "not_listed" for c in firm_checks)
    assert next(c for c in a.registry_checks if c.registry == "knf_investment_advisors").status == "not_listed"
    assert round(a.forensics.accounts.share_younger_14d, 2) == 0.89
    assert any(e.legal_ref == "art. 76 ustawy o obrocie instrumentami finansowymi" for e in a.evidence)
    meta = json.loads(CASES["case3"].read_text(encoding="utf-8"))["meta"]
    assert meta["seed"] is False


def test_cases_are_ordered_and_separated(analyze_sample):
    scores = [analyze_sample(CASES[c]).risk_score for c in ("case1", "case2", "case3")]
    assert scores[0] < 35 <= scores[1] < 70 <= scores[2]


# ---------------------------------------------------------------- calibration set
def test_eval_set_shape():
    samples = [json.loads(p.read_text(encoding="utf-8")) for p in EVAL]
    labels = [s["context"]["ground_truth"] for s in samples]
    assert 38 <= len(samples) <= 50 and set(labels) == {"violation", "ok"}
    assert min(labels.count("violation"), labels.count("ok")) >= 15
    assert all(s["context"]["synthetic"] is True for s in samples)
    assert {s["context"]["module_hint"] for s in samples} == {1, 2, 3}
    assert len({s["meta"]["platform"] for s in samples}) >= 6
    days = [s["meta"]["detected_days_ago"] for s in samples]
    assert min(days) <= 1 and max(days) >= 25 and all(0 <= d < 30 for d in days)
    assert all(".example" in s["meta"]["url"] for s in samples)


def test_eval_scores_separate_classes_but_overlap(analyze_sample):
    scores = {"violation": [], "ok": []}
    for p in EVAL:
        a = analyze_sample(p)
        scores[a.ground_truth].append(a.risk_score)
    mean = {k: sum(v) / len(v) for k, v in scores.items()}
    assert mean["violation"] > mean["ok"] + 20  # the engine clearly separates the classes on average ...
    assert min(scores["violation"]) < max(scores["ok"])  # ... but not perfectly: the threshold is a real trade-off

    def confusion(t):
        return sum(s < t for s in scores["violation"]), sum(s >= t for s in scores["ok"])  # (FN, FP)

    fn_low, fp_low = confusion(15)
    fn_high, fp_high = confusion(45)
    assert fn_low < fn_high and fp_low > fp_high


# ---------------------------------------------------------------- contract invariants on every sample
@pytest.mark.parametrize("path", ALL, ids=lambda p: p.stem)
def test_contract_invariants(analyze_sample, path):
    a = analyze_sample(path)
    text = a.source.text
    ids = {e.id for e in a.evidence}
    assert len(ids) == len(a.evidence)
    # 1. every quote is an exact substring at its span
    for e in a.evidence:
        if e.kind == "quote":
            assert e.quote and e.quote in text and text[e.span.start : e.span.end] == e.quote
    # 2. every evidence id resolves
    referenced = [i for m in a.module_results for f in m.findings for i in f.evidence_ids]
    referenced += [i for r in a.rules for i in r.evidence_ids] + [i for c in a.debate.claims for i in c.evidence_ids]
    assert set(referenced) <= ids
    # 3. always 19 rule rows in attachment order
    assert [r.id for r in a.rules] == RULE_ORDER
    # score semantics
    assert 0 <= a.risk_score <= 100 and a.compliance_score == pytest.approx(100 - a.risk_score, abs=0.05)
    assert a.risk_level == risk_level(a.risk_score)
    assert a.primary_module in a.modules and a.modules == sorted(set(a.modules))
    assert a.engine.llm_used is False and a.engine.model is None
    assert a.title and a.summary and a.debate.arbiter_rationale
    claim_ids = {c.id for c in a.debate.claims}
    assert set(a.debate.arguments_for) | set(a.debate.arguments_against) <= claim_ids
    assert all(i in claim_ids for r in a.debate.rounds for i in r.claim_ids)


def test_scores_are_deterministic(engine):
    import asyncio

    from run_eval import analyze_file

    for path in CASES.values():
        first = asyncio.run(analyze_file(engine, path))
        second = asyncio.run(analyze_file(engine, path))
        assert first.model_dump(exclude={"engine"}) == second.model_dump(exclude={"engine"})


def test_analysis_is_fast(engine):
    import asyncio

    from run_eval import analyze_file

    started = time.perf_counter()
    for path in CASES.values():
        asyncio.run(analyze_file(engine, path))
    assert (time.perf_counter() - started) / len(CASES) < 0.5
