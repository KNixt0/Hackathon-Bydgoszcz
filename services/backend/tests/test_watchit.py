"""WatchIT requirements: processing time, calibration history, remit, no public reports, chart ranges."""

from __future__ import annotations

from tests.conftest import SUPERVISOR
from tests.test_pipeline import ARTICLE, URL, job, scan
from tests.test_workflow import move


def case_id(client) -> str:
    client.world.pages[URL] = ARTICLE
    return job(client, scan(client))["incident_id"]


def test_processing_time_starts_with_the_review_and_ends_with_the_case(client):
    cid = case_id(client)
    first = client.get(f"/api/incidents/{cid}").json()["workflow"]
    assert first["started_at"] is None and first["closed_at"] is None
    started = move(client, cid, "in_review").json()["workflow"]["started_at"]
    assert started is not None
    summary = next(i for i in client.get("/api/incidents").json()["items"] if i["id"] == cid)
    assert summary["workflow"]["started_at"] == started
    closed = move(client, cid, "resolved", reason="Potwierdzone").json()["workflow"]
    assert closed["started_at"] == started and closed["closed_at"] is not None


def test_taking_a_case_starts_the_clock(client, analyst):
    cid = case_id(client)
    assert analyst.post(f"/api/incidents/{cid}/assign").json()["workflow"]["started_at"] is not None


def test_calibration_history_records_who_changed_what(client, analyst):
    assert (
        analyst.post("/api/settings/thresholds/preview", json={"flag": 25, "critical": 75}).status_code == 204
    )
    assert (
        analyst.post("/api/settings/thresholds/preview", json={"flag": 25, "critical": 75}).status_code == 204
    )  # no repeat
    assert (
        analyst.post("/api/settings/thresholds/preview", json={"flag": 80, "critical": 70}).status_code == 422
    )
    assert client.put("/api/settings/thresholds", json={"flag": 30, "critical": 70}).status_code == 200
    items = analyst.get("/api/settings/thresholds/history").json()["items"]  # any user may read it
    assert [i["action"] for i in items] == ["thresholds", "calibration_preview"]
    assert items[0]["actor_email"] == SUPERVISOR[0] and items[0]["new"] == {"flag": 30, "critical": 70}
    assert items[1]["actor_role"] == "ANALYST" and items[1]["new"] == {"flag": 25, "critical": 75}


def test_out_of_remit_material_is_not_listed_or_counted(client):
    client.world.pages[URL] = ARTICLE.replace("Nowa oferta", "POZA_ZAKRESEM Nowa oferta")
    hidden = job(client, scan(client))["incident_id"]
    assert client.get(f"/api/incidents/{hidden}").status_code == 200  # still reachable by its link
    assert client.get("/api/incidents").json()["total"] == 0
    assert all(not day["items"] for day in client.get("/api/stats/trends").json()["days"])


def test_public_reports_are_switched_off(client, anon):
    assert anon.post("/api/public/reports", json={"url": "https://promo.example/x"}).status_code == 404
    cid = case_id(client)
    assert client.get(f"/api/incidents/{cid}/reports").status_code == 404


def test_trends_by_hour_for_the_24_hour_range(client):
    case_id(client)
    days = client.get("/api/stats/trends?hours=24").json()["days"]
    assert len(days) == 24 and days[-1]["date"].endswith(":00:00Z")
    assert sum(len(d["items"]) for d in days) == 1


def test_audit_log_filters(client, analyst):
    from datetime import UTC, datetime

    cid = case_id(client)
    move(client, cid, "in_review")
    move(client, cid, "resolved", reason="Treść usunięta po piśmie")
    analyst.post("/api/settings/thresholds/preview", json={"flag": 22, "critical": 70})
    today = datetime.now(UTC).date().isoformat()

    by_case = client.get(f"/api/audit?incident_id={cid.replace('-', '')[-8:]}").json()["items"]
    assert by_case and all(e["incident_id"] == cid for e in by_case)
    assert all(e["incident_title"] for e in by_case)
    actions = client.get("/api/audit?action=transition,calibration_preview").json()["items"]
    assert {e["action"] for e in actions} == {"transition", "calibration_preview"}
    assert {e["actor_role"] for e in client.get("/api/audit?role=ANALYST").json()["items"]} == {"ANALYST"}
    assert client.get(f"/api/audit?from={today}&to={today}").json()["items"]
    assert client.get("/api/audit?to=2000-01-01").json()["items"] == []
    found = client.get("/api/audit?q=pi%C5%9Bmie").json()["items"]
    assert [e["reason"] for e in found] == ["Treść usunięta po piśmie"]
    assert client.get("/api/audit?from=wczoraj").status_code == 422


# ── Ported from #33 (agent/KNixt0/32) ──────────────────────────────────────────────


def test_calibration_notifications_are_persistent_and_private(client, analyst):
    assert client.put("/api/settings/thresholds", json={"flag": 25, "critical": 75}).status_code == 200
    supervisor_items = client.get("/api/notifications").json()["items"]
    analyst_items = analyst.get("/api/notifications").json()["items"]
    assert len(supervisor_items) == len(analyst_items) == 1
    assert "25" in analyst_items[0]["message"] and "75" in analyst_items[0]["message"]
    supervisor_id, analyst_id = supervisor_items[0]["id"], analyst_items[0]["id"]
    assert supervisor_id != analyst_id
    assert analyst.post(f"/api/notifications/{supervisor_id}/read").status_code == 404  # not theirs
    assert analyst.post(f"/api/notifications/{analyst_id}/read").status_code == 200
    assert analyst.get("/api/notifications").json()["items"][0]["read_at"]
    assert client.get("/api/notifications").json()["items"][0]["read_at"] is None  # read state is per user
    client.put("/api/settings/thresholds", json={"flag": 25, "critical": 75})  # no change, no notification
    assert len(client.get("/api/notifications").json()["items"]) == 1


def test_notifications_need_a_session(anon):
    assert anon.get("/api/notifications").status_code == 401


def test_date_filters_reject_future_and_an_end_before_system_start(client):
    from datetime import UTC, datetime, timedelta

    case_id(client)
    bounds = client.get("/api/stats/date-bounds").json()
    earliest = datetime.fromisoformat(bounds["earliest"].replace("Z", "+00:00"))
    assert bounds["timezone"] == "Europe/Warsaw"
    before = (earliest - timedelta(days=1)).date().isoformat()
    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    for path in ("/api/incidents", "/api/audit"):
        assert client.get(path, params={"to": before}).status_code == 422
        assert client.get(path, params={"to": future}).status_code == 422
        assert client.get(path, params={"from": future}).status_code == 422
        assert "uruchomienia systemu" in client.get(path, params={"to": before}).json()["detail"]
        # a start before the system existed means "from the beginning" (the 7 / 30-day quick ranges)
        assert client.get(path, params={"from": before}).status_code == 200
    today = datetime.now(UTC).date().isoformat()
    assert client.get("/api/incidents", params={"from": earliest.date().isoformat(), "to": today}).json()[
        "items"
    ]
    assert client.get("/api/incidents", params={"from": before}).json()["items"]


def test_launch_is_exactly_2050_warsaw():
    from datetime import UTC, datetime

    from app.config import Settings

    settings = Settings(system_start_date="2026-11-21", system_start_time="20:50")
    assert settings.system_start == datetime(2026, 11, 21, 19, 50, tzinfo=UTC)


def test_custom_trends_keep_partial_first_bucket_and_exclude_outside_range(client, monkeypatch):
    from datetime import UTC, datetime

    import app.api.incidents as endpoint
    import app.date_bounds as bounds
    from app.config import get_settings
    from app.db import session_scope
    from app.models import Incident

    cid = case_id(client)
    settings = get_settings()
    monkeypatch.setattr(settings, "system_start_date", "2026-11-21")
    monkeypatch.setattr(settings, "system_start_time", "20:50")
    now = datetime(2026, 11, 22, 12, tzinfo=UTC)
    monkeypatch.setattr(endpoint, "utcnow", lambda: now)
    monkeypatch.setattr(bounds, "utcnow", lambda: now)
    with session_scope() as db:
        db.get(Incident, cid).created_at = settings.system_start
    params = {"from": "2026-11-21T19:50:00Z", "to": "2026-11-21T19:59:00Z"}
    response = client.get("/api/stats/trends", params=params)
    assert response.status_code == 200
    buckets = response.json()["days"]
    assert len(buckets) == 1 and buckets[0]["date"] == "2026-11-21T19:00:00Z"
    assert [i["id"] for i in buckets[0]["items"]] == [cid]
    params["from"] = "2026-11-21T19:51:00Z"
    assert client.get("/api/stats/trends", params=params).json()["days"][0]["items"] == []
    for params in (
        {"from": "bad"},
        {"from": "2026-11-22T11:00Z", "to": "2026-11-22T10:00Z"},
        {"to": "2026-11-21T19:49Z"},
        {"to": "2026-11-23T00:00Z"},
        {"to": "2026-11-22T12:01Z"},
    ):
        assert client.get("/api/stats/trends", params=params).status_code == 422
