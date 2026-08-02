# Issue 1043: Forwarding-Agent Realization and Posture Preflight

## Decision guidance

`runtime.forwarding_agents` remains a non-executable, typed runtime inventory.
For SEM-218, realizing that inventory means materializing and independently
corroborating the agent's **identity, placement, implementation, and declared
configuration projection**. It does not mean proving that a source is currently
shipping, that an IOC transform ran, or that a reload was consumed.

Consequently, an exact forwarding-agent declaration is realized exactly when
the canonical `forwarding-agents` configuration projection agrees with the
backend's independently obtained readback at the declared verification scope.
A digest-locked sidecar or installed unit may therefore satisfy the concern;
the reference backend must not report it absent merely because it does not run
the forwarding workload. Conversely, a planned payload echoed as an observation
is not readback and cannot discharge the gate.

## Keep three claims separate

| Claim | Owner / canonical carrier | Meaning |
| --- | --- | --- |
| Agent inventory and configuration | ADR-050 model, SEM-218 `forwarding-agents` descriptor and projection | The agent and its declared configuration are present as declared. |
| Corroboration capability and result | `RealizationSupportDeclaration`, the backend-return gate, and a concern-keyed observation profile | What independent evidence supports the inventory/configuration claim. |
| Operational forwarding posture | ADR-079 proposition/assertion, probe binding, truth result, and evidence record | Whether the agent actually forwards, fails to forward, routes to an intended/different destination, or produces a rule/reload effect during a governed window. |

Do not use any one of these carriers as a substitute for another. In
particular, a configured `ship_target` is not evidence of delivery, and a
failed forwarding proposition does not make an intentionally configured agent
unrealized.

The existing `ObservationStrength` in the realization-envelope carrier remains
the provenance/source axis (`driver-reported`, `daemon-observed`, or
`guest-observed`). It must not be relabelled as `presence`, `configuration`, or
`behavior`: those are the scope of the claim. Extend the existing realization
support/disclosure path with a closed, concern-keyed **verification scope**
(`presence`, `configuration`; `behavior` is reserved for a future concern that
actually owns behavior), paired with the existing strength. An exact inventory
requirement may only be accepted when its declared required scope is met by the
backend's independently observed scope. This is a capability/observation
qualification on the existing SEM-218 descriptor and manifest declaration, not
a second realization taxonomy, envelope dialect, or a new `RealizationConcern`
value in ADR-070's carrier.

The initial forwarding-agent exact projection must be the present
configuration projection already owned by `project_forwarding_agents`, with
the existing keyed ordering, annotation removal, secret-safe setting
commitments, and `validate_forwarding_agents_observation` boundary. It must
not add a `forwarding`, `healthy`, `delivery_status`, `last_shipped`, or
runtime-log field to that projection.

## Endogenous and exogenous agents

Add a closed authored role on a forwarding-agent inventory entry:

- `system_under_test`: the agent is scenario state; its configuration may be a
  variation target and its operational posture may be an observed proposition.
- `measurement_apparatus`: the agent exists to collect experiment evidence. It
  is not a scenario factor or a substitute for a scenario-native observation.

The role is an ownership classification, not an execution mode and not a
visibility claim. A measurement-apparatus entry that is environment-visible or
comparability-relevant must also be disclosed through the existing
`ExperimentAugmentationDisclosureModel` on the run, using its existing
classification, carrier references, affected references, evidence references,
and marking requirements. `apparatus_only` continues to use the established
operational-observability boundary.

The evidence plane is the authoritative direction for the binding. An
`EvidenceRequirement` (and, when executable, its capture specification) names
the forwarding-agent qualified reference as its `source_refs`, with its
channel, artifact role, sensitivity, redaction, integrity, retention, and loss
requirements. It describes the abstract evidence destination; no forwarding
agent field may contain a host path, evidence-pack URI, storage credential, or
capture payload. Semantic validation must require at least one such inbound
evidence binding for `measurement_apparatus` and reject a binding that targets
an agent marked `system_under_test` as measurement apparatus. Keep this
relation single-directional: do not duplicate evidence requirement references
on the agent.

This is the first application of an agent-role pattern, not justification for a
universal runtime-agent base model. A future EDR or comparable family should
reuse the same closed role vocabulary, evidence-direction rule, augmentation
disclosure, and proposition boundary only after it has the same semantics.

## Required gates and invariants

- Preserve `RuntimeForwardingAgent` profile validation, stable ids, target
  resolution, the closed enrollment posture, and ADR-056 secret-value
  redaction. Role and evidence binding must use `SDLModel`, `extra="forbid"`,
  existing enum/variable parsing, and `SemanticValidator`; compiler code must
  not parse or revalidate raw YAML.
- Preserve `raes.explicitness`, realization designation, instantiation
  provenance, and concrete revalidation. Exactness remains aggregate
  configuration exactness; it is never inferred from serialization or a
  backend snapshot.
- Extend only `raes_processor.semantics.realization_concerns` and its one
  descriptor/projection/observation-validator route. Compilation, envelope
  admission, backend capability matching, `realization_disclosure()`, and
  `_call_backend_apply()` must consume that route. A non-matching or
  under-observed exact declaration fails closed as
  `runtime.backend-contract-invalid` before snapshot persistence.
- Reuse `RealizationSupportDeclaration` / `RealizationSupportDeclarationModel`
  and the backend-manifest-v2 concept/schema/fixture path for observation-scope
  support. Do not add per-backend booleans, a forwarding-specific manifest, or
  a second capability registry.
- Reuse the existing snapshot serializers and
  `RuntimeSnapshotEnvelopeModel`; validate every backend-returned forwarding
  observation before storage or API conversion. `RealizationProvenanceEntry`
  still records no realized value and must not become the observation carrier.
- A behavioral probe must be a closed typed proposition and capability-bound
  probe binding under ADR-079. It requires governed evidence and reports
  `true`, `false`, `unknown`, or `unsupported`; lack of a delivery observation
  is `unknown`, not `false`. It must not be an arbitrary command, healthcheck,
  manager-log heuristic, or a backdoor field in the realization snapshot.

## Security and exposure

The change passes the existing parser/model, semantic-reference,
instantiation, manifest/configuration, backend-return, persistence/schema,
control-plane authorization, diagnostic, audit, and OS/process-exposure gates.
No raw forwarding setting, enrollment material, evidence-store credential,
native inspect object, probe payload, or evidence location may enter a
snapshot, provenance entry, diagnostic, audit event, fixture, exception, or
process argv. Continue using safe commitments for permitted setting equality,
the existing redacted error envelope, authenticated snapshot reads, role checks,
request limits, audit recording, and backend fixed-argv/no-shell execution.

## Explicit non-goals

- Implementing shipping, capture storage, rule generation, reload execution,
  liveness, or delivery monitoring.
- Treating image attestation or configuration readback as behavioral proof.
- Redesigning ADR-070 realization-envelope concerns, ADR-064 evidence records,
  ADR-066 planes, ADR-079 truth algebra, or service materialization.
- Adding a universal runtime-agent schema, evidence-path fields, secret
  resolver, new endpoint, sidecar persistence store, exception hierarchy, or
  backend-specific forwarding dialect.

## Follow-on ADR handling

Before implementation changes public SDL/contracts, promote these choices by
an ADR-050 amendment plus any necessary ADR-056/ADR-066/SEM-218 amendment,
recording ADR-059 amendment rows and `adr-index.yaml` pins in the same change.
The implementation must update model/schema parity, publication governance,
fixtures, semantic and conformance tests together; this preflight adds none of
those executable artifacts.
