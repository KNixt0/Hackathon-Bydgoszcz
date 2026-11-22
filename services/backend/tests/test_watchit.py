"""WatchIt requirements: processing time, calibration history, remit, no public reports, chart ranges."""

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
