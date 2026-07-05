# Prior Art And Design Criteria For Realization Envelopes

Issue #667 asks ACES to describe a *set* of scenarios in one portable semantic
model. Authors need to request a family of acceptable scenarios; backends need
to declare the family they can actually realize. The same expression must
support membership, subsumption, witness generation, and closed-envelope refusal
without becoming a second backend-manifest capability language.

## Design Question

The design must answer four questions.

1. What typed expression describes the set of scenario instances under
   discussion?
2. How does openness or closure apply from a field up to a whole scenario?
3. When does one expression subsume another, so a backend can honestly claim it
   realizes a requested family?
4. How can conformance derive both an in-envelope witness and an
   out-of-envelope negative probe without a hard-coded reference scenario?

The answer must coordinate with the existing ACES incumbents:

- SDL variables and instantiation:
  `specs/sdl/variables-and-instantiation.md`.
- SEM-218 explicitness and realization:
  `specs/formal/realization/explicitness-and-realization.md`.
- The temporary target-conformance bridge:
  `run_target_conformance(reference_scenario=...)`, documented in issue #663
  as superseded by this issue and the scenario/envelope subsumption relation.

## Prior Art

### CUE: constraints as values

[CUE](https://cuelang.org/docs/reference/spec/) is the closest config-language
precedent. Its type/value lattice makes constraints, concrete data, and
subsumption part of one language rather than separate schema and data layers.
That is the right direction for ACES: an authored family and a backend
realizability declaration should be comparable as expressions in one type
system.

ACES should not adopt CUE wholesale. The envelope fragment needs only the
portable parts ACES can validate, publish, and test: typed variables, finite
sets, bounded intervals, governed references, structural closure, and a clear
subset relation. Arbitrary CUE expressions would make backend portability and
schema publication harder to reason about.

### Dhall: total typed configuration

[Dhall](https://dhall-lang.org/) shows a different useful boundary: a
configuration language can be typed, normalized, and deliberately non-general
purpose. The ACES lesson is that envelope expressions should normalize to a
stable portable form before they enter manifests, conformance reports, or
diagnostics. The language must not depend on backend callbacks, host state, or
side effects.

### JSON Schema: closed records and schema composition

[JSON Schema object validation](https://json-schema.org/understanding-json-schema/reference/object)
shows why closure is not just "reject unknown properties." `additionalProperties`
and `unevaluatedProperties` demonstrate that closure interacts with composition:
a schema can close one record while still composing with a base shape.

ACES needs the same discipline at semantic scope. A field, node, topology, app,
or whole scenario may be closed without making every enclosing layer a closed
singleton. The closure decision must be explicit and scoped; silence is not
universal realizability.

### Admission policy languages: CEL and Rego

Kubernetes
[ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
uses CEL to make admission checks declarative and scoped to API resources. The
Kubernetes
[CEL resource-constraint guidance](https://kubernetes.io/docs/reference/using-api/cel/)
also makes the operational point ACES needs: production admission expressions
need bounded execution and complexity controls. [OPA/Rego](https://openpolicyagent.org/docs/policy-language)
is a broader declarative policy language for deciding over nested documents.

The ACES lesson is negative. Envelope semantics are an admission relation, but
they must not become an arbitrary policy callback. The portable fragment should
be a structural set expression with known domain kinds and deterministic
membership/subsumption, not a user-authored program that can query backend state
or depend on evaluation order.

### Capability and conformance declarations

The [FMI 3.0 specification](https://fmi-standard.org/docs/3.0/) publishes FMU
capability flags in `modelDescription.xml`; [OGC API Common](https://docs.ogc.org/is/19-072/19-072.html)
advertises conformance classes through a `/conformance` resource and ties them
to requirements classes and tests. These systems establish the pattern ACES
already follows in backend manifests: declarations are portable claims, and
conformance must be able to falsify them.

The limit is coarseness. A boolean capability or conformance-class URI does not
say which scenario family a backend realizes, which values are closed, or which
out-of-envelope request it must refuse. ACES should keep coarse capability
claims as discovery and compatibility data, but realization envelopes are the
value-level set relation those claims cannot express.

### Decidable constraint fragments

[SMT-LIB logics](https://smt-lib.org/logics.shtml) and the
[Z3 arithmetic guide](https://microsoft.github.io/z3guide/docs/theories/Arithmetic/)
show the benefit of naming fragments such as linear integer or real arithmetic.
They also show why ACES should be conservative: once a portable language admits
unbounded quantification, non-linear arithmetic, recursive structures, or
backend-defined predicates, subsumption and witness generation stop being a
simple repo-owned semantic service.

ACES does not need a solver dependency for issue #667. The initial fragment can
be deliberately smaller: finite sets, enum subsets, exact values, bounded
numeric intervals, governed references, acyclic record/product structure, and
closed-scope extra-key rejection. That fragment supports useful envelopes while
keeping membership, subsumption, and witness generation mechanically checkable.

## Design Criteria

The ADR and formal spec must satisfy these criteria.

1. **One SDL semantic model.** Authored scenario families and backend
   realizability declarations use the same envelope expression. A backend
   manifest may carry or reference an expression, but it does not define a
   second language.
2. **Typed domains first.** Envelope variables build on the SDL variable model:
   type, optional default, optional closed value set, and fail-closed binding.
   New domain kinds are governed extensions.
3. **Scoped closure.** Open, constrained, and exact posture is evaluated at a
   declared scope: field, node, topology, app, or scenario. Most-specific-wins
   applies only when the more specific posture is compatible with the enclosing
   closure.
4. **Decidable relation.** Membership and subsumption reduce to per-domain
   checks and structural key-set checks in the admitted fragment. No arbitrary
   Python predicates, unbounded regex/SMT fragments, backend callbacks, or
   external service calls belong in portable envelopes.
5. **Witnesses are evidence, not proof.** A generated in-envelope witness proves
   only that the expression is satisfiable and executable for that concrete
   instance. It does not prove subsumption or closed-world honesty by itself.
6. **Negative conformance is first class.** A closed envelope must be tested by
   refusal of at least one generated out-of-envelope request for every closed
   dimension that can be varied safely.
7. **Manifest carriage is versioned.** Backend manifests should embed small
   envelopes or reference published envelope artifacts by contract id and
   digest. Current `realization_support.constraints` prose is not sufficient.
8. **Experiment run sets stay separate.** Experiment-core replications, cohorts,
   and comparisons describe what was executed and how it varied. A realization
   envelope describes what could be realized before execution.
9. **No sensitive witness leakage.** Generated witnesses, diagnostics,
   fixtures, manifests, and conformance reports must not expose credentials,
   backend-native ids, host paths, process argv, raw backend errors, or hidden
   truth.

## Decision Sketch Carried Into The ADR

- Add a proposed ADR selecting a versioned realization-envelope expression as
  the shared SDL semantics for authored families and backend declarations.
- Add a formal semantics note under `specs/formal/realization/` defining:
  scope order, posture, closure, domain descriptors, effective constraint
  lookup, membership, subsumption, witness generation, and negative
  conformance.
- Treat `backend-manifest-v2` as the current coarse carrier and reserve the
  envelope expression for a manifest schema evolution that embeds or references
  the versioned expression. Do not overload the current `constraints` string
  map as the final design.
- Leave runtime implementation, schema publication, conformance runner changes,
  and replacement of the #663 bridge to downstream issues.
