"""Real Chromium: measurements of a local fixture page, offline (own origin only), within budget."""

from __future__ import annotations

import functools
import http.server
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.config import Settings
from app.scraper.visual_audit import audit_page, png_size

pytest.importorskip("playwright.sync_api")

SETTINGS = Settings(visual_audit_timeout_seconds=20)

PAGE = """<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/site.css">
<link rel="stylesheet" href="{other}/tracker.css">
<style>
 body {{ font-family: Arial, sans-serif; font-size: 16px; margin: 0 auto; max-width: 900px; padding: 16px; color: #111; background: #fff; }}
 .faint {{ color: rgba(0, 0, 0, 0.25); }}
 .wrap {{ position: relative; }}
 .cover {{ position: absolute; inset: 0; background: #fff; }}
 .box {{ height: 24px; line-height: 24px; overflow: hidden; }}
 .hero {{ font-size: 64px; font-weight: bold; min-height: 300px; }}
</style></head><body>
<p class="hero">Stopa zwrotu w 2025 roku: +31%</p>
<p>Dom Maklerski Przykład S.A. oferuje rachunek. Możliwy zysk zależy od rynku i decyzji inwestora, a opłaty są w tabeli.</p>
<p>Ten akapit ma zwykłą treść, która przeważa długością nad pozostałymi elementami strony i wyznacza czcionkę główną.</p>
<p class="tiny">Inwestowanie wiąże się z ryzykiem.</p>
<p class="faint">Możesz stracić część zainwestowanego kapitału.</p>
<div class="wrap"><p>Wartość jednostek może spadać, istnieje ryzyko straty.</p><div class="cover"></div></div>
<div class="box"><p style="margin:0">Kontrakty CFD wiążą się z dużym ryzykiem szybkiej utraty środków pieniężnych z powodu dźwigni finansowej, szczególnie na małych ekranach.</p></div>
<footer><details><summary>Nota prawna</summary><p>Inwestowanie wiąże się z ryzykiem utraty całości środków.</p></details></footer>
<p><a href="https://bursztyn-przykladowy.example/konto?ref=abc">otwórz rachunek</a></p>
</body></html>"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    hits: list[str]

    def log_message(self, *args) -> None:  # noqa: D401 - silence the test server
        pass

    def do_GET(self) -> None:
        self.hits.append(self.path)
        super().do_GET()


@pytest.fixture
def servers(tmp_path: Path) -> Iterator[tuple[str, str, list[str], list[str]]]:
    (tmp_path / "own").mkdir()
    (tmp_path / "other").mkdir()
    (tmp_path / "own" / "site.css").write_text(".tiny { font-size: 10px; }", encoding="utf-8")
    (tmp_path / "other" / "tracker.css").write_text(".tiny { font-size: 40px; }", encoding="utf-8")
    started = []
    hits: dict[str, list[str]] = {}
    for name in ("own", "other"):
        hits[name] = []
        handler = type(f"H{name}", (_Quiet,), {"hits": hits[name]})
        httpd = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(handler, directory=str(tmp_path / name))
        )
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started.append(httpd)
    own, other = (f"http://127.0.0.1:{s.server_address[1]}" for s in started)
    yield own, other, hits["own"], hits["other"]
    for s in started:
        s.shutdown()


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not _chromium_available(), reason="Chromium for Playwright is not installed")
def test_measures_fixture_page_offline(servers):
    own, other, own_hits, other_hits = servers
    started = time.perf_counter()
    result = audit_page(
        f"{own}/page.html",
        PAGE.format(other=other),
        user_agent="test",
        own_origin_only=True,
        settings=SETTINGS,
    )
    elapsed = time.perf_counter() - started
    visual = result.visual

    # offline: own-origin CSS applied, other origin never contacted, page itself never re-fetched
    assert "/site.css" in own_hits and "/page.html" not in own_hits and other_hits == []
    assert elapsed < 10 and result.duration_ms < 10_000

    assert [v["name"] for v in visual["viewports"]] == ["desktop", "tablet", "mobile"]
    assert visual["dominant_font_px"] == 16 and visual["max_font_px"] == 64
    for vp in visual["viewports"]:
        size = png_size(result.screenshots[vp["name"]])
        assert size and size[0] >= vp["width"] - 1 and size[1] == vp["screenshot_height"] <= 8000

    by_text = {e["text"][:20]: e for e in visual["risk_elements"]}
    tiny = next(e for e in visual["risk_elements"] if e["text"] == "Inwestowanie wiąże się z ryzykiem.")
    assert tiny["font_px"] == 10 and tiny["ratio_to_dominant"] == pytest.approx(0.625)
    assert tiny["visible"] and tiny["placement"] == "body" and tiny["bbox"]["viewport"] == "desktop"
    assert by_text["Możesz stracić część"]["contrast"] < 3
    assert by_text["Wartość jednostek mo"]["occluded"] is True
    hidden = next(e for e in visual["risk_elements"] if "całości środków" in e["text"])
    assert hidden["requires_interaction"] == "details" and hidden["placement"] in {"legal_section", "footer"}
    assert hidden["bbox_of"] == "control" and hidden["control_text"] == "Nota prawna"
    cfd = by_text["Kontrakty CFD wiążą "]
    assert cfd["by_viewport"]["mobile"]["clipped"] is True
    mobile = next(v for v in visual["viewports"] if v["name"] == "mobile")
    assert mobile["min_risk_font_px"] == 10 and any("Kontrakty CFD" in t for t in mobile["clipped_texts"])

    hero = visual["performance_blocks"][0]
    assert hero["font_px"] == 64 and hero["area_share"] > 0.01 and hero["bbox"]["viewport"] == "desktop"
    assert "https://bursztyn-przykladowy.example/konto?ref=abc" in result.links


@pytest.mark.skipif(not _chromium_available(), reason="Chromium for Playwright is not installed")
def test_hard_timeout_raises(servers):
    own, _, _, _ = servers
    from app.scraper.visual_audit import VisualAuditError

    with pytest.raises(VisualAuditError):
        audit_page(
            f"{own}/page.html",
            "<html><body>x</body></html>",
            user_agent="t",
            own_origin_only=True,
            settings=SETTINGS,
            timeout_s=0.001,
        )
