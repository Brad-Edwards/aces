# Enterprise Participant Evidence Loop

`enterprise-participant-evidence-loop.sdl.yaml` is the ACES reference scenario for the
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

`aces_operations.libvirt_evidence_run.run_libvirt_evidence_run` (CLI: `aces
libvirt evidence validate`) produces a stable, validated evaluator-evidence
run artifact for this scenario — `aces.libvirt.scenario-evidence-run/v1`, written to
`runs/<run-id>/scenario-evidence/libvirt-scenario-evidence-run.json`. It composes the
existing ACES surfaces (libvirt deterministic participant runtime #614, native
substrate realization #601, backend manifest/capability contracts, and the
experiment/evaluation contracts) into one artifact carrying scenario+compiled
identity, backend manifest/capability profile and realization provenance, the
realized/planned topology and network-attachment matrix, the participant action
proof, the terminal behavior-history-equivalent observation, evaluator-only
Wazuh/SOC evidence, negative boundary checks, an evaluator outcome record, and
redaction/provenance metadata. Embedded published-contract payloads
(`BackendManifestV2Model`, `EvaluationResultStateModel`,
`EvaluationHistoryEventModel`, `ExperimentRealizedFormDisclosureModel`)
re-validate against their contracts; the artifact carries a strict redaction gate
(no raw libvirt XML, domain UUIDs, QEMU command lines, host paths, connection
URIs, credentials, or private keys).

### Evidence-source modes

- `deterministic` (default; no libvirt daemon; used by CI): participant proof,
  compiled topology, structural negative-boundary evidence, and an evaluator-only
  translated SOC-readback record explicitly marked as not upstream Wazuh.
- `native-live` (operator-run): additionally realizes the libvirt VM/network
  substrate and records the native topology and native SOC readback. Native
  realization is **gating** — the run only reports `PASS` when the libvirt driver
  actually realizes substrate, so the mode can never claim success without
  realizing. The libvirt backend declares no content-type support, so the *reference*
  scenario's content, orchestration, and evaluation planes are not
  backend-realized: native-live against this scenario therefore reports the
  realization gate as **failed** and surfaces the unrealized planes under
  `unrealized_capabilities` (disclosed, not faked). The artifact is still written
  and validates, recording the attempt and the disclosure. Native realization
  passes for a scenario the libvirt backend can fully provision (e.g. a
  VM/network-only substrate scenario).

### How libvirt evidence differs from APTL Docker/Wazuh evidence

APTL realizes the scenario as Docker/Compose containers with a full upstream
Wazuh stack, so its scenario evidence artifact (Brad-Edwards/aptl#558) carries live
container-native Wazuh detection telemetry and Docker-network reachability
evidence. The libvirt proof realizes a different substrate — native libvirt/QEMU
appliances — and its participant runtime is deterministic (#614), so:

- the **substrate** is genuinely different (VM/network appliances vs.
  containers), which is the point of the n=2 backend-diversity claim;
- the **defensive evidence** is an evaluator-only *translated/native* SOC
  readback (or, in deterministic mode, the declared evaluator-only evidence
  channels), explicitly disclosed as not upstream Wazuh detection output — the
  artifact makes no Wazuh detection-quality claim;
- the **participant action proof** is structural (deterministic domain adapter),
  disclosed as such.

The claim that this difference supports is narrow and explicit: ACES can
drive the *same authored scenario, action contract, and observation/evaluator
boundary* across two independent backends, producing comparable evaluator
evidence shapes for the Brad-Edwards/aces#600 cross-backend **invariant ledger**.
It is **not** a claim of byte-equivalence, application-internals equivalence,
Wazuh detection-quality parity, model-defense robustness, or full
semantic-equivalence between the libvirt and APTL realizations.

## Downstream Links

- ACES issue: Brad-Edwards/aces#598
- Participant implementation binding: Brad-Edwards/aces#599
- ACES n=2 backend proof: Brad-Edwards/aces#600
  (corpus: `examples/corpus/reference-demonstration/`)
- Libvirt participant runtime: Brad-Edwards/aces#614
- Libvirt evaluator/Wazuh evidence readback: Brad-Edwards/aces#615
- APTL realization and proof: Brad-Edwards/aptl#556,
  Brad-Edwards/aptl#557, Brad-Edwards/aptl#558

This ACES scenario supplies the authored scenario that downstream APTL and
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
