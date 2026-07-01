#!/usr/bin/env bash
# Provision an ephemeral AWS EC2 host with a real libvirt/QEMU daemon, run the
# libvirt-backend real-daemon smoke test (tools/real-daemon/libvirt_smoke.py)
# against it, then tear everything down. Use this to periodically confirm the
# libvirt reconciliation/teardown backend actually works against real libvirtd
# (the hermetic `nox verify` graph deliberately uses in-process fakes).
#
# Usage:
#   AWS_PROFILE=aws-dev AWS_REGION=us-east-1 tools/real-daemon/run_aws_smoke.sh [--keep]
#
#   --keep   leave the instance running (skip teardown) for manual poking;
#            re-run without --keep, or delete via the printed instance id.
#
# Requirements on the caller's box: aws CLI (authenticated), ssh, rsync.
# The instance uses TCG (software emulation), so no bare-metal/nested-virt is
# needed — the driver emits <domain type="qemu">.
set -euo pipefail

PROFILE="${AWS_PROFILE:-aws-dev}"
REGION="${AWS_REGION:-us-east-1}"
INSTANCE_TYPE="${INSTANCE_TYPE:-c5.2xlarge}"
KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$(mktemp -d)"
KEY="$WORK/aces-libvirt-test.pem"
NAME="aces-libvirt-test"
AWS=(aws --profile "$PROFILE" --region "$REGION")

cleanup_aws() {
  [ "$KEEP" = "1" ] && { echo "--keep: leaving instance ${IID:-?} ($IP) up"; return; }
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

SG=$("${AWS[@]}" ec2 create-security-group --group-name "$NAME-sg" --description "aces libvirt real-daemon smoke" --vpc-id "$VPC" --query GroupId --output text 2>/dev/null \
  || "${AWS[@]}" ec2 describe-security-groups --filters Name=group-name,Values="$NAME-sg" --query 'SecurityGroups[0].GroupId' --output text)
"${AWS[@]}" ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 22 --cidr "$MYIP/32" >/dev/null 2>&1 || true

cat > "$WORK/userdata.sh" <<'UD'
#!/bin/bash
set -x
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y qemu-system-x86 qemu-utils libvirt-daemon-system libvirt-clients libvirt-dev genisoimage python3-dev pkg-config build-essential curl rsync
systemctl enable --now libvirtd
usermod -aG libvirt,kvm ubuntu
# test-host libvirt config so seeds/disks outside /var/lib/libvirt/images work
sed -i 's/^#*security_driver *=.*/security_driver = "none"/' /etc/libvirt/qemu.conf
grep -q '^security_driver' /etc/libvirt/qemu.conf || echo 'security_driver = "none"' >> /etc/libvirt/qemu.conf
sed -i 's/^#*user *=.*/user = "root"/; s/^#*group *=.*/group = "root"/' /etc/libvirt/qemu.conf
systemctl restart libvirtd
mkdir -p /var/lib/libvirt/images
curl -sL https://download.cirros-cloud.net/0.6.2/cirros-0.6.2-x86_64-disk.img -o /var/lib/libvirt/images/cirros.img || true
chmod 644 /var/lib/libvirt/images/cirros.img || true
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
for _ in $(seq 1 30); do ssh "${SSHOPT[@]}" ubuntu@"$IP" "test -f /var/lib/cloud/userdata-done" 2>/dev/null && break; sleep 10; done

echo "=== deploy code ==="
# rsync does not create multiple missing parent levels; pre-create the tree.
ssh "${SSHOPT[@]}" ubuntu@"$IP" "mkdir -p /home/ubuntu/aces/implementations/python /home/ubuntu/aces/contracts"
rsync -az --delete --exclude '.venv' --exclude '__pycache__' --exclude '.git' --exclude '.pytest_cache' --exclude '.nox' --exclude '*.pyc' \
  -e "ssh ${SSHOPT[*]}" "$REPO_ROOT/implementations/python/" ubuntu@"$IP":/home/ubuntu/aces/implementations/python/
rsync -az --delete --exclude '.git' -e "ssh ${SSHOPT[*]}" "$REPO_ROOT/contracts/" ubuntu@"$IP":/home/ubuntu/aces/contracts/
scp "${SSHOPT[@]}" "$REPO_ROOT/tools/real-daemon/libvirt_smoke.py" ubuntu@"$IP":/home/ubuntu/aces/implementations/python/real_daemon_smoke.py

echo "=== install venv + libvirt-python ==="
ssh "${SSHOPT[@]}" ubuntu@"$IP" "curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; cd ~/aces/implementations/python && ~/.local/bin/uv sync --all-extras >/dev/null 2>&1 && ~/.local/bin/uv pip install libvirt-python >/dev/null 2>&1 && echo venv-ready"

echo "=== run real-daemon smoke ==="
ssh "${SSHOPT[@]}" ubuntu@"$IP" "cd ~/aces/implementations/python && .venv/bin/python real_daemon_smoke.py"
