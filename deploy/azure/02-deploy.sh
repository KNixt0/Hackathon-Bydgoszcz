#!/usr/bin/env bash
# Ships the current git HEAD to the VM and starts the compose stack.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

need az ssh scp git
require_login

ip="$(vm_ip)"
[ -n "$ip" ] || die "VM $AZ_VM_NAME not found in $AZ_RESOURCE_GROUP. Run 01-provision.sh first."

archive="$(mktemp -t investwatch.XXXXXX)"
trap 'rm -f "$archive"' EXIT
git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1 || die "$REPO_ROOT is not a git repository"
git -C "$REPO_ROOT" archive --format=tar.gz -o "$archive" HEAD
echo "Archive of HEAD created ($(du -h "$archive" | cut -f1)). Uncommitted changes are NOT included."

run_scp "$archive" "$AZ_ADMIN_USER@$ip:/tmp/investwatch.tar.gz"

# Everything below runs on the VM. Variables are passed as arguments, secrets are generated there.
run_ssh "$ip" bash -s -- "$ENABLE_LLM" "$OLLAMA_MODEL" <<'REMOTE'
set -euo pipefail
ENABLE_LLM="$1"; OLLAMA_MODEL="$2"
APP="$HOME/investwatch"
docker compose version >/dev/null || { echo "docker compose not available yet (log out/in or wait for cloud-init)"; exit 1; }

mkdir -p "$APP"
# Keep the existing .env (so database credentials stay valid across redeploys).
[ -f "$APP/.env" ] && cp "$APP/.env" /tmp/investwatch.env.keep
tar -xzf /tmp/investwatch.tar.gz -C "$APP"
rm -f /tmp/investwatch.tar.gz
cd "$APP"

if [ -f /tmp/investwatch.env.keep ]; then
  mv /tmp/investwatch.env.keep .env
else
  cp .env.example .env
  set_var() { sed -i "s|^$1=.*|$1=$2|" .env; }
  set_var POSTGRES_PASSWORD "$(openssl rand -hex 24)"
  set_var S3_ACCESS_KEY "$(openssl rand -hex 10)"
  set_var S3_SECRET_KEY "$(openssl rand -hex 24)"
  chmod 600 .env
fi
sed -i "s|^FRONTEND_PORT=.*|FRONTEND_PORT=80|" .env

if [ "$ENABLE_LLM" = "yes" ]; then
  sed -i "s|^LLM_ENABLED=.*|LLM_ENABLED=true|; s|^OLLAMA_URL=.*|OLLAMA_URL=http://ollama:11434|; s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$OLLAMA_MODEL|; s|^EMBEDDINGS_BACKEND=.*|EMBEDDINGS_BACKEND=ollama|" .env
  profile=(--profile llm)
else
  profile=()
fi

C=(docker compose "${profile[@]}" -f docker-compose.yml -f deploy/azure/compose.azure.yml)
"${C[@]}" up -d --build

if [ "$ENABLE_LLM" = "yes" ]; then
  embed="$(sed -n 's|^OLLAMA_EMBED_MODEL=||p' .env)"
  "${C[@]}" exec -T ollama ollama pull "$OLLAMA_MODEL"
  [ -z "$embed" ] || "${C[@]}" exec -T ollama ollama pull "$embed"
  "${C[@]}" up -d
fi

echo "Waiting for /api/health ..."
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1/api/health >/dev/null 2>&1; then echo "healthy"; exit 0; fi
  sleep 5
done
echo "health check timed out"; "${C[@]}" ps; exit 1
REMOTE

echo "Done: http://$ip/  (reachable only from the allowed CIDR)"
