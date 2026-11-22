from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.db import session_scope
from app.jurisdiction import scope
from app.models import Incident
from tests.test_pipeline import ARTICLE, job, scan


def create_case(client):
    client.world.pages["https://promo.example/oferta"] = ARTICLE
    return job(client, scan(client))["incident_id"]


def test_calibration_notifications_are_persistent_and_private(client, analyst):
    response = client.put("/api/settings/thresholds", json={"flag": 25, "critical": 75})
    assert response.status_code == 200
    supervisor_items = client.get("/api/notifications").json()["items"]
    analyst_items = analyst.get("/api/notifications").json()["items"]
    assert len(supervisor_items) == len(analyst_items) == 1
    supervisor_id, analyst_id = supervisor_items[0]["id"], analyst_items[0]["id"]
    assert supervisor_id != analyst_id
    assert analyst.post(f"/api/notifications/{supervisor_id}/read").status_code == 404
    assert analyst.post(f"/api/notifications/{analyst_id}/read").status_code == 200
    assert analyst.get("/api/notifications").json()["items"][0]["read_at"]
    assert client.get("/api/notifications").json()["items"][0]["read_at"] is None
    client.put("/api/settings/thresholds", json={"flag": 25, "critical": 75})
    assert len(client.get("/api/notifications").json()["items"]) == 1


def test_processing_start_survives_reassignment_and_finishes(client, analyst):
    case_id = create_case(client)
    first = analyst.post(f"/api/incidents/{case_id}/assign").json()["workflow"]["processing_started_at"]
    assert first
    reassigned = client.post(f"/api/incidents/{case_id}/assign").json()
    assert reassigned["workflow"]["processing_started_at"] == first
    client.post(f"/api/incidents/{case_id}/transition", json={"to": "in_review"})
    closed = client.post(
        f"/api/incidents/{case_id}/transition", json={"to": "resolved", "reason": "Zweryfikowano"}
    ).json()
    assert closed["workflow"]["processing_started_at"] == first
    assert closed["workflow"]["processing_finished_at"]
    assert client.get(f"/api/incidents/{case_id}").json()["workflow"] == closed["workflow"]


def test_monitoring_bounds_are_automatic_and_stable(client, monkeypatch):
    initial = client.get("/api/stats/date-bounds").json()
    start = datetime.fromisoformat(initial["earliest"].replace("Z", "+00:00"))
    assert start.astimezone(ZoneInfo("Europe/Warsaw")).strftime("%H:%M") == "20:50"
    now = datetime.now(UTC)
    assert start <= now
    monkeypatch.setattr("app.monitoring.utcnow", lambda: now + timedelta(days=3))
    assert client.get("/api/stats/date-bounds").json()["earliest"] == initial["earliest"]


def test_dates_reject_before_start_and_future_and_exclude_future_rows(client):
    case_id = create_case(client)
    bounds = client.get("/api/stats/date-bounds").json()
    first = datetime.fromisoformat(bounds["earliest"].replace("Z", "+00:00"))
    for path in ("/api/incidents", "/api/stats/trends", "/api/audit"):
        assert (
            client.get(path, params={"from": (first - timedelta(minutes=1)).isoformat()}).status_code == 422
        )
        assert (
            client.get(path, params={"to": (datetime.now(UTC) + timedelta(days=1)).isoformat()}).status_code
            == 422
        )
    with session_scope() as db:
        db.get(Incident, case_id).created_at = datetime.now(UTC) + timedelta(days=1)
    assert client.get("/api/incidents").json()["items"] == []
    assert not any(day["items"] for day in client.get("/api/stats/trends?period=24h").json()["days"])


def test_chart_presets_and_audit_sorting(client):
    create_case(client)
    for period in ("24h", "7d", "30d"):
        response = client.get("/api/stats/trends", params={"period": period})
        assert response.status_code == 200
        assert sum(len(day["items"]) for day in response.json()["days"]) == 1
        assert response.json()["interval"] == ("hour" if period == "24h" else "day")
    asc = client.get("/api/audit?sort=at&order=asc").json()["items"]
    desc = client.get("/api/audit?sort=at&order=desc").json()["items"]
    assert [row["id"] for row in asc] == [row["id"] for row in reversed(desc)]
    assert client.get("/api/audit?sort=invalid").status_code == 422
    assert client.get("/api/audit?sort=details").status_code == 200


def test_foreign_entities_excluded_unless_locally_supervised_branch(client):
    payload = {"entities": {"investment_firm": {"name": "Firma", "country": "CY"}}, "registry_checks": []}
    assert scope(payload) == "outside"
    payload["registry_checks"] = [
        {"registry": "knf_foreign_branches", "subject": "Firma", "status": "listed"}
    ]
    assert scope(payload) == "uknf"
    payload["entities"]["investment_firm"]["country"] = "PL"
    payload["registry_checks"] = []
    assert scope(payload) == "uknf"
    case_id = create_case(client)
    with session_scope() as db:
        db.get(Incident, case_id).jurisdiction_scope = "outside"
    assert client.get("/api/incidents").json()["items"] == []
    assert client.get(f"/api/incidents/{case_id}").status_code == 404


def test_url_analysis_ignores_module_selection(client):
    client.world.pages["https://promo.example/oferta"] = ARTICLE
    job(client, scan(client, module_hint=3))
    assert "module_hint" not in client.world.ai_calls[-1].get("context", {})
