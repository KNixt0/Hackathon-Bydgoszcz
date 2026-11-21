"""Public reports: normalisation, counting, priority, alert:viral, limits and exports."""

from __future__ import annotations

import pytest

from app import pipeline
from app.config import get_settings
from app.exports import csv_export, pdf
from app.models import AuditLog, Incident, ScanJob, UserReport
from app.public_reports import InvalidReportURL, normalize_url, priority_score, report_throttle
from tests.conftest import events_named

RISKY = (
    "<html><head><title>Oferta</title></head><body><p>Gwarantowany zysk 30% miesięcznie.</p></body></html>"
)
CALM = "<html><head><title>Info</title></head><body><p>Rzetelna informacja o funduszu.</p></body></html>"
URL = "https://oferta.example/promo?id=7"


@pytest.fixture(autouse=True)
def _fresh_throttle():
    report_throttle.reset()
    yield
    report_throttle.reset()


def report(anon, url=URL, ip="10.0.0.1", **body):
    return anon.post("/api/public/reports", json={"url": url, **body}, headers={"X-Real-IP": ip})


def incident(client) -> dict:
    items = client.get("/api/incidents").json()["items"]
    assert len(items) == 1
    return items[0]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HTTPS://Example.COM/Path?b=2&a=1#frag", "https://example.com/Path?a=1&b=2"),
        ("https://example.com", "https://example.com/"),
        ("https://example.com:443/x", "https://example.com/x"),
        ("http://example.com:8080/x", "http://example.com:8080/x"),
        ("https://e.com/p?utm_source=a&UTM_medium=b&id=3", "https://e.com/p?id=3"),
        ("https://e.com/p?fbclid=1&gclid=2&mc_eid=3&igshid=4&id=3", "https://e.com/p?id=3"),
        ("https://youtu.be/x?si=abc&t=10", "https://youtu.be/x?t=10"),
        ("https://e.com/p?ref=jan20&v=1", "https://e.com/p?ref=jan20&v=1"),
        ("https://e.com/p?utm_source=a", "https://e.com/p"),
    ],
)
def test_normalisation(raw, expected):
    assert normalize_url(raw) == expected


def test_equivalent_urls_hash_equal():
    from app.incidents import url_hash

    a = url_hash(normalize_url("https://Example.com/p?b=2&a=1&utm_campaign=x#top"))
    b = url_hash(normalize_url("https://example.com:443/p?a=1&b=2&fbclid=9"))
    assert a == b


@pytest.mark.parametrize("raw", ["ftp://e.com/x", "javascript:alert(1)", "https://u:p@e.com/", "https:///x"])
def test_normalisation_rejects(raw):
    with pytest.raises(InvalidReportURL):
        normalize_url(raw)


def test_priority_formula():
    assert priority_score(80, 0) == 80
    assert priority_score(80, 1) == 80 * 1.25
    assert priority_score(90, 100) == 100
    assert priority_score(10, 7) == 10 * (1 + 0.25 * 3)


def test_no_login_and_validation(client, anon):
    client.world.pages[URL] = RISKY
    assert report(anon).status_code == 202
    assert report(anon, url="ftp://x.example/a", ip="10.0.0.2").status_code == 422
    assert report(anon, url="not a url", ip="10.0.0.3").status_code == 422
    assert report(anon, comment="x" * 501, ip="10.0.0.4").status_code == 422
    assert report(anon, category_hint=9, ip="10.0.0.5").status_code == 422
    assert anon.post("/api/public/reports", json={"url": URL, "extra": 1}).status_code == 422


def test_origin_check_allows_same_origin_form_post(client, anon):
    client.world.pages[URL] = RISKY
    headers = {"Origin": "http://testserver", "Host": "testserver"}
    assert anon.post("/api/public/reports", json={"url": URL}, headers=headers).status_code == 202
    bad = {"Origin": "https://evil.example"}
    assert anon.post("/api/public/reports", json={"url": URL + "2"}, headers=bad).status_code == 403


def test_new_url_is_scanned_and_report_linked(client, anon):
    client.world.pages[URL] = RISKY
    response = report(anon, url=URL + "&utm_source=x#frag", category_hint=3, comment="Podejrzane")
    assert response.status_code == 202
    assert response.json() == {"status": "accepted", "known": False}  # no ids leaked
    case = incident(client)
    assert case["user_reports_count"] == 1
    assert case["priority_score"] == priority_score(case["risk_score"], 1)
    assert client.world.ai_calls[0]["context"]["module_hint"] == 3
    with_row = client.get(f"/api/incidents/{case['id']}").json()
    assert with_row["user_reports_count"] == 1
    stored = client.get(f"/api/incidents/{case['id']}/reports").json()["items"]
    assert stored == [{"created_at": stored[0]["created_at"], "category_hint": 3, "comment": "Podejrzane"}]


def test_known_url_counts_and_emits_update(client, anon):
    client.world.pages[URL] = RISKY
    report(anon)
    before = len(events_named(client, "incident:updated"))
    response = report(anon, url="https://OFERTA.example/promo?utm_source=a&id=7", ip="10.0.0.2")
    assert response.json() == {"status": "accepted", "known": True}
    case = incident(client)
    assert case["user_reports_count"] == 2
    assert case["priority_score"] == priority_score(case["risk_score"], 2)
    updates = events_named(client, "incident:updated")
    assert len(updates) == before + 1 and updates[-1]["user_reports_count"] == 2
    assert len(client.world.ai_calls) == 1  # not scanned again


def test_audit_row_without_personal_data(client, anon):
    client.world.pages[URL] = RISKY
    report(anon)
    report(anon, ip="10.9.9.9")
    rows = client.get("/api/audit?action=public_report").json()["items"]
    assert len(rows) == 2
    assert {r["actor_email"] for r in rows} == {"public"}
    assert "10.9.9.9" not in str(rows)
    assert rows[0]["new"]["user_reports_count"] in (1, 2)


def test_viral_alert_once_on_critical_case(client, anon):
    client.world.pages[URL] = RISKY
    for n in range(1, 8):
        report(anon, ip=f"10.0.1.{n}")
        assert len(events_named(client, "alert:viral")) == (1 if n >= 5 else 0)
    viral = events_named(client, "alert:viral")[0]
    assert viral["user_reports_count"] == 5 and viral["risk_score"] >= 70


def test_no_viral_alert_on_low_risk_case(client, anon):
    client.world.pages[URL] = CALM
    for n in range(1, 8):
        report(anon, ip=f"10.0.1.{n}")
    assert incident(client)["user_reports_count"] == 7
    assert events_named(client, "alert:viral") == []


def test_repeat_from_same_reporter_is_not_counted(client, anon):
    client.world.pages[URL] = RISKY
    assert report(anon).status_code == 202
    again = report(anon, url=URL + "&fbclid=zzz")
    assert again.status_code == 202 and again.json() == {"status": "accepted", "known": True}
    assert incident(client)["user_reports_count"] == 1


def test_hourly_limit_returns_429_with_retry_after(client, anon, monkeypatch):
    monkeypatch.setattr(get_settings(), "public_reports_per_hour", 2)
    client.world.pages[URL] = RISKY
    assert report(anon, url=URL + "&a=1").status_code == 202
    assert report(anon, url=URL + "&a=2").status_code == 202
    third = report(anon, url=URL + "&a=3")
    assert third.status_code == 429 and int(third.headers["Retry-After"]) > 0
    assert report(anon, url=URL + "&a=3", ip="10.0.0.99").status_code == 202  # other reporter


def test_queue_cap(client, anon, monkeypatch):
    monkeypatch.setattr(get_settings(), "public_reports_max_queued", 1)
    monkeypatch.setattr("app.api.public.dispatch", lambda job_id: None)  # scans stay queued
    assert report(anon, url="https://a.example/1").status_code == 202
    capped = report(anon, url="https://b.example/2", ip="10.0.0.2")
    assert capped.status_code == 429 and "Retry-After" in capped.headers
    assert report(anon, url="https://a.example/1", ip="10.0.0.3").status_code == 202  # same pending scan


def test_ssrf_refused(client, anon):
    for url in (
        "http://internal.test/x",
        "http://localhost/admin",
        "http://127.0.0.1/",
        "http://mixed.test/",
    ):
        assert report(anon, url=url).status_code == 422, url
    assert client.get("/api/incidents").json()["total"] == 0


def test_pending_reports_are_linked_when_the_scan_finishes(client, anon, monkeypatch):
    jobs: list[str] = []
    monkeypatch.setattr("app.api.public.dispatch", jobs.append)
    client.world.pages[URL] = RISKY
    for n in range(1, 6):
        report(anon, ip=f"10.0.2.{n}", comment=f"zgłoszenie {n}")
    assert len(jobs) == 1  # one scan for five reports
    assert client.get("/api/incidents").json()["total"] == 0
    pipeline.process_job(jobs[0])
    case = incident(client)
    assert case["user_reports_count"] == 5
    assert len(events_named(client, "alert:viral")) == 1  # reached 5 through linking
    assert len(client.get(f"/api/incidents/{case['id']}/reports").json()["items"]) == 5
    from app.db import session_scope

    with session_scope() as db:
        assert db.query(UserReport).filter(UserReport.incident_id.is_(None)).count() == 0
        assert db.query(ScanJob).count() == 1
        assert db.query(AuditLog).filter(AuditLog.action == "public_report").count() == 1


def test_rescan_keeps_count_and_recomputes_priority(client, anon):
    client.world.pages[URL] = RISKY
    report(anon)
    case = incident(client)
    client.world.pages[URL] = CALM
    client.post(f"/api/incidents/{case['id']}/rescan")
    after = incident(client)
    assert after["user_reports_count"] == 1
    assert after["priority_score"] == priority_score(after["risk_score"], 1) != case["priority_score"]


def test_sort_and_min_reports(client, anon):
    low, high = "https://calm.example/a", "https://risky.example/b"
    client.world.pages[low], client.world.pages[high] = CALM, RISKY
    for n in range(1, 6):
        report(anon, url=low, ip=f"10.0.3.{n}")
    report(anon, url=high, ip="10.0.3.9")
    by_risk = [i["source"]["url"] for i in client.get("/api/incidents").json()["items"]]
    assert by_risk[0].startswith(high)
    assert client.get("/api/incidents?min_reports=5").json()["total"] == 1
    assert client.get("/api/incidents?sort=nope").status_code == 422
    items = client.get("/api/incidents?sort=priority").json()["items"]
    scores = [i["priority_score"] for i in items]
    assert scores == sorted(scores, reverse=True)


def test_reports_endpoint_needs_a_session(client, anon):
    client.world.pages[URL] = RISKY
    report(anon)
    case = incident(client)
    assert anon.get(f"/api/incidents/{case['id']}/reports").status_code == 401


def test_comment_is_escaped_in_exports_and_stored_as_text(client, anon):
    client.world.pages[URL] = RISKY
    report(anon, comment="<script>alert(1)</script>")
    report(anon, ip="10.0.0.2", comment='=HYPERLINK("http://evil")')
    case = client.get(f"/api/incidents/{incident(client)['id']}").json()
    reports = client.get(f"/api/incidents/{case['id']}/reports").json()["items"]
    assert any(r["comment"] == "<script>alert(1)</script>" for r in reports)
    html = pdf.render_html(case, [], reports)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    body = csv_export.incident_csv(case, reports).decode("utf-8")
    assert "'=HYPERLINK" in body
    listing = client.get("/api/incidents/export.csv").content.decode("utf-8")
    header = listing.splitlines()[0]
    assert "liczba_zgloszen" in header and "priorytet" in header


def test_existing_rows_without_counters_are_upgraded(client):
    from sqlalchemy import text

    from app.db import get_engine, init_db

    client.post("/api/samples/import")
    with get_engine().begin() as c:
        c.execute(
            text(
                "UPDATE incidents SET user_reports_count = NULL, priority_score = NULL, norm_url_hash = NULL"
            )
        )
    init_db(attempts=1, delay=0)
    from app.db import session_scope

    with session_scope() as db:
        rows = db.query(Incident).all()
        assert rows and all(r.user_reports_count == 0 and r.priority_score == r.risk_score for r in rows)
        assert all(r.norm_url_hash for r in rows)
