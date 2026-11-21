#!/usr/bin/env bash
# Regenerates screenshots (from the running stack) and docs/presentation/InvestWatch.pdf.
set -euo pipefail
cd "$(dirname "$0")/../.."
P=docs/presentation
mkdir -p $P/img
docker compose exec -T backend python - < $P/shots.py
for f in 01_kolejka 02_sprawa2_werdykt 03a_macierz 03b_graf 04_argumenty 05_dowod 05b_dowod_zoom 06_workflow 06b_historia 07a_kalibracja_20 07b_kalibracja_35 08_audyt 09_zglos 10_logowanie; do
  docker compose cp backend:/tmp/$f.png $P/img/
done
D=deck-$(date +%s)  # fresh dir: files copied in by docker cp are root-owned and cannot be removed
docker compose exec -T backend mkdir -p /tmp/$D
docker compose cp $P/deck.html backend:/tmp/$D/deck.html
docker compose cp $P/img backend:/tmp/$D/img
docker compose exec -T -e D=$D backend python - <<'PY'
import os
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(args=["--no-sandbox"])
    p = b.new_page()
    p.goto(f"file:///tmp/{os.environ['D']}/deck.html"); p.wait_for_load_state("networkidle")
    p.pdf(path=f"/tmp/{os.environ['D']}/InvestWatch.pdf", width="1280px", height="720px", print_background=True)
    b.close()
PY
docker compose cp backend:/tmp/$D/InvestWatch.pdf $P/InvestWatch.pdf
ls -l $P/InvestWatch.pdf
