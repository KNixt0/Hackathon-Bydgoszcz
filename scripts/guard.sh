#!/usr/bin/env bash
# Enforce the checkable rules from coord/GUIDELINES.md. Runs in check.sh and CI.
# Fast and dependency-free (grep + git). License/vulnerability scans live in CI (security.yml).
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

fail=0
bad() { printf '✗ %s\n' "$1"; [[ -n "${2:-}" ]] && printf '%s\n' "$2" | sed 's/^/    /' | head -20; fail=1; }
good() { printf '✓ %s\n' "$1"; }
EXCL=(--exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=venv --exclude-dir=dist --exclude-dir=build --exclude-dir=.next --exclude-dir=__pycache__)

# 1. No paid / external AI APIs in product code (GUIDELINES #1)
if [[ -d services ]]; then
  hits=$(grep -rInE "${EXCL[@]}" \
    -e 'api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com|api\.cohere\.(ai|com)|api\.mistral\.ai' \
    -e '^[[:space:]]*(from|import)[[:space:]]+(openai|anthropic|google\.generativeai|google\.genai|cohere|mistralai)\b' \
    -e '"(openai|@anthropic-ai/[a-z-]+|@google/generative-ai|@google/genai|cohere-ai|@mistralai/mistralai)"[[:space:]]*:' \
    -e '^(openai|anthropic|google-generativeai|google-genai|cohere|mistralai)([<>=~! ]|$)' \
    services 2>/dev/null)
  [[ -z "$hits" ]] && good "brak płatnych API AI w services/" || bad "płatne/zewnętrzne API AI w kodzie produktu (zakaz)" "$hits"
else
  good "brak katalogu services/ (jeszcze nic do sprawdzenia)"
fi

# 2. No committed .env files except .env.example (GUIDELINES #4)
envs=$(git ls-files | grep -E '(^|/)\.env(\.|$)' | grep -vE '\.env\.example$' || true)
[[ -z "$envs" ]] && good "brak commitowanych plików .env" || bad "plik .env w repo (tylko .env.example jest dozwolony)" "$envs"

# 3. Obvious secrets in tracked files (full scan: gitleaks in CI)
secrets=$(git grep -InE \
  -e '(sk-(ant-)?[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})' \
  -e '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----' \
  -- ':!*.md' ':!scripts/guard.sh' 2>/dev/null || true)
[[ -z "$secrets" ]] && good "brak oczywistych sekretów" || bad "wygląda na sekret w kodzie" "$secrets"

# 4. No console.log in frontend code (GUIDELINES #6)
if [[ -d services/frontend ]]; then
  logs=$(grep -rInE "${EXCL[@]}" --include='*.js' --include='*.jsx' --include='*.ts' --include='*.tsx' --include='*.vue' \
    'console\.(log|debug)\(' services/frontend 2>/dev/null || true)
  [[ -z "$logs" ]] && good "brak console.log we froncie" || bad "console.log we froncie (kryterium Console.log)" "$logs"
fi

# 5. Each service has its own Dockerfile + compose exists (GUIDELINES #3)
if [[ -d services ]]; then
  for s in services/*/; do
    [[ -f "$s/Dockerfile" ]] || bad "brak Dockerfile w $s"
  done
  [[ -f docker-compose.yml || -f compose.yml || -f docker-compose.yaml || -f compose.yaml ]] \
    && good "docker compose obecny" || bad "brak docker-compose.yml (wymóg: jedna komenda docker compose up)"
  [[ -f .env.example ]] || bad "brak .env.example"
fi

exit $fail
