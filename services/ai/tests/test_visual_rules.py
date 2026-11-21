"""Rules 4-8 and 13 decided from browser measurements (`document.visual`, contract v3).

`tests/fixtures/visual/*.json` are measurements recorded by the backend scraper
(app/scraper/visual_audit.py) on the sample HTML files; the synthetic cases below pin the
thresholds in app/rules/settings.py.
"""

from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import pytest
from run_eval import load_sample

from app.rules import VISUAL_RULES
from app.rules import settings as S
from app.schemas import AnalyzeRequest

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT.parent.parent.parent / "samples"
RECORDED = ROOT / "fixtures" / "visual"


def recorded(stem: str) -> dict:
    visual = json.loads((RECORDED / f"{stem}.json").read_text(encoding="utf-8"))
    for vp in visual["viewports"]:
        vp["screenshot_key"] = f"evidence/test/screenshot-{vp['name']}.png"
    return visual


def run(engine, body: dict):
    request = AnalyzeRequest.model_validate(body)
    return asyncio.run(engine.analyze(request.document, request.context))


def sample_body(stem: str, visual: dict | None = None) -> dict:
    path = next(p for d in ("cases", "eval") for p in (SAMPLES / d).glob(f"{stem}.json"))
    body = load_sample(path)
    if visual is not None:
        body["document"]["visual"] = visual
        body["document"]["archive"] = {
            "html_key": "evidence/test/page.html",
            "screenshot_key": "evidence/test/screenshot-desktop.png",
            "screenshots": {n: f"evidence/test/screenshot-{n}.png" for n in ("desktop", "tablet", "mobile")},
        }
    return body


def rule(analysis, rule_id: str):
    return next(r for r in analysis.rules if r.id == rule_id)


def bbox_evidence(analysis, rule_id: str):
    by_id = {e.id: e for e in analysis.evidence}
    return [by_id[i] for i in rule(analysis, rule_id).evidence_ids if by_id[i].bbox is not None]


# ------------------------------------------------------------------ recorded measurements


def test_case2_fails_4_6_7_by_measurement_and_stays_orange(engine):
    a = run(engine, sample_body("case2-kormoran-niezalezna-recenzja", recorded("case2-kormoran-niezalezna-recenzja")))
    for rid in ("4", "6", "7"):
        r = rule(a, rid)
        assert r.status == "fail" and r.method == "rendered" and 0.5 <= r.score <= 1.0, rid
        ev = bbox_evidence(a, rid)
        assert ev and ev[0].storage_key == f"evidence/test/screenshot-{ev[0].bbox.viewport}.png"
        assert ev[0].quote in a.source.text and ev[0].bbox.w > 0 and ev[0].bbox.h > 0
    assert "16 px" in rule(a, "4").explanation and "10 px" in rule(a, "4").explanation
    assert "0,62×" in rule(a, "4").explanation or "0,63×" in rule(a, "4").explanation
    assert "Nota prawna" in rule(a, "7").explanation
    assert rule(a, "5").status == "pass" and rule(a, "5").method == "rendered"
    assert a.risk_level == "orange"
    assert a.source.archive.screenshots.mobile == "evidence/test/screenshot-mobile.png"


def test_case1_passes_every_display_rule_by_measurement(engine):
    a = run(
        engine,
        sample_body("case1-bursztyn-licencjonowana-kampania", recorded("case1-bursztyn-licencjonowana-kampania")),
    )
    for rid in ("4", "5", "6", "7", "8"):
        assert rule(a, rid).status == "pass" and rule(a, rid).method == "rendered", rid
    assert a.risk_level == "green"


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("m2-vio-46-html-niski-kontrast", {"5", "6"}),
        ("m2-vio-47-html-uciete-na-telefonie", {"5", "8"}),
        ("m2-vio-48-html-dominujacy-wynik", {"13"}),
        ("m2-ok-45-html-czytelne-ostrzezenie", set()),
    ],
)
def test_focused_fixtures_fail_only_by_measurement(engine, stem, expected):
    static = run(engine, sample_body(stem))
    measured = run(engine, sample_body(stem, recorded(stem)))
    rendered_fails = {r.id for r in measured.rules if r.status == "fail" and r.method == "rendered"}
    assert rendered_fails == expected
    # the source-code analysis alone cannot see these problems (that is why the page is rendered)
    assert not {r.id for r in static.rules if r.status == "fail"} & expected
    if expected:
        assert measured.risk_score > static.risk_score


def test_dominance_explains_measured_numbers(engine):
    a = run(engine, sample_body("m2-vio-48-html-dominujacy-wynik", recorded("m2-vio-48-html-dominujacy-wynik")))
    r = rule(a, "13")
    assert "największym tekstem" in r.explanation and "16 px" in r.explanation
    assert bbox_evidence(a, "13")


# ------------------------------------------------------------------ synthetic thresholds

HTML = (
    '<html lang="pl"><head><meta name="viewport" content="width=device-width"></head><body>'
    "<p>Dom Maklerski Bursztyn Przykładowy S.A. oferuje rachunek maklerski. Możliwy zysk zależy od rynku.</p>"
    "<p>Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanych środków.</p>"
    "<p>Tabela opłat jest dostępna na stronie.</p></body></html>"
)
WARNING = "Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanych środków."


def element(**over) -> dict:
    base = {
        "text": WARNING,
        "font_px": 16,
        "ratio_to_dominant": 1.0,
        "color": "rgb(17, 17, 17)",
        "background": "rgb(255, 255, 255)",
        "contrast": 18.9,
        "opacity": 1,
        "visible": True,
        "occluded": False,
        "placement": "body",
        "requires_interaction": None,
        "bbox": {"viewport": "desktop", "x": 10, "y": 100, "w": 600, "h": 20},
        "by_viewport": {
            n: {
                "font_px": 16,
                "visible": True,
                "clipped": False,
                "bbox": {"viewport": n, "x": 10, "y": 100, "w": 300, "h": 40},
            }
            for n in ("desktop", "tablet", "mobile")
        },
    }
    for key, value in over.items():
        base[key] = value
    return base


def visual(elements: list[dict], dominant: float = 16, **vp_over) -> dict:
    viewports = []
    for name, w, h in (("desktop", 1920, 1080), ("tablet", 768, 1024), ("mobile", 390, 844)):
        vp = {"name": name, "width": w, "height": h, "page_height": h, "screenshot_key": f"k/{name}.png",
              "overflow_x": False, "clipped_texts": [], "min_risk_font_px": 16}  # fmt: skip
        vp.update(vp_over.get(name, {}))
        viewports.append(vp)
    return {"dominant_font_px": dominant, "max_font_px": 32, "viewports": viewports, "risk_elements": elements,
            "performance_blocks": []}  # fmt: skip


def analyze_visual(engine, vis: dict | None, html: str = HTML):
    body = {
        "document": {"url": "https://bursztyn-przykladowy.example/x", "platform": "web", "fetched_at": "2026-11-21T12:00:00Z",
                     "html": html, "text": "", "visual": vis},
        "context": {"module_hint": 2},
    }  # fmt: skip
    return run(engine, body)


@pytest.mark.parametrize(
    ("font", "status"),
    [(16 * S.RENDERED_FONT_RATIO_MIN, "pass"), (16 * S.RENDERED_FONT_RATIO_MIN - 0.5, "fail")],
)
def test_rule4_ratio_threshold(engine, font, status):
    a = analyze_visual(engine, visual([element(font_px=font)]))
    assert rule(a, "4").status == status and rule(a, "4").method == "rendered"


def test_rule4_absolute_floor(engine):
    a = analyze_visual(engine, visual([element(font_px=11)], dominant=13))  # 0.85x, but under 12 px
    assert rule(a, "4").status == "fail" and "11 px" in rule(a, "4").explanation


@pytest.mark.parametrize(("contrast", "status"), [(4.6, "pass"), (4.4, "fail")])
def test_rule5_wcag_threshold(engine, contrast, status):
    a = analyze_visual(engine, visual([element(contrast=contrast)]))
    assert rule(a, "5").status == status
    if status == "fail":
        assert "4,4:1" in rule(a, "5").explanation


def test_rule5_occlusion_and_opacity(engine):
    assert rule(analyze_visual(engine, visual([element(occluded=True)])), "5").status == "fail"
    assert rule(analyze_visual(engine, visual([element(opacity=0.4)])), "5").status == "fail"


@pytest.mark.parametrize("placement", ["footer", "footnote", "legal_section"])
def test_rule6_only_warning_tucked_away(engine, placement):
    a = analyze_visual(engine, visual([element(placement=placement)]))
    assert rule(a, "6").status == "fail" and rule(a, "6").method == "rendered"


@pytest.mark.parametrize("kind", ["details", "accordion", "tooltip", "modal", "link"])
def test_rule7_needs_interaction(engine, kind):
    a = analyze_visual(engine, visual([element(requires_interaction=kind, visible=kind == "link")]))
    assert rule(a, "7").status == "fail" and rule(a, "7").method == "rendered"


def test_rule8_small_on_mobile_clipped_or_overflow(engine):
    small = element()
    small["by_viewport"]["mobile"]["font_px"] = S.RESPONSIVE_FONT_MIN_PX - 1
    a = analyze_visual(engine, visual([small]))
    assert rule(a, "8").status == "fail" and "telefon" in rule(a, "8").explanation
    assert bbox_evidence(a, "8")[0].bbox.viewport == "mobile"
    clipped = element()
    clipped["by_viewport"]["tablet"]["clipped"] = True
    assert rule(analyze_visual(engine, visual([clipped])), "8").status == "fail"
    overflow = analyze_visual(engine, visual([element()], mobile={"overflow_x": True, "scroll_width": 980}))
    assert rule(overflow, "8").status == "fail" and "980 px" in rule(overflow, "8").explanation
    assert rule(analyze_visual(engine, visual([element()])), "8").status == "pass"


def test_rule13_area_share(engine):
    html = (
        "<html><body><p>Stopa zwrotu funduszu w 2025 roku wyniosła 9%.</p>"
        "<p>Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanych środków.</p></body></html>"
    )
    vis = visual([element()])
    block = {"text": "Stopa zwrotu funduszu w 2025 roku wyniosła 9%.", "font_px": 20, "area_share": S.HISTORY_AREA_SHARE_MAX,
             "bbox": {"viewport": "desktop", "x": 0, "y": 0, "w": 1900, "h": 500}}  # fmt: skip
    vis["performance_blocks"] = [block]
    assert rule(analyze_visual(engine, vis, html), "13").status == "fail"
    vis = copy.deepcopy(vis)
    vis["performance_blocks"][0]["area_share"] = 0.05
    r = rule(analyze_visual(engine, vis, html), "13")
    assert r.status == "pass" and r.method == "rendered"


# ------------------------------------------------------------------ invariant 5, method, score


def test_without_visual_no_rule_is_rendered(engine):
    a = analyze_visual(engine, None)
    assert all(r.method != "rendered" for r in a.rules)
    assert {r.method for r in a.rules if r.id in VISUAL_RULES and r.status != "na"} <= {"static"}
    assert all(r.method == "text" for r in a.rules if r.id not in VISUAL_RULES)
    assert all(0 <= r.score <= 1 for r in a.rules)


def test_unmatched_candidate_falls_back_to_static(engine):
    # the scraper's keyword list matched "bez ryzyka", which is a safety claim, not risk information
    a = analyze_visual(engine, visual([element(text="Zero ryzyka, pełne bezpieczeństwo!", font_px=8)]))
    assert all(r.method != "rendered" for r in a.rules)


def test_text_only_document_uses_text_method(engine):
    body = {
        "document": {"url": "https://x.example/p", "platform": "x", "fetched_at": "2026-11-21T12:00:00Z",
                     "text": "Gwarantowany zysk 20% rocznie! Inwestowanie wiąże się z ryzykiem."},
        "context": {},
    }  # fmt: skip
    a = run(engine, body)
    assert all(r.method in {"text", "static"} for r in a.rules)
    assert rule(a, "3").method == "text"


def test_score_tracks_status(engine):
    a = run(engine, sample_body("case2-kormoran-niezalezna-recenzja", recorded("case2-kormoran-niezalezna-recenzja")))
    for r in a.rules:
        if r.status == "fail":
            assert r.score >= 0.5
        elif r.status == "na":
            assert r.score == 0


# ------------------------------------------------------------------ source fields (contract v3)


def test_source_echoes_redirects_and_omits_absent_fields(engine):
    body = sample_body("case1-bursztyn-licencjonowana-kampania")
    plain = run(engine, body).model_dump()
    assert "final_url" not in plain["source"] and "screenshots" not in plain["source"]["archive"]
    assert "bbox" not in json.dumps(plain["evidence"])
    body["document"].update(
        final_url="https://bursztyn-przykladowy.example/konto?ref=abc",
        redirect_chain=["https://sho.rt/x", "https://bursztyn-przykladowy.example/konto?ref=abc"],
        affiliate_params=["ref=abc"],
    )
    src = run(engine, body).model_dump()["source"]
    assert (
        src["final_url"].endswith("ref=abc")
        and len(src["redirect_chain"]) == 2
        and src["affiliate_params"] == ["ref=abc"]
    )
