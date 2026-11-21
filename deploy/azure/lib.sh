#!/usr/bin/env bash
# Shared helpers, sourced by the numbered scripts. Not meant to be run directly.
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/../.." && pwd)"

# Optional config file (never contains secrets).
if [ -f "$DEPLOY_DIR/config.env" ]; then
  # shellcheck disable=SC1091
  set -a; . "$DEPLOY_DIR/config.env"; set +a
fi

: "${AZ_LOCATION:=polandcentral}"
: "${AZ_RESOURCE_GROUP:=rg-investwatch-demo}"
: "${AZ_VM_NAME:=vm-investwatch}"
: "${AZ_VM_SIZE:=Standard_D4s_v5}"
: "${AZ_ADMIN_USER:=azureuser}"
: "${AZ_SSH_KEY:=$HOME/.ssh/id_rsa.pub}"
: "${AZ_ALLOW_CIDR:=}"
: "${AZ_ALLOW_PUBLIC:=no}"
: "${AZ_OS_DISK_GB:=64}"
: "${ENABLE_LLM:=no}"
: "${OLLAMA_MODEL:=gemma4:e4b}"
: "${AZ_SUBSCRIPTION:=}"
: "${CONFIRM:=no}"

NSG_NAME="${AZ_VM_NAME}-nsg"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)

die() { echo "ERROR: $*" >&2; exit 1; }

need() {
  local t
  for t in "$@"; do
    command -v "$t" >/dev/null 2>&1 || die "missing required tool: $t"
  done
}

require_login() {
  az account show >/dev/null 2>&1 || die "not logged in to Azure. Run: az login"
  if [ -n "$AZ_SUBSCRIPTION" ]; then
    az account set --subscription "$AZ_SUBSCRIPTION" || die "cannot select subscription '$AZ_SUBSCRIPTION'"
  fi
}

# Ask for confirmation unless CONFIRM=yes.
confirm() {
  [ "$CONFIRM" = "yes" ] && return 0
  [ -t 0 ] || die "non-interactive shell: set CONFIRM=yes to proceed"
  local ans
  read -r -p "$1 Type 'yes' to continue: " ans
  [ "$ans" = "yes" ] || die "aborted"
}

normalize_cidr() {
  case "$1" in
    */*) printf '%s' "$1" ;;
    *) printf '%s/32' "$1" ;;
  esac
}

valid_cidr() {
  [[ "$1" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}/[0-9]{1,2}$ ]]
}

detect_public_ip() {
  local ip
  for url in https://api.ipify.org https://ifconfig.me/ip; do
    ip="$(curl -fsS --max-time 10 "$url" 2>/dev/null || true)"
    if [[ "$ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
      printf '%s' "$ip"; return 0
    fi
  done
  return 1
}

vm_ip() {
  az vm show -d -g "$AZ_RESOURCE_GROUP" -n "$AZ_VM_NAME" --query publicIps -o tsv 2>/dev/null
}

# Private key path matching AZ_SSH_KEY (strip .pub); empty means use ssh defaults.
ssh_identity_args() {
  local priv="${AZ_SSH_KEY%.pub}"
  if [ -f "$priv" ]; then printf '%s\n' -i "$priv"; fi
}

run_ssh() {
  local ip="$1"; shift
  local id=()
  while IFS= read -r l; do id+=("$l"); done < <(ssh_identity_args)
  ssh "${SSH_OPTS[@]}" "${id[@]}" "$AZ_ADMIN_USER@$ip" "$@"
}

run_scp() {
  local id=()
  while IFS= read -r l; do id+=("$l"); done < <(ssh_identity_args)
  scp "${SSH_OPTS[@]}" "${id[@]}" "$@"
}
