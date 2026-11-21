"""UKNF remit (contract v4 `scope`): material outside modules 1-3 is never flagged."""

from __future__ import annotations

import asyncio

import pytest

from app.schemas import Context, Document
from app.scoring import weights as W


def analyze(engine, text: str, url: str = "https://przyklad.pl/oferta", **doc) -> object:
    document = Document(
        url=url, platform=doc.pop("platform", "web"), fetched_at="2026-11-21T12:00:00Z", text=text, **doc
    )
    return asyncio.run(engine.analyze(document, Context()))


OUT_OF_SCOPE = {
    "consumer_credit": "SzybkaKasa sp. z o.o. Pożyczka do 5000 zł w 15 minut, RRSO 0%, bez BIK. Zysk dla Ciebie!",
    "deposit": "Bank Przykładowy S.A. Lokata 8% w skali roku, gwarantowany zysk bez ryzyka. Załóż lokatę online.",
    "crypto": "KryptoEx: kupuj Bitcoin i Ethereum, klienci zarobili 200% w rok! Opiekun wskaże, które kryptowaluty kupić.",
    "insurance": "Polisa inwestycyjna z UFK Towarzystwa Ubezpieczeń Przykład S.A. - nawet 12% rocznie!",
    "tax_legal": "Kancelaria Podatkowa Nowak, doradca podatkowy. Rozliczymy PIT-38 i podatek od zysków kapitałowych.",
    "no_financial_offer": "ButyMax: wyprzedaż! Zysk dla Ciebie: rabaty do 50%. Inwestuj w wygodę, trzecia para gratis.",
}


@pytest.mark.parametrize(("category", "text"), OUT_OF_SCOPE.items())
def test_out_of_scope_material_is_not_flagged(engine, category, text):
    a = analyze(engine, text)
    assert a.scope.in_scope is False and a.scope.category == category
    assert a.title.startswith("Materiał poza właściwością UKNF")
    assert a.risk_score < W.T_ORANGE and a.risk_level == "green"
    assert a.recommendation.action == "none" and a.recommendation.label == "Poza właściwością UKNF"
    assert all(r.status == "na" for r in a.rules) and len(a.rules) == 19
    assert not [f for m in a.module_results for f in m.findings if f.severity != "info"]


def test_foreign_language_ad_of_unknown_firm_is_out_of_scope(engine):
    a = analyze(
        engine,
        "Trade CFDs with GlobalFX Markets Ltd. Earn up to 200% a year. Open your account now.",
        "https://globalfx.example/en",
    )
    assert a.scope.in_scope is False and a.scope.category == "foreign_market"


def test_unlicensed_investment_promise_stays_in_scope(engine):
    a = analyze(
        engine, "Testowa Platforma Zysku Ltd wypłaca zyski co tydzień. Wpłać 1000 zł i odbierz 20% miesięcznie."
    )
    assert a.scope.in_scope is True and a.scope.basis == "investment_offer"
    assert a.risk_score >= W.T_ORANGE


def test_licensed_tfi_is_not_unlicensed_advice(engine):
    a = analyze(
        engine,
        "Quercus TFI S.A. oferuje zarządzanie portfelami instrumentów finansowych. Nasz doradca przygotuje dla "
        "Ciebie indywidualne rekomendacje, które akcje kupić, a które sprzedać.",
        "https://quercus-przyklad.pl/zarzadzanie",
    )
    codes = {f.code for m in a.module_results for f in m.findings}
    assert a.scope.basis == "supervised_entity"
    assert "REGISTRY_NOT_LISTED" not in codes and "ENTITY_AUTHORISED" in codes
    assert any(c.registry == "knf_tfi" and c.status == "listed" for c in a.registry_checks)
    assert a.risk_score < W.T_ORANGE


def test_bank_brokerage_name_is_resolved_with_its_prefix(engine):
    a = analyze(engine, "mBank S.A. Biuro maklerskie: zarządzanie portfelem akcji dla klientów private banking.")
    assert a.entities.investment_firm.name == "mBank S.A."


def test_professional_self_regulation_findings_do_not_score(engine):
    for code in ("LEGAL_ADVISER_INACTIVE", "LEGAL_ADVISER_NOT_FOUND", "TAX_ADVISER_INACTIVE", "TAX_ADVISER_NOT_FOUND"):
        assert W.FINDING_WEIGHTS[code] == 0.0
    assert W.FINDING_WEIGHTS["COOPERATION_NOT_NOTIFIED"] == 0.0


def test_recommendations_never_propose_formal_steps(engine):
    from app.debate.arbiter import RECOMMENDATIONS

    text = " ".join(label + " " + step for label, step in RECOMMENDATIONS.values()).lower()
    for forbidden in ("wezwa", "zawiadom", "lista ostrzeżeń", "listę ostrzeżeń", "przestęp"):
        assert forbidden not in text


def test_published_at_is_kept_apart_from_detection(engine):
    a = analyze(engine, "Fundusz akcji Przykład: stopa zwrotu 9% w 2025 r.", published_at="2026-11-01")
    assert a.source.published_at == "2026-11-01" and a.source.fetched_at == "2026-11-21T12:00:00Z"
