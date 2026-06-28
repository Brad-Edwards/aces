# Paper Enterprise Participant Evidence Loop

`paper-agent-loop.sdl.yaml` is the ACES paper reference scenario for the
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

The scenario declares one participant, `paper-agent`, bound to the
`paper-participant` red-role entity. Its authored behavior is intentionally
narrow: probe `nodes.customer-portal.services.http` and report a bounded
terminal observation. The concrete coding-agent runner is outside the SDL and
is referenced only through `participant-implementation-manifest:paper-agent` in
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

`paper-agent-view` separates the public task brief, the DMZ service before and
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
paper demonstration without treating local action success as broad benchmark
success, Wazuh effectiveness, or model-defense robustness.

## Runtime Binding

The runtime/backend binding is intentionally downstream. APTL and the libvirt
reference backend should bind `paper-agent` to a participant implementation
manifest and provenance record, realize the declared portal probe, retain
participant/Wazuh/policy evidence, and record negative boundary evidence where
the backend supports live checks. That binding must not require new SDL syntax,
a new backend manifest shape, or APTL-private keys inside the scenario body.

## Downstream Links

- ACES issue: Brad-Edwards/aces#598
- Participant implementation binding: Brad-Edwards/aces#599
- ACES n=2 backend proof: Brad-Edwards/aces#600
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
