#!/usr/bin/env bash
# Post this agent's check-in block on the roster issue (label swarm:roster).
# usage: scripts/checkin.sh [--status online|busy|offline] [--issue N]
#                           [--tool T] [--model M] [--tier strong|standard|light] [--strengths "a,b"]
# Defaults come from env: SWARM_TOOL, SWARM_MODEL, SWARM_TIER, SWARM_STRENGTHS.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

status=online; issue=none
tool="${SWARM_TOOL:-claude}"; model="${SWARM_MODEL:-}"; tier="${SWARM_TIER:-}"; strengths="${SWARM_STRENGTHS:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --status) status="$2"; shift 2 ;;
    --issue) issue="$2"; shift 2 ;;
    --tool) tool="$2"; shift 2 ;;
    --model) model="$2"; shift 2 ;;
    --tier) tier="$2"; shift 2 ;;
    --strengths) strengths="$2"; shift 2 ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done

# Claude defaults from coord/roles.json (builder) when not given.
if [[ "$tool" == "claude" && -z "$model" ]]; then read -r model _ < <(python3 scripts/roles.py builder); fi
model="${model:-unknown}"
if [[ -z "$tier" ]]; then
  case "$model" in
    *opus*|gpt-5|gpt-5-high|*pro*) tier=strong ;;
    *haiku*|*mini-light*|*:1b*|*:3b*|*:7b*) tier=light ;;
    *) tier=standard ;;
  esac
fi

operator=$(gh api user --jq .login)
agent="$operator/$tool-$model"
roster=$(gh issue list --state open --label "swarm:roster" --limit 1 --json number --jq '.[0].number // empty')
if [[ -z "$roster" ]]; then echo "no open issue labeled swarm:roster (owner: create it)" >&2; exit 1; fi

body=$(cat <<EOF
\`\`\`yaml
checkin: $status
agent: $agent
operator: $operator
tool: $tool
model: $model
tier: $tier
strengths: [${strengths}]
working_on: $issue
\`\`\`
EOF
)
gh issue comment "$roster" --body "$body" >/dev/null
echo "checked in on #$roster as $agent ($tier, $status)"
