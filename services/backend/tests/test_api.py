from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import GREEN_HTML, events_named
from tests.test_pipeline import ARTICLE, job, scan

SUMMARY_KEYS = {
    "user_reports_count",
    "priority_score",
    "id",
    "title",
    "summary",
    "modules",
    "primary_module",
    "risk_score",
    "compliance_score",
    "risk_level",
    "status",
    "created_at",
    "updated_at",
    "synthetic",
    "ground_truth",
    "demo_case",
    "source",
    "advertiser",
    "firm",
    "failed_rules",
    "workflow",
    "in_scope",  # contract v4
    "content_state",
    "follow_up",
}


@pytest.fixture
def seeded(client, samples_dir):
    """Three incidents: the two seedable samples + one live web scan."""
    for extra in ("sub/pendrive.html", "sub/note.txt"):
        (samples_dir / extra).unlink()
    assert len(client.post("/api/samples/import", json={}).json()["job_ids"]) == 2
    client.world.pages["https://promo.example/oferta"] = ARTICLE
    scan(client, module_hint=2)
    assert client.get("/api/incidents").json()["total"] == 3
    return client


def parse_csv(response):
    assert response.content.startswith(b"\xef\xbb\xbf")
    return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))


def test_health(client):
    body = client.get("/api/health").json()
    assert body == {
        "status": "ok",
        "ai": {"reachable": True, "llm_available": True, "model": "gemma"},
        "queue": True,
        "storage": True,
    }
    client.world.ai_down = True
    assert client.get("/api/health").json()["ai"] == {
        "reachable": False,
        "llm_available": False,
        "model": None,
    }


def test_list_shape_and_order(seeded):
    body = seeded.get("/api/incidents").json()
    assert body["total"] == 3 and set(body["items"][0]) == SUMMARY_KEYS
    scores = [item["risk_score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)
    assert set(body["items"][0]["source"]) == {"platform", "url"}


def test_list_filters(seeded):
    def total(query):
        response = seeded.get(f"/api/incidents?{query}")
        assert response.status_code == 200, response.text
        return response.json()["total"]

    assert total("module=3") == 1 and total("module=2") == 1
    assert total("module=1") == 3  # stub adds module 1 findings to risky items; green has primary 1
    assert total("source=instagram") == 1 and total("source=youtube") == 1 and total("source=tiktok") == 0
    assert total("status=new") == 3 and total("status=escalated") == 0
    assert total("q=SZYBKI") == 1 and total("q=promo.example") == 1 and total("q=%25") == 0
    today = datetime.now(UTC).date()
    assert total(f"from={today.isoformat()}") == 1  # samples are back-dated 3 and 10 days
    assert total(f"to={(today - timedelta(days=5)).isoformat()}") == 1
    assert total(f"from={(today - timedelta(days=4)).isoformat()}&to={today.isoformat()}") == 2
    assert total(f"from={(today - timedelta(days=4)).isoformat()}T00:00:00Z") == 2
    assert total("module=3&source=instagram&status=new&q=zysk") == 1


@pytest.mark.parametrize(
    "query", ["module=4", "module=x", "source=myspace", "status=done", "from=yesterday", "to=2026-13-01"]
)
def test_list_filter_validation(client, query):
    response = client.get(f"/api/incidents?{query}")
    assert response.status_code == 422 and isinstance(response.json()["detail"], str)


def test_detail_patch_and_404(seeded):
    incident_id = seeded.get("/api/incidents").json()["items"][0]["id"]
    incident = seeded.get(f"/api/incidents/{incident_id}").json()
    assert incident["id"] == incident_id and incident["status"] == "new"
    assert {"rules", "evidence", "debate", "engine", "source", "entities", "created_at", "updated_at"} <= set(
        incident
    )

    patched = seeded.patch(f"/api/incidents/{incident_id}", json={"status": "in_review"})  # transition alias
    assert patched.status_code == 200 and patched.json()["status"] == "in_review"
    assert seeded.get(f"/api/incidents/{incident_id}").json()["status"] == "in_review"
    assert events_named(seeded, "incident:updated")[-1]["status"] == "in_review"
    assert seeded.patch(f"/api/incidents/{incident_id}", json={"status": "escalated"}).status_code == 409

    for body in ({"status": "bogus"}, {}, {"status": "new", "risk_score": 0}):
        bad = seeded.patch(f"/api/incidents/{incident_id}", json=body)
        assert bad.status_code == 422 and isinstance(bad.json()["detail"], str)
    for method, path in [
        ("get", "/api/incidents/nope"),
        ("get", "/api/incidents/nope/export.csv"),
        ("get", "/api/incidents/nope/export.pdf"),
        ("get", "/api/evidence/evidence/x/page.html"),
    ]:
        assert getattr(seeded, method)(path).status_code == 404
    missing = seeded.patch("/api/incidents/nope", json={"status": "new"})
    assert missing.status_code == 404 and missing.json() == {"detail": "incident not found"}


def test_trends(seeded):
    body = seeded.get("/api/stats/trends").json()
    assert len(body["days"]) == 30 and body["days"][-1]["date"] == datetime.now(UTC).date().isoformat()
    items = [item for day in body["days"] for item in day["items"]]
    assert len(items) == 3 and set(items[0]) == {"id", "risk_score", "module"}
    assert len(body["days"][-4]["items"]) == 1  # the sample detected 3 days ago
    assert sum(len(d["items"]) for d in seeded.get("/api/stats/trends?days=2").json()["days"]) == 1
    assert seeded.get("/api/stats/trends?days=0").status_code == 422


def test_calibration_only_labelled(seeded):
    items = seeded.get("/api/calibration").json()["items"]
    assert {(i["ground_truth"], i["risk_score"], i["module"]) for i in items} == {
        ("violation", 88.0, 3),
        ("ok", 12.0, 1),
    }
    assert set(items[0]) == {"id", "title", "risk_score", "ground_truth", "module", "label_source"}
    assert {i["label_source"] for i in items} == {"sample"}


def test_scan_validation_and_ssrf(client):
    for body in (
        {},
        {"url": "notaurl"},
        {"url": "ftp://example.com/x"},
        {"url": "file:///etc/passwd"},
        {"url": "https://example.com", "module_hint": 9},
        {"url": "https://example.com", "extra": 1},
        {"url": "http://127.0.0.1:8000/api/health"},
        {"url": "http://localhost/"},
        {"url": "http://10.1.2.3/"},
        {"url": "http://169.254.169.254/latest/meta-data/"},
        {"url": "http://[::1]/"},
        {"url": "http://internal.test/"},
        {"url": "http://mixed.test/"},
        {"url": "http://user:pw@example.com/"},
        {"url": "http://0x7f.1/"},
        {"url": "http://backend:9999/"},
    ):
        response = client.post("/api/scans", json=body)
        assert response.status_code == 422, body
        assert isinstance(response.json()["detail"], str)
    assert client.get("/api/scans").json() == {"items": []}
    assert client.world.requests == []


def test_scans_list_latest_50(client):
    for n in range(52):
        scan(client, f"https://promo.example/{n}")
    items = client.get("/api/scans").json()["items"]
    assert len(items) == 50
    assert set(items[0]) == {"id", "url", "state", "incident_id", "error", "created_at", "finished_at"}


def test_registries_proxy_and_offline_fallback(client):
    items = client.get("/api/registries").json()["items"]
    assert items == [
        {
            "registry": "knf_brokerage_houses",
            "label": "Domy maklerskie",
            "url": "https://www.knf.gov.pl/dm",
            "entries": 37,
            "snapshot_date": "2026-11-01",
        }
    ]
    client.world.ai_down = True
    offline = client.get("/api/registries").json()["items"]
    assert len(offline) == 5 and all(i["entries"] == 0 and i["snapshot_date"] is None for i in offline)
    assert all(i["url"].startswith("https://www.knf.gov.pl/") for i in offline)


def test_exports_csv(seeded):
    rows = parse_csv(seeded.get("/api/incidents/export.csv"))
    assert rows[0][:3] == ["id", "tytul", "risk_score"] and len(rows) == 4
    assert "Żółw Capital S.A." in rows[1]
    filtered = seeded.get("/api/incidents/export.csv?source=instagram")
    assert filtered.headers["content-type"] == "text/csv; charset=utf-8" and len(parse_csv(filtered)) == 2

    web = seeded.get("/api/incidents?source=web").json()["items"][0]
    assert web["advertiser"] == "=Anonim"
    one = parse_csv(seeded.get(f"/api/incidents/{web['id']}/export.csv"))
    assert [r[0] for r in one].count("regula") == 19 and [r[0] for r in one].count("dowod") == 2
    assert any("gwarantowany zysk" in r[7].lower() for r in one if r[0] == "dowod")
    # formula injection: the advertiser name "=Anonim" is neutralised in the list export
    listing = parse_csv(seeded.get("/api/incidents/export.csv?source=web"))
    assert "'=Anonim" in listing[1] and "=Anonim" not in listing[1]


def test_pdf_html_has_polish_labels_and_everything(seeded):
    from app.exports.pdf import render_html

    red = seeded.get("/api/incidents?source=instagram").json()["items"][0]
    html = render_html(seeded.get(f"/api/incidents/{red['id']}").json())
    for needle in (
        "Raport z wykrycia",
        "Dane syntetyczne",
        "WYSOKIE RYZYKO",
        "Macierz 19 kryteriów",
        "Żółw Capital S.A.",
        "Statusy w rejestrach",
        "nie figuruje",
        "Za naruszeniem",
        "Obietnica zysku bez ryzyka",
        "Rekomendacja",
        "Skrót treści (SHA-256)",
        red["source"]["url"],
        "stub-1",
        "Kryterium 12b",
        "art. 44 ust. 2",
        "Moduł 3",
        "Zbyt mała czcionka" if False else "Jest ostrzeżenie o ryzyku",
    ):
        assert needle in html, needle
    web = seeded.get("/api/incidents?source=web").json()["items"][0]
    assert "Dane syntetyczne" not in render_html(seeded.get(f"/api/incidents/{web['id']}").json())


def test_pdf_escapes_html(seeded):
    from app.exports.pdf import render_html

    incident = seeded.get(f"/api/incidents/{seeded.get('/api/incidents').json()['items'][0]['id']}").json()
    incident["title"] = "<script>alert(1)</script>"
    assert "<script>alert(1)" not in render_html(incident)


def test_pdf_export(seeded):
    from app.scraper.browser import BrowserUnavailable, html_to_pdf

    try:
        html_to_pdf("<p>x</p>")
    except BrowserUnavailable:
        pytest.skip("Chromium not installed")
    incident_id = seeded.get("/api/incidents").json()["items"][0]["id"]
    response = seeded.get(f"/api/incidents/{incident_id}/export.pdf")
    assert response.status_code == 200 and response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-") and len(response.content) > 5000


def test_watchlist_and_rescan(client):
    from app.tasks import enqueue_rescan

    assert client.post("/api/watchlist", json={"url": "http://127.0.0.1/"}).status_code == 422
    created = client.post("/api/watchlist", json={"url": "https://watch.example/a", "module_hint": 1})
    assert created.status_code == 201
    client.post("/api/watchlist", json={"url": "https://watch.example/a"})  # idempotent
    assert len(client.get("/api/watchlist").json()["items"]) == 1

    client.post("/api/samples/import", json={})  # synthetic samples are never re-scanned
    client.world.pages["https://promo.example/oferta"] = GREEN_HTML
    client.world.pages["https://watch.example/a"] = ARTICLE
    incident_id = job(client, scan(client))["incident_id"]

    job_ids = enqueue_rescan()
    assert len(job_ids) == 2
    assert {job(client, j)["url"] for j in job_ids} == {
        "https://promo.example/oferta",
        "https://watch.example/a",
    }
    assert client.get("/api/incidents").json()["total"] == 6
    assert len(client.get(f"/api/incidents/{incident_id}/versions").json()["items"]) == 2
    assert client.get("/api/watchlist").json()["items"][0]["last_scanned_at"]

    item_id = created.json()["id"]
    assert client.delete(f"/api/watchlist/{item_id}").status_code == 204
    assert client.delete(f"/api/watchlist/{item_id}").status_code == 404


def test_unknown_route_and_no_stack_traces(client, monkeypatch):
    assert client.get("/api/nope").json() == {"detail": "Not Found"}
    monkeypatch.setattr("app.api.scans.job_dict", lambda job: 1 / 0)
    scan(client, "https://promo.example/x")
    response = client.get("/api/scans")
    assert response.status_code == 500 and response.json() == {"detail": "internal server error"}


def test_cors_disabled_by_default(client):
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_socketio_handshake_and_origin_check(client):
    ok = client.get("/api/health")  # API still served next to the socket app
    assert ok.status_code == 200
    from fastapi.testclient import TestClient

    from app.events import origin_allowed
    from app.main import app as asgi_app

    with TestClient(asgi_app) as sock:
        sock.cookies.set("iw_session", client.cookies["iw_session"])  # Socket.IO needs the session too
        url = "/socket.io/?EIO=4&transport=polling"
        # nginx forwards Host without the published port: must still be accepted
        same = sock.get(url, headers={"Origin": "http://localhost:3000", "Host": "localhost"})
        assert same.status_code == 200 and same.text.startswith("0{")
        assert (
            sock.get(url, headers={"Origin": "https://evil.example", "Host": "localhost"}).status_code == 400
        )
    assert origin_allowed(None) and origin_allowed(
        "http://iw.example:8080", {"HTTP_X_FORWARDED_HOST": "iw.example"}
    )
    assert not origin_allowed("http://localhost.evil.example", {"HTTP_HOST": "localhost:8000"})


def test_manual_triggers(client, monkeypatch):
    client.post("/api/watchlist", json={"url": "https://watch.example/a"})
    client.world.pages["https://watch.example/a"] = ARTICLE
    response = client.post("/api/watchlist/rescan")
    assert response.status_code == 202 and len(response.json()["job_ids"]) == 1
    assert client.get("/api/incidents").json()["total"] == 1
    ran = []

    class InlineThread:
        def __init__(self, target, **_):
            self.target = target

        def start(self):
            ran.append(self.target())

    monkeypatch.setattr("app.api.scans.threading.Thread", InlineThread)
    assert client.post("/api/registries/refresh").json() == {"status": "queued"}
    assert ran and ran[0]["updated"] == [] and len(ran[0]["kept"]) == 5  # offline: snapshots kept
