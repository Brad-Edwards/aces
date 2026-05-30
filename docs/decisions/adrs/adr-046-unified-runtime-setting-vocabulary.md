# ADR-046: Unified Runtime Setting Vocabulary

## Status

accepted

## Date

2026-05-30

## Context

Runtime inventories added for database, DNS, mail, security monitoring,
directory identity, filesystem, and environment facts all needed to describe
observed configuration values. Before issue #440, ACES had separate setting
models, separate provenance enums, two sensitivity enums, two credential
classification enums, and several non-equivalent secret-name classifiers.

That made the SDL's redaction guarantee depend on which runtime family observed
a fact. For example, the same `api_key`, `credential`, `token`, or hyphenated
setting name could be accepted as plain in one surface and rejected in another.
For a peer-reviewed SDL this is a model soundness problem: observed state must
have one portable vocabulary and one secrecy policy.

## Decision

### 1. Add a canonical observed-setting model

`RuntimeObservedSetting` is the shared model for observed runtime settings. It
contains:

- optional `setting_id` for families that need stable local setting refs;
- optional `component_ref` for component-scoped settings;
- `name`;
- scalar `value` or multi-valued `values`;
- unified `value_classification`;
- unified `provenance`;
- optional `source` and `source_path`;
- `description`.

Database settings, DNS runtime settings, mail settings, security-monitoring
settings, identity attributes/policy settings, and runtime environment
variables are aliases of this model. The old public names stay importable for
source compatibility, but they no longer define independent schemas or
validators.

### 2. Unify setting provenance without erasing distinctions

`RuntimeSettingProvenance` is the setting provenance taxonomy. It preserves all
previous family-specific values, including `compose`, `image`, `operator`,
`container`, `runtime`, `introspection`, `configuration_file`,
`command_output`, `environment`, `api`, `image_default`, `operator_override`,
`runtime_default`, `built_in`, `directory`, `synchronized`, `federated`,
`provisioned`, `runtime_created`, `unknown`, and `other`.

Identity settings may still be authored with `origin`; that key maps to
`provenance` so existing captures can migrate losslessly while the schema
surface exposes the unified concept.

### 3. Unify sensitivity and credential classification separately

`RuntimeSensitivityClassification` is the value sensitivity and redaction
classification for observed runtime values. It is separate from
`RuntimeCredentialClassification`, which describes credential strength or
posture (`no_credential`, `weak`, `default_or_trivial`, `fixture`, `strong`,
`redacted`, `unknown`, `other`) and never stores a raw credential.

This separation is deliberate. A redacted setting value is not the same concept
as a weak or strong credential.

### 4. Use one secret-name policy

All shared observed settings use one secret-name classifier. Secret-bearing
names include password/passphrase/pwd forms, credentials, tokens, connection
info, private-key labels, keytab labels, DNS signing labels,
access/auth/client-key labels, Kerberos key attributes, and common fixture or
service-specific secret labels.

If a concrete setting name is secret-bearing, raw `value` and `values` must be
omitted. The setting must use `redacted`, `operator_secret`, or
`secret_fixture` classification. `secret_fixture` is valid only as an explicit
fixture classification; it does not allow raw values for secret-bearing names.
The classifier does not treat exact current-directory labels such as `PWD`, or
metadata identifiers such as `*_key_id`, as secret material by name alone.

### 5. Publish the unified schema

The generated SDL schemas expose `RuntimeObservedSetting`,
`RuntimeSettingProvenance`, `RuntimeSensitivityClassification`, and
`RuntimeCredentialClassification` rather than stale per-family setting copies.

## Security and Validation Gates

- Model gate: one `RuntimeObservedSetting` validator normalizes provenance,
  sensitivity, scalar/multi-valued shape, source paths, and redaction.
- Parser gate: kebab-case authoring keys normalize into the unified model.
- Secret gate: secret-bearing concrete setting names must omit raw values
  across database, DNS, mail, security monitoring, identity, and environment
  surfaces.
- Schema gate: published SDL JSON schemas are regenerated from the unified
  Pydantic models.
- Compatibility gate: old public class and enum names remain importable as
  aliases, but they do not define separate semantics.

## Guardrails

- Do not add new family-local setting models for runtime configuration facts.
- Do not add a family-local secret-name matcher.
- Do not collapse credential strength into value sensitivity.
- Do not map identity `origin` into provenance unless the original value is
  preserved by the unified taxonomy.
- Do not pass real secret values through migration scripts, command-line
  arguments, logs, diagnostics, or schema fixtures.

## Non-Goals

- Modeling raw vendor configuration files as SDL records.
- Building a capture migration tool in the SDL package.
- Removing compatibility import names in this change.
- Changing filesystem, application-disclosure, or mount sensitivity semantics
  beyond their use of the shared sensitivity enum.

## Consequences

### Positive

- Observed settings have one model and one redaction policy.
- Secret-name decisions are deterministic across runtime families.
- Schema reviewers can inspect one setting/provenance/sensitivity contract.
- New runtime families can reuse the canonical setting model without adding
  copy-pasted validators.

### Negative

- Published SDL schemas change substantially because repeated per-family
  setting definitions collapse into one shared definition.
- Existing fixture examples with raw values under secret-bearing setting names
  must migrate to non-secret fixture markers or omit raw values.

### Risks

- A broadened secret-name policy can expose previously accepted raw values in
  captures. Capture reconciliation must audit every setting name rather than
  sampling.
- Compatibility aliases may make source code migration appear complete before
  downstream captures have moved to the unified schema. The published schema is
  the authority for the model shape.

## References

- Issue #440.
- [SDL Runtime Layer](adr-004-sdl-runtime-layer.md).
- [Directory and Domain Identity Runtime Surface](adr-032-directory-domain-identity-runtime-surface.md).
- [Runtime File-Service and Filesystem Presence Semantics](adr-037-runtime-file-service-and-filesystem-presence-semantics.md).
- [Runtime Mail-Service Logical State](adr-038-runtime-mail-service-logical-state.md).
- [DNS Service Runtime Inventory](adr-039-dns-service-runtime-inventory.md).
- [Security-Monitoring Manager Runtime Inventory](adr-040-security-monitoring-manager-runtime-inventory.md).
- [Lineage and Prior Work](../../explain/sdl/lineage.md).
