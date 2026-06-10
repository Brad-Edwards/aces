# ADR-032: Directory and Domain Identity Runtime Surface

## Status

accepted

## Date

2026-05-24

## Context

Issue #401 captures an SDL expressivity gap found while modeling the APTL
TechVault Active Directory container. The inventory includes a domain
authority, directory users, groups, computers, service accounts, service
principals, LDAP/Kerberos-facing services, domain policy, group membership,
and trust-style relationships.

The existing SDL can encode fragments of that state through nearby surfaces,
but none owns the full meaning:

- top-level `accounts` records curated scenario/provisioning account resources
- `entities` and `agents` record participant framing and behavior
- `Node.services` records transport bindings such as LDAP or Kerberos ports
- `runtime.local_identity` records OS-local users, groups, and sudo policy
- `runtime.database_services` records database-local principals
- `runtime.ssh_servers` records SSH daemon policy
- top-level `relationships` records scenario graph edges

Compressing directory/domain identity into those surfaces makes important
facts hard to validate, compare, query, or preserve across scenarios. At the
same time, the surface must not become an Active Directory schema clone.
LDAP/X.500, Kerberos realms, SAML/OIDC identity providers, cloud IAM
directories, SCIM provisioning systems, and authorization systems share enough
identity-authority pressure that the boundary should be provider-neutral.

The design uses primary standards for protocol and object semantics:
LDAP/X.500 directory information models
([RFC 4510](https://www.rfc-editor.org/rfc/rfc4510),
[RFC 4512](https://www.rfc-editor.org/rfc/rfc4512)), Kerberos
([RFC 4120](https://www.rfc-editor.org/rfc/rfc4120)), SCIM
([RFC 7643](https://www.rfc-editor.org/rfc/rfc7643),
[RFC 7644](https://www.rfc-editor.org/rfc/rfc7644)),
[SAML V2.0 Assertions and Protocols](http://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf),
OAuth 2.0 ([RFC 6749](https://www.rfc-editor.org/rfc/rfc6749)),
[OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0-18.html),
[NIST SP 800-63C-4](https://doi.org/10.6028/NIST.SP.800-63C-4),
[NIST SP 800-162](https://doi.org/10.6028/NIST.SP.800-162), and
[NIST SP 800-207](https://doi.org/10.6028/NIST.SP.800-207). It uses
access-control literature, especially Lampson's access matrix, Saltzer and
Schroeder's protection principles, RBAC, and ABAC, to justify separating
subjects, attributes, policies, and authority boundaries. It uses cyber-range
and verification/validation literature as adjacent evidence for why authored
scenario state, observed runtime state, and evidence/telemetry must remain
separate and reviewable. It does not treat any one vendor export format,
BloodHound/OpenGraph graph, OCSF event, UCO object, or backend inspect payload
as the normative SDL shape.

## Decision

### 1. Model identity authorities under node runtime

Directory and domain identity observations belong under `Node.runtime` as a
typed `identity_authorities` inventory.

Each identity authority has a stable `authority_id`, a provider-neutral
`kind`, namespace fields such as domain, realm, issuer, tenant, or base DN,
optional protocol/API service endpoints, subjects, policies, and
relationships.

The owning node is implicit from the enclosing node. Identity authority
services may reference a same-node `Node.services[].name` or qualified
`nodes.<node>.services.<name>` transport binding, but the identity inventory
does not mutate `Node.services`.

### 2. Keep adjacent identity concepts distinct

The new inventory is observed identity-authority state. It must not promote
every directory user, group, device, service principal, or role into top-level
`accounts`.

The boundaries are:

- top-level `accounts` remain curated scenario/provisioning accounts
- `entities` and `agents` remain participant framing and action surfaces
- `runtime.local_identity` remains host-local OS identity state
- `runtime.database_services.roles` remain database-local principals
- `runtime.ssh_servers` remains SSH daemon policy
- control-plane identities remain API caller authentication subjects

Some scenarios may deliberately reference both a top-level account and a
directory subject with similar names. That is valid only because the meanings
are different.

### 3. Use stable ids and typed relationships

Observed names, distinguished names, UPNs, SPNs, issuers, and group names are
data. They may be provider-specific, case-sensitive, or unsafe as reference
segments.

The portable reference targets are stable ids:

- `authority_id`
- `service_id`
- `subject_id`
- `policy_id`
- `relationship_id`

Those ids share one authority-local namespace. A `service_id`, `subject_id`,
`policy_id`, or `relationship_id` must not reuse the authority id or any other
stable id in the same authority, because local refs are intentionally bare
symbols.

Membership, trust, federation, sync, delegation, ownership, and association
facts are typed `RuntimeIdentityRelationship` records. Local `source_ref` and
`target_ref` values resolve within the owning authority. Trust/federation to a
system outside the inventory uses `external_target`.

Qualified references are published for every stable id family, for example:

`nodes.<node>.runtime.identity_authorities.<authority_id>`

`nodes.<node>.runtime.identity_authorities.<authority_id>.services.<service_id>`

`nodes.<node>.runtime.identity_authorities.<authority_id>.subjects.<subject_id>`

`nodes.<node>.runtime.identity_authorities.<authority_id>.policies.<policy_id>`

`nodes.<node>.runtime.identity_authorities.<authority_id>.relationships.<relationship_id>`

Those refs participate in generic relationship/objective resolution and module
composition rewrites. Authority-local refs use the same stable id set, so
`source_ref`, `target_ref`, and `applies_to_refs` may target the owning
authority, a service, a subject, a policy, or a relationship without forcing a
fully qualified path inside the authority.

### 4. Model only a neutral core

The initial neutral core is:

- identity authority kind: directory, domain, Kerberos realm, identity
  provider, cloud IAM, authorization system, or other
- authority namespace facts: name, namespace, domain name, realm, issuer,
  tenant id, and base DN
- authority services: protocol/API, address, port, and optional same-node
  transport-service reference
- subjects: users, groups, computers, devices, service accounts, service
  principals, roles, applications, organizational units, and other subjects
- bounded attributes/settings with provenance and value classification
- policies and applies-to refs
- typed membership, trust, federation, sync, delegation, management, ownership,
  and association relationships

Vendor-specific AD DS, LDAP schema, SCIM enterprise, IAM, SAML, OIDC, or UCO
fields may be added later only by extending this neutral seam deliberately. The
base shape must not mirror any vendor schema wholesale.

Provider-stable external identifiers are carried as observed data rather than
ACES reference identity. Where a portable field exists, it is used directly
(`distinguished_name`, `principal_name`, `service_principal_names`, `issuer`,
`tenant_id`, or `base_dn`). Otherwise the identifier belongs in a bounded
attribute or setting with provenance and value classification, for example AD
`objectGUID`/SID, LDAP `entryUUID`, SCIM `id`/`externalId`, SAML NameID, or
OIDC `iss` + `sub`. This lets ACES preserve evidence needed for comparison or
translation without promising provider-level equality semantics across
unrelated authorities.

### 5. Reuse existing SDL gates

The implementation must reuse:

- parser key normalization and variable mapping-key rejection
- `SDLModel` closed-world Pydantic validation
- existing parse helpers such as `require_symbol()`, `parse_int_or_var()`,
  `parse_optional_bool_or_var()`, `parse_runtime_enum_or_var()`, and
  `coerce_string_list()`
- `SemanticValidator` for same-node service refs and authority-local refs
- `instantiate_scenario()` revalidation for variable substitution
- `schema_bundle()`, `tools/generate_contract_schemas.py`, and
  `tools/check_generated_schemas.py`

Generated schemas under `contracts/schemas/` must come from the generator and
must not be edited directly.

### 6. Prevent secret leakage

Directory/authentication material is sensitive. Identity attributes or policy
settings whose names indicate password, credential, Kerberos key, keytab,
private key, token, client secret, or similar material must omit raw values and
use `redacted` or `operator_secret` classification.

SDL examples, fixtures, generated schemas, diagnostics, logs, runtime
snapshots, operation metadata, and process argv must not carry real passwords,
hashes, Kerberos keys, keytabs, certificates, bearer tokens, or client secrets.

Validation errors should name the bad field or reference and must not dump raw
directory exports.

## Guardrails

- Do not add AD-only top-level sections.
- Do not add directory users or groups to top-level `accounts` unless they are
  intentionally scenario/provisioning accounts.
- Do not encode directory membership or trust only as untyped
  `relationships.properties` strings when the runtime authority inventory is
  the semantic owner.
- Do not treat LDAP/Kerberos-facing services as the directory contents.
  Services are endpoints; identity authorities are the modeled state.
- Do not use OCSF, BloodHound/OpenGraph, LDAP dumps, `dsquery`, `ldapsearch`,
  Graph API payloads, or backend inspect output as the canonical authored SDL
  shape.
- Do not create a new parser, schema registry, exception hierarchy, logging
  stack, persistence mechanism, or control-plane authentication model.
- Do not add implementation logic under `implementations/python/src/aces/`;
  that tree is compatibility-only wrappers.

## Non-Goals

- Building an Active Directory, LDAP, Kerberos, SCIM, IAM, SAML, OIDC, or
  BloodHound parser.
- Modeling every AD DS, LDAP, SCIM, IAM, SAML, OIDC, or UCO field.
- Defining backend provisioning behavior for directory authorities.
- Redesigning top-level `accounts`, participant framing, host-local identity,
  database principals, SSH server configuration, runtime snapshots,
  control-plane authentication, persistence, logging, or conformance tooling.
- Updating APTL inventory bundles.

## Consequences

### Positive

- Directory/domain identity state becomes typed, queryable, and schema-covered
  without overloading scenario accounts or host-local identity.
- AD, LDAP, Kerberos, IdP, IAM, SCIM, and federation concepts share a neutral
  runtime seam.
- Existing SDL parsing, validation, instantiation, schema generation, module
  composition, concept-authority posture, and policy gates remain
  authoritative.

### Negative

- The runtime surface gains another optional inventory submodel.
- Some identity refs are long because they include node, runtime, authority,
  and subject context.

### Risks

- A free-form metadata bag would recreate the original semantic loss under a
  new name.
- An AD-specific model would make other identity authorities second-class and
  invite later incompatible surfaces.
- Recording raw directory secrets would leak sensitive material into fixtures,
  generated artifacts, diagnostics, or logs.

## Amendments

| Date | Commit/PR | Summary |
|------|-----------|---------|
| 2026-05-25 | 5e42bd8 | Added primary-standards and access-control literature grounding (LDAP/Kerberos/SCIM/SAML/OAuth/OIDC RFCs, NIST SP 800-63C/162/207, RBAC/ABAC) for identity authorities and authority boundaries. |
