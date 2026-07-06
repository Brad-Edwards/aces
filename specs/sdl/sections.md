# Catalog 1 — Section Catalog

This catalog enumerates every top-level field of an SDL document: its kind, its
value shape, whether it is required, the shape of its keys, and the sections it
references. It is the normative section enumeration and is written to match the
published `contracts/schemas/sdl/sdl-authoring-input-v1.json` schema; where this
table and that schema diverge, the divergence is a defect to reconcile
([README](README.md)).

Value-shape legend:

- **scalar** — a single string value.
- **mapping** — a mapping with fixed keys (a structured object, not keyed by
  user identifiers).
- **map** — a mapping keyed by **user-defined identifiers**, each value an
  element of the named type.
- **list** — an ordered sequence of elements; element identity is carried by an
  `<noun>_id` field on each element, not by a mapping key.

"References" names the other sections an element of this section may name; the
resolution rules and full reference-edge catalog with failure semantics are in
[`references.md`](references.md). A blank "References" cell means the section is
referenced by others but does not itself reference another section.

## Metadata and composition fields

These describe the document and its composition. They are **not** authoring
sections.

| Field | Shape | Required | Notes |
|-------|-------|----------|-------|
| `name` | scalar | **REQUIRED** | The scenario identity. The only required top-level field. |
| `version` | scalar | optional (default `*`) | Scenario version; `*` means unpinned. |
| `description` | scalar | optional (default empty) | Free-text description. |
| `module` | mapping \| null | optional (default null) | Published module metadata when this document is a composable module: a canonical `publisher/name` id, a `version`, declared `parameters`, and `exports` ([ADR-053](../../docs/decisions/adrs/adr-053-sdl-module-composition-for-inventory-backed-scenarios.md)). |
| `imports` | list | optional (default empty) | Module imports. Each import names a module by `source` (or the deprecated `path`) and binds it under a `namespace` with `parameters`. Imports are expanded before full semantic validation ([document-model.md §7](document-model.md)). |

## Authoring sections — map-keyed

Each is a map keyed by a user-defined identifier ([document-model.md §6](document-model.md))
and defaults to an empty map when omitted.

| Section | Required | Key shape | References |
|---------|----------|-----------|------------|
| `nodes` | optional | identifier ≤ 35 chars; may contain `.` | `features`, `conditions`, `injects`, `vulnerabilities`; hosts the runtime inventory ([runtime-inventory.md](runtime-inventory.md)) |
| `infrastructure` | optional | identifier matching a node | `nodes`; switch/network nodes; other `infrastructure` (dependencies) |
| `features` | optional | identifier | `vulnerabilities`; other `features` (dependencies, acyclic) |
| `conditions` | optional | identifier | — |
| `vulnerabilities` | optional | identifier | — |
| `entities` | optional | identifier | `vulnerabilities` |
| `injects` | optional | identifier | `entities` |
| `events` | optional | identifier | `conditions`, `injects` |
| `scripts` | optional | identifier | `events` |
| `stories` | optional | identifier | `scripts` |
| `content` | optional | identifier | `nodes` (VM target) |
| `accounts` | optional | identifier | `nodes` (VM) |
| `relationships` | optional | identifier | typed by subtype: `entities`/`accounts`/targetable elements; runtime families (`applications`, `database_services`, `mail_services`, `platform_applications`, `app_authorizations`); scenario `forwarding_agents` ([ADR-052](../../docs/decisions/adrs/adr-052-typed-runtime-relationship-subtypes.md)) |
| `agents` | optional | identifier | `entities`, `accounts`, `infrastructure`, `nodes`, `conditions`, `action_contracts`, `observation_boundaries`, targetable elements |
| `action_contracts` | optional | identifier | other `action_contracts` (interactions) |
| `observation_boundaries` | optional | identifier | own information refs (observable/hidden/evidence) |
| `outcome_interpretation_rules` | optional | identifier | `action_contracts`, `objectives`, `workflows` |
| `evidence_requirements` | optional | identifier | targetable elements for source, scope, channel, trigger, and boundary refs; distinct from `objectives` and scenario-native observability systems ([observability-and-evidence.md](observability-and-evidence.md)) |
| `objectives` | optional | identifier | `agents`/`entities` (actor), `action_contracts` (action), targetable elements (target), `conditions` (success — observable state only, [ADR-073](../../docs/decisions/adrs/adr-073-scoring-reward-language-scope.md)), `stories`/`scripts`/`events`/`workflows` (window), other `objectives` (depends_on, acyclic) |
| `workflows` | optional | identifier | own steps (`start`, successors), other `workflows` (compensation), `conditions` (predicates) |
| `variables` | optional | identifier matching `[A-Za-z_][A-Za-z0-9_-]*` | referenced by `${…}` placeholders ([variables-and-instantiation.md](variables-and-instantiation.md)) |

## Authoring section — list-valued

| Section | Shape | Required | Element identity | Referenced by |
|---------|-------|----------|------------------|---------------|
| `forwarding_agents` | list | optional (default empty) | `forwarding_agent_id` on each element | `relationships` (`forwarding_edge.forwarder_ref`) |

`forwarding_agents` is the **scenario-level** forwarding-agent inventory. It is
distinct from the node-scoped `forwarding_agents` runtime-family collection that
lives under `nodes.<id>.runtime` ([runtime-inventory.md](runtime-inventory.md));
both carry `forwarding_agent_id` identity and the same family invariants, but
they occupy different positions in the document.

## Narrative chain

One reference chain runs through the catalog and is called out because its
ordering is normative (resolution and failure semantics in
[`references.md`](references.md)):

- **Narrative chain:** `injects` → `events` → `scripts` → `stories`, with
  `injects` naming `entities` and `events` naming `conditions`. Objective
  windows bind `stories`/`scripts`/`events`/`workflows`.

`conditions` are observable state: an objective's success is expressed against
`conditions`, and workflow predicates reference `conditions`. The SDL carries no
graded scoring pipeline — the OCR-inherited `metrics`, `evaluations`, `tlos`
(Training Learning Objectives), and `goals` sections were removed with
[ADR-073](../../docs/decisions/adrs/adr-073-scoring-reward-language-scope.md).
Graded scoring, reward, leaderboard values, and evaluation outputs live in the
experiment/evaluator plane
([ADR-055](../../docs/decisions/adrs/adr-055-experiment-core-contract-boundary.md),
[ADR-064](../../docs/decisions/adrs/adr-064-experiment-evidence-and-measure-contract-boundary.md),
[ADR-069](../../docs/decisions/adrs/adr-069-cage-2-replication-architecture.md)),
never as authored SDL.

## Extending the section set

A new top-level authoring section is added by: defining its model and the
published schema field, adding a row to this catalog (with its shape,
requiredness, key shape, and references), adding its reference edges to
[`references.md`](references.md), and updating the reference implementation and
its tests. Scenario-native observability or authored evidence-requirement
sections must also satisfy
[`observability-and-evidence.md`](observability-and-evidence.md). No parallel
section registry exists or should be created.
