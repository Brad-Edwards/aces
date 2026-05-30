# ADR-047: Scheduled-Job Runtime Inventory

## Status

accepted

## Date

2026-05-30

## Context

The SCN-010 expressivity gap analysis (issue #441) identifies recurring
node-scoped scheduled work as a shared gap (gap IDs MISP-DSS-02 and TIP-004),
observed at `misp-suricata-sync` (a 300-second IOC-to-rule pull loop), MISP's
scheduled jobs, and the indexing/ISM cadences of search clusters. The defining
fact is a recurrence cadence plus observed run-state for a recurring job, and no
existing runtime surface can carry it.

Adjacent surfaces each own narrower meaning:

- `runtime.service_manager_units` carries systemd-scoped unit lifecycle
  (load/active/enabled/exit-code/main-pid), including the `timer` unit kind. It
  is structurally systemd-scoped: a bare-container ENTRYPOINT cadence loop has
  no systemd unit and cannot be encoded there.
- A recurring forwarder's inputs, transforms, and ship targets are the
  forwarding agent's concern; re-encoding them on the job would double-encode the
  same fact.
- An event-triggered task is a trigger relationship, not a recurrence.

The design risk is to force scheduled work into a fake systemd timer unit, to
re-encode forwarder inputs/outputs on the job, or to model event triggers as
recurrences.

## Decision

### 1. Add a node-scoped scheduled-job surface, cadence-only

Add `Node.runtime.scheduled_jobs` as an observed runtime inventory surface. Each
entry is a `RuntimeScheduledJob` with a stable `scheduled_job_id`, an `enabled`
flag, an optional `command_ref`, an optional `schedule`, and an optional
`run_state`. The surface is deliberately hollowed to cadence plus run-state
only.

### 2. Closed recurrence vocabulary plus observed run-state

The `schedule` carries a closed structural `kind` (`interval`, `cron`,
`calendar`) and an opaque `spec` string. Because the recurrence vocabulary is a
fixed structural set (POSIX crontab / RFC 5545 RRULE / fixed interval), the
`kind` carries neither `unknown` nor `other`. The `run_state` records observed
`last_run`/`next_run` timestamps and an open `last_result` outcome (`success`,
`failure`, `pending`, `unknown`, `other`).

### 3. Exclude inputs, outputs, and trigger targets

Per the adversarial verdict, `inputs`, `outputs`, and `trigger_targets` are
removed: they belong to the referencing forwarding agent, fencing off the
double-encoding hazard. The `event` schedule member is dropped — event-triggered
work is a trigger relationship, not a recurrence. The Resque `queue_role` facet
is dropped as vendor-config-shaped; worker pools are modeled as `processes` plus
per-worker `scheduled_jobs`.

### 4. Keep scheduled-job inventory targetable but not executable

Scheduled jobs may be referenced from relationships using the qualified ref
`nodes.<node>.runtime.scheduled_jobs.<scheduled_job_id>`. These refs are
inventory targets; they do not imply schedule execution or job dispatch.

## Security and Validation Gates

- Parser/model gate: stable scheduled-job ids are concrete symbols, not
  variables, and are unique within a node runtime block. The `schedule.kind` is
  a closed enum; `run_state.last_result` is an open enum.
- Boundary gate: the `scheduled_jobs` / `service_units` / `forwarding_agents`
  triple boundary is documented in `validation.md` — systemd lifecycle stays in
  `runtime.service_manager_units`, forwarder inputs/outputs stay in the
  forwarding agent, and only cadence plus run-state lives here.
- Relationship/reference gate: scheduled-job qualified refs resolve in generic
  relationships and survive module import namespacing.
- Contract/schema gate: published schemas are regenerated from Python model
  sources; generated JSON schemas are not edited by hand.

## Guardrails

- Do not model scheduled jobs as fake systemd timer units.
- Do not re-encode forwarder inputs, outputs, or ship targets on the job.
- Do not model event-triggered tasks as recurrences.
- Do not add an `unknown`/`other` member to the closed `schedule.kind`
  recurrence vocabulary.

## Non-Goals

- Implementing schedule execution, job dispatch, or backend scheduler behavior.
- Replacing POSIX crontab, RFC 5545, systemd.timer, or Kubernetes CronJob
  semantics.
- Redesigning `runtime.service_manager_units` or the forwarding-agent surface.

## Consequences

### Positive

- Recurring node-scoped work becomes typed, targetable, and validation-backed as
  a small cadence-plus-run-state primitive shared across forwarders and indexing
  cadences.
- The cadence-only shape avoids double-encoding what a recurring forwarder ships.

### Negative

- Node runtime gains another optional inventory surface.
- Consumers needing full job input/output semantics must compose the referencing
  forwarding agent.

### Risks

- Treating run-state evidence as proof of successful execution would overclaim
  what the SDL can validate; `run_state` is observed evidence, not control
  intent.

## References

- [Service-Manager Unit State Runtime Surface](adr-035-service-manager-unit-state-runtime-surface.md)
- [Scenario/Delivery Boundary for Runtime Node State](adr-033-scenario-delivery-boundary-for-runtime-node-state.md)
- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md)
