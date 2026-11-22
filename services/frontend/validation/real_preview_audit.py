"""Exercise the actual app bundle with the three captured public-page analyses."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

out = Path(os.environ.get("VALIDATION_OUTPUT", "validation-results"))
report = {"screens": 0, "defects": [], "console": []}
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    for width, height in ((1440, 1000), (390, 844)):
        page = browser.new_page(
            viewport={"width": width, "height": height}, reduced_motion="reduce"
        )
        page.on("pageerror", lambda error: report["console"].append(str(error)))
        page.on(
            "console",
            lambda message: (
                report["console"].append(message.text)
                if message.type in ("error", "warning")
                else None
            ),
        )
        page.goto("http://127.0.0.1:5193/real-data.html", wait_until="networkidle")
        expect(page.get_by_test_id("queue-row")).to_have_count(3)
        expect(page.get_by_text("3 rzeczywiste strony:", exact=False)).to_be_visible()
        for index in range(4):
            name = "real-queue" if index == 0 else f"real-case-{index}"
            if index:
                page.locator(".queue__title").nth(index - 1).click()
                expect(page.get_by_test_id("recommendation")).to_be_visible()
                expect(
                    page.get_by_role("heading", name="Materiał źródłowy")
                ).to_have_count(1)
                expect(page.locator(".verdict-disclosure")).not_to_have_attribute(
                    "open", ""
                )
                page.get_by_test_id("evidence-row").first.click()
                expect(page.get_by_role("dialog")).to_be_visible()
                page.keyboard.press("Escape")
                expect(page.get_by_role("dialog")).to_have_count(0)
            overflow = page.evaluate(
                "document.documentElement.scrollWidth > innerWidth + 1"
            )
            if overflow:
                report["defects"].append(
                    {"screen": name, "width": width, "type": "page-overflow"}
                )
            page.evaluate("document.fonts.ready")
            page.screenshot(path=str(out / f"{name}-{width}.png"), full_page=True)
            if index < 2:
                page.evaluate("window.scrollTo(0, 0)")
                thumbnail = page.screenshot(type="jpeg", quality=50)
                print(
                    f"WATCHIT_SCREEN|{name}|{width}|"
                    + base64.b64encode(thumbnail).decode()
                )
            report["screens"] += 1
            if index:
                page.get_by_role("link", name="Kolejka spraw", exact=True).first.click()
                expect(page.get_by_test_id("queue-row")).to_have_count(3)
        page.close()
    browser.close()
(out / "real-preview-audit.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2)
)
print(json.dumps({"real_preview": report}, ensure_ascii=False))
if report["defects"] or report["console"]:
    raise SystemExit("Real-data preview has layout defects or console errors")
