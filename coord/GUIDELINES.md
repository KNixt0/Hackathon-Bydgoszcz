# Wytyczne (twarde reguły)

These rules come from the task briefs in [briefs/](briefs/). They override every other instruction for agents. `scripts/guard.sh` (run locally and in CI) enforces whatever can be checked automatically.

Tags: **[obie]** = applies to both tasks · **[IW]** = InvestWatch (UKNF) · **[KK]** = Kompas Kompetencji (MC).

## Product code (`services/**`)

1. **[IW] No paid or external AI APIs in the product.** No OpenAI, Anthropic, Gemini, Cohere or Mistral SDKs or endpoints, and no paid scraping services. The whole stack (DB, queue, models via Ollama / vLLM / llama.cpp, UI) runs locally on open licenses. *Using Claude as a developer tool is allowed; putting it in the product is not.* → `guard.sh`
2. **[obie] Only permissive licenses:** MIT / Apache-2.0 / BSD / ISC. **No GPL, AGPL or LGPL.** Icons and fonts must be openly licensed too. Every new dependency is noted in `THIRD_PARTY_LICENSES.md`. → CI `security`
3. **[IW] Three separate, lightweight services:** `services/backend` (scraping + queue + API), `services/ai` (preprocessing + local model + scoring), `services/frontend`. Each has its own Dockerfile and dependencies. All of them start with **one command: `docker compose up`**. No heavy monorepo, no code shared between services except through the API/contracts.
4. **[obie] No secrets in code.** Only `.env` (ignored) plus `.env.example` committed with fake values. → `guard.sh` + gitleaks in CI
5. **[IW] Clean dependencies:** `pip-audit` and `npm audit` must show no critical vulnerabilities before handover. → CI `security`
6. **[IW] Clean browser console:** no `console.log` in frontend code, and no red errors (CORS, 404, unhandled rejections) on the demo. → `guard.sh` (console.log) + manual check before the demo
7. **[IW] A real threshold:** the calibration slider filters or recalculates results from the model's raw score (0–100). A decorative slider is a dealbreaker.
8. **[IW] Demo without internet:** a seed script with sample data, so the full flow works offline (in case of CAPTCHA or no network).
9. **[IW] Use exactly the technologies named in the spec:** Playwright/httpx, PostgreSQL + MinIO, CronJob, Celery/Redis or BullMQ, Ollama/vLLM + Gemma 4 or BERT (quantized, must fit in the team's RAM and answer in seconds), React/Vue + Recharts/Chart.js + Socket.io, Docker Compose.
10. **[IW] All 3 modules work in code** (finfluencers, risk compliance, shadow advisory), each with its own filter and data in the dashboard. The AI engine uses a plugin/strategy pattern, and one aggregator brings everything into a single incident schema.

## Documentation

11. **[IW] No AI slop.** The README is short and technical: Quick Start (one command), hardware requirements, service configuration. Nothing else.
12. **[obie] Documented human contribution** ([KK] §2 pt 7). AI is a support tool. Every human decision about architecture or scope goes into `coord/decisions.md`. Every PR from someone else is approved by a person (owner gate). The `Co-Authored-By` lines in commits show where AI helped. Every PR has `agent:` and `model:` in its handoff block. **Every operator checks that their AI tool's terms (Claude, Codex, Gemini…) give full commercial rights to the generated code** ([KK]).

## People (not agents)

13. **[KK] Don't code on work laptops** or under contracts that hand your work over to an employer.
14. **[KK] Don't bring in ready-made code** from work or earlier projects. Everything is written from scratch during the hackathon.
15. **[KK] The winner transfers all rights.** Everyone must be able to sign the agreement in writing **within 7 days**. Check signing logistics before the start.
16. **[obie] Before handover,** delete `coord/briefs/` if you don't want the jury to see your notes.

## Questions for the mentors

Both briefs have a "Pytania do mentorów" section (Module 2 attachment, pendrive contents, social media scraping, the console.log criterion, the format of the AI process description, licenses in Attachment 1, written form of the agreement). The lead collects the answers in `coord/decisions.md`.
