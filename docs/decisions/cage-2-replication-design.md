# CAGE-2 Replication Design

Date: 2026-07-01

Issue: #635.

Requirement: REP-001.

Status: accepted by ADR-069.

## Purpose

This design record turns ADR-069 into an implementation checklist for the
CAGE-2 replication program. It does not author the CAGE-2 ACES SDL scenario,
create `aces-adapters`, implement a CybORG backend, add `sim_adapter_base`,
publish fixtures, or claim equivalence. It defines what those downstream
artifacts must prove.

## Source Pins and Evidence

Downstream mapping work must pin immutable upstream source identifiers and
record file paths and digests for every consumed source fact. During REP-001,
the following floating heads were inspected only to shape the design:

| Source | Observed commit | Source paths to ledger |
|---|---|---|
| `https://github.com/cage-challenge/cage-challenge-2` | `26ce1c1253fa9e2e73f25e6a7f2da32860c11257` | `README.md`; `CybORG/CybORG/Shared/Scenarios/Scenario2.yaml`; `CybORG/CybORG/Evaluation/evaluation.py`; `CybORG/CybORG/Shared/*RewardCalculator.py`; wrappers; simple agents; action implementations |
| `https://github.com/cage-challenge/CybORG` | `2742b5e0ce4330c9b14006b38acd3b5ebe00d6fd` | `CybORG/Simulator/Scenarios/scenario_files/Scenario2.yaml`; `CybORG/Evaluation/evaluation.py`; wrappers; reward calculators; `CybORG/Simulator/Actions/**`; test scenario fixtures |
| `https://arxiv.org/abs/2309.07388` | arXiv paper version available during REP-001 | Challenge narrative, red-agent variants, action/reward/evaluation semantics, evaluation protocol context |

The downstream ledger may choose a different upstream commit or release. It
must state the exact identifier it uses and why.

## CAGE-2 to ACES Mapping Ledger

The mapping ledger is the primary bridge from upstream CAGE facts to ACES
portable artifacts. Each row has this shape:

| Field | Meaning |
|---|---|
| `source_id` | Stable row id, unique within the ledger |
| `source_repo` | Upstream repository or paper URL |
| `source_version` | Commit, release, tag, or paper version |
| `source_path` | File path, section, figure, or table |
| `source_selector` | YAML path, Python symbol, line range, or prose selector |
| `source_digest` | Optional content digest when practical |
| `cage_fact_type` | Host, subnet, service, account, role, action, observation, reward, terminal condition, turn order, red-agent policy, seed, or evaluation fact |
| `aces_target` | ACES artifact, contract, field, concept binding, or evidence record that carries the fact |
| `mapping_rule` | Transformation from source fact to ACES value |
| `loss_disclosure` | Required when ACES cannot carry the exact source fact |
| `verification` | Structural check, conformance probe, evidence ref, or manual review note |

The ledger must cover at least the following source categories.

### Topology and Assets

- subnets and subnet roles;
- hosts, servers, operational hosts, defender host, and user hosts;
- operating-system families and versions where available;
- services, ports, decoy-compatible services, and vulnerable services;
- accounts, sessions, credentials, privilege levels, and initial foothold;
- network access controls and reachability.

ACES targets include SDL infrastructure, nodes, services, accounts,
authorization surfaces, runtime inventory families, concept bindings, and
evidence requirements. Source facts that cannot be encoded must be disclosed
rather than stored in `metadata` as hidden semantics.

### Participants and Identities

The design keeps these identities separate:

- backend identity: the CybORG simulator backend target;
- evaluator identity: the component projecting reward and score into ACES;
- blue participant implementation identity;
- red policy identity, including B-line, Meander, and Sleep variants;
- green/user behavior identity;
- control-plane caller identity.

Participant identities map to participant implementation manifests,
participant runtime episode records, behavior histories, provenance, and
experiment apparatus context. Backend or evaluator identity must not stand in
for participant implementation identity.

### Actions, Observations, and Hidden Truth

CAGE actions are source facts, not ACES semantics. The ledger maps them into
compiled ACES action contracts, action-admission requests, observed effects,
participant-visible observations, hidden truth disclosures, evidence records,
and derived measures.

Blue actions such as monitor, analyse, restore, remove, and decoys must declare
their ACES action category, target grammar, observation boundary, admissibility
rule, and effect reporting. Red actions such as discovery, service discovery,
exploitation, privilege escalation, and impact must declare whether they are
participant behavior, backend state transition, evaluator fact, or hidden
truth. Green/user behavior maps to participant or background-workload
semantics with disclosed limits.

Native action ids, gym spaces, simulator observations, reward arrays, and
object reprs must not appear as portable ACES payloads.

### Timing, Turn Order, and Stochastic Controls

The ledger must state:

- trial lengths and logical step counts;
- ordering among red, blue, green, backend, and evaluator operations;
- episode start and terminal conditions;
- red-agent variant selection;
- random seeds and stochastic policy, including any uncontrolled source of
  randomness;
- simulator package and scenario source version.

These facts map to experiment task/run/study parameters, apparatus context,
condition assignments, run allocation, stochastic controls, and realized-form
disclosures.

### Reward, Objectives, and Evaluation

CAGE reward and score facts map to ACES objectives, evaluator results,
evidence records, derived measures, and study analysis plans. The design keeps
these concepts distinct:

- participant-local outcome;
- workflow success;
- backend conformance;
- reward component;
- cumulative score;
- objective satisfaction;
- derived measure;
- replication/equivalence claim.

A high CAGE score is evidence for an analysis claim. It is not by itself
semantic equivalence, conformance, or scenario correctness.

## CybORG Backend Protocol Mapping

The CybORG adapter is a target registered through the ACES backend registry.
It provides a `BackendManifest`, components, and protocol implementations that
consume neutral DTOs from `aces_contracts`.

### Provisioner

The provisioner owns target construction and source validation:

- validates selected CAGE source pins and mapping-ledger refs;
- validates simulator package/version and target config;
- constructs the simulator driver leaf;
- publishes capability declarations and realization-support disclosures;
- returns `Diagnostic`, `ProvisioningPlan`, `ApplyResult`, and operation
  receipts through ACES contracts.

It does not return native simulator state or mutate SDL.

### Orchestrator

The orchestrator owns step execution against compiled ACES plans:

- translates compiled action contracts into driver calls;
- applies turn-order and clock policy;
- records runtime snapshots and shared-state transitions;
- rejects invalid native outputs before they cross the adapter boundary;
- reports all failures as ACES diagnostics.

The orchestrator must not bypass `RuntimeTarget`,
`_validate_runtime_target_shape()`, `_call_backend_apply()`, or runtime
snapshot validation.

### Evaluator

The evaluator projects CAGE reward and terminal facts into ACES evaluation
records:

- maps reward components and score;
- records terminal conditions;
- creates evidence records and derived measures;
- discloses unsupported or lossy mappings;
- binds metrics to experiment study analysis plans.

It must not treat reward arrays as participant-local outcomes or workflow
success without an explicit mapping.

### ParticipantRuntime

The participant runtime mediates blue/red/green episodes:

- initializes, resets, and terminates episodes through the participant
  lifecycle;
- admits actions through `ParticipantActionAdmissionRequest`;
- emits observation envelopes and participant histories;
- records implementation provenance and exposure policy;
- keeps red policy, blue implementation, green behavior, backend, evaluator,
  and caller identities separate.

## `sim_adapter_base`

The future `sim_adapter_base` package may include:

- simulator target factory helpers;
- clock/step and seed controls;
- source-pin and source-ledger utilities;
- action translator base classes;
- observation projector base classes;
- reward/evaluator projector base classes;
- redaction helpers for diagnostics and evidence;
- conformance probe helpers that wrap ACES conformance APIs.

It must not include:

- SDL syntax, schema, profile, fixture, or concept-authority definitions;
- backend protocol definitions;
- capability evidence rules;
- conformance profile authority;
- exception or diagnostic envelope authority;
- persistent stores or audit logs used as portable truth.

## `aces-adapters` Monorepo Layout

The future repository should use this shape:

```text
aces-adapters/
  README.md
  pyproject.toml                 # workspace/tooling only, not one lock for all adapters
  packages/
    sim_adapter_base/
      pyproject.toml
      uv.lock
      src/sim_adapter_base/
      tests/
    cyborg_adapter/
      pyproject.toml
      uv.lock
      src/aces_adapter_cyborg/
      tests/
      mapping/
        cage2-source-ledger.jsonl
        cage2-loss-disclosures.md
      profiles/
        conformance-overrides/
    <future-adapter>/
      pyproject.toml
      uv.lock
      src/
      tests/
  .github/workflows/
    ci.yml
```

The root workflow fans out by matrix:

- adapter project path;
- adapter lockfile;
- Python version;
- optional simulator extras;
- conformance profile id;
- seed suite;
- source-ledger id.

An adapter may depend on `sim_adapter_base` by version or workspace reference,
but it does not share one global simulator dependency resolution with other
adapters.

## Backend Conformance Harness

The adapter harness composes existing ACES conformance:

1. Load the adapter manifest via `backend_manifest_payload()`.
2. Validate as `backend-manifest-v2`.
3. Select a published backend profile from `contracts/profiles/backend/**`.
4. Load canonical fixtures from `contracts/fixtures/**`.
5. Run `run_target_conformance()` against a fully constructed `RuntimeTarget`.
6. Run simulator-specific probes for source-ledger coverage, seed controls,
   action/observation projection, and reward/evaluator projection.
7. Emit structured `Diagnostic` values, evidence records, and derived measures.

Simulator probes are additive. They must not become a second profile table,
fixture corpus, schema registry, or manifest renderer.

## Replication and Equivalence Criteria

Replication success requires all tiers below. A tier can fail, pass, or pass
with disclosed weakness.

| Tier | Required evidence |
|---|---|
| Authored source | One ACES SDL scenario; no backend-specific SDL branches; complete pinned mapping ledger |
| Contract | Valid backend manifests; supported contracts declared; applicable backend conformance profile passes |
| Execution control | Same trial length, red-agent variant, seed/stochastic-control declaration, turn order, terminal rule, participant selection |
| State and observation | Topology, services, privileges, visibility, observations, action admissibility, and shared-state transitions satisfy declared ACES semantics |
| Outcome and evaluation | Reward components, objective results, evidence records, derived measures, cumulative score, margins, and confidence criteria satisfy the study plan |
| Disclosure | Every unsupported fact has a loss disclosure and weakens or fails the claim explicitly |

No claim may be based only on CI success, notebook output, native simulator log
similarity, or a single cumulative score.

## Cross-Repo Workflow

ACES remains the authority repository for requirements, decisions, and
portable contracts.

The workflow is:

1. ACES issue #635 and `REP-001` own this architecture.
2. Downstream `aces-adapters` issues reference issue #635, `REP-001`, ADR-069,
   and this design record.
3. Adapter PRs include the mapped ACES requirement UID, the source-ledger id,
   source pins, conformance profile id, seed suite, and evidence outputs.
4. ACES follow-on issues read downstream evidence before advancing
   requirement status or replication claims.
5. Cross-repo status is inferred only from linked issues, PRs, conformance
   reports, evidence artifacts, and requirement traceability.

Informal comments, branch names, and docs-only status tables are not
implementation evidence.

## Non-Goals

- Authoring the CAGE-2 ACES SDL scenario.
- Creating `aces-adapters`.
- Implementing `sim_adapter_base`.
- Implementing a CybORG backend.
- Adding ACES schemas, profiles, fixtures, concept vocabularies, or policy
  gates.
- Running CAGE-2 through a backend.
- Claiming replication/equivalence.
- Designing an emulation backend.

## Clause Checklist

| REP-001 clause | Design location |
|---|---|
| Accepted ADR | `docs/decisions/adrs/adr-069-cage-2-replication-architecture.md` |
| CAGE-2 to ACES SDL mapping | `CAGE-2 to ACES Mapping Ledger` |
| CybORG adapter against four protocols | `CybORG Backend Protocol Mapping` |
| Shared `sim_adapter_base` package | `` `sim_adapter_base` `` |
| Backend conformance harness | `Backend Conformance Harness` |
| `aces-adapters` independent monorepo layout | `` `aces-adapters` Monorepo Layout `` |
| Replication/equivalence success criteria | `Replication and Equivalence Criteria` |
| Cross-repo issue-driven workflow | `Cross-Repo Workflow` |
| Emulation out of scope | `Non-Goals` |
