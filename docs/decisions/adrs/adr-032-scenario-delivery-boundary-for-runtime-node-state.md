# ADR-032: Scenario/Delivery Boundary for Runtime Node State

## Status

accepted

## Date

2026-05-24

## Context

Issue #399 identifies a classification error in the SDL design precedents:
several concerns were excluded because their source evidence looked like
Docker or Docker Compose configuration. That rule is too broad. Docker,
Compose, Podman, Kubernetes, a harness, or a backend inspector can all expose
facts with different meanings:

- facts that exist on a realized range node
- host, kernel, container-runtime, or orchestration mechanics that create the
  range
- source-artifact or image provenance facts
- raw backend payloads used as evidence

The recent runtime ADR sequence has already corrected individual cases:

- ADR-025 records container network realization, including host-published port
  bindings, under node runtime state.
- ADR-027 records backend-injected init/PID-1 reaper configuration under
  runtime container configuration.
- ADR-028 records seccomp and backend-native security options under runtime
  container configuration.
- ADR-030 records process-scoped Linux capability posture under runtime
  capability policy.
- ADR-031 records SSH server policy under node runtime configuration.

The common rule behind those decisions needs to be explicit so future omission
decisions are not made by backend syntax resemblance.

This ADR is grounded in three evidence sets:

- the existing ACES typed runtime and provenance surfaces, including
  `RuntimeConfiguration.mounts`, `RuntimeConfiguration.network`,
  `RuntimeCapabilityPolicy`, and `ContainerImageBuildProvenance`;
- the ACES lineage notes for cyber-range SDL separation, participant
  observation semantics, DSL adequacy, and runtime/evidence boundaries; and
- downstream [Brad-Edwards/aptl#339](https://github.com/Brad-Edwards/aptl/issues/339)
  / SCN-010 evidence, where the TechVault Kali inventory exposed Compose
  profiles, build inputs, volume mounts, Linux capabilities, seccomp posture,
  runtime network realization, image provenance, and raw Docker evidence that
  had to be classified without making Docker Compose the SDL authority.

The sensitivity labels used for mount sources/options and local-control bind
sources are an ACES-native field-level redaction discipline reused from the
existing runtime filesystem, application, and database surfaces. The cited
literature and standards motivate the scenario/runtime/evidence separation; they
do not define ACES's specific sensitivity enum names or omission rule.

## Decision

### 1. Classify by semantic locus, not backend syntax

A fact is scenario/runtime state when it exists on a realized range node and a
participant, evaluator, scanner, or in-range process can invoke it, observe it,
depend on it, or interact with its effects.

The delivery layer is the machinery that creates, hosts, and controls the
range: orchestrators, host kernels, container runtimes, backend adapters,
control planes, package/build executors, and host-local operator state. A fact
does not become delivery-only merely because Docker, Compose, or another
backend exposes it.

### 2. Use the owning typed surface

Participant-interactable node state belongs on the smallest existing typed
surface that owns its meaning:

- transport listeners remain `Node.services`
- host-published port bindings belong in `Node.runtime.network`
- filesystem mounts belong in `Node.runtime.mounts`
- container host/security posture belongs in `Node.runtime.container`
- Linux capability policy belongs in `Node.runtime.linux_capabilities`
- protocol-specific daemon policy, such as SSH server policy, belongs in a
  typed runtime service-configuration surface
- source-artifact and image build provenance belong on the source artifact
  boundary

If no owning surface exists, add a bounded typed surface at the correct
semantic boundary. Do not add a Docker-specific top-level field and do not use
an untyped backend payload as the SDL contract.

### 3. Keep delivery facts and evidence bounded

Delivery decisions can be relevant evidence, but they are not automatically SDL
scenario meaning. Backend-native values may be retained only through bounded
fields on the owning surface, with redaction and stability rules where needed.
Raw inspect payloads, credentials, tokens, secret argv, backend exceptions, and
host-only operator state must not become normative SDL payloads.

Host-local paths and backend-local path fragments need field-level handling, not
ad hoc prose. Runtime mount sources, runtime mount options, and local-control
bind sources have explicit sensitivity classification. Values classified as
`redacted` or `operator_secret` must omit the raw value; values retained as
plain data remain bounded evidence on the owning runtime surface rather than
portable scenario authoring semantics.

### 4. Preserve authored intent, observed runtime state, and provenance

The SDL must keep these meanings distinct:

- authored scenario intent, such as declared nodes, services, content, and
  objectives
- observed runtime state on realized nodes
- source-artifact and image provenance
- backend deployment mechanics and host-local delivery state

The same real-world evidence may support more than one surface, but the
surfaces do not collapse into each other. For example, a container-side service
listener, a host-published port binding, and an image-default exposed port are
different facts.

## Guardrails

- Do not exclude participant-interactable state solely because it is exposed by
  Docker, Compose, or another backend tool.
- Do not import Docker Compose as the SDL schema.
- Do not model host paths, host networking policy, or backend execution plans
  as participant-visible scenario state unless the participant can observe or
  interact with their effects through a typed surface.
- Do not claim host-local path redaction unless the owning field has an explicit
  sensitivity/redaction signal and the raw value is omitted when classified as
  `redacted` or `operator_secret`.
- Do not infer defaults from missing backend evidence. Record explicit state
  only when it is known.
- Do not hand-edit generated schemas under `contracts/schemas/`; schema
  changes come from generator inputs.
- Do not add implementation logic under `implementations/python/src/aces/`;
  that tree is compatibility-only wrappers.

## Non-Goals

- Adding new SDL fields for every previously omitted Docker or Compose key.
- Building a Docker, Compose, Podman, Kubernetes, or harness inspector.
- Modifying or fully auditing downstream APTL inventories;
  [Brad-Edwards/aptl#339](https://github.com/Brad-Edwards/aptl/issues/339) is
  used here as motivating consumer evidence, not as a new ACES conformance
  fixture.
- Claiming downstream APTL artifacts have already adopted this redaction
  contract everywhere. Existing downstream evidence may still carry raw host or
  backend-local paths until that consumer updates its SDL inventory.
- Rewriting broad documentation outside the issue #399 precedent rule.
- Reclassifying source-artifact provenance as runtime node state.

## Consequences

### Positive

- Future omission decisions use a stable scenario-vs-delivery boundary instead
  of backend syntax resemblance.
- Recent runtime ADRs have a shared architectural rationale.
- Participant-interactable node facts can be represented without making raw
  backend payloads normative.

### Negative

- Some facts must be represented in adjacent surfaces with different meanings.
  Contributors need to distinguish authored intent, observed runtime state,
  provenance, and delivery mechanics explicitly.
- Omission decisions may require more analysis than checking whether the source
  evidence came from a Docker or Compose file.

### Risks

- If the rule is applied too broadly, SDL surfaces could import backend
  implementation details that are not scenario meaning.
- If the rule is applied too narrowly, participant-interactable state could be
  hidden from downstream consumers and repeat the issue #399 failure mode.

## References

- [Lineage and Prior Work](../../explain/sdl/lineage.md) — cyber-range SDL,
  participant-semantics, DSL-evaluation, runtime/federation, and
  evidence/provenance lineage.
- [Design Precedents](../../explain/sdl/precedents.md) — element-level
  precedent map and deliberate omissions table.
- [Documentation Style Guide](../../explain/reference/documentation-style-guide.md)
  — current-state evidence and citation rules for academic-facing prose.
- [ADR-023](adr-023-container-image-build-provenance-surface.md),
  [ADR-025](adr-025-container-network-realization-surface.md),
  [ADR-027](adr-027-container-init-reaper-runtime-surface.md),
  [ADR-028](adr-028-container-seccomp-security-options-surface.md),
  [ADR-030](adr-030-process-scoped-linux-capability-policy.md), and
  [ADR-031](adr-031-ssh-server-configuration-surface.md) — concrete runtime and
  provenance surfaces that this ADR generalizes.
- [`runtime_configuration.py`](../../../implementations/python/packages/aces_sdl/runtime_configuration.py),
  [`runtime_filesystem.py`](../../../implementations/python/packages/aces_sdl/runtime_filesystem.py),
  [`runtime_network.py`](../../../implementations/python/packages/aces_sdl/runtime_network.py),
  [`runtime_capabilities.py`](../../../implementations/python/packages/aces_sdl/runtime_capabilities.py),
  and [`image_provenance.py`](../../../implementations/python/packages/aces_sdl/image_provenance.py)
  — current implementation surfaces checked for the owning typed fields.
- [Open Cyber Range SDL](https://documentation.opencyberrange.ee/docs/sdl/),
  [CACAO Security Playbooks v2.0](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.pdf),
  [OCSF](https://ocsf.io/),
  [CybORG](https://arxiv.org/abs/2108.09118), and the DSL-evaluation sources
  cited from the lineage document — adjacent primary sources behind the
  scenario/deployment, participant-observation, schema-discipline, and language
  adequacy boundaries.
