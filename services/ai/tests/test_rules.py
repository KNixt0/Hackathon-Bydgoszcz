"""Each of the 19 criteria: one material that passes and one that fails."""

from __future__ import annotations

import pytest

from app.rules import RULE_ORDER, SPECS, run_rules

RISK = "Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanych środków."
STD = (
    "Kontrakty CFD są złożonymi instrumentami i wiążą się z dużym ryzykiem szybkiej utraty środków pieniężnych z "
    "powodu dźwigni finansowej. 76% rachunków inwestorów detalicznych odnotowuje straty pieniężne w wyniku handlu "
    "kontraktami CFD u niniejszego dostawcy."
)
FIRM = "Dom Maklerski Bursztyn Przykładowy S.A."


def page(body: str, style: str = "", head: str = '<meta name="viewport" content="width=device-width">') -> dict:
    return {
        "html": f"<html><head>{head}<style>body{{font-size:16px;color:#111;background:#fff}}{style}</style></head>"
        f"<body>{body}</body></html>"
    }


CLAIM = f"<p>Materiał reklamowy. {FIRM} daje szansę na wysoki zysk.</p>"

# rule id -> (passing material, failing material); each is kwargs for make_ctx
CASES: dict[str, tuple[dict, dict]] = {
    "1": (
        {"text": f"Reklama. {FIRM} zaprasza. Zysk możliwy. {RISK}"},
        {"text": f"Reklama. Zarabiaj z Bursztynem już dziś. {RISK}"},
    ),
    "2": (
        {"text": f"Materiał reklamowy. {FIRM}: zysk możliwy. {RISK}"},
        {"text": f"{FIRM}: zarabiaj z nami, załóż konto już dziś. {RISK}"},
    ),
    "3": (
        {"text": f"Reklama. {FIRM}: zysk możliwy. {RISK}"},
        {"text": f"Reklama. {FIRM}: zarabiaj 20% rocznie, załóż konto."},
    ),
    "4": (page(f"{CLAIM}<p>{RISK}</p>"), page(f"{CLAIM}<p class='r'>{RISK}</p>", ".r{font-size:9px}")),
    "5": (page(f"{CLAIM}<p>{RISK}</p>"), page(f"{CLAIM}<p class='r'>{RISK}</p>", ".r{color:#cccccc}")),
    "6": (page(f"{CLAIM}<p>{RISK}</p>"), page(f"{CLAIM}<footer><small>{RISK}</small></footer>")),
    "7": (
        page(f"{CLAIM}<p>{RISK}</p>"),
        page(f"{CLAIM}<details><summary>Nota prawna – rozwiń</summary><p>{RISK}</p></details>"),
    ),
    "8": (
        page(f"{CLAIM}<p>{RISK}</p>"),
        page(f"{CLAIM}<p class='r'>{RISK}</p>", "@media (max-width:600px){.r{display:none}}"),
    ),
    "9": (
        {"text": f"Reklama. {FIRM}: zysk możliwy. {STD}"},
        {
            "text": f"Reklama. {FIRM}: zysk możliwy. Inwestowanie wiąże się z ryzykiem utraty kapitału wynikającym z "
            "niekorzystnej zmienności wyceny instrumentów bazowych, uwarunkowań makroekonomicznych, "
            "ograniczonej płynności, niewypłacalności kontrahenta, ekspozycji lewarowanej oraz nieprzewidywalnych "
            "okoliczności geopolitycznych oddziałujących równocześnie na wielosegmentowe rynki kapitałowe, "
            "towarowe i walutowe w perspektywie krótkoterminowej, średnioterminowej oraz długoterminowej, "
            "co inwestor powinien uwzględnić przed podjęciem jakiejkolwiek decyzji inwestycyjnej."
        },
    ),
    "10": (
        {"text": f"Reklama. {FIRM}: handluj kontraktami i zarabiaj na wzrostach. {RISK}"},
        {
            "text": f"Reklama. {FIRM}: handluj kontraktami i zarabiaj na wzrostach oraz spadkach, aplikacja po polsku. "
            "CFDs are complex instruments and come with a high risk of losing money rapidly due to leverage. "
            "Most retail investor accounts lose money when trading with this provider."
        },
    ),
    "11": (
        {
            "text": f"Reklama. {FIRM}: prowizja niższa niż średnia rynkowa. Źródło: zestawienie taryf, stan na "
            f"30.09.2026, przy założeniu zlecenia 5 000 zł. {RISK}"
        },
        {"text": f"Reklama. {FIRM} to najtańszy broker w Polsce. {RISK}"},
    ),
    "12a": (
        {
            "text": f"Reklama {FIRM}. Stopa zwrotu w latach 2021–2025 wyniosła 8%, -4%, 11%, 6% i 9% (pełne lata, "
            "okres 01.01.2021–31.12.2025). Źródło: opracowanie własne. Wyniki po uwzględnieniu opłat. "
            f"Wyniki historyczne nie stanowią gwarancji przyszłych wyników. {RISK}"
        },
        {"text": f"Reklama {FIRM}. Portfel zarobił 40% w 3 miesiące. {RISK}"},
    ),
    "12b": (
        {
            "text": f"Reklama {FIRM}. W 2024 r. portfel w USD zarobił 12%. Wynik po uwzględnieniu prowizji i opłat. "
            f"Zmiany kursów walut mogą wpłynąć na wynik. {RISK}"
        },
        {"text": f"Reklama {FIRM}. W 2024 r. portfel akcji amerykańskich w USD zarobił 12%. {RISK}"},
    ),
    "13": (
        page(f"{CLAIM}<p>W 2024 r. portfel zarobił 12%.</p><p>{RISK}</p>"),
        page(f"<h1>W 2024 r. portfel zarobił 12%</h1>{CLAIM}<p>{RISK}</p>"),
    ),
    "14": (
        {
            "text": f"Reklama {FIRM}. W 2024 r. portfel zarobił 12%. Wyniki historyczne nie stanowią gwarancji "
            f"przyszłych wyników. {RISK}"
        },
        {"text": f"Reklama {FIRM}. W 2024 r. portfel zarobił 12%. {RISK}"},
    ),
    "15": (
        {
            "text": f"Reklama {FIRM}. Prognozujemy wzrost indeksu o 5%. Prognozy nie stanowią wiarygodnego wskaźnika "
            f"przyszłych wyników. {RISK}"
        },
        {"text": f"Reklama {FIRM}. Akcje spółek AI wzrosną o 50% do końca roku. {RISK}"},
    ),
    "16": (
        {
            "text": f"Reklama {FIRM}. Zyski z IKE mogą być zwolnione z podatku. Traktowanie podatkowe zależy od "
            f"indywidualnej sytuacji klienta i może ulec zmianie w przyszłości. {RISK}"
        },
        {"text": f"Reklama {FIRM}. Inwestuj bez podatku Belki na koncie IKZE. {RISK}"},
    ),
    "17": (
        {"text": f"Reklama. {FIRM} podlega nadzorowi Komisji Nadzoru Finansowego. {RISK}"},
        {"text": f"Reklama. Produkt {FIRM} został zatwierdzony przez KNF. {RISK}"},
    ),
    "18": (
        {"text": f"Reklama. {FIRM} podlega nadzorowi Komisji Nadzoru Finansowego. {RISK}"},
        {
            "text": f"Reklama. Nasza inwestycja jest w pełni bezpieczna – {FIRM} spełnia rygorystyczne wymogi "
            f"nadzorcze KNF. {RISK}"
        },
    ),
}


def status(make_ctx, rule_id: str, kwargs: dict) -> str:
    ctx = make_ctx(companies=[{"name": FIRM, "role": "investment_firm"}], **kwargs)
    return next(r for r in run_rules(ctx) if r.id == rule_id).status


def test_every_rule_has_a_case():
    assert list(CASES) == RULE_ORDER


@pytest.mark.parametrize("rule_id", RULE_ORDER)
def test_rule_passes(make_ctx, rule_id):
    assert status(make_ctx, rule_id, CASES[rule_id][0]) == "pass"


@pytest.mark.parametrize("rule_id", RULE_ORDER)
def test_rule_fails(make_ctx, rule_id):
    assert status(make_ctx, rule_id, CASES[rule_id][1]) == "fail"


def test_always_19_rows_in_attachment_order(make_ctx):
    rules = run_rules(make_ctx(text="Dzień dobry."))
    assert [r.id for r in rules] == RULE_ORDER and len(rules) == 19
    assert all(r.name == SPECS[r.id].name and r.legal_basis == SPECS[r.id].legal_basis for r in rules)
    assert SPECS["18"].name == "Nadzór jako argument bezpieczeństwa"
    assert SPECS["2"].legal_basis == "art. 24 ust. 3 MiFID II"
    assert SPECS["6"].legal_basis == "art. 44 ust. 2 lit. e rozporządzenia del. 2017/565"


def test_visual_rules_are_unknown_without_html(make_ctx):
    rules = {r.id: r for r in run_rules(make_ctx(text=f"Reklama. {FIRM}: zysk możliwy. {RISK}"))}
    assert [rules[i].status for i in ("4", "5", "7", "8")] == ["unknown"] * 4
    assert all(rules[i].confidence == 0 for i in ("4", "5", "7", "8"))


def test_visual_rules_not_applicable_without_risk_text(make_ctx):
    rules = {r.id: r for r in run_rules(make_ctx(text="Reklama. Zarabiaj 20% rocznie."))}
    assert rules["3"].status == "fail" and rules["4"].status == "na" and rules["9"].status == "na"


def test_negated_guarantee_is_a_warning_not_a_claim(make_ctx):
    ctx = make_ctx(text="Nie gwarantujemy zysku. Inwestycje są ryzykowne.")
    assert not ctx.facts.guarantees and not ctx.facts.profit_claims and len(ctx.facts.risk) == 2


def test_external_stylesheet_makes_contrast_unknown(make_ctx):
    html = f'<html><head><link rel="stylesheet" href="a.css"></head><body>{CLAIM}<p>{RISK}</p></body></html>'
    rules = {r.id: r for r in run_rules(make_ctx(html=html))}
    assert rules["5"].status == "unknown" and rules["8"].status == "unknown" and rules["4"].status == "unknown"
