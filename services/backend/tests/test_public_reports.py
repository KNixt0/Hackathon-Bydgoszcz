"""The public report feature is retired; its records do not influence current case priority."""

from app.db import session_scope
from app.models import Incident
from tests.test_pipeline import ARTICLE, job, scan


def test_public_report_endpoint_removed(client, anon):
    for browser in (client, anon):
        assert browser.post("/api/public/reports", json={"url": "https://example.com"}).status_code == 404


def test_historical_report_counts_do_not_raise_priority(client):
    client.world.pages["https://promo.example/oferta"] = ARTICLE
    result = job(client, scan(client))
    with session_scope() as db:
        row = db.get(Incident, result["incident_id"])
        row.user_reports_count = 999
        row.priority_score = 100
    summary = client.get("/api/incidents").json()["items"][0]
    assert summary["priority_score"] == summary["risk_score"]
    assert client.get(f"/api/incidents/{summary['id']}/reports").status_code == 404
    exported = client.get("/api/incidents/export.csv").content.decode("utf-8-sig")
    assert "liczba_zgloszen" not in exported and "priorytet" not in exported
