# Diagnostics — Errors and Advisories

This file documents the SDL diagnostic boundary: the stages at which a document
is checked, the fail-closed error semantics, and the distinction between a fatal
**error** and a non-fatal **advisory**. It documents the **existing** boundary by
reference; it does not introduce a new diagnostic mechanism, and it does not
re-decide the classification of individual cases (see §5).

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

## 5. Coordination with review IMP-3

The precise, case-by-case normative classification of which specific conditions
are errors and which are advisories — and any change to where the line falls —
is the subject of the review **IMP-3** work. This specification:

- states the **principle** (errors are fatal and fail-closed; advisories are
  non-fatal and not optional errors) and the **stages** at which checks run;
- documents the **existing** advisory conditions by reference; and
- **does not** re-decide individual classifications or introduce new ones.

A future change that moves a condition between the error and advisory channels, or
that adds a new diagnostic category, **MUST** be coordinated with IMP-3 and
reflected here, in the published schemas, and in the reference implementation
together, so the boundary stays single-sourced.
