# Coordination protocol

Every agent (and human) follows this. It is the only way agents on different accounts talk to each other.

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
agent: <github-login>/<agent-name>
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
3. **No peer-to-peer chat.** Workers talk to the planner and reviewer through issues and PRs only.
4. **Read before you start:** `CLAUDE.md`, `coord/decisions.md`, the issue, and the contracts it lists.
5. **Write decisions down:** anything a human decides gets one line in `coord/decisions.md`.
6. **Finish or give it back:** if you stop work, unassign yourself, set `status:ready` and say where you left off in the block.
7. **CI is the checker:** a PR isn't done until `scripts/check.sh` passes in CI.

## 5. Branches and merging

- Branch: `agent/<login>/<issue>`, made from the latest `origin/main`.
- One PR per issue, with `Closes #<issue>` in the body.
- Squash-merge only. The reviewer merges, workers never merge their own PRs.
- **Owner gate:** a PR whose author is not `KNixt0` is merged only after `KNixt0` has approved its **latest commit**. Every such PR gets:
  1. an automatic Claude review (a comment ending in `claude-verdict: …`),
  2. a review request to KNixt0 and the label `needs:owner-review`,
  3. a check `owner-approval` that stays red until KNixt0 approves.
  Never merge while that check is red. If anything reaches `main` without approval, `main-guard` opens an issue for KNixt0.
- After a merge, the reviewer checks whether any `status:blocked` issues can move to `status:ready`.
