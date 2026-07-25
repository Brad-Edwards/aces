# Issue 258 ASR-511 Layered Validation Profiles Preflight

Date: 2026-07-24

Issue: #258. This is a requirement-free Ground Control run; the issue and the
ASR-511 statement quoted there are the delivery contract.

This note fixes the executable taxonomy boundary before implementation. It does
not implement a contract, profile, loader, validator, fixture, API, admission
decision, or disclosure. No new ADR is needed: ADR-072 and
`specs/formal/validation-admission-profiles/` already own the design.

## Decision Boundary

Issue #258 owns one static, governed validation-profile taxonomy. It defines:

- the ordered `structural`, `semantic`, `behavioral`, `evidence_backed`, and
  `falsification_backed` strength terms from ADR-072;
- portable subject kinds, gate kinds, and limitation categories;
- versioned profile definitions with intended subject kinds, minimum strength,
  required and optional gates, evidence/diagnostic expectations, limitations,
  and extension rules; and
- lookup and validation of those checked-in definitions.

Use one closed catalog contract under the existing `contracts/profiles/`
authority and one cached loader through `aces_contracts.corpus`. The catalog is
the single authority for the validation-profile term set and profile
definitions. Do not repeat the same lists in
`controlled-vocabularies-v1.json`, Python enums, conformance code, backend
manifests, or carrier schemas. Python types and generated schemas implement the
catalog contract; the checked-in published schema and profile artifact remain
normative under ADR-009.

The catalog must keep vocabulary definitions separate from profile
definitions. Profiles reference declared terms; they do not redefine strength,
gate, subject, or limitation meaning inline. Required and optional gate sets
must be disjoint, ids and `(profile_id, profile_version)` identities must be
unique, references must resolve exactly, and extension terms must use the
ADR-012 `x-<owner>:<term>` discipline. File order, dictionary order, a Python
enum ordinal, or profile naming must not create an unstated strength relation.

Strength is an ordered disclosure class, not a proof lattice or a substitute
for gate membership. In particular, `evidence_backed` may build on a semantic
or behavioral basis, so its higher disclosure rank must not imply that a
behavioral gate ran. A profile must name the gates it actually requires.

Issue #259 owns profile use: gate-result statuses, achieved strength,
per-subject basis records, weak/not-run/withheld outcomes, evidence and
diagnostic references, public versus internal views, and bindings to scenario,
task, run, study, conformance, or claim carriers. #258 must leave a stable
`(profile_id, profile_version)` lookup seam for that work, but must not add
disclosures or carrier fields early.

## Canonical Incumbents

| Concern | Canonical incumbent and boundary |
| --- | --- |
| Normative design | ADR-072, the formal validation/admission-profile specification, and the joint #97 preflight. Do not mint a competing taxonomy or reinterpret the strength order. |
| Contract shape | `ContractModel(extra="forbid")`, the primitive aliases and validators in `aces_contracts.contracts`, and the catalog pattern used by `ScientificCompletenessTaxonomyModel`. Reuse the closed catalog idiom, not that domain's concepts or delivery statuses. |
| Profile authority and loading | `contracts/profiles/`, `aces_contracts.corpus.PROFILES`, `corpus_family_root()`, `importlib.resources`, and the wheel/sdist corpus inclusion in `implementations/python/hatch_build.py` and `pyproject.toml`. Do not reconstruct repository-relative paths or add an environment-selected profile root. |
| Schema publication | `schema_bundle()`, `aces_contracts.versions`, `contracts/schemas/`, the per-contract entries under `contracts/schema-publication/entries/`, `generate_contract_schemas.py`, generated-schema parity, publication checks, and JSON artifact checks. The checked-in schema is authority; generator output alone is not. |
| Fixtures and conformance | `contracts/fixtures/`, `aces_conformance.conformance.validators`, `_validate_payload()`, `_STRUCTURAL_ONLY_VALIDATORS`, `_fixture_case_diagnostics()`, `Diagnostic`, and `Severity`. Taxonomy conformance validates its closed shape and cross-references; it does not execute a profile's gates. |
| Adjacent profile families | `SemanticProfileModel`/`load_semantic_profile()`, `BackendProfileModel`/`load_backend_profile()`, random-stream profiles, scientific-completeness profiles, and `InstantiationRequestModel.profile`. These remain distinct authorities and are not aliases for a validation profile. |
| Admission and claims | `ParticipantActionAdmissionRequest`, participant `admission_disposition`, `RuntimeControlPlane.admit_participant_action()`, `BehavioralClaimBindingModel`, ADR-021 evidence status, and the assurance policy's FM levels. None is a validation-profile definition or strength value. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, `tools/verify_all.py`, repository policy, requirement governance with `ACES_REQUIREMENT_UID=ASR-511`, module-boundary checks, Sphinx, gitleaks, and private-key detection. Extend the existing verification graph once; do not add a parallel workflow. |

There is no controller, service, repository, mutable store, or runtime
configuration object in this design. The owning implementation belongs in
`implementations/python/packages/aces_contracts`; the compatibility-only
`implementations/python/src/aces/` tree must not gain logic.

## Cross-Cutting And Security Gates

1. **Authority and shape.** The checked-in profile catalog passes a closed
   `ContractModel` and a published JSON Schema. Reject unknown fields, duplicate
   identities, dangling term references, empty required sets, required/optional
   overlap, invalid strength references, and invalid extension ids. Cross-row
   rules that JSON Schema cannot express use the existing `x-aces-invariants`
   mechanism rather than prose-only validation or a second schema.
2. **Profile selection and path safety.** Load the canonical catalog through
   `corpus_family_root(PROFILES)` and select a validated
   `(profile_id, profile_version)` from it. Do not turn either value into a
   caller-controlled path, accept absolute/parent traversal, scan arbitrary
   directories, fetch URLs, dynamically import a validator named by profile
   data, or allow a caller-supplied profile root. Unknown profiles and versions
   fail closed.
3. **Configuration and environment.** The taxonomy is packaged, immutable
   contract data, not an environment binding. It adds no secret, token, host,
   backend, executable, plugin, or environment-variable field. Installed and
   editable layouts continue to use the existing corpus resolver; there is no
   fallback to the current working directory or an empty catalog.
4. **Authentication and authorization.** #258 is an offline contract/loader
   surface and adds no HTTP, CLI, MCP, or control-plane endpoint. A later remote
   exposure must reuse `ControlPlaneSecurityConfig.strict_defaults()`, verified
   identity, role/target authorization, request-size limits, idempotency and
   request fingerprints, audit events, response models, and the redacted
   internal-error handler. Profile selection must not create an auth bypass or
   imply permission to run the named gates.
5. **Secrets and publication.** Profile artifacts, fixtures, descriptions,
   diagnostics, and examples contain only public ids, bounded prose, and
   contract references. They must not contain credentials, hidden answers,
   prompts, environment dumps, backend-native ids or objects, raw evidence,
   tracebacks, or executable snippets. Existing repository secret and
   private-key gates remain mandatory.
6. **Errors and diagnostics.** Contract construction uses existing Pydantic
   `ValidationError`/`ValueError` behavior; conformance projection uses the
   existing bounded `Diagnostic`/`Severity` shape. Do not add an exception
   hierarchy. Diagnostics identify catalog/profile/term ids and contract paths,
   not rejected payload bodies. The current conformance helper renders
   `str(exc)` and is safe only for repository-owned public fixtures here; it
   must not be reused as a public untrusted-input error envelope without
   sanitization.
7. **OS and process exposure.** No subprocess, shell, daemon, network call, or
   privileged operation is needed. If a later tool accepts profile selection,
   argv may contain only bounded profile ids/versions and paths, never tokens,
   raw scenario/evidence bodies, claim text, or profile JSON.
8. **Persistence, logging, and observability.** The durable source is the
   Git-tracked normative catalog and schema. Loader caching is process-local
   optimization only. Do not copy taxonomy state into `RuntimeSnapshot`,
   `ControlPlaneStore`, operation details, audit blobs, experiment archives,
   backend DTOs, logs, telemetry, tags, or free-form metadata. Loading and
   validation do not emit a runtime event or admission receipt.

## Extensibility Seam

The seam is catalog lookup by `(profile_id, profile_version)` plus declared
subject kind. A new profile using existing terms should be a governed data
addition, not a new Python enum member, loader branch, backend table, schema
registry, or carrier field. A new portable strength, subject, gate, or
limitation term changes the one catalog authority and its contract/version;
implementation-specific terms use the governed extension namespace.

Profile definitions may describe expected evidence and diagnostics with ids and
contract references, but they must not carry Python callables, module names,
shell commands, URLs to execute, or backend-specific dispatch rules. Execution
remains with the existing parser, semantic validator, processor, conformance,
runtime, admission, evidence, and falsification owners. #259 can therefore join
a disclosure to one profile definition without making the taxonomy an
orchestrator.

## Gotchas And Anti-Patterns

Avoid:

- calling schema/Pydantic acceptance `semantic` or a passing catalog
  `behavioral`;
- treating FM0-FM3, ADR-021 evidence statuses, gate-result statuses, backend
  capability levels, realization support, or admission dispositions as
  validation strengths;
- using a generic `profile` field where `validation_profile_id` and version are
  required for family identity;
- equating a higher strength rank with every lower-domain gate having run;
- defining the same term set in both a validation-profile catalog and
  `controlled-vocabularies-v1.json`, Python enums, manifests, or conformance
  registries;
- one JSON file and loader per strength, or hard-coded profile-to-gate tables in
  processor/backend/runtime code;
- arbitrary dictionaries such as `validation_metadata`, `admission_metadata`,
  `gate_config`, or `limitations`;
- executable gate plugins, dynamic imports, remote registries, environment
  overrides, filesystem discovery, or silent fallback to a default profile;
- creating disclosure models, gate outcomes, scenario/task/run/study fields,
  evidence storage, runtime decisions, or public API behavior in #258; and
- editing compatibility wrappers, runtime snapshots, operation envelopes,
  participant admission history, or experiment carriers to make the taxonomy
  appear integrated.

## Non-Goals

- Implementing ASR-515 or issue #259 validation-basis disclosures.
- Running structural, semantic, behavioral, evidence, or falsification gates.
- Changing SDL parsing, semantic validation, instantiation, compilation,
  planning, backend conformance, participant action admission, or runtime
  authorization.
- Redesigning semantic profiles, backend profiles, instantiation profiles,
  scientific-completeness profiles, random-stream profiles, ADR-021 claim
  evidence, or FM assurance classification.
- Adding an API, CLI, MCP tool, database, evidence store, audit stream,
  telemetry event, plugin system, remote registry, or mutable profile service.
