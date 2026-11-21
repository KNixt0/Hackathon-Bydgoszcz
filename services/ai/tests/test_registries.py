from __future__ import annotations

import json

import pytest

from app.registries import REGISTRIES, RegistryStore, core_name, normalize_name


def test_legal_form_normalisation():
    assert normalize_name("XTB S.A.") == normalize_name("xtb sa") == "xtb"
    assert normalize_name("Kormoran Go sp. z o.o.") == "kormoran go"
    assert normalize_name("Aurum Capital Ltd.") == "aurum capital"
    assert core_name("DOM MAKLERSKI BANKU OCHRONY ŚRODOWISKA S.A.") == "ochrony srodowiska"


@pytest.mark.parametrize(
    "query", ["XTB", "XTB S.A.", "xtb sa", "X-Trade Brokers Dom Maklerski S.A.", "Dom Maklerski XTB"]
)
def test_xtb_is_listed_as_brokerage_house(registries, query):
    match = registries.lookup("knf_brokerage_houses", query)
    assert match and match.listed and match.entry["name"] == "XTB S.A."
    assert registries.lookup("knf_investment_firms", query).listed


@pytest.mark.parametrize("query", ["PKO BP", "Bank Pekao SA", "mBank", "Biuro Maklerskie mBank"])
def test_bank_aliases(registries, query):
    assert registries.lookup("knf_banks_brokerage", query).listed


@pytest.mark.parametrize("query", ["XTB Wealth Partners Ltd", "XTB sp. z o.o.", "Wisła Zmyślona Wealth Management Ltd"])
def test_same_brand_other_entity_is_similar_not_listed(registries, query):
    match = registries.lookup("knf_investment_firms", query)
    assert match and not match.listed and match.how == "brand_contained"


@pytest.mark.parametrize("query", ["Aurum Capital Ltd", "Zupełnie Inna Firma sp. z o.o.", "Capital Partners"])
def test_unrelated_names_do_not_match(registries, query):
    assert registries.lookup("knf_investment_firms", query) is None


def test_real_snapshots_are_bundled(registries):
    rows = {r["registry"]: r for r in registries.summary()}
    assert list(rows) == list(REGISTRIES)
    assert rows["knf_brokerage_houses"]["entries"] >= 28 and rows["knf_foreign_cross_border"]["entries"] >= 700
    assert rows["knf_investment_firms"]["entries"] >= 750
    assert rows["uknf_cooperation_notice"]["entries"] == 0 and rows["uknf_cooperation_notice"]["snapshot_date"] is None
    assert all(rows[r]["snapshot_date"] for r in rows if r != "uknf_cooperation_notice")


def test_demo_overlay_is_flagged_and_optional():
    with_overlay = RegistryStore(None, demo_overlay=True)
    without = RegistryStore(None, demo_overlay=False)
    assert with_overlay.lookup("knf_brokerage_houses", "Dom Maklerski Wisła Zmyślona S.A.").entry["synthetic"] is True
    assert without.lookup("knf_brokerage_houses", "Dom Maklerski Wisła Zmyślona S.A.") is None
    assert without.lookup("knf_brokerage_houses", "XTB S.A.").listed


def test_lookup_by_number(registries):
    assert registries.lookup_number("knf_investment_advisors", "nr 9001")["name"] == "Anna Przykładowa"
    assert registries.lookup_number("knf_investment_advisors", "4821") is None
    assert registries.lookup_number("kirp_legal_advisers", "xx-90001")["status"] == "Nie wykonuje zawodu"


def test_brands_in_text_need_capital_letter(registries):
    text = "Mam konto w XTB, a inc to tylko skrót."
    hits = registries.brands_in_text("knf_investment_firms", text, text.lower())
    assert [text[a:b] for a, b, _ in hits] == ["XTB"]


def test_replace_persists_and_reloads(tmp_path):
    store = RegistryStore(tmp_path, demo_overlay=False)
    n = store.replace("knf_public_warnings", "2026-12-01", [{"name": "Nowy Podmiot Testowy Ltd", "aliases": ["NPT"]}])
    assert n == 1
    assert store.snapshot("knf_public_warnings").snapshot_date == "2026-12-01"
    assert store.lookup("knf_public_warnings", "Nowy Podmiot Testowy").listed
    saved = json.loads((tmp_path / "registries" / "knf_public_warnings.json").read_text(encoding="utf-8"))
    assert saved["entries"][0]["name"] == "Nowy Podmiot Testowy Ltd"
    assert RegistryStore(tmp_path, demo_overlay=False).lookup("knf_public_warnings", "NPT").listed


def test_replace_rejects_context_only_and_unknown(tmp_path):
    store = RegistryStore(tmp_path)
    with pytest.raises(ValueError):
        store.replace("uknf_cooperation_notice", "2026-12-01", [])
    with pytest.raises(KeyError):
        store.replace("nope", "2026-12-01", [])
