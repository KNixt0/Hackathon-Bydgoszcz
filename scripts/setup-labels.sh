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
