#!/usr/bin/env bash
# Single entry point for tests + lint. CI and every agent run this.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

bash scripts/guard.sh

py_service() { # dir
  local d="$1"
  [[ -d "$d" ]] || return 0
  echo "── $d"
  if [[ ! -x "$d/.venv/bin/python" ]]; then
    if command -v uv >/dev/null; then
      uv venv --quiet --python 3.12 "$d/.venv"
      uv pip install --quiet -p "$d/.venv/bin/python" -r "$d/requirements-dev.txt"
    else
      python3 -m venv "$d/.venv"
      "$d/.venv/bin/pip" install --quiet -r "$d/requirements-dev.txt"
    fi
  fi
  (cd "$d" && .venv/bin/ruff check . && .venv/bin/python -m pytest -q)
}

py_service services/ai
py_service services/backend

if [[ -d services/frontend ]]; then
  echo "── services/frontend"
  (cd services/frontend && { [[ -d node_modules ]] || npm ci --no-audit --no-fund; } \
    && npm run lint && npm test -- --run && npm run build)
fi
