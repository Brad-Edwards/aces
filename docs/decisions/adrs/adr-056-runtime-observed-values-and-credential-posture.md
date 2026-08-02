# ADR-056: Runtime Observed Values and Credential Posture

## Status

accepted

## Date

2026-06-05

## Context

Runtime SDL now has many places that record observed values, settings,
sensitivity or redaction state, provenance, and credential posture. Similar
field names do not always mean the same concept. A database setting, a DNS
setting, a directory attribute, a route-exposed fixture field, a mount source,
a file sensitivity label, and a principal credential posture each carry
different constraints.

The repo already has narrow runtime family ADRs for database, DNS, mail,
security monitoring, identity, datastore, platform applications, forwarding
agents, application authorization, filesystems, mounts, service units, SSH, and
application routes. Those ADRs deliberately preserve local ids, component refs,
scopes, source paths, evidence refs, profile guards, and closed lattices. The
missing design layer is a current cross-surface contract that says which
invariants are shared and which differences must remain family-specific.

## Decision

Adopt a shared observed-value redaction invariant, but do not introduce a
universal `ObservedValue` or `ObservedSetting` model.

### Shared invariant

The common invariant is:

- redacted and operator-secret classifications must omit raw values;
- concrete secret-bearing names must not carry raw values unless the value is
  explicitly classified as a deliberate `secret_fixture`;
- a concrete secret-bearing name with no raw value must use the redaction or
  fixture classification allowed by its surface;
- full `${var}` classification placeholders pass through to instantiation-time
  revalidation;
- the shared secret-name vocabulary is helper logic, not a source of credential
  values.

Realization corroboration follows the same exposure boundary. A runtime
observation disclosure carries only the concern address, field path, kind,
verification scope, and observation strength. It MUST NOT repeat a forwarding
setting, enrollment material, native inspect object, evidence location, or
credential. Secret-safe commitments remain the comparison form for permitted
forwarding settings; observation metadata does not become a second value
carrier.

This invariant is implemented as a shared helper in `runtime_values.py`. Family
models call that helper only where the semantics are actually shared. Family
models still own their ids, refs, scopes, provenance enums, and closed/open
vocabulary choices.

### Surface inventory

| Surface | Concept | Shared semantics | Family-specific semantics |
| --- | --- | --- | --- |
| `runtime.environment` | observed environment key/value | secret-bearing names and redacted/operator-secret values omit raw values; `secret_fixture` may carry a deliberate fixture value | environment provenance uses compose/image/operator/container/runtime classes; names are keys, not stable refs |
| `source.build.build_args` and image default environment | image artifact observed key/value | same value classification and raw-value omission discipline as environment values | artifact provenance, not node runtime state |
| `runtime.applications.routes.exposed_fields` | participant-visible fixture or diagnostic field | redacted/operator-secret fields omit raw values; secret-bearing names require redacted/operator-secret or `secret_fixture` | route exposure metadata is tied to HTTP route inventory, not generic settings |
| `runtime.database_services.settings` | database setting | shared secret-name and raw-value omission helper | observed setting name is data; provenance is database-specific; database ids, roles, grants, engine/protocol pairing remain local |
| `runtime.dns_services.settings` | DNS setting | shared secret-name and raw-value omission helper | DNS setting provenance, zones, RRsets, resolver policy, dynamic update posture, and DNSSEC fields remain DNS-specific |
| `runtime.mail_services.settings` | mail setting | shared secret-name and raw-value omission helper | stable `setting_id`, component refs, source path, mailbox/auth/TLS/queue semantics remain mail-specific |
| `runtime.identity_authorities.subjects.attributes` and policy settings | identity attribute or bounded policy setting | shared secret-name and raw-values omission helper | values are multi-valued; origin and provenance must align; identity refs are authority-local stable ids |
| `runtime.security_monitoring_managers.settings` | manager setting | shared secret-name and raw-value omission helper | stable `setting_id`, component refs, source path, content/detection/agent refs, and manager-specific provenance remain local |
| `runtime.datastore_services.settings` | scoped datastore setting | shared secret-name and raw-value omission helper | `scope`, datastore provenance, data-model profile guard, cluster/persistence/transport posture, and datastore refs remain local |
| `runtime.platform_applications.settings` | platform setting | shared secret-name and raw-value omission helper | closed platform setting classification; capability, legacy category/content, marking, connector, and upstream-binding semantics remain local |
| `runtime.forwarding_agents.settings` | forwarding agent setting | shared secret-name and raw-value omission helper | forwarding source/transform/ship-target/buffer/reload profile guards remain local |
| `runtime.mounts` and `runtime.local_control_interfaces` | path and option sensitivity | redacted/operator-secret path or option classifications omit raw path/option values | source kind, propagation, backend-generated flag, control interface kind, and named-pipe validation remain path/control-specific |
| `runtime.filesystem_inventory` | observed filesystem entry | sensitivity classification and provenance are explicit | presence, digest pairs, mode/owner/size constraints, and present-only fields remain filesystem-specific |
| `runtime.container`, `runtime.health`, `runtime.service_units`, and `runtime.ssh_servers` | command, argv, log, and process redaction | redaction booleans/kinds omit command, argv, or output values | service-manager, SSH, init process, and healthcheck semantics are not generic key/value settings |
| `runtime.app_authorizations.principals` | credential posture | raw credential fields are unrepresentable | closed `none`/`redacted`/`operator_secret` posture; principal/role/grant/resource semantics remain RBAC-specific |
| `runtime.mail_services.mailboxes`, `runtime.file_services.principals`, `runtime.platform_applications.connectors`, and forwarding ship targets/edges | credential posture or strength | raw credential fields are unrepresentable or refs require redacted/operator-secret posture | strength/posture vocabularies stay separate from settings; connector/enrollment/mailbox/file-service semantics remain local |
| `runtime.software_components`, `runtime.packages`, `runtime.dependency_manifests`, and package vulnerabilities | observed software and scanner provenance | provenance/evidence is explicit and raw scanner payloads are not the portable model | package, purl/CPE/hash, manifest, vulnerability, scan-time, and component-type constraints remain software-specific |
| `runtime.scheduled_jobs`, `runtime.network_sensors`, `runtime.network_detection_engines`, `runtime.service_listeners`, and `runtime.orchestration_authorities` | runtime posture and relationships | no raw credential value surface is introduced | their discriminators, refs, profile guards, cadence, detection content, listener, and orchestration semantics remain family-specific |

### Credential posture and credential strength

Credential posture answers whether a credential is absent, present but
redacted, operator-controlled, or intentionally modeled as fixture data.
Credential strength answers whether a credential is weak, strong, default,
rotated, MFA-backed, policy-compliant, or similar. These are different claims
and must not be collapsed into one enum.

Posture-only surfaces must not gain a `value`, `raw_value`,
`credential_value`, `password`, `secret`, `api_key`, or hash field. Setting
surfaces may carry a `value` only when the classification allows it.

### Enum openness and closedness

Observed open taxonomies carry both `unknown` and `other`. Closed structural or
redaction lattices carry neither unless an existing family ADR says otherwise.
`RuntimeEnvironmentValueClassification` remains an open observed-value
taxonomy and includes `operator_secret` so environment and image-default values
can express withheld operator-controlled material while keeping
`secret_fixture` for deliberate exercise disclosure.

### Schema and validation

The Python model validators are the primary semantic gate. JSON Schema
generation publishes enum and shape changes, and custom schema extras remain
appropriate for structural path/raw-value constraints such as mounts and bind
sources. Generated schemas must be regenerated from model inputs rather than
edited directly.

## Consequences

Positive consequences:

- Shared raw-value omission is reviewable in one helper and covered by
  cross-surface tests.
- New runtime families can opt into the helper without giving up stable ids,
  refs, scopes, provenance, or closed profile guards.
- Deliberate fixture values remain explicit through `secret_fixture` instead of
  being confused with operator secrets.
- Credential posture-only models remain unable to carry raw credential values.

Trade-offs and risks:

- There is still no single setting base class; contributors must choose the
  right family model and helper parameters.
- The helper cannot prove semantic secrecy from values themselves; it only
  enforces name and classification invariants.
- JSON Schema cannot express every semantic validator in the Python models, so
  generated schema drift checks and model-level tests remain necessary.

Rejected alternatives:

- A universal observed-value model was rejected because it would erase
  required differences such as datastore scope, mail component refs, identity
  multi-values, DNS provenance, and platform closed lattices.
- A free-form `raw_value` plus documentation warning was rejected because it
  would make raw secret omission advisory instead of executable.
- Folding credential strength into credential posture was rejected because it
  would conflate presence/redaction with quality or assurance.

## Amendments

| Date | Commit/PR | Summary |
|------|-----------|---------|
| 2026-07-13 | #417 | Narrowed the authored SDL boundary: health results, generated network identity, scanner-derived package findings, and scanner capture provenance use evidence/derived carriers rather than `Node.runtime`; the shared redaction invariant continues to govern the remaining declarative runtime fields. |
| 2026-07-29 | #956 | Removed the obsolete platform-kind profile-guard claim; platform capability and legacy category/content semantics remain family-local while shared explicit-redaction handling is unchanged. |
| 2026-08-01 | #1043 | Applied the raw-value omission boundary to forwarding-agent realization observation disclosures. |
