#!/usr/bin/env bash
# Print the number of the next claimable issue for this agent. Exit 1 if none.
# Order: tasks reserved for me (assigned to my login) → strong tasks if my tier is strong
#        → prio:high → oldest. Tier filter (SWARM_TIER, default standard):
#   strong   : everything
#   standard : everything except model:opus
#   light    : only size:xs
# Area filter (SWARM_AREAS, comma separated, default: all): only tasks with one of
#   the labels area:<name>. Aliases: ui → frontend, api → backend, model → ai.
#   e.g. SWARM_AREAS=ui,docs ./scripts/next-task.sh
set -euo pipefail

me=$(gh api user --jq .login)
tier="${SWARM_TIER:-standard}"
areas="${SWARM_AREAS:-}"

candidates=$(gh issue list --state open --label "status:ready" --limit 100 \
  --json number,assignees,labels,createdAt \
  | python3 -c '
import json, sys
me, tier, areas = sys.argv[1], sys.argv[2], sys.argv[3]
alias = {"ui": "frontend", "front": "frontend", "api": "backend", "back": "backend", "model": "ai", "ml": "ai", "ops": "devops"}
want = {"area:" + alias.get(a.strip().lower(), a.strip().lower()) for a in areas.split(",") if a.strip()}
out = []
for i in json.load(sys.stdin):
    a = [x["login"] for x in i["assignees"]]
    L = {l["name"] for l in i["labels"]}
    if a and a != [me]:
        continue                      # someone else has it / reserved for someone else
    if tier == "light" and "size:xs" not in L:
        continue
    if tier == "standard" and "model:opus" in L:
        continue
    if want and not (want & L) and a != [me]:
        continue                      # not my area (tasks reserved for me always pass)
    key = (0 if a == [me] else 1,
           0 if tier == "strong" and "model:opus" in L else 1,
           0 if "prio:high" in L else 1,
           i["createdAt"])
    out.append((key, i["number"]))
print("\n".join(str(n) for _, n in sorted(out)))
' "$me" "$tier" "$areas")

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

echo "no claimable issue for tier $tier${areas:+, areas $areas}" >&2
exit 1
