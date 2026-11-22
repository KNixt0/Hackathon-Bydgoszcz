"""Browser regression audit of our own app, including layout measurements and screenshots."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(os.environ.get("VALIDATION_OUTPUT", "validation-results"))
OUT.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("VALIDATION_URL", "http://127.0.0.1:5193")
REPORT = {"screens": [], "defects": [], "console": []}


def inspect(page, label, width):
    page.screenshot(path=str(OUT / f"{label}-{width}.png"), full_page=True)
    measurement = page.evaluate("""() => {
      const visible = (el) => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
      const spills = [...document.querySelectorAll('.sort-heading')].filter(visible).flatMap(el => {
        const box=el.getBoundingClientRect(), cell=el.closest('th').getBoundingClientRect();
        return box.right>cell.right+1 ? [{text:el.textContent.trim(),excess:Math.ceil(box.right-cell.right)}] : [];
      });
      const forbidden=[...document.querySelectorAll('button,summary,[role=tooltip],.notification-count')].filter(visible).flatMap(el=>{
        const css=getComputedStyle(el), issues=[];
        if(css.fontWeight==='600')issues.push('weight-600');
        if(css.boxShadow!=='none'&&!css.boxShadow.includes('inset'))issues.push('depth-shadow');
        if(el.matches('.notification-count')&&parseFloat(css.borderRadius)>4)issues.push('pill');
        return issues.map(issue=>({issue,text:el.textContent.trim().slice(0,60)}));
      });
      return {pageOverflow:document.documentElement.scrollWidth>innerWidth+1,spills,forbidden,tableWidth:document.querySelector('.queue')?.getBoundingClientRect().width, viewport:innerWidth};
    }""")
    REPORT["screens"].append({"name": label, "width": width, **measurement})
    for key in ("pageOverflow", "spills", "forbidden"):
        value = measurement[key]
        if value:
            REPORT["defects"].append({"screen": label, "width": width, "type": key, "details": value})


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    for width, height in ((1440, 1000), (1024, 900), (390, 844)):
        context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
        page = context.new_page()
        page.on("pageerror", lambda error: REPORT["console"].append(str(error)))
        page.on("console", lambda message: REPORT["console"].append(message.text) if message.type in ("error", "warning") else None)
        for attempt in range(30):
            try:
                page.goto(BASE, wait_until="networkidle")
                break
            except Exception:
                if attempt == 29:
                    raise
                time.sleep(0.5)
        page.get_by_role("button", name="Zaloguj jako kierownik (demo)").click()
        page.get_by_test_id("queue-row").first.wait_for()
        page.evaluate("document.fonts.ready")
        inspect(page, "queue", width)
        page.locator('.filters-disclosure > summary').first.click()
        inspect(page, "queue-filters", width)
        page.get_by_role("button", name="7 dni", exact=True).click()
        page.get_by_role("button", name="Własny zakres", exact=True).click()
        inspect(page, "queue-range", width)
        page.locator('.queue__title').filter(has_text="Recenzja platformy CFD").first.click()
        page.locator('[data-testid="recommendation"]').wait_for()
        inspect(page, "case", width)
        reasoning = page.locator('.rounds > summary')
        if reasoning.count():
            reasoning.click()
            inspect(page, "reasoning", width)
        page.get_by_role("link", name="Kalibracja", exact=True).click()
        page.get_by_label("Próg flagowania").wait_for()
        inspect(page, "calibration", width)
        page.get_by_label("Próg flagowania").fill("26")
        save=page.get_by_role("button", name="Zapisz jako progi globalne")
        if save.count():
            save.click()
        page.get_by_role("link", name="Dziennik audytu", exact=True).click()
        page.get_by_role("heading", name="Dziennik audytu", exact=True).wait_for()
        inspect(page, "audit", width)
        context.close()
    browser.close()

(OUT / "visual-audit.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps({"screens": len(REPORT["screens"]), "defects": REPORT["defects"], "console": REPORT["console"]}, ensure_ascii=False))
summary = os.environ.get("GITHUB_STEP_SUMMARY")
if summary:
    with open(summary, "a") as handle:
        handle.write(f"## Browser audit\nScreens: {len(REPORT['screens'])}; layout/style observations: {len(REPORT['defects'])}; console messages: {len(REPORT['console'])}.\n")
