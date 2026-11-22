"""Contract v4: detection vs publication vs later checks; follow-up after an intervention."""

from __future__ import annotations

from tests.conftest import GREEN_HTML, events_named
from tests.test_pipeline import ARTICLE, URL, job, scan
from tests.test_workflow import move


def detected_case(client) -> dict:
    client.world.pages[URL] = ARTICLE
    case_id = job(client, scan(client))["incident_id"]
    return client.get(f"/api/incidents/{case_id}").json()


def test_detection_is_frozen_when_the_page_is_corrected(client):
    case = detected_case(client)
    assert case["observation"]["evidence_version_id"] is not None
    assert case["observation"]["content_state"] == "online"
    quotes = [e for e in case["evidence"] if e["kind"] == "quote"]

    client.world.pages[URL] = GREEN_HTML  # the advertiser corrects the page
    assert job(client, scan(client))["incident_id"] == case["id"]
    after = client.get(f"/api/incidents/{case['id']}").json()
    # the case still documents what was detected: score, quotes, archive keys
    assert after["risk_score"] == case["risk_score"]
    assert [e for e in after["evidence"] if e["kind"] == "quote"] == quotes
    assert after["source"]["archive"] == case["source"]["archive"]
    assert after["observation"]["content_state"] == "changed"

    versions = client.get(f"/api/incidents/{case['id']}/versions").json()["items"]
    assert [v["is_evidence"] for v in versions] == [False, True]
    assert versions[0]["risk_score"] < case["risk_score"] and versions[0]["has_snapshot"] is True
    newest = client.get(f"/api/incidents/{case['id']}/versions/{versions[0]['id']}").json()
    assert newest["is_evidence"] is False and newest["analysis"]["risk_score"] == versions[0]["risk_score"]
    evidence = client.get(f"/api/incidents/{case['id']}/versions/{versions[1]['id']}").json()
    assert evidence["is_evidence"] is True and evidence["analysis"]["risk_score"] == case["risk_score"]
    assert client.get(f"/api/incidents/{case['id']}/versions/999999").status_code == 404


def test_removed_page_is_an_observation_not_a_failed_scan(client):
    case = detected_case(client)
    move(client, case["id"], "in_review")
    move(
        client,
        case["id"],
        "awaiting_correction",
        reason="Wezwanie wysłane przez departament",
        follow_up_days=3,
    )

    del client.world.pages[URL]  # the page now answers 404
    finished = job(client, scan(client))
    assert finished["state"] == "done" and finished["incident_id"] == case["id"]
    after = client.get(f"/api/incidents/{case['id']}").json()
    assert after["observation"]["content_state"] == "removed"
    assert after["follow_up"]["outcome"] == "removed"
    assert after["risk_score"] == case["risk_score"]  # evidence intact
    newest = client.get(f"/api/incidents/{case['id']}/versions").json()["items"][0]
    assert newest["outcome"] == "removed" and newest["http_status"] == 404
    assert events_named(client, "incident:updated")[-1]["content_state"] == "removed"


def test_unknown_url_answering_404_still_fails(client):
    failed = job(client, scan(client, "https://promo.example/missing"))
    assert failed["state"] == "failed" and failed["incident_id"] is None


def test_follow_up_records_a_corrected_page(client):
    case = detected_case(client)
    move(client, case["id"], "in_review")
    move(client, case["id"], "awaiting_correction", reason="Pismo do podmiotu")
    client.world.pages[URL] = GREEN_HTML
    job(client, scan(client))
    after = client.get(f"/api/incidents/{case['id']}").json()
    assert after["follow_up"]["outcome"] == "corrected" and after["status"] == "awaiting_correction"


def test_recurrence_after_closure_opens_a_linked_case(client):
    client.world.pages[URL] = GREEN_HTML
    first = job(client, scan(client))["incident_id"]
    client.world.pages[URL] = ARTICLE
    assert job(client, scan(client))["incident_id"] == first  # first flagged observation = detection
    move(client, first, "in_review")
    move(client, first, "resolved", reason="Podmiot poprawił materiał", resolution_action="content_corrected")

    client.world.pages[URL] = ARTICLE.replace("Nowa oferta", "Znowu nowa oferta")  # violating content again
    second = job(client, scan(client))["incident_id"]
    assert second != first
    new_case = client.get(f"/api/incidents/{second}").json()
    assert new_case["previous_incident_id"] == first and new_case["status"] == "new"
    assert client.get(f"/api/incidents/{first}").json()["status"] == "resolved"


def test_old_escalation_paths_are_renamed_on_start(client):
    from app.db import _upgrade_data, session_scope
    from app.models import Incident

    case = detected_case(client)
    with session_scope() as db:
        db.get(Incident, case["id"]).escalation_path = "LEGAL_WARNING_LIST"
    _upgrade_data()
    with session_scope() as db:
        assert db.get(Incident, case["id"]).escalation_path == "UNLICENSED_ACTIVITY"


def test_cases_from_before_v4_get_their_evidence_frozen_on_start(client):
    from app.db import _upgrade_data, session_scope
    from app.models import Incident

    case = detected_case(client)
    with session_scope() as db:  # simulate a row written before contract v4
        db.get(Incident, case["id"]).evidence_version_id = None
    _upgrade_data()
    with session_scope() as db:
        row = db.get(Incident, case["id"])
        assert row.evidence_version_id is not None
        evidence = row.evidence_version_id
    _upgrade_data()  # idempotent
    with session_scope() as db:
        assert db.get(Incident, case["id"]).evidence_version_id == evidence


def test_db_session_is_closed_when_the_request_is_cancelled(client):
    """Regression (scripts/stress.py): a cancelled request must not leak its connection."""
    import asyncio
    import contextlib

    from sqlalchemy import text

    from app.db import get_db

    async def scenario() -> bool:
        gen = get_db()
        session = await gen.__anext__()
        session.execute(text("SELECT 1"))  # a transaction is open now
        assert session.in_transaction()
        with contextlib.suppress(asyncio.CancelledError):
            await gen.athrow(asyncio.CancelledError())
        return session.in_transaction()

    assert asyncio.run(scenario()) is False


def test_no_detection_before_the_system_start(monkeypatch):
    """WatchIt: the system did not exist before SYSTEM_START_DATE; demo back-dating is squeezed after it."""
    from datetime import UTC, datetime

    from app import pipeline
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "system_start_date", "2026-11-21")
    now = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(pipeline, "utcnow", lambda: now)
    start = datetime(2026, 11, 21, 19, 50, tzinfo=UTC)
    times = [pipeline.detection_time(d) for d in (0, 0.5, 1, 3, 10, 29, 400)]
    assert all(start <= t <= now for t in times)
    assert times[0] == now and times[-1] == start  # newest stays now, the oldest lands on the start
    assert times == sorted(times, reverse=True)  # older samples stay older
    assert pipeline.detection_time(None) is None and pipeline.detection_time(True) is None
