# ADR-057: Runtime Scenario Value Realizability and Explicit Redaction

## Status

accepted

## Date

2026-06-06

## Context

[ADR-056](adr-056-runtime-observed-values-and-credential-posture.md) adopted a
shared observed-value helper for runtime SDL surfaces. Its original invariant
combined two different rules:

- explicit `redacted` and `operator_secret` classifications omit raw values;
- concrete names that looked secret-bearing also forced raw-value omission,
  except for deliberate `secret_fixture` values.

Issue #471 first exposed false positives in that name-derived omission rule:
`GPG_KEY` can be a public package-signing fingerprint, `secret_key_length` can
be an integer, `LABADMIN_SSH_KEY_FILE` can be a path, and `PWD` can be a working
directory. The downstream APTL TechVault inventory then exposed the deeper
problem: the SDL is consumed by a backend to stand up a synthetic range. Runtime
values such as Wazuh API credentials, OpenSearch `internal_users` hashes,
mutual-TLS key material, Flask/JWT weak secrets, database passwords, and image
environment defaults are not incidental leaks from an operator system; they are
scenario facts required for realization and, often, participant exploitation.

The ACES lineage supports that distinction. ADR-026 records route-visible
application facts as participant-observable scenario surface. ADR-033 separates
portable scenario/runtime evidence from backend-native payloads and keeps
withholding as an explicit classification. ADR-056 correctly keeps credential
posture, credential strength, and observed settings distinct, but its
name-based omission rule overreached for SDL scenario values. The lineage guide
frames ACES as a scenario-meaning layer, not a sanitizer for an operator's
out-of-scenario host, cloud, CI, or SSH credentials.

## Decision

Drop the secret-name omission obligation from SDL runtime validators. This
decision supersedes the name-driven omission clauses in ADR-056 and in earlier
runtime-family ADRs while preserving their explicit-redaction clauses.

`enforce_observed_value_redaction()` now enforces only explicit withholding:
when a value is classified as `redacted` or `operator_secret`, the raw value
must be omitted. A field name such as `JWT_SECRET`, `DB_PASSWORD`,
`admin_password`, `api_key`, `update_key`, `GPG_KEY`, `PWD`, or
`secret_key_length` does not by itself require omission or a redaction
classification. The same rule applies across runtime environment variables,
image build arguments, image default environment, route exposed fields,
database/DNS/mail/identity/security-monitoring/datastore/platform/forwarding
settings, and other surfaces using the shared helper.

Posture-only models also must not infer mandatory redaction from a name.
Application-authorization principals and platform connectors may still carry an
explicit credential classification, but a secret-shaped `name` alone does not
make `none` or `plain` invalid. Those models still carry no raw credential
value fields.

`secret_fixture` remains meaningful as an author classification for deliberate
exercise fixtures, but it is no longer a bypass around a name-derived omission
rule. Generated scenario credentials and keys that are required to realize the
range may be recorded as ordinary scenario content unless the author explicitly
chooses to withhold them.

`runtime_values.name_indicates_secret()` may remain as advisory helper logic for
future defaults, warnings, or user-interface hints, but it is not a validation
gate for raw-value omission.

Operator secrets are out of scope for SDL node inventory. Host SSH keys, cloud
credentials, CI tokens, and other real operational secrets must not be captured
as facts of a described scenario system. If a projection or publication channel
needs a sanitized view of an SDL, that is a separate export/redaction concern,
not a structural-validity rule for the authoritative scenario specification.

## Consequences

Positive consequences:

- Scenario documents remain executable: generated credentials, hashes, keys,
  route-visible weak secrets, and other scenario values are available to the
  backend that realizes the range.
- False positives from name heuristics no longer block SDL parsing for paths,
  public key fingerprints, working-directory variables, or scalar metadata.
- Explicit redaction remains enforceable and centralized: a field classified
  `redacted` or `operator_secret` still omits raw values across the runtime
  families.
- The difference between scenario content and operator environment secrets is
  documented instead of hidden inside a brittle classifier.

Trade-offs and risks:

- SDL artifacts may contain exploit-relevant scenario credentials. That is a
  property of executable range content, not an accidental leak, and downstream
  handling must treat authoritative SDL files accordingly.
- Name heuristics no longer provide fail-closed protection against an author
  accidentally inventorying an out-of-scenario operator secret. The mitigation
  is capture-boundary discipline and optional advisory tooling, not structural
  omission of scenario values.
- Sanitized external publications require a projection/export redaction layer
  if they should hide scenario credentials while preserving the authoritative
  executable SDL.

## References

- Issue #471: Runtime SDL secret-name omission rule cannot represent
  intentional disclosed weak-credential values
- Issue #471 reframing comment: Runtime value omission is a realizability
  defect for SDL scenario content
- [ADR-026: Application HTTP Surface Inventory](adr-026-application-http-surface-inventory.md)
- [ADR-033: Scenario/Delivery Boundary for Runtime Node State](adr-033-scenario-delivery-boundary-for-runtime-node-state.md)
- [ADR-056: Runtime Observed Values and Credential Posture](adr-056-runtime-observed-values-and-credential-posture.md)
- [Lineage and Prior Work](../../explain/sdl/lineage.md)
