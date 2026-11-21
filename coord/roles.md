# Role, modele i effort

The machine-readable version is [roles.json](roles.json). `./swarm` and the live view read it, so change the values there.

| Rola | Kto | Model | Effort | Co robi |
|---|---|---|---|---|
| **Właściciel** (owner) | KNixt0, człowiek | — | — | Approves PRs from others, decides `needs-decision` |
| **Lead** | Claude on KNixt0's account | Sonnet | medium | **Only delegates and merges.** Never writes code |
| **Planer** (planner) | Claude on KNixt0's account, once per phase | Opus | high | Plan → contracts → small tasks |
| **Budowniczy** (builder) | Claude on each teammate's account | Sonnet | medium | Builds a task, opens a PR |
| ↳ label `model:opus` | | Opus | high | Hard tasks |
| ↳ label `size:xs` | | Haiku | low | Small tasks |
| **Weryfikator** (verifier) | GitHub Action + CI | Opus | high | Independent review of every PR |

## Why this split

- **Planner on Opus/high:** splitting the work and writing contracts decides everything that follows. A bad split means conflicts and blocked tasks for the whole team. It runs rarely (a few times per hackathon), so it can afford the most expensive model.
- **Builders on Sonnet/medium:** most tasks take 1–3 h and are well specified, so speed and cost matter most. Several of them run in parallel on everyone's limits. The lead escalates with `model:opus` and steps down with `size:xs`.
- **Verifier on Opus/high, a different model from the builder:** an independent read catches more when it doesn't share the author's assumptions. It also has a fresh context and sees only the diff, the issue and the protocol.
- **Lead on Sonnet/medium:** coordination is routine (read state, check lamps, merge) and runs in a long loop, so a cheaper model is enough. The lead decides little on substance; harder calls go to the owner.
- **Owner is human:** a final approval from a person on PRs from other accounts.

## Who does NOT do what

- The lead doesn't write code or fix PRs, it only sends them back.
- A builder doesn't merge and doesn't review its own work (beyond `check.sh`).
- The verifier doesn't merge; it only gives a verdict.
- The planner doesn't write feature code.

## Flow

```
plan.md ─▶ Planer (Opus/high) ─▶ issues status:ready
                                     │  lead sets priority/model/size
                                     ▼
                     Budowniczy (Sonnet/medium; Opus/Haiku via label) ─▶ PR
                                     ▼
              CI ─ Weryfikator (Opus/high) ─ Właściciel (approve)
                                     ▼
                         Lead merges ─▶ main ─▶ unblocks the next tasks
```

## Other models (Codex, Gemini, local)

The roles stay the same. Only the tool behind them changes. A non-Claude agent:

1. checks in on the roster (`./swarm checkin --tool codex --model gpt-5 --tier strong`),
2. works through `SWARM_TOOL=codex SWARM_MODEL=gpt-5 SWARM_TIER=strong ./swarm work --loop`,
3. takes tasks matching its tier: `strong` everything, `standard` everything except `model:opus`, `light` only `size:xs`.

The lead reads the roster, does roll calls and adjusts tasks to whoever is online (PROTOCOL §0, `coord/prompts/lead.md`).
**The product itself still uses no paid APIs.** Other models are developer tools, just like Claude.

