# Hackathon-Bydgoszcz: agent instructions

Several Claude agents on different accounts work in this repo at the same time. They coordinate only through GitHub. Read and follow [coord/PROTOCOL.md](coord/PROTOCOL.md).

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
- Don't edit `coord/contracts/*`, `CLAUDE.md` or `.github/*` unless the issue says so.
- Run `./scripts/check.sh` before you push.
- Make small commits with messages like `#<issue> short description`.

## When done

- Push the branch and open a PR with `Closes #<n>` and the handoff YAML block from the protocol.
- Set the label `status:review`. Don't merge your own PR.

## Project facts

<!-- Planner: fill these in once the stack is chosen -->
- Stack: TBD
- Run locally: TBD
- Test/lint: `./scripts/check.sh`
