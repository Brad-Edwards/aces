# Backend Conformance Guardrails

This note is the architecture preflight for `ASR-502`. It is guidance, not an
implementation plan.

`ADR-009` makes `contracts/` the authority boundary for machine-readable
contracts, fixtures, and profiles. Backend conformance implementation code must
consume that authority; it must not recreate it in a runner-local schema,
fixture, or profile model.

## Architecture Decisions

- Backend conformance is an implementation-side verifier under
  `implementations/python/packages/aces_conformance`, not a normative artifact
  family under `contracts/`.
- `contracts/fixtures/**/<contract-id>/{valid,invalid}/*.json` is the canonical
  fixture corpus. The runner may accept an override root for tests, but the
  default root is the repository `contracts/fixtures` tree.
- `contracts/profiles/backend/*.json` is the canonical backend capability
  profile corpus. Profile-to-contract requirements must be loaded from these
  artifacts instead of copied into a second in-code table.
- Published payload validation must go through `aces_contracts.contracts`
  `ContractModel` descendants, `schema_bundle()`, and the existing semantic
  diagnostics helpers.
- Backend manifests must be rendered through
  `aces_backend_protocols.manifest.backend_manifest_payload()` and validated as
  `backend-manifest-v2`; the conformance suite must not reassemble manifest
  JSON by hand.
- CLI entry points belong in the Typer-based `aces_cli` surface unless a
  compatibility wrapper is retained only as a thin delegate.
- End-to-end proof tests for backend conformance should exercise the public
  runner or CLI against a full backend profile and the published fixture corpus;
  seeded-corruption tests should mutate a temporary copy of one existing
  required fixture and expect the shared conformance diagnostics to name the
  contract and validation failure.

## Cross-Cutting Concerns

Reuse these existing surfaces before adding anything new:

- contract models and closed-world validation:
  `aces_contracts.contracts.ContractModel`, `BackendManifestV2Model`,
  runtime envelope models, plan models, and history event models
- contract publication inventory: `schema_bundle()` and
  `contracts/schema-publication-manifest.json`
- contract-corpus resolution: `aces_contracts.corpus.corpus_family_root()` with
  the `FIXTURES` and `PROFILES` family constants, so source checkouts and
  packaged installs resolve the same published corpus through one seam
- backend contract authority:
  `aces_contracts.manifest_authority.BACKEND_SUPPORTED_CONTRACT_IDS` and
  `validate_backend_supported_contract_versions()`
- controlled vocabulary and concept-binding gates:
  `aces_contracts.controlled_vocabularies`,
  `aces_contracts.apparatus`, and the `BackendManifestV2Model` validators
- manifest rendering: `aces_backend_protocols.manifest.backend_manifest_payload`
- participant capability declarations:
  `capabilities.participant_runtime.supported_participant_roles`,
  `supported_behavior_features`, and `supported_interaction_features`
- runtime behavior probes: `compile_runtime_model()`, `plan()`,
  `RuntimeControlPlane`, and `RuntimeTarget`
- diagnostics: `aces_processor.models.Diagnostic` and `Severity`
- participant-episode semantic invariants:
  `iter_participant_episode_snapshot_violations()`
- verification workflow: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and
  `tools/verify_all.py`

## Security And Runtime Gates

The conformance path touches these gates:

- JSON parsing: load only local fixture/profile files selected by explicit
  roots or canonical repo roots; do not fetch remote fixtures or execute fixture
  content.
- Corpus path resolution: default fixture/profile roots must flow through
  `aces_contracts.corpus`; tests may pass explicit temporary override roots for
  mutated corpora, but loaders must not reintroduce `Path(__file__).parents[N]`
  repo-root heuristics.
- Profile id and path validation: profile ids must pass the backend-profile id
  grammar before path construction, and any caller-supplied `profiles_root`
  resolution must remain confined to that root.
- Contract shape validation: all fixture, manifest, plan, status, result,
  history, and snapshot payloads must pass the existing Pydantic contract models
  and closed-world `extra="forbid"` behavior.
- Manifest authority validation: `supported_contract_versions`,
  `concept_bindings`, capability vocabulary terms, and backend profile claims
  must resolve through existing authority helpers, not local string checks.
- Participant capability validation: role, behavior-feature, and
  interaction-feature support claims must resolve through the governed
  vocabulary scopes on `capabilities.participant_runtime`; backend-specific
  terms must use the governed `x-<owner>:<term>` extension format.
- Participant capability evidence: standard API-405 claims must also have the
  published contract surfaces required by
  `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`; the conformance runner
  reports `conformance.unsupported-capability-claim` when a manifest claims a
  role or feature without the runtime contract evidence surface needed to check
  it.
- Control-plane probe validation: target probes must use `RuntimeControlPlane`
  and existing operation receipt/status/snapshot envelopes rather than backend
  native objects.
- Error-envelope leakage: report failures as `Diagnostic` values with stable
  codes and messages; do not surface raw tracebacks, environment variables,
  bearer tokens, credentials, or backend-private object representations.
  Proof tests should assert stable `Diagnostic.code`, `contract_name`, and
  structured addresses rather than exact Pydantic prose.
- Host/OS exposure: CLI options may accept profile names and local roots, but
  must not require secrets or bearer tokens in process argv. Live-target
  authentication belongs in headers or process-local configuration that is not
  echoed in diagnostics.
- Persistence: the suite is report-oriented and should not write durable state
  except explicit report output requested by the caller.

## Extension Boundary

The seam is the published contract id and backend profile artifact, not a Python
enum branch or hard-coded path. Adding a backend profile or contract
family should require adding the contract schema/fixtures/profile artifact and
registering the matching validator once, not editing every call site.

Keep the profile loader parameterized by `profiles_root` and the fixture runner
parameterized by `fixtures_root` so tests can use temporary corpora while the
default path remains the published `contracts/` tree.

Participant capability declarations follow the same extension boundary. API-405
adds governed vocabulary surfaces under `capabilities.participant_runtime`
instead of a backend-profile branch, snapshot metadata field, or control-plane
role. Absence of the `participant_runtime` block declares no participant runtime
surface; when the block is present, the role and feature declarations are
mandatory and set-like. The standard terms are grounded in
`docs/explain/sdl/lineage.md`, ADR-020, ADR-022, and
`specs/formal/participant-semantics/`: exercise roles map to the existing
`white`/`green`/`red`/`blue` framing vocabulary; behavior terms map to the
action, observation, state-transition, failure, temporal, attribution, and
outcome semantics already modeled in ACES; interaction terms map to the SEM-209
coordination, contention, interference, and shared-state classes. Standard terms
are not accepted as prose-only promises: target conformance checks that the
manifest also declares the published participant episode or behavior-history
contract surfaces that carry the evidence for those claims.

## Gotchas And Anti-Patterns

Avoid:

- treating semantic profiles in `contracts/profiles/semantic` as backend
  capability profiles
- keeping a duplicate `_PROFILE_REQUIREMENTS` authority table after backend
  profile artifacts exist
- accepting `backend-manifest-v1` or legacy conformance paths as current
  defaults
- changing `contracts/schemas/` without the
  `contracts/schema-publication-manifest.json` change ledger, or changing only
  reference implementation models while leaving the published schema authority
  untouched
- validating fixtures with ad hoc JSON key checks when contract models already
  exist
- adding a conformance-specific exception hierarchy, logging stack, schema
  registry, or DTO layer
- leaking backend exception strings that may include secrets into diagnostics
- making invalid fixtures multi-concern when a single-concern fixture can prove
  the same contract rule
- proving only an empty-root failure; issue `#502` needs a realistic pass over
  the canonical corpus and a seeded violation in a temporary copy of a required
  contract fixture
- mutating source fixtures in place, relying on exact validator prose, or
  broadening the test into unrelated profile, schema, or live-backend behavior

## Authority and CLI

The published backend capability profile JSONs under
`contracts/profiles/backend/` are the single source of truth for the
profile-to-contract mapping. `aces_contracts.backend_profiles.load_backend_profile`
loads them through `BackendProfileModel` — a closed-world `ContractModel`
that validates `required_contracts` against the authoritative
`BACKEND_SUPPORTED_CONTRACT_IDS` set. The conformance runner reads its
required contract sets from those profiles; no second authority table
lives in code.

The canonical CLI surface is `aces conformance backend`, registered on the
Typer `aces_cli` app next to `aces sdl` and `aces processor`. It accepts
`--profile`, `--fixtures-root`, and `--profiles-root` overrides; the
defaults point at the canonical `contracts/` tree. The runner exits
non-zero when the report has any failing case or top-level diagnostic so
the command can be wired directly into CI gates. The historic
`python -m aces_conformance.runner` entry point is preserved as a thin
delegate that forwards to the same Typer command.

## Target Conformance Reference Scenario

Target conformance drives a provisioning/snapshot probe (issue #606) that proves
the target adapter accepts a plan, reports changed addresses, and mutates a
snapshot rather than passing on manifest shape alone. With a recording driver,
this is hermetic adapter evidence, not native libvirt or guest realization.
Native and guest certification require the stronger observation gates tracked
by issues #715-#717. The probe needs a scenario to exercise and defaults to a
generic linux-vm scenario (`_DEFAULT_CONFORMANCE_SCENARIO`).

A single hard-coded scenario wrongly assumes *every* backend can realize it.
Fixed-topology emulation backends (which map ACES nodes onto a pre-built
environment) and bounded simulation backends legitimately cannot realize an
arbitrary scenario, yet still honor the provisioning contract. `run_target_conformance`
therefore accepts an optional `reference_scenario` (issue #663): a backend or
caller supplies a scenario inside its declared envelope. The probe verifies
adapter-level accounting for that scenario; it does not upgrade driver-reported
facts to daemon- or guest-observed evidence.

Issue #100 publishes configuration-bound realization envelopes using the shared
parameterized SDL semantics from #667 and the membership/subsumption relation
from #668. Manifests, provisioning plans, and snapshots carry one immutable
envelope/configuration identity. Replacing the temporary
`reference_scenario` bridge with generated positive and negative probes remains
tracked by #716; contract, adapter, native-daemon, and guest conformance remain
distinct reportable dimensions.

## Non-Goals

This preflight does not implement `ASR-502`, change requirement status, add new
fixtures, add new schemas, migrate the CLI, or repair profile drift. It only
locks the repository-wide guardrails for the implementation work that follows.
