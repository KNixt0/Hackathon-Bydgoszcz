from __future__ import annotations

from app.plugins import Plugin, discover, get_plugins

BUR = "Dom Maklerski Bursztyn Przykładowy S.A."
RISK = "Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanych środków."
AUTHOR = {"name": "Testowy Twórca Finansowy", "handle": "@testowy"}


def run(make_ctx, plugin_id: str, **kwargs):
    ctx = make_ctx(**kwargs)
    plugin = get_plugins()[plugin_id]
    assert plugin.applies(ctx)
    return plugin.run(ctx), ctx


def codes(result) -> set[str]:
    return {f.code for f in result.findings}


# ---------------------------------------------------------------- registry / discovery
def test_discovery_finds_all_plugins_in_module_order():
    plugins = discover()
    assert list(plugins) == [
        "m1_finfluencer",
        "m2_risk_disclosure",
        "m3_shadow_advisory",
        "graph_intel",
        "opinion_forensics",
    ]
    assert [p.module for p in plugins.values()] == [1, 2, 3, None, None]
    assert all(isinstance(p, Plugin) and p.description for p in plugins.values())


# ---------------------------------------------------------------- module 1
def test_m1_compliant_campaign(make_ctx):
    res, _ = run(
        make_ctx,
        "m1_finfluencer",
        platform="youtube",
        author=AUTHOR,
        text=f"#reklama Współpraca reklamowa z {BUR}. Link w opisie. {RISK}",
        cooperation_notified=True,
        companies=[{"name": BUR, "role": "investment_firm"}],
    )
    assert {"FIRM_REGISTERED", "COOPERATION_NOTIFIED", "AD_MARKED"} <= codes(res)
    assert all(f.severity == "info" for f in res.findings)
    by_reg = {c.registry: c for c in res.registry_checks}
    assert by_reg["knf_brokerage_houses"].status == "listed" and by_reg["knf_banks_brokerage"].status == "not_listed"
    assert by_reg["uknf_cooperation_notice"].status == "listed"
    assert by_reg["knf_public_warnings"].status == "not_listed"


def test_m1_unmarked_unnotified_ad_of_unlisted_firm(make_ctx):
    res, _ = run(
        make_ctx,
        "m1_finfluencer",
        platform="tiktok",
        author=AUTHOR,
        text="Testowa Platforma Zysku Ltd wypłaca zyski co tydzień. Załóż konto z mojego linku.",
        cooperation_notified=False,
    )
    assert {"PROMOTED_FIRM_NOT_LISTED", "COOPERATION_NOT_NOTIFIED", "UNMARKED_THIRD_PARTY_AD"} <= codes(res)
    assert next(c for c in res.registry_checks if c.registry == "uknf_cooperation_notice").status == "not_listed"


def test_m1_disguised_ad_and_unknown_notification(make_ctx):
    res, _ = run(
        make_ctx,
        "m1_finfluencer",
        platform="instagram",
        author=AUTHOR,
        text=f"To nie jest reklama: {BUR} ma świetną aplikację. Załóż konto z kodem rabatowym TEST.",
        companies=[{"name": BUR, "role": "investment_firm"}],
    )
    assert "DISGUISED_AD" in codes(res) and "UNMARKED_THIRD_PARTY_AD" not in codes(res)
    assert next(c for c in res.registry_checks if c.registry == "uknf_cooperation_notice").status == "not_checked"


def test_m1_warning_list_and_inactive_legal_adviser(make_ctx):
    res, _ = run(
        make_ctx,
        "m1_finfluencer",
        platform="youtube",
        author=AUTHOR,
        text="Fikcja Trade Solutions OÜ to pewny zysk. Link w bio.",
        declared={"legal_adviser_name": "Marek Nieistniejący", "legal_adviser_no": "XX-90001"},
    )
    assert {"WARNING_LISTED", "LEGAL_ADVISER_INACTIVE"} <= codes(res)
    kirp = next(c for c in res.registry_checks if c.registry == "kirp_legal_advisers")
    assert kirp.status == "inactive" and kirp.detail == "Nie wykonuje zawodu"


def test_m1_not_applicable_for_firms_own_channel(make_ctx):
    ctx = make_ctx(
        text=f"{BUR} zaprasza.",
        author={"name": "DM Bursztyn Przykładowy"},
        companies=[{"name": BUR, "role": "investment_firm"}],
    )
    assert not get_plugins()["m1_finfluencer"].applies(ctx)


# ---------------------------------------------------------------- module 2
def test_m2_reports_failed_rules_and_proportion(make_ctx):
    text = (
        "Reklama. "
        + "Zarabiaj więcej, zysk rośnie, pomnażaj oszczędności z nami każdego dnia. " * 6
        + "Inwestycje są ryzykowne."
    )
    res, _ = run(make_ctx, "m2_risk_disclosure", text=text)
    assert len(res.rules) == 19
    assert "PROFIT_RISK_IMBALANCE" in codes(res) and "RULES_SUMMARY" in codes(res)
    res2, _ = run(make_ctx, "m2_risk_disclosure", text="Zarabiaj 20% rocznie, gwarantowany zysk, załóż konto.")
    assert {"RULE_2", "RULE_3"} <= codes(res2)
    assert all(f.evidence_ids for f in res2.findings if f.code.startswith("RULE_"))


# ---------------------------------------------------------------- module 3
OFFER = (
    "Testowa Aurora Family Office sp. z o.o. przygotuje dla Ciebie indywidualne rekomendacje: wskażemy, które "
    "akcje i obligacje kupić, a które sprzedać. Zarządzamy Twoim portfelem. Gwarantowany zysk 10% miesięcznie."
)


def test_m3_unauthorised_personalised_advice(make_ctx):
    res, ctx = run(make_ctx, "m3_shadow_advisory", text=OFFER)
    assert {"ADVISORY_PHRASE", "PORTFOLIO_MANAGEMENT", "GUARANTEED_RETURN", "REGISTRY_NOT_LISTED"} <= codes(res)
    advisory = next(f for f in res.findings if f.code == "ADVISORY_PHRASE")
    legal = [ctx.evidence.get(e).legal_ref for e in advisory.evidence_ids if ctx.evidence.get(e).kind == "legal"]
    assert "art. 76 ustawy o obrocie instrumentami finansowymi" in legal
    assert {c.registry for c in res.registry_checks} >= {
        "knf_investment_firms",
        "knf_banks_brokerage",
        "knf_brokerage_houses",
        "knf_foreign_branches",
        "knf_foreign_cross_border",
        "knf_public_warnings",
    }


def test_m3_authorised_firm_is_not_accused(make_ctx):
    res, _ = run(
        make_ctx,
        "m3_shadow_advisory",
        text=f"{BUR} świadczy doradztwo inwestycyjne: rekomendacje akcji dopasowane do Twojej sytuacji.",
    )
    assert "ENTITY_AUTHORISED" in codes(res) and "REGISTRY_NOT_LISTED" not in codes(res)


def test_m3_negated_offer_is_ignored(make_ctx):
    ctx = make_ctx(text="Nie świadczymy doradztwa inwestycyjnego ani nie rekomendujemy instrumentów finansowych.")
    assert not get_plugins()["m3_shadow_advisory"].applies(ctx)


def test_m3_fake_and_valid_licence(make_ctx):
    res, _ = run(
        make_ctx,
        "m3_shadow_advisory",
        platform="instagram",
        author=AUTHOR,
        text="Mentoring inwestycyjny. Doradca inwestycyjny, licencja nr 7777, powie Ci, które spółki kupić.",
    )
    assert "FAKE_LICENCE" in codes(res)
    assert next(c for c in res.registry_checks if c.registry == "knf_investment_advisors").status == "not_listed"
    res2, _ = run(make_ctx, "m3_shadow_advisory", text=OFFER, declared={"advisor_licence_no": "9001"})
    assert "ADVISOR_LICENCE_VALID" in codes(res2)


def test_m3_brand_impersonation(make_ctx):
    res, _ = run(
        make_ctx,
        "m3_shadow_advisory",
        url="https://bursztyn-vip.example/oferta",
        text="Bursztyn Przykładowy Capital Ltd: nasz doradca wskaże Ci, które akcje kupić.",
        companies=[{"name": "Bursztyn Przykładowy Capital Ltd", "role": "investment_firm"}],
    )
    imp = next(f for f in res.findings if f.code == "BRAND_IMPERSONATION")
    assert imp.data["registered"] == BUR and imp.severity == "high"


def test_m3_tax_adviser_check(make_ctx):
    res, _ = run(make_ctx, "m3_shadow_advisory", text=OFFER, declared={"tax_adviser_no": "12345"})
    assert "TAX_ADVISER_NOT_FOUND" in codes(res)
    assert next(c for c in res.registry_checks if c.registry == "kidp_tax_advisers").status == "not_listed"


# ---------------------------------------------------------------- graph
GRAPH = {
    "nodes": [
        {"id": "go", "type": "company", "label": "Testowa Spółka Go sp. z o.o.", "meta": {"role": "investment_firm"}},
        {"id": "parent", "type": "company", "label": "Testowa Matka S.A."},
        {"id": "board", "type": "person", "label": "Jan Testowy"},
        {"id": "pr", "type": "pr_agency", "label": "Agencja Testowa"},
        {"id": "inf", "type": "influencer", "label": "Testowy Twórca Finansowy"},
        {"id": "ad", "type": "ad", "label": "Film"},
    ],
    "edges": [
        {"source": "parent", "target": "go", "type": "owner", "label": "100%"},
        {"source": "board", "target": "parent", "type": "board_member", "label": "zarząd"},
        {"source": "board", "target": "pr", "type": "owner", "label": "wspólnik"},
        {"source": "pr", "target": "inf", "type": "contract", "label": "umowa"},
        {"source": "inf", "target": "ad", "type": "publishes", "label": "publikuje"},
        {"source": "ad", "target": "go", "type": "promotes", "label": "promuje"},
    ],
}


def test_graph_finds_board_pr_influencer_path(make_ctx):
    res, _ = run(make_ctx, "graph_intel", text="x", graph=GRAPH)
    assert "PR_CONFLICT_PATH" in codes(res)
    path = res.graph.flagged_paths[0]
    assert path.node_ids == ["go", "parent", "board", "pr", "inf"]
    assert "członek zarządu" in path.description and "Agencja Testowa" in path.description
    suspicious = {(e.source, e.target) for e in res.graph.edges if e.suspicious}
    assert suspicious == {("parent", "go"), ("board", "parent"), ("board", "pr"), ("pr", "inf")}


def test_graph_direct_contract_is_not_flagged(make_ctx):
    graph = {
        "nodes": GRAPH["nodes"][:1] + GRAPH["nodes"][4:],
        "edges": [
            {"source": "go", "target": "inf", "type": "contract", "label": "umowa reklamowa"},
            {"source": "inf", "target": "ad", "type": "publishes"},
            {"source": "ad", "target": "go", "type": "promotes"},
        ],
    }
    res, _ = run(make_ctx, "graph_intel", text="x", graph=graph)
    assert res.graph.flagged_paths == [] and "NO_HIDDEN_TIES" in codes(res)
    assert not any(e.suspicious for e in res.graph.edges)


def test_financial_flags(make_ctx):
    res, _ = run(
        make_ctx,
        "graph_intel",
        text="x",
        companies=[
            {
                "name": "Testowa Spółka Go sp. z o.o.",
                "role": "investment_firm",
                "incorporated_on": "2025-12-10",
                "share_capital_pln": 5000,
                "statements": [],
            }
        ],
    )
    assert res.financials.age_months == 11 and res.financials.share_capital_pln == 5000
    assert res.financials.flags == [
        "Spółka młodsza niż 12 miesięcy",
        "Minimalny kapitał zakładowy (5 000 zł)",
        "Brak pełnego sprawozdania finansowego",
    ]
    assert {"COMPANY_YOUNG", "LOW_SHARE_CAPITAL", "NO_FINANCIAL_STATEMENTS"} == codes(res)


def test_financials_with_unknown_data_have_no_flags(make_ctx):
    res, _ = run(make_ctx, "graph_intel", text="x", companies=[{"name": "XTB S.A.", "role": "investment_firm"}])
    f = res.financials
    assert (f.krs, f.incorporated_on, f.age_months, f.share_capital_pln, f.statements, f.flags) == (
        None,
        None,
        None,
        None,
        [],
        [],
    )


def test_foreign_shell_flag(make_ctx):
    res, _ = run(
        make_ctx,
        "graph_intel",
        text="x",
        companies=[{"name": "Testowa Shell Ltd", "role": "investment_firm", "country": "SC"}],
    )
    assert "FOREIGN_SHELL" in codes(res) and "Siedziba poza EOG (SC)" in res.financials.flags


# ---------------------------------------------------------------- forensics
def comment(handle, created, posted, country="PL", text="Opinia", rating=5):
    return {
        "handle": handle,
        "account_created": created,
        "country": country,
        "lang": "pl",
        "text": text,
        "posted_at": posted,
        "rating": rating,
    }


ORGANIC = [
    comment(
        f"@user_{name}",
        f"20{15 + i % 8}-03-01T10:00:00Z",
        f"2026-11-{1 + i:02d}T10:00:00Z",
        text=f"Komentarz numer {i} o czymś zupełnie innym {name}",
        rating=3 + i % 3,
    )
    for i, name in enumerate(["ala", "ola", "jan", "ewa", "iza", "adam", "piotr", "kasia", "marek", "zosia"])
]
BOTS = [
    comment(
        f"@zysk_pewny{100 + i}",
        "2026-11-08T10:00:00Z",
        f"2026-11-10T{8 + i % 10:02d}:00:00Z",
        "NG",
        "Polecam, zarobiłem w tydzień!",
    )
    for i in range(30)
]


def test_forensics_organic_comments(make_ctx):
    res, _ = run(make_ctx, "opinion_forensics", text="Polski tekst o inwestowaniu i ryzyku.", comments=ORGANIC)
    f = res.forensics
    assert f.accounts.total == 10 and f.accounts.share_younger_14d == 0 and f.anomalies == []
    assert codes(res) == {"ORGANIC_OPINIONS"}
    assert [b.bucket for b in f.accounts.age_buckets] == ["<14d", "14–90d", "3–12m", "1–3y", ">3y"]


def test_forensics_bot_farm(make_ctx):
    res, _ = run(
        make_ctx,
        "opinion_forensics",
        text="Polski tekst o inwestowaniu i ryzyku, który jest po polsku.",
        comments=ORGANIC + BOTS,
    )
    f = res.forensics
    assert f.accounts.share_younger_14d == 0.75
    assert {a.type for a in f.anomalies} == {
        "opinion_spike",
        "fresh_account_cluster",
        "name_pattern_cluster",
        "foreign_origin_cluster",
    }
    assert f.accounts.name_patterns[0].pattern == "zysk_pewny<cyfry>" and f.accounts.name_patterns[0].count == 30
    spike = next(p for p in f.opinion_timeline if p.date == "2026-11-10")
    assert spike.count == 31 and spike.new_account_share > 0.9
    assert f.accounts.origins[0].country == "NG"
    assert all(f.evidence_ids for f in res.findings)


def test_forensics_makes_no_claim_on_tiny_samples(make_ctx):
    res, _ = run(make_ctx, "opinion_forensics", text="Polski tekst.", comments=BOTS[:3])
    assert res.findings == [] and res.forensics.anomalies == []
