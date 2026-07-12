# Catalog 2 — Reference-Resolution Catalog

This catalog defines how one SDL element names another: the reference forms, the
resolution algorithm, the fail-closed ambiguity rule, the treatment of
unresolved variable placeholders, and the catalog of cross-section reference
edges with their failure semantics.

References are resolved during **semantic validation**, after structural parsing
and module expansion ([document-model.md §7](document-model.md)). Reference
failures are fatal and are collected together ([diagnostics.md](diagnostics.md)).

## 1. Reference forms

A reference is a string that names a target element. Five forms exist:

1. **Bare** — a single identifier, e.g. `web_db`. Resolved within the section(s)
   the referencing field expects.
2. **Qualified** — a dotted path that names the section and identifier
   explicitly, e.g. `conditions.system_online`, or a deeper path that addresses
   a nested element, e.g. `nodes.web1.services.httpd`. Used to address an element
   unambiguously, or to address an element that has no bare form.
3. **Nested runtime-family** — a qualified path into a node's runtime inventory:
   `nodes.<node>.runtime.<collection>.<id>` and, for child collections,
   `…<collection>.<id>.<child-collection>.<child-id>` to any depth the family
   defines ([runtime-inventory.md](runtime-inventory.md)).
4. **Workflow-step** — `<workflow>.<step>`, naming a step within a workflow.
   Used by objective windows. The workflow portion may be a composition-generated
   qualified name and the step is exactly one portable local-id segment
   ([document-model.md §6](document-model.md)).
5. **Module-composed (namespaced)** — after a module import is expanded, imported
   elements are addressed under their import namespace, and node segments are
   rewritten to their namespaced form. Module-composed references resolve against
   the expanded document
   ([ADR-053](../../docs/decisions/adrs/adr-053-sdl-module-composition-for-inventory-backed-scenarios.md)).

Dots are path syntax, never authored identifier content. A dotted node key in a
raw or normalized authoring object is invalid. A dotted node segment seen after
composition is a validated namespace path and is carried structurally until the
canonical renderer produces the external string; it is not recovered with a
longest-match rule.

## 2. Resolution algorithm

1. A reference **MUST** resolve to **exactly one** declared element of a kind the
   referencing field accepts.
2. A field defines its **candidate set** — the section or sections a value may
   name. Some fields accept a single section (e.g. an objective's `success` →
   `conditions`); others accept a set of targetable sections (e.g. an
   objective's `target`, a relationship's `source`/`target`). The candidate set
   is part of each field's definition and is reflected in the edge catalog (§5).
3. A **bare** reference resolves against the candidate set. A **qualified**
   reference resolves by exact lookup of the typed canonical address and
   **MUST** match it exactly. Implementations **MUST NOT** discover ownership by
   `split`, `partition`, `rsplit`, longest-prefix guessing, declaration order,
   or first match. Compact aliases such as `<qualified-workflow>.<step>` are
   constructed and resolved from declared workflow/step pairs.
4. Some targetable candidate sets are deliberately restricted. For example, an
   objective `target` excludes the `variables`, `objectives`, and `workflows`
   prefixes; an agent `operating_scope` is restricted to VM nodes,
   switch-backed infrastructure, services, and content. A reference outside its
   field's candidate set does not resolve and fails as dangling (§4).
5. Resolution is **declaration-based**: only declared elements are resolution
   targets. There is no implicit creation of a target by referencing it.
6. Alias lookup occurs only after the canonical declaration index has retained
   kind and provenance for every declaration and rejected address collisions.
   A set or map that has already erased a duplicate rendering is not evidence of
   uniqueness.

## 3. Unresolved variable placeholders

1. A field whose value is a variable placeholder (`${name}`) is **not** resolved
   as a reference during authoring-time semantic validation; the placeholder
   stands for a value not yet bound.
2. The only requirement on an unresolved placeholder at authoring time is that
   `name` **MUST** be a declared variable
   ([variables-and-instantiation.md](variables-and-instantiation.md)). A
   placeholder naming an undeclared variable is a fatal error.
3. After instantiation substitutes a concrete value, the normal reference rules
   (§2) apply to that value. A reference that becomes dangling or ambiguous only
   after substitution fails at instantiation.

## 4. Failure semantics (fail-closed)

Reference resolution is fail-closed. Two failure modes exist, both fatal:

1. **Dangling** — the reference names no declared element in its candidate set
   (or, for a qualified reference, the path does not exist). This is an error.
2. **Ambiguous** — a bare reference matches **more than one** declared element in
   its candidate set. This is an error. An ambiguous reference **MUST NOT** be
   resolved by first match, by declaration order, or by source-file locality.
   The author resolves the ambiguity by using a qualified reference.

Additional structural reference constraints — uniqueness of an addressed
`<noun>_id`, acyclicity of dependency graphs (`features.dependencies`,
`objectives.depends_on`, workflow step graphs), and closure of workflow control
flow (every referenced successor/join step exists) — are likewise fatal when
violated.

All reference failures in a document are reported together in a single
validation pass rather than one-at-a-time ([diagnostics.md](diagnostics.md)).

## 5. Cross-section reference edge catalog

Each row is a reference edge: a source section's field names a target. Unless
noted, an unresolved (dangling) or ambiguous reference is a fatal error.

The SDL carries no graded scoring pipeline: the OCR-inherited `metrics`,
`evaluations`, `tlos`, and `goals` sections were removed with
[ADR-073](../../docs/decisions/adrs/adr-073-scoring-reward-language-scope.md), so
no reference edge targets them. Graded scoring, reward, and evaluation outputs
live in the experiment/evaluator plane (ADR-055/064/069). `conditions` remain the
observable-state target for objective success and workflow predicates.

### Narrative chain

| Source | Field | Target |
|--------|-------|--------|
| `injects` | from/to entity | `entities` |
| `events` | condition refs | `conditions` |
| `events` | inject refs | `injects` |
| `scripts` | event refs | `events` |
| `stories` | script refs | `scripts` |

### Composition graph

| Source | Field | Target |
|--------|-------|--------|
| `features` | vulnerability refs | `vulnerabilities` |
| `features` | dependencies | `features` (acyclic) |
| `entities` | vulnerabilities | `vulnerabilities` |
| `nodes` | feature/condition/inject/vulnerability refs | `features` / `conditions` / `injects` / `vulnerabilities` |
| `infrastructure` | node / link / dependency | `nodes` / switch-backed `infrastructure` |
| `content` | target | `nodes` (VM) |
| `accounts` | node | `nodes` (VM) |

### Agents, objectives, participant surfaces

| Source | Field | Target |
|--------|-------|--------|
| `agents` | entity | `entities` |
| `agents` | starting accounts | `accounts` |
| `agents` | subnets / initial-knowledge subnets | switch-backed `infrastructure` |
| `agents` | initial-knowledge hosts | `nodes` (VM) |
| `agents` | initial-knowledge services | declared services on nodes |
| `agents` | starting conditions | `conditions` |
| `agents` | actions / observation boundaries | `action_contracts` / `observation_boundaries` |
| `action_contracts` | interaction related-action | `action_contracts` |
| `observation_boundaries` | view-rule information refs | own observable/hidden/evidence refs |
| `objectives` | actor | `agents` or flattened `entities` |
| `objectives` | action | the bound agent's `action_contracts` |
| `objectives` | target | targetable elements (excl. `variables`/`objectives`/`workflows`) |
| `objectives` | success criteria | `conditions` (observable state only, [ADR-073](../../docs/decisions/adrs/adr-073-scoring-reward-language-scope.md)) |
| `objectives` | window | `stories`/`scripts`/`events`/`workflows` (with closure rules) |
| `objectives` | depends_on | `objectives` (acyclic) |
| `outcome_interpretation_rules` | source | `action_contracts`/`objectives`/`workflows` |
| `outcome_interpretation_rules` | target | `objectives`/`workflows` |

### Observability and evidence authoring

| Source | Field | Target |
|--------|-------|--------|
| `evidence_requirements` | source refs | targetable elements, including scenario-native observability runtime-family refs |
| `evidence_requirements` | scope refs | targetable elements |
| `evidence_requirements` | channel refs | targetable elements |
| `evidence_requirements` | trigger / boundary refs | targetable elements |

`evidence_requirements` entries are authored capture obligations. They are not
objective targets, workflow steps, variables, or evidence records. Bare
runtime-family child identifiers do not resolve; authors use the qualified
`nodes.<node>.runtime.<collection>.<id>` form when a node-scoped runtime-family
element is the source or channel.

### Workflows

| Source | Field | Target |
|--------|-------|--------|
| `workflows` | start | own steps |
| `workflows` | step successors (`on_success`/`on_failure`) | own steps |
| `workflows` | compensation | other `workflows` |
| `workflows` | predicate condition refs | `conditions` (observable state) |
| `workflows` | predicate step refs | own steps (executable) |

Parallel/join control flow MUST be closed: every branch reaches its join and no
join is unreferenced.

### Typed relationships

`relationships` carry a subtype that fixes the kinds of `source`/`target` and
any role-bearing refs
([ADR-052](../../docs/decisions/adrs/adr-052-typed-runtime-relationship-subtypes.md)):

| Subtype | Endpoints / role refs resolve to |
|---------|----------------------------------|
| generic | targetable elements (`source`/`target`) |
| `database_access` | `source` → an `applications` element; `target` → a `database_services` element; role ref → a declared role on the target |
| `mail_access` | `target` → a `mail_services` element; listener/mailbox/domain refs → declared children of that mail service |
| `forwarding_edge` | `forwarder_ref` → exactly one `forwarding_agents` element (node-scoped or scenario-level); protocol/role MUST agree with a declared ship target |
| `service_integration` | consumer/engine refs → `platform_applications`; auth-principal ref → a declared app-authorization on the engine's node |
| `proxy_upstream` | upstream → a resolved runtime application/endpoint |

### Variables

| Source | Field | Target |
|--------|-------|--------|
| any field | `${name}` placeholder | a declared `variables` entry (name only, at authoring time) |

## 6. Machine-checkable reference-edge index

This index gives every editor-visible reference field a stable candidate-domain
token and makes the participant behavior surface explicit. It complements the
semantic detail above: subtype-specific relationship and nested-runtime rules
remain narrower than the broad completion domain recorded here. `targetable`
means the declaration index excluding `variables`, `evidence_requirements`,
`objectives`, and `workflows`; it is not a synonym for every named object.
`derived:*`, `vocabulary:*`, `registry:*`, `contract:*`, and `opaque:*` name
deliberately distinct resolution mechanisms and MUST NOT be collapsed into a
generic symbol lookup.

| Source path | Candidate domain | Resolution phase | Failure | Semantic owner |
| --- | --- | --- | --- | --- |
| `nodes.*.features[]` | `features` | semantic validation | fatal dangling or ambiguous | [node validator](../../implementations/python/packages/aces_sdl/validator/_nodes_infra_network.py) |
| `nodes.*.conditions[]` | `conditions` | semantic validation | fatal dangling or ambiguous | [node validator](../../implementations/python/packages/aces_sdl/validator/_nodes_infra_network.py) |
| `nodes.*.injects[]` | `injects` | semantic validation | fatal dangling or ambiguous | [node validator](../../implementations/python/packages/aces_sdl/validator/_nodes_infra_network.py) |
| `nodes.*.vulnerabilities[]` | `vulnerabilities` | semantic validation | fatal dangling or ambiguous | [node validator](../../implementations/python/packages/aces_sdl/validator/_nodes_infra_network.py) |
| `infrastructure.*.links[]` | `infrastructure` | semantic validation | fatal dangling or ambiguous | [infrastructure validator](../../implementations/python/packages/aces_sdl/validator/_nodes_infra_network.py) |
| `infrastructure.*.dependencies[]` | `infrastructure` | semantic validation | fatal dangling or ambiguous | [infrastructure validator](../../implementations/python/packages/aces_sdl/validator/_nodes_infra_network.py) |
| `features.*.dependencies[]` | `features` | semantic validation | fatal dangling, ambiguous, or cyclic | [section validator](../../implementations/python/packages/aces_sdl/validator/_sections.py) |
| `entities.*.vulnerabilities[]` | `vulnerabilities` | semantic validation | fatal dangling or ambiguous | [section validator](../../implementations/python/packages/aces_sdl/validator/_sections.py) |
| `injects.*.from_entity` | `entities` | semantic validation | fatal dangling or ambiguous | [section validator](../../implementations/python/packages/aces_sdl/validator/_sections.py) |
| `injects.*.to_entities[]` | `entities` | semantic validation | fatal dangling or ambiguous | [section validator](../../implementations/python/packages/aces_sdl/validator/_sections.py) |
| `events.*.conditions[]` | `conditions` | semantic validation | fatal dangling or ambiguous | [section validator](../../implementations/python/packages/aces_sdl/validator/_sections.py) |
| `events.*.injects[]` | `injects` | semantic validation | fatal dangling or ambiguous | [section validator](../../implementations/python/packages/aces_sdl/validator/_sections.py) |
| `scripts.*.events[]` | `events` | semantic validation | fatal dangling or ambiguous | [section validator](../../implementations/python/packages/aces_sdl/validator/_sections.py) |
| `stories.*.scripts[]` | `scripts` | semantic validation | fatal dangling or ambiguous | [section validator](../../implementations/python/packages/aces_sdl/validator/_sections.py) |
| `content.*.target` | `nodes` | semantic validation | fatal unless target is a VM node | [content validator](../../implementations/python/packages/aces_sdl/validator/_content_objectives.py) |
| `accounts.*.node` | `nodes` | semantic validation | fatal unless target is a VM node | [account validator](../../implementations/python/packages/aces_sdl/validator/_content_objectives.py) |
| `relationships.*.source` | `targetable` | semantic validation | fatal dangling or ambiguous; subtype may narrow domain | [relationship validator](../../implementations/python/packages/aces_sdl/validator/_relationships.py) |
| `relationships.*.target` | `targetable` | semantic validation | fatal dangling or ambiguous; subtype may narrow domain | [relationship validator](../../implementations/python/packages/aces_sdl/validator/_relationships.py) |
| `agents.*.entity` | `entities` | semantic validation | fatal dangling or ambiguous | [participant validator](../../implementations/python/packages/aces_sdl/validator/_content_objectives.py) |
| `agents.*.starting_accounts[]` | `accounts` | semantic validation | fatal dangling or ambiguous | [participant validator](../../implementations/python/packages/aces_sdl/validator/_content_objectives.py) |
| `action_contracts.*.interactions.*.related_action_ref` | `action_contracts` | semantic validation | fatal dangling or ambiguous | [participant semantics](../../implementations/python/packages/aces_sdl/semantics/participant_behavior.py) |
| `observation_boundaries.*.view_rules.*.information_refs[]` | `derived:boundary_information` | semantic validation | fatal outside declared boundary information | [participant semantics](../../implementations/python/packages/aces_sdl/semantics/participant_behavior.py) |
| `outcome_interpretation_rules.*.source_ref` | `action_contracts,objectives,workflows` | semantic validation | fatal dangling or ambiguous | [outcome semantics](../../implementations/python/packages/aces_sdl/semantics/participant_outcome.py) |
| `behavior_specifications.*.participant_refs[]` | `agents` | semantic validation | fatal dangling or ambiguous | [behavior semantics](../../implementations/python/packages/aces_sdl/semantics/participant_behavior.py) |
| `behavior_specifications.*.participant_role_refs[]` | `derived:agent_roles` | semantic validation | fatal unless bound by a referenced participant | [behavior semantics](../../implementations/python/packages/aces_sdl/semantics/participant_behavior.py) |
| `behavior_specifications.*.action_contract_refs[]` | `action_contracts` | semantic validation | fatal dangling or ambiguous | [behavior semantics](../../implementations/python/packages/aces_sdl/semantics/participant_behavior.py) |
| `behavior_specifications.*.observation_boundary_refs[]` | `observation_boundaries` | semantic validation | fatal dangling or ambiguous | [behavior semantics](../../implementations/python/packages/aces_sdl/semantics/participant_behavior.py) |
| `behavior_specifications.*.outcome_interpretation_rule_refs[]` | `outcome_interpretation_rules` | semantic validation | fatal dangling or ambiguous | [behavior semantics](../../implementations/python/packages/aces_sdl/semantics/participant_behavior.py) |
| `behavior_specifications.*.authority_scope_refs[]` | `targetable` | semantic validation | fatal dangling or ambiguous | [behavior validator](../../implementations/python/packages/aces_sdl/validator/_content_objectives.py) |
| `behavior_specifications.*.behavior_mode` | `vocabulary:behavior_mode` | structural validation | fatal invalid vocabulary value | [behavior model](behavior-specifications.md) |
| `behavior_specifications.*.ai_offensive_behavior_refs[]` | `vocabulary:ai_offensive_behavior` | semantic validation | fatal unknown vocabulary identifier | [behavior model](behavior-specifications.md) |
| `behavior_specifications.*.offensive_behavior_refs[]` | `vocabulary:offensive_behavior` | semantic validation | fatal unknown vocabulary identifier | [behavior model](behavior-specifications.md) |
| `behavior_specifications.*.realization_profile_ref` | `opaque:realization_profile` | structural validation | fatal invalid reference shape; resolution belongs to realization | [behavior model](behavior-specifications.md) |
| `behavior_specifications.*.backend_feature_support_refs[]` | `registry:behavior_features` | semantic validation | fatal unsupported feature identifier | [behavior semantics](../../implementations/python/packages/aces_sdl/semantics/participant_behavior.py) |
| `behavior_specifications.*.evidence_contract_refs[]` | `contract:participant_evidence` | semantic validation | fatal unknown contract identifier | [behavior semantics](../../implementations/python/packages/aces_sdl/semantics/participant_behavior.py) |
| `evidence_requirements.*.source_refs[]` | `targetable` | semantic validation | fatal dangling or ambiguous | [evidence validator](../../implementations/python/packages/aces_sdl/validator/_evidence_requirements.py) |
| `evidence_requirements.*.scope_refs[]` | `targetable` | semantic validation | fatal dangling or ambiguous | [evidence validator](../../implementations/python/packages/aces_sdl/validator/_evidence_requirements.py) |
| `evidence_requirements.*.channel_refs[]` | `targetable` | semantic validation | fatal dangling or ambiguous | [evidence validator](../../implementations/python/packages/aces_sdl/validator/_evidence_requirements.py) |
| `evidence_requirements.*.trigger_ref` | `targetable` | semantic validation | fatal dangling or ambiguous | [evidence validator](../../implementations/python/packages/aces_sdl/validator/_evidence_requirements.py) |
| `evidence_requirements.*.boundary_ref` | `targetable` | semantic validation | fatal dangling or ambiguous | [evidence validator](../../implementations/python/packages/aces_sdl/validator/_evidence_requirements.py) |
| `objectives.*.agent` | `agents` | semantic validation | fatal dangling or ambiguous | [objective semantics](objective-semantics.md) |
| `objectives.*.entity` | `entities` | semantic validation | fatal dangling or ambiguous | [objective semantics](objective-semantics.md) |
| `objectives.*.targets[]` | `targetable` | semantic validation | fatal dangling or ambiguous | [objective semantics](objective-semantics.md) |
| `objectives.*.depends_on[]` | `objectives` | semantic validation | fatal dangling, ambiguous, or cyclic | [objective semantics](objective-semantics.md) |
| `workflows.*.start` | `workflow_steps` | semantic validation | fatal dangling step | [workflow semantics](workflow-semantics.md) |

The index is checked against language-service completion metadata and against a
required behavior-edge set. Adding a completion-aware field or behavior
reference without a corresponding row fails the repository contract gate.

## Extending the reference catalog

A new reference edge is added by defining the field's candidate set, adding a
row here, and enforcing it in the reference implementation and tests. New
runtime-family child refs follow the nested runtime-family form (§1.3)
automatically once registered in the family index
([runtime-inventory.md](runtime-inventory.md)); they do not need bespoke prose.
