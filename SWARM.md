# Swarm framework

This framework lets many Claude agents, running on **different teammates' accounts and machines**, build one project together. GitHub is the only shared channel between them.

There are two layers:

```
┌──────────────── GitHub (shared by everyone) ─────────────────┐
│ Issues = tasks · Labels = state · Assignee = lock            │
│ PRs = results · CI = checks · coord/ = plan, contracts, log  │
└───────▲──────────────────▲──────────────────▲────────────────┘
        │                  │                  │
  laptop A (acct A)   laptop B (acct B)   GitHub Action (@claude)
  Agent Team:         Agent Team:         one-off fixes and
  lead + 2-3 mates    lead + 2-3 mates    reviews on PRs
```

- **Layer 1, on each laptop:** Claude Code *Agent Teams* (the experimental "swarm" feature). One lead agent plus a few teammates, all on that person's own Claude account. Each teammate works in its own git worktree.
- **Layer 2, between laptops and accounts:** the GitHub protocol in [coord/PROTOCOL.md](coord/PROTOCOL.md). Agents never chat with each other across accounts. They only read and write issues, PRs and `coord/` files.

## Setup (each teammate, once)

1. Install `gh` and Claude Code, then log in: `gh auth login` and `claude` (use your **own** Claude account).
2. Clone the repo. The project's [.claude/settings.json](.claude/settings.json) already turns on Agent Teams and lets Claude run `git`, `gh` and `./scripts/*` without asking. Restart Claude Code after cloning so it picks this up.
   **Run `claude` once inside the cloned folder and accept the "trust this folder" prompt.** Until you do, Claude ignores the allow list, and `scripts/worker.sh` (which runs Claude without supervision) can't run `git`/`gh`.
   It also **denies** force-pushes, direct pushes to `main`, and deleting the repo, branches or secrets. GitHub can't enforce branch protection on this private free-plan repo, so this agent-side guard is what protects `main`. Humans: please work through PRs too.
3. Add yourself to [coord/agents.md](coord/agents.md) with your role.

Once per repo (owner only):

```bash
./scripts/setup-labels.sh
```

To use `@claude` on GitHub: run `claude setup-token`, then add the result as the repo secret `CLAUDE_CODE_OAUTH_TOKEN`. You can use an API key in `ANTHROPIC_API_KEY` instead.

## Running it

| Who | Command | What it does |
|---|---|---|
| Planner (1 person) | `claude` → paste [coord/prompts/planner.md](coord/prompts/planner.md) | Turns `coord/plan.md` into contracts and small `status:ready` issues |
| Worker (anyone) | `./scripts/worker.sh` (`--loop` to keep going) | Picks the next free issue, claims it, builds it in a worktree, opens a PR |
| Worker with a team | `claude` → paste [coord/prompts/team-lead.md](coord/prompts/team-lead.md) | The lead claims 2–3 issues and gives each to a teammate |
| Reviewer (1 person) | `claude` → paste [coord/prompts/reviewer.md](coord/prompts/reviewer.md) | Reviews and merges PRs marked `status:review` |
| Anyone on GitHub | comment `@claude …` on an issue or PR | Small fixes and review answers |

Useful scripts:

- `./scripts/next-task.sh`: prints the next claimable issue number. It skips issues that are assigned or whose dependencies are still open.
- `./scripts/claim.sh <issue>`: locks the issue, creates branch `agent/<login>/<issue>` and worktree `.worktrees/<issue>`.

## Ground rules

Read [coord/PROTOCOL.md](coord/PROTOCOL.md). In short:

- One issue = one PR = one owner = its own set of files.
- Contracts are written first. Changing one is a decision for a human.
- Every handoff ends with the YAML status block.
- 3–6 workers in total. More than that mostly creates merge conflicts.
