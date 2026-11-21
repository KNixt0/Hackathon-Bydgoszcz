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

Once per repo (owner only; already done):

```bash
./scripts/setup-labels.sh
```

To use `@claude` on GitHub: run `claude setup-token`, then add the result as the repo secret `CLAUDE_CODE_OAUTH_TOKEN`. You can use an API key in `ANTHROPIC_API_KEY` instead.

## Quick start (everyone)

```bash
git clone https://github.com/KNixt0/Hackathon-Bydgoszcz && cd Hackathon-Bydgoszcz
./swarm setup     # checks gh, claude, python + shows roles
./swarm view      # opens the live view in your browser
```

On a Mac you can also **double-click `Swarm.command`** to open the live view. On Windows (no bash), run `python dashboard/server.py --open`.

## Running it: one command, `./swarm`

| Command | Who | Role · model · effort | What it does |
|---|---|---|---|
| `./swarm view` | anyone | — | Animated live view (opens the browser, finds a free port) |
| `./swarm status` | anyone | — | Task and PR counts in the terminal |
| `./swarm roles` | anyone | — | Who does what, which model and effort |
| `./swarm work [--loop]` | anyone | Builder · Sonnet · medium (`model:opus` → Opus/high, `size:xs` → Haiku/low) | Takes the next free task, builds it in a worktree, opens a PR |
| `./swarm team [N]` | anyone | Builder | An Agent Team on your laptop: a lead plus N builders |
| `./swarm plan` | KNixt0 | Planner · Opus · high | `coord/plan.md` → contracts → tasks |
| `./swarm lead` | KNixt0 | Lead · Sonnet · medium | **Only delegates and merges.** Never writes code |
| (automatic) | GitHub Actions | Verifier · Opus · high | Independent review of every PR from others |
| `@claude …` on GitHub | anyone | Sonnet · medium | Small ad-hoc fixes |

Why it's split this way: [coord/roles.md](coord/roles.md), also as a page for the team: [docs/swarm-roles.html](docs/swarm-roles.html). To change a model or effort, edit [coord/roles.json](coord/roles.json); everything reads from there.

Lower-level scripts: `./scripts/next-task.sh` (next claimable issue) and `./scripts/claim.sh <issue>` (lock, branch `agent/<login>/<issue>`, worktree `.worktrees/<issue>`).

## Live view (2D)

`./swarm view` opens an animated map of the swarm. It refreshes every 10 s from GitHub through your own `gh` login, so no token reaches the browser:

- **Do wzięcia** (to take): `status:ready` issues pinned on a board.
- **Warsztat** (workshop): one robot per claimed issue, colored by its owner, typing at a desk.
- **Recenzja** (review): open PRs with three lamps: CI · AI (Claude review) · Ty (owner approval).
- **Zablokowane** (blocked): `status:blocked` / `needs-decision`.
- **main**: merged PRs become commit nodes, with confetti on each new merge.
- **Zespół** (team): every collaborator, with a badge showing how many agents they have running.
- The right panel shows **Kto co robi** (who does what: roles, models, effort) and a live activity feed.

Click **Demo** to see a simulated swarm while the repo has no tasks yet.

## Guidelines from the task briefs

The hard rules from the HackNation briefs ([coord/briefs/](coord/briefs/)) are in [coord/GUIDELINES.md](coord/GUIDELINES.md). They are enforced by:

- `scripts/guard.sh`, run as part of `check.sh`: no paid AI APIs in `services/`, no `.env`/secrets, no `console.log` in the frontend, a Dockerfile per service plus docker compose;
- the CI workflow `security.yml`: gitleaks, pip-audit / npm audit, and a license scan that blocks GPL/AGPL/LGPL;
- the verifier, which also checks PRs against GUIDELINES.

The process description for the jury (20% of the score) is [docs/AI-PROCESS.md](docs/AI-PROCESS.md).

## Owner review gate

Every PR from someone other than **KNixt0** goes through this before merge:

1. **Claude reviews it automatically** (`owner-review.yml`) and leaves comments plus a `claude-verdict: APPROVE | CHANGES` line. This needs the repo secret `CLAUDE_CODE_OAUTH_TOKEN`; without it the step is skipped with a warning.
2. **KNixt0 gets a review request.** The check `owner-approval` stays red and the PR carries `needs:owner-review` until KNixt0 approves the **latest** commit. A new push needs a new approval.
3. **Safety net:** GitHub Free can't block the merge button on private repos. If something lands on `main` without that approval, `main-guard.yml` opens an issue assigned to KNixt0 with the diff.

## Ground rules

Read [coord/PROTOCOL.md](coord/PROTOCOL.md). In short:

- One issue = one PR = one owner = its own set of files.
- Contracts are written first. Changing one is a decision for a human.
- Every handoff ends with the YAML status block.
- 3–6 workers in total. More than that mostly creates merge conflicts.
