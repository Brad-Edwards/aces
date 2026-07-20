# Scenario Satisfiability

This specification defines the normative v1 whole-scenario satisfiability
boundary adopted by ADR-086. The keywords MUST, MUST NOT, SHALL, and SHOULD are
normative.

## Profile Identity And Phase

The analysis profile `aces-finite-domain-satisfiability-v1` SHALL mean exactly:

```text
theory_profile      = aces-finite-domain-theory/v1
translation_profile = aces-sdl-authoring-translation/v1
solver_profile      = aces-z3-finite-domain/v1
```

The input SHALL be a successfully parsed and semantically validated, composed
authoring `Scenario`, before variable instantiation and before planning or
backend realization. The root source SHALL be read with `SDLParserLimits` before
UTF-8 decoding. The analyzer SHALL bind both exact source bytes and canonical
authored semantics.

## Finite-Domain Model

Let `S` be a finite, canonically ordered set of symbols. Each symbol `s` has one
sort in `{string, integer, boolean}` and a finite domain `D(s)`.

Let `C` be a canonically ordered set of named clauses. Each clause is a tuple:

```text
(clause_id, kind, symbol_id, source_address, allowed_values)
```

where `kind` is `declared-domain` or `target-domain`, and
`allowed_values` is a subset of `D(s)`. A binding `b` satisfies the normalized
model iff:

```text
for every c in C: b(c.symbol_id) is in c.allowed_values
```

Empty target domains are valid clauses and make the model unsatisfiable.
Symbols, clauses, domains, and clause values MUST be unique and use canonical
RFC 8785 scalar order. Bounds are 128 symbols, 256 domain members per symbol,
and 512 clauses.

## Translation Coverage

Required or referenced string and integer variables MUST declare finite
`allowed_values`. A Boolean variable MAY omit `allowed_values`, in which case
its domain is canonically `(false, true)`. Number variables are unsupported.

The translation SHALL recognize only whole-token occurrences `${name}` at:

| Authoring address | Required sort | Target membership |
|---|---|---|
| `/nodes/<id>/os` | string | normalized `OSFamily` values |
| `/infrastructure/<id>/acls/<n>/action` | string | normalized `ACLAction` values |
| `/infrastructure/<id>/count` | integer | values greater than or equal to one |
| `/infrastructure/<id>/properties/internal` | boolean | the declared Boolean domain |

The translator SHALL recursively inspect every other authored scenario field
after excluding the variable declarations, import declarations, module marker,
and expansion-provenance carrier. An embedded occurrence, unsupported sort,
unbounded domain, unrecognized address, missing symbol, or exceeded resource
bound SHALL produce a stable `unsupported` diagnostic. No occurrence may be
silently dropped.

## Solver Semantics

The v1 adapter SHALL use Z3 package `4.16.0.0`, engine `4.16.0`, `QF_LIA`, seed
zero, timeout 5000 ms, one thread, automatic configuration disabled, and model
and unsat-core production enabled. Scalar domain members SHALL be encoded as
integer indices. The published solver configuration SHALL contain every one of
these choices and be digest-bound.

For a satisfiable model, the witness SHALL select the first feasible value for
each symbol in canonical symbol and domain order while preserving previous
choices. The resulting binding SHALL pass normal scenario instantiation and
admission and SHALL be published as the canonical instantiated-scenario
snapshot and digest.

For an unsatisfiable model, the adapter SHALL start from all canonical clause
ids and remove a clause in sorted order whenever the remainder stays
unsatisfiable. The final sorted set is subset-minimal under that deletion
procedure. It MUST be named an unsatisfiable core, not a proof certificate or a
globally minimum core.

Solver `unknown`, timeout, package/profile mismatch, and internal failure SHALL
be operational failures. They MUST NOT be labelled `unsupported`.

## Evidence And Replay

The published `scenario-satisfiability-evidence-v1` contract SHALL bind:

1. portable source id and exact root-byte SHA-256;
2. canonical authored semantic digest and import provenance;
3. the normalized model and its RFC 8785 SHA-256;
4. the exact solver configuration and its RFC 8785 SHA-256;
5. exactly one of a witness, unsatisfiable core, or unsupported disclosure; and
6. stable, value-free diagnostics.

Replay SHALL verify the exact source-byte digest and then recompute the entire
evidence envelope with the evidence's analysis profile. Any mismatch SHALL
fail. Evidence models SHALL reject unknown fields and inconsistent cross-object
joins.

## Claims And Nonclaims

The executable corpus contains satisfiable, unsatisfiable, and unsupported
controls. Passing replay demonstrates the implementation's result for this
finite profile and the pinned artifacts only.

It does not demonstrate arbitrary-SDL satisfiability, translation completeness
outside the table, backend realizability, execution success, exploit-path
validity, temporal properties, uniqueness, optimality, independent Z3 proof
verification, or universal soundness/completeness. New sorts, targets, theories,
encodings, solver versions, witness orders, core algorithms, or evidence meaning
require a new governed profile/version.
