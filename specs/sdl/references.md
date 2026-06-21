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
   Used by objective windows. Because `.` separates the workflow from the step,
   workflow **step** identifiers MUST NOT contain `.`
   ([document-model.md §6](document-model.md)).
5. **Module-composed (namespaced)** — after a module import is expanded, imported
   elements are addressed under their import namespace, and node segments are
   rewritten to their namespaced form. Module-composed references resolve against
   the expanded document
   ([ADR-053](../../docs/decisions/adrs/adr-053-sdl-module-composition-for-inventory-backed-scenarios.md)).

### Dotted node identifiers

A node identifier MAY itself contain `.` (e.g. `wazuh.manager`). A qualified
reference that traverses a node segment therefore resolves the **longest**
node-identifier match rather than splitting on the first `.`. Resolution MUST
account for dotted node names so that `nodes.wazuh.manager.runtime.…` addresses
the `wazuh.manager` node, not a `wazuh` node with a `manager` member.

## 2. Resolution algorithm

1. A reference **MUST** resolve to **exactly one** declared element of a kind the
   referencing field accepts.
2. A field defines its **candidate set** — the section or sections a value may
   name. Some fields accept a single section (e.g. `metric.condition_ref` →
   `conditions`); others accept a set of targetable sections (e.g. an
   objective's `target`, a relationship's `source`/`target`). The candidate set
   is part of each field's definition and is reflected in the edge catalog (§5).
3. A **bare** reference resolves against the candidate set. A **qualified**
   reference resolves against the named section/path and MUST match it exactly.
4. Some targetable candidate sets are deliberately restricted. For example, an
   objective `target` excludes the `variables`, `objectives`, and `workflows`
   prefixes; an agent `operating_scope` is restricted to VM nodes,
   switch-backed infrastructure, services, and content. A reference outside its
   field's candidate set does not resolve and fails as dangling (§4).
5. Resolution is **declaration-based**: only declared elements are resolution
   targets. There is no implicit creation of a target by referencing it.

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

### Assessment pipeline

| Source | Field | Target |
|--------|-------|--------|
| `metrics` | condition ref | `conditions` |
| `evaluations` | metric refs | `metrics` |
| `tlos` | evaluation refs | `evaluations` |
| `goals` | tlo refs | `tlos` |

A condition referenced by a metric MUST be scored by exactly one metric;
an evaluation's minimum score MUST NOT exceed the sum of its metrics' maxima.

### Narrative chain

| Source | Field | Target |
|--------|-------|--------|
| `injects` | from/to entity | `entities` |
| `injects` | tlo refs | `tlos` |
| `events` | condition refs | `conditions` |
| `events` | inject refs | `injects` |
| `scripts` | event refs | `events` |
| `stories` | script refs | `scripts` |

### Composition graph

| Source | Field | Target |
|--------|-------|--------|
| `features` | vulnerability refs | `vulnerabilities` |
| `features` | dependencies | `features` (acyclic) |
| `entities` | tlos / vulnerabilities | `tlos` / `vulnerabilities` |
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
| `objectives` | success criteria | `conditions`/`metrics`/`evaluations`/`tlos`/`goals` |
| `objectives` | window | `stories`/`scripts`/`events`/`workflows` (with closure rules) |
| `objectives` | depends_on | `objectives` (acyclic) |
| `outcome_interpretation_rules` | source | `action_contracts`/`objectives`/`workflows`/`evaluations` |
| `outcome_interpretation_rules` | target | `objectives`/`workflows`/`evaluations` |

### Workflows

| Source | Field | Target |
|--------|-------|--------|
| `workflows` | start | own steps |
| `workflows` | step successors (`on_success`/`on_failure`) | own steps |
| `workflows` | compensation | other `workflows` |
| `workflows` | predicate assessment refs | `conditions`/`metrics`/`evaluations`/`tlos`/`goals` |
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

## Extending the reference catalog

A new reference edge is added by defining the field's candidate set, adding a
row here, and enforcing it in the reference implementation and tests. New
runtime-family child refs follow the nested runtime-family form (§1.3)
automatically once registered in the family index
([runtime-inventory.md](runtime-inventory.md)); they do not need bespoke prose.
