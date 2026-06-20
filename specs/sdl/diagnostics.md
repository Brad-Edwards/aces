# Diagnostics — Errors and Advisories

This file documents the SDL diagnostic boundary: the stages at which a document
is checked, the fail-closed error semantics, and the distinction between a fatal
**error** and a non-fatal **advisory**. It states the normative criterion that
classifies a condition as an error or an advisory (§5); it does not introduce a
new diagnostic mechanism, and it does not reclassify any existing condition.

## 1. Diagnostic stages

An SDL document is checked at three stages, in order. Each is **fail-closed**:
a problem at a stage stops the document from advancing past that stage.

1. **Parse / structural.** YAML loading and structural shape: the root is a
   mapping, keys are strings, values have the right shapes, and **no unknown key
   is present** ([document-model.md §4](document-model.md)). A structural problem
   is a parse error.
2. **Semantic validation.** Cross-section reference resolution
   ([references.md](references.md)), uniqueness, acyclicity, control-flow
   closure, and the runtime-family invariants
   ([runtime-inventory.md](runtime-inventory.md)). A semantic problem is a
   validation error.
3. **Instantiation.** Variable binding, type/constraint checks, undeclared
   parameters, and unresolved placeholders
   ([variables-and-instantiation.md §3](variables-and-instantiation.md)). A
   problem here is an instantiation error. Instantiation re-runs semantic
   validation on the concrete document, so semantic errors can also surface at
   this stage.

## 2. Collect-all semantics

The semantic-validation and instantiation stages **collect all errors in a pass**
and report them together, rather than failing at the first problem. An author
fixing a document sees the full set of errors a stage found, not one error at a
time. (Parsing may stop at the first structural fault that prevents
interpretation.)

## 3. Errors are fatal

An **error** is fatal: it prevents the document from advancing past its stage. A
parse error prevents semantic validation; a semantic error prevents a document
from being treated as valid; an instantiation error prevents a concrete document
from being produced. There is no "warn and continue" for an error.

> *Implementation evidence (non-normative): the reference implementation reports
> these as `SDLParseError`, `SDLValidationError`, and `SDLInstantiationError`;
> the latter two carry the full collected error list. This specification does
> not define a new exception hierarchy or diagnostic envelope.*

## 4. Advisories are non-fatal

An **advisory** is a non-fatal observation about a document that is otherwise
valid. Advisories are carried alongside a successfully parsed/validated
document; they do not prevent it from advancing.

The boundary rule is symmetric and **MUST** be honoured:

1. An advisory **MUST NOT** be described or treated as an optional error. A tool
   **MUST NOT** unilaterally promote an advisory to a failure.
2. An error **MUST NOT** be demoted to an advisory to let an invalid document
   pass.

Existing advisory conditions, documented here by reference (not redefined):

- **VM without resources.** A virtual-machine node declared without a
  `resources` block is **valid** SDL; it is flagged as an advisory because it may
  be undeployable unless a backend supplies defaults. It is not an error.
- **Name-based secret-classification heuristics.** A field whose *name* suggests
  it carries a secret, but which is not explicitly classified
  `redacted`/`operator_secret`, may raise an advisory. The heuristic is advisory
  **only**: it never silently strips or rewrites a value, and an unflagged value
  is not, by the heuristic alone, an error
  ([ADR-057](../../docs/decisions/adrs/adr-057-runtime-secret-name-classifier-boundaries.md),
  [runtime-inventory.md §3](runtime-inventory.md)). Explicit redaction
  (`redacted`/`operator_secret` omitting the raw value) is the **error-enforced**
  rule; the name heuristic is the advisory complement.

> *Implementation evidence (non-normative): advisories are surfaced on the parsed
> scenario's advisory list and the language-service diagnostics, separately from
> the error channel.*

## 5. Classification criterion

This section states the normative rule that decides whether a condition is an
**error** or an **advisory**. It resolves the classification deferred by review
**IMP-3**: the boundary is single-sourced here, and the classification of an
individual condition follows from this criterion rather than from each pass's
implementation.

The criterion is **meaning preservation**:

1. A condition is an **error** if and only if it affects the *meaning* of the SDL
   document — whether the document denotes a well-defined scenario at all. The
   meaning-affecting categories are: structural shape and closure (the §1 stage-1
   checks, including unknown-key rejection); cross-section reference resolution
   ([references.md](references.md)); identifier uniqueness; reference ambiguity;
   dependency and control-flow acyclicity; control-flow reachability,
   convergence, and "known-before-evaluation" visibility; required-profile guards
   on discriminated runtime spines ([runtime-inventory.md](runtime-inventory.md));
   variable binding, type, and constraint checks at instantiation
   ([variables-and-instantiation.md §3](variables-and-instantiation.md)); and
   explicit-redaction enforcement ([runtime-inventory.md §3](runtime-inventory.md)).
   A document that violates one of these has no single well-defined meaning, so
   the stage **MUST** fail closed (§3).
2. A condition is an **advisory** if and only if the document still has a single
   well-defined meaning and the condition reports a *deployability* or *quality*
   heuristic that does not change what the scenario means — for example, a
   construct a backend may be unable to realise without defaults, or a non-binding
   observation an author may wish to review. Advisories are non-fatal (§4).

**Borderline rule.** SDL diagnostics are fail-closed, so the default for a
condition whose classification is genuinely unclear is **error**. A condition is
classified as an advisory **only** when it is clearly a deployability or quality
heuristic that leaves SDL meaning intact; if a violation could leave the
document's meaning undefined, or if two conforming tools could legitimately
disagree about whether the document is valid, it is an error. This rule is
directional with §4: it governs how a *new* condition is classified, while §4
forbids re-labelling an *already-classified* condition to change its severity.

The existing conditions in §4 are consistent with this criterion. "VM without
resources" and the name-based secret heuristic are deployability/quality
heuristics that leave meaning intact, so they are advisories; reference
resolution, uniqueness, acyclicity, ambiguity, required-profile guards, and
explicit redaction are meaning-affecting, so they are errors.

A future change that moves a condition between the error and advisory channels,
or that adds a new diagnostic category, **MUST** apply this criterion and be
reflected here, in the published schemas, and in the reference implementation
together, so the boundary stays single-sourced.
