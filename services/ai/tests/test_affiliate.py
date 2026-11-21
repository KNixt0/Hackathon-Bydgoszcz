"""Module 1: affiliate links and redirect chains to registered firms (contract v3 inputs)."""

from __future__ import annotations

import asyncio

from app.schemas import AnalyzeRequest

BLOG = (
    "<html lang='pl'><body><h1>Mój rachunek maklerski po roku</h1>"
    "<p>Od roku inwestuję przez Dom Maklerski Bursztyn Przykładowy S.A. i opisuję swoje wrażenia.</p>"
    "<p>{marker}Jeśli chcesz spróbować, <a href='{href}'>otwórz rachunek tutaj</a>.</p>"
    "<p>Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanych środków.</p></body></html>"
)


def analyze(engine, href: str, marker: str = "", **doc):
    body = {
        "document": {
            "url": "https://blog.example/wpis",
            "platform": "web",
            "fetched_at": "2026-11-21T12:00:00Z",
            "html": BLOG.format(href=href, marker=marker),
            "author": {"name": "Blog Zmyślone Finanse"},
            **doc,
        },
        "context": {"module_hint": 1},
    }
    request = AnalyzeRequest.model_validate(body)
    return asyncio.run(engine.analyze(request.document, request.context))


def findings(a) -> dict[str, object]:
    return {f.code: f for m in a.module_results for f in m.findings}


def test_affiliate_link_to_registered_firm_is_a_commercial_tie(engine):
    a = analyze(engine, "https://bursztyn-przykladowy.example/konto?ref=blog23&utm_source=blog")
    f = findings(a)["AFFILIATE_LINK_TO_FIRM"]
    assert "ref=blog23" in f.text and "nie jest oznaczony" in f.text
    ev = {e.id: e for e in a.evidence}
    assert any(ev[i].kind == "url" and "ref=blog23" in ev[i].url for i in f.evidence_ids)


def test_scraper_supplied_links_are_used(engine):
    a = analyze(
        engine,
        "https://bursztyn-przykladowy.example/konto",  # rendered DOM had the tracking link, the HTML not
        affiliate_links=[
            {
                "url": "https://bursztyn-przykladowy.example/konto?aff=77",
                "host": "bursztyn-przykladowy.example",
                "params": ["aff=77"],
            }
        ],
        affiliate_params=["aff=77"],
    )
    assert "aff=77" in findings(a)["AFFILIATE_LINK_TO_FIRM"].text


def test_marked_material_reports_disclosed_link_without_risk(engine):
    marked = analyze(engine, "https://bursztyn-przykladowy.example/konto?ref=blog23", marker="Reklama. ")
    f = findings(marked)
    assert "AFFILIATE_LINK_TO_FIRM" not in f and f["AFFILIATE_LINK_DISCLOSED"].severity == "info"
    unmarked = analyze(engine, "https://bursztyn-przykladowy.example/konto?ref=blog23")
    assert unmarked.risk_score > marked.risk_score


def test_links_to_other_domains_or_without_params_are_ignored(engine):
    for href in ("https://shop.example/x?ref=1", "https://bursztyn-przykladowy.example/konto"):
        assert not {"AFFILIATE_LINK_TO_FIRM", "AFFILIATE_LINK_DISCLOSED"} & set(findings(analyze(engine, href)))


def test_redirect_chain_landing_on_firm_with_params(engine):
    a = analyze(
        engine,
        "https://blog.example/inny-wpis",
        final_url="https://bursztyn-przykladowy.example/start?partner=xyz",
        redirect_chain=["https://sho.rt/abc", "https://bursztyn-przykladowy.example/start?partner=xyz"],
        affiliate_params=["partner=xyz"],
    )
    f = findings(a)["AFFILIATE_LINK_TO_FIRM"]
    assert "przekierowuje" in f.text and "partner=xyz" in f.text
