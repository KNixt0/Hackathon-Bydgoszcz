"""Rendered visual audit: URL helpers, pipeline hook (no browser) and Chromium measurements."""

from __future__ import annotations

import logging

import httpx

from app.scraper import visual_audit
from app.scraper.visual_audit import VisualAudit, affiliate_links, affiliate_params, png_size

URL = "https://blog.example/wpis"
FIRM_LINK = "https://bursztyn-przykladowy.example/konto?ref=blog23&utm_source=yt&lang=pl"
BLOG = f"""<html lang="pl"><head><title>Wpis</title></head><body>
<p>Od roku inwestuję przez Dom Maklerski Bursztyn Przykładowy S.A. i opisuję wrażenia z aplikacji.</p>
<p>Jeśli chcesz spróbować, <a href="{FIRM_LINK}">otwórz rachunek tutaj</a> albo <a href="/o-mnie?ref=self">o mnie</a>.</p>
<p>Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanych środków.</p></body></html>"""
PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_affiliate_params_and_links():
    assert affiliate_params(FIRM_LINK) == ["ref=blog23", "utm_source=yt"]
    assert affiliate_params("https://x.example/?q=1") == []
    links = affiliate_links(
        [FIRM_LINK, "https://blog.example/o-mnie?ref=self", "https://y.example/plain"], URL
    )
    assert links == [
        {"url": FIRM_LINK, "host": "bursztyn-przykladowy.example", "params": ["ref=blog23", "utm_source=yt"]}
    ]
    assert png_size(PNG_1x1) == (1, 1) and png_size(b"nope") is None


def scan(client, url=URL):
    response = client.post("/api/scans", json={"url": url})
    assert response.status_code == 202, response.text
    return client.world.ai_calls[-1]["document"]


def test_pipeline_records_links_and_redirects_without_a_browser(client):
    start = "https://sho.rt/abc"
    client.world.pages[start] = httpx.Response(301, headers={"location": URL})
    client.world.pages[URL] = BLOG
    document = scan(client, start)
    assert document["redirect_chain"] == [start, URL] and document["final_url"] == URL
    assert document["affiliate_params"] == ["ref=blog23", "utm_source=yt"]
    assert document["affiliate_links"][0]["host"] == "bursztyn-przykladowy.example"
    assert "visual" not in document  # tests run without Chromium (mock transport)


def fake_audit(**_kwargs) -> VisualAudit:
    vp = {
        "name": "desktop",
        "width": 1920,
        "height": 1080,
        "page_height": 1080,
        "screenshot_key": None,
        "overflow_x": False,
        "clipped_texts": [],
        "min_risk_font_px": 10,
    }
    return VisualAudit(
        visual={
            "dominant_font_px": 16,
            "viewports": [vp, {**vp, "name": "mobile", "width": 390, "height": 844}],
            "risk_elements": [],
            "performance_blocks": [],
        },  # fmt: skip
        screenshots={"desktop": PNG_1x1, "mobile": PNG_1x1},
        navigations=[URL],
        links=[FIRM_LINK],
        duration_ms=12.0,
    )


def test_pipeline_archives_one_screenshot_per_viewport(client, monkeypatch):
    monkeypatch.setattr(visual_audit, "visual_audit_available", lambda settings=None: True)
    calls = []
    monkeypatch.setattr(visual_audit, "audit_page", lambda *a, **k: calls.append((a, k)) or fake_audit())
    client.world.pages[URL] = BLOG
    document = scan(client)
    assert calls and calls[0][1]["own_origin_only"] is False
    keys = document["archive"]["screenshots"]
    assert set(keys) == {"desktop", "mobile"} and document["archive"]["screenshot_key"] == keys["desktop"]
    assert all(client.store.objects[k] == (PNG_1x1, "image/png") for k in keys.values())
    assert [vp["screenshot_key"] for vp in document["visual"]["viewports"]] == [
        keys["desktop"],
        keys["mobile"],
    ]
    served = client.get(f"/api/evidence/{keys['mobile']}")
    assert served.status_code == 200 and served.headers["content-type"] == "image/png"


def test_pipeline_continues_when_rendering_fails(client, monkeypatch, caplog):
    def boom(*_a, **_k):
        raise visual_audit.VisualAuditError("browser error: crashed")

    monkeypatch.setattr(visual_audit, "visual_audit_available", lambda settings=None: True)
    monkeypatch.setattr(visual_audit, "audit_page", boom)
    client.world.pages[URL] = BLOG
    with caplog.at_level(logging.WARNING, logger="app.scraper.visual_audit"):
        document = scan(client)
    assert "visual" not in document and document["affiliate_params"]  # links still come from the HTML
    warnings = [
        r for r in caplog.records if r.name == "app.scraper.visual_audit" and r.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    jobs = client.get("/api/scans").json()["items"]
    assert jobs[0]["state"] == "done"


def test_samples_use_material_url_not_fixture_origin(client, monkeypatch):
    monkeypatch.setattr(visual_audit, "visual_audit_available", lambda settings=None: False)
    client.post("/api/samples/import", json={"path": "green.json"})
    document = client.world.ai_calls[-1]["document"]
    assert (
        document["final_url"] == "https://www.youtube.com/watch?v=green" and "redirect_chain" not in document
    )
