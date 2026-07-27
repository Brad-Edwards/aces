# Reference Emulation Backend

The reference emulation backend (RUN-314,
[ADR-063](../../decisions/adrs/adr-063-reference-emulation-backend.md)) is a
repository-owned, concrete implementation of the four backend protocol roles —
Provisioner, Orchestrator, Evaluator, and ParticipantRuntime. It lives in the
implementation package `raes_reference_backend` and is **not** a normative
authority surface: it consumes the existing manifest, registry, conformance, and
SEM-218 realization seams and proves compatibility against the published
contracts.

Unlike the non-normative in-memory stub (`raes_backend_stubs`), the reference
backend realizes provisioning plans against a pluggable deployment driver. The
default driver is hermetic; an opt-in OCI driver realizes against a real
container runtime (docker/podman). Either way, only portable RAES facts reach
snapshots, diagnostics, and conformance reports.

## Constructing and registering a target

The backend registers on the standard `BackendRegistry` descriptor seam under
the name `reference-emulation`. Construct a target directly or through the
registry:

```python
from raes_reference_backend import (
    create_reference_backend_target,
    register_reference_backend,
)
from raes_runtime.registry import BackendRegistry

# Direct: default hermetic in-process driver.
target = create_reference_backend_target()

# Via the registry; driver config flows through the descriptor seam.
registry = BackendRegistry()
register_reference_backend(registry)
target = registry.create("reference-emulation")
```

Config kwargs flow to both the manifest factory and the components factory, so a
`driver=` (or any other extra) passes through; the manifest factory accepts and
ignores extras it does not use.

## Drivers

- **In-process (default).** `InProcessDriver` records the realize/destroy
  operations it is asked to perform and synthesizes portable handles. It runs no
  subprocess and needs no container runtime, so it is safe in CI and in the
  default conformance/apply path.
- **OCI (opt-in).** `OciDeploymentDriver` realizes against docker or podman
  through fixed-argv subprocess calls (never a shell string), a closed runtime
  allowlist, and bounded timeouts. Backend-native output (container ids, daemon
  inspect payloads, raw stderr) is consumed privately and never reaches the
  returned handles or diagnostics. It enforces an operator **image-trust
  policy** — only the configured `default_image`, an `allowed_images` entry, or a
  digest-pinned ref is realized, so a plan-pinned `node.source` cannot turn plan
  submission into arbitrary-image code execution. Realization is transactional
  (a partial failure rolls back what succeeded), and containers are attached to
  every network their plan declares.

### Service and ACL boundary

The interpreter preserves each authored `Node.services[]` entry as a typed
service descriptor on the portable container specification, including unnamed
services and non-TCP protocols. Both bundled drivers treat those descriptors as
descriptor-only: they do not publish host ports, configure daemons, synthesize
allow rules, or claim that a listener exists. Reachability therefore never
follows from a service declaration.

Traffic authorization remains the separate `infrastructure.*.acls` concern.
The reference backend declares `supports_acls=false` because neither bundled
driver enforces ACLs; the planner rejects such a plan before apply. A future
driver that realizes services or ACLs must use the existing realization-concern
and diagnostic surfaces and provide evidence for the runtime effect it claims.

```python
from raes_reference_backend import create_reference_backend_target
from raes_reference_backend.drivers.oci import OciDeploymentDriver

driver = OciDeploymentDriver(runtime="docker", workspace="raes-ref")
target = create_reference_backend_target(driver=driver)
```

## Running it: apply and provenance

Drive apply and control through `RuntimeManager` / `RuntimeControlPlane`, never
by calling backend components directly. Apply records SEM-218 realization
provenance through the existing apply gate:

```python
import textwrap
from raes_runtime.manager import RuntimeManager
from raes import parse_sdl
from raes_reference_backend import create_reference_backend_target

manager = RuntimeManager(create_reference_backend_target())
plan = manager.plan(parse_sdl(textwrap.dedent("""
    name: demo
    nodes:
      web:
        type: vm
        os: linux
        resources: {ram: 1 gib, cpu: 1}
""")))
result = manager.apply(plan)

assert result.success
# The realized snapshot entry preserves the planned (portable) payload; real
# container realization is a driver side effect, not a snapshot mutation.
assert result.snapshot.entries["provision.node.web"].payload["os_family"] == "linux"
# SEM-218 provenance is filled by the apply gate.
provenance = {e.field_path: e for e in result.snapshot.realization_provenance}
assert provenance["nodes.web.os"].requirement_kind == "os-family"
```

## Conformance

The reference target passes `run_target_conformance` at the
`FULL_REMOTE_CONTROL_PLANE` profile — the same case set the stub passes,
including the full RUN-311 participant-episode probe:

```python
from raes_conformance.conformance import (
    BackendCapabilityProfile,
    run_target_conformance,
)
from raes_reference_backend import create_reference_backend_target

report = run_target_conformance(create_reference_backend_target())
assert report.profile == BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE
assert report.passed
```

## Opt-in container integration

Real-container realization is verified by a `docker`-marked integration test
(`implementations/python/tests/test_reference_backend_docker_integration.py`).
The `docker` marker is excluded from the default hermetic test suite, and the
test self-skips cleanly when no container runtime is available. Run it
explicitly:

```bash
# from the repo root
nox -s integration_docker
# or directly
cd implementations/python && uv run --frozen python -m pytest -m docker -q
```

A non-blocking, runtime-gated CI job runs the same session when a container
runtime is present; the canonical `verify` graph stays hermetic and never
depends on a runtime.

## Portable-fact boundary

Container, VM, and network ids, daemon inspect payloads, host paths,
environment, process argv, tokens, credentials, SSH keys, and backend-native
object reprs never appear in manifests, snapshots, diagnostics, conformance
reports, or examples. The portable surface is references, digests, sensitivity
labels, and redaction classifications. Public failures are `Diagnostic`,
`OperationReceipt`, or `OperationStatus` values; the backend defines no
backend-specific exception hierarchy, log channel, or raw traceback.
