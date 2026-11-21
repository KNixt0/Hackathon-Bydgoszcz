# Plan

## Challenge
**#InvestWatch (UKNF, HackNation 2026).** An on-premise system that scrapes the web and social media and, with local AI, flags non-compliant financial advertising for the supervisor: third-party/finfluencer ads of investment firms (Module 1), insufficient risk information in firms' own material against the 18 UKNF criteria (Module 2), and unlicensed investment advice, "shadow advisory" (Module 3).

## What we demo at the end
- `docker compose up` on one laptop, no internet: seeded cases appear, each scored by the real pipeline.
- Live: push the unseeded red sample → scraper → AI → WebSocket alert lands on top of the queue.
- Calibration: move the threshold slider → flagged counts, FP/FN, precision/recall change from raw scores.
- One case end to end: verdict, 18-rule matrix, relationship graph (board ↔ PR agency ↔ influencer), opinion forensics, for/against debate, evidence drawer, PDF/CSV evidence package.

## Stack
| Layer | Choice |
|---|---|
| Backend | Python, FastAPI, Celery + Valkey (queue, beat = cron), httpx + Playwright, PostgreSQL, S3 object storage (SeaweedFS), Socket.IO |
| AI | Python, FastAPI, plugin/strategy modules, rule + embedding scoring, optional local LLM via Ollama, debate with cross-critique, aggregator |
| Frontend | React + TypeScript + Vite, Recharts, socket.io-client, nginx |
| Run | Docker Compose; contracts in `coord/contracts/` |

## Main parts
| Part | Owns (paths) | Notes |
|---|---|---|
| Contracts, compose, docs | `coord/contracts/**`, `docker-compose.yml`, `.env.example`, `README.md`, `docs/**` | lead |
| Backend + scraper | `services/backend/**` | API, queue, scraper, storage, sockets, seed/import, exports |
| AI engine + samples | `services/ai/**`, `samples/**` | plugins M1–M3, 18 rules, registers, graph, forensics, debate, scoring |
| Dashboard | `services/frontend/**` | triage, calibration, case detail (4 blocks), evidence drawer |
| QA / security / deploy | `scripts/**`, `docs/security/**`, `deploy/**` | check.sh, audits, E2E, Azure CLI scripts last |

## Out of scope
- Logging in to social platforms or bypassing anti-bot protection (public pages, ad libraries and samples only).
- Real KRS/CRBR/KIRP/KIDP connectors: modelled as `Context` enrichment with sample data; the interface is in the contract.
- OCR of banners; production authentication (the demo has two local demo accounts).

## Timeline
| When | Milestone | State |
|---|---|---|
| Sat 21.11 20:00 | Draft checkpoint: HackTribe project, repo link, task locked | owner |
| Sat 21.11 evening | Must-haves end to end on compose, audits, README, deck | done (PR #30) |
| Sat 21.11 night | Additions from the owner's spec: rendered visual audit, login + workflow + audit log, public reports; redesign; Azure demo | done (PR #30) |
| Sun 22.11 morning | Clean demo data, rehearse the 3-minute script, final deck numbers, merge | open |
| Sun 22.11 11:00 | Final submission | open |
