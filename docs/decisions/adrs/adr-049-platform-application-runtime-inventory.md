# ADR-049: Platform Application Runtime Inventory

## Status

accepted

## Date

2026-05-30

## Context

SCN-010 (DSL-133) identifies an SDL expressivity gap for the
participant-observable runtime state of a node's security platform application:
the threat-intelligence platform (MISP), SOAR (Shuffle), analyzer engine
(Cortex), case-management application (TheHive), and analytics dashboard
(Kibana / OpenSearch Dashboards). These nodes already fit adjacent ACES surfaces
for transport listeners, HTTP routes, processes, and software identity, but no
surface carries the platform facts that matter to participants and downstream
consumers: the platform's bounded content manifests (taxonomies, galaxy
clusters, feeds, workflows, analyzers, case templates, dashboard saved objects),
releasability markings, upstream data-source bindings, and connectors.

Adjacent surfaces each own narrower meaning:

- `runtime.applications` records the HTTP/WS route surface, not the platform's
  internal content/binding inventory.
- `runtime.app_authorizations` records application-internal RBAC, referenced
  here only by a string `authorization_ref`.
- `runtime.software_components` records installed component identity.
- `runtime.datastore_services` records the datastore that may back a dashboard,
  referenced via an upstream binding rather than re-typed here.

The design risk is to inline raw object bodies (a full STIX bundle, a raw MISP
event, a serialized playbook) into the model, or to force platform semantics
into fake HTTP routes or free-form relationships — silently shallow-encoding a
defining fact such as a threat-intel platform with no taxonomy.

## Decision

### 1. Add a single discriminated platform-application spine under runtime

Add `Node.runtime.platform_applications`. Each entry is a single
`RuntimePlatformApplication` spine with a stable `platform_application_id`, an
optional same-node `service` ref, and an OPEN `platform_kind` discriminator
(`threat_intel` / `soar` / `analyzer_engine` / `case_management` /
`analytics_dashboard` / `unknown` / `other`).

### 2. Model content objects as bounded parsed manifests, never raw bodies

`content_objects` carry a typed `kind` (OPEN enum), bounded typed `attributes`,
typed `references` to sibling content objects, `marking_refs`, and
`evidence_refs` — structurally never a raw object body. `markings` carry a CLOSED
releasability `scheme` (`tlp` / `pap` / `distribution`).

### 3. Make the discriminator executable with a required-profile guard

A model-local `require_profile_for_platform_kind` after-validator fails an
under-populated instance. A `${var}` placeholder is exempt and `unknown` /
`other` are permissive, but each concrete kind requires its defining profile:

- `threat_intel` requires taxonomy, galaxy-cluster, warninglist, feed, and
  sharing-group content objects.
- `soar` requires a workflow content object.
- `analyzer_engine` requires analyzer/responder content objects plus an
  `execution_policy`.
- `case_management` requires case-template and custom-field content objects.
- `analytics_dashboard` requires at least one saved-object content object
  (`index_pattern` / `visualization` / `dashboard` / `search`) carrying
  references, plus at least one `upstream_binding` with role `index_backend` /
  `data_source`.

### 4. Preserve typed child inventories and keep them targetable

The application owns id-bearing child collections (`organizations`, `tenants`,
`content_objects`, `markings`, `upstream_bindings`, `connectors`, `settings`) and
an optional `execution_policy`. Connectors and secret-bearing settings never
carry a raw credential value. Applications and id-bearing children may be
referenced from relationships using qualified refs:

- `nodes.<node>.runtime.platform_applications.<platform_application_id>`
- `...platform_applications.<id>.content_objects.<content_object_id>`
- `...platform_applications.<id>.markings.<marking_id>`
- `...platform_applications.<id>.upstream_bindings.<binding_id>`
- `...platform_applications.<id>.connectors.<connector_id>`

These refs are inventory targets. They do not imply playbook execution, analyzer
runs, feed ingestion, or dashboard rendering.

## Security and Validation Gates

- Parser/model gate: stable application and child ids are concrete symbols. Enum
  fields are normalized through the single runtime enum-parse helper. Duplicate
  application ids and duplicate application-local child ids fail early.
- Required-profile gate: the `require_profile_for_platform_kind` guard fails an
  under-populated `threat_intel` / `soar` / `analyzer_engine` /
  `case_management` / `analytics_dashboard` instance.
- Semantic validation gate: the owning `service` ref resolves to a same-node
  binding; a non-empty, non-variable `authorization_ref` resolves to a same-node
  `app_authorization`; content-object `references` resolve to sibling
  `content_object_id` values and `marking_refs` to sibling `marking_id` values.
- Relationship/reference gate: application and child qualified refs resolve in
  generic relationships and survive module import namespacing.
- Secret/payload gate: raw object bodies, credentials, and secret-bearing
  setting/connector values stay out of SDL model data.
- Contract/schema gate: published schemas are regenerated from Python model
  sources; generated JSON schemas are not edited by hand.

## Guardrails

- Do not inline raw STIX bundles, MISP events, playbooks, or analyzer reports;
  content objects are bounded manifests with typed references only.
- Do not embed principals, roles, or grants here; internal RBAC is delegated to
  `runtime.app_authorizations` via `authorization_ref`.
- Do not implement playbook/analyzer execution; the surface records inventory
  and execution *policy*, not execution semantics (boundary with CACAO/OpenC2).
- Do not make MISP, Shuffle, Cortex, TheHive, or Kibana the schema authority.
  They motivate the surface; the SDL model remains product-neutral.

## Non-Goals

- Implementing playbook execution, analyzer runs, feed ingestion, case workflow,
  or dashboard rendering behavior.
- Replacing STIX/TAXII, MISP, CACAO, OpenC2, ATT&CK, or vendor schemas.
- Redesigning `runtime.applications`, `runtime.app_authorizations`, or
  `runtime.datastore_services`.

## Consequences

### Positive

- Security-platform application facts become typed, targetable, and
  validation-backed without inlining raw bodies or corrupting adjacent surfaces.
- The required-profile guard makes a defining platform fact impossible to
  silently omit.

### Negative

- Node runtime gains another optional inventory surface.
- Consumers needing raw object bodies must retain separate evidence.

### Risks

- Over-expanding content objects toward raw bodies would recreate the original
  ambiguity under a new name; the bounded-manifest discipline prevents this.
- Treating evidence presence as proof of a platform profile would overclaim what
  the SDL can validate; the required-profile guard exists to prevent this.

## References

- [Application HTTP Surface Inventory](adr-026-application-http-surface-inventory.md)
- [App-Authorization Runtime Inventory](adr-046-app-authorization-runtime-inventory.md)
- [Datastore Service Runtime Inventory](adr-048-datastore-service-runtime-inventory.md)
- [Scenario/Delivery Boundary for Runtime Node State](adr-033-scenario-delivery-boundary-for-runtime-node-state.md)
- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md)
