# Explicitness And Realization Semantics

This note defines the normative semantic boundary for `SEM-218`.

It states the rules that distinguish *binding* author declarations from
concerns *left open* to backend realization, names when realization is
permitted, names when an explicit declaration must be honored, and names
when an unsupported exact requirement must be rejected rather than
silently approximated. In RAES the processor layer does not realize
underspecified author concerns: it compiles the typed runtime
requirement and plans against backend support. Realization is a backend
responsibility; this spec scopes the realization surface accordingly.

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**
in this note are to be interpreted as described in RFC 2119.

## Scope

The semantics in this note govern, for every authored scenario element
that names a concern a backend will later realize, three questions:

1. is the author's declaration *binding* — that is, must the realizer
   honor it exactly or reject?
2. is the concern *open* to realization — that is, may the realizer pick a
   value or structure, and under what bounds?
3. if the realizer cannot honor a binding declaration, what must happen?

The note owns one typed scenario-root SDL `realization` designation surface.
It does not add realization fields to nested models, define new
exact-requirement kinds, or describe wave-3 participant semantics that build
on this boundary. Those are governed elsewhere.

## Realization Status

The semantic boundary defined in §"Required Semantics" is normative
immediately on landing. Its enforcement across the seven `SEM-200`
lifecycle phases is now complete. The current realization, recorded in the
SEM-200 coverage table at `docs/explain/reference/shared-semantic-integrity.md`,
is `active`. What is *enforced today* spans authoring through observation:

- the apparatus-contract shape gates on backend
  `RealizationSupportDeclaration` (the `EXACT_ONLY` ⇒ no constraint
  kinds rule, the at-least-one-kind-populated rule, the non-empty
  `disclosure_kinds` rule);
- the JSON-schema conditional gate for the same shape rules on the
  generated backend-manifest schema;
- the processor-vs-backend asymmetry: `ProcessorManifestV2Model`
  rejects any `realization_support` section, so the processor layer's
  non-realizing role is enforced structurally;
- the closed-Pydantic SDL model boundary (`extra="forbid"`), which
  fails closed on unknown keys at points the schema does not designate
  as realizable;
- the SEM-218 classifier in `raes.explicitness`, invoked by
  `SemanticValidator`, which tags authored SDL declarations as
  *exact*, *constrained*, or *open* for downstream consumers;
- the typed `raes.realization_designation` authoring surface, which carries
  a scenario default and RFC 6901 scoped overrides using `closed`, `open`, or
  `unspecified`, resolved by semantic specificity rather than list order;
- the instantiation downgrade rule in `instantiate_scenario`, which
  preserves authored explicitness metadata across parameter/default
  substitution without promoting substituted concrete values to false
  exact declarations;
- the typed compiler emission in `compile_runtime_model`, which lowers
  each authored realization concern into a `CompiledRealizationRequirement`
  on the `RuntimeModel` preserving its exact / constrained / open class;
- the planner realization-support gate in `raes_processor.planner.plan`,
  which matches each compiled exact / constrained / open requirement against
  the selected backend's `realization_support` and rejects open demand unless
  the selected domain explicitly declares `OPEN_REALIZATION`;
- the runtime non-approximation gate on backend adapters in
  `raes_processor.semantics.realization.realization_disclosure` (invoked from
  `raes_runtime.backend_calls._call_backend_apply`, the runtime adapter
  boundary), which compares each realized exact concern against the author
  declaration and rejects a silent approximation with a
  `runtime.backend-contract-invalid` diagnostic before the backend snapshot is
  accepted into runtime state;
- the SEM-218 provenance ledger (`realization_provenance`) on the runtime
  snapshot envelope, which records each realized concern with its explicitness
  class, author-declared / processor-derived / backend-realized origin, and a
  redacted governing-scope reference preserved through store and authenticated
  snapshot API conversion.

With those last two enforcement points realized, every `SEM-200` lifecycle
phase boundary is now enforced by named, tested code; no rule in this spec
remains normative-but-unrealized. The SEM-200 coverage row in
`shared-semantic-integrity.md` records the realization as `active`.

## Canonical Inputs

The semantics rest on existing authority surfaces. Implementations MUST
extend these rather than introduce parallel registries:

- realization support modes:
  `implementations/python/packages/raes_contracts/vocabulary.py`
  (`RealizationSupportMode`)
- apparatus declarations:
  `implementations/python/packages/raes_contracts/apparatus.py`
  (`RealizationSupportDeclaration`)
- contract-model gates and generated JSON schema:
  `implementations/python/packages/raes_contracts/contracts/`
  (`RealizationSupportDeclarationModel`)
- processor and backend manifest payloads:
  `implementations/python/packages/raes_processor/manifest.py`,
  `implementations/python/packages/raes_backend_protocols/manifest.py`
- native concept family for realization concerns:
  `contracts/concept-authority/concept-families-v1.json`
  (`realization-and-disclosure`)
- shared SDL static semantics:
  `implementations/python/packages/raes/validator/`
  (`SemanticValidator`, `SDLValidationError`)
- scoped author designation and canonical scope resolution:
  `implementations/python/packages/raes/realization_designation.py`
- instantiation and revalidation:
  `implementations/python/packages/raes/instantiate.py`
  (`instantiate_scenario`, `SDLInstantiationError`)
- runtime compilation and planning:
  `implementations/python/packages/raes_processor/compiler/`,
  `implementations/python/packages/raes_processor/semantics/planner.py`
- runtime diagnostics, results, and snapshots:
  `implementations/python/packages/raes_processor/models/`
  (`Diagnostic`, runtime plan / result / snapshot models)
- semantic profiles, controlled vocabularies, and reference models:
  `specs/concept-authority/`, `implementations/python/packages/raes_contracts/`

## Required Semantics

### Author intent has three classes

This taxonomy is normative. Every authored value or structure that names
a concern subject to later realization belongs to exactly one of these
classes:

- **Exact author declaration.** The author has stated a specific value or
  structure that the realizer MUST honor. Concrete examples in this
  repository include canonical identities (`SEM-205`), declared agent
  identifiers and actions, declared workflow successor relations, and any
  controlled-vocabulary value bound to a concept family.
- **Constrained declaration.** The author has stated a typed surface
  (range, enumeration, predicate, or structural constraint) bounding the
  set of acceptable realizations. The realizer MUST pick a realization
  that satisfies every stated bound, or reject.
- **Open realization.** The author has been silent at a point where the
  owning SDL schema or semantic rule explicitly designates the concern as
  realizable later. The realizer MAY pick any realization consistent with
  its declared capability domain.

The taxonomy and its **concrete classification authority** are binding. The
incumbent classifier owns explicit leaf declarations. The scenario-root typed
designation table owns inherited defaults only at realization points registered
by the same SEM-218 concern authority. A scope default never turns an arbitrary
missing model field into a realization point and never relaxes closed Pydantic
unknown-key rejection.

Silence at any other point is **not** open realization. The SDL parser,
`SemanticValidator`, instantiation, the compiler, and the runtime
adapter layer MUST treat unstated values at non-realizable points as a
validation failure, not as permission to fill them in. This is the
closed-world default for the ecosystem; the existing closed-Pydantic
SDL model boundary (`extra="forbid"`) enforces it structurally today.

### Scoped default cascade

`Scenario.realization` is optional. When present, it contains a root `default`
and zero or more `scopes`. The only author posture spellings are `closed`,
`open`, and `unspecified`. Scope identities combine a structured module
`namespace` tuple with an RFC 6901 `field_pointer`; JSONPath, wildcards, and
permissive dotted author paths are not accepted.

Resolution is deterministic: an explicit leaf exact/constrained/open
declaration wins first, then the most-specific concrete scoped default, then an
inherited concrete outer default. `unspecified` delegates to the selected
apparatus default; until a typed apparatus-default contract exists, that seam
resolves closed. Omitting `realization` is distinct and preserves the legacy
closed fallback. Equal-scope duplicates are invalid, and list/import order has
no semantic effect. Imported declarations and designation scopes are qualified
through the composition symbol map, so a module default cannot govern host or
sibling declarations.

### Five invariants

The following invariants are normative for every stage that has authority
over the realization of a concern.

**I1 — Bindings are honored.** If an authored construct carries an exact
declaration `R` for a concern `C`, every downstream stage with authority
over `C`'s realization (validation, instantiation, compilation, planning,
execution) MUST either realize `R` exactly as declared *or* reject the
artifact through the structured error surface that owns that stage —
`SDLValidationError`, `SDLInstantiationError`, a compiler `Diagnostic`,
or the equivalent runtime error envelope. No stage MAY substitute, drop,
coerce, or weaken `R` without rejection.

**I2 — No silent approximation.** A backend realizer MUST NOT realize
an exact declaration in a way that differs from the declared value or
structure. Substitution that changes the declared meaning is rejection,
not realization; approximation is forbidden. If a backend can realize a
nearby, weaker construct, it MUST reject and surface the gap through a
structured diagnostic so the authoring layer can revise the declaration
explicitly. Approximation is not a backend-private choice. The
processor layer plays no realization role under SEM-218: it compiles
the typed runtime requirement and plans against backend support, but
does not pick values for underspecified concerns.

**I3 — Openness is explicit.** A backend MAY realize an underspecified
concern only at a point where the owning SDL schema or semantic rule
explicitly designates that concern as realizable, *and* where the
backend's manifest declares a per-domain `RealizationSupportMode` of
`OPEN_REALIZATION` covering that open concern. When the backend also publishes
a finer realization envelope, its offered projection MUST subsume the compiled
open request under the canonical envelope relation. Constrained declarations
use the separately declared constrained support surface. Silence
outside such designated points is fail-closed: the authoring artifact
MUST be rejected with a structured error rather than filled in.

**I4 — Capability disclosure.** Every **backend** manifest MUST carry
per-domain `RealizationSupportDeclaration` entries that name (i) the
support mode (`EXACT_ONLY`, `CONSTRAINED`, or `OPEN_REALIZATION`), (ii)
the supported exact-requirement-kinds, (iii) the supported
constraint-kinds, and (iv) the disclosure kinds the apparatus will emit.
Processor manifests MUST NOT carry `realization_support`: in RAES the
processor layer does not realize underspecified author concerns — its
manifest discloses processing features (compilation, planning,
orchestration coordination, evaluation coordination, and related
semantics) and not realization capabilities. This asymmetry is encoded
today by `ProcessorManifestV2Model` rejecting any `realization_support`
section.

The contract model MUST enforce on every `RealizationSupportDeclaration`:

- a declaration with `support_mode = EXACT_ONLY` MUST NOT carry any
  `supported_constraint_kinds`;
- a declaration MUST carry at least one of `supported_constraint_kinds`
  or `supported_exact_requirement_kinds`;
- `disclosure_kinds` MUST NOT be empty.

These shape rules are the structural floor of I4 and are enforced today
by `RealizationSupportDeclaration.__post_init__` and
`RealizationSupportDeclarationModel._validate_realization_support`. The
planner-side matching of compiled exact-requirement-kinds against the
selected backend's `realization_support` — by which an unsupported
exact requirement causes plan rejection before deployment — is
realized by the realization-support gate in `raes_processor.planner.plan`
(over the compiled `RuntimeModel.realization_requirements`), alongside the
concrete provisioner / orchestrator / evaluator capability checks in
`_validate_manifest`. The rule is binding under this spec.

**I5 — Provenance is preserved.** Values that enter snapshots, results,
history, or evidence envelopes MUST be recorded with provenance
distinguishing three origins:

- **author-declared** — the value is exactly as the author wrote it in
  the SDL and survives instantiation without parameter or default
  substitution;
- **processor-derived** — the value was produced by deterministic
  processor activity that does NOT constitute realization: parameter
  substitution (whether the selected value is caller-bound or comes from an
  SDL default), defaulting permitted by the SDL schema, canonical identity
  normalization, and compilation transformations. The
  processor does not realize underspecified concerns; "processor-derived"
  is the provenance label for deterministic processing of declared
  input.
- **backend-realized** — the value was picked by the backend during
  execution from an open or constrained surface admitted by I3.

Provenance lives on the existing runtime plan / result / snapshot /
participant-episode contracts; no new private channel may carry
realization decisions out of band. The provenance contract above is realized
on the existing runtime snapshot contract. Backend-filled open slots carry a
stable `governing_scope` reference, never the realized value itself.

### Phase responsibilities

The seven canonical `SEM-200` lifecycle phases interact with the
invariants as follows. The list is normative for the phase boundary, not
for the engineering layout of any one phase. The **Status** column
records what is enforced in the repository today; every phase boundary is
now enforced by named, tested code.

| Phase | Responsibility | Status |
| --- | --- | --- |
| Authoring | Source of declarations. The authoring layer is the only authority that may classify a construct as exact, constrained, or open; downstream stages MUST treat that classification as immutable input. | active — closed Pydantic models, the leaf classifier, and the typed scenario/scoped `realization` designation surface carry author intent without conflating it with apparatus capability. |
| Validation | Apparatus declarations and SDL designation scopes are structurally and semantically validated, including canonical pointers, namespace ownership, and equal-specificity conflicts. | active — contract shape gates and `SemanticValidator` enforce both authorities fail closed. |
| Instantiation | Parameter and default substitution may resolve open concerns and constrained surfaces. Substitution MUST NOT downgrade an exact declaration into a constrained or open one, and MUST NOT introduce an exact declaration that the author did not write. The concrete scenario MUST be revalidated after substitution. | active — `instantiate_scenario` preserves explicitness plus typed designation provenance and revalidates concrete content. |
| Compilation | Lowers each declaration into a typed runtime requirement preserving class. Exact requirements carry their declared kind into the compiled representation; constrained requirements carry the typed constraint surface; open requirements are emitted as realizable slots tagged with the realization-and-disclosure family. | active — `compile_runtime_model` applies leaf precedence and the scoped cascade, carrying open and delegated demand plus its governing scope. |
| Planning | Matches every compiled requirement against the candidate backend manifest. An unsupported exact-requirement-kind MUST cause plan rejection through a structured `Diagnostic` before deployment; an unsupported constraint-kind MUST cause the same outcome. An open realizable slot MAY be left for the backend only when its manifest declares matching support. | active — the planner rejects open demand without explicit `OPEN_REALIZATION` support and never approximates it. |
| Execution | Backend realizers honor the compiled class. A runtime adapter MUST NOT silently broaden an exact requirement, MUST NOT silently narrow an open realization beyond its declared constraints, and MUST surface incompatibilities through the existing runtime error envelope rather than approximate. | active — the runtime non-approximation gate `raes_processor.semantics.realization.realization_disclosure` (invoked from `raes_runtime.backend_calls._call_backend_apply`) compares each realized exact concern against the author declaration and rejects a silent approximation with a `runtime.backend-contract-invalid` diagnostic before the backend snapshot is accepted. |
| Observation | Realized values land in plan, result, snapshot, history, and evidence surfaces with provenance per I5. Realization choices are observation data, not private backend state. | active — realized concerns are recorded on the runtime snapshot envelope's `realization_provenance` ledger with their explicitness class and author-declared / processor-derived / backend-realized origin; the snapshot is the aggregate observation surface that carries result and history data. |

## Cross-Cutting Gates

A SEM-218 realization MUST pass every gate it touches. The binding
gates, with the spec invariant they enforce and their current
realization status, are:

- **SDL parser gate** — `${var}` substitution MUST NOT create or rename
  an exact-declaration identity (I1, I3). *Enforced today* by the
  variable-key rejection rules in `raes.parser`.
- **SDL model gate** — explicit-vs-open state MUST live in typed fields
  or structured extension surfaces, not untyped `dict` side channels
  (I3). *Enforced today* by the closed Pydantic SDL models
  (`extra="forbid"`).
- **Semantic validation gate** — exact declarations MUST be validated
  as exact; open realizable concerns MUST still be checked for shape,
  scope, and ambiguity (I1, I3). *Enforced today* by
  `SemanticValidator` and `SDLValidationError`.
- **Apparatus-contract shape gate** — backend
  `RealizationSupportDeclaration` declarations MUST satisfy the three
  shape rules in I4 (`EXACT_ONLY` MUST NOT carry constraint kinds; at
  least one of constraint-kinds or exact-requirement-kinds MUST be
  declared; `disclosure_kinds` MUST NOT be empty). Processor manifests
  MUST NOT carry `realization_support`. *Enforced today* by
  `RealizationSupportDeclaration.__post_init__`,
  `RealizationSupportDeclarationModel._validate_realization_support`,
  the JSON-schema conditional gate, and the processor-manifest
  rejection rule.
- **Instantiation gate** — substitution MUST NOT downgrade an exact
  declaration; concrete scenarios MUST be revalidated after
  substitution (I1). *Enforced today* by `instantiate_scenario`,
  `SDLInstantiationError`, and `raes.explicitness` deriving the
  instantiated explicitness map from the pre-substitution authored map.
- **Compiler / planner gate** — compiled exact, constrained, and open
  requirements MUST be matched against the selected backend's
  `realization_support`; unsupported kinds and unsupported open demand MUST
  cause `Diagnostic`-bearing rejection before
  deployment (I1, I2, I4). *Enforced today* by the typed compiler
  emission on `RuntimeModel.realization_requirements` and the
  realization-support plus open-request envelope-subsumption gates in
  `raes_processor.planner.plan`.
- **Error-envelope gate** — unsupported exact requirements and
  forbidden approximations MUST be surfaced through stable validation
  errors or structured diagnostics (I1, I2). *Enforced today*; the
  shape-gate errors and the planner's
  `realization.unsupported-exact-requirement` /
  `realization.unsupported-constraint-requirement` /
  `realization.unsupported-open-requirement` diagnostics surface unsupported
  demand before deployment.
- **Persistence and observation gate** — values entering snapshots,
  results, history, and evidence MUST carry provenance distinguishing
  author-declared, processor-derived, and backend-realized origins (I5).
  *Enforced today* by the `realization_provenance` ledger on the runtime
  snapshot envelope (`RealizationProvenanceEntry` /
  `RealizationProvenanceEntryModel`), which records each realized concern's
  explicitness class, origin, and governing designation scope and round-trips
  through the control-plane snapshot serializers and authenticated snapshot
  response model.
- **Host / OS exposure gate** — exact values, credentials, and backend
  tokens MUST NOT be passed through process argv, logs, audit details,
  diagnostics, JSON fixtures, or semantic-profile artifacts when they
  may carry sensitive material. *Enforced today* by the existing
  secret-handling discipline (gitleaks, private-key detection, the
  audit-detail redaction rules).

The companion at
`docs/explain/reference/explicitness-realization-semantics.md` records
implementer-facing architecture guidance for the gates above and is
**not normative**. Where its prose differs from this spec, the spec
governs; where the companion records detail that is not stated here, it
is implementer reference rather than a binding rule.

## Extensibility Seam

The extensibility seam is the existing `RealizationSupportDeclaration`
on backend manifests plus the `realization-and-disclosure` native
concept family. Future variation — additional exact-requirement-kinds,
additional constraint-kinds, additional disclosure-kinds — adds new
governed values to these surfaces and is consumed through the same
manifest-bound helper everywhere it is checked. Per-backend call-site
branches or one-off planner heuristics are non-conforming.

The governance of the surface is **staged**:

- `RealizationSupportMode` is the only `RealizationSupportDeclaration`
  field with a governed controlled vocabulary today (`EXACT_ONLY`,
  `CONSTRAINED`, `OPEN_REALIZATION`); the contract model accepts those
  three values and rejects others.
- `domain`, `supported_exact_requirement_kinds`,
  `supported_constraint_kinds`, and `disclosure_kinds` are currently
  validated only as non-empty strings (the `__post_init__` invariants
  and `RealizationSupportDeclarationModel` enforce shape, not value
  membership). The contract model at
  `implementations/python/packages/raes_contracts/contracts/`
  declares each as `list[NonEmptyString]`; the controlled-vocabulary
  authority does not yet bind those slots.
- Adding governed vocabularies for those four fields is normative
  future work that closes a planner-side authority gap. Until then,
  manifests MAY publish project-defined kind strings, and a planner
  that consults them MUST compare them as opaque strings. This spec
  binds the planner to that matching contract; it does **not** rely
  on a vocabulary authority for those values existing today.

A future change that introduces a new governed exact-requirement kind
adds the constant in the controlled-vocabulary surface, adds matching
`supported_exact_requirement_kinds` entries to backend manifests that
can carry it, and reuses the existing planner gate — it MUST NOT
duplicate the match logic across the compiler, planner, conformance
suite, and backend adapters.

## Anti-Patterns

A SEM-218 realization MUST NOT:

- treat the apparatus manifest's `realization_support` as a substitute
  for authoring semantics — the manifest discloses *capability*, not
  *intent*;
- treat `OPEN_REALIZATION` as permission to ignore an exact author
  declaration that landed in the same domain;
- treat missing data at a non-realizable point as equivalent to backend
  freedom — closed-world is the default;
- silently downgrade an exact requirement into a constrained or
  best-effort realization;
- carry explicitness flags inside free-text `constraints` strings or
  similar untyped side channels;
- duplicate realization-support matching in the compiler, planner,
  conformance suite, and backend adapters instead of sharing the same
  manifest-bound helper;
- add a second exception hierarchy, schema registry, controlled
  vocabulary, or manifest contract for explicitness semantics;
- treat semantic profiles as backend capability profiles, or backend
  capability profiles as semantic profiles.

## Implementation Mapping

The rules above are realized today by these existing surfaces; every
invariant I1–I5 is enforced by named code.

- I4 shape floor (backend manifests) — apparatus contract:
  `implementations/python/packages/raes_contracts/apparatus.py`
  (`RealizationSupportDeclaration.__post_init__` rejects empty kinds and
  forbids `EXACT_ONLY` with `supported_constraint_kinds`).
- I4 JSON-schema gate (backend manifests) —
  `implementations/python/packages/raes_contracts/contracts/`
  (`RealizationSupportDeclarationModel._validate_realization_support`
  and the `__get_pydantic_json_schema__` conditional schema, exercised
  by published `contracts/schemas/`).
- I4 processor-vs-backend asymmetry — `ProcessorManifestV2Model` in
  `implementations/python/packages/raes_contracts/contracts/` rejects
  any `realization_support` section; the generated processor schema has
  no `realization_support` property.
- I4 backend-manifest payload boundary —
  `implementations/python/packages/raes_backend_protocols/manifest.py`
  (sorted-kind serialization preserves the contract under
  canonicalization).
- I3 concept-authority binding —
  `contracts/concept-authority/concept-families-v1.json`
  (`realization-and-disclosure` family is the native authority for what
  may be realized at all).
- I1, I3 fail-closed authoring / validation —
  `implementations/python/packages/raes/explicitness.py`,
  `implementations/python/packages/raes/validator/`,
  `implementations/python/packages/raes/instantiate.py`
  (closed-world validation, classifier output on validated scenarios,
  and substitution-downgrade metadata on instantiated scenarios).
- I4 fail-closed evidence — invalid fixtures
  `contracts/fixtures/backend-manifest/backend-manifest-v2/invalid/hollow-realization-support.json`,
  `contracts/fixtures/backend-manifest/backend-manifest-v2/invalid/malformed-realization-support.json`,
  `contracts/fixtures/processor-manifest/processor-manifest-v2/invalid/hollow-realization-support.json`,
  `contracts/fixtures/processor-manifest/processor-manifest-v2/invalid/malformed-realization-support.json`.
- I1, I2, I4 typed compiler emission + planner gate —
  `raes_processor.compiler._compile_realization_requirements` emits
  `RuntimeModel.realization_requirements`, and
  `raes_processor.semantics.realization.realization_support_diagnostics`
  (called from `raes_processor.planner.plan`) matches them against the
  backend's `realization_support`, rejecting unsupported kinds with a
  `Diagnostic`. `realization_envelope_diagnostics` projects the offered
  envelope onto compiled open concern paths and calls the canonical
  `subsumes()` relation.
- I2 runtime non-approximation gate —
  `raes_processor.semantics.realization.realization_disclosure` (re-exported
  through `raes_processor.planner`), invoked from
  `raes_runtime.backend_calls._call_backend_apply`, compares each realized
  exact concern against the author declaration and rejects a silent
  approximation with a `runtime.backend-contract-invalid` diagnostic before the
  backend snapshot is accepted.
- I5 runtime provenance — the `realization_provenance` ledger
  (`RealizationProvenanceEntry` in
  `implementations/python/packages/raes_contracts/runtime_state.py`, published as
  `RealizationProvenanceEntryModel` on the `runtime-snapshot-v1` envelope)
  records each realized concern's explicitness class and author-declared /
  processor-derived / backend-realized origin, and round-trips through the
  control-plane snapshot serializers.

## Tests

- `implementations/python/tests/test_backend_manifest.py` —
  backend-manifest shape-gate rejection: hollow `realization_support`,
  malformed declarations, `EXACT_ONLY` combined with
  `supported_constraint_kinds` (I4 structural floor).
- `implementations/python/tests/test_processor_manifest.py` —
  `test_processor_manifest_v2_rejects_realization_support_section`
  enforces the processor-vs-backend asymmetry (I4 scope).
- `implementations/python/tests/test_runtime_contracts.py` —
  JSON-schema conditional gate for backend manifests and the assertion
  that the generated processor schema has no `realization_support`
  property (I4 shape + scope).
- `implementations/python/tests/test_sem_218_explicitness.py` —
  SDL-scenario classifier output for representative exact,
  constrained, and open declarations; instantiation substitution
  downgrade; and unclassifiable variable diagnostics.
- `implementations/python/tests/test_sem_218_realization.py` —
  typed compiler emission preserving the class through compilation,
  and the planner realization-support gate rejecting an unsupported
  exact or constrained requirement kind.
- `implementations/python/tests/test_sem_218_runtime_realization.py` —
  the runtime non-approximation gate rejecting a silently-weakened exact
  realization (I2), the `realization_provenance` ledger recorded for honoured
  concerns (I5), the rejection diagnostic naming the field path and kind but
  not the value, and the ledger's round-trip through snapshot persistence.
- `implementations/python/tests/test_sem_218_realization_designation.py` —
  typed scenario/scoped designation parsing, both cascade override directions,
  explicit-leaf precedence, delegation-versus-omission preservation,
  namespace isolation, canonical-pointer rejection, open-support planning,
  fine-envelope subsumption, governing-scope disclosure, authenticated
  persistence delivery, and schema/model differential coverage.

## Non-Goals

This spec does not:

- add realization fields to individual SDL declarations — explicit leaves are
  still classified from their typed fields, while inherited defaults use the
  single scenario-root `realization` designation surface;
- enumerate the full set of governed exact-requirement-kinds — that
  expansion belongs to the controlled-vocabulary and reference-model
  authorities;
- define participant behavior, observation, evidence, view-boundary, or
  temporal semantics — those are owned by `SEM-208`–`SEM-229` and build
  on this boundary;
- replace `ADR-016`'s seven-phase lifecycle model — SEM-218 maps onto
  those phases, not around them;
- amend the assurance-policy mapping or change FM-classification
  thresholds — those remain governed by `ADR-007` and `ADR-018`.

## Prior Art

The semantics above synthesize patterns from established declarative
languages, scenario / playbook DSLs, and academically-supported cyber
SDLs. The repository's curated primary-source corpus is at
`research/research/primary/literature/`. The most directly relevant
precedents:

- **Modelica `fixed` and `start` attributes** (Modelica Language
  Specification): the `fixed = true` annotation on an initial value
  makes the value a binding constraint a solver MUST honor; `fixed =
  false` makes it a hint a solver MAY revise. This is the cleanest
  field-level prior model for the exact-vs-open distinction in I1 / I3.
- **PDDL `:requirements`** (Ghallab et al, *PDDL — The Planning Domain
  Definition Language*, 1998; IPC competitions): a planning domain
  declares features it requires, and a planner MUST refuse to plan over
  a domain whose `:requirements` it cannot fully support. Direct
  precedent for the I1 / I2 fail-closed rule and for I4 capability
  disclosure.
- **OMG MDA — PIM / PSM separation** (OMG, *MDA Guide*, 2003): the
  platform-independent model holds binding author intent; the
  platform-specific model holds the realization. Transformations are
  semantics-preserving and refuse non-realizable inputs. Precedent for
  treating authoring-intent and realization as distinct authorities
  rather than a single mutable record.
- **XML Schema PSVI** (W3C XSD, *Post-Schema-Validation Infoset*):
  infoset items carry provenance distinguishing input, defaulted, and
  fixed values; fixed values cannot be silently overridden. Precedent
  for I5 (provenance) and for the closed-world default on non-realizable
  points.
- **OWL Open-World Assumption** (W3C OWL 2): silence about an assertion
  is not negation. SEM-218 deliberately **diverges**: at non-realizable
  SDL points the ecosystem is closed-world by default, because honest
  reproducibility requires the failure mode "I cannot realize this" to
  be louder than the failure mode "I quietly assumed something".
- **OASIS CACAO v2** (`research/research/primary/literature/dsl-and-standards/cacao_v2_spec.pdf`):
  RFC 2119 field-level MUST / SHOULD / MAY semantics in a security
  playbook DSL; consumers MUST reject playbooks whose
  `playbook_extensions` are not supported, rather than silently dropping
  them. Direct analogue for I1 / I2 / I4.
- **OASIS OpenC2 v2** (`research/research/primary/literature/dsl-and-standards/openc2_v2_spec.html`):
  required `target` versus optional `args`; actuators advertise
  supported actions and reject commands outside that surface.
  Apparatus-manifest analogue for I4.
- **Costa et al 2020, *VSDL — A Virtual Scenario Description Language***
  (`research/research/primary/literature/dsl-and-standards/costa2020_vsdl.pdf`): distinguishes scenario
  template (open over parameters) from instantiated scenario (closed
  after binding); processor rejects scenarios it cannot fully
  instantiate rather than approximating. Precedent for the
  authoring / validation / instantiation boundary above.
- **Sigma rules** (`research/research/primary/literature/dsl-and-standards/sigma_rules_spec.yml`):
  detection rules with backend-translation semantics that require a
  backend to signal `unsupported` rather than silently drop or
  approximate a field. Reinforces I2.
- **CACAO playbook-extensions, OpenC2 actuator profiles, and Sigma
  backend profiles** all share the same general shape with the
  `RealizationSupportDeclaration` per-domain mode used here. SEM-218
  adopts the shape and makes its semantics normative for RAES.
- **Pham et al 2016 *CyRIS***
  (`research/research/primary/literature/dsl-and-standards/pham2016_cyris.pdf`),
  **Vykopal et al 2017 *KYPO***
  (`research/research/primary/literature/dsl-and-standards/vykopal2017_kypo.pdf`),
  **Standen et al 2021 *CybORG***
  (`research/research/primary/literature/dsl-and-standards/standen2021_cyborg.pdf`): academically
  published cyber-range and agent-evaluation systems whose authoring
  layers separate declared scenario structure from runtime instantiation
  choices. Aligned with the lifecycle-phase responsibilities above.

The prior art is not normative — this spec is. The citations record the
ecosystems whose practice SEM-218 is consistent with, so a reader can
verify the design decisions against published precedent.
