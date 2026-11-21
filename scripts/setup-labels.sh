#!/usr/bin/env bash
# Create (or update) the swarm labels. Run once per repo.
set -euo pipefail

create() { gh label create "$1" --color "$2" --description "$3" --force >/dev/null && echo "label: $1"; }

create "status:ready"          "0e8a16" "Specified and free to claim"
create "status:claimed"        "fbca04" "Being worked on (assignee is the lock)"
create "status:review"         "1d76db" "PR open, waiting for review"
create "status:blocked"        "b60205" "Waiting on another issue (Depends on:)"
create "status:needs-decision" "d93f0b" "A human must decide (contract/scope)"
create "prio:high"             "5319e7" "Critical path, picked first"
create "needs:owner-review"    "e99695" "Waiting for KNixt0 approval before merge"
create "model:opus"            "8250df" "Hard task: builder runs on Opus, effort high"
create "size:xs"               "c2e0c6" "Small task: builder runs on Haiku, effort low"
create "swarm:roster"          "0052cc" "The single agent roster issue (check-ins)"
create "area:frontend"         "1f6feb" "UI / dashboard (services/frontend)"
create "area:backend"          "0e8a16" "Scraping, queue, API (services/backend)"
create "area:ai"               "8250df" "Preprocessing, local model, scoring (services/ai)"
create "area:devops"           "6e7781" "Docker compose, CI, security scans"
create "area:docs"             "c5def5" "README, presentation, AI process doc"
