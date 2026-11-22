from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.samples import UnsafePath, discover, safe_join
from tests.conftest import RED_TEXT, events_named
from tests.test_pipeline import job


def incidents(client, query=""):
    return client.get(f"/api/incidents{query}").json()["items"]


def test_discover(samples_dir):
    found = {s.path: s for s in discover()}
    assert sorted(found) == ["case3.json", "green.json", "red.json", "sub/note.txt", "sub/pendrive.html"]
    assert found["green.json"].fetch_path == "green.html" and found["green.json"].seed
    assert found["red.json"].fetch_path == "red.json"
    assert not found["case3.json"].seed
    assert found["sub/pendrive.html"].meta["platform"] == "sample"
    assert found["sub/pendrive.html"].url == "http://backend:8000/fixtures/sub/pendrive.html"
    assert [s.path for s in discover("sub")] == ["sub/note.txt", "sub/pendrive.html"]


def test_seed_goes_through_real_pipeline(client):
    from app.seed import seed_if_empty

    job_ids = seed_if_empty()
    assert len(job_ids) == 4  # everything except case3 (seed: false)
    assert all(job(client, j)["state"] == "done" for j in job_ids)

    # fetched over HTTP from the fixture origin, scored by the AI service
    fetched = [str(r.url) for r in client.world.requests if r.url.host == "backend"]
    assert (
        "http://backend:8000/fixtures/green.html" in fetched
        and "http://backend:8000/fixtures/red.json" in fetched
    )
    assert len(client.world.ai_calls) == 4

    green = incidents(client, "?source=youtube")[0]
    assert (
        green["source"]["url"] == "https://www.youtube.com/watch?v=green"
        and green["title"] == "Spokojny film"
    )
    assert green["synthetic"] and green["ground_truth"] == "ok" and green["advertiser"] == "Kanał Spokojny"
    age = datetime.now(UTC) - datetime.fromisoformat(green["created_at"].replace("Z", "+00:00"))
    assert 0 <= age.total_seconds() < 60  # detection time is real, not fabricated history

    red_call = next(c for c in client.world.ai_calls if c["document"]["platform"] == "instagram")
    assert red_call["document"]["text"] == RED_TEXT and red_call["document"]["html"] == ""
    assert red_call["context"] == {"synthetic": True, "ground_truth": "violation", "module_hint": 3}
    assert red_call["document"]["fetch"]["engine"] == "httpx"

    bare = incidents(client, "?source=sample")
    assert {i["source"]["url"] for i in bare} == {
        "http://backend:8000/fixtures/sub/pendrive.html",
        "http://backend:8000/fixtures/sub/note.txt",
    }
    assert not any(i["demo_case"] for i in incidents(client))

    # second start: nothing happens (db not empty, lock taken)
    assert seed_if_empty() == []
    assert len(incidents(client)) == 4


def test_seed_runs_once_when_containers_race(client):
    from app.seed import _claim_seed_lock

    assert _claim_seed_lock() is True
    assert _claim_seed_lock() is False


def test_import_subdirectory_and_traversal(client):
    response = client.post("/api/samples/import", json={"path": "sub"})
    assert response.status_code == 202 and len(response.json()["job_ids"]) == 2
    assert len(incidents(client)) == 2
    assert client.post("/api/samples/import", json={"path": "missing"}).json() == {"job_ids": []}
    assert client.post("/api/samples/import").status_code == 202  # body optional
    for path in ("../", "/etc", "sub/../../x", "..\\x/../../.."):
        bad = client.post("/api/samples/import", json={"path": path})
        assert bad.status_code == 422, path


def test_demo_trigger_is_repeatable(client):
    assert client.post("/api/demo/trigger", json={"case": "nope"}).status_code == 404
    assert client.post("/api/demo/trigger", json={}).status_code == 422
    assert client.post("/api/demo/trigger", json={"case": "../x"}).status_code == 422

    first = client.post("/api/demo/trigger", json={"case": "case3"})
    assert first.status_code == 202
    first_id = job(client, first.json()["job_id"])["incident_id"]
    incident = client.get(f"/api/incidents/{first_id}").json()
    assert incident["demo_case"] == "case3" and incident["risk_score"] == 88.0
    created = datetime.fromisoformat(incident["created_at"].replace("Z", "+00:00"))
    assert (datetime.now(UTC) - created).total_seconds() < 60  # live demo: not back-dated

    second = client.post("/api/demo/trigger", json={"case": "case3"})
    second_id = job(client, second.json()["job_id"])["incident_id"]
    assert second_id != first_id and client.get(f"/api/incidents/{first_id}").status_code == 404
    assert len(incidents(client)) == 1
    assert len(events_named(client, "incident:new")) == 2 and len(events_named(client, "alert:high")) == 2


@pytest.mark.parametrize(
    "path",
    [
        "../conftest.py",
        "..%2F..%2Fetc%2Fpasswd",
        "%2e%2e/%2e%2e/etc/passwd",
        "/etc/passwd",
        "sub/../../etc/passwd",
        "....//etc/passwd",
        ".hidden",
        "sub",
        "missing.html",
    ],
)
def test_fixtures_path_traversal(client, samples_dir, path):
    (samples_dir / ".hidden").write_text("secret")
    response = client.get(f"/fixtures/{path}")
    assert response.status_code == 404 and "secret" not in response.text and "root:" not in response.text


def test_fixtures_serve_samples_read_only(client):
    response = client.get("/fixtures/green.html")
    assert response.status_code == 200 and "Fundusz Spokojny" in response.text
    assert response.headers["content-type"].startswith("text/html")
    assert "sandbox" in response.headers["content-security-policy"]
    assert client.get("/fixtures/sub/note.txt").headers["content-type"].startswith("text/plain")
    assert client.post("/fixtures/green.html").status_code == 405


def test_fixture_symlink_escape(samples_dir, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("secret")
    (samples_dir / "link.txt").symlink_to(secret)
    with pytest.raises(UnsafePath):
        safe_join(samples_dir, "link.txt")
    (samples_dir / "link.txt").unlink()
