# ADR-075: Ecosystem Versioning, Deprecation, and Migration Governance

## Status

proposed

## Date

2026-07-11

## Classification

Classification: FM2
Required artifacts: ADR, normative specification, repository-policy and docs verification
Waivers: none

## Context

RAES now has several independently versioned surfaces:

- the Python distribution and Git tags;
- published JSON Schema contract lineages;
- wire discriminators in closed contract DTOs;
- SDL scenarios and reusable modules;
- processor, backend, participant, and apparatus declarations;
- experiment tasks, runs, studies, and evidence artifacts; and
- ADR and Ground Control workflow statuses.

These surfaces use similar words, such as version, compatibility,
deprecation, stability, migration, and lifecycle, but they do not all carry the
same semantics. ADR-061 already governs published JSON Schema evolution, while
ADR-010 governs compatibility-only Python import wrappers. Those decisions are
necessary but not sufficient for GOV-901, GOV-902, and GOV-903 because the
ecosystem needs one cross-surface policy that explains how versioning,
deprecation, and migration claims are made without collapsing every surface
into a single package-version model.

The current repository also has a practical tension: release-please owns the
package release process, the package is still pre-1.0, and all checked-in JSON
Schemas are currently `draft` even when their filenames carry `v1` or `v2`
lineage suffixes. A reader can otherwise infer stronger compatibility
guarantees than the repository can honestly provide.

## Decision

Adopt a two-part governance structure:

1. This ADR records the architectural decision and rationale.
2. `specs/evolution/versioning-deprecation-and-migration.md` is the normative
   operational policy for versioning, compatibility, deprecation, removal, and
   migration across ecosystem surfaces.

The policy has these core rules.

Version identifiers are surface-local. Package SemVer, Git tags, contract
lineage suffixes, wire discriminators, module versions, apparatus versions,
domain artifact versions, ADR status, and requirement status must not be
treated as interchangeable.

Compatibility claims must name their direction, producer, consumer, surface,
and dimension. The recognized directions are backward, forward, and full
compatibility. The recognized dimensions are structural acceptance, semantic
equivalence, behavioral compatibility, and operational interoperability.

Stability, deprecation, and removal are separate lifecycle concepts. ADR-061
`draft` or `stable` classification governs how a schema may evolve; it does
not say whether a surface is deprecated or removed. ADR status and Ground
Control requirement status remain governance workflow state, not artifact
lifecycle records.

Published JSON Schemas continue to follow ADR-061. This decision narrows the
meaning of "additive" at the ecosystem boundary: an optional schema property or
enum value can be structurally additive to the schema lineage, but it is not an
end-to-end compatibility guarantee unless the relevant installed readers are
shown to accept it or the policy explicitly scopes the claim to schema
structure only.

Deprecations must be explicit records. A deprecation record identifies the
exact surface, first release or contract lineage carrying the notice,
replacement, migration reference, expected notice window or removal eligibility
rule, verification evidence, and any security exception.

Migrations are surface-specific. Human migration notes belong under the
existing documentation boundary. Automated migrations are added only when the
transformation is deterministic, idempotent, preserves source data, reports
ambiguous or lossy cases, and fails closed.

Adapters stay at their owning boundary. The policy does not create a universal
version registry, migration service, runtime endpoint, persistence layer, or
cross-package exception hierarchy.

## Alternatives Considered

Extend ADR-061 to govern every ecosystem surface. Rejected: ADR-061 is the
right authority for published JSON Schemas, but package releases, SDL modules,
apparatus manifests, and experiment artifacts have different authorities and
compatibility relations.

Use Python package SemVer as the single ecosystem version. Rejected: the
package is a release vehicle, not the identity of each contract lineage,
scenario module, processor/backend declaration, or experiment artifact.

Create a central runtime versioning or migration service. Rejected: the current
need is repository governance, and each executable surface already has an
owning validator, registry, checker, or adapter boundary. A central service
would blur ownership and invite best-effort coercion.

Treat deprecation as a generic warning. Rejected: lifecycle notice must remain
separate from semantic validity. Deprecated-but-supported use is non-fatal;
removed or unsupported input fails through the owning surface's existing error
envelope.

## Consequences

The ecosystem gets one vocabulary for versioning, compatibility, deprecation,
and migration without weakening existing authorities such as ADR-061,
release-please, the schema publication manifest, or module registry checks.

Future surface families have a clear extension seam: add a row to the
normative surface-class matrix and update that surface's owning checker or
documentation rather than adding a universal runtime abstraction.

Some existing documentation remains more informal than the new policy. Follow-up
work may need to align release, migration, SDL, API, and conformance prose with
the normative spec.

Because this ADR is proposed, teams can still refine the surface matrix before
acceptance. Accepted amendments to already accepted ADRs remain governed by
ADR-059; this ADR does not silently edit ADR-061 or any earlier decision.
