#!/usr/bin/env bash
# Provision an ephemeral AWS EC2 host with a real libvirt/QEMU daemon, run the
# guest-certified realization proof (ASR-519, issue #715) against it through the
# production apply path, pull back the redaction-safe machine-readable evidence
# artifact, then tear everything down. This is the guest-observed counterpart to
# run_aws_smoke.sh (which proves daemon-level reconciliation with a cirros disk).
#
# Usage:
#   AWS_PROFILE=proof AWS_REGION=us-east-2 tools/real-daemon/run_aws_guest_certify.sh [--keep]
#
#   --keep   leave the instance running (skip teardown) for manual poking.
#
# On success the emitted evidence JSON is copied to
#   tools/real-daemon/evidence/guest-certified-<run-id>.json
# The instance uses TCG (software emulation); no bare-metal/nested-virt needed.
set -euo pipefail

PROFILE="${AWS_PROFILE:-proof}"
REGION="${AWS_REGION:-us-east-2}"
INSTANCE_TYPE="${INSTANCE_TYPE:-c5.2xlarge}"
RUN_ID="${RUN_ID:-aws-guest-certified}"
KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$(mktemp -d)"
KEY="$WORK/raes-guest-test.pem"
NAME="raes-guest-certify-test"
AWS=(aws --profile "$PROFILE" --region "$REGION")

cleanup_aws() {
  [ "$KEEP" = "1" ] && { echo "--keep: leaving instance ${IID:-?} (${IP:-?}) up"; return; }
  echo "=== teardown ==="
  [ -n "${IID:-}" ] && "${AWS[@]}" ec2 terminate-instances --instance-ids "$IID" >/dev/null 2>&1 || true
  [ -n "${IID:-}" ] && "${AWS[@]}" ec2 wait instance-terminated --instance-ids "$IID" 2>/dev/null || true
  [ -n "${SG:-}" ] && "${AWS[@]}" ec2 delete-security-group --group-id "$SG" >/dev/null 2>&1 || true
  "${AWS[@]}" ec2 delete-key-pair --key-name "$NAME" >/dev/null 2>&1 || true
  echo "torn down."
}
trap cleanup_aws EXIT

echo "=== identity ==="; "${AWS[@]}" sts get-caller-identity --query Account --output text

AMI=$("${AWS[@]}" ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text)
MYIP=$(curl -s https://checkip.amazonaws.com)
VPC=$("${AWS[@]}" ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SUBNET=$("${AWS[@]}" ec2 describe-subnets --filters Name=default-for-az,Values=true --query 'Subnets[0].SubnetId' --output text)

"${AWS[@]}" ec2 delete-key-pair --key-name "$NAME" >/dev/null 2>&1 || true
"${AWS[@]}" ec2 create-key-pair --key-name "$NAME" --query KeyMaterial --output text > "$KEY"
chmod 600 "$KEY"

SG=$("${AWS[@]}" ec2 create-security-group --group-name "$NAME-sg" --description "raes guest-certify proof" --vpc-id "$VPC" --query GroupId --output text 2>/dev/null \
  || "${AWS[@]}" ec2 describe-security-groups --filters Name=group-name,Values="$NAME-sg" --query 'SecurityGroups[0].GroupId' --output text)
"${AWS[@]}" ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 22 --cidr "$MYIP/32" >/dev/null 2>&1 || true

cat > "$WORK/userdata.sh" <<'UD'
#!/bin/bash
set -x
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y qemu-system-x86 qemu-utils libvirt-daemon-system libvirt-clients libvirt-dev genisoimage python3-dev pkg-config build-essential curl rsync busybox-static cpio
systemctl enable --now libvirtd
usermod -aG libvirt,kvm ubuntu
# The guest-observing appliance builder defaults to /usr/bin/busybox.
[ -x /usr/bin/busybox ] || ln -sf "$(command -v busybox)" /usr/bin/busybox
# test-host libvirt config so boot artifacts + the guest fact channel outside
# /var/lib/libvirt/images are readable/writable by the qemu process.
sed -i 's/^#*security_driver *=.*/security_driver = "none"/' /etc/libvirt/qemu.conf
grep -q '^security_driver' /etc/libvirt/qemu.conf || echo 'security_driver = "none"' >> /etc/libvirt/qemu.conf
sed -i 's/^#*user *=.*/user = "root"/; s/^#*group *=.*/group = "root"/' /etc/libvirt/qemu.conf
systemctl restart libvirtd
touch /var/lib/cloud/userdata-done
UD

IID=$("${AWS[@]}" ec2 run-instances --image-id "$AMI" --instance-type "$INSTANCE_TYPE" \
  --key-name "$NAME" --security-group-ids "$SG" --subnet-id "$SUBNET" --associate-public-ip-address \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=30,VolumeType=gp3}' \
  --user-data "file://$WORK/userdata.sh" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME}]" \
  --query 'Instances[0].InstanceId' --output text)
echo "instance: $IID"
"${AWS[@]}" ec2 wait instance-running --instance-ids "$IID"
IP=$("${AWS[@]}" ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "public ip: $IP"

SSHOPT=(-i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15)
echo "=== wait for ssh + userdata ==="
for _ in $(seq 1 40); do ssh "${SSHOPT[@]}" ubuntu@"$IP" "test -f /var/lib/cloud/userdata-done" 2>/dev/null && break; sleep 10; done

echo "=== deploy code ==="
ssh "${SSHOPT[@]}" ubuntu@"$IP" "mkdir -p /home/ubuntu/raes/implementations/python /home/ubuntu/raes/contracts /home/ubuntu/raes/examples"
rsync -az --delete --exclude '.venv' --exclude '__pycache__' --exclude '.git' --exclude '.pytest_cache' --exclude '.nox' --exclude '*.pyc' \
  -e "ssh ${SSHOPT[*]}" "$REPO_ROOT/implementations/python/" ubuntu@"$IP":/home/ubuntu/raes/implementations/python/
rsync -az --delete --exclude '.git' -e "ssh ${SSHOPT[*]}" "$REPO_ROOT/contracts/" ubuntu@"$IP":/home/ubuntu/raes/contracts/
rsync -az --delete --exclude '.git' -e "ssh ${SSHOPT[*]}" "$REPO_ROOT/examples/" ubuntu@"$IP":/home/ubuntu/raes/examples/
scp "${SSHOPT[@]}" "$REPO_ROOT/.ground-control.yaml" ubuntu@"$IP":/home/ubuntu/raes/.ground-control.yaml
# The editable build (hatch_build.py) reads the repo-root README for packaging.
scp "${SSHOPT[@]}" "$REPO_ROOT/README.md" ubuntu@"$IP":/home/ubuntu/raes/README.md

echo "=== install venv + libvirt-python ==="
ssh "${SSHOPT[@]}" ubuntu@"$IP" "curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; cd ~/raes/implementations/python && ~/.local/bin/uv sync --all-extras >/dev/null 2>&1 && ~/.local/bin/uv pip install libvirt-python >/dev/null 2>&1 && echo venv-ready"

echo "=== run guest-certified proof ==="
ssh "${SSHOPT[@]}" ubuntu@"$IP" "sudo bash -lc 'cd /home/ubuntu/raes && implementations/python/.venv/bin/python -c \"
from pathlib import Path
from raes_operations.libvirt_evidence_run import run_libvirt_evidence_run, LibvirtEvidenceRunConfig
r = run_libvirt_evidence_run(scenario_path=Path(\\\"examples/scenarios/techvault-guest-certified.sdl.yaml\\\").resolve(), project_dir=Path(\\\"/home/ubuntu/raes/gc-out\\\"), run_id=\\\"$RUN_ID\\\", config=LibvirtEvidenceRunConfig(evidence_source_mode=\\\"guest-certified\\\", connection_uri=\\\"qemu:///system\\\"))
print(r.render())
import sys; sys.exit(0 if r.passed else 1)
\"'"

echo "=== pull evidence artifact ==="
ssh "${SSHOPT[@]}" ubuntu@"$IP" "sudo chown -R ubuntu /home/ubuntu/raes/gc-out 2>/dev/null || true"
mkdir -p "$REPO_ROOT/tools/real-daemon/evidence"
scp "${SSHOPT[@]}" ubuntu@"$IP":/home/ubuntu/raes/gc-out/runs/"$RUN_ID"/scenario-evidence/libvirt-scenario-evidence-run.json \
  "$REPO_ROOT/tools/real-daemon/evidence/guest-certified-$RUN_ID.json"
echo "pulled: tools/real-daemon/evidence/guest-certified-$RUN_ID.json"
