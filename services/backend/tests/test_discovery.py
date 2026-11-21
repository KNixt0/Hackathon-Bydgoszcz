from __future__ import annotations

import json
import logging

from sqlalchemy import text

from app.config import get_settings
from app.discovery import extract_links, matches_keywords, register_fixture_source, run_discovery
from tests.conftest import GREEN_HTML, events_named
from tests.test_pipeline import ARTICLE, job, scan

LISTING = "https://search.example/results?q=inwestycje"
LISTING_HTML = """<html><head><base href="https://search.example/"></head><body>
<a href="https://promo.example/oferta">Gwarantowany zysk – oferta dnia</a>
<a href="/artykul/forex">Forex dla każdego</a>
<a href="https://promo.example/oferta#opinie">duplikat z kotwicą</a>
<a href="https://news.example/pogoda" title="Prognoza">Pogoda na jutro</a>
<a href="http://internal.test/admin">zysk w sieci wewnętrznej</a>
<a href="http://127.0.0.1/zysk">zysk lokalny</a>
<a href="javascript:alert(1)">zysk js</a><a href="mailto:a@b.pl">zysk mail</a><a href="#top">zysk</a>
<a href="/static/zysk.png">zysk obrazek</a><a href="ftp://files.example/zysk">zysk ftp</a>
<a href="https://promo.example/kolejna-inwestycja">Czytaj dalej</a>
</body></html>"""


def test_extract_links_and_keywords():
    links = dict(extract_links(LISTING_HTML, LISTING))
    assert list(links) == [
        "https://promo.example/oferta",
        "https://search.example/artykul/forex",
        "https://news.example/pogoda",
        "http://internal.test/admin",
        "http://127.0.0.1/zysk",
        "https://promo.example/kolejna-inwestycja",
    ]
    assert links["https://news.example/pogoda"] == "Pogoda na jutro Prognoza"
    assert matches_keywords("https://x.example/a", "Gwarantowany ZYSK", ["zysk"])
    assert matches_keywords("https://x.example/kolejna-inwestycja", "Czytaj dalej", ["inwestyc"])  # URL match
    assert not matches_keywords("https://x.example/a", "Pogoda", ["zysk", "forex"])
    assert matches_keywords("https://x.example/a", "cokolwiek", [])


def test_sources_crud_and_validation(client):
    created = client.post(
        "/api/discovery/sources",
        json={"url": LISTING, "module_hint": 1, "keywords": ["zysk", "forex"], "max_links": 5},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["url"] == LISTING and body["keywords"] == ["zysk", "forex"] and body["max_links"] == 5
    assert set(body) == {
        "id",
        "url",
        "module_hint",
        "keywords",
        "max_links",
        "render",
        "created_at",
        "last_run_at",
        "last_found",
        "last_error",
    }
    again = client.post("/api/discovery/sources", json={"url": LISTING, "keywords": ["zysk"]})
    assert (
        again.json()["id"] == body["id"] and again.json()["max_links"] == get_settings().discovery_max_links
    )
    assert len(client.get("/api/discovery/sources").json()["items"]) == 1
    for bad in (
        {"url": "http://10.0.0.1/"},
        {"url": "ftp://x.example"},
        {"url": LISTING, "max_links": 0},
        {"url": LISTING, "keywords": "zysk"},
        {"url": LISTING, "keywords": [""]},
        {},
    ):
        response = client.post("/api/discovery/sources", json=bad)
        assert response.status_code == 422 and isinstance(response.json()["detail"], str), bad
    assert client.delete(f"/api/discovery/sources/{body['id']}").status_code == 204
    assert client.delete(f"/api/discovery/sources/{body['id']}").status_code == 404
    assert client.get("/api/discovery/sources").json() == {"items": []}


def test_run_queues_only_new_matching_public_links(client):
    client.world.pages[LISTING] = LISTING_HTML
    client.world.pages["https://promo.example/oferta"] = ARTICLE
    client.world.pages["https://search.example/artykul/forex"] = GREEN_HTML
    client.world.pages["https://promo.example/kolejna-inwestycja"] = GREEN_HTML
    client.post(
        "/api/discovery/sources",
        json={"url": LISTING, "module_hint": 3, "keywords": ["zysk", "forex", "inwestycja"]},
    )

    assert client.post("/api/discovery/run").json() == {"status": "queued"}
    incidents = client.get("/api/incidents").json()["items"]
    assert {i["source"]["url"] for i in incidents} == {
        "https://promo.example/oferta",
        "https://search.example/artykul/forex",
        "https://promo.example/kolejna-inwestycja",
    }
    assert all(i["primary_module"] == 3 for i in incidents)  # module_hint of the source travels with the scan
    fetched = {str(r.url) for r in client.world.requests}
    assert not any("internal.test" in u or "127.0.0.1" in u or "pogoda" in u for u in fetched)
    source = client.get("/api/discovery/sources").json()["items"][0]
    assert source["last_found"] == 3 and source["last_run_at"] and source["last_error"] is None
    assert len(events_named(client, "incident:new")) == 3

    # second run: nothing is new
    assert run_discovery()["queued"] == 0
    assert len(client.get("/api/scans").json()["items"]) == 3
    # a new link appears on the listing -> only that one is queued
    client.world.pages[LISTING] = LISTING_HTML.replace(
        "</body>", '<a href="/artykul/nowy-zysk">Nowy</a></body>'
    )
    client.world.pages["https://search.example/artykul/nowy-zysk"] = ARTICLE
    assert run_discovery()["queued"] == 1


def test_run_respects_cap_and_known_incidents(client):
    client.world.pages[LISTING] = LISTING_HTML
    client.world.pages["https://promo.example/oferta"] = ARTICLE
    scan(client)  # already known from a manual scan
    client.post("/api/discovery/sources", json={"url": LISTING, "max_links": 1})
    result = run_discovery()
    assert result["sources"] == 1 and result["queued"] == 1
    assert job(client, result["job_ids"][0])["url"] == "https://search.example/artykul/forex"


def test_failing_source_does_not_stop_others(client):
    client.world.pages[LISTING] = LISTING_HTML
    client.world.pages["https://promo.example/oferta"] = ARTICLE
    client.post("/api/discovery/sources", json={"url": "https://down.example/list"})
    client.post("/api/discovery/sources", json={"url": LISTING, "keywords": ["oferta dnia"]})
    assert run_discovery()["queued"] == 1
    by_url = {s["url"]: s for s in client.get("/api/discovery/sources").json()["items"]}
    assert "404" in by_url["https://down.example/list"]["last_error"] and by_url[LISTING]["last_found"] == 1


def test_fixture_listing_is_registered_and_works_offline(client, samples_dir):
    assert register_fixture_source() is False  # no discovery/index.html: nothing happens
    (samples_dir / "discovery").mkdir(exist_ok=True)
    (samples_dir / "discovery" / "kontakt.html").write_text("<html><body><p>Kontakt: biuro</p></body></html>")
    (samples_dir / "discovery" / "oferta-kurs.html").write_text(
        "<html><body><p>Kurs inwestowania, gwarantowany zysk dla uczestników.</p></body></html>",
        encoding="utf-8",
    )
    (samples_dir / "discovery" / "index.html").write_text(
        '<html><body><a href="../green.html">Fundusz inwestycyjny</a><a href="../case3.html">VIP zysk</a>'
        '<a href="../sub/pendrive.html">Oferta z pendrive</a><a href="../missing.html">Brak inwestycji</a>'
        '<a href="kontakt.html">Kontakt</a><a href="oferta-kurs.html">Kurs</a></body></html>',
        encoding="utf-8",
    )
    assert register_fixture_source() is True and register_fixture_source() is False
    sources = client.get("/api/discovery/sources").json()["items"]
    assert [s["url"] for s in sources] == ["http://backend:8000/fixtures/discovery/index.html"]

    from app.samples import discover

    assert not any(s.path.startswith("discovery/") for s in discover())  # a listing is not a sample

    result = run_discovery()
    states = {job(client, j)["url"]: job(client, j)["state"] for j in result["job_ids"]}
    assert (
        states
        == {
            "https://www.youtube.com/watch?v=green": "done",  # mapped back to its sample (meta + context)
            "http://backend:8000/fixtures/sub/pendrive.html": "done",
            "http://backend:8000/fixtures/missing.html": "failed",
            "http://backend:8000/fixtures/discovery/oferta-kurs.html": "done",
        }
    )  # "Kontakt" is dropped by the default keyword filter;  # case3 (seed: false) stays reserved for the demo trigger
    green = client.get("/api/incidents?source=youtube").json()["items"][0]
    assert green["ground_truth"] == "ok" and green["synthetic"]
    offer = client.get("/api/incidents?q=oferta-kurs").json()["items"][0]
    assert offer["synthetic"] and offer["source"]["platform"] == "sample"
    assert sources[0]["keywords"] == ["oferta", "inwest", "doradztw", "family office", "wealth"]
    assert run_discovery()["queued"] == 0
    # pages under discovery/ are never imported as ordinary samples
    assert client.post("/api/samples/import", json={"path": "discovery"}).json() == {"job_ids": []}


# ---- periodic update on demand ----


def test_rescan_endpoint_records_changed_content(client, samples_dir):
    client.post("/api/samples/import", json={})
    green = client.get("/api/incidents?source=youtube").json()["items"][0]
    assert green["risk_score"] == 12.0
    client.patch(f"/api/incidents/{green['id']}", json={"status": "in_review"})
    before = len(events_named(client, "incident:updated"))

    # unchanged source -> version row with changed=false
    same = client.post(f"/api/incidents/{green['id']}/rescan")
    assert same.status_code == 202 and job(client, same.json()["job_id"])["incident_id"] == green["id"]

    # the advertiser edits the page -> new hash, new score, same incident
    (samples_dir / "green.html").write_text(
        GREEN_HTML.replace("</body>", "<p>Teraz gwarantowany zysk!</p></body>"), encoding="utf-8"
    )
    changed = client.post(f"/api/incidents/{green['id']}/rescan")
    assert job(client, changed.json()["job_id"])["state"] == "done"

    after = client.get(f"/api/incidents/{green['id']}").json()
    assert (
        after["risk_score"] == 88.0
        and after["status"] == "in_review"
        and after["created_at"] == green["created_at"]
    )
    assert (
        after["ground_truth"] == "ok" and after["title"] == "Spokojny film"
    )  # sample meta/context re-applied
    versions = client.get(f"/api/incidents/{green['id']}/versions").json()["items"]
    assert [(v["changed"], v["risk_score"]) for v in versions] == [(True, 88.0), (False, 12.0), (False, 12.0)]
    updates = events_named(client, "incident:updated")[before:]
    assert [u["risk_score"] for u in updates] == [12.0, 88.0] and all(u["id"] == green["id"] for u in updates)
    assert client.get("/api/incidents").json()["total"] == 4
    assert client.post("/api/incidents/nope/rescan").status_code == 404


def test_scheduled_rescan_includes_samples_only_when_enabled(client, monkeypatch):
    from app.tasks import enqueue_rescan

    client.post("/api/samples/import", json={})
    assert enqueue_rescan() == []
    monkeypatch.setattr(get_settings(), "rescan_samples", True)
    job_ids = enqueue_rescan()
    assert len(job_ids) == 4 and all(job(client, j)["state"] == "done" for j in job_ids)
    assert client.get("/api/incidents").json()["total"] == 4
    red = next(c for c in client.world.ai_calls[::-1] if c["document"]["platform"] == "instagram")
    assert red["context"]["ground_truth"] == "violation"


# ---- logs ----


def test_one_log_line_per_state_change_and_no_tracebacks(client, caplog):
    caplog.set_level(logging.INFO)
    client.world.pages["https://promo.example/oferta"] = ARTICLE
    job_id = scan(client)
    scan(client, "https://promo.example/missing")
    lines = [r for r in caplog.records if r.name.startswith("app.")]
    states = [r.state for r in lines if r.getMessage() == "job state" and r.job_id == job_id]
    assert states == ["queued", "scraping", "analyzing", "done"]
    failed = [r for r in lines if r.getMessage() == "job state" and r.state == "failed"]
    assert len(failed) == 1 and "404" in failed[0].error
    assert not any(r.exc_info for r in caplog.records)
    dumped = json.dumps([r.getMessage() + str(r.__dict__.get("error", "")) for r in lines])
    assert "Gwarantowany zysk" not in dumped  # payloads are never logged


def test_existing_database_gets_new_columns(client):
    from app.db import _add_missing_columns, get_engine

    with get_engine().begin() as connection:
        connection.execute(text("ALTER TABLE incidents DROP COLUMN scan_context"))
    _add_missing_columns()
    client.world.pages["https://promo.example/oferta"] = ARTICLE
    assert job(client, scan(client))["state"] == "done"
