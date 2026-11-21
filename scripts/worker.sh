#!/usr/bin/env bash
# Headless worker: take the next issue, claim it, let Claude build it, repeat with --loop.
# Uses YOUR local Claude login and YOUR gh login.
# usage: scripts/worker.sh [--loop] [agent-name]
set -euo pipefail

loop=0
[[ "${1:-}" == "--loop" ]] && { loop=1; shift; }
agent="${1:-${SWARM_AGENT:-worker-$$}}"
root=$(git rev-parse --show-toplevel)
cd "$root"

run_one() {
  local issue out wt branch prompt
  issue=$(./scripts/next-task.sh) || return 1
  out=$(./scripts/claim.sh "$issue" "$agent") || return 2
  wt=$(sed -n 's/^WORKTREE=//p' <<<"$out")
  branch=$(sed -n 's/^BRANCH=//p' <<<"$out")
  prompt=$(sed -e "s|{{ISSUE}}|$issue|g" -e "s|{{BRANCH}}|$branch|g" coord/prompts/worker.md)
  # Model + effort come from coord/roles.json (builder; model:opus / size:xs labels override).
  labels=$(gh issue view "$issue" --json labels --jq '[.labels[].name] | join(",")')
  read -r model effort < <(python3 scripts/roles.py builder "$labels")

  echo "▶ #$issue in $wt ($branch) · $model/$effort"
  (cd "$wt" && claude -p "$prompt" --permission-mode acceptEdits --model "$model" --effort "$effort")
  echo "■ #$issue finished"
}

while true; do
  rc=0; run_one || rc=$?
  if [[ $rc == 1 ]]; then
    [[ $loop == 1 ]] || exit 0
    echo "nothing to do, waiting 60s…"; sleep 60
  elif [[ $rc == 2 ]]; then
    sleep 5   # lost a claim race, try the next one
  else
    [[ $loop == 1 ]] || exit 0
  fi
done
