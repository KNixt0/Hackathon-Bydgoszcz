# AGENT-START: set yourself up and start working

> **Dla ludzi:** powiedz swojemu agentowi AI (Claude Code, Codex, Gemini CLI, agent w Cursorze albo Antigravity):
> **„Przeczytaj AGENT-START.md z repo KNixt0/Hackathon-Bydgoszcz i wykonaj go.”**
> Agent sam sprawdzi środowisko, zapyta Cię tylko o imię (wymagane), zamelduje się i weźmie zadania z obszarów, które **przydzielił mu KNixt0**. Bez przydziału tylko się melduje i czeka.
>
> **Tylko raport, bez zadań:** „Przeczytaj AGENT-START.md w trybie TYLKO RAPORT: zamelduj się z imieniem właściciela, pokaż mi swój blok i nie bierz żadnych zadań.”

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
| **owner name** | **REQUIRED.** The name of the human who owns you. **ASK the operator: "What is your name (owner of this agent)?"** Never make it up and never use the GitHub login instead. Without it your check-in is rejected. |

Export them for this terminal session. All later commands use them:
```bash
export SWARM_TOOL=<tool> SWARM_MODEL=<model> SWARM_TIER=<tier> SWARM_OPERATOR_NAME="<owner name>"
```

## Report-only mode

If the operator said **"report only" / "tylko raport"**, or asked you not to do tasks:
1. do Steps 1–3,
2. check in: `./swarm checkin --tool "$SWARM_TOOL" --model "$SWARM_MODEL" --tier "$SWARM_TIER"`,
3. show the operator your check-in block (agent, operator, **operator_name**, tool, model, tier) and the output of `./swarm status`,
4. **stop**: don't claim, edit, commit or open PRs.

## Step 4: Read the rules (once, skim)

Read `AGENTS.md`, then `coord/GUIDELINES.md` (hard rules), then sections 0–3 of `coord/PROTOCOL.md`. The rules that matter most:
- **Never** push to `main`, merge PRs, force-push or delete branches. Those actions are blocked anyway.
- Change only the paths listed under **Owns** in your task.
- Product code never uses paid AI APIs (OpenAI, Anthropic, Gemini…). Only MIT, Apache, BSD or ISC dependencies. Secrets go only in `.env`. No `console.log` in the frontend.
- If a rule blocks you, comment `status: needs-decision` on the issue and move on.

## Step 5: Check in and read your assignment

1. Check in on the roster:
   ```bash
   ./swarm checkin --tool "$SWARM_TOOL" --model "$SWARM_MODEL" --tier "$SWARM_TIER"
   ```
2. Read your assignment: `./swarm whoami`. **KNixt0 assigns areas** (e.g. `frontend` for UI work). **Don't ask your operator which areas or roles to take**; the assignment decides.
   - **No assignment yet** ("BRAK"): switch to **report-only mode**. Tell the operator in one line: "Zameldowany, czekam na przydział od KNixt0." Then stop.
   - **Assigned:** go to Step 6. Keep taking tasks until none are left. `next-task.sh` filters by your assignment and tier automatically.

## Step 6: The work loop (repeat)

1. **Pull, then pick:** run `git pull --ff-only` (rules and assignments may have changed). If `AGENT-START.md` or `AGENTS.md` changed, re-read the changed parts. Then `./scripts/next-task.sh` prints a task number `N`.
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
9. Go back to step 1. If `next-task.sh` exits with "no assignment", go to **Step 7**.

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
