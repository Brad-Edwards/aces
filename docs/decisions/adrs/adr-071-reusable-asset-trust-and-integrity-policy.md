# ADR-071: Reusable Asset Trust and Integrity Policy

## Status

accepted

## Date

2026-07-05

## Classification

Classification: FM1
Required artifacts: ADR, normative spec, schema, fixtures, contract tests
Waivers: none

## Context

GOV-913 (MUST, Wave 3) states: *"The ecosystem shall support trust,
authenticity, and integrity policies for reusable scenarios, modules, tasks,
studies, behavior vocabularies, and comparable reusable assets."* It is the
requirement anchor for the Packaging & Supply Chain wave (issue #648), whose
ordering rule is contract-first: the normative contract surface publishes before
implementation.

The trust/authenticity/integrity **mechanisms already exist** across the
codebase and are governed by prior ADRs:

- SDL module composition trust — descriptors, imports, lock records, digest
  pins, signature verification, registry trust policy, bounded OCI reads, safe
  tar extraction (ADR-053).
- Participant implementation manifests and run-level provenance, with the rule
  that portable artifacts carry references and digests, not secrets (ADR-041).
- Experiment tasks, studies, run provenance, raw-content checksums, and
  evidence records (ADR-055, ADR-064, ADR-065, ADR-066).
- Concept-family and controlled-vocabulary governance, including external
  source metadata and `source_digest` (ADR-012, ADR-062).
- Published schema evolution and authority discipline (ADR-009, ADR-019,
  ADR-061).

What is missing is a **single, declarative policy** that says, for each reusable
asset family, which of these mechanisms constitutes required trust evidence. The
architecture preflight for issue #115 established the binding guardrails: treat
"reusable asset" as a role over existing families, not a new universal object;
prefer family-specific checks over a generic `TrustedAssetModel`; bind digests
only where a validator binds them to concrete bytes; keep scenario identity
distinct from scenario-snapshot integrity; do not duplicate registries,
lockfiles, vocabulary catalogs, or add digest fields to references that lack a
payload validator.

The policy model is grounded in established supply-chain frameworks (primary
sources reviewed during design): SLSA v1.0 (declarative expectation comparison;
resolved-dependency provenance), the in-toto attestation framework (digest-bound
subjects; authenticity decoupled from integrity), The Update Framework (M-of-N
signature thresholds; offline trust roots; delegation), Sigstore (identity-bound
signing; transparency), the OCI Image Spec 1.1 (content-addressable descriptors;
out-of-band evidence attached by digest), NIST SP 800-218 SSDF (PS.2 release
integrity verification; PS.3 archived provenance), and C2PA (hard-binding hashes
and signed claims for content assets).

## Decision

Publish a normative, contract-first **reusable-asset trust, authenticity, and
integrity policy**:

1. A normative specification,
   `specs/supply-chain/reusable-asset-trust-integrity.md`, defines the policy
   model over three orthogonal axes — identity, integrity (digest), authenticity
   (signature) — and the five evidence classes (`integrity_digest`,
   `authenticity_signature`, `provenance_lock_record`, `governance_source`,
   `artifact_checksum`), each mapped to an existing ACES mechanism.

2. A published contract, `reusable-asset-trust-policy-v1`
   (`contracts/schemas/asset-trust/`), makes the policy machine-checkable. It is
   a **policy-declaration** contract: per asset family it declares the required
   evidence classes and, for signature-bearing families, a trusted-signer set
   and M-of-N threshold. It carries no evidence payload and no key material, and
   it references — rather than duplicates — the incumbent mechanisms.

3. The contract enforces the policy invariants (complete family coverage,
   required integrity baseline per family, unique evidence classes,
   threshold-backed authenticity, closed/no-secret shape) via model validators,
   valid/invalid conformance fixtures, and a dedicated test module. It is
   registered in `schema_bundle()`, the schema generator, and the schema
   publication manifest under the existing contract discipline.

Runtime verification/enforcement is out of scope for this contract-first ADR;
future enforcement consumes and conforms to this policy.

## Alternatives Considered

- **A universal `TrustedAsset` / `reusable_assets` SDL section.** Rejected: it
  collapses families with genuinely different identity, evidence, and authority
  boundaries, and duplicates existing trust machinery (preflight anti-pattern).
- **Per-asset trust-record contract (in-toto-statement style) carried by every
  asset.** Rejected as the first slice: the incumbent mechanisms already carry
  per-asset evidence (lock records, checksums, provenance, source digests); a
  new record would duplicate them and add digest fields lacking payload
  validators. A policy-declaration contract references those mechanisms instead.
- **Spec-only, no contract.** Rejected: a MUST requirement needs a
  machine-checkable, conformance-tested surface, not prose alone.
- **Inventing ACES-native signing/registry/transparency.** Rejected: the
  standards compose existing primitives; the policy names evidence classes and
  defers to established formats and the existing `RegistryTrustPolicy`.

## Consequences

- **Positive.** GOV-913 gains a single, testable, standards-grounded policy
  surface; producers (including the companion `aces-scenario-packs` repo) have
  one place to read the ecosystem's trust expectations; the model is extensible
  by adding families/evidence classes without touching parser, runtime, or
  backend code.
- **Negative / trade-offs.** The policy declares expectations but does not, by
  itself, enforce them at runtime; enforcement is deferred to follow-on work.
  The reference policy encodes today's mechanism mapping and will need updates as
  new mechanisms land (guarded by the schema publication ledger).
- **Risks.** If future enforcement diverges from the declared policy, the
  contract becomes advisory; the follow-on enforcement work must trace back to
  this contract and spec.
