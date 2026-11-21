#!/usr/bin/env bash
# Usage: 04-allow-ip.sh <ip-or-cidr>   Adds another allowed source for ports 22 and 80.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

need az python3
[ $# -eq 1 ] || die "usage: $0 <ip-or-cidr>"
cidr="$(normalize_cidr "$1")"
valid_cidr "$cidr" || die "invalid CIDR: $cidr"
if [ "$cidr" = "0.0.0.0/0" ] && [ "$AZ_ALLOW_PUBLIC" != "yes" ]; then
  die "0.0.0.0/0 exposes the dashboard (no login) to everyone. Set AZ_ALLOW_PUBLIC=yes to accept."
fi
require_login

rule_json="$(az network nsg rule show -g "$AZ_RESOURCE_GROUP" --nsg-name "$NSG_NAME" -n allow-ssh-http -o json)" \
  || die "rule allow-ssh-http not found; run 01-provision.sh"
prefixes=()
while IFS= read -r p; do [ -n "$p" ] && prefixes+=("$p"); done < <(
  printf '%s' "$rule_json" | python3 -c 'import json,sys; r=json.load(sys.stdin); l=r.get("sourceAddressPrefixes") or [r.get("sourceAddressPrefix")]; print("\n".join(x for x in l if x))')
for p in "${prefixes[@]}"; do
  [ "$p" = "$cidr" ] && { echo "$cidr already allowed."; exit 0; }
done
prefixes+=("$cidr")
az network nsg rule update -g "$AZ_RESOURCE_GROUP" --nsg-name "$NSG_NAME" -n allow-ssh-http \
  --source-address-prefixes "${prefixes[@]}" -o none
echo "Allowed now: ${prefixes[*]}"
