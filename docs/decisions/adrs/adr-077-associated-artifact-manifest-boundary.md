# ADR-077: Associated Artifact Manifest Boundary

## Status

accepted

## Date

2026-07-12

## Classification

Classification: FM1
Required artifacts: ADR, normative spec, schema, fixtures, contract tests
Waivers: none

## Context

ACES gives validated, expanded SDL a canonical semantic digest and gives
experiment artifacts checksum-bearing references. Neither surface defines one
portable set of non-semantic artifacts attached to a scenario, sealed scenario
snapshot, or experiment artifact. Downstream packaging and ingestion tools
therefore cannot distinguish a verified companion set from a caller-asserted
package digest without inventing an asset model outside ACES.

The missing model must preserve existing boundaries. Documentation, operator
material, evaluator assets, reports, profiles, and similar bytes are not SDL
meaning. A live directory is not an atomic snapshot. An artifact checksum is
not a manifest identity, and neither a checksum nor a manifest digest proves
authenticity. Attachment at one scope must not silently imply attachment at
another scope.

## Decision

Publish `associated-artifact-manifest-v1` as a closed, standalone contract. One
manifest attaches one exact keyed artifact-reference set to one explicit
parent. Its scope is either:

- `scenario`, with a `scenario` or `scenario-snapshot` parent; or
- `experiment`, with a task, authoring input, apparatus context, run, or study
  parent.

The contract reuses the experiment-core typed-reference, checksum, and artifact
descriptor shapes. It adds the missing `authoring-input` reference kind and
shared companion roles without creating a scenario-only descriptor or a
universal `TrustedAsset` payload. Generic scenario parents remain id-only;
scenario snapshots may carry the existing version and semantic-digest binding.
Experiment parents do not gain self-asserted payload digests.

The logical manifest id/version is separate from the derived
`associated-artifact-set/v1` identity. Set identity is lowercase SHA-256 over
RFC 8785 canonical bytes containing the profile id, scope, exact parent
reference, and exact keyed artifact-reference set. It excludes the set digest
itself and all filesystem, archive, OCI, filename, materialization, and export
layout metadata. Changing the parent or any artifact reference changes set
identity; changing only a downstream layout does not.

Full conformance requires the cross-artifact validator to match the concrete
parent, derive the set digest, and recompute every artifact checksum and size
from exactly one explicitly supplied, bounded byte reader. The validator does
not fetch locators, walk directories, unpack archives, follow symlinks, or read
ambient configuration. A digest, path, URI, or prior validation flag is not a
byte binding.

Add `associated_artifact_set` as a distinct reusable-asset family under
ADR-071. Its set digest supplies `integrity_digest`; every payload supplies
`artifact_checksum`. The parent retains its existing identity and integrity
mechanism. Authenticity remains an independent signature/trust-policy decision.

Attachments never inherit between scenario, snapshot, task, authoring input,
apparatus context, run, and study. Attaching the same bytes to another parent
requires another manifest and therefore another set digest.

## Consequences

### Positive

- Producers and consumers share one portable parent-plus-artifact-set contract
  without importing scenario-pack filesystem layout into ACES.
- Caller-asserted package digests cannot establish conformance or trust.
- Scenario meaning, parent identity, set identity, raw checksums, and
  authenticity remain independently testable claims.
- The typed parent matcher, versioned canonicalization profile, shared role
  vocabulary, and injected byte-reader seam admit future families and transports
  without changing SDL semantics.

### Negative

- Full validation requires callers to stage and supply every referenced
  payload, even in offline workflows.
- Adding parent families or canonicalization revisions requires a contract
  revision and focused compatibility evidence.

### Risks

- Consumers may validate schema shape but skip the required semantic byte gate;
  the published `x-aces-invariants` annotation and conformance diagnostics make
  that limitation explicit.
- Mutable locators can drift; immutable staging and use-time verification remain
  consumer responsibilities.

## Non-goals

This decision does not define scenario-pack directories, manifest filenames,
archive or OCI layout, release tiers, catalog metadata, acquisition, storage,
entitlement, launchability, a registry, new cryptography, or an API/persistence
service. It does not change SDL syntax or `canonical_sdl_digest()`.
