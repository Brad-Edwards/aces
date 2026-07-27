# Autonomous Execution V2 Migration

`participant-autonomous-execution/v2` is an explicit opt-in profile for
ordinary participant activity with governed work windows, bounded timing
variation, weighted candidates, dependencies, retries, cooldowns, and bursts.
It does not change the meaning of existing
`participant-autonomous-execution/v1` documents.

## Existing V1 Scenarios

No migration is required. Keep the v1 cadence constraint, `action_order`,
`ordered_cycle`, and existing finite attempt/in-flight limits. Omitting
`profile` continues to select v1. A v1 backend declaration must now list the
exact `participant-autonomous-execution/v1` policy profile and the occurrence,
retry, and burst capability limits used for common admission accounting.

## Opting Into V2

Replace v1 cadence/order fields with the explicit v2 shape:

```yaml
autonomous_execution:
  profile: participant-autonomous-execution/v2
  participant_implementation_ref: participant-implementation-manifests.green-worker.v1
  clock_ref: scenario-clock
  progression_policy_ref: scenario-progression
  work_window_refs: [work-window]
  pause_window_refs: [break-window]
  observation_boundary_ref: participant-view
  stochastic_control_ref: green-activity-policy
  selection_strategy: weighted
  timing:
    minimum_ticks: 10
    maximum_ticks: 30
  outside_window_disposition: next_opening
  empty_eligible_disposition: complete
  action_candidates:
    portal-login:
      action_ref: probe-customer-portal-login
      weight: 3
      depends_on: []
      retryable_failure_classes: [target_unavailable, timeout]
      max_retries: 2
      cooldown_ticks: 20
  max_occurrences: 8
  max_action_attempts: 24
  max_burst_size: 2
  max_in_flight: 1
  failure_policy: continue
  evaluation_authority:
    mode: none
```

Work and pause refs must resolve to finite shared-time `window` constraints on
the policy clock and name the behavior specification or every governed
participant as a subject. Windows are half-open `[start, end)`. On stepped
clocks, timing bounds must be multiples of `step_ticks`.

The SDL contains only `stochastic_control_ref`. Run apparatus must supply an
exact `agent-policy` control bound to `blake3-xof-participant-v1`, a namespace,
and public seed or resolvable governed entropy. Seeds do not belong in SDL.
The reference runtime currently fails closed for governed entropy because no
authorized resolver is installed.

Backends must explicitly advertise the v2 profile, all activity features,
weighted selection, the participant random-stream profile, window support, and
finite occurrence/retry/burst limits. Existing v1 capability claims do not
implicitly admit v2.

Runtime snapshots gain typed v2 continuation fields, and participant behavior
history gains safe activity occurrence provenance. Consumers should preserve
unknown optional fields when forwarding current contract payloads. No new API
endpoint or private scheduler state surface is introduced.
