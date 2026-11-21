# Runs inside the backend container (python + Playwright). Writes PNGs to /tmp.
import json, urllib.request, time
from playwright.sync_api import sync_playwright
B = "http://frontend:8080"
OUT = "/tmp/"
HIDE = """()=>{document.querySelectorAll('*').forEach(e=>{const p=getComputedStyle(e).position; if((p==='sticky'||p==='fixed')&&!e.closest('[role=dialog]')) e.style.visibility='hidden'})}"""

def login(ctx, role):
    p = ctx.new_page()
    p.goto(B + "/logowanie"); p.wait_for_load_state("networkidle")
    p.get_by_role("button", name=f"Zaloguj jako {'analityk' if role == 'ANALYST' else 'kierownik'} (demo)").click()
    p.wait_for_timeout(2000)
    return p

def settle(p, ms=3500):
    p.wait_for_load_state("networkidle"); p.wait_for_timeout(ms)

def clip(p, out, y0, y1, hide=True):
    if hide: p.evaluate(HIDE)
    p.evaluate("window.scrollTo(0,0)")
    p.screenshot(path=OUT + out, full_page=True, clip={"x": 0, "y": y0, "width": 1440, "height": y1 - y0})

def top(p, sel):
    return p.evaluate("(s)=>document.querySelector(s).getBoundingClientRect().top+scrollY", sel)

with sync_playwright() as pw:
    b = pw.chromium.launch(args=["--no-sandbox"])
    mk = lambda: b.new_context(viewport={"width": 1440, "height": 900}, locale="pl-PL")
    ctx = mk(); p = login(ctx, "ANALYST")
    def jget(path):
        d = ctx.request.get(B + path).json(); return d if isinstance(d, list) else d["items"]
    def ids():
        return {i["demo_case"]: i["id"] for i in jget("/api/incidents") if i.get("demo_case")}
    I = ids()
    if "case3" not in I:
        ctx.request.post(B + "/api/demo/trigger", data=json.dumps({"case": "case3"}),
                         headers={"Content-Type": "application/json", "Origin": B}); time.sleep(10); I = ids()
    c2, c3 = "/sprawy/" + I["case2"], "/sprawy/" + I["case3"]
    inc2 = ctx.request.get(B + "/api/incidents/" + I["case2"]).json()
    ev_bbox = [e["id"] for e in inc2["evidence"] if e.get("bbox")][0]
    def go(path): p.goto(B + path); settle(p)

    # workflow: real transitions as analyst on a fresh queue case (not a demo case): start -> request escalation
    WF = None
    for it in jget("/api/incidents"):
        if it.get("demo_case") or it["risk_score"] < 70: continue
        d = ctx.request.get(B + "/api/incidents/" + it["id"]).json()
        if d["status"] in ("new", "in_review", "escalation_requested") and d["workflow"]["assigned_to"] in (None, "analityk@uknf.local"):
            WF = d["id"]; st = d["status"]; break
    wf = "/sprawy/" + WF
    go(wf)
    if st == "new":
        p.get_by_role("button", name="Rozpocznij weryfikację").click(); p.wait_for_timeout(2000); st = "in_review"
    if st == "in_review":
        p.get_by_role("button", name="Wnioskuj o eskalację").click(); p.wait_for_timeout(800)
        p.locator("#transition-reason").fill("Oferta bez licencji, autor nie figuruje w rejestrze doradców. Proszę o ścieżkę: lista ostrzeżeń publicznych.")
        p.get_by_role("button", name="Wyślij wniosek").click(); p.wait_for_timeout(2500)

    go("/"); clip(p, "01_kolejka.png", 0, 1180, hide=False)
    go(c2); clip(p, "02_sprawa2_werdykt.png", 0, 1090)
    go(c2 + "?widok=zgodnosc"); y = top(p, "#wizualizacje"); clip(p, "03a_macierz.png", y - 10, y + 700)
    go(c2 + "?widok=powiazania"); y = top(p, "#wizualizacje"); clip(p, "03b_graf.png", y - 10, y + 640)
    go(c2); y = top(p, "#argumenty"); clip(p, "04_argumenty.png", y - 10, y + 820)
    go(c2 + "?dowod=" + ev_bbox); p.wait_for_timeout(2500); p.screenshot(path=OUT + "05_dowod.png")
    # hi-DPI shot of the real drawer image (stored page screenshot + box drawn by the app)
    zc = b.new_context(viewport={"width": 1440, "height": 900}, locale="pl-PL", device_scale_factor=3)
    z = login(zc, "ANALYST"); z.goto(B + c2 + "?dowod=" + ev_bbox); settle(z, 3500)
    z.screenshot(path=OUT + "05b_dowod_zoom.png", clip={"x": 870, "y": 150, "width": 560, "height": 340})
    zc.close()
    go(wf); y = top(p, "[data-testid=workflow]"); clip(p, "06_workflow.png", y - 10, y + 330)
    h = top(p, "#historia"); p.evaluate("window.scrollTo(0,0)")
    clip(p, "06b_historia.png", h - 10, h + 440)
    go("/kalibracja"); p.screenshot(path=OUT + "07a_kalibracja_20.png", full_page=True)
    print("SENTENCE20:", p.locator("[data-testid=live-sentence]").inner_text())
    p.locator('input[type=range]').first.focus()
    for _ in range(15): p.keyboard.press("ArrowRight")
    p.wait_for_timeout(1500); p.screenshot(path=OUT + "07b_kalibracja_35.png", full_page=True)
    print("SENTENCE35:", p.locator("[data-testid=live-sentence]").inner_text())
    for _ in range(15): p.keyboard.press("ArrowLeft")
    p.wait_for_timeout(800)
    ctx.close()

    ctx = mk(); p = login(ctx, "SUPERVISOR")
    go("/audyt")
    p.locator("select").first.select_option(WF); p.wait_for_timeout(2000); p.screenshot(path=OUT + "08_audyt.png")
    ctx.close()

    ctx = mk(); p = ctx.new_page()
    p.goto(B + "/zglos"); settle(p, 1500); p.screenshot(path=OUT + "09_zglos.png")
    p.goto(B + "/logowanie"); settle(p, 1500); p.screenshot(path=OUT + "10_logowanie.png")
    b.close()
