# Issue 1173 RUN-316 Libvirt Failure Observability Preflight

Date: 2026-09-03

Issue: #1173.

Requirement: RUN-316.

This note narrows the existing RUN-316 guidance to backend failures deliberately
collapsed by the libvirt adapters. It is design guidance only; it adds no
runtime behavior, public contract, configuration, persistence, or evidence.

## Binding Boundaries

- ADR-066 and the issue #338 preflight own observability-plane separation.
  Backend failure records are operator-side apparatus telemetry, not scenario
  observations, experiment evidence, or derived analysis.
- `raes_backend_libvirt.drivers.libvirt._native` remains the single authority
  for libvirt exception identity, native error codes, expected absence, and
  stop/lookup semantics. `raes_backend_libvirt._observability` may format a safe
  record; it must not become a second native-error classifier.
- Existing portable outcomes remain authoritative: `Diagnostic`, `Severity`,
  `DriverResult`, `ApplyResult`, and runtime/control-plane error envelopes.
  Operator logging must not change success, failure, retry, rollback, ownership,
  or fail-closed teardown behavior.
- Use the existing `raes_backend_libvirt` logger and
  `record_suppressed_failure()`. Add no handler, global logging configuration,
  telemetry registry, exception hierarchy, DTO, schema, or store.

## Failure Classification Guardrails

- Every broad catch has exactly one semantic disposition: propagate; recognize
  a proven expected condition and remain silent; or intentionally collapse a
  non-benign failure and emit bounded classification before discarding it.
  Cleanup catches that re-raise, including atomic filesystem cleanup, are not
  suppressed failures and must not be logged as though they were.
- Expected native absence requires both the native exception family and an
  operation-appropriate libvirt code. Duck typing on `get_error_code()` alone
  is insufficient: an unrelated exception exposing that method remains a real
  failure and must not change control flow into an absence/no-op success.
- The existing explicit `KeyError` convention in injected TechVault lookup
  adapters is a narrow absence sentinel at those named lookup seams. It is not
  a package-wide native-error rule and must not make arbitrary `KeyError`
  failures silent elsewhere.
- Reuse the native code vocabulary and predicates owned by `_native`; do not
  repeat numeric absence/operation-invalid literals or create a parallel
  classifier in TechVault or observability modules. Tolerated-code sets remain
  operation-specific so absence, already-inactive teardown, permission failure,
  connection failure, and internal failure cannot collapse into one category.
- The observability path is non-interfering. Classification and formatting must
  be total for arbitrary caught exceptions and must not raise, call exception
  stringification, or replace the portable diagnostic/control-flow outcome.

## Bounded Record Contract

A suppressed-failure record may contain only a fixed internal operation token
and bounded allowlisted scalar classification already supported by
`record_suppressed_failure()`: a sanitized exception type token, an integer OS
`errno`, and an integer native code when safely classified. Operation tokens
must remain code-owned constants, never resource names, addresses, paths, or
caller-supplied text.

Never record exception messages, `repr`, `args`, causes or contexts, tracebacks
or `exc_info`, connection URIs, XML, SDL or plan payloads, environment values,
host paths, subprocess output, native object representations, credentials,
keys, tokens, prompts, hidden truth, or captured evidence. Keep each record
bounded independently of exception or payload size, and keep the library silent
unless the embedding application configures its logger.

## Cross-Cutting Layers

- **Authentication/authorization:** this is an internal backend logging seam,
  not a new API. It adds no authorization shortcut. Any future reader or export
  must use `create_control_plane_app()`, `ControlPlaneSecurityConfig`, target
  binding, the existing `BACKEND`/`OPERATOR`/`AUDITOR` read-role gates, auditing,
  and bounded response models.
- **Secrets and redaction:** the allowlist above is the redaction boundary.
  Exception text and native payloads must not enter logs first and be scrubbed
  later. Existing value-free libvirt diagnostics remain unchanged.
- **Configuration and shape validation:** do not add environment binding or a
  second logger/libvirt config shape. Target construction continues through
  `target._CONFIG_KEYS`, `_validate_config_keys()`, `_driver_config()`,
  `LibvirtDriverMode`, manifest/envelope pairing, and TechVault's
  `validate_driver_configuration()` URI, flag, and name checks.
- **OS/process exposure:** the change adds no subprocess, shell, argv,
  environment dump, file, socket, daemon-inspection, or privilege surface.
  Preserve lazy libvirt loading, structured API calls, ownership UUID checks,
  stop-before-undefine, scoped artifact cleanup, and fail-closed teardown.
- **Error envelopes:** public failures continue through the existing diagnostic
  and apply-result path, then runtime backend-call validation and the control
  plane's redacted HTTP 500 handler. Native details never enter `Diagnostic`,
  snapshot metadata, operation details, audit reasons, or HTTP bodies.
- **Persistence/evidence:** logs remain ephemeral operator telemetry. Do not put
  them in `ControlPlaneStore`, `RuntimeSnapshot`, apparatus summaries, audit
  events, or experiment records merely to make the failure durable. A future
  evidence use requires an explicit experiment-evidence projection with the
  existing provenance, sensitivity, redaction, and authorization contracts.
- **Repository policy:** keep changes within ADR-036 package dependencies and
  ADR-015's 500-line cap. No published schema, schema manifest, generated
  fixture, or changelog change follows from this issue.

## Extension Seam

The extension seam is the native classifier in `_native`: native exception
identity plus an operation-supplied tolerated-code set. Future libvirt
operations or bindings extend that one seam and the existing fixed operation
token vocabulary. They do not add public target configuration, observability
schemas, vendor-specific diagnostics, or per-driver loggers.

## Anti-Patterns And Non-Goals

Avoid raw tracebacks; exception text at any log level; log calls scattered
outside intentional collapse points; treating all code-bearing exceptions as
libvirt errors; globally treating `KeyError` as absence; duplicate error-code
constants or predicates; logging propagated failures as suppressed; changing
portable diagnostics for richer operator detail; and exposing logs through the
operational apparatus summary.

This issue does not redesign RUN-316, scenario-native observability, evidence
capture, the runtime control-plane API, backend manifests, libvirt lifecycle or
ownership semantics, persistence, logger configuration, or experiment
contracts. It does not require a new ADR because ADR-066 already owns the
architectural decision.
