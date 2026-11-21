#!/usr/bin/env bash
# Headless worker for ANY AI coding tool: take the next task for my tier, claim it,
# check in on the roster, run the tool, check in again. Repeat with --loop.
#
# usage: scripts/worker.sh [--loop]
# env:
#   SWARM_TOOL   claude (default) | codex | gemini | custom
#   SWARM_MODEL  model name (Claude: from coord/roles.json per task labels if unset)
#   SWARM_TIER   strong | standard | light   (decides which tasks you may take)
#   SWARM_CMD    for SWARM_TOOL=custom: command; the prompt arrives on stdin
#                e.g. SWARM_CMD='aider --yes --message-file /dev/stdin'
# Flags for codex/gemini follow their CLIs at the time of writing; check `codex exec --help`
# and `gemini --help` for your version.
set -euo pipefail

loop=0
[[ "${1:-}" == "--loop" ]] && { loop=1; shift; }
tool="${SWARM_TOOL:-claude}"
root=$(git rev-parse --show-toplevel)
cd "$root"

if [[ -z "${SWARM_TIER:-}" ]]; then
  case "$tool:${SWARM_MODEL:-}" in
    claude:|claude:*sonnet*) export SWARM_TIER=standard ;;
    *opus*|*pro*) export SWARM_TIER=strong ;;
    *haiku*) export SWARM_TIER=light ;;
    *) export SWARM_TIER=standard ;;
  esac
fi

run_tool() {  # <model> <effort> <prompt>   (cwd = worktree)
  local m="$1" e="$2" p="$3"
  case "$tool" in
    claude) claude -p "$p" --permission-mode acceptEdits --model "$m" --effort "$e" ;;
    codex)  codex exec --full-auto ${m:+-m "$m"} "$p" ;;
    gemini) gemini --yolo ${m:+-m "$m"} -p "$p" ;;
    custom) [[ -n "${SWARM_CMD:-}" ]] || { echo "set SWARM_CMD for SWARM_TOOL=custom" >&2; return 2; }
            printf '%s' "$p" | bash -c "$SWARM_CMD" ;;
    *) echo "unknown SWARM_TOOL=$tool" >&2; return 2 ;;
  esac
}

run_one() {
  local issue out wt branch prompt labels model effort
  issue=$(./scripts/next-task.sh) || return 1
  out=$(./scripts/claim.sh "$issue" "$tool") || return 2
  wt=$(sed -n 's/^WORKTREE=//p' <<<"$out")
  branch=$(sed -n 's/^BRANCH=//p' <<<"$out")
  labels=$(gh issue view "$issue" --json labels --jq '[.labels[].name] | join(",")')

  if [[ "$tool" == "claude" && -z "${SWARM_MODEL:-}" ]]; then
    read -r model effort < <(python3 scripts/roles.py builder "$labels")
  else
    model="${SWARM_MODEL:-}"; effort="${SWARM_EFFORT:-medium}"
  fi
  prompt=$(sed -e "s|{{ISSUE}}|$issue|g" -e "s|{{BRANCH}}|$branch|g" \
               -e "s|{{AGENT}}|$(gh api user --jq .login)/$tool-${model:-unknown}|g" \
               -e "s|{{MODEL}}|${model:-unknown}|g" coord/prompts/worker.md)

  SWARM_MODEL="$model" ./scripts/checkin.sh --status busy --issue "$issue" >/dev/null || true
  echo "▶ #$issue in $wt ($branch) · $tool ${model:-default}/$effort · tier $SWARM_TIER"
  (cd "$wt" && run_tool "$model" "$effort" "$prompt") || echo "tool exited with an error on #$issue" >&2
  SWARM_MODEL="$model" ./scripts/checkin.sh --status online >/dev/null || true
  echo "■ #$issue finished"
}

while true; do
  rc=0; run_one || rc=$?
  if [[ $rc == 1 ]]; then
    [[ $loop == 1 ]] || exit 0
    echo "nothing for tier $SWARM_TIER, waiting 60s…"; sleep 60
  elif [[ $rc == 2 ]]; then
    sleep 5   # lost a claim race, try the next one
  else
    [[ $loop == 1 ]] || exit 0
  fi
done
