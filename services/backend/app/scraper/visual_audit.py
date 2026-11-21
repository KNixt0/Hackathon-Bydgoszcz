"""Rendered visual audit: how a risk warning is actually presented in a real browser.

The archived HTML is rendered in headless Chromium at three viewports (desktop, tablet,
mobile). One browser launch per document, one context per viewport. In each context the page
is measured with `getComputedStyle` / `getBoundingClientRect` / `elementFromPoint` and one
full-page PNG is taken. The result is the `Document.visual` block of the API contract
(version 3) plus the screenshots, the navigations seen while rendering and the outbound links.

The main document is served from the archived HTML (the page is measured exactly as it was
archived, without a second fetch); sub-resources go through the network guard: only the page's
own origin for local fixture pages (the stack works offline), public addresses only otherwise.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import struct
import sys
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from app.config import Settings, get_settings
from app.scraper.ssrf import BlockedURL, check_url

log = logging.getLogger(__name__)

# name, width, height, mobile emulation (meta viewport honoured, touch, zoom-to-fit like a real device)
VIEWPORTS: tuple[tuple[str, int, int, bool], ...] = (
    ("desktop", 1920, 1080, False),
    ("tablet", 768, 1024, True),
    ("mobile", 390, 844, True),
)
MAX_PAGE_HEIGHT = 8000  # px of a full-page screenshot
MAX_SCREENSHOT_BYTES = 4_000_000
MAX_ITEMS = 40  # risk elements / performance blocks per viewport
JS_BUDGET_MS = 1500  # in-page measuring budget per viewport

# Candidate risk warnings (folded: lower case, no diacritics, "ł" -> "l"). The scraper only
# collects candidates; the AI service decides which of them really are risk information.
RISK_PATTERN = (
    r"ryzyk|\bstrat|stracic|stracisz|utrat|utracic|"
    r"rachunkow inwestorow detalicznych|inwestorow detalicznych odnotowuje|"
    r"kontrakty cfd sa zlozonymi|\bcfd\b.{0,80}dzwigni|nie gwarantuj|"
    r"\brisks?\b|\blos(?:e|s|ses|ing)\b|capital at risk|retail investor accounts"
)
# Past-performance claims: a percentage together with a return word or a period.
PERF_PATTERN = (
    r"zysk|zarobi|stop[aey] zwrotu|zwrot|wynik|rentown|wzros|zyskal|"
    r"\breturns?\b|performance|\bytd\b|"
    r"\b(?:19|20)\d\d\s?[-–/]\s?(?:19|20)\d\d\b|\bw (?:ciagu|ostatni\w*)\b|"
    r"\b(?:rok|lat|lata|miesi\w*|kwarta\w*|tygodni\w*)\b"
)
AFFILIATE_KEYS = {
    "ref",
    "ref_id",
    "refid",
    "refcode",
    "ref_code",
    "referral",
    "referrer",
    "reflink",
    "aff",
    "aff_id",
    "affid",
    "affiliate",
    "affiliate_id",
    "partner",
    "partner_id",
    "partnerid",
    "promo",
    "promocode",
    "promo_code",
    "code",
    "coupon",
    "voucher",
    "invite",
    "invite_code",
    "clickid",
    "click_id",
    "subid",
    "sub_id",
    "irclickid",
    "tracking_id",
    "tid",
    "via",
}
AFFILIATE_PREFIXES = ("utm_",)


class VisualAuditError(RuntimeError):
    pass


@dataclass
class VisualAudit:
    visual: dict  # contract `Document.visual`, screenshot keys still None
    screenshots: dict[str, bytes]  # viewport name -> PNG
    navigations: list[str]  # main-frame URLs seen while rendering (JS / meta redirects)
    links: list[str]  # absolute outbound http(s) links of the rendered desktop page
    duration_ms: float
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------- in-page script

_MEASURE_JS = (Path(__file__).with_name("measure.js")).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------- helpers


def png_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def affiliate_params(url: str) -> list[str]:
    """Affiliate / tracking parameters of one URL as `key=value` strings."""
    try:
        query = urlsplit(url).query
    except ValueError:
        return []
    out = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        k = key.lower()
        if k in AFFILIATE_KEYS or k.startswith(AFFILIATE_PREFIXES):
            out.append(f"{key}={value}"[:120])
    return out


def affiliate_links(links: list[str], page_url: str) -> list[dict]:
    """Outbound links (other host than the page) that carry affiliate / tracking parameters."""
    own = (urlsplit(page_url).hostname or "").lower().removeprefix("www.")
    out: list[dict] = []
    seen: set[str] = set()
    for link in links:
        try:
            host = (urlsplit(link).hostname or "").lower().removeprefix("www.")
        except ValueError:
            continue
        if not host or host == own or link in seen:
            continue
        params = affiliate_params(link)
        if params:
            seen.add(link)
            out.append({"url": link[:500], "host": host, "params": params})
        if len(out) >= 30:
            break
    return out


def _launch_args(settings: Settings) -> list[str]:
    args = ["--disable-dev-shm-usage", "--disable-gpu", "--hide-scrollbars", "--force-color-profile=srgb"]
    if settings.chromium_no_sandbox:
        args.append("--no-sandbox")
    return args


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower()


def _merge(per_view: dict[str, dict], timings: dict[str, float]) -> dict:
    """Per-viewport measurements -> contract `visual` block."""
    desktop = per_view.get("desktop") or next(iter(per_view.values()))
    dominant = desktop.get("dominant_font_px") or 16.0
    viewports = []
    elements: dict[str, dict] = {}
    blocks: dict[str, dict] = {}
    for name, width, height, _ in VIEWPORTS:
        data = per_view.get(name)
        if data is None:
            continue
        scale = float(data.get("scale") or 1.0)
        fonts = []
        for item in data["risk"]:
            eff = round(item["font_px"] * scale, 2)
            if item["visible"] and not item["requires_interaction"]:
                fonts.append(eff)
            el = elements.get(item["key"])
            if el is None:
                el = elements[item["key"]] = {
                    "text": item["text"],
                    "font_px": item["font_px"],
                    "ratio_to_dominant": round(item["font_px"] / dominant, 3) if dominant else 1.0,
                    "color": item["color"],
                    "background": item["background"],
                    "contrast": item["contrast"],
                    "opacity": item["opacity"],
                    "visible": item["visible"],
                    "occluded": item["occluded"],
                    "placement": item["placement"],
                    "requires_interaction": item["requires_interaction"],
                    "control_text": item["control_text"],
                    "chars": item["chars"],
                    "bbox": None,
                    "bbox_of": None,
                    "bboxes": [],
                    "by_viewport": {},
                    "_order": item["order"],
                }
            bbox = dict(item["bbox"], viewport=name) if item["bbox"] else None
            el["by_viewport"][name] = {
                "font_px": eff,
                "css_font_px": item["font_px"],
                "visible": item["visible"],
                "occluded": item["occluded"],
                "clipped": item["clipped"],
                "contrast": item["contrast"],
                "requires_interaction": item["requires_interaction"],
                "bbox": bbox,
                "bbox_of": item["bbox_of"],
            }
            if bbox and item["bbox_of"] == "element":
                el["bboxes"].append(bbox)
            if bbox and el["bbox"] is None:
                el["bbox"], el["bbox_of"] = bbox, item["bbox_of"]
        for item in data["perf"]:
            bb = dict(item["bbox"], viewport=name) if item["bbox"] else None
            blk = blocks.get(item["key"])
            if blk is None:
                blk = blocks[item["key"]] = {
                    "text": item["text"],
                    "font_px": item["font_px"],
                    "area_share": item["area_share"],
                    "bbox": bb,
                    "by_viewport": {},
                    "_order": item["order"],
                }
            blk["by_viewport"][name] = {
                "font_px": round(item["font_px"] * scale, 2),
                "area_share": item["area_share"],
                "bbox": bb,
            }
        viewports.append(
            {
                "name": name,
                "width": width,
                "height": height,
                "page_height": int(data["page_height"]),
                "layout_width": int(data["inner_width"]),
                "scale": round(scale, 4),
                "screenshot_key": None,
                "screenshot_height": data.get("screenshot_height"),
                "overflow_x": bool(data["scroll_width"] > data["client_width"] + 1),
                "scroll_width": int(data["scroll_width"]),
                "clipped_texts": data["clipped_texts"],
                "min_risk_font_px": min(fonts) if fonts else None,
                "dominant_font_px": data.get("dominant_font_px"),
            }
        )
    risk_elements = sorted(elements.values(), key=lambda e: e.pop("_order"))
    performance_blocks = sorted(blocks.values(), key=lambda b: b.pop("_order"))
    return {
        "dominant_font_px": dominant,
        "max_font_px": desktop.get("max_font_px") or dominant,
        "has_viewport_meta": bool(desktop.get("has_viewport_meta")),
        "viewports": viewports,
        "risk_elements": risk_elements,
        "performance_blocks": performance_blocks,
        "engine": {"name": "chromium", "timings_ms": timings},
    }


# ---------------------------------------------------------------------------- main entry


def audit_page(
    url: str,
    html: str,
    *,
    user_agent: str,
    own_origin_only: bool,
    settings: Settings | None = None,
    timeout_s: float | None = None,
) -> VisualAudit:
    """Render `html` as the document at `url` in three viewports and measure it.

    Raises VisualAuditError (or BrowserUnavailable-like errors) on any failure; callers treat a
    failure as "no visual data".
    """
    settings = settings or get_settings()
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise VisualAuditError("playwright is not installed") from exc

    budget = timeout_s if timeout_s is not None else settings.visual_audit_timeout_seconds
    deadline = time.monotonic() + budget
    page_origin = _origin(url)

    def remaining_ms(floor: int = 500) -> int:
        left = int((deadline - time.monotonic()) * 1000)
        if left <= 0:
            raise VisualAuditError("visual audit timed out")
        return max(floor, left)

    @lru_cache(maxsize=256)
    def allowed(origin: str) -> bool:
        if origin == page_origin:
            return True
        if own_origin_only:
            return False
        try:
            check_url(origin + "/", settings)
            return True
        except BlockedURL:
            return False

    navigations: list[str] = []
    started = time.perf_counter()
    timings: dict[str, float] = {}
    per_view: dict[str, dict] = {}
    screenshots: dict[str, bytes] = {}
    links: list[str] = []
    body = html.encode("utf-8")

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=_launch_args(settings), timeout=remaining_ms())
            timings["launch"] = round((time.perf_counter() - started) * 1000, 1)
            try:
                for name, width, height, mobile in VIEWPORTS:
                    t_view = time.perf_counter()
                    route = _router(url, body, allowed)
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        device_scale_factor=1,
                        is_mobile=mobile,
                        has_touch=mobile,
                        user_agent=user_agent,
                        locale="pl-PL",
                        service_workers="block",
                        accept_downloads=False,
                        reduced_motion="reduce",
                    )
                    try:
                        context.set_default_timeout(remaining_ms())
                        context.route("**/*", route)
                        page = context.new_page()
                        if name == "desktop":
                            page.on(
                                "framenavigated",
                                lambda frame, page=page: (
                                    navigations.append(frame.url)
                                    if frame == page.main_frame and frame.url not in ("about:blank",)
                                    else None
                                ),
                            )
                        page.goto(url, wait_until="load", timeout=remaining_ms())
                        with contextlib.suppress(PlaywrightError):  # web fonts change metrics
                            page.evaluate("document.fonts && document.fonts.ready.then(() => true)")
                        data = page.evaluate(
                            _MEASURE_JS,
                            {
                                "riskSrc": RISK_PATTERN,
                                "perfSrc": PERF_PATTERN,
                                "maxItems": MAX_ITEMS,
                                "budgetMs": JS_BUDGET_MS,
                                "collectLinks": name == "desktop",
                            },
                        )
                        if name == "desktop":
                            links = list(data.get("links") or [])
                        shot = _screenshot(page, data, remaining_ms)
                        if shot is not None:
                            screenshots[name] = shot
                            size = png_size(shot)
                            data["screenshot_height"] = size[1] if size else None
                        per_view[name] = data
                    finally:
                        context.close()
                    timings[name] = round((time.perf_counter() - t_view) * 1000, 1)
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise VisualAuditError(f"browser error: {str(exc).splitlines()[0][:200]}") from exc

    if not per_view:
        raise VisualAuditError("no viewport could be measured")
    duration = round((time.perf_counter() - started) * 1000, 1)
    timings["total"] = duration
    visual = _merge(per_view, timings)
    return VisualAudit(
        visual=visual,
        screenshots=screenshots,
        navigations=list(dict.fromkeys(navigations)),
        links=links,
        duration_ms=duration,
        timings=timings,
    )


def _router(url: str, body: bytes, allowed):  # type: ignore[no-untyped-def]
    """Route handler: the first main-frame navigation gets the archived HTML, the rest the guard."""
    served = {"main": False}
    wanted = url.split("#")[0]

    def handle(route, request) -> None:  # type: ignore[no-untyped-def]
        target = request.url
        if target.startswith(("data:", "blob:", "about:")):
            route.continue_()
            return
        if not served["main"] and request.is_navigation_request() and target.split("#")[0] == wanted:
            served["main"] = True
            route.fulfill(status=200, body=body, headers={"content-type": "text/html; charset=utf-8"})
            return
        if allowed(_origin(target)):
            route.continue_()
        else:
            route.abort()

    return handle


def _screenshot(page, data: dict, remaining_ms) -> bytes | None:  # type: ignore[no-untyped-def]
    """Full-page PNG, capped at MAX_PAGE_HEIGHT and MAX_SCREENSHOT_BYTES (height is reduced to fit)."""
    from playwright.sync_api import Error as PlaywrightError

    width = max(1, int(data.get("scroll_width") or data.get("inner_width") or 1))
    height = max(1, min(int(data.get("page_height") or 1), MAX_PAGE_HEIGHT))
    for _ in range(3):
        try:
            shot = page.screenshot(
                type="png",
                full_page=True,
                clip={"x": 0, "y": 0, "width": width, "height": height},
                timeout=remaining_ms(),
                animations="disabled",
            )
        except PlaywrightError:
            return None
        if len(shot) <= MAX_SCREENSHOT_BYTES:
            return shot
        height = max(200, int(height * MAX_SCREENSHOT_BYTES / len(shot) * 0.9))
    return None


# ---------------------------------------------------------------------------- CLI (manual audits)


def _cli() -> None:  # pragma: no cover - manual tool
    ap = argparse.ArgumentParser(description="Render a page at three viewports and print the visual audit.")
    ap.add_argument("url", help="page URL (its HTML is fetched once with httpx unless --html is given)")
    ap.add_argument("--html", type=Path, help="local HTML file to render as the document at URL")
    ap.add_argument("--out", type=Path, help="directory for the screenshots and visual.json")
    ap.add_argument(
        "--any-origin", action="store_true", help="allow public sub-resources (default: own origin only)"
    )
    args = ap.parse_args()
    if args.html:
        html = args.html.read_text(encoding="utf-8")
    else:
        import httpx

        html = httpx.get(args.url, timeout=20).text
    result = audit_page(
        args.url, html, user_agent="InvestWatch visual audit", own_origin_only=not args.any_origin
    )
    out = {
        "duration_ms": result.duration_ms,
        "timings_ms": result.timings,
        "navigations": result.navigations,
        "affiliate_links": affiliate_links(result.links, args.url),
        "visual": result.visual,
    }
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        for name, png in result.screenshots.items():
            (args.out / f"screenshot-{name}.png").write_bytes(png)
        (args.out / "visual.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":  # pragma: no cover
    _cli()


# ---------------------------------------------------------------------------- pipeline hook


def _html_links(html: str, base: str) -> list[str]:
    from urllib.parse import urljoin

    from bs4 import BeautifulSoup

    out = []
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True)[:200]:
        href = urljoin(base, str(a["href"]).strip())
        if href.startswith(("http://", "https://")):
            out.append(href)
    return out


def visual_audit_available(settings: Settings | None = None) -> bool:
    from app.scraper import engine

    settings = settings or get_settings()
    return settings.visual_audit_enabled and settings.playwright_enabled and engine.transport is None


def attach_visual(
    document: dict, page, job_id: str, *, fixture: bool, store, settings: Settings | None = None
) -> None:  # type: ignore[no-untyped-def]
    """Add `final_url`, `redirect_chain`, `affiliate_params` (+ `affiliate_links`) and, for HTML,
    `visual` with one archived screenshot per viewport. Never raises: without a browser (or on
    any rendering problem) the document simply has no `visual`."""
    settings = settings or get_settings()
    if fixture:  # offline sample: the fetch URL is the local fixture origin, not the material's address
        final_url, chain = document["url"], []
    else:
        final_url = page.url
        chain = list(page.redirect_chain or [page.requested_url, page.url])
    audit: VisualAudit | None = None
    if document.get("html") and visual_audit_available(settings):
        try:
            audit = audit_page(
                page.url,
                document["html"],
                user_agent=page.user_agent,
                own_origin_only=fixture,
                settings=settings,
            )
        except Exception as exc:  # noqa: BLE001 - the pipeline continues without visual data
            log.warning("visual audit skipped", extra={"job_id": job_id, "error": str(exc)[:200]})
    if audit is not None and not fixture:
        for nav in audit.navigations:  # client-side redirects seen while rendering
            if nav not in chain:
                chain.append(nav)
        final_url = chain[-1] if chain else final_url
    links = (
        audit.links
        if audit is not None
        else (_html_links(document["html"], page.url) if document.get("html") else [])
    )
    aff_links = affiliate_links(links, final_url if not fixture else page.url)
    params = list(
        dict.fromkeys(affiliate_params(final_url) + [p for link in aff_links for p in link["params"]])
    )
    document["final_url"] = final_url
    if chain:
        document["redirect_chain"] = list(dict.fromkeys(chain))
    document["affiliate_params"] = params[:40]
    if aff_links:
        document["affiliate_links"] = aff_links
    if audit is None:
        return
    keys: dict[str, str] = {}
    for name, png in audit.screenshots.items():
        key = f"evidence/{job_id}/screenshot-{name}.png"
        try:
            store.put(key, png, "image/png")
        except Exception as exc:  # noqa: BLE001
            log.warning("screenshot not archived", extra={"job_id": job_id, "error": type(exc).__name__})
            continue
        keys[name] = key
    for viewport in audit.visual["viewports"]:
        viewport["screenshot_key"] = keys.get(viewport["name"])
    document["visual"] = audit.visual
    if keys:
        document["archive"]["screenshots"] = keys
        if keys.get("desktop"):
            document["archive"]["screenshot_key"] = keys["desktop"]
    log.info(
        "visual audit done",
        extra={
            "job_id": job_id,
            "duration_ms": audit.duration_ms,
            "risk_elements": len(audit.visual["risk_elements"]),
        },
    )
