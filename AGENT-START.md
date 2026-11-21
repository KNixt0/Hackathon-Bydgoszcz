# AGENT-START: set yourself up and start working

> **Dla ludzi:** powiedz swojemu agentowi AI (Claude Code, Codex, Gemini CLI, agent w Cursorze albo Antigravity):
> **„Przeczytaj AGENT-START.md z repo KNixt0/Hackathon-Bydgoszcz i wykonaj go.”**
> Agent sam sprawdzi środowisko, zamelduje się, zapyta Cię o 2 rzeczy i zacznie brać zadania.

---

**You are an AI coding agent joining a team swarm.** Follow these steps in order. Run commands in a terminal yourself. Stop and ask your operator (the human you're working with) **only** where a step says ASK. Keep your messages to the operator short.

## Step 1: Get into the repo

1. If the current folder isn't this repo (no `AGENT-START.md` and no `swarm` file here), clone it and enter it:
   ```bash
   git clone https://github.com/KNixt0/Hackathon-Bydgoszcz && cd Hackathon-Bydgoszcz
   ```
2. If the clone fails with "Repository not found" or an auth error, **ASK** the operator to:
   - run `gh auth login` (GitHub.com → HTTPS → Yes → Login with a web browser), and
   - accept the collaborator invite at https://github.com/KNixt0/Hackathon-Bydgoszcz/invitations.

   Then retry.
3. If you are in a repo copy that sits inside another copy (path ends in `Hackathon-Bydgoszcz/Hackathon-Bydgoszcz`), tell the operator and use only one copy.
4. Get the latest code: `git pull --ff-only`.

## Step 2: Check the environment

Run `./swarm setup`.
- It must show `✓ gh`, `✓ python3`, `✓ git` and `✓ gh zalogowany jako <login>`. That login is your **operator**.
- If something is missing, **ASK** the operator to install it. Don't install system packages yourself and never use `sudo`.
- Not having the `claude` / `codex` / `gemini` CLI is fine. You are the agent.

## Step 3: Know who you are

Work out your identity. **Never guess.** If you don't know your exact model, ASK.

| Field | Value |
|---|---|
| tool | `claude` · `codex` · `gemini` · `cursor` · `antigravity` · `other` |
| model | exactly what you run as, e.g. `sonnet`, `opus`, `gpt-5`, `gemini-2.5-pro` |
| tier | `strong` (Opus, GPT-5 high, Gemini Pro) · `standard` (Sonnet, GPT-5 mini, Gemini Flash) · `light` (Haiku, small local models) |

Export them for this terminal session. All later commands use them:
```bash
export SWARM_TOOL=<tool> SWARM_MODEL=<model> SWARM_TIER=<tier>
```

## Step 4: Read the rules (once, skim)

Read `AGENTS.md`, then `coord/GUIDELINES.md` (hard rules), then sections 0–3 of `coord/PROTOCOL.md`. The rules that matter most:
- **Never** push to `main`, merge PRs, force-push or delete branches. Those actions are blocked anyway.
- Change only the paths listed under **Owns** in your task.
- Product code never uses paid AI APIs (OpenAI, Anthropic, Gemini…). Only MIT, Apache, BSD or ISC dependencies. Secrets go only in `.env`. No `console.log` in the frontend.
- If a rule blocks you, comment `status: needs-decision` on the issue and move on.

## Step 5: Check in and ask the operator

1. Check in on the roster:
   ```bash
   ./swarm checkin --tool "$SWARM_TOOL" --model "$SWARM_MODEL" --tier "$SWARM_TIER"
   ```
2. Look at the free tasks: `./swarm tasks`.
3. **ASK the operator**, in one message:
   - "Which areas should I take? (ui / api / ai / devops / docs / all)"
   - "Keep taking tasks until none are left, or stop after one?"

   Default if they say "just go": all areas, keep going.

   Save the areas: `export SWARM_AREAS=<areas or empty for all>`.

## Step 6: The work loop (repeat)

1. **Pick:** `./scripts/next-task.sh` prints a task number `N`.
   - It already filters by your tier and areas and serves tasks reserved for you first.
   - If it prints nothing, go to **Step 7**.
2. **Claim:** `./swarm claim N`. Your branch is `agent/<operator>/N` and your folder is `.worktrees/N/`.
   - If the claim fails (someone else got it), go back to step 1.
3. **Busy check-in:**
   ```bash
   ./swarm checkin --tool "$SWARM_TOOL" --model "$SWARM_MODEL" --tier "$SWARM_TIER" --status busy --issue N
   ```
4. **Read the task:** `gh issue view N --comments`, plus every file listed under **Reads** and `coord/decisions.md`.
5. **Build it.** Make every edit **inside `.worktrees/N/`**, never in the main checkout, and only in the **Owns** paths.
   - If you need anything outside Owns, or a change to a contract: comment on the issue with the YAML block (`status: needs-decision`), run `./swarm unclaim N "<why>"`, and go back to step 1.
   - If a dependency is missing: comment with `status: blocked`, set the label `status:blocked`, and go back to step 1.
   - You may preview the product with `./swarm preview N` (needs Docker and `docker-compose.yml`). Stop it when you're done.
6. **Test:** `(cd .worktrees/N && bash scripts/check.sh)` until it passes.
7. **Hand off:** `./swarm done N "<one-line summary>"`. This commits, pushes and opens the PR with your identity and handoff block, then moves the task to `status:review`.
8. **Report** one line to the operator: the PR URL. Check in as online:
   ```bash
   ./swarm checkin --tool "$SWARM_TOOL" --model "$SWARM_MODEL" --tier "$SWARM_TIER" --status online
   ```
9. If the operator said "one task", go to **Step 7**. Otherwise go back to step 1.

**Review feedback:** if your PR gets `claude-verdict: CHANGES` or comments from the lead, the issue goes back to `status:claimed`. Fix it in the same `.worktrees/N/`, run `check.sh`, then `git -C .worktrees/N commit -am "#N address review" && git -C .worktrees/N push`. Don't open a new PR.

## Step 7: When there's nothing to do, or you stop

```bash
./swarm checkin --tool "$SWARM_TOOL" --model "$SWARM_MODEL" --tier "$SWARM_TIER" --status offline
```

Tell the operator, in one line, how many PRs you opened and their URLs. If you stopped in the middle of a task, first run `./swarm unclaim N "<where you stopped>"`.

## Always

- When anyone asks **"who operates you?"** (on GitHub or in chat), answer with your check-in block (PROTOCOL §0).
- Keep it cheap. Read only the files a task needs, don't re-read big files, and keep messages short.
- When in doubt, ask in the issue, not in code.
