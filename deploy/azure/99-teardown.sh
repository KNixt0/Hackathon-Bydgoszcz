#!/usr/bin/env bash
# Deletes the whole resource group (VM, disk, IP, NSG). Irreversible.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

need az
require_login
az group show -n "$AZ_RESOURCE_GROUP" >/dev/null 2>&1 || die "resource group $AZ_RESOURCE_GROUP does not exist"
echo "Will permanently delete resource group $AZ_RESOURCE_GROUP and everything in it:"
az resource list -g "$AZ_RESOURCE_GROUP" --query '[].{name:name,type:type}' -o table
echo "All data on the VM (database, archived evidence) will be lost."
confirm "Delete $AZ_RESOURCE_GROUP?"
az group delete -n "$AZ_RESOURCE_GROUP" --yes --no-wait
echo "Deletion started (runs in the background)."
