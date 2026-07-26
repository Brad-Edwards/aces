#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(git rev-parse --show-toplevel)}"
ASSET_ID="${ASSET_ID:?Set ASSET_ID to the inventory asset id}"
ASSET_DIR="${ASSET_DIR:-$ROOT/docs/raes/inventory/$ASSET_ID}"
OUT="${EVIDENCE_DIR:-$ASSET_DIR/evidence}"
IMAGE="${IMAGE:?Set IMAGE to an image tag or immutable digest}"
CONTAINER="${CONTAINER:-}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.yml}"
COMPOSE_SERVICE="${COMPOSE_SERVICE:-}"
COMPOSE_PROFILES="${COMPOSE_PROFILES:-}"
CAPTURE_BOUNDARY="${CAPTURE_BOUNDARY:-}"
OPERATOR_SECRET_NAME_REGEX="${OPERATOR_SECRET_NAME_REGEX:-}"

TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy@sha256:be1190afcb28352bfddc4ddeb71470835d16462af68d310f9f4bca710961a41e}"
SYFT_IMAGE="${SYFT_IMAGE:-anchore/syft@sha256:86fde6445b483d902fe011dd9f68c4987dd94e07da1e9edc004e3c2422650de6}"
OSQUERY_IMAGE="${OSQUERY_IMAGE:-osquery/osquery@sha256:f8ec3300048158292df2d4bb0d1d7804af358f530005828c3387553f23c796cd}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYFT_NORMALIZER="${SYFT_NORMALIZER:-$SCRIPT_DIR/normalize-syft-cyclonedx.jq}"

require() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'required command missing: %s\n' "$1" >&2
    exit 2
  }
}

require_capture_boundary() {
  if [[ "$CAPTURE_BOUNDARY" != "scenario-target" ]]; then
    printf '%s\n' \
      "Set CAPTURE_BOUNDARY=scenario-target after confirming this capture is scoped to participant-discoverable target state." \
      "Use OPERATOR_SECRET_NAME_REGEX only for operator/out-of-scenario material that must be withheld." >&2
    exit 2
  fi
}

record_limit() {
  printf -- '- %s\n' "$*" >> "$OUT/capture-limits.txt"
}

redact_text_stream() {
  if [[ -z "$OPERATOR_SECRET_NAME_REGEX" ]]; then
    cat
    return
  fi
  awk -v secret_re="$OPERATOR_SECRET_NAME_REGEX" '
    {
      for (i = 1; i <= NF; i++) {
        token = $i
        lowered = tolower(token)
        if (lowered ~ secret_re) {
          if (token ~ /=/) {
            sub(/=.*/, "=<REDACTED>", token)
          } else if (token ~ /:/) {
            sub(/:.*/, ":<REDACTED>", token)
          } else {
            token = "<REDACTED>"
            if (i < NF) {
              $(i + 1) = "<REDACTED>"
            }
          }
          $i = token
        }
      }
      print
    }
  '
}

redact_env_jq='
  def redact_env($secret_re):
    if (($secret_re | length) > 0) and contains("=") then
      capture("^(?<name>[^=]+)=(?<value>.*)$") as $m
      | if ($m.name | test($secret_re; "i")) then
          "\($m.name)=<REDACTED-\($m.name | gsub("_"; "-"))>"
        else
          .
        end
    else
      .
    end;

  def redact_sensitive_keys($secret_re):
    if ($secret_re | length) == 0 then
      .
    else
      walk(
        if type == "object" then
          with_entries(
            if (.key | test($secret_re; "i")) then
              .value = "<REDACTED>"
            else
              .
            end
          )
        else
          .
        end
      )
    end;
'

require docker
require jq
require sha256sum
require_capture_boundary

mkdir -p "$OUT"
: > "$OUT/capture-limits.txt"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$OUT/captured-at-utc.txt"

# With CAPTURE_BOUNDARY=scenario-target, this template preserves scenario-target values by default.
# Configure OPERATOR_SECRET_NAME_REGEX only after classifying a value as
# operator/out-of-scenario material rather than target evidence.
if [[ -n "$OPERATOR_SECRET_NAME_REGEX" ]]; then
  record_limit "Operator/out-of-scenario values matching OPERATOR_SECRET_NAME_REGEX were withheld by the capture template; ledger must describe the boundary and evidence impact"
fi

docker version --format json | jq . > "$OUT/docker-version.json"
if compose_version="$(docker compose version --format json 2>/dev/null)"; then
  printf '%s\n' "$compose_version" | jq . > "$OUT/docker-compose-version.json"
else
  record_limit "Docker Compose version was not captured because docker compose is unavailable"
fi

if [[ -n "$COMPOSE_SERVICE" && -f "$COMPOSE_FILE" ]]; then
  if [[ -n "$COMPOSE_PROFILES" ]]; then
    COMPOSE_PROFILES="$COMPOSE_PROFILES" docker compose -f "$COMPOSE_FILE" config --format json
  else
    docker compose -f "$COMPOSE_FILE" config --format json
  fi | jq \
    --arg service "$COMPOSE_SERVICE" \
    --arg secret_re "$OPERATOR_SECRET_NAME_REGEX" '
      if ((.services // {}) | has($service) | not) then
        error("compose service not found: " + $service)
      else
        .services[$service]
      end
      | .environment = (
          (.environment // {})
          | with_entries(
              if (($secret_re | length) > 0 and (.key | test($secret_re; "i"))) then
                .value = ("<REDACTED-" + (.key | gsub("_"; "-")) + ">")
              else
                .
              end
            )
        )
    ' > "$OUT/compose-service.$COMPOSE_SERVICE.json"
else
  record_limit "Compose service config was not captured; set COMPOSE_SERVICE and COMPOSE_FILE for composed assets"
fi

if [[ -n "$CONTAINER" ]]; then
  docker inspect "$CONTAINER" \
    | jq --arg secret_re "$OPERATOR_SECRET_NAME_REGEX" \
        "$redact_env_jq
        .[].Config.Env |= ((. // []) | map(redact_env(\$secret_re)))
        | redact_sensitive_keys(\$secret_re)" \
    > "$OUT/docker-inspect.container.json"
  docker top "$CONTAINER" | redact_text_stream > "$OUT/docker-top.txt"
  docker exec "$CONTAINER" sh -lc '
    echo --os-release--
    cat /etc/os-release 2>/dev/null || true
    echo --id--
    id 2>/dev/null || true
    echo --pwd--
    pwd
    echo --uname--
    uname -a 2>/dev/null || true
    echo --environment--
    env | sort
    echo --listeners--
    (ss -lntup || netstat -lntup || true) 2>&1
    echo --mounts--
    mount | sed -n "1,160p"
    echo --users--
    getent passwd | sed -n "1,200p" || true
    echo --groups--
    getent group | sed -n "1,200p" || true
    echo --process-tree--
    ps -eo pid,ppid,user,args || true
  ' | redact_text_stream > "$OUT/runtime-baseline.txt"
else
  record_limit "Container runtime state was not captured; set CONTAINER for running-container captures"
fi

docker image inspect "$IMAGE" \
  | jq --arg secret_re "$OPERATOR_SECRET_NAME_REGEX" "$redact_env_jq redact_sensitive_keys(\$secret_re)" \
  > "$OUT/docker-inspect.image.json"
docker history --no-trunc "$IMAGE" | redact_text_stream > "$OUT/docker-history.image.txt"

docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$TRIVY_IMAGE" --version \
  > "$OUT/trivy-version.txt"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$TRIVY_IMAGE" \
  image --format cyclonedx "$IMAGE" \
  | jq -c . > "$OUT/trivy-sbom.cyclonedx.json"

trivy_json="$(mktemp)"
trap 'rm -f "$trivy_json"' EXIT
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$TRIVY_IMAGE" \
  image --format json --scanners vuln "$IMAGE" > "$trivy_json"
jq '
  [
    .Results[]?.Vulnerabilities[]?
    | {
        id: .VulnerabilityID,
        package_name: .PkgName,
        installed_version: .InstalledVersion,
        fixed_version: (.FixedVersion // ""),
        severity: .Severity,
        primary_url: (.PrimaryURL // ""),
        target: (.Target // null)
      }
  ]
' "$trivy_json" > "$OUT/trivy-vulnerability-list.json"
jq 'group_by(.severity) | map({severity: .[0].severity, count: length})' \
  "$OUT/trivy-vulnerability-list.json" > "$OUT/trivy-vulnerability-counts.json"

if [[ -f "$SYFT_NORMALIZER" ]] && docker run --rm "$SYFT_IMAGE" version -o json \
  | jq . > "$OUT/syft-version.json"; then
  if docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$SYFT_IMAGE" \
    "docker:$IMAGE" \
    --output cyclonedx-json \
    --select-catalogers "-file-content-cataloger,-file-digest-cataloger,-file-executable-cataloger,-file-metadata-cataloger" \
    | jq -c -f "$SYFT_NORMALIZER" > "$OUT/syft-sbom.cyclonedx.json"; then
    record_limit "Syft CycloneDX output was deterministically normalized by stripping syft:location:* properties; ledger must reference filesystem provenance or this limit"
  else
    rm -f "$OUT/syft-sbom.cyclonedx.json"
    record_limit "Syft SBOM capture failed; preserve the command failure details outside committed evidence if needed"
  fi
else
  record_limit "Syft SBOM capture skipped; normalizer or digest-pinned Syft scanner was unavailable"
fi

if docker run --rm "$OSQUERY_IMAGE" osqueryi --version > "$OUT/osquery-version.txt"; then
  if [[ -n "$CONTAINER" ]]; then
    osquery_tool="$(cat "$OUT/osquery-version.txt")"
    rows="$(docker run --rm --pid="container:$CONTAINER" --network="container:$CONTAINER" \
      "$OSQUERY_IMAGE" osqueryi --json \
      'select pid, name, path, cmdline, uid, gid, start_time from processes where name != "osqueryi" order by pid;')"
    jq -n --arg table processes --arg tool "$osquery_tool" --argjson rows "$rows" \
      '{table: $table, tool: $tool, vantage: "container pid namespace", status: "captured", rows: $rows}' \
      > "$OUT/osquery-processes.json"
    rows="$(docker run --rm --pid="container:$CONTAINER" --network="container:$CONTAINER" \
      "$OSQUERY_IMAGE" osqueryi --json \
      'select port, protocol, address, pid, socket, path from listening_ports order by port, protocol, pid;')"
    jq -n --arg table listening_ports --arg tool "$osquery_tool" --argjson rows "$rows" \
      '{table: $table, tool: $tool, vantage: "container network namespace", status: "captured", rows: $rows}' \
      > "$OUT/osquery-listening-ports.json"
  else
    record_limit "osquery process/listener capture skipped because CONTAINER was not set"
  fi
else
  record_limit "osquery capture skipped because the digest-pinned osquery scanner was unavailable"
fi

(
  cd "$ASSET_DIR"
  find evidence -maxdepth 1 -type f ! -name evidence-sha256sums.txt -print \
    | sort \
    | xargs sha256sum
) > "$OUT/evidence-sha256sums.txt"
