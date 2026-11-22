#!/usr/bin/env bash
# Native local AI using the already installed Ollama model. No cloud service or automatic model download.
set -euo pipefail
service_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$service_dir"
export LLM_ENABLED=true
export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-gemma4:e4b}"
export LLM_TIMEOUT_S="${LLM_TIMEOUT_S:-180}"
export AI_DEMO_OVERLAY="${AI_DEMO_OVERLAY:-false}"
export EMBEDDINGS_BACKEND="${EMBEDDINGS_BACKEND:-hash}"
if [[ ! -x .venv/bin/python ]]; then
  if command -v uv >/dev/null; then
    uv venv --python 3.12 .venv
    uv pip install -p .venv/bin/python -r requirements.txt
  else
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
  fi
fi
.venv/bin/python scripts/check_local_model.py
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${AI_PORT:-8001}"
