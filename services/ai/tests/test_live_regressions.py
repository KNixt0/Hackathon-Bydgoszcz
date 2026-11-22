"""Regressions found by the bounded public-page scrape, with minimal source-derived inputs."""

from app.preprocess.normalize import fold
from app.registries.matching import find_brands_in_text


def test_sector_words_do_not_identify_inc_in_bos_material(make_ctx):
    text = (
        "Dom maklerski. Oferta domu maklerskiego. Dom maklerski. "
        "Dom Maklerski Banku Ochrony Środowiska S.A. z siedzibą w Warszawie. "
        "Dom maklerski. Dom maklerski."
    )
    ctx = make_ctx(text=text, author={"name": "Dom Maklerski Banku Ochrony Środowiska"})
    assert ctx.entities.firm.name == "DOM MAKLERSKI BANKU OCHRONY ŚRODOWISKA S.A."
    assert not ctx.entities.third_party
    assert all(entry["name"] != "DOM MAKLERSKI INC S.A." for _, _, entry in ctx.entities.registered_brands)


def test_literal_inc_name_still_identifies_the_actual_firm():
    entry = {"name": "DOM MAKLERSKI INC S.A.", "aliases": []}
    text = "Dom Maklerski INC S.A. opublikował ofertę."
    assert find_brands_in_text(text, fold(text), [entry])[0][2] is entry
    assert find_brands_in_text("Dom maklerski", fold("Dom maklerski"), [entry]) == []


def test_long_register_names_are_not_cut_off_at_six_words():
    entry = {"name": "Pierwszy Krajowy Specjalistyczny Zintegrowany Dom Maklerski Nowa Firma", "aliases": []}
    text = entry["name"] + " świadczy usługi."
    hits = find_brands_in_text(text, fold(text), [entry])
    assert len(hits) == 1 and text[hits[0][0] : hits[0][1]] == entry["name"]


def test_all_three_modules_are_checked_even_when_not_all_apply(analyze, engine, monkeypatch):
    from unittest.mock import Mock

    probes = {}
    for name, plugin in engine.plugins.items():
        probe = Mock(wraps=plugin.applies)
        monkeypatch.setattr(plugin, "applies", probe)
        probes[name] = probe
    result = analyze(text="Rzetelna informacja o rachunku maklerskim. Inwestowanie wiąże się z ryzykiem.")
    assert {plugin.module for name, plugin in engine.plugins.items() if probes[name].called and plugin.module} == {
        1,
        2,
        3,
    }
    assert len(result.rules) == 19
