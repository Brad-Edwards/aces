# Paper Agent Loop Scenario

`paper-agent-loop.sdl.yaml` is a compact ACES paper reference scenario for the
authored SDL -> processor -> runtime -> backend handoff. It is shaped as a
small security-range vignette: a participant workbench, a target web service,
an internal dependency, a Suricata-style sensor, and a model-defense gate. It is
a positive worked example, not a benchmark, backend profile, APTL-private
scenario, or proof that a specific coding-agent runner executed.

## Topology

The scenario uses two small networks. `range-net` carries the participant and
target slice; `telemetry-net` gives the sensor and model-defense gate a place to
retain evaluator-facing evidence. The modeled systems are:

- `participant-workbench`: the participant's runtime-facing host.
- `target-web`: the service the participant is allowed to inspect.
- `target-db`: an internal dependency that stays outside the participant task.
- `security-sensor`: a Suricata-style open-source sensor that emits bounded
  telemetry evidence.
- `model-defense-gate`: a reference policy gate that records tool-use
  allow/deny/bounding provenance.

## Participant

The scenario declares one participant, `paper-agent`, bound to the
`paper-participant` red-role entity. Its authored behavior is intentionally
narrow: inspect `nodes.target-web.services.http` through a model-defense gate
and report a bounded terminal observation. The concrete coding-agent runner is
outside the SDL and is referenced only through
`participant-implementation-manifest:paper-agent` in the behavior
specification.

## Declared Action

`inspect-service` is the governed action contract. It records the participant's
authority, target, realization preconditions, portable effect classes, failure
classes, backend diagnostic mappings, and a shared-state interaction over the
target service. It also declares two non-primary evidence effects: defender
telemetry from the Suricata-style sensor and model-defense provenance from the
policy gate. The contract does not embed commands, prompts, runner config,
backend-native action labels, Suricata rule bodies, or model-defense policy
internals.

## Observation Boundary

`paper-agent-view` separates the public task brief, hidden target-service state,
hidden internal dependency, evidence-only defender telemetry, evidence-only
model-defense provenance, and adjudication-only evaluator notes. The target web
service becomes discovered only after the terminal participant observation,
while `nodes.target-db.services.postgres`, `nodes.security-sensor`,
`nodes.model-defense-gate`, and `content.evaluator-notes` remain outside the
participant view.

## Expected Evidence

The expected evidence is deliberately bounded:

- `content.participant-observation`: the participant runtime observation
  envelope.
- `content.sensor-telemetry`: a compact defender telemetry record.
- `content.defense-decision-log`: model-defense allow/deny/bounding
  provenance.

The objective and outcome interpretation rule use those evidence records to
support the paper demonstration without treating local action success as broad
benchmark success, defensive effectiveness, or model-defense robustness.

## Runtime Binding

The runtime/backend binding is intentionally a downstream concern. A reference
emulation backend or APTL realization should bind `paper-agent` to a
participant implementation manifest and provenance record, route the declared
`inspect-service` action through the model-defense gate, and retain the
participant, sensor, and defense evidence records through existing participant
runtime contracts. That binding must not require new SDL syntax, a new backend
manifest shape, or APTL-private keys inside the scenario body.

## Downstream Links

- ACES issue: Brad-Edwards/aces#598
- Parent APTL proof issue: Brad-Edwards/aptl#554
- Related ACES issues: Brad-Edwards/aces#197, Brad-Edwards/aces#171,
  Brad-Edwards/aces#221, Brad-Edwards/aces#317,
  Brad-Edwards/aces#318

This ACES scenario does not close Brad-Edwards/aptl#554. It supplies the
ACES-side authored scenario that downstream APTL/backend realization and n=2
proof issues can consume.

## Limitations

- The scenario proves SDL parsing, semantic validation, and processor
  compilation of the participant handoff surfaces.
- It does not claim purple-team benchmark coverage or autonomous-agent
  capability.
- It does not evaluate Suricata detection quality or model-defense robustness.
- It does not include a private runner command, prompt, sandbox policy,
  credential, backend log, Suricata ruleset, model-defense policy body, or
  hidden answer key.
- It is designed for small reference-emulation topologies and should remain
  reusable as a corpus example.
