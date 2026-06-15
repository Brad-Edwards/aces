# Scenario/Delivery Classification Drift Audit and Remediation

Issue #400 audits and repairs ACES design surfaces for residue from the earlier
scenario-vs-delivery classification error: treating a fact as outside SDL
scope because it resembles Docker, Compose, SSH, seccomp, init, network, or
process configuration vocabulary, instead of asking whether the fact exists on
a realized range node and can be invoked, observed, depended on, or affected
by a participant, evaluator, scanner, or in-range process.

This is an audit and remediation record. It fixes the live drift found in this
pass and records why the remaining narrow surfaces are principled retentions
rather than instances of the old classification rule. It does not revise ADRs,
schemas, contracts, or runtime models when the checked surface already applies
the corrected boundary.

## Boundary Used

The audit applies the rule accepted in
[ADR-033](../../decisions/adrs/adr-033-scenario-delivery-boundary-for-runtime-node-state.md):
classify by semantic locus rather than backend syntax. Runtime node state does
not become delivery-only because Docker, Compose, Podman, Kubernetes, a
harness, or an inspector exposed the evidence. Delivery mechanics remain the
orchestrator, host kernel, container runtime, backend adapter, control plane,
build executor, and host-local operator state.

The external/source basis is the existing ACES lineage set rather than a new
taxonomy:

- [Open Cyber Range SDL](https://documentation.opencyberrange.ee/docs/sdl/reference/)
  for the author-facing scenario surface.
- [CyRIS](https://www.jaist.ac.jp/~razvan/publications/cyris_facilitating_training.pdf),
  [VSDL](https://arxiv.org/abs/2001.06681), and
  [CRACK](https://www.sciencedirect.com/science/article/pii/S0167404820301103)
  for repeatable cyber-range scenario construction and validation pressure.
- [OCSF](https://ocsf.io/), [CACAO v2.0](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html),
  and [STIX 2.1](https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html)
  for portable schema, workflow, and typed-reference discipline.
- [Docker Compose services](https://docs.docker.com/reference/compose-file/services/)
  and [Docker Compose volumes](https://docs.docker.com/reference/compose-file/volumes/)
  as primary references for backend evidence vocabulary, not as SDL authority.

## Method

The audit re-read the issue body, ADR-021 through ADR-034, the SDL explanation
set, `specs/`, `contracts/`, and the implemented runtime/test surfaces under
`implementations/python/`. Searches covered exclusion language such as
`delivery`, `deployment`, `backend-specific`, `implementation layer`,
`infrastructure detail`, `runtime state`, and `participant`.

Each finding records:

- the surface and citation;
- the suspect exclusion or scope language;
- whether participant-interactable range-node state is actually involved;
- the disposition and any remediation applied in this issue.

Status vocabulary:

- `fixed-drift`: wording did risk excluding participant-interactable runtime
  node state by backend/tool resemblance and was corrected in this issue.
- `already-corrected`: the surface shows a drift pattern that has already
  been corrected by ADR-033 or a specific runtime ADR.
- `principled-retention`: narrow scope is justified by a semantic owner,
  security/redaction boundary, or source-vs-runtime distinction, not by the
  mistaken classification rule.
- `no-drift-found`: the surface was checked and did not show the rule's
  fingerprint.

## Audit Coverage

| Surface | Evidence read | Result |
| --- | --- | --- |
| ADR-021 | `docs/decisions/adrs/adr-021-falsification-first-claim-evidence-gate.md` | no-drift-found |
| ADR-022 | `docs/decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md` | no-drift-found |
| ADR-023 | `docs/decisions/adrs/adr-023-container-image-build-provenance-surface.md` | principled-retention |
| ADR-024 | `docs/decisions/adrs/adr-024-local-identity-inventory-surface.md` | already-corrected |
| ADR-025 | `docs/decisions/adrs/adr-025-container-network-realization-surface.md` | already-corrected |
| ADR-026 | `docs/decisions/adrs/adr-026-application-http-surface-inventory.md` | principled-retention |
| ADR-027 | `docs/decisions/adrs/adr-027-container-init-reaper-runtime-surface.md` | already-corrected |
| ADR-028 | `docs/decisions/adrs/adr-028-container-seccomp-security-options-surface.md` | already-corrected |
| ADR-029 | `docs/decisions/adrs/adr-029-database-logical-state-runtime-surface.md` | already-corrected |
| ADR-030 | `docs/decisions/adrs/adr-030-process-scoped-linux-capability-policy.md` | already-corrected |
| ADR-031 | `docs/decisions/adrs/adr-031-ssh-server-configuration-surface.md` | already-corrected |
| ADR-032 | `docs/decisions/adrs/adr-032-directory-domain-identity-runtime-surface.md` | already-corrected |
| ADR-033 | `docs/decisions/adrs/adr-033-scenario-delivery-boundary-for-runtime-node-state.md` | boundary-source |
| ADR-034 | `docs/decisions/adrs/adr-034-runtime-software-component-inventory.md` | principled-retention |
| lineage.md | `docs/explain/sdl/lineage.md` | no-drift-found |
| sections.md | `docs/explain/sdl/sections.md` | fixed-drift |
| validation.md | `docs/explain/sdl/validation.md` | no-drift-found |
| limitations.md | `docs/explain/sdl/limitations.md` | no-drift-found |
| runtime-architecture.md | `docs/explain/sdl/runtime-architecture.md` | no-drift-found |
| precedents.md | `docs/explain/sdl/precedents.md` | already-corrected baseline plus principled retention |
| specs/ | `specs/formal/participant-semantics/`, `specs/formal/runtime-contracts/`, `specs/formal/realization/` | no-drift-found |
| contracts/ | `contracts/README.md`, `contracts/concept-authority/`, `contracts/schemas/` | no-drift-found |
| implementations/python/packages/aces_sdl/ | runtime models, parser, validator, and tests for runtime surfaces | aligned with corrected boundary |

## Findings

### D-001 Sections runtime summary has a wording-risk residue

**Surface:** `docs/explain/sdl/sections.md`

**Citation:** The pre-fix `docs/explain/sdl/sections.md` runtime summary
started with "observed VM/runtime facts that are not authored deployable
features or exposed network services"; the same section then correctly documents
`runtime.network.published_ports`, `runtime.applications`,
`runtime.database_services`, `runtime.identity_authorities`, and SSH/runtime
state.

**Suspect exclusion or scope language:** "not ... exposed network services"
can be misread as excluding participant-interactable service exposure from
runtime state because it looks like network/deployment vocabulary.

**Boundary analysis:** The surrounding prose and implemented models apply the
correct boundary: host-published bindings are runtime/host exposure facts,
HTTP route inventories are participant-observable application state, database
listeners are database-process observations, and SSH server policy is
participant-observable daemon policy. The drift is therefore wording risk, not
schema or implementation drift.

**Disposition:** fixed-drift. `docs/explain/sdl/sections.md` now states that
`runtime` covers observed facts about realized VM/container nodes, including
participant-observable and analysis-relevant runtime state, and explicitly says
host-published bindings, application routes, daemon policy, databases, identity
authorities, and other participant-interactable state are not excluded merely
because the evidence came from Docker, Compose, a scanner, or a backend
inspector.

### A-001 Precedents deliberate omissions baseline is corrected

**Surface:** `docs/explain/sdl/precedents.md`

**Citation:** `docs/explain/sdl/precedents.md:220` states the current rule as
semantic rather than syntax-based, and the deliberate-omissions table now maps
port mappings, volume mounts, Linux capabilities, network realization, HTTP
application routes, local identity, image provenance, and directory/domain
identity to their owning surfaces or principled omissions.

**Suspect exclusion or scope language:** The historical rule was "looks like
Docker/Compose config, therefore backend implementation layer." That is the
issue #399 source rule, not the current text.

**Boundary analysis:** Current `precedents.md` no longer excludes runtime node
state merely because Docker or Compose exposed it. It distinguishes raw backend
payloads and host-local delivery mechanics from typed runtime observations and
source-artifact provenance.

**Disposition:** already-corrected. This remains the baseline reference for
the fixed boundary, not an issue #400 edit target.

### A-002 Runtime network exposure was corrected into node runtime state

**Surface:** ADR-025 and the implemented SDL runtime network surface.

**Citation:** `docs/decisions/adrs/adr-025-container-network-realization-surface.md:40`
places container network realization facts under `Node.runtime`, and
`docs/decisions/adrs/adr-025-container-network-realization-surface.md:63`
separates host publication from services and image exposed ports.
Implementation evidence appears in
`implementations/python/packages/aces_sdl/runtime_network.py` and validator
references around `implementations/python/packages/aces_sdl/validator/`.

**Suspect exclusion or scope language:** Host port bindings, aliases, endpoint
IDs, DNS names, and backend driver/IPAM details can look like Docker or
Compose deployment fields.

**Boundary analysis:** The current ADR and code classify observed endpoint and
host-publication facts as runtime/host exposure on the node, while keeping
backend-generated identifiers classified and raw inspect payloads outside the
portable SDL model.

**Disposition:** already-corrected. No additional drift found in ADR-025,
runtime model code, or tests.

### A-003 Init, seccomp, and capability posture were corrected as runtime security state

**Surface:** ADR-027, ADR-028, ADR-030, and corresponding runtime models.

**Citation:** `docs/decisions/adrs/adr-027-container-init-reaper-runtime-surface.md:42`
puts backend-injected init/PID-1 reaper facts under runtime container
configuration; `docs/decisions/adrs/adr-028-container-seccomp-security-options-surface.md:37`
puts seccomp and backend-native security options under runtime container
configuration; `docs/decisions/adrs/adr-030-process-scoped-linux-capability-policy.md:35`
keeps process-scoped Linux capability facts under
`Node.runtime.linux_capabilities`. Implementation evidence appears in
`implementations/python/packages/aces_sdl/runtime_container.py` and
`implementations/python/packages/aces_sdl/runtime_capabilities.py`.

**Suspect exclusion or scope language:** `init: true`, `security_opt`, and
`cap_add`/`cap_drop` are backend-looking configuration terms.

**Boundary analysis:** The current decisions avoid the old classification
error. They model participant-observable or security-relevant runtime facts
under typed runtime surfaces, while excluding raw Docker/Compose inspect
payloads, backend provisioning behavior, and secret-bearing argv as delivery
or evidence concerns.

**Disposition:** already-corrected. No current drift found in the ADR/code/test
alignment.

### A-004 SSH server policy was corrected as participant-observable daemon state

**Surface:** ADR-031 and the implemented SSH runtime surface.

**Citation:** `docs/decisions/adrs/adr-031-ssh-server-configuration-surface.md:31`
puts SSH server configuration under node runtime; lines around
`docs/decisions/adrs/adr-031-ssh-server-configuration-surface.md:47` identify
`AcceptEnv`, `ForceCommand`, and `Match` rules as participant-observable sshd
policy. Implementation evidence appears in
`implementations/python/packages/aces_sdl/runtime_ssh_server.py` and
`implementations/python/packages/aces_sdl/validator/`.

**Suspect exclusion or scope language:** `sshd_config`, wrapper commands, and
accepted environment names can look like backend or process implementation
details.

**Boundary analysis:** The corrected classification is explicit: transport
service bindings, account resources, environment values, process evidence, and
HTTP applications do not own SSH daemon policy. The daemon policy itself is a
node-scoped runtime configuration fact because it changes the participant's
login surface.

**Disposition:** already-corrected. No schema or text drift remains in this
surface.

### A-005 Database and identity-authority inventories were corrected as runtime logical state

**Surface:** ADR-029, ADR-032, `sections.md`, schemas, and runtime models.

**Citation:** `docs/decisions/adrs/adr-029-database-logical-state-runtime-surface.md:40`
puts database logical-state observations under `Node.runtime`; `docs/decisions/adrs/adr-032-directory-domain-identity-runtime-surface.md:63`
does the same for directory and domain identity observations. Generated schema
descriptions in `contracts/schemas/sdl/sdl-authoring-input-v1.json` and
`contracts/schemas/sdl/instantiated-scenario-v1.json` carry those surfaces,
and model evidence appears in `implementations/python/packages/aces_sdl/runtime_database.py`
and `implementations/python/packages/aces_sdl/runtime_directory_identity.py`.

**Suspect exclusion or scope language:** Database catalogs, database roles,
LDAP/AD/SCIM/OIDC/SAML/IAM authority facts, and provider identifiers can look
like product-specific backend payloads.

**Boundary analysis:** The current decisions keep vendor/provider identifiers
as data and preserve neutral stable ACES ids. They separate runtime logical
state from top-level authored accounts, `Node.services`, local identity,
application routes, raw catalog dumps, and downstream attack-graph or telemetry
schemas.

**Disposition:** already-corrected. No unremediated drift found.

### A-006 Service-manager unit state was corrected as participant-observable lifecycle state

**Surface:** ADR-035 and the implemented service-manager unit runtime surface.

**Citation:** `docs/decisions/adrs/adr-035-service-manager-unit-state-runtime-surface.md:54`
puts service-manager unit state under `Node.runtime.service_manager_units`;
lines around
`docs/decisions/adrs/adr-035-service-manager-unit-state-runtime-surface.md:62`
enumerate the participant-observable fields (manager kind, native unit name,
load/enable/active/sub state, result/exit code, main PID, unit-file path,
redactable `ExecStart`, optional same-node service ref). Implementation
evidence appears in
`implementations/python/packages/aces_sdl/runtime_service_units.py` and the
new validator hook in
`implementations/python/packages/aces_sdl/validator/`.

**Suspect exclusion or scope language:** `systemctl` output, unit-file text,
journal excerpts, and Docker/container-host configuration adjacency can look
like a backend-only delivery concern.

**Boundary analysis:** The corrected classification is explicit: failed,
disabled, static, enabled-but-not-running, and active/exited units are
participant-observable lifecycle facts that the existing `Node.services`,
`conditions`, `runtime.processes`, `runtime.container`,
`runtime.operational_policy`, `runtime.ssh_servers`, packages, software
components, content, and filesystem inventory surfaces cannot semantically
own. The surface keeps raw `systemctl`/`journalctl`/unit-file output out of
the portable schema; secret-bearing `ExecStart` values use the redacted
shape.

**Disposition:** already-corrected. No further drift remediation needed in
this surface.

### R-001 Image build provenance remains source-artifact state, not runtime node state

**Surface:** ADR-023 and `precedents.md`

**Citation:** `docs/decisions/adrs/adr-023-container-image-build-provenance-surface.md:40`
places build provenance on the source artifact boundary; lines around
`docs/decisions/adrs/adr-023-container-image-build-provenance-surface.md:51`
separate image defaults from runtime-effective state. `docs/explain/sdl/precedents.md:245`
keeps Dockerfile/build execution as delivery/packaging while keeping observable
image/source provenance on `Source.build`.

**Suspect exclusion or scope language:** Dockerfile instructions, build args,
layers, image labels, and source-to-runtime mappings are Docker/OCI-looking.

**Boundary analysis:** This is not a recurrence of the old error. The
participant-interactable runtime fact is the realized node state; build
provenance is artifact provenance. ADR-023 retains image defaults and build
inputs without converting build execution mechanics into runtime node state or
importing Dockerfile syntax as SDL authority.

**Disposition:** principled-retention. No drift remediation is needed because
the current boundary is source-artifact provenance rather than runtime node
state.

### R-002 HTTP-only application inventory is narrow but principled

**Surface:** ADR-026 and `sections.md`

**Citation:** `docs/decisions/adrs/adr-026-application-http-surface-inventory.md:40`
scopes the initial application surface to HTTP route/API/UI inventory under
node runtime; `docs/decisions/adrs/adr-026-application-http-surface-inventory.md:140`
names future variations such as virtual hosts, GraphQL, WebSocket, and
gRPC-over-HTTP; `docs/explain/sdl/sections.md:472` documents
`runtime.applications` as participant-observable HTTP application state.

**Suspect exclusion or scope language:** A narrow `runtime.applications` scope
could become drift if it excluded non-HTTP participant-interactable daemon or
application state merely because it is not a web route.

**Boundary analysis:** Current ADR-026 does not make that mistake. It confines
this specific surface to HTTP because the issue required HTTP parity and nearby
concepts already own transport, host publication, source files, content,
vulnerabilities, and participant visibility. SSH and database examples are
handled by separate runtime surfaces, which demonstrates principled separation
rather than delivery-based exclusion.

**Disposition:** principled-retention. No drift remediation is needed because
the current HTTP scope is justified by semantic ownership, while adjacent
participant-interactable daemon and database state already has separate runtime
owners.

### R-003 Compose profiles and backend execution mechanics remain delivery concerns

**Surface:** `docs/explain/sdl/precedents.md`, ADR-033, contracts, and specs.

**Citation:** `docs/explain/sdl/precedents.md:243` keeps Docker Compose
profiles in the backend implementation layer unless promoted to an ACES
scenario/profile composition surface; `docs/decisions/adrs/adr-033-scenario-delivery-boundary-for-runtime-node-state.md:77`
defines delivery machinery as orchestrators, host kernels, container runtimes,
backend adapters, control planes, build executors, and host-local operator
state. `contracts/README.md` preserves backend and participant-implementation
declaration surfaces as language-neutral contracts.

**Suspect exclusion or scope language:** Compose `profiles`, service lifecycle
selection, and backend execution plans look adjacent to scenario composition.

**Boundary analysis:** No participant-interactable range-node state is lost by
not importing Compose profile labels as SDL. The realized node set is already
represented by SDL nodes and runtime observations; backend packaging and
selection machinery remains delivery unless a future ACES composition surface
is explicitly designed.

**Disposition:** principled-retention. No current drift found.

### R-004 Runtime software component inventory keeps evidence vocabulary bounded

**Surface:** ADR-034, `sections.md`, `precedents.md`, and runtime software
models.

**Citation:** `docs/decisions/adrs/adr-034-runtime-software-component-inventory.md:24`
adds `Node.runtime.software_components` for node-scoped runtime inventory
facts, while lines around
`docs/decisions/adrs/adr-034-runtime-software-component-inventory.md:38` keep raw
CycloneDX, SPDX, package-manager, and scanner output as evidence/provenance
input rather than SDL authority. `docs/explain/sdl/sections.md:453` separates
package-manager rows from software component identity, and
`docs/explain/sdl/precedents.md:247` classifies software component identity as
runtime-observed state.

**Suspect exclusion or scope language:** Package rows, SBOM identifiers,
scanner provenance, manifest paths, and installed paths can look like backend,
scanner, or evidence-bundle vocabulary rather than scenario/runtime semantics.

**Boundary analysis:** ADR-034 keeps the corrected boundary: observed software
identity on a realized node is runtime state, but raw SBOM documents, scanner
reports, package-manager command output, and backend-native inspect payloads do
not become normative SDL schemas. The current model therefore includes the
participant- and analysis-relevant runtime fact without importing delivery or
evidence machinery.

**Disposition:** principled-retention. No current drift found in the ADR, docs,
runtime model, or tests.

### R-005 Specs and contracts preserve apparatus/runtime separation

**Surface:** `specs/`, `contracts/`, and generated schemas.

**Citation:** `specs/formal/participant-semantics/README.md:243` explicitly
warns against mistaking deployment topology for experiment semantics;
`specs/formal/runtime-contracts/README.md:20` puts participant runtime support
claims in backend apparatus capabilities rather than authored participant
assignments; `contracts/concept-authority/concept-families-v1.json` separates
scenario authoring, apparatus declarations, and evidence/provenance families.

**Suspect exclusion or scope language:** Backend capability declarations,
participant runtime support, and runtime snapshot contracts could be mistaken
for evidence that participant-interactable state belongs outside SDL.

**Boundary analysis:** The checked specs/contracts do the opposite: they keep
authored scenario meaning, backend capability support, participant runtime
evidence, and provenance distinct. That separation supports ADR-033 instead of
replicating the old Docker/Compose vocabulary error.

**Disposition:** no-drift-found.

### R-006 Lineage and general SDL explanations preserve the corrected boundary

**Surface:** `lineage.md`, `validation.md`, `limitations.md`, and
`runtime-architecture.md`.

**Citation:** `docs/explain/sdl/lineage.md:14` says ACES keeps the logical
scenario surface separate from backend realization, and
`docs/explain/sdl/lineage.md:200` separates authored scenario meaning,
processor/runtime contracts, backend realization, participant implementations,
live state, and evidence/provenance. `docs/explain/sdl/limitations.md:11`
uses ADR-033 to distinguish authored deployment intent from observed runtime
facts, and `docs/explain/sdl/runtime-architecture.md:13` lists authored
scenario meaning, processor, backend, participant implementations, live
runtime state, and archival records as separate surfaces. `docs/explain/sdl/validation.md:128`
keeps broader participant and evidence-capture concerns out of validator-only
behavior until their authored or external contract surfaces exist.

**Suspect exclusion or scope language:** General explanation documents often
use broad words such as backend, deployment, runtime, and validation; these
could hide the old mistake if they used those words to exclude
participant-interactable state.

**Boundary analysis:** The checked explanation docs do not use backend or
deployment vocabulary as the exclusion test. They consistently separate
authored intent, observed runtime facts, backend realization, participant
apparatus, validation domains, and evidence/provenance. `limitations.md`
explicitly records host-published bindings, runtime network realization,
application route state, database logical state, and identity-authority state
as observed runtime facts despite their Docker/backend-adjacent evidence
vocabulary.

**Disposition:** no-drift-found.

### R-007 Actual code matches the corrected typed-surface boundary

**Surface:** `implementations/python/packages/aces_sdl/`

**Citation:** `implementations/python/packages/aces_sdl/runtime_configuration.py`
owns `mounts`, `filesystem_inventory`, `container`, `network`,
`linux_capabilities`, `local_identity`, `identity_authorities`,
`applications`, `database_services`, `ssh_servers`, and
`software_components`;
`implementations/python/packages/aces_sdl/validator/` adds runtime
application, database, identity authority, SSH, network, and capability
cross-checks; tests in `implementations/python/tests/test_sdl_models.py`,
`test_runtime_models.py`, `test_sdl_parser.py`, `test_sdl_validator.py`, and
`test_runtime_ssh_server.py` exercise those surfaces.

**Suspect exclusion or scope language:** The implementation could have kept
the old rule by accepting raw backend dictionaries, omitting runtime node
state, or hiding participant-observable facts in `Node.services` or
`infrastructure.properties`.

**Boundary analysis:** The code does not show that pattern. It uses closed
typed models and validators for runtime node state, keeps raw backend payloads
out of the portable model, and preserves adjacent meanings through distinct
surfaces.

**Disposition:** no-drift-found.

## Summary

The audit found and fixed one live wording-risk residue in `sections.md`: a
runtime summary phrase that could be misread as excluding exposed
network-service facts, even though the surrounding document, ADRs, schemas, and
implementation applied the corrected boundary. The broader ADR, specs,
contracts, and code surfaces are aligned with ADR-033 after the recent spot
fixes, including ADR-034's runtime software identity surface. The remaining
narrow surfaces, such as HTTP applications, image provenance, runtime software
identity, and Compose profile omission, justify scope by semantic owner,
provenance, and participant interactability rather than by backend vocabulary
resemblance.
