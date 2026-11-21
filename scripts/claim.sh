#!/usr/bin/env bash
# Claim an issue: lock it (assignee), relabel, create branch + worktree.
# usage: scripts/claim.sh <issue> [agent-name]
# prints: WORKTREE=<path> BRANCH=<name>
set -euo pipefail

issue="${1:?usage: claim.sh <issue> [agent-name]}"
agent="${2:-${SWARM_AGENT:-claude}}"
me=$(gh api user --jq .login)
root=$(git rev-parse --show-toplevel)

assignees() { gh issue view "$issue" --json assignees --jq '[.assignees[].login] | sort | join(" ")'; }

current=$(assignees)
if [[ -n "$current" && "$current" != "$me" ]]; then
  echo "issue #$issue already taken by: $current" >&2; exit 1
fi
if ! gh issue view "$issue" --json labels --jq '.labels[].name' | grep -qx "status:ready"; then
  if [[ "$current" != "$me" ]]; then echo "issue #$issue is not status:ready" >&2; exit 1; fi
fi

gh issue edit "$issue" --add-assignee "$me" --add-label "status:claimed" --remove-label "status:ready" >/dev/null

# Race check: if someone claimed at the same moment, alphabetically-first login keeps it.
sleep 2
current=$(assignees)
winner=$(echo "$current" | tr ' ' '\n' | head -n1)
if [[ "$winner" != "$me" ]]; then
  gh issue edit "$issue" --remove-assignee "$me" >/dev/null
  echo "lost claim race for #$issue to $winner" >&2; exit 1
fi

branch="agent/$me/$issue"
wt="$root/.worktrees/$issue"
git -C "$root" fetch -q origin
if [[ ! -d "$wt" ]]; then
  if git -C "$root" show-ref -q "refs/remotes/origin/$branch"; then
    git -C "$root" worktree add -q "$wt" -B "$branch" "origin/$branch"
  else
    git -C "$root" worktree add -q "$wt" -b "$branch" origin/main
  fi
fi

gh issue comment "$issue" --body "$(cat <<EOF
Claimed.
\`\`\`yaml
status: claimed
agent: $me/$agent
issue: $issue
changed: []
contracts_touched: none
blockers: []
next: "working on branch $branch"
\`\`\`
EOF
)" >/dev/null

echo "WORKTREE=$wt"
echo "BRANCH=$branch"
