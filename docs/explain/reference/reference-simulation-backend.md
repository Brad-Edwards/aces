# Reference Simulation Backend

The reference simulation backend (RUN-315) is a repository-owned implementation
of the standard backend protocol roles behind an in-process simulation engine.
It lives in `aces_reference_simulation_backend` and registers on the standard
`BackendRegistry` descriptor seam under the name `reference-simulation`.

The backend is intentionally hermetic. It does not start subprocesses, contact a
simulator service, read credentials, or expose simulator-native object ids.
Provisioning plans are interpreted into portable simulation specs for networks,
nodes, and placements; the engine records simulated resources and a monotonic
simulation tick privately. Runtime snapshots keep the authored ACES payloads and
portable simulation metadata only.

## Constructing and registering a target

```python
from aces_reference_simulation_backend import (
    create_reference_simulation_backend_target,
    register_reference_simulation_backend,
)
from aces.core.runtime.registry import BackendRegistry

target = create_reference_simulation_backend_target()

registry = BackendRegistry()
register_reference_simulation_backend(registry)
target = registry.create("reference-simulation")
```

Config kwargs flow through the registry descriptor. Pass `engine=` to adapt a
different simulator behind the same portable contract seam:

```python
from aces_reference_simulation_backend import InProcessSimulationEngine

engine = InProcessSimulationEngine()
target = create_reference_simulation_backend_target(engine=engine)
```

## Running it

Drive execution through `RuntimeManager` or `RuntimeControlPlane` so the
existing apply, result, conformance, and SEM-218 provenance gates run:

```python
import textwrap

from aces.core.runtime.manager import RuntimeManager
from aces.core.sdl import parse_sdl
from aces_reference_simulation_backend import create_reference_simulation_backend_target

manager = RuntimeManager(create_reference_simulation_backend_target())
plan = manager.plan(parse_sdl(textwrap.dedent("""
    name: simulated
    nodes:
      web:
        type: vm
        os: linux
        resources: {ram: 1 gib, cpu: 1}
""")))
result = manager.apply(plan)

assert result.success
assert result.snapshot.entries["provision.node.web"].status == "simulated"
assert result.snapshot.metadata["reference_simulation"]["clock"] == "simulation_tick"
```

`RuntimeManager.apply()` attaches the same SEM-218
`realization_provenance` ledger used by other runtime targets. The simulation
backend does not create a new provenance format.

## Conformance

The target declares Provisioner, Orchestrator, Evaluator, and
ParticipantRuntime capabilities, so `run_target_conformance()` infers the
`FULL_REMOTE_CONTROL_PLANE` profile:

```python
from aces.core.runtime.conformance import (
    BackendCapabilityProfile,
    run_target_conformance,
)
from aces_reference_simulation_backend import create_reference_simulation_backend_target

report = run_target_conformance(create_reference_simulation_backend_target())
assert report.profile == BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE
assert report.passed
```

## Portable-Fact Boundary

The public surface is standard ACES contracts: backend manifest v2, runtime
snapshots, operation statuses, workflow/evaluation result envelopes, participant
episode state/history, and SEM-218 realization provenance. Simulator-native ids,
event queues, object reprs, host paths, environment values, credentials, and raw
tracebacks stay out of snapshots, diagnostics, conformance reports, and docs.
