# ADR-049: Platform Application Runtime Inventory

## Status

accepted

## Date

2026-05-30

## Context

SCN-010 (DSL-133) identified an SDL expressivity gap while modeling MISP,
Shuffle, Cortex, TheHive, and an analytics dashboard. The original response
introduced a single `platform_kind` discriminator and made each category imply
a required product-shaped configuration/content profile. In particular, a
`threat_intel` application was invalid unless it declared MISP-shaped
taxonomies, galaxy clusters, warning lists, feeds, and sharing groups.

Issue #956 exposed the immediate symptom: a default MISP deployment does not
have every required object. The deeper defect is independent of that default.
An application category or product identity does not prove configured state,
and the MISP profile does not define other threat-intelligence platforms.
Applications such as OpenCTI also expose several roles at once—intelligence
management and exchange, cases, analysis, workflow automation, and
presentation—so a single product-category discriminator is not a sound type
spine.

The resulting semantic failure has three parts:

- classification, functional capability, configured state, content, transport,
  and distribution policy were conflated;
- the validation guard checked only the presence of broad object kinds, so
  dummy manifests could satisfy supposed completeness without proving useful
  configuration;
- product-specific concepts bled into the SDL core even though adjacent
  applications and standards divide responsibility differently.

Existing SDL precedent points to a provider-neutral correction. ADR-032 turns
an Active Directory scenario into a neutral identity-authority surface rather
than an AD schema clone. ADR-088 and `specs/sdl/initial-service-state.md` place
authored initial data under top-level `content` and service materialization.
The runtime contract boundary in the issue #417 preflight distinguishes
declared runtime contract state from observations and evidence. Scientific
scenario completeness is explicitly stronger than ordinary SDL validity.

Adjacent systems reinforce that separation without becoming schema authority:
TOSCA and CAMP distinguish capabilities, requirements, artifacts, and
configuration; STIX and TAXII distinguish intelligence content from exchange;
CACAO distinguishes playbooks, commands, agents, and targets. No source makes a
product category prove the presence of a particular corpus or policy.

## Decision

### 1. Retain one application inventory and make capability composable

`Node.runtime.platform_applications` remains the node-scoped inventory for a
participant-visible application. Each `RuntimePlatformApplication` has a stable
`platform_application_id`, optional same-node `service` ref, product metadata,
and zero or more provider-neutral `capabilities`.

Each capability has:

- a stable `capability_id`;
- an OPEN `kind`;
- optional `evidence_refs`; and
- a description.

The initial capability kinds are:

- `threat_intelligence_management`: curate, relate, and analyze intelligence;
- `intelligence_exchange`: ingest, publish, or synchronize intelligence across
  an application boundary;
- `case_management`: manage investigation or incident case lifecycle;
- `analysis_execution`: invoke analysis, enrichment, or response jobs;
- `workflow_automation`: coordinate workflows or playbooks; and
- `analytics_presentation`: expose saved queries, visualizations, or dashboards.

`unknown` and `other` keep the taxonomy open. A `${var}` placeholder remains
valid until instantiation. One application may declare several capabilities.
The capability declares a functional role only; it does not assert a product,
configuration profile, content inventory, policy, transport binding, successful
execution, or scientific completeness.

### 2. Remove product-category completeness validation

Remove `require_profile_for_platform_kind` and every product-category profile
dispatch. `platform_kind` no longer determines validity, requires content, or
implies a capability. A platform application may be valid with no declared
capabilities because ordinary SDL validation must not invent a completeness
claim.

Completeness belongs at the requirement or use site. A future contract may, for
example, require a referenced application to expose
`intelligence_exchange`; that requirement must resolve an explicit capability
instead of deriving one from `product` or `platform_kind`.

Capabilities are not inferred from the legacy category. Inference would retain
the original conflation, create false multi-role claims, and make migration
dependent on product assumptions.

### 3. Keep configuration, content, policy, and evidence with their owners

Application capabilities and application state are orthogonal. New SDL design
must route facts according to meaning:

| Fact | Owning semantic surface |
|---|---|
| Product/version/name | Platform-application identity metadata |
| Functional role | `platform_applications[].capabilities` |
| Initial files, datasets, messages, records, or comparable data | Top-level `content`, with `service_materialization` for named-service state |
| Feed or peer synchronization | Connector, binding, or relationship semantics |
| Sharing/distribution policy | Authorization or distribution-policy semantics |
| Workflow/playbook definition | Workflow or content artifact semantics |
| Analyzer/responder implementation | Analysis capability plus its artifact/interface contract |
| Dashboard/search/visualization definition | Presentation content/artifact semantics |
| Proof of a declared capability | Capability `evidence_refs` and the existing evidence plane |

Not every destination in this table is fully generalized today. That is not
authority to place a vendor concept in the capability model. Until the correct
owner exists, existing bounded manifests may be retained as legacy input or the
fact may remain external evidence.

Raw STIX bundles, MISP events, playbooks, analyzer reports, dashboard exports,
credentials, and backend payloads remain outside this model.

### 4. Preserve compatible input while making the new authority clear

`platform_kind` and `content_objects` remain accepted in the current schema so
existing SDL documents do not break. Both are marked deprecated compatibility
fields:

- `platform_kind` remains an OPEN legacy classification and proves nothing
  about capabilities or configured state;
- `content_objects` remain bounded parsed manifests with typed references and
  never raw bodies, but their presence proves no capability.

The existing organizations, tenants, markings, upstream bindings, connectors,
execution policy, settings, service ref, and authorization ref remain intact.
No enum member is removed or silently remapped. Previously valid documents stay
valid; documents formerly rejected only by a product profile become valid.

A future breaking SDL revision may remove the legacy fields after correct
owners and migration tooling exist. That removal is outside #956.

### 5. Keep capabilities targetable

`capability_id` joins the application's local stable-id namespace and cannot
collide with the application id or another child id. Capabilities participate
in the existing qualified runtime reference tree:

- `nodes.<node>.runtime.platform_applications.<platform_application_id>`
- `...platform_applications.<id>.capabilities.<capability_id>`
- `...platform_applications.<id>.content_objects.<content_object_id>`
- `...platform_applications.<id>.markings.<marking_id>`
- `...platform_applications.<id>.upstream_bindings.<binding_id>`
- `...platform_applications.<id>.connectors.<connector_id>`

These refs identify declared inventory targets. They do not imply configuration,
playbook execution, analyzer runs, feed ingestion, policy enforcement, or
dashboard rendering.

## Security and Validation Gates

- Parser/model gate: stable application and child ids are concrete symbols. Enum
  fields are normalized through the single runtime enum-parse helper. Duplicate
  application ids and duplicate application-local child ids fail early.
- Capability gate: capability ids share the application-local namespace;
  capability kinds use the OPEN runtime enum contract; duplicate evidence refs
  fail locally.
- Semantic validation gate: the owning `service` ref resolves to a same-node
  binding; a non-empty, non-variable `authorization_ref` resolves to a same-node
  `app_authorization`; legacy content-object `references` resolve to sibling
  `content_object_id` values and `marking_refs` to sibling `marking_id` values.
- Relationship/reference gate: application and child qualified refs resolve in
  generic relationships and survive module import namespacing.
- Secret/payload gate: raw object bodies, credentials, and secret-bearing
  setting/connector values stay out of SDL model data.
- Contract/schema gate: schemas expose capabilities and legacy deprecation
  metadata while continuing to accept existing documents.

## Guardrails

- Do not infer a capability or required configuration from product,
  `platform_kind`, organization count, or legacy content presence.
- Do not make capability kinds aliases for products or vendor features.
- Do not inline raw STIX bundles, MISP events, playbooks, or analyzer reports.
- Do not embed principals, roles, or grants here; internal RBAC is delegated to
  `runtime.app_authorizations` via `authorization_ref`.
- Do not implement playbook/analyzer execution; capabilities record functional
  roles, not execution semantics (boundary with CACAO/OpenC2).
- Do not make MISP, Shuffle, Cortex, TheHive, OpenCTI, or Kibana the schema
  authority. Products are evidence and examples, not SDL types.

## Non-Goals

- Implementing playbook execution, analyzer runs, feed ingestion, case workflow,
  or dashboard rendering behavior.
- Replacing STIX/TAXII, MISP, CACAO, OpenC2, ATT&CK, or vendor schemas.
- Generalizing every legacy content/configuration concept in this issue.
- Redesigning `runtime.applications`, `runtime.app_authorizations`, or
  `runtime.datastore_services`.

## Consequences

### Positive

- Multi-role applications are representable without pretending to be several
  products.
- Capability, configuration, content, binding, policy, and evidence no longer
  collapse into a product category.
- Existing SDL documents remain readable while new documents have a
  provider-neutral authority.

### Negative

- Node runtime gains another optional inventory collection.
- Legacy product-shaped fields remain in the schema until a breaking revision,
  so consumers must understand the deprecation boundary.
- SDL validity alone does not prove application completeness; consumers needing
  that guarantee must use an explicit requirement/profile contract.

### Risks

- Capability kinds could accrete vendor features and recreate `platform_kind`;
  additions must describe portable functional roles.
- Consumers could continue treating legacy fields as authoritative. Deprecation
  metadata, documentation, and tests make the compatibility-only status clear.
- A capability assertion could be mistaken for operational proof. Optional
  evidence supports the claim, but execution and scientific completeness remain
  separate contracts.

## References

- [Application HTTP Surface Inventory](adr-026-application-http-surface-inventory.md)
- [Directory and Domain Identity Runtime Surface](adr-032-directory-domain-identity-runtime-surface.md)
- [App-Authorization Runtime Inventory](adr-046-app-authorization-runtime-inventory.md)
- [Datastore Service Runtime Inventory](adr-048-datastore-service-runtime-inventory.md)
- [Scenario/Delivery Boundary for Runtime Node State](adr-033-scenario-delivery-boundary-for-runtime-node-state.md)
- [Initial Service State and Native Materialization](adr-088-initial-service-state-and-native-materialization.md)
- [Scientific Scenario Completeness](../../../specs/sdl/scientific-scenario-completeness.md)
- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md)

## Amendments

| Date | Commit/PR | Summary |
|------|-----------|---------|
| 2026-07-29 | #956 | Replaced product-category completeness profiles with composable provider-neutral capabilities; retained `platform_kind` and `content_objects` as deprecated compatible input and separated capability from configuration, content, binding, policy, and evidence ownership. |
