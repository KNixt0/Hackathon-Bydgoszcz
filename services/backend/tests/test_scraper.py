from __future__ import annotations

import random
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.exports.csv_export import render_csv, safe_cell
from app.scraper import BlockedURL, Fetcher, check_url
from app.scraper.engine import FetchedPage
from app.scraper.extract import extract, guess_language, looks_js_empty
from app.scraper.parsers import detect_platform, select_parser
from app.scraper.ua import (
    DESKTOP_USER_AGENTS,
    MOBILE_USER_AGENTS,
    ProxyRotator,
    UserAgentRotator,
    redact_proxy,
)

FIXTURES = Path(__file__).parent / "fixtures"
SETTINGS = Settings(fixture_base_url="http://backend:8000")


def page(url: str, body: str, content_type: str = "text/html") -> FetchedPage:
    return FetchedPage(url, url, 200, content_type, body, "httpx", "ua", None, "2026-11-21T10:00:00Z")


# ---- SSRF guard (real resolver logic, literal addresses) ----


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://127.1/",
        "http://[::1]/",
        "http://10.0.0.1/",
        "http://172.16.5.4/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/",
        "http://[fe80::1]/",
        "http://[fc00::1]/",
        "http://0.0.0.0/",
        "http://[::ffff:127.0.0.1]/",
        "http://100.64.0.1/",
        "http://224.0.0.1/",
        "http://localhost/",
        "http://localhost.localdomain:8000/",
        "ftp://example.com/",
        "file:///etc/passwd",
        "gopher://example.com/",
        "javascript:alert(1)",
        "http:///nohost",
        "http://user:pass@93.184.216.34/",
        "http://backend:8001/",
        "https://backend:8000/",
        "http://backend.evil.example:99999/",
    ],
)
def test_ssrf_blocks(url):
    with pytest.raises(BlockedURL):
        check_url(url, SETTINGS)


@pytest.mark.parametrize(
    "url",
    [
        "http://93.184.216.34/x",
        "https://[2606:2800:220:1:248:1893:25c8:1946]/",
        "http://backend:8000/fixtures/a.html",
        "http://BACKEND:8000/fixtures/a.html",
    ],
)
def test_ssrf_allows_public_and_fixture_origin(url):
    check_url(url, SETTINGS)


def test_ssrf_blocks_if_any_resolved_address_is_private(monkeypatch):
    from app.scraper import ssrf

    monkeypatch.setattr(ssrf, "resolver", lambda host, port: ["93.184.216.34", "10.0.0.7"])
    with pytest.raises(BlockedURL):
        check_url("http://rebind.example/", SETTINGS)

    def unresolvable(host, port):
        raise OSError("nxdomain")

    monkeypatch.setattr(ssrf, "resolver", unresolvable)
    with pytest.raises(BlockedURL):
        check_url("http://nxdomain.example/", SETTINGS)


# ---- rotation ----


def test_user_agent_rotation():
    rotator = UserAgentRotator(rng=random.Random(7))
    picks = [rotator.next() for _ in range(200)]
    assert (
        set(picks) == set(DESKTOP_USER_AGENTS)
        and len(DESKTOP_USER_AGENTS) >= 5
        and len(MOBILE_USER_AGENTS) >= 2
    )
    assert all(a != b for a, b in zip(picks, picks[1:], strict=False))  # never the same twice in a row
    assert all(
        ua.startswith("Mozilla/5.0 (") and "bot" not in ua.lower()
        for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS
    )


def test_fetcher_sends_rotating_user_agents(client):
    seen = []
    client.world.pages["https://a.example/"] = "<html><body><p>" + "tekst " * 80 + "</p></body></html>"
    fetcher = Fetcher()
    for _ in range(6):
        seen.append(fetcher.fetch("https://a.example/").user_agent)
    sent = [r.headers["user-agent"] for r in client.world.requests if r.url.path == "/"]
    assert sent == seen and len(set(seen)) > 1 and set(seen) <= set(DESKTOP_USER_AGENTS)


def test_proxy_rotation_and_redaction():
    rotator = ProxyRotator(["http://u:secret@p1:8080", "socks5://p2:1080"])
    assert [rotator.next() for _ in range(3)] == [
        "http://u:secret@p1:8080",
        "socks5://p2:1080",
        "http://u:secret@p1:8080",
    ]
    assert ProxyRotator([]).next() is None
    assert redact_proxy("http://u:secret@p1:8080") == "http://p1:8080" and redact_proxy(None) is None
    assert Settings(proxy_urls=" http://a:1 , ,http://b:2").proxy_list == ["http://a:1", "http://b:2"]


def test_retries_then_gives_up(client):
    from app.scraper import FetchError

    client.world.pages["https://flaky.example/"] = httpx.Response(503)
    with pytest.raises(FetchError) as info:
        Fetcher().fetch("https://flaky.example/")
    assert info.value.retryable
    assert len([r for r in client.world.requests if r.url.path == "/"]) == 3  # 1 + SCRAPE_RETRIES


def test_charset_sniffing(client):
    body = (
        '<html><head><meta charset="iso-8859-2"></head><body><p>Zażółć gęślą jaźń</p></body></html>'.encode(
            "iso-8859-2"
        )
    )
    client.world.pages["https://old.example/"] = httpx.Response(
        200, content=body, headers={"content-type": "text/html"}
    )
    assert "Zażółć gęślą jaźń" in Fetcher().fetch("https://old.example/").body


# ---- extraction ----

OG_HTML = """<!doctype html><html lang="pl-PL"><head><title>Tytuł strony | Serwis</title>
<meta property="og:title" content="Zarabiaj z nami 20% rocznie"><meta property="og:description" content="Opis OG">
<meta property="og:site_name" content="Serwis"><meta property="article:published_time" content="2026-10-12T08:00:00+02:00">
<meta name="author" content="Jan Kowalski"><meta name="twitter:creator" content="@jkowalski">
<style>.x{color:red}</style><script>var hidden = "nie pokazuj";</script></head>
<body><nav>Menu</nav><h1>Zarabiaj z nami</h1><p>Pierwszy   akapit&nbsp;z ofertą.</p><!-- komentarz -->
<div style="display:none">ukryty tekst</div><p hidden>ukryty atrybutem</p><noscript>włącz js</noscript>
<ul><li>Punkt A</li><li>Punkt B</li></ul><footer>Inwestowanie wiąże się z ryzykiem.</footer></body></html>"""

JSONLD_HTML = """<html><head><title>x</title>
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"WebSite","name":"Portal"},
 {"@type":"NewsArticle","headline":"Nowy fundusz bez ryzyka","datePublished":"2026-09-01","inLanguage":"pl",
  "description":"Opis artykułu","author":[{"@type":"Person","name":"Anna Nowak","url":"https://portal.example/anna"}]}]}</script>
<script type="application/ld+json">{ broken json</script></head>
<body><article><p>Treść artykułu o funduszu.</p></article></body></html>"""


def test_extract_opengraph_and_visible_text():
    data = extract(OG_HTML)
    assert (
        data.title == "Zarabiaj z nami 20% rocznie"
        and data.description == "Opis OG"
        and data.language == "pl"
    )
    assert data.published_at == "2026-10-12T08:00:00+02:00" and data.site_name == "Serwis"
    assert data.author == {"name": "Jan Kowalski", "handle": "@jkowalski"}
    assert data.text.splitlines() == [
        "Menu",
        "Zarabiaj z nami",
        "Pierwszy akapit z ofertą.",
        "Punkt A",
        "Punkt B",
        "Inwestowanie wiąże się z ryzykiem.",
    ]


def test_extract_jsonld():
    data = extract(JSONLD_HTML)
    assert (
        data.title == "Nowy fundusz bez ryzyka"
        and data.published_at == "2026-09-01"
        and data.language == "pl"
    )
    assert data.author == {"name": "Anna Nowak", "url": "https://portal.example/anna"}
    assert data.text == "Treść artykułu o funduszu." and data.description == "Opis artykułu"


def test_extract_fallbacks_and_garbage():
    plain = extract(
        "<html><head><title> Tylko  tytuł </title></head><body><p>The quick offer is for you and the rest.</p>"
    )
    assert (
        plain.title == "Tylko tytuł"
        and plain.language == "en"
        and plain.author is None
        and plain.published_at is None
    )
    assert extract("").text == "" and extract("<<<>>>not html").title == ""
    assert (
        guess_language("Zysk gwarantowany dla każdego, nie czekaj") == "pl"
        and guess_language("12345") is None
    )


def test_js_shell_detection():
    assert looks_js_empty(
        '<html><body><div id="root"></div><script src="/app.js"></script></body></html>', ""
    )
    assert not looks_js_empty(
        "<html><body><p>" + "a" * 300 + "</p><script></script></body></html>", "a" * 300
    )
    assert not looks_js_empty("<html><body><p>krótko</p></body></html>", "krótko")


# ---- platform parsers ----


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://www.youtube.com/watch?v=1", "youtube"),
        ("https://youtu.be/1", "youtube"),
        ("https://www.instagram.com/p/x/", "instagram"),
        ("https://www.facebook.com/ads/library/?id=1", "facebook"),
        ("https://m.facebook.com/page", "facebook"),
        ("https://www.tiktok.com/@a/video/1", "tiktok"),
        ("https://x.com/a/status/1", "x"),
        ("https://twitter.com/a", "x"),
        ("https://adstransparency.google.com/x", "google_ads"),
        ("https://notyoutube.com/", "web"),
        ("https://example.com/youtube.com", "web"),
    ],
)
def test_detect_platform(url, platform):
    assert detect_platform(url) == platform


def test_youtube_parser_reads_player_json():
    html = """<html><head><title>Film - YouTube</title></head><body><script>var ytInitialPlayerResponse = {"videoDetails":
    {"title":"Forex w 5 minut","shortDescription":"Gwarantowany zysk. Link do brokera w opisie.","author":"Krypto Król"},
    "microformat":{"playerMicroformatRenderer":{"publishDate":"2026-10-01","ownerProfileUrl":"http://www.youtube.com/@kryptokrol"}}};
    var meta = 1;</script></body></html>"""
    url = "https://www.youtube.com/watch?v=1"
    parsed = select_parser(url).parse(page(url, html), aux=None)
    assert (
        parsed.platform == "youtube"
        and parsed.title == "Forex w 5 minut"
        and parsed.published_at == "2026-10-01"
    )
    assert parsed.author == {
        "name": "Krypto Król",
        "url": "http://www.youtube.com/@kryptokrol",
        "handle": "@kryptokrol",
    }
    assert "Gwarantowany zysk. Link do brokera w opisie." in parsed.text


def test_youtube_parser_falls_back_to_oembed():
    calls = []

    def aux(url):
        calls.append(url)
        return '{"title": "Z oEmbed", "author_name": "Kanał", "author_url": "https://www.youtube.com/@kanal"}'

    url = "https://www.youtube.com/watch?v=1"
    parsed = select_parser(url).parse(page(url, "<html><body><p>consent wall</p></body></html>"), aux=aux)
    assert parsed.title == "Z oEmbed" and parsed.author["name"] == "Kanał"
    assert calls and calls[0].startswith("https://www.youtube.com/oembed?format=json&url=https%3A%2F%2F")


def test_instagram_tiktok_x_parsers():
    ig = "https://www.instagram.com/p/x/"
    html = """<html><head><meta property="og:title" content="Guru on Instagram"><meta property="og:description"
    content='12 likes, 3 comments - guru.inwestor on November 1, 2026: "Pewny zysk, pisz na DM"'></head><body></body></html>"""
    parsed = select_parser(ig).parse(page(ig, html), aux=None)
    assert parsed.platform == "instagram" and parsed.text == "Pewny zysk, pisz na DM"
    assert (
        parsed.author == {"name": "guru.inwestor", "handle": "@guru.inwestor"}
        and select_parser(ig).prefers_render
    )

    tt = "https://www.tiktok.com/@trader/video/1"
    parsed = select_parser(tt).parse(
        page(tt, "<html><body></body></html>"),
        aux=lambda u: '{"title": "Kup teraz #krypto", "author_name": "Trader", "author_unique_id": "trader"}',
    )
    assert parsed.text == "Kup teraz #krypto" and parsed.author == {"name": "Trader", "handle": "@trader"}

    x = "https://x.com/analityk/status/1"
    oembed = '{"author_name": "Analityk", "author_url": "https://twitter.com/analityk", "html": "<blockquote><p>Kupuj akcje XYZ</p>&mdash; A</blockquote>"}'
    parsed = select_parser(x).parse(page(x, "<html><body></body></html>"), aux=lambda u: oembed)
    assert parsed.text == "Kupuj akcje XYZ" and parsed.author["handle"] == "@analityk"
    assert (
        select_parser(x).parse(page(x, "<html><body></body></html>"), aux=lambda u: None).author["handle"]
        == "@analityk"
    )


# ---- CSV injection ----


@pytest.mark.parametrize(
    "value", ["=1+1", "+48 123", "-2+3", "@SUM(A1)", "\t=cmd", "\r=cmd", '=HYPERLINK("http://x")']
)
def test_csv_formula_injection_is_neutralised(value):
    assert safe_cell(value) == "'" + value


def test_csv_safe_values_and_encoding():
    assert safe_cell("zwykły tekst") == "zwykły tekst" and safe_cell(None) == "" and safe_cell(-5) == -5
    assert safe_cell(12.5) == 12.5 and safe_cell(True) == "tak"
    raw = render_csv(["kolumna", "b"], [['Zażółć; "gęślą"\njaźń', "=A1"]])
    assert raw.startswith(b"\xef\xbb\xbf")
    assert raw.decode("utf-8-sig") == 'kolumna;b\r\n"Zażółć; ""gęślą""\njaźń";\'=A1\r\n'


# ---- KNF registers ----


def test_parse_real_knf_page():
    from app.registries import parse_register_page

    entries, last_page = parse_register_page(
        (FIXTURES / "knf_domy_maklerskie.html").read_text(encoding="utf-8")
    )
    assert last_page == 2
    assert entries[0] == {
        "name": "AIXON INVESTMENT MANAGEMENT SP. Z O.O.",
        "status": "listed",
        "detail": "Data zezwolenia: 2024-12-06",
    }
    assert entries[1]["name"] == "CERES DOM INWESTYCYJNY S.A." and entries[1]["aliases"] == [
        "EFIX DOM MAKLERSKI S.A."
    ]


def _register(names, pages=1):
    tables = "".join(
        f"<table><tr><th>Nazwa podmiotu</th><td><span>{n}</span></td></tr>"
        f"<tr><th>Państwo macierzyste</th><td>Niemcy</td></tr></table>"
        for n in names
    )
    nav = "".join(f'<a href="?page={n}">{n}</a>' for n in range(2, pages + 1))
    return (
        f'<html><body><div id="entityTable">{tables}</div><nav>{nav}</nav>'
        + "<p>tekst</p>" * 60
        + "</body></html>"
    )


def test_registry_refresh_pushes_snapshots_and_survives_failures(client):
    from app.registries import REGISTRIES, UMBRELLA, local_registry_list, refresh_all

    for spec in REGISTRIES:
        short = spec["registry"]
        if short == UMBRELLA:
            client.world.pages[spec["url"]] = (
                "<html><body>" + "<p>indeks rejestrów</p>" * 40 + "</body></html>"
            )
        else:
            client.world.pages[spec["url"]] = _register([f"{short} A", f"{short} B", f"{short} C"], pages=2)
            client.world.pages[spec["url"] + "?page=2"] = _register([f"{short} D"], pages=2)
    result = refresh_all()
    assert sorted(result["updated"]) == sorted(s["registry"] for s in REGISTRIES) and result["kept"] == []
    assert len(client.world.registries_put) == 5
    houses = client.world.registries_put["knf_brokerage_houses"]
    assert [e["name"] for e in houses["entries"]] == [f"knf_brokerage_houses {x}" for x in "ABCD"]
    assert houses["snapshot_date"] and houses["entries"][0]["detail"] == "Państwo macierzyste: Niemcy"
    assert len(client.world.registries_put[UMBRELLA]["entries"]) == 16  # union of the four lists

    # offline: every page fails -> previous snapshots stay, nothing is pushed, no exception
    client.world.pages.clear()
    client.world.registries_put.clear()
    result = refresh_all()
    assert result["updated"] == [] and len(result["kept"]) == 5 and client.world.registries_put == {}
    client.world.ai_down = True
    assert {i["registry"]: i["entries"] for i in local_registry_list()}["knf_brokerage_houses"] == 4

    # a layout change (page loads, no entries) must not wipe a good snapshot either
    client.world.ai_down = False
    for spec in REGISTRIES:
        client.world.pages[spec["url"]] = "<html><body>" + "<p>przerwa techniczna</p>" * 40 + "</body></html>"
    assert refresh_all()["updated"] == []
    client.world.ai_down = True
    assert {i["registry"]: i["entries"] for i in local_registry_list()}[UMBRELLA] == 16


def test_registry_push_retried_when_ai_was_down(client):
    from app.registries import REGISTRIES, UMBRELLA, push_pending, refresh_all

    for spec in REGISTRIES:
        if spec["registry"] != UMBRELLA:
            client.world.pages[spec["url"]] = _register(["A", "B", "C"])
    client.world.ai_down = True
    assert refresh_all()["pushed"] == []
    client.world.ai_down = False
    assert len(push_pending()) == 5 and push_pending() == []


# ---- storage fallback ----


def test_storage_falls_back_to_database(client):
    from app.storage import DbStore, FallbackStore

    class Broken:
        calls = 0

        def put(self, key, data, content_type):
            self.calls += 1
            raise ConnectionError("s3 down")

        def get(self, key):
            self.calls += 1
            raise ConnectionError("s3 down")

        def healthy(self):
            return False

    broken = Broken()
    store = FallbackStore(broken, DbStore())
    store.put("evidence/j1/page.html", "zażółć".encode(), "text/html; charset=utf-8")
    store.put("evidence/j1/screenshot.png", b"\x89PNG", "image/png")
    assert broken.calls == 1  # cooldown: S3 is not hammered while it is down
    assert store.get("evidence/j1/page.html") == ("zażółć".encode(), "text/html; charset=utf-8")
    assert store.get("evidence/missing") is None and store.healthy() and store.backend() == "db"

    from app import storage

    storage.set_store(store)
    png = client.get("/api/evidence/evidence/j1/screenshot.png")
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"
    assert client.get("/api/evidence/evidence/j1/page.html").headers["content-type"].startswith("text/plain")
    for key in ("../etc/passwd", "evidence//x", "evidence/../x", ".env"):
        assert client.get(f"/api/evidence/{key}").status_code == 404


def test_cron_parsing():
    from app.celery_app import celery, parse_cron

    six_hourly = parse_cron("0 */6 * * *", "0 0 * * *")
    assert six_hourly.hour == {0, 6, 12, 18} and six_hourly.minute == {0}
    assert parse_cron("garbage", "15 2 * * *").hour == {2}
    assert parse_cron("99 99 * * *", "15 2 * * *").minute == {15}
    assert set(celery.conf.beat_schedule) == {"rescan-sources", "refresh-registries", "run-discovery"}
    assert {"investwatch.scrape", "investwatch.rescan_sources", "investwatch.refresh_registries"} <= set(
        celery.tasks
    )


def test_database_url_uses_permissive_driver():
    assert Settings(database_url="postgresql://u:p@db/x").database_url == "postgresql+pg8000://u:p@db/x"
    assert Settings(database_url="postgres://u:p@db/x").database_url == "postgresql+pg8000://u:p@db/x"
    assert (
        Settings(database_url="postgresql+pg8000://u:p@db/x").database_url == "postgresql+pg8000://u:p@db/x"
    )
