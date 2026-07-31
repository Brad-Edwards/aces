# Enterprise Participant Evidence Loop

`enterprise-participant-evidence-loop.sdl.yaml` is the RAES reference scenario for the
authored SDL -> processor -> runtime -> backend handoff. It is a generic
enterprise slice: a red participant workbench, a DMZ customer portal, an
internal database, a Wazuh evidence surface, and optional participant policy
provenance. It is a positive worked example, not a benchmark, backend profile,
APTL-private scenario, TechVault-specific scenario, or proof that a specific
coding-agent runner executed.

## Topology

The topology carries the participant-observation claim:

- `red-workbench`: the participant's runtime-facing host, attached to
  `redteam-net` and `dmz-net`.
- `customer-portal`: the DMZ web application, attached to `dmz-net` and
  `internal-net`.
- `customer-db`: the internal database, attached only to `internal-net`.
- `wazuh-manager` and `wazuh-indexer`: Wazuh evaluator evidence surfaces on
  `security-net`, with the manager also attached to `internal-net` so monitored
  hosts can report events.
- `participant-policy-gate`: an optional policy/provenance surface on
  `security-net`.

The participant host is not attached to `internal-net` or `security-net`. Direct
database and Wazuh API access from the participant host is outside the declared
participant action and is represented as negative evaluator evidence for live
backends that support those checks.

## Participant

The scenario declares one participant, `participant-agent`, bound to the
`enterprise-participant` red-role entity. Its authored behavior is intentionally
narrow: probe `nodes.customer-portal.services.http` and report a bounded
terminal observation. The concrete coding-agent runner is outside the SDL and
is referenced only through `participant-implementation-manifest:participant-agent` in
the behavior specification.

## Declared Action

`probe-customer-portal-login` is the governed action contract. It records the
participant's authority, DMZ target, realization preconditions, portable effect
classes, failure classes, backend diagnostic mappings, and a shared-state
interaction over the customer portal service. It also declares evaluator-only
evidence effects from Wazuh, optional policy provenance, and negative boundary
checks. The contract does not embed commands, prompts, runner config,
backend-native action labels, Wazuh rule bodies, credentials, or model-defense
policy internals.

## Observation Boundary

`participant-view` separates the public task brief, the DMZ service before and
after discovery, hidden internal resources, evaluator-only evidence, and hidden
adjudication material. The portal service becomes discovered only after the
terminal participant observation. `nodes.customer-db.services.postgres`, Wazuh
internals, `nodes.participant-policy-gate`, and `content.evaluator-notes` remain
outside the participant view.

This is stronger than saying the agent was not told something. The authored
topology places the participant host outside `internal-net` and `security-net`,
the agent operating scope names only the DMZ portal and task brief, and the
Wazuh/policy/boundary records are evidence-only surfaces for the evaluator.

## Expected Evidence

The expected evidence is deliberately bounded:

- `content.participant-observation`: the participant runtime observation
  envelope.
- `content.wazuh-evidence`: Wazuh evaluator evidence for the portal probe.
- `content.policy-decision-log`: optional model-defense or tool-use
  authorization provenance.
- `content.boundary-check-evidence`: negative evidence for direct DB and Wazuh
  API reachability from the participant host where supported by a live backend.

The objective and outcome interpretation rule use those records to support the
reference demonstration without treating local action success as broad benchmark
success, Wazuh effectiveness, or model-defense robustness.

## Runtime Binding

The runtime/backend binding is intentionally downstream. APTL and the libvirt
reference backend should bind `participant-agent` to a participant implementation
manifest and provenance record, realize the declared portal probe, retain
participant/Wazuh/policy evidence, and record negative boundary evidence where
the backend supports live checks. That binding must not require new SDL syntax,
a new backend manifest shape, or APTL-private keys inside the scenario body.

## Libvirt Scenario Evidence Artifact (#615)

`raes_operations.libvirt_evidence_run.run_libvirt_evidence_run` (CLI: `raes
libvirt evidence validate`) produces a stable, validated evaluator-evidence
run artifact for this scenario — `raes.libvirt.scenario-evidence-run/v1`, written to
`runs/<run-id>/scenario-evidence/libvirt-scenario-evidence-run.json`. It composes the
existing RAES surfaces (libvirt deterministic participant runtime #614, native
substrate realization #601, backend manifest/capability contracts, and the
experiment/evaluation contracts) into one artifact carrying scenario+compiled
identity, backend manifest/capability profile and realization provenance, the
realized/planned topology and network-attachment matrix, the participant action
proof, the terminal participant-projected history under the named observation
boundary (explicitly not an equivalence comparison), evaluator-only
Wazuh/SOC evidence, negative boundary checks, an evaluator outcome record, and
redaction/provenance metadata. Embedded published-contract payloads
(`BackendManifestV2Model`, `EvaluationResultStateModel`,
`EvaluationHistoryEventModel`, `ExperimentRealizedFormDisclosureModel`)
re-validate against their contracts; the artifact carries a strict redaction gate
(no raw libvirt XML, domain UUIDs, QEMU command lines, host paths, connection
URIs, credentials, or private keys).

### Evidence-source modes

- `deterministic` (default; no libvirt daemon; used by CI): participant proof,
  compiled topology, structural negative-boundary evidence, and declared
  evaluator-only defensive evidence channels. No SOC state is observed.
- `native-live` (operator-run): additionally realizes the libvirt VM/network
  substrate only when every concern passes the TechVault admission gate, then
  records bounded daemon-observed fields with a realization binding. Native
  realization is **gating**. The reference scenario declares unsupported guest
  content/account/feature concerns, so native-live reports the realization gate
  as **failed** and surfaces those concerns under `unrealized_capabilities`
  (disclosed, not faked). The artifact is still written and validates, recording
  the attempt. Native realization can pass for an admitted VM/network-only
  substrate scenario. Guest readiness, services, and SOC state remain
  `not-observed` in both modes.

### How libvirt evidence differs from APTL Docker/Wazuh evidence

APTL realizes the scenario as Docker/Compose containers with a full upstream
Wazuh stack, so its scenario evidence artifact (Brad-Edwards/aptl#558) carries live
container-native Wazuh detection telemetry and Docker-network reachability
evidence. The libvirt proof realizes a different substrate — native libvirt/QEMU
appliances — and its participant runtime is deterministic (#614), so:

- the **substrate** is genuinely different (VM/network appliances vs.
  containers) only for concerns admitted and daemon-verified by the bounded
  native mode;
- the **defensive evidence** is a declaration of evaluator-only evidence
  channels, not native SOC readback — the artifact makes no Wazuh
  detection-quality claim;
- the **participant action proof** is structural (deterministic domain adapter),
  disclosed as such.

The claim is narrow: RAES can compile the same authored scenario and execute its
deterministic participant contract while honestly disclosing that the full
guest/application provisioning plane is not realized by the libvirt TechVault
mode. A separate bounded scenario demonstrates an independent VM/network
substrate. This is **not** a claim that the reference scenario is fully realized
on two backends, nor a claim of byte-equivalence, application-internals
equivalence, Wazuh detection-quality parity, model-defense robustness, or full
semantic equivalence.

## Downstream Links

- RAES issue: OpenRAE/rae#598
- Participant implementation binding: OpenRAE/rae#599
- RAES n=2 backend proof: OpenRAE/rae#600
  (corpus: `examples/corpus/reference-demonstration/`)
- Libvirt participant runtime: OpenRAE/rae#614
- Libvirt evaluator/Wazuh evidence readback: OpenRAE/rae#615
- APTL realization and proof: Brad-Edwards/aptl#556,
  Brad-Edwards/aptl#557, Brad-Edwards/aptl#558

This RAES scenario supplies the authored scenario that downstream APTL and
libvirt proof issues can consume.

## Limitations

- The scenario proves SDL parsing, semantic validation, and processor
  compilation of participant handoff surfaces.
- It does not claim TechVault coverage, purple-team benchmark coverage, or
  autonomous-agent capability.
- It does not evaluate Wazuh detection quality or model-defense robustness.
- It does not include a private runner command, prompt, sandbox policy,
  credential, backend log, Wazuh ruleset, model-defense policy body, or hidden
  answer key.
- It is designed for small n=2 reference-emulation proof work and should remain
  reusable as a corpus example.
