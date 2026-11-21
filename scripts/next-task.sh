#!/usr/bin/env bash
# Print the number of the next claimable issue (status:ready, unassigned, deps closed).
# prio:high first, then oldest. Exit 1 if nothing is available.
set -euo pipefail

candidates=$(gh issue list --state open --label "status:ready" --limit 100 \
  --json number,assignees,labels,createdAt \
  --jq '[.[] | select(.assignees | length == 0)]
        | sort_by([(if any(.labels[]; .name == "prio:high") then 0 else 1 end), .createdAt])
        | .[].number')

for n in $candidates; do
  deps=$(gh issue view "$n" --json body --jq '.body' \
    | grep -iE '^[[:space:]]*depends on:' | grep -oE '#[0-9]+' | tr -d '#' || true)
  ok=1
  for d in $deps; do
    state=$(gh issue view "$d" --json state --jq '.state' 2>/dev/null || echo "OPEN")
    [[ "$state" == "CLOSED" ]] || { ok=0; break; }
  done
  if [[ $ok == 1 ]]; then echo "$n"; exit 0; fi
done

echo "no claimable issue" >&2
exit 1
