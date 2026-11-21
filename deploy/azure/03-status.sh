#!/usr/bin/env bash
# Shows VM state, containers, health and the allowed source ranges.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

need az ssh scp
require_login

echo "== VM =="
az vm show -d -g "$AZ_RESOURCE_GROUP" -n "$AZ_VM_NAME" --query '{name:name,state:powerState,size:hardwareProfile.vmSize,ip:publicIps}' -o table
echo "== Allowed sources (NSG) =="
az network nsg rule list -g "$AZ_RESOURCE_GROUP" --nsg-name "$NSG_NAME" \
  --query '[].{rule:name,from:sourceAddressPrefix,froms:sourceAddressPrefixes,ports:destinationPortRanges}' -o json
ip="$(vm_ip)"
[ -n "$ip" ] || die "no public IP (VM deallocated?)"
echo "== Containers =="
run_ssh "$ip" 'cd ~/investwatch && docker compose -f docker-compose.yml -f deploy/azure/compose.azure.yml --profile llm ps' || true
echo "== Health =="
run_ssh "$ip" 'curl -fsS http://127.0.0.1/api/health' || echo "health check failed"
echo
echo "URL: http://$ip/"
