# ADR-086: Governed Whole-Scenario Satisfiability

## Status

accepted

## Date

2026-07-19

## Classification

Classification: FM2

Required artifacts: a bounded formal fragment, solver-neutral normalized model,
exact solver profile, executable positive/negative/unsupported controls,
deterministic witness and unsatisfiable-core evidence, replay, a published
evidence contract, mutation tests, and explicit nonclaims.

Waivers: the v1 fragment is finite-domain only. It does not prove arbitrary SDL,
backend realizability, exploit paths, temporal properties, optimality, uniqueness,
or universal correctness of Z3. Its reduced unsatisfiable core is evidence for
the pinned translation and solver profile, not a proof certificate.

## Context

ACES parses, semantically validates, instantiates, and admits scenarios, but
those operations do not answer whether all authored variable constraints can be
satisfied together. Issue #168 therefore kept `constraint-satisfiability`
untested: structural acceptance, individual field validation, successful
instantiation of one supplied binding, and deterministic compilation are not a
whole-scenario satisfiability decision.

Issue #826 requires a production boundary that can make that narrower claim
without implying more. The result must be reproducible, portable, resistant to
unsupported-language overclaim, and bound to exact source, model, translation,
solver, and result identities.

## Decision

### 1. Analyze the composed authoring scenario before instantiation

The processor owns satisfiability analysis. It consumes the same bounded UTF-8
SDL source reader and semantic parser as normal authoring, including resolved
imports, then translates the composed authoring `Scenario`. It does not analyze
raw YAML mappings, an execution plan, or a backend-specific realization.

Source files are read as at most `max_input_bytes + 1` bytes before UTF-8 decode.
Evidence binds the exact root bytes and the canonical authored semantic digest.
Import provenance remains the canonical resolved-import provenance carried by
the composed scenario.

### 2. Adopt one closed finite-domain theory profile

`aces-finite-domain-satisfiability-v1` is the only v1 analysis profile. It is
the exact triple:

```text
(aces-finite-domain-theory/v1,
 aces-sdl-authoring-translation/v1,
 aces-z3-finite-domain/v1)
```

The theory contains string, integer, and Boolean symbols with finite domains and
named domain-membership clauses. String and integer variables require explicit
`allowed_values`; Boolean variables without them use `{false, true}`. Bounds are
128 symbols, 256 members per domain, and 512 clauses.

The v1 translator covers whole-token variable occurrences at:

- `nodes.<id>.os`, against the `OSFamily` vocabulary;
- `infrastructure.<id>.acls[<n>].action`, against `ACLAction`;
- `infrastructure.<id>.count`, restricted to integers at least one; and
- `infrastructure.<id>.properties.internal`, as Boolean membership.

Every remaining variable occurrence is traversed. Embedded substitutions,
number variables, missing finite domains, unknown targets, and exceeded bounds
produce `unsupported`; they are never ignored or treated as satisfiable.

### 3. Publish a solver-neutral normalized model

`aces_contracts.satisfiability` owns closed portable models for symbols,
clauses, diagnostics, solver configuration, outcomes, and evidence. Clause ids,
symbol ids, domains, and collections are uniquely and canonically ordered. The
normalized model is independently digest-bound using RFC 8785 JSON
canonicalization and SHA-256.

The SDL package does not import the processor or Z3. Translation, solving, and
replay live in `aces_processor.satisfiability`; the CLI imports only that public
surface.

### 4. Pin every output-affecting solver choice

The v1 solver profile is Z3 package `4.16.0.0`, engine `4.16.0`, logic `QF_LIA`,
random seed `0`, timeout `5000` ms, one thread, `auto_config=false`, model
production enabled, and unsat-core production enabled. A different installed
version is an operational failure, not a silent profile change.

Finite scalar values are encoded as indices into canonical domains. A
satisfiable model selects the lexicographically first binding in symbol/domain
order by repeated governed solver checks. An unsatisfiable model reduces the
named clause set by deterministic sorted deletion until it is subset-minimal.

### 5. Expose exactly three completed outcomes

The completed outcome vocabulary is `satisfiable`, `unsatisfiable`, and
`unsupported`.

- `satisfiable` carries exactly one canonical `InstantiatedScenarioSnapshot`
  witness. The normal instantiation/admission path validates the binding, and
  the canonical instantiated-scenario digest binds it.
- `unsatisfiable` carries exactly one sorted subset-minimal set of normalized
  clause ids. It is not labelled a minimal unsatisfiable subset, a proof, or a
  certificate.
- `unsupported` carries stable value-free diagnostics and matching reason
  codes, with no witness or core.

Solver timeout, `unknown`, version mismatch, and internal failure are
operational errors outside that completed vocabulary. They must not be converted
to `unsupported`, which describes language/profile coverage only.

### 6. Make evidence replay the full join

`scenario-satisfiability-evidence/v1` binds the exact source-byte digest,
authored semantic digest, resolved imports, normalized model and digest, full
solver configuration and digest, outcome, and exactly one matching payload.
Replay rereads the bounded source, verifies its byte digest, recomputes the
complete analysis, and requires contract equality. Unknown fields and mutated
source, model, solver, witness, core, or outcome joins fail closed.

The production CLI is:

```text
aces processor satisfiability <scenario> \
  --profile aces-finite-domain-satisfiability-v1
```

It writes only the evidence JSON to standard output. Completed satisfiable and
unsatisfiable analyses exit `0`; typed unsupported exits `2`; sanitized input or
operational failure exits `1`.

### 7. Keep claims bounded

Passing controls demonstrate that the pinned implementation decides and replays
the stated finite-domain fragment. They do not establish satisfiability for
unsupported SDL, completeness of future translations, backend provisionability,
runtime success, exploit reachability, temporal correctness, model uniqueness,
or solver proof verification. Any expanded target, theory, solver, or evidence
meaning requires a new versioned profile and compatible contract evolution.

## Alternatives Considered

- **Treat successful semantic validation as satisfiable.** Rejected because it
  does not compose variable-domain constraints across target vocabularies.
- **Search Python values without a governed model.** Rejected because it would
  hide translation coverage and make solver evidence non-portable.
- **Send source or SMT text to an external solver service.** Rejected for v1
  because it adds network, authentication, availability, and evidence-boundary
  complexity without improving the bounded claim.
- **Return Boolean or `unknown`.** Rejected because Boolean erases evidence and
  `unknown` conflates unsupported language with operational incompleteness.
- **Call a raw Z3 unsat core a certificate.** Rejected because tracked cores are
  solver/model evidence, not independently checked proofs.

## Consequences

Positive:

- ACES gains a falsifiable whole-scenario claim for a precisely named fragment.
- Unsupported syntax cannot silently strengthen a result.
- Evidence is deterministic, schema-published, portable, and replayable.
- SDL, processor, contracts, and CLI ownership remain aligned with ADR-036.

Negative:

- The initial target surface is intentionally small and must be versioned as it
  grows.
- Z3 is a pinned runtime dependency and upgrades require evidence/profile review.
- Deterministic witness and core reduction require multiple solver calls.
- Exact source-byte identity makes harmless byte edits invalidate replay, by
  design; canonical semantic identity remains separately visible.

Risks:

- A translation defect can invalidate the bounded claim even when the solver is
  correct. Total occurrence traversal, unsupported diagnostics, mutation tests,
  normalized-model publication, and replay reduce but do not eliminate that risk.
- Solver resource bounds can cause operational failure on a supported model.
  Such failure remains distinct from all three completed outcomes.
