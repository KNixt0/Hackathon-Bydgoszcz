"""Publisher identification regression found in the captured official XTB offer page."""

import json

from app.scraper.extract import extract


def page(*nodes):
    scripts = "".join(f'<script type="application/ld+json">{json.dumps(node)}</script>' for node in nodes)
    return (
        f'<html><head><meta name="twitter:site" content="@xtbpl">{scripts}</head><body>Oferta</body></html>'
    )


WEBSITE = {"@type": "WebSite", "name": "XTB.pl", "url": "https://www.xtb.com/pl/konto-i-oplaty"}
ORGANIZATION = {"@type": "Organization", "name": "XTB Polska", "url": "https://www.xtb.com/pl"}


def test_identified_site_publisher_is_not_replaced_by_a_social_handle():
    author = extract(page(WEBSITE, ORGANIZATION)).author
    assert author == {"name": "XTB Polska", "url": "https://www.xtb.com/pl", "handle": "@xtbpl"}


def test_explicit_article_author_retains_precedence():
    article = {"@type": "Article", "author": {"name": "Jan Kowalski"}}
    assert extract(page(WEBSITE, ORGANIZATION, article)).author["name"] == "Jan Kowalski"


def test_unrelated_organization_does_not_become_the_site_publisher():
    other = {**ORGANIZATION, "url": "https://unrelated.example/"}
    assert extract(page(WEBSITE, other)).author["name"] == "xtbpl"


def test_malformed_publisher_url_does_not_crash_extraction():
    invalid = {**ORGANIZATION, "url": "https://[invalid/"}
    assert extract(page(WEBSITE, invalid)).author["name"] == "xtbpl"
