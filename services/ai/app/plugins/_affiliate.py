"""Affiliate links and redirect chains as evidence of a commercial relationship (module 1).

Inputs come from the scraper (`document.affiliate_links`, `affiliate_params`, `final_url`,
`redirect_chain`, contract v3); when they are absent (offline samples) the anchors of
`document.html` are read directly. A link counts only when it points at an official domain of a
firm in the KNF investment-firm registers (register `domains`) or of the resolved firm.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urljoin, urlsplit

from ..context import AnalysisContext
from ..registries import KNF_FIRM_REGISTERS

AFFILIATE_KEYS = {
    "ref", "ref_id", "refid", "refcode", "ref_code", "referral", "referrer", "reflink",
    "aff", "aff_id", "affid", "affiliate", "affiliate_id", "partner", "partner_id", "partnerid",
    "promo", "promocode", "promo_code", "code", "coupon", "voucher", "invite", "invite_code",
    "clickid", "click_id", "subid", "sub_id", "irclickid", "tracking_id", "tid", "via",
}  # fmt: skip


@dataclass
class AffiliateLink:
    url: str
    host: str
    params: list[str]
    firm: str  # registered entity whose domain the link points at
    registry: str | None
    via_redirect: bool = False  # the analysed address itself redirects there


def params_of(url: str) -> list[str]:
    try:
        query = urlsplit(url).query
    except ValueError:
        return []
    return [
        f"{k}={v}"[:120]
        for k, v in parse_qsl(query, keep_blank_values=True)
        if k.lower() in AFFILIATE_KEYS or k.lower().startswith("utm_")
    ]


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


class _Anchors(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):  # type: ignore[no-untyped-def]
        if tag == "a" and len(self.hrefs) < 300:
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href.strip())


def _html_links(html: str, base: str) -> list[str]:
    parser = _Anchors()
    with contextlib.suppress(Exception):  # malformed HTML only means fewer links
        parser.feed(html)
    return [u for u in (urljoin(base, h) for h in parser.hrefs) if u.startswith(("http://", "https://"))]


def _registered_domain(ctx: AnalysisContext, host: str) -> tuple[str, str | None] | None:
    for registry in KNF_FIRM_REGISTERS:
        for entry in ctx.registries.snapshot(registry).entries:
            for domain in entry.get("domains", []):
                d = domain.lower().removeprefix("www.")
                if host == d or host.endswith("." + d):
                    return entry["name"], registry
    firm = ctx.entities.firm
    if firm and firm.url:
        d = _host(firm.url)
        if d and (host == d or host.endswith("." + d)):
            return firm.name, None
    return None


def affiliate_links(ctx: AnalysisContext) -> list[AffiliateLink]:
    doc = ctx.document
    own = ctx.host
    candidates: list[tuple[str, list[str], bool]] = []
    if doc.affiliate_links:
        candidates += [(link.url, list(link.params) or params_of(link.url), False) for link in doc.affiliate_links]
    elif doc.html:
        for url in _html_links(doc.html, doc.url):
            params = params_of(url)
            if params and _host(url) != own:
                candidates.append((url, params, False))
    final = doc.final_url
    if final and len(doc.redirect_chain) > 1 and _host(final) != _host(doc.redirect_chain[0]):
        params = params_of(final) or [p for p in doc.affiliate_params if p in final]
        if params:
            candidates.append((final, params, True))
    out: list[AffiliateLink] = []
    seen: set[str] = set()
    for url, params, via_redirect in candidates:
        host = _host(url)
        if not host or url in seen:
            continue
        match = _registered_domain(ctx, host)
        if match:
            seen.add(url)
            out.append(AffiliateLink(url, host, params, match[0], match[1], via_redirect))
    return out
