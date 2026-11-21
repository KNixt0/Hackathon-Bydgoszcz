#!/usr/bin/env bash
# Single entry point for tests + lint. CI and every agent run this.
# The skeleton issue adds the real per-service test commands below the guard.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

bash scripts/guard.sh

# TODO (skeleton issue): per-service tests, e.g.
#   (cd services/backend && pytest -q)
#   (cd services/ai && pytest -q)
#   (cd services/frontend && npm test -- --run && npx eslint . --max-warnings 0)
