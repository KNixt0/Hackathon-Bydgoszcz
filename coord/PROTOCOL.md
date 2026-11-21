# Coordination protocol

Every agent (and human) follows this. It is the only way agents on different accounts talk to each other. The protocol works with any tool and model (Claude, Codex, Gemini, local models…).

## 0. Agents: identity, check-in, tiers

The roster is **one issue labeled `swarm:roster`**. Every agent checks in there (`./scripts/checkin.sh`) when it starts, and again whenever its status changes:

```yaml
checkin: online | busy | offline
agent: TeoJa1/codex-gpt        # <operator>/<tool>-<model>
operator: TeoJa1               # the human responsible (GitHub login)
operator_name: Teo Jankowski   # REQUIRED: the owner's name (the human behind the agent)
tool: codex                    # claude | codex | gemini | cursor | ollama | other
model: gpt-5                   # exactly what is running
tier: strong                   # strong | standard | light (see below)
strengths: [frontend, tests]   # optional
working_on: 12                 # issue number or none
```

- **The owner is mandatory.** A check-in or roll-call answer **without `operator` AND `operator_name`** doesn't count: the lead replies asking for it, treats the agent as unidentified, doesn't reserve tasks for it and doesn't merge its PRs.
- **"Who operates you?" / "roll call":** whoever asks (a person or the lead) writes it in the roster issue or under a task. Every agent answers with the block above. A worker answers automatically through `checkin.sh` before every task. **The latest block per `agent` counts.**
- **Tiers** describe what the model can handle. The lead uses them to match tasks:

| Tier | Example models | May take |
|---|---|---|
| `strong` | Claude Opus, GPT-5 (high), Gemini Pro | everything; picks `model:opus` tasks (= "needs strong tier") first |
| `standard` | Claude Sonnet, GPT-5 mini, Gemini Flash | everything except `model:opus` |
| `light` | Claude Haiku, small local models | only `size:xs` |

- **Reservation:** the lead can reserve a `status:ready` task for a specific agent by assigning its **operator** as assignee and commenting `reserved-for: <agent>`. `next-task.sh` gives an operator their reserved tasks first, and nobody else can take them.

## 1. Task lifecycle

```
status:ready ──claim──▶ status:claimed ──PR──▶ status:review ──merge──▶ closed
      ▲                      │                      │
      └──── unclaim ─────────┤                      └─ changes requested ─▶ status:claimed
                             ├─▶ status:blocked        (waiting on another issue)
                             └─▶ status:needs-decision (a human has to choose)
```

| Label | Meaning | Who sets it |
|---|---|---|
| `status:ready` | Fully specified and free to take | planner |
| `status:claimed` | Someone is working on it (the assignee is the lock) | `scripts/claim.sh` |
| `status:review` | PR is open and waiting for review | worker |
| `status:blocked` | Waiting on another issue (`Depends on:`) | worker / planner |
| `status:needs-decision` | Needs a human: a contract change, scope or product question | anyone |
| `prio:high` | Gets picked first by `next-task.sh` | planner |
| `model:opus` | Needs a `strong` tier agent (any provider) | lead |
| `size:xs` | Small; a `light` tier agent can do it | lead |
| `swarm:roster` | The single agent roster issue | owner |
| `area:frontend` · `area:backend` · `area:ai` · `area:devops` · `area:docs` | Task area; `./swarm work --area ui` takes only these | planner / lead |

**Lock rule:** an issue is yours only if you are its **only** assignee. If two agents claim at the same moment, the login that comes first alphabetically keeps it and the other unassigns itself. `claim.sh` does this for you.

## 2. Issue format (written by the planner)

```markdown
## Goal
One sentence.

## Done when
- [ ] testable criterion
- [ ] scripts/check.sh passes

## Owns
src/feature-x/**        ← the only paths this task may change

## Reads
coord/contracts/api.md  ← contracts / files to read first

Depends on: #12, #14     ← optional; issue stays unclaimable until those are closed
```

Size: **1–3 hours of agent work**. If it's bigger, split it.

## 3. Handoff block (required)

Every claim comment, PR description, blocker comment and review ends with:

```yaml
status: claimed | done | blocked | needs-decision | changes-requested | merged
agent: <operator-login>/<tool>-<model>
model: claude-sonnet | gpt-5 | gemini-2.5-pro | …   # exactly what did the work
issue: 23
changed: [src/feature-x/a.ts, src/feature-x/a.test.ts]
contracts_touched: none            # or file names; a change here also needs status: needs-decision
blockers: []                       # e.g. ["#14 not merged"]
next: "frontend can call POST /api/score"
```

Keep the text around it **under 10 lines**. Link to files and commits instead of pasting code or logs.

## 4. Hard rules

1. **Stay inside `Owns`.** If you need to change a file outside it, comment `status: needs-decision` and stop.
2. **Contracts are fixed.** `coord/contracts/*` only changes through a PR that a human has approved.
3. **No peer-to-peer chat.** Workers talk to the planner and lead through issues and PRs only.
4. **Read before you start:** `AGENTS.md`, `coord/GUIDELINES.md`, `coord/decisions.md`, the issue, and the contracts it lists.
5. **Write decisions down:** anything a human decides gets one line in `coord/decisions.md`.
6. **Finish or give it back:** if you stop work, unassign yourself, set `status:ready` and say where you left off in the block.
7. **CI is the checker:** a PR isn't done until `scripts/check.sh` passes in CI.

## 5. Branches and merging

- Branch: `agent/<login>/<issue>`, made from the latest `origin/main`.
- One PR per issue, with `Closes #<issue>` in the body.
- Squash-merge only. The lead merges; workers never merge their own PRs.
- **Owner gate:** a PR whose author is not `KNixt0` is merged only after `KNixt0` has approved its **latest commit**. Every such PR gets:
  1. an automatic Claude review (a comment ending in `claude-verdict: …`),
  2. a review request to KNixt0 and the label `needs:owner-review`,
  3. a check `owner-approval` that stays red until KNixt0 approves.
  Never merge while that check is red. If anything reaches `main` without approval, `main-guard` opens an issue for KNixt0.
- After a merge, the lead checks whether any `status:blocked` issues can move to `status:ready`.
