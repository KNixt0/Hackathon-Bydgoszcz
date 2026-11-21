from __future__ import annotations

import asyncio
import itertools

from app.debate import run_debate
from app.debate.critic import Critic, grounding_error
from app.debate.models import DebateClaim
from app.plugins import get_plugins
from app.schemas import Evidence, Span

BUR = "Dom Maklerski Bursztyn Przykładowy S.A."
RISK = "Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanych środków."
AUTHOR = {"name": "Testowy Twórca Finansowy", "handle": "@testowy"}
OFFER = (
    "przygotuje dla Ciebie indywidualne rekomendacje: wskażemy, które akcje i obligacje kupić, a które "
    "sprzedać. Zarządzamy Twoim portfelem."
)


def debate(make_ctx, **kwargs):
    ctx = make_ctx(**kwargs)
    return asyncio.run(run_debate(ctx, list(get_plugins().values()))), ctx


def by_code(outcome, code):
    return next(c for c in outcome.all_claims() if c.code == code)


# ---------------------------------------------------------------- grounding
def test_grounding_accepts_exact_quotes(make_ctx):
    ctx = make_ctx(text="Zarabiaj 20% rocznie bez ryzyka.")
    ev = ctx.evidence.quote(0, 20, "cytat")
    assert ctx.evidence.get(ev).quote == "Zarabiaj 20% rocznie" and grounding_error(ctx.evidence, [ev]) is None


def test_grounding_rejects_invented_quote_wrong_span_and_missing_id(make_ctx):
    ctx = make_ctx(text="Zarabiaj 20% rocznie bez ryzyka.")
    ctx.evidence.items.append(
        Evidence(id="x1", kind="quote", label="zmyślony", quote="Gwarantujemy 50% zysku", span=Span(start=0, end=22))
    )
    ctx.evidence.items.append(
        Evidence(id="x2", kind="quote", label="zły zakres", quote="Zarabiaj 20%", span=Span(start=5, end=17))
    )
    assert "nie występuje dosłownie" in grounding_error(ctx.evidence, ["x1"])
    assert "Zakres znaków" in grounding_error(ctx.evidence, ["x2"])
    assert "nie istnieje" in grounding_error(ctx.evidence, ["brak"])


def test_critic_rejects_ungrounded_claim(make_ctx):
    outcome, ctx = debate(make_ctx, text="Zarabiaj 20% rocznie, załóż konto.")
    ctx.evidence.items.append(
        Evidence(id="fake", kind="quote", label="x", quote="tego nie ma w tekście", span=Span(start=0, end=21))
    )
    claim = DebateClaim(
        id="c99",
        stance="for",
        text="Teza bez pokrycia",
        confidence=0.9,
        evidence_ids=["fake"],
        agent="test",
        code="RULE_3",
    )
    Critic().review_claim(claim, outcome.world)
    assert claim.verdict == "rejected" and claim.confidence == 0 and "brak ugruntowania" in claim.critique


# ---------------------------------------------------------------- rounds
def test_three_rounds_and_agents(make_ctx):
    outcome, _ = debate(make_ctx, text="Zarabiaj 20% rocznie, załóż konto.")
    d = outcome.to_schema()
    assert [r.round for r in d.rounds] == [1, 1, 1, 2, 3]
    assert [r.agent for r in d.rounds] == [
        "Agent regulacyjno-reklamowy",
        "Śledczy KRS / grafu powiązań",
        "Agent analizy opinii",
        "Krytyk / Red-Teamer",
        "Arbiter i agregator",
    ]
    ids = {c.id for c in d.claims}
    assert len(ids) == len(d.claims)
    assert set(d.arguments_for) <= ids and set(d.arguments_against) <= ids
    assert all(next(c for c in d.claims if c.id == i).stance == "for" for i in d.arguments_for)
    assert all(next(c for c in d.claims if c.id == i).stance == "against" for i in d.arguments_against)
    assert all(c.critique for c in d.claims)


def test_upheld_claim_keeps_confidence(make_ctx):
    outcome, _ = debate(make_ctx, text=f"Testowa Aurora Family Office sp. z o.o. {OFFER}")
    claim = by_code(outcome, "REGISTRY_NOT_LISTED")
    assert claim.verdict == "upheld" and claim.confidence == claim.finding.confidence


# ---------------------------------------------------------------- false-positive patterns
def test_authorised_firm_rejects_advisory_claims(make_ctx):
    outcome, _ = debate(make_ctx, text=f"{BUR} {OFFER} {RISK}")
    assert by_code(outcome, "ADVISORY_PHRASE").verdict == "rejected"
    assert by_code(outcome, "PORTFOLIO_MANAGEMENT").verdict == "rejected"
    assert "FIRM_REGISTERED" in {c.code for c in outcome.against}
    assert outcome.verdict.breakdown.risk_score < 20


def test_reporting_context_weakens_everything(make_ctx):
    text = (
        "KNF ostrzega przed fałszywymi doradcami, którzy obiecują gwarantowany zysk i wskazują, które akcje "
        "kupić. Oszuści proponują zarządzanie portfelem przez komunikatory."
    )
    outcome, _ = debate(make_ctx, text=text)
    fors = [c for c in outcome.all_claims() if c.stance == "for"]
    assert fors and all(c.verdict == "weakened" for c in fors)
    assert "REPORTING_CONTEXT" in {c.code for c in outcome.against}
    same_text_as_offer, _ = debate(
        make_ctx,
        text="Obiecujemy gwarantowany zysk i wskażemy, które akcje kupić. "
        "Zarządzamy portfelem przez komunikatory. Zapisz się.",
    )
    assert same_text_as_offer.verdict.breakdown.risk_score > outcome.verdict.breakdown.risk_score + 25


def test_registered_parent_weakens_not_listed_and_rejects_impersonation(make_ctx):
    graph = {
        "nodes": [
            {
                "id": "go",
                "type": "company",
                "label": "Kormoran Fikcyjny Go sp. z o.o.",
                "meta": {"role": "investment_firm"},
            },
            {"id": "parent", "type": "company", "label": "Dom Maklerski Kormoran Fikcyjny S.A."},
        ],
        "edges": [{"source": "parent", "target": "go", "type": "owner", "label": "100%"}],
    }
    kwargs = {
        "platform": "youtube",
        "author": AUTHOR,
        "url": "https://youtube.example/x",
        "text": f"Kormoran Fikcyjny Go sp. z o.o. {OFFER} Załóż konto z mojego linku partnerskiego.",
        "companies": [{"name": "Kormoran Fikcyjny Go sp. z o.o.", "role": "investment_firm"}],
    }
    with_parent, _ = debate(make_ctx, graph=graph, **kwargs)
    without, _ = debate(make_ctx, **kwargs)
    assert by_code(with_parent, "PROMOTED_FIRM_NOT_LISTED").verdict == "weakened"
    assert by_code(without, "PROMOTED_FIRM_NOT_LISTED").verdict == "upheld"
    assert by_code(with_parent, "BRAND_IMPERSONATION").verdict == "rejected"
    assert by_code(without, "BRAND_IMPERSONATION").verdict == "upheld"
    assert "PARENT_REGISTERED" in {c.code for c in with_parent.against}
    assert with_parent.verdict.breakdown.risk_score < without.verdict.breakdown.risk_score


def test_notified_and_marked_cooperation_weakens_graph_tie(make_ctx):
    graph = {
        "nodes": [
            {"id": "f", "type": "company", "label": BUR, "meta": {"role": "investment_firm"}},
            {"id": "p", "type": "person", "label": "Jan Testowy"},
            {"id": "pr", "type": "pr_agency", "label": "Agencja Testowa"},
            {"id": "i", "type": "influencer", "label": AUTHOR["name"]},
        ],
        "edges": [
            {"source": "p", "target": "f", "type": "board_member"},
            {"source": "p", "target": "pr", "type": "owner"},
            {"source": "pr", "target": "i", "type": "contract"},
        ],
    }
    kwargs = {
        "platform": "youtube",
        "author": AUTHOR,
        "graph": graph,
        "companies": [{"name": BUR, "role": "investment_firm"}],
    }
    disclosed, _ = debate(
        make_ctx, text=f"#reklama Współpraca reklamowa z {BUR}. {RISK}", cooperation_notified=True, **kwargs
    )
    hidden, _ = debate(
        make_ctx,
        text=f"{BUR} to świetny wybór. Załóż konto z mojego linku. {RISK}",
        cooperation_notified=False,
        **kwargs,
    )
    assert by_code(disclosed, "PR_CONFLICT_PATH").confidence < by_code(hidden, "PR_CONFLICT_PATH").confidence
    assert "zgłoszona" in by_code(disclosed, "PR_CONFLICT_PATH").critique


def test_small_comment_sample_weakens_forensics(make_ctx):
    bots = [
        {
            "handle": f"@zysk_pewny{100 + i}",
            "account_created": "2026-11-08T10:00:00Z",
            "country": "NG",
            "lang": "pl",
            "text": "Polecam, zarobiłem w tydzień!",
            "posted_at": "2026-11-10T10:00:00Z",
            "rating": 5,
        }
        for i in range(8)
    ]
    outcome, _ = debate(make_ctx, text="Polski tekst o inwestowaniu, który jest napisany po polsku.", comments=bots)
    claim = by_code(outcome, "FRESH_ACCOUNT_CLUSTER")
    assert claim.verdict == "weakened" and "Mała próba" in claim.critique


def test_partial_register_snapshot_weakens_missing_licence(make_ctx):
    outcome, _ = debate(
        make_ctx, text=f"Testowa Aurora Family Office sp. z o.o. {OFFER}", declared={"advisor_licence_no": "7777"}
    )
    claim = by_code(outcome, "FAKE_LICENCE")
    assert claim.verdict == "weakened" and "niepełna" in claim.critique


def test_recommendation_levels(make_ctx):
    green, _ = debate(make_ctx, text=f"Materiał reklamowy. {BUR}: zysk możliwy. {RISK}")
    red, _ = debate(
        make_ctx,
        text=f"Testowa Aurora Family Office sp. z o.o. {OFFER} Gwarantowany zysk 10% "
        "miesięcznie, bez ryzyka. Zostaw numer.",
    )
    assert green.verdict.recommendation.action == "none" and green.verdict.level == "green"
    assert red.verdict.recommendation.action in {"explain", "escalate"}
    assert red.verdict.recommendation.label in {"Postępowanie wyjaśniające", "Eskalacja"}
    assert "Rekomendacja" in red.verdict.rationale


def test_claim_ids_are_unique_and_sequential(make_ctx):
    outcome, _ = debate(make_ctx, text=f"Testowa Aurora Family Office sp. z o.o. {OFFER}")
    ids = [c.id for c in outcome.all_claims()]
    assert ids == [f"c{i}" for i in itertools.islice(itertools.count(1), len(ids))]
