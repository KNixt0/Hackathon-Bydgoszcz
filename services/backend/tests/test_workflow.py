"""Case workflow, audit log, thresholds, calibration labels and the warning-list request (contract v3)."""

from __future__ import annotations

import pytest

from app.config import get_settings
from tests.conftest import ANALYST, SUPERVISOR, events_named
from tests.test_pipeline import ARTICLE, scan

ALLOWED = [
    ("new", "in_review"),
    ("in_review", "escalation_requested"),
    ("in_review", "resolved"),
    ("in_review", "false_positive"),
    ("escalation_requested", "escalated"),
    ("escalation_requested", "in_review"),
    ("escalated", "resolved"),
    ("escalated", "false_positive"),
    # contract v4: follow-up after an intervention
    ("in_review", "awaiting_correction"),
    ("escalated", "awaiting_correction"),
    ("awaiting_correction", "resolved"),
    ("awaiting_correction", "in_review"),
    ("awaiting_correction", "escalation_requested"),
]
# shortest route from "new" to each status
ROUTE = {
    "new": [],
    "in_review": ["in_review"],
    "escalation_requested": ["in_review", "escalation_requested"],
    "escalated": ["in_review", "escalation_requested", "escalated"],
    "awaiting_correction": ["in_review", "awaiting_correction"],
    "resolved": ["in_review", "resolved"],
    "false_positive": ["in_review", "false_positive"],
}
STATUSES = list(ROUTE)


@pytest.fixture
def cases(client):
    """id of the red Module 3 sample (violation) and of the green Module 1 sample (ok)."""
    client.post("/api/samples/import", json={"path": None})
    items = client.get("/api/incidents").json()["items"]
    red = next(i for i in items if i["source"]["platform"] == "instagram")
    green = next(i for i in items if i["source"]["platform"] == "youtube")
    return {"red": red["id"], "green": green["id"]}


def move(client, incident_id, to, **extra):
    return client.post(f"/api/incidents/{incident_id}/transition", json={"to": to, **extra})


def drive(client, incident_id, status):
    for step in ROUTE[status]:
        body = {"reason": "uzasadnienie"} if step in ("resolved", "false_positive", "awaiting_correction") else {}
        response = move(client, incident_id, step, **body)
        assert response.status_code == 200, (step, response.text)


def fresh_case(client):
    client.world.pages["https://promo.example/oferta"] = ARTICLE
    from tests.test_pipeline import job

    return job(client, scan(client, module_hint=3))["incident_id"]


@pytest.mark.parametrize(("start", "target"), ALLOWED)
def test_every_allowed_transition(client, start, target):
    incident_id = fresh_case(client)
    drive(client, incident_id, start)
    needs_reason = ("resolved", "false_positive", "awaiting_correction")
    body = {"reason": "Potwierdzone w materiale"} if target in needs_reason else {}
    response = move(client, incident_id, target, **body)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == target
    assert events_named(client, "incident:updated")[-1]["status"] == target


@pytest.mark.parametrize(
    ("start", "target"),
    [(s, t) for s in STATUSES for t in STATUSES if (s, t) not in ALLOWED],
)
def test_forbidden_transitions_are_409(client, start, target):
    incident_id = fresh_case(client)
    drive(client, incident_id, start)
    response = move(client, incident_id, target, reason="x")
    assert response.status_code == 409, (start, target, response.text)
    assert client.get(f"/api/incidents/{incident_id}").json()["status"] == start


def test_only_a_supervisor_approves_an_escalation(client, analyst, cases):
    drive(analyst, cases["red"], "escalation_requested")
    denied = move(analyst, cases["red"], "escalated")
    assert denied.status_code == 403 and denied.json() == {
        "detail": "only a supervisor can approve an escalation"
    }
    approved = move(client, cases["red"], "escalated")
    assert approved.status_code == 200 and approved.json()["status"] == "escalated"
    # an analyst may withdraw a request, and close an approved escalation
    assert move(analyst, cases["red"], "resolved", reason="Wpis na listę").status_code == 200


def test_reasons_are_required_to_close(client, cases):
    drive(client, cases["red"], "in_review")
    for body in ({}, {"reason": ""}, {"reason": "   "}):
        response = move(client, cases["red"], "resolved", **body)
        assert response.status_code == 422 and "reason" in response.json()["detail"]
        assert move(client, cases["red"], "false_positive", **body).status_code == 422
    assert move(client, cases["red"], "resolved", reason="x" * 2001).status_code == 422
    assert client.get(f"/api/incidents/{cases['red']}").json()["status"] == "in_review"


def test_payload_must_match_the_transition(client, cases):
    drive(client, cases["red"], "in_review")
    for body in (
        {"to": "escalation_requested", "resolution_action": "evidence_report"},
        {"to": "resolved", "reason": "x", "escalation_path": "THIRD_PARTY_AUDIT"},
        {"to": "resolved", "reason": "x", "resolution_action": "false_positive"},
        {"to": "false_positive", "reason": "x", "resolution_action": "content_removed"},
        {"to": "escalation_requested", "escalation_path": "NOWHERE"},
        {"to": "bogus"},
        {"to": "resolved", "reason": "x", "extra": 1},
    ):
        assert client.post(f"/api/incidents/{cases['red']}/transition", json=body).status_code == 422, body


def test_workflow_shape_defaults_and_escalation_path(client, analyst, cases):
    incident = client.get(f"/api/incidents/{cases['red']}").json()
    assert incident["workflow"] == {
        "assigned_to": None,
        "escalation_path": None,
        "resolution_action": None,
        "resolution_note": "",
        "label": "unlabeled",
    }
    summary = next(i for i in client.get("/api/incidents").json()["items"] if i["id"] == cases["red"])
    assert summary["workflow"] == {"assigned_to": None, "label": "unlabeled"}

    started = move(analyst, cases["red"], "in_review").json()
    assert started["workflow"]["assigned_to"] == ANALYST[0]  # starting the review takes the case
    requested = move(analyst, cases["red"], "escalation_requested").json()
    assert requested["workflow"]["escalation_path"] == "UNLICENSED_ACTIVITY"  # Module 3 default
    approved = move(client, cases["red"], "escalated", escalation_path="RISK_INFORMATION").json()
    assert approved["workflow"]["escalation_path"] == "RISK_INFORMATION"

    drive(client, cases["green"], "escalation_requested")
    assert (
        client.get(f"/api/incidents/{cases['green']}").json()["workflow"]["escalation_path"]
        == "THIRD_PARTY_ADVERTISING"
    )
    back = move(client, cases["green"], "in_review", reason="Brak podstaw").json()
    assert back["status"] == "in_review" and back["workflow"]["escalation_path"] is None


def test_assign_and_label(client, analyst, cases):
    assigned = analyst.post(f"/api/incidents/{cases['red']}/assign")
    assert assigned.status_code == 200 and assigned.json()["workflow"]["assigned_to"] == ANALYST[0]
    taken = client.post(f"/api/incidents/{cases['red']}/assign").json()
    assert taken["workflow"]["assigned_to"] == SUPERVISOR[0]
    labelled = analyst.post(f"/api/incidents/{cases['red']}/label", json={"label": "true_positive"})
    assert labelled.status_code == 200 and labelled.json()["workflow"]["label"] == "true_positive"
    assert analyst.post(f"/api/incidents/{cases['red']}/label", json={"label": "maybe"}).status_code == 422
    assert analyst.post("/api/incidents/nope/assign").status_code == 404
    assert len(events_named(client, "incident:updated")) == 3
    drive(client, cases["green"], "false_positive")
    assert client.post(f"/api/incidents/{cases['green']}/assign").status_code == 409  # closed


def test_false_positive_sets_label_and_resolution(client, cases):
    drive(client, cases["red"], "in_review")
    closed = move(client, cases["red"], "false_positive", reason="Materiał edukacyjny").json()
    assert closed["workflow"]["label"] == "false_positive"
    assert closed["workflow"]["resolution_action"] == "false_positive"
    assert closed["workflow"]["resolution_note"] == "Materiał edukacyjny"


def test_resolved_defaults_to_an_evidence_report(client, cases):
    drive(client, cases["red"], "in_review")
    closed = move(client, cases["red"], "resolved", reason="Naruszenie").json()
    assert closed["workflow"]["resolution_action"] == "evidence_report"
    assert closed["workflow"]["label"] == "unlabeled"


def test_intervention_follow_up_watches_the_url_and_records_the_outcome(client, cases):
    """Contract v4: after an intervention the source is re-checked every 6 h until the case is closed."""
    from datetime import timedelta

    from app.db import session_scope
    from app.models import WatchlistItem, utcnow
    from app.tasks import enqueue_rescan

    drive(client, cases["red"], "in_review")
    assert move(client, cases["red"], "awaiting_correction").status_code == 422  # what was done is required
    moved = move(client, cases["red"], "awaiting_correction", reason="Pismo do podmiotu z 21.11", follow_up_days=7)
    assert moved.status_code == 200
    body = moved.json()
    assert body["status"] == "awaiting_correction"
    assert body["follow_up"]["note"] == "Pismo do podmiotu z 21.11" and body["follow_up"]["outcome"] is None
    url = body["source"]["url"]
    assert [i["url"] for i in client.get("/api/watchlist").json()["items"]] == [url]
    with session_scope() as db:
        assert db.query(WatchlistItem).one().interval_hours == 6

    before = client.get("/api/incidents").json()["total"]
    assert len(enqueue_rescan()) == 1  # the sample is fetched again from its fixture
    assert client.get("/api/scans").json()["items"][0]["state"] == "done"
    assert client.get("/api/incidents").json()["total"] == before  # the same case, not a new one
    after = client.get(f"/api/incidents/{cases['red']}").json()
    assert after["follow_up"]["outcome"] == "persisting"  # unchanged content
    assert enqueue_rescan() == []  # too early: the interval is 6 h
    with session_scope() as db:
        item = db.query(WatchlistItem).one()
        item.last_scanned_at = utcnow() - timedelta(hours=6)
    assert len(enqueue_rescan()) == 1

    closed = move(client, cases["red"], "resolved", reason="Treść usunięta", resolution_action="content_removed")
    assert closed.status_code == 200 and closed.json()["workflow"]["resolution_action"] == "content_removed"
    assert client.get("/api/watchlist").json()["items"] == []  # the follow-up ends with the case


def test_audit_rows_have_previous_new_and_reason(client, analyst, cases):
    case = cases["red"]
    analyst.post(f"/api/incidents/{case}/assign")
    move(analyst, case, "in_review")
    move(analyst, case, "escalation_requested", reason="Doradztwo bez licencji")
    move(client, case, "escalated")
    move(client, case, "resolved", reason="Raport przekazany", resolution_action="evidence_report")
    analyst.post(f"/api/incidents/{case}/label", json={"label": "true_positive"})

    history = client.get(f"/api/incidents/{case}/history").json()["items"]
    assert [h["action"] for h in history] == [
        "assign",
        "transition",
        "transition",
        "transition",
        "transition",
        "label",
    ]
    assert set(history[0]) == {
        "id",
        "at",
        "actor_email",
        "actor_role",
        "action",
        "incident_id",
        "previous",
        "new",
        "reason",
    }
    assert history[0]["previous"] == {"assigned_to": None} and history[0]["new"] == {
        "assigned_to": ANALYST[0]
    }
    assert history[0]["actor_role"] == "ANALYST"
    req = history[2]
    assert req["previous"] == {"status": "in_review", "escalation_path": None}
    assert req["new"] == {"status": "escalation_requested", "escalation_path": "UNLICENSED_ACTIVITY"}
    assert req["reason"] == "Doradztwo bez licencji"
    assert history[3]["actor_email"] == SUPERVISOR[0] and history[3]["actor_role"] == "SUPERVISOR"
    closing = history[4]
    assert (
        closing["new"]["resolution_action"] == "evidence_report"
        and closing["reason"] == "Raport przekazany"
    )
    assert history[5]["previous"] == {"label": "unlabeled"} and history[5]["new"] == {
        "label": "true_positive"
    }
    assert analyst.get(f"/api/incidents/{case}/history").status_code == 200  # any logged-in user
    assert client.get("/api/incidents/nope/history").status_code == 404

    everything = client.get("/api/audit").json()["items"]
    assert everything[0]["action"] == "label"  # newest first
    assert {e["action"] for e in everything} >= {"login", "assign", "transition", "label"}
    only_case = client.get(f"/api/audit?incident_id={case}").json()["items"]
    assert len(only_case) == 6
    by_actor = client.get(f"/api/audit?actor={ANALYST[0].upper()}").json()["items"]
    assert by_actor and all(e["actor_email"] == ANALYST[0] for e in by_actor)
    assert len(client.get("/api/audit?limit=2").json()["items"]) == 2
    assert analyst.get("/api/audit").status_code == 403


def test_failed_transitions_write_no_audit_row(client, cases):
    move(client, cases["red"], "escalated")
    move(client, cases["red"], "resolved")
    assert client.get(f"/api/incidents/{cases['red']}/history").json() == {"items": []}


def test_audit_rows_cannot_be_changed(client, cases):
    from app.db import session_scope
    from app.models import AuditLog

    client.post(f"/api/incidents/{cases['red']}/assign")
    with pytest.raises(PermissionError), session_scope() as db:
        db.query(AuditLog).first().reason = "rewritten"
    with pytest.raises(PermissionError), session_scope() as db:
        db.delete(db.query(AuditLog).first())
    paths = {p for p in client.app.openapi()["paths"] if "audit" in p}
    assert paths == {"/api/audit"}
    assert set(client.app.openapi()["paths"]["/api/audit"]) == {"get"}


def test_exports_and_rescan_are_audited(client, cases):
    client.get(f"/api/incidents/{cases['red']}/export.csv")
    client.get("/api/incidents/export.csv")
    client.post(f"/api/incidents/{cases['red']}/rescan")
    actions = [(e["action"], e["incident_id"], e["new"]) for e in client.get("/api/audit").json()["items"]]
    assert ("export", cases["red"], {"format": "csv"}) in actions
    assert any(a == "export" and i is None and n["scope"] == "list" for a, i, n in actions)
    assert any(a == "rescan" and i == cases["red"] for a, i, _ in actions)


def test_thresholds_defaults_permissions_and_alert(client, analyst):
    assert analyst.get("/api/settings/thresholds").json() == {
        "flag": 20,
        "critical": 70,
        "updated_by": None,
        "updated_at": None,
    }
    assert analyst.put("/api/settings/thresholds", json={"flag": 30, "critical": 80}).status_code == 403
    for body in (
        {"flag": 80, "critical": 30},
        {"flag": -1, "critical": 50},
        {"flag": 10, "critical": 101},
        {},
    ):
        assert client.put("/api/settings/thresholds", json=body).status_code == 422, body
    saved = client.put("/api/settings/thresholds", json={"flag": 25, "critical": 90})
    assert saved.status_code == 200
    body = saved.json()
    assert (
        body["flag"] == 25
        and body["critical"] == 90
        and body["updated_by"] == SUPERVISOR[0]
        and body["updated_at"]
    )
    assert analyst.get("/api/settings/thresholds").json() == body
    entry = client.get("/api/audit").json()["items"][0]
    assert entry["action"] == "thresholds"
    assert entry["previous"] == {"flag": 20, "critical": 70} and entry["new"] == {"flag": 25, "critical": 90}

    # the server-side alert:high now follows `critical`: the stub scores risky text 88 < 90
    client.world.pages["https://promo.example/oferta"] = ARTICLE
    scan(client)
    assert events_named(client, "incident:new") and not events_named(client, "alert:high")
    client.put("/api/settings/thresholds", json={"flag": 25, "critical": 85})
    client.world.pages["https://promo.example/oferta2"] = ARTICLE
    scan(client, "https://promo.example/oferta2")
    assert len(events_named(client, "alert:high")) == 1


def test_calibration_includes_analyst_labels(client, analyst, cases):
    fresh = fresh_case(client)  # unlabeled live scan: not in the set
    ids = {i["id"] for i in client.get("/api/calibration").json()["items"]}
    assert fresh not in ids and ids == {cases["red"], cases["green"]}

    analyst.post(f"/api/incidents/{fresh}/label", json={"label": "true_positive"})
    analyst.post(
        f"/api/incidents/{cases['red']}/label", json={"label": "false_positive"}
    )  # overrides the sample
    items = {i["id"]: i for i in client.get("/api/calibration").json()["items"]}
    assert items[fresh]["ground_truth"] == "violation" and items[fresh]["label_source"] == "analyst"
    assert items[cases["red"]]["ground_truth"] == "ok" and items[cases["red"]]["label_source"] == "analyst"
    assert items[cases["green"]]["ground_truth"] == "ok" and items[cases["green"]]["label_source"] == "sample"
    analyst.post(f"/api/incidents/{fresh}/label", json={"label": "unlabeled"})
    assert fresh not in {i["id"] for i in client.get("/api/calibration").json()["items"]}


def test_old_statuses_are_migrated_on_start(client, cases):
    from sqlalchemy import text

    from app.db import _upgrade_data, get_engine

    with get_engine().begin() as connection:
        connection.execute(
            text("UPDATE incidents SET status = 'closed_violation' WHERE id = :i"), {"i": cases["red"]}
        )
        connection.execute(
            text("UPDATE incidents SET status = 'closed_ok' WHERE id = :i"), {"i": cases["green"]}
        )
    _upgrade_data()
    _upgrade_data()  # idempotent
    assert client.get(f"/api/incidents/{cases['red']}").json()["status"] == "resolved"
    assert client.get(f"/api/incidents/{cases['green']}").json()["status"] == "false_positive"
    assert client.get("/api/incidents?status=closed_ok").status_code == 422


def test_existing_volume_gets_workflow_columns(client, cases):
    from sqlalchemy import text

    from app.db import _add_missing_columns, get_engine

    with get_engine().begin() as connection:
        for column in ("assigned_to", "label"):
            connection.execute(text(f"DROP INDEX IF EXISTS ix_incidents_{column}"))
            connection.execute(text(f"ALTER TABLE incidents DROP COLUMN {column}"))
    _add_missing_columns()
    assert client.post(f"/api/incidents/{cases['red']}/assign").status_code == 200


def test_no_warning_list_request_document(client, cases):
    """Contract v4: the system detects and reports; it does not draft formal motions."""
    assert client.get(f"/api/incidents/{cases['red']}/warning-list-request.pdf").status_code == 404
    drive(client, cases["red"], "in_review")
    bad = move(client, cases["red"], "resolved", reason="x", resolution_action="warning_list_request")
    assert bad.status_code == 422


def test_evidence_pdf_has_decision_history(client, cases):
    from app.exports.pdf import render_html

    drive(client, cases["red"], "escalation_requested")
    incident = client.get(f"/api/incidents/{cases['red']}").json()
    history = client.get(f"/api/incidents/{cases['red']}/history").json()["items"]
    html = render_html(incident, history)
    assert "Historia decyzji" in html and "Wniosek o eskalację" in html and SUPERVISOR[0] in html
    assert "Brak decyzji w sprawie." in render_html(incident)


def test_pdf_endpoints_render_and_audit(client, cases):
    from app.scraper.browser import BrowserUnavailable, html_to_pdf

    try:
        html_to_pdf("<p>x</p>")
    except BrowserUnavailable:
        pytest.skip("Chromium not installed")
    for path in ("export.pdf", "warning-list-request.pdf"):
        response = client.get(f"/api/incidents/{cases['red']}/{path}")
        assert response.status_code == 200 and response.content.startswith(b"%PDF-"), path
    documents = [
        e["new"].get("document") for e in client.get("/api/audit").json()["items"] if e["action"] == "export"
    ]
    assert set(documents) == {"evidence_package", "warning_list_request"}


def test_internal_callers_need_no_session(client, samples_dir):
    """Seed, workers and the scheduler call the pipeline directly, never through HTTP auth."""
    from app.seed import seed_if_empty
    from app.tasks import enqueue_rescan

    assert len(seed_if_empty()) == 4
    assert enqueue_rescan() == []
    assert client.get("/api/incidents").json()["total"] == 4
    assert get_settings().demo_login is True
