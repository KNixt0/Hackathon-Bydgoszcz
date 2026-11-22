from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.config import get_settings
from tests.conftest import GREEN_HTML, events_named

ARTICLE = """<html lang="pl"><head><title>Oferta</title></head><body>
<p>Nowa oferta inwestycyjna. Gwarantowany zysk 12% rocznie bez żadnego ryzyka dla każdego klienta.</p>
<p>Zadzwoń już dziś i zainwestuj swoje oszczędności w nasz niezawodny produkt finansowy premium.</p>
<p>Inwestycje bez ryzyka to nasza specjalność od lat, sprawdź opinie zadowolonych klientów.</p></body></html>"""
URL = "https://promo.example/oferta"


def scan(client, url=URL, **extra):
    response = client.post("/api/scans", json={"url": url, **extra})
    assert response.status_code == 202, response.text
    return response.json()["job_id"]


def job(client, job_id):
    return next(j for j in client.get("/api/scans").json()["items"] if j["id"] == job_id)


def test_happy_path_stores_incident_and_emits(client):
    client.world.pages[URL] = ARTICLE
    job_id = scan(client, module_hint=2)

    done = job(client, job_id)
    assert done["state"] == "done" and done["incident_id"] and done["finished_at"] and done["error"] is None

    # the AI got a contract-shaped Document + context
    call = client.world.ai_calls[0]
    document = call["document"]
    assert document["url"] == URL and document["platform"] == "web" and document["http_status"] == 200
    assert "Gwarantowany zysk" in document["text"] and document["html"].startswith("<html")
    assert document["language"] == "pl" and document["fetch"]["engine"] == "httpx"
    assert document["fetch"]["proxy"] is None and "Mozilla" in document["fetch"]["user_agent"]
    assert "module_hint" not in call.get("context", {})

    # raw HTML archived, key stored on the incident, readable as text/plain
    key = document["archive"]["html_key"]
    assert client.store.objects[key][0].decode() == ARTICLE
    incident = client.get(f"/api/incidents/{done['incident_id']}").json()
    assert incident["source"]["archive"]["html_key"] == key
    assert incident["status"] == "new" and incident["risk_score"] == 88.0 and len(incident["rules"]) == 19
    archived = client.get(f"/api/evidence/{key}")
    assert archived.status_code == 200 and archived.headers["content-type"].startswith("text/plain")
    assert archived.headers["x-content-type-options"] == "nosniff"

    # socket events
    states = [p["state"] for p in events_named(client, "scan:progress") if p["id"] == job_id]
    assert states == ["queued", "scraping", "analyzing", "done"]
    new = events_named(client, "incident:new")
    assert len(new) == 1 and new[0]["id"] == incident["id"]
    assert new[0]["failed_rules"] == ["6", "12a"] and new[0]["firm"] == "Żółw Capital S.A."
    assert new[0]["source"] == {"platform": "web", "url": URL}
    assert [p["id"] for p in events_named(client, "alert:high")] == [incident["id"]]


def test_low_score_has_no_alert(client):
    client.world.pages[URL] = GREEN_HTML
    scan(client)
    assert len(events_named(client, "incident:new")) == 1
    assert events_named(client, "alert:high") == []


def test_alert_threshold_is_configurable(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "alert_threshold", 10.0)
    client.world.pages[URL] = GREEN_HTML
    scan(client)
    assert len(events_named(client, "alert:high")) == 1


def test_rescan_updates_same_incident_and_keeps_versions(client):
    client.world.pages[URL] = GREEN_HTML
    first = job(client, scan(client))["incident_id"]
    client.patch(f"/api/incidents/{first}", json={"status": "in_review"})

    # unchanged content -> same incident, version marked unchanged
    assert job(client, scan(client))["incident_id"] == first
    # changed content -> still the same incident, new score, version marked changed
    client.world.pages[URL] = ARTICLE
    assert job(client, scan(client))["incident_id"] == first

    listing = client.get("/api/incidents").json()
    assert listing["total"] == 1
    assert listing["items"][0]["risk_score"] == 88.0 and listing["items"][0]["status"] == "in_review"
    versions = client.get(f"/api/incidents/{first}/versions").json()["items"]
    assert [v["changed"] for v in versions] == [True, False, False]
    assert [v["risk_score"] for v in versions] == [88.0, 12.0, 12.0]
    assert len({v["content_hash"] for v in versions}) == 2
    assert len(events_named(client, "incident:new")) == 1
    assert len([p for p in events_named(client, "incident:updated") if p["risk_score"] in (12.0, 88.0)]) == 3
    assert events_named(client, "alert:high") == []  # alerts only for new incidents


def test_fetch_failure_marks_job_failed(client):
    job_id = scan(client, "https://promo.example/missing")
    failed = job(client, job_id)
    assert failed["state"] == "failed" and "404" in failed["error"] and failed["incident_id"] is None
    assert events_named(client, "scan:progress")[-1]["state"] == "failed"
    assert client.get("/api/incidents").json()["total"] == 0


def test_ai_down_fails_without_incident(client):
    client.world.pages[URL] = ARTICLE
    client.world.ai_down = True
    failed = job(client, scan(client))
    assert failed["state"] == "failed" and "AI service unreachable" in failed["error"]


def test_ai_down_retries_then_succeeds(client, monkeypatch):
    from app.pipeline import process_job

    monkeypatch.setattr(get_settings(), "scan_max_retries", 2)
    monkeypatch.setattr("app.api.scans.dispatch", lambda job_id: None)
    client.world.pages[URL] = ARTICLE
    client.world.ai_down = True
    job_id = scan(client)
    assert process_job(job_id) == get_settings().scan_retry_backoff_seconds
    assert job(client, job_id)["state"] == "queued"
    client.world.ai_down = False
    assert process_job(job_id) is None
    assert job(client, job_id)["state"] == "done"


def test_invalid_ai_response_fails_cleanly(client):
    client.world.pages[URL] = ARTICLE
    client.world.ai_response = {"title": "x", "risk_score": 400}
    failed = job(client, scan(client))
    assert failed["state"] == "failed" and "contract" in failed["error"]


def test_redirect_to_private_address_is_blocked(client):
    client.world.pages[URL] = httpx.Response(302, headers={"location": "http://internal.test/admin"})
    failed = job(client, scan(client))
    assert failed["state"] == "failed" and "blocked" in failed["error"]
    assert not any(r.url.host == "internal.test" for r in client.world.requests)


def test_robots_disallow_is_respected(client):
    client.world.pages["https://promo.example/robots.txt"] = httpx.Response(
        200, text="User-agent: *\nDisallow: /oferta\n", headers={"content-type": "text/plain"}
    )
    client.world.pages[URL] = ARTICLE
    failed = job(client, scan(client))
    assert failed["state"] == "failed" and "robots" in failed["error"]


def test_platform_detection_and_metadata(client):
    url = "https://www.youtube.com/watch?v=abc"
    client.world.pages[url] = """<html lang="pl"><head><title>Jak zarobić - YouTube</title>
    <meta property="og:title" content="Jak zarobić"><meta property="og:description" content="Gwarantowany zysk na forex, link w opisie">
    <script type="application/ld+json">{"@type":"VideoObject","name":"Jak zarobić","uploadDate":"2026-10-30",
    "author":{"@type":"Person","name":"Finfluencer Jan","url":"https://www.youtube.com/@jan"}}</script></head><body></body></html>"""
    assert job(client, scan(client, url))["error"] is None
    document = client.world.ai_calls[0]["document"]
    assert document["platform"] == "youtube" and document["title"] == "Jak zarobić"
    assert document["published_at"] == "2026-10-30"
    assert document["author"] == {"name": "Finfluencer Jan", "url": "https://www.youtube.com/@jan"}
    assert "Gwarantowany zysk na forex" in document["text"]
    assert client.get("/api/incidents?source=youtube").json()["total"] == 1


def test_backdating_only_from_sample_meta(client):
    client.world.pages[URL] = ARTICLE
    incident_id = job(client, scan(client))["incident_id"]
    created = datetime.fromisoformat(
        client.get(f"/api/incidents/{incident_id}").json()["created_at"].replace("Z", "+00:00")
    )
    assert abs((datetime.now(UTC) - created).total_seconds()) < 60
