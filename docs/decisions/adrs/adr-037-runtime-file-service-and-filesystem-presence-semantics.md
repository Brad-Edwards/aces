# ADR-037: Runtime File-Service and Filesystem Presence Semantics

## Status

accepted

## Date

2026-05-26

## Context

Issue #421 identifies an SDL expressivity gap while encoding the APTL
TechVault `fileshare` container inventory. The current model can record the
transport listener in `Node.services` and present paths in
`runtime.filesystem_inventory`, but it cannot represent SMB/Samba share
topology, service-local Samba accounts, share authorization, probe outcomes, or
expected runtime paths that were absent at capture time without collapsing those
facts into prose or `other`.

The repository already has adjacent surfaces:

- `Node.services` records transport bindings such as TCP/445.
- `runtime.network.published_ports` records host/OS publication.
- `runtime.applications` records HTTP route/API/UI inventory only.
- `runtime.local_identity` records OS-local `/etc/passwd`, `/etc/group`, and
  sudo facts.
- `runtime.identity_authorities` records directory/domain/realm/IdP/IAM
  authorities.
- `runtime.database_services` records database-local principals and grants.
- `runtime.ssh_servers` records SSH daemon policy.
- `runtime.filesystem_inventory` records runtime filesystem entries by path.
- top-level `accounts` records curated scenario/provisioning account resources.
- top-level `relationships` records typed scenario graph edges.

The design risk is to overload one of those nearby concepts and make transport
ports, HTTP applications, OS users, directory subjects, scenario accounts,
Samba passdb rows, file-share resources, filesystem ACLs, observed probes, and
expected absence all mean the same thing.

The required source review points in one direction:

- Open Cyber Range SDL, CyRIS, KYPO topology definitions, VSDL, and CRACK model
  scenario topology, deployable services/features, accounts, tasks, and
  validation/deployment concerns. They do not provide a portable first-class
  share-permission/passdb inventory that ACES can reuse directly.
- OCSF is event/log normalization, STIX gives typed relationship edges, CASE
  and UCO emphasize evidence/provenance and cyber object concepts, and SBOM
  standards inform component identity. They support ACES's separation among
  runtime inventory, evidence, relationships, and component metadata, but none
  should be imported as the authored SDL file-share schema.
- The identity-authority sources already cited in `lineage.md` support a
  subject/resource/action/policy split. LDAP/X.500, Kerberos, SCIM, SAML/OIDC,
  Lampson's access matrix, Saltzer/Schroeder, RBAC96, and NIST ABAC all argue
  against hiding authorization semantics inside prose fields.
- SMB/CIFS, Samba, POSIX ACLs, Windows security descriptors/ACE/DACL, and
  NFSv4 ACLs show that file-service authorization has share-level resources,
  principals, actions, access masks or ACL entries, guest/anonymous behavior,
  and backend filesystem enforcement. They also show that those mechanisms are
  not one portable vendor-neutral ACL algebra.
- Zanzibar/ReBAC-style relationship tuples are useful design input for
  subject-relation-resource modeling at scale, but they are not the ACES SDL
  schema and should not force a global authorization-system abstraction into
  node runtime inventory.

This is therefore a systemic non-HTTP runtime-surface limitation, not just an
SMB enum gap.

## Decision

### 1. Model file services under node runtime

Add a node-scoped runtime file-service inventory, for example
`Node.runtime.file_services`, when implementation work begins.

The surface is observed runtime state for services that expose file-like
resources over a protocol: initially SMB/Samba, with a deliberate seam for NFS,
FTP/SFTP, WebDAV, object-store APIs, and similar services later. It must not be
added to `runtime.applications`, and `RuntimeApplicationProtocol` must not grow
`smb` merely to make the parser accept TechVault data.

Each file service should have a stable id, a same-node owning `Node.services`
reference, bounded service/protocol kind fields, optional version/backend facts,
shares/resources, service-local principals, policy/rule records, and observed
access outcomes. The owning node is implicit from the enclosing node. The
transport service remains explicit through the existing same-node service-ref
pattern.

### 2. Keep shares/resources, principals, policies, and observations distinct

The model should keep these facts separate:

- share/resource identity: stable id, observed share name, optional local path,
  comment/label, browseability/listability, read-only posture, and resource
  kind;
- service-local principals: Samba/passdb or equivalent service-local accounts,
  groups, aliases, anonymous/guest subjects, and optional links to OS-local or
  directory subjects;
- authorization assertions: subject ref, resource ref, action, effect, scope,
  and basis/provenance;
- access observations: who/what was used to probe, what action was attempted,
  what outcome was observed, and whether the result is evidence rather than
  asserted policy;
- filesystem entries: path-level presence, type, ownership, mode, hashes, and
  sensitivity when the path itself is part of runtime filesystem inventory.

Do not let a share name become the stable reference id unless it already passes
the repo's stable-symbol rules. Observed names are data and may be
case-sensitive, backend-specific, localized, or unsafe as reference segments.

### 3. Represent share access as portable subject/resource/action facts

Share access should be represented through a bounded portable access-policy
shape, not through raw `smb.conf`, Windows DACLs, POSIX ACLs, NFSv4 ACEs, or
Zanzibar tuples.

The portable core is:

- subject: service-local principal, guest/anonymous subject, local OS identity
  ref, identity-authority subject ref, group ref, or external subject label;
- resource: file-service share/resource ref, optionally narrowed to a path
  under that share;
- action: browse/list, read, write/create, delete, execute/traverse,
  administer, or other;
- effect/outcome: allow, deny, not_applicable, unknown, or probe-specific
  success/failure classes;
- basis: share configuration, service passdb/account data, filesystem
  permission/ACL, directory/domain policy, observed probe, scanner evidence,
  computed effective access, unknown, or other.

Vendor-specific ACL details may be retained only as bounded evidence or
settings with explicit provenance and redaction. They must not become the
portable ACES rule language.

### 4. Model Samba passdb as service-scoped identity, not OS or scenario identity

Standalone Samba passdb rows such as `nobody` and `svc-fileshare` are
service-local principals. They do not belong directly in top-level `accounts`,
`runtime.local_identity`, or `runtime.identity_authorities`.

The file-service surface should own passdb-like records with fields for stable
principal id, observed account name, account kind/status, SID/RID when known,
credential-strength classification, origin/provenance, and optional account
control flags. Passwords, NT hashes, LM hashes, Kerberos keys, private keys,
bearer tokens, and captured credentials must be omitted or classified with the
existing redaction vocabulary.

When a service-local account maps to an OS-local user, use an optional ref to
`runtime.local_identity.users` and cross-check it only when local identity
inventory is present. When a file service is domain-backed, reference
`runtime.identity_authorities` subjects rather than cloning directory state into
the file-service model.

### 5. Record probe outcomes as evidence-bearing observations

Observed per-share access outcomes are evidence, not automatically policy.

An implementation should represent probe outcomes as bounded records under the
file-service inventory, with subject/resource/action/outcome/provenance fields
and redacted tool details. A successful `smbclient` read, a denied anonymous
write, or a not-found path result is an observation that may support a policy
claim, but it must not silently overwrite configured share policy or filesystem
permission facts.

Participant-specific visibility still belongs in observation boundaries and
participant behavior surfaces. The file-service inventory records runtime state
and evidence; it does not decide which participant can see each fact.

### 6. Add filesystem presence state, not an `absent` entry type

Do not add `absent`, `expected_absent`, or similar values to
`RuntimeFilesystemEntry.entry_type`. `entry_type` is the file kind of a path,
not a presence assertion.

Extend `RuntimeFilesystemEntry` with a presence field when implementation work
begins. The default should preserve current behavior as present observed state.
At minimum the vocabulary must represent an expected path that was absent at
capture time, so a deploy-key path can be encoded as an expected file with
`presence` indicating expected-but-absent rather than as `entry_type: other`.

Absent entries must not carry present-only facts such as size, content digest,
owner ids, or mode unless a future design explicitly models expected metadata
separately. If the filesystem inventory is non-empty, semantic validators that
resolve file associations must account for presence: present-file refs and
absence assertions are different facts even when they share the same path
string.

### 7. Reuse existing SDL gates

The implementation must reuse the repository's existing cross-cutting gates:

- `SDLModel` closed-world Pydantic validation and local field/model validators.
- parser key normalization, source-shorthand behavior, nested hashmap-key
  preservation, and variable-placeholder key rejection. Prefer list records
  with explicit stable ids instead of native maps.
- shared helpers in `_base.py` and `runtime_values.py`, especially
  `require_symbol()`, `parse_int_or_var()`, `parse_optional_bool_or_var()`,
  `parse_runtime_enum_or_var()`, `absolute_path_or_var()`, and
  `coerce_string_list()`.
- `RuntimeSensitivityClassification` and the existing redacted-value
  invariants for secret-bearing values.
- `SemanticValidator` and `SDLValidationError` for same-node service refs,
  service-local refs, optional local-identity refs, optional
  identity-authority refs, share/resource refs, and path-presence checks.
- `instantiate_scenario()` and `SDLInstantiationError` for substitution and
  concrete revalidation.
- `_module_symbols.py` and named-reference validation if file services, shares,
  principals, policies, or observations become generic relationship/objective
  targets.
- `compile_runtime_model()`'s existing node runtime dump path; do not add a
  second runtime compiler pipeline.
- `schema_bundle()`, `tools/generate_contract_schemas.py`, and
  `tools/check_generated_schemas.py`; generated schemas under
  `contracts/schemas/` must not be edited directly.
- existing `aces_processor.models.Diagnostic`, runtime snapshots,
  control-plane envelopes, MCP operation error shapes, and redacted error
  handling if file-service facts later flow through APIs or tools.

No new parser, schema registry, validation framework, exception hierarchy,
logging stack, persistence mechanism, workflow engine, or backend-specific
Samba dialect is justified.

## Security and Validation Gates

- Parser gate: stable ids are concrete values, not `${var}` placeholders or
  mapping keys. Avoid nested fields named `source` unless source-shorthand skip
  behavior is deliberately updated.
- SDL model gate: reject empty ids, duplicate service/share/principal/policy
  ids in their owning scopes, malformed ports and paths, invalid enum values,
  duplicate action rules where the same subject/resource/action/effect/basis
  would be ambiguous, and raw values where sensitivity classification requires
  omission.
- Semantic validation gate: file-service `service` refs resolve only to
  same-node `Node.services[]`; share-local refs resolve inside the service;
  local-user refs resolve against `runtime.local_identity` when present;
  identity-authority refs resolve through the existing qualified runtime ref
  machinery when used; path refs check filesystem presence, not just path text.
- Instantiation gate: variable placeholders may stand in ordinary values, but
  not in symbol-defining ids, mapping keys, or relationship endpoint identities.
  Instantiated scenarios revalidate.
- Contract/schema gate: schema changes come from Python model sources and the
  schema generator only.
- Host/OS exposure gate: TCP/445 or other transport exposure remains in
  `Node.services` and `runtime.network.published_ports`; file-service inventory
  must not hide externally reachable attack surface or duplicate host bindings.
- Identity/auth gate: guest, anonymous, passdb users, OS users, directory
  users, and scenario accounts are different subject classes. Any links among
  them are explicit refs, not inferred name equality.
- Secret-handling gate: passwords, NT/LM hashes, Kerberos keys, keytabs,
  private keys, bearer tokens, credentialed probe commands, raw `smbclient`
  invocations, passdb dumps, and backend inspect payloads must not enter SDL
  examples, fixtures, generated schemas, diagnostics, logs, snapshots, audit
  details, or process argv.
- Error-envelope gate: validation and runtime errors should name the bad field,
  id, and rule without echoing raw Samba configuration, passdb output, probe
  transcripts, or credentials.

## Guardrails

- Do not put SMB/Samba under `runtime.applications` or add `smb` to
  `RuntimeApplicationProtocol`.
- Do not add file-share facts to `Node.services`; services are transport
  bindings.
- Do not promote every Samba passdb user into top-level `accounts`.
- Do not put standalone Samba passdb directly in `runtime.local_identity` or
  `runtime.identity_authorities`; use refs when it maps to those surfaces.
- Do not encode share access only in `description`, `relationships.properties`,
  or unbounded `metadata`.
- Do not treat `read only = no`, `valid users`, POSIX mode bits, Windows DACLs,
  and observed write success as one interchangeable permission fact.
- Do not infer effective access without recording whether the basis is config,
  filesystem permission/ACL, directory policy, probe evidence, or computed
  synthesis.
- Do not dump raw `smb.conf`, `testparm`, `pdbedit`, `smbpasswd`, `smbclient`,
  `getfacl`, `icacls`, packet captures, scanner JSON, or backend inspect output
  as the portable model.
- Do not case-fold observed share names, account names, SIDs, RIDs, or path
  names unless a protocol-specific submodel explicitly owns that rule.
- Do not publish file-service refs into relationships/objectives unless module
  composition aliases, named-reference indexes, docs, and tests are updated
  together.
- Do not add implementation logic under `implementations/python/src/aces/`;
  that tree is compatibility-only wrappers.

## Non-Goals

- Implementing issue #421.
- Updating `examples/scenarios/techvault.sdl.yaml` or downstream APTL
  inventories.
- Building an SMB, Samba, NFS, FTP/SFTP, WebDAV, object-store, ACL, `smb.conf`,
  `pdbedit`, `testparm`, `smbclient`, scanner, or backend discovery parser.
- Designing a complete cross-protocol ACL algebra.
- Defining backend provisioning behavior for shares, Samba users, passdb
  credentials, ACLs, or filesystem paths.
- Redesigning `Node.services`, `runtime.network`, `runtime.applications`,
  `runtime.local_identity`, `runtime.identity_authorities`,
  `runtime.database_services`, top-level `accounts`, top-level
  `relationships`, participant observation boundaries, runtime snapshots,
  control-plane APIs, persistence, logging, or workflow semantics.

## Consequences

### Positive

- SMB/Samba share and passdb facts can become typed, queryable runtime
  inventory without corrupting HTTP applications, OS identity, directory
  identity, or scenario accounts.
- The same file-service seam can later represent NFS, FTP/SFTP, WebDAV, and
  object-store style resources without making SMB second-class or forcing a
  global authorization system into the SDL.
- Expected-but-absent filesystem paths become explicit presence facts instead
  of fake `other` entries.
- Existing parser, validation, instantiation, schema generation, module
  composition, diagnostics, redaction, and control-plane boundaries remain
  authoritative.

### Negative

- Node runtime gains another optional inventory surface.
- Some facts may need to appear in adjacent surfaces with explicit different
  meanings, such as a Samba passdb principal and a same-named OS-local user.
- Consumers that care about effective access must inspect both configured
  policy and observed access outcomes when both are present.

### Risks

- A generic free-form service configuration or ACL dictionary would recreate
  the original semantic loss under a new field name.
- An SMB-only model would be faster for TechVault but would likely require a
  second incompatible surface for NFS, SFTP, or object stores.
- A global resource-access-policy surface would be too broad before the repo
  has multiple concrete resource-service examples and could blur runtime
  inventory, scenario relationships, participant visibility, and evidence.
- Recording credentialed probe commands, password hashes, or raw backend output
  could leak secrets into fixtures, generated schemas, diagnostics, logs, or
  snapshots.

## References

- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md).
- [Open Cyber Range SDL Reference](https://documentation.opencyberrange.ee/docs/sdl/reference/),
  [CyRIS](https://www.jaist.ac.jp/~razvan/publications/cyris_facilitating_training.pdf),
  [KYPO topology definition](https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/topology-definition/),
  [VSDL](https://arxiv.org/abs/2001.06681), and
  [CRACK](https://doi.org/10.1016/j.cose.2020.101787).
- [OCSF schema](https://github.com/ocsf/ocsf-schema),
  [UCO design document](https://unifiedcyberontology.org/resources/uco_design_document.html),
  [CASE design document](https://caseontology.org/resources/case_design_document.html),
  [STIX 2.1](https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html),
  [CycloneDX](https://cyclonedx.org/specification/overview/), and
  [SPDX](https://spdx.dev/use/specifications/).
- [MS-SMB2](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-smb2/5606ad47-5ee0-437a-817e-70c366052962),
  [Microsoft SMB/CIFS overview](https://learn.microsoft.com/en-us/windows/win32/fileio/microsoft-smb-protocol-and-cifs-protocol-overview),
  [Samba `smb.conf`](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html),
  [Samba `pdbedit`](https://www.samba.org/samba/docs/current/man-html/pdbedit.8.html),
  and [Samba `net usershare`](https://www.samba.org/samba/docs/current/man-html/net.8.html).
- [Linux ACL man page](https://man7.org/linux/man-pages/man5/acl.5.html),
  [Windows ACL documentation](https://learn.microsoft.com/en-us/windows/win32/secauthz/access-control-lists),
  [Windows security descriptor string format](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-descriptor-string-format),
  and [NFSv4.1 RFC 8881](https://www.rfc-editor.org/rfc/rfc8881).
- [Zanzibar: Google's Consistent, Global Authorization System](https://research.google/pubs/zanzibar-googles-consistent-global-authorization-system/).
