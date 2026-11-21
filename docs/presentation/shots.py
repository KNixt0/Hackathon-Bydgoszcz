import json, urllib.request, time
from playwright.sync_api import sync_playwright
B="http://frontend:8080"
def jget(path):
    d=json.load(urllib.request.urlopen(B+path)); return d if isinstance(d,list) else d["items"]
ids={i["demo_case"]:i["id"] for i in jget("/api/incidents") if i.get("demo_case")}
if "case3" not in ids:
    urllib.request.urlopen(urllib.request.Request(B+"/api/demo/trigger",data=json.dumps({"case":"case3"}).encode(),headers={"Content-Type":"application/json"},method="POST"))
    time.sleep(8); ids={i["demo_case"]:i["id"] for i in jget("/api/incidents") if i.get("demo_case")}
HIDE="""()=>{document.querySelectorAll('*').forEach(e=>{const p=getComputedStyle(e).position; if((p==='sticky'||p==='fixed')&&!e.closest('[role=dialog]')) e.style.visibility='hidden'})}"""
def settle(p):
    p.wait_for_load_state("networkidle"); p.wait_for_timeout(2500)
def clip(p,sel,out,h=None,y0=0):
    p.evaluate(HIDE); p.evaluate("window.scrollTo(0,0)")
    bb=p.locator(sel).first.bounding_box()
    p.screenshot(path=out,full_page=True,clip={"x":bb["x"],"y":bb["y"]+y0,"width":bb["width"],"height":min(h or bb["height"],bb["height"]-y0)})
with sync_playwright() as pw:
    b=pw.chromium.launch(args=["--no-sandbox"])
    p=b.new_context(viewport={"width":1440,"height":900},locale="pl-PL").new_page()
    def go(path): p.goto(B+path); settle(p)
    go("/"); p.screenshot(path="/tmp/01_kolejka.png")
    c2="/sprawy/"+ids["case2"]
    go(c2); p.screenshot(path="/tmp/02_sprawa2_werdykt.png")
    go(c2+"?widok=zgodnosc"); clip(p,"#wizualizacje","/tmp/03a_macierz.png",h=640)
    go(c2+"?widok=powiazania"); clip(p,"#wizualizacje","/tmp/03b_graf.png")
    go(c2+"?widok=opinie"); clip(p,"#wizualizacje","/tmp/03c_opinie.png",h=994)
    go(c2); clip(p,"#argumenty","/tmp/04_argumenty.png",h=1250)
    go(c2); p.locator("#zrodla").scroll_into_view_into_view if False else None
    go(c2)
    chip=p.locator("#werdykt .chip, #wizualizacje .chip").first
    chip.scroll_into_view_if_needed(); chip.click(); p.wait_for_timeout(2000)
    p.screenshot(path="/tmp/05_dowod.png")
    go("/sprawy/"+ids["case3"]); p.screenshot(path="/tmp/06_sprawa3_werdykt.png")
    go("/kalibracja"); p.screenshot(path="/tmp/07a_kalibracja_20.png",full_page=True)
    p.locator('[role=slider]').first.focus()
    for _ in range(15): p.keyboard.press("ArrowRight")
    p.wait_for_timeout(1500); p.screenshot(path="/tmp/07b_kalibracja_35.png",full_page=True)
    b.close()
