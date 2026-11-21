#!/usr/bin/env bash
# Creates the resource group, VM, NSG (22 + 80 from AZ_ALLOW_CIDR only) and installs Docker via cloud-init.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

need az ssh scp git curl
require_login

if [ -z "$AZ_ALLOW_CIDR" ]; then
  ip="$(detect_public_ip)" || die "cannot detect your public IP; set AZ_ALLOW_CIDR=<ip>/32"
  AZ_ALLOW_CIDR="$ip/32"
fi
AZ_ALLOW_CIDR="$(normalize_cidr "$AZ_ALLOW_CIDR")"
valid_cidr "$AZ_ALLOW_CIDR" || die "invalid AZ_ALLOW_CIDR: $AZ_ALLOW_CIDR"
if [ "$AZ_ALLOW_CIDR" = "0.0.0.0/0" ] && [ "$AZ_ALLOW_PUBLIC" != "yes" ]; then
  die "0.0.0.0/0 exposes a dashboard WITHOUT login to the internet. Set AZ_ALLOW_PUBLIC=yes to accept."
fi

sub_name="$(az account show --query name -o tsv)"
cat <<PLAN
Plan (nothing is created until you confirm):
  subscription : $sub_name
  region       : $AZ_LOCATION
  resource grp : $AZ_RESOURCE_GROUP (tag project=investwatch)
  VM           : $AZ_VM_NAME, $AZ_VM_SIZE, Ubuntu 24.04 LTS, ${AZ_OS_DISK_GB} GB disk, SSH key only
  NSG          : ports 22 and 80 from $AZ_ALLOW_CIDR only
  SSH key      : $AZ_SSH_KEY (generated if missing)
  LLM          : $ENABLE_LLM (size matters; see config.example.env)
The VM bills while it is running. Check the Azure pricing calculator for your region and size.
PLAN
confirm "Create these resources?"

tmp_ci="$(mktemp)"
trap 'rm -f "$tmp_ci"' EXIT
sed "s/__ADMIN_USER__/$AZ_ADMIN_USER/g" "$DEPLOY_DIR/cloud-init.yaml" > "$tmp_ci"

az group create -n "$AZ_RESOURCE_GROUP" -l "$AZ_LOCATION" --tags project=investwatch -o none
echo "Resource group ready."

if az vm show -g "$AZ_RESOURCE_GROUP" -n "$AZ_VM_NAME" >/dev/null 2>&1; then
  echo "VM $AZ_VM_NAME already exists, skipping creation."
else
  key_args=(--generate-ssh-keys)
  if [ -f "$AZ_SSH_KEY" ]; then key_args=(--ssh-key-values "$AZ_SSH_KEY"); fi
  az vm create \
    -g "$AZ_RESOURCE_GROUP" -n "$AZ_VM_NAME" -l "$AZ_LOCATION" \
    --image Canonical:ubuntu-24_04-lts:server:latest \
    --size "$AZ_VM_SIZE" \
    --os-disk-size-gb "$AZ_OS_DISK_GB" \
    --admin-username "$AZ_ADMIN_USER" \
    "${key_args[@]}" \
    --authentication-type ssh \
    --public-ip-sku Standard \
    --nsg "$NSG_NAME" --nsg-rule NONE \
    --custom-data "$tmp_ci" \
    --tags project=investwatch \
    -o none
fi

# NSG rules: only the allowed source gets 22 and 80.
az network nsg rule create -g "$AZ_RESOURCE_GROUP" --nsg-name "$NSG_NAME" -n allow-ssh-http \
  --priority 1000 --direction Inbound --access Allow --protocol Tcp \
  --source-address-prefixes "$AZ_ALLOW_CIDR" --destination-port-ranges 22 80 -o none
echo "NSG rule allow-ssh-http set for $AZ_ALLOW_CIDR."

ip="$(vm_ip)"
[ -n "$ip" ] || die "could not read the VM public IP"
echo "Public IP: $ip"
echo "Waiting for cloud-init to install Docker (a few minutes)..."
for _ in $(seq 1 60); do
  if run_ssh "$ip" 'test -f /var/lib/cloud/instance/investwatch-ready' 2>/dev/null; then
    echo "Docker is ready on $ip."
    echo "Next: deploy/azure/02-deploy.sh"
    exit 0
  fi
  sleep 10
done
die "timed out waiting for cloud-init; check: ssh $AZ_ADMIN_USER@$ip 'cloud-init status --long'"
