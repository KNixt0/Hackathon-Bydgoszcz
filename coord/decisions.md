# Decisions log

Append only. One line per decision. Agents read this before starting work.

| # | Date | Decision | Why | By |
|---|---|---|---|---|
| 1 | 2026-11-21 | Coordinate agents through GitHub issues/PRs (see PROTOCOL.md) | Agents on different accounts can't see each other's sessions | KNixt0 |
| 2 | 2026-11-21 | Hard rules from both briefs in coord/GUIDELINES.md, enforced by guard.sh + security.yml | Briefs forbid paid AI APIs, copyleft licenses and secrets in code | KNixt0 |
| 3 | 2026-11-21 | Warm-up demo: portfolio site in demo/portfolio/ (issues labeled demo), plan in coord/demo/portfolio-plan.md | Test the full swarm flow before the real task | KNixt0 |
| 4 | 2026-11-21 | Demo paused (status:paused on #5–#10); open demo PRs not merged; agents asked for owner names + improvement notes | Retro and token optimisation before the real task | KNixt0 |
| 5 | 2026-11-21 | Every PR from others needs KNixt0 approval, including size:xs (no auto-merge without the owner) | Owner keeps full human review | KNixt0 |
| 6 | 2026-11-21 | Task: #InvestWatch (UKNF). Layout stays `services/{backend,ai,frontend}` (not the `backend-scraper/` names from the planning prompt) | GUIDELINES #3 and guard.sh already assume it | KNixt0 |
| 7 | 2026-11-21 | Object storage = SeaweedFS (S3 API), queue broker = Valkey, Postgres driver = pg8000 | MinIO is AGPL, Redis ≥7.4 is not permissive, psycopg is LGPL; GUIDELINES #2 bans them. The brief names MinIO/Redis only as examples | KNixt0 (proposed by lead agent, pending PR approval) |
| 8 | 2026-11-21 | One score: `risk_score` 0–100 (higher = worse) is the raw engine output and the slider's input; "Compliance Score" = 100 − risk | The planning prompt mixed a compliance score (92 = green) with a risk threshold | KNixt0 |
| 9 | 2026-11-21 | Demo cases: only the green case names a real firm (XTB, verifiable register facts only); cases 2–3 use invented entities; all three marked synthetic | No invented allegations about real entities in front of the regulator | KNixt0 |
| 10 | 2026-11-21 | Engine is deterministic without an LLM; Ollama model is optional and not chosen yet. LLM output is accepted only if its quotes are exact substrings of the source | Demo must be fast and stable on any laptop; no hallucinated evidence | KNixt0 |
| 11 | 2026-11-21 | Seed and pendrive import run through the real pipeline (scraper → AI); nothing is stored pre-scored. A labelled synthetic set feeds the calibration panel | Threshold and FP/FN must be real (GUIDELINES #7, #8) | KNixt0 |
| 12 | 2026-11-21 | All three demo cases use invented entities (replaces #9); real firms appear only in the real KNF register snapshots | Audit: the green case attributed an invented cooperation and notification to XTB | KNixt0 |
| 13 | 2026-11-21 | Calibration threshold = flag threshold `T_orange` (default 20); `T_red` 70 only marks critical and drives the live alert. Contract incident.md v2 | At 35 the engine caught 12 of 23 labelled violations; at 20 it catches 19 with 2 false alarms | KNixt0 |
| 14 | 2026-11-21 | Local models: `gemma4:e4b-it-q4` + `embeddinggemma:300m-qat-q4` via Ollama as the demo configuration; engine stays deterministic when no model is reachable | Audit: challenge lists an inference engine and a model as expected results | KNixt0 |
