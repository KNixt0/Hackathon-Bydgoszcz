"""Rules 1-2: who is behind the material and whether it is marked as advertising."""

from __future__ import annotations

from .base import RuleOutcome, RuleView, failed, not_applicable, passed, rule


def is_promotional(v: RuleView) -> bool:
    """Promotional = praises returns, calls to action, is marked as an ad or is a notified cooperation.

    A third party merely mentioning a firm is not advertising.
    """
    f = v.facts
    return bool(f.profit_claims or f.cta or f.ad_markers or v.ctx.context.cooperation_notified)


@rule("1", "Identyfikacja firmy", "art. 44 ust. 2 lit. a rozporządzenia del. 2017/565")
def identification(v: RuleView) -> RuleOutcome:
    ent = v.ctx.entities
    if ent.official_name_span:
        a, b = ent.official_name_span
        ev = [v.ctx.evidence.quote(a, b, "Oficjalna nazwa firmy w materiale")]
        return passed(f"Materiał zawiera oficjalną nazwę firmy: „{v.page.text[a:b]}”.", 0.9, ev)
    for a, b, entry in ent.registered_brands:
        if v.page.text[a:b].lower() == entry["name"].lower():
            ev = [v.ctx.evidence.quote(a, b, "Oficjalna nazwa firmy w materiale")]
            return passed(f"Materiał zawiera nazwę firmy zgodną z rejestrem KNF: „{entry['name']}”.", 0.9, ev)
    if not is_promotional(v):
        return not_applicable(
            "Materiał nie ma charakteru promocyjnego, więc nie musi identyfikować firmy inwestycyjnej."
        )
    if ent.firm_mentions:
        a, b = ent.firm_mentions[0]
        ev = [v.ctx.evidence.quote(a, b, "Wzmianka o firmie (bez pełnej nazwy)")]
        return failed(
            f"W materiale pada tylko nazwa handlowa „{v.page.text[a:b]}”, bez pełnej oficjalnej nazwy "
            "firmy inwestycyjnej (z formą prawną).",
            0.7,
            ev,
        )
    return failed(
        "Materiał promuje usługę lub produkt inwestycyjny, ale nie wskazuje nazwy firmy "
        "inwestycyjnej, która za nim stoi.",
        0.65,
    )


@rule("2", "Oznaczenie reklamy", "art. 24 ust. 3 MiFID II")
def ad_marking(v: RuleView) -> RuleOutcome:
    f = v.facts
    if not is_promotional(v):
        return not_applicable("Materiał nie ma cech przekazu reklamowego lub promocyjnego.")
    open_markers = [h for h in f.ad_markers if not v.is_concealed(h)]
    if open_markers:
        h = open_markers[0]
        ev = [v.ctx.evidence.quote(h.start, h.end, "Oznaczenie materiału reklamowego")]
        marker = v.page.text[h.start : h.end]
        if all(m.sentence.text.count("#") >= 4 and v.page.text[m.start] == "#" for m in open_markers):
            return passed(
                f"Oznaczenie reklamy („{marker}”) występuje tylko wśród wielu hasztagów, więc jest mało "
                "widoczne; jednoznaczność wymaga oceny analityka.",
                0.4,
                ev,
            )
        conf = 0.7 if v.is_low_visibility(h) else 0.9
        return passed(f"Materiał jest oznaczony jako reklamowy („{marker}”).", conf, ev)
    if f.ad_markers:
        h = f.ad_markers[0]
        ev = [v.ctx.evidence.quote(h.start, h.end, "Oznaczenie widoczne dopiero po rozwinięciu")]
        return failed(
            "Oznaczenie reklamy znajduje się wyłącznie w ukrytej lub zwiniętej części materiału, "
            "więc nie jest jednoznaczne.",
            0.75,
            ev,
        )
    denial = f.ad_negations or f.independence
    if denial:
        ev = [v.ctx.quote(denial[0], label="Przedstawienie materiału jako niezależnego")]
        return failed(
            "Materiał ma charakter promocyjny, nie jest oznaczony jako reklama, a dodatkowo "
            "przedstawia się jako treść niezależna.",
            0.9,
            ev,
        )
    promo = f.profit_claims or f.cta
    ev = [v.ctx.quote(promo[0], label="Treść o charakterze promocyjnym")] if promo else []
    return failed(
        "Materiał ma charakter promocyjny, ale nie zawiera jednoznacznego oznaczenia "
        "(np. „reklama”, „materiał promocyjny”, „współpraca płatna”).",
        0.8,
        ev,
    )
