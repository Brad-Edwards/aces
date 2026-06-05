# ADR-038: Runtime Mail-Service Logical State

## Status

accepted

## Date

2026-05-28

## Context

Issue #420 identifies an SDL expressivity gap while encoding the APTL
TechVault `mailserver` container inventory. The existing model can describe
transport listeners in `Node.services`, host publication in
`runtime.network.published_ports`, generic accounts in top-level `accounts`,
and filesystem evidence in `runtime.filesystem_inventory`, but none of those
surfaces owns mail-server logical state.

The missing facts are mail-specific and node-scoped: SMTP/submission/IMAP/IMAPS
listener roles, advertised capabilities and banners, AUTH and TLS/STARTTLS
posture, local domains, mailbox provisioning, aliases, routing/relay policy,
queue shape, mailbox storage, and Postfix/Dovecot runtime settings. Encoding
those facts as HTTP routes, generic content, filesystem paths, or untyped
relationship prose would make equivalence tooling compare the wrong concepts.

The nearby ADRs establish the expected placement:

- ADR-026 keeps HTTP application state under `Node.runtime.applications`.
- ADR-029 keeps database logical state under `Node.runtime.database_services`
  and uses typed relationship access details.
- ADR-033 keeps participant-interactable runtime node state on the smallest
  typed surface that owns its meaning.
- ADR-037 keeps file-service logical state under `Node.runtime.file_services`
  rather than overloading filesystem inventory or generic accounts.

## Decision

Add a provider-neutral runtime mail-service inventory under
`Node.runtime.mail_services`.

Each `RuntimeMailService` has a stable `service_id`, optional same-node
`Node.services` reference, engine/version/name data, and typed child records:
components, listeners, domains, mailbox stores, mailboxes, aliases,
routing rules, queues, and settings. Stable ids are explicit data fields, not
mapping keys, and are unique within the service namespace.

Transport ownership remains in `Node.services`. A mail service or listener may
reference a same-node transport service by bare name or by
`nodes.<node>.services.<name>`, but it does not create ports or host exposure.

Listeners record mail protocol role, advertised capabilities, banners,
advertised identity, AUTH mechanisms, TLS posture, and component ownership.
They are not HTTP routes and do not extend `RuntimeApplicationProtocol`.

Mailboxes are service-local runtime records, not top-level scenario accounts.
They may reference top-level accounts or OS-local users when that relationship
is observed, but the mailbox surface owns mailbox address, role/status,
authentication mechanisms, credential-strength classification, and mailbox
store linkage. Raw passwords, hashes, tokens, keytabs, and private keys are
unrepresentable in mailbox records.

Settings are typed runtime configuration facts with component ref, name, value,
provenance, source path, and sensitivity classification. Secret-bearing setting
names must omit raw values and use `redacted` or `operator_secret`; source paths
resolve to observed filesystem inventory when that inventory is present.

Keep top-level `relationships` as the relationship owner. Add
`RelationshipMailAccess` as a typed relationship detail for mail-specific
protocol, auth, TLS, mailbox, listener, and domain semantics. Relationship
endpoints resolve to qualified runtime mail-service refs and stable child refs.

The implementation must reuse existing SDL gates:

- closed-world Pydantic models and enum/variable parsing helpers;
- semantic validation for same-node transport refs and service-local refs;
- module symbol rewriting for qualified runtime refs;
- generated-schema publication from Python model sources only;
- repo policy, requirement governance, and full verification gates.

## Consequences

Positive:

- TechVault mailserver logical state becomes typed and queryable without
  overloading HTTP routes, filesystem evidence, or generic accounts.
- Transport, runtime logical state, evidence/provenance, and relationships stay
  separated.
- Mail-specific relationship semantics can be validated structurally.
- Future POP3, LMTP, Sieve, DKIM/SPF/DMARC, alternate MTA/MDA, and relay
  extensions can add vocabulary or bounded child records without adding a new
  top-level mail section.

Trade-offs:

- The runtime model grows another protocol-family surface under `Node.runtime`.
- The portable model intentionally does not clone Postfix, Dovecot, or RFC
  object trees, so rare vendor-specific settings may remain bounded settings or
  evidence rather than first-class fields.
- Dynamic queue/log contents remain summarized shape and stability facts, not
  a stable message-by-message inventory.

Rejected alternatives:

- Add top-level `mail`, `mailboxes`, or protocol roots. This would break the
  runtime-node boundary established by ADR-026, ADR-029, ADR-033, and ADR-037.
- Encode SMTP/IMAP as `runtime.applications[].routes`. That surface is
  HTTP/URL/method oriented and validates the wrong protocol grammar.
- Encode mailbox and queue state only as filesystem or content records. Those
  surfaces are evidence/data placement, not mail-service logical state.
- Store raw Postfix/Dovecot config dumps. Raw dumps are provider-coupled,
  untyped, and unsafe for secret-bearing settings.
