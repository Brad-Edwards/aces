# Formal Specs

Optional formal artifacts for RAES SDL semantic and stateful subsystems live under:

`specs/formal/<domain>/`

Examples:

- `specs/formal/workflows/`
- `specs/formal/objectives/`
- `specs/formal/planner/`
- `specs/formal/runtime-contracts/`
- `specs/formal/participant-semantics/`
- `specs/formal/participant-behavior-model/`
- `specs/formal/participant-runtime/`
- `specs/formal/time-model/`
- `specs/formal/experiment-core/`
- `specs/formal/scenario-variation-trial-realization/`
- `specs/formal/scenario-satisfiability/`
- `specs/formal/exploit-path-analysis/`
- `specs/formal/validation-admission-profiles/`
- `specs/formal/sdl-phases/`

Cross-domain semantic notes that constrain future phases may also live at the
top level when they apply across multiple domains, for example
`specs/formal/composition-readiness.md`.

Each domain directory should include a short README that explains:

- scope
- invariants or properties under study
- relationship to implementation and tests

This directory is intentionally optional. See
`docs/explain/reference/coding-standards.md` and
`docs/decisions/adrs/adr-007-lightweight-formal-methods-policy.md` for the policy on
when formal artifacts are warranted.

The canonical mapping from change classification to verification artifacts
lives in `specs/formal/assurance-policy.yaml`, governed by
`docs/decisions/adrs/adr-018-classification-based-assurance-policy.md` and
gated by `tools/check_assurance_policy.py` (`nox -s policy`).

Per-subsystem **fulfillment** — whether each classified domain above actually
delivers (or explicitly, with an ISO date and tracking reference, waives) the
artifact kinds its FM level requires — is recorded in
`specs/formal/assurance-fulfillment.yaml` and gated by the same checker.
