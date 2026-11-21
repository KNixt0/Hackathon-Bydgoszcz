# Hackathon-Bydgoszcz: agent instructions

> **New here? Do [AGENT-START.md](AGENT-START.md) first**: self-setup, check-in, and the work loop.

This file is shared by **every AI agent**, whatever tool or model it runs on (Claude Code, Codex, Gemini CLI, Cursor, local models…). Many agents on different accounts work here at the same time and coordinate only through GitHub. Read and follow [coord/PROTOCOL.md](coord/PROTOCOL.md).

## Who you are (required)

- Every agent has an identity: `<operator-login>/<tool>-<model>`, for example `TeoJa1/codex-gpt` or `KNixt0/claude-sonnet`. The **operator** is the person (GitHub login) responsible for you.
- Before your first task, check in on the issue labeled `swarm:roster`: `./scripts/checkin.sh`, or a comment with the block from PROTOCOL.md §0.
- **When anyone asks "who operates you?" / "kto cię obsługuje?" / "roll call"**, reply with your check-in block. Never invent an operator or model; if you don't know, say `unknown`.
- Every handoff block includes `agent:` and `model:`.

## Hard rules: [coord/GUIDELINES.md](coord/GUIDELINES.md) (they override everything else)

- **No paid or external AI APIs in the product** (OpenAI, Anthropic, Gemini…). Product AI runs locally: Ollama / vLLM / llama.cpp.
- **Only MIT / Apache-2.0 / BSD / ISC dependencies.** No GPL, AGPL or LGPL. Record each new dependency in `THIRD_PARTY_LICENSES.md`.
- **Three separate services** under `services/` (backend, ai, frontend), each with its own Dockerfile, all started with `docker compose up`.
- **Secrets only in `.env`** (ignored), with `.env.example` committed using fake values.
- **No `console.log` in the frontend.** The browser console must be clean.
- **A short README:** Quick Start, hardware requirements, configuration. No AI slop.
- If a rule blocks your task, set `status: needs-decision` and stop. Never work around a rule.

## Before any work

1. Read `coord/plan.md` (what we're building), `coord/decisions.md` (what's already decided) and the contracts your issue lists.
2. Work only on an issue you claimed with `./scripts/claim.sh <n>`, inside its worktree `.worktrees/<n>`.

## While working

- Change only the paths listed under **Owns** in your issue.
- Don't edit `coord/contracts/*`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` or `.github/*` unless the issue says so.
- Run `./scripts/check.sh` before you push.
- Make small commits with messages like `#<issue> short description`.

## When done

- Push the branch and open a PR with `Closes #<n>` and the handoff YAML block from the protocol.
- Set the label `status:review`. Don't merge your own PR.

## Project facts

<!-- Planner: fill these in once the stack is chosen -->
- Stack: see `coord/plan.md` (FastAPI + Celery/Valkey + Postgres + SeaweedFS · FastAPI AI engine · React/Vite)
- Run locally: `cp .env.example .env && docker compose up --build` → http://localhost:3000
- Contracts: `coord/contracts/incident.md`, `coord/contracts/api.md`
- Test/lint: `./scripts/check.sh`
