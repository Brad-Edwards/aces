# Issue 516 Inventory Redaction Boundary Preflight

This note is architecture guidance for the issue 516 documentation and
workflow cleanup. It is not an implementation plan and does not replace the
canonical methodology, skill, or runtime ADRs.

## Architecture Decisions

- ADR-057 is the controlling secret-boundary decision for scenario inventory.
  A scenario-target value that a participant or in-range agent can discover is
  scenario content, even when it is a password, token, private key, bcrypt
  hash, generated service secret, config secret, or other credential-shaped
  value.
- Source inventory bundles are authoritative capture artifacts, not sanitized
  publication views. Sanitized exports may redact scenario secrets later, but
  that is a separate projection concern and must not change the source bundle.
- Operator and out-of-scenario secrets remain outside the inventory boundary:
  host SSH keys, cloud or CI tokens, maintainer credentials, local control-plane
  secrets, unrelated prior-run transcripts, and other values that are not facts
  of the described target system must not be captured as scenario facts.
- APTL #341 would have preserved the Wazuh indexer OpenSearch Security
  `internal_users.yml` bcrypt hashes in the source evidence bundle because they
  are target configuration facts inside the participant range.

## Cross-Cutting Concerns To Reuse

- Inventory authority: `docs/raes/inventory/asset-inventory-methodology.md`
  remains the canonical capture workflow and inclusion rule.
- Agent workflow: `.codex-skills/raes-asset-inventory-capture/SKILL.md` must
  continue to operationalize the methodology without defining a second ledger
  schema or secret taxonomy.
- Template workflow:
  `.codex-skills/raes-asset-inventory-capture/scripts/capture-container-evidence-template.sh`
  is the reusable Docker/Compose capture entry point. It must not keep
  name-based blanket redaction as the default for scenario-target evidence.
- Runtime SDL validation: `runtime_values.enforce_observed_value_redaction()`
  is the canonical helper for explicit `redacted` and `operator_secret`
  omission. `name_indicates_secret()` is advisory only and must not be copied
  into capture-time source evidence policy.
- Ledger accountability: `mapping-ledger.yaml`, `capture-limits.txt`, evidence
  checksums, and the downstream `aptl raes-inventory validate/gaps/schema`
  commands remain the evidence accountability surface.

## Security And Validation Layers

- **Secret-handling surface:** scenario-target secrets pass through unredacted
  when they are participant-discoverable facts. Operator/out-of-scenario
  secrets are excluded or explicitly recorded as capture limits; they are not
  represented as scenario facts.
- **Schema and model validators:** no SDL schema or validator change is
  required for this issue. Existing explicit-redaction validators already
  reject raw values only when the author marks a field `redacted` or
  `operator_secret`.
- **Config and environment shapes:** do not introduce a second env parser,
  secret classifier, or config schema. Capture scripts should parameterize the
  scenario-vs-operator boundary instead of relying on credential-shaped names.
- **OS/process exposure:** capture commands should avoid putting operator
  secrets in argv, logs, tracebacks, or issue comments. Scenario-target secrets
  that are read from target files or target runtime state may appear in source
  evidence, but tooling should still avoid leaking unrelated host/operator
  material through command construction.
- **Error envelopes and observability:** CLI/test/helper failures should report
  narrow diagnostics and avoid dumping host-side command payloads that could
  contain operator secrets.

## Extensibility Seam

The reusable seam is an explicit capture-boundary parameter: target scenario
content versus operator/out-of-scenario material. Future sanitized publication,
teaching, or external-release workflows should consume the source bundle and
emit a redacted projection instead of changing capture semantics or adding a
second source-artifact schema.

## Gotchas And Anti-Patterns

- Do not replace blanket redaction with blanket publication of all host-side
  material. The boundary is participant-discoverable target state.
- Do not require `secret_fixture` for generated scenario credentials, hashes,
  keys, or tokens that are needed to realize or inspect the range. ADR-057 made
  `secret_fixture` an author classification, not a bypass for name-based
  omission.
- Do not update generated schemas under `contracts/schemas/` directly.
- Do not edit accepted ADRs to clean up stale historical language unless the
  change follows ADR-059 with an amendment record and pin update, or a new ADR
  supersedes the old one.
- Do not create a new inventory validator, secret taxonomy, exception
  hierarchy, or logging/redaction utility for this issue.

## Non-Goals

- No change to SDL runtime model semantics.
- No new source evidence schema.
- No implementation of a sanitized export/publication pipeline.
- No change to downstream APTL runtime behavior.
- No broad rewrite of historical preflight notes beyond correcting or marking
  stale guidance that could be reused as current capture policy.
