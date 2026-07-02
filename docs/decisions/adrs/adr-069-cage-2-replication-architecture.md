# ADR-069: CAGE-2 Replication Architecture

## Status

accepted

## Date

2026-07-01

## Classification

Classification: FM2
Required artifacts: ADR, design record, preflight guardrails, changelog
fragment
Waivers: No schema, fixture, profile, contract-source, implementation, or
runtime artifact is introduced by this issue. REP-001 is a design decision for
an adapter-driven replication program; downstream issues must author the SDL
scenario, create the adapter repository, implement the CybORG backend, add
conformance probes, and publish evidence artifacts.

## Context

REP-001 asks ACES to define how the TTCP CAGE Challenge 2 scenario is driven
through ACES into a conformant simulator backend. The design must cover the
CAGE-2 to ACES SDL mapping, a CybORG simulator adapter against the ACES backend
protocols, a shared simulator adapter base, the future `aces-adapters`
monorepo, replication/equivalence criteria, and the cross-repo workflow. It
explicitly excludes realizing CAGE-2 on an emulation backend.

ACES already has most of the load-bearing architecture:

- ADR-001, ADR-002, ADR-004, ADR-008, ADR-020, ADR-022, ADR-054, ADR-060,
  ADR-066, and ADR-067 define SDL, runtime, participant, observation, and
  outcome semantics.
- ADR-009, ADR-012, ADR-019, ADR-061, and ADR-062 define normative artifact
  authority, schema publication, concept authority, controlled vocabularies,
  and governed extension discipline.
- ADR-036 keeps processor, runtime, contract, and backend protocol packages
  separated.
- ADR-063 defines the reference emulation backend as one concrete backend
  pattern, not as a superclass for simulators.
- ADR-064, ADR-065, ADR-066, and ADR-068 define experiment evidence, run
  provenance, plane separation, replication, and replay-claim boundaries.

The missing decision is how to make CAGE-2 a portable ACES replication target
without creating CAGE-specific SDL syntax, a second backend protocol family, a
parallel conformance harness, or an informal cross-repo status process.

The upstream sources that downstream mapping work must pin include:

- `https://github.com/cage-challenge/cage-challenge-2`, observed at
  `26ce1c1253fa9e2e73f25e6a7f2da32860c11257` during this design, especially
  `README.md`, `CybORG/CybORG/Shared/Scenarios/Scenario2.yaml`,
  `CybORG/CybORG/Evaluation/evaluation.py`, reward calculators, wrappers, and
  red/blue/green agent implementations.
- `https://github.com/cage-challenge/CybORG`, observed at
  `2742b5e0ce4330c9b14006b38acd3b5ebe00d6fd` during this design, especially
  `CybORG/Simulator/Scenarios/scenario_files/Scenario2.yaml`,
  `CybORG/Evaluation/evaluation.py`, wrappers, reward calculators, and action
  implementations.
- The CAGE Challenge 2 paper, `https://arxiv.org/abs/2309.07388`, for
  challenge description, red-agent variants, action/reward/evaluation
  semantics, and evaluation protocol context.

These observed pins are not an executable dependency. The downstream mapping
issue must re-pin the exact commits or releases it consumes and record source
paths and digests in its mapping ledger.

## Decision

### 1. ACES remains the semantic authority

CAGE-2 is an authored ACES scenario plus backend-specific realization evidence.
The scenario mapping must use existing SDL, runtime, participant, objective,
observation, evidence, and experiment surfaces. It must not add
CAGE-specific SDL sections, schemas, profiles, vocabularies, manifest blocks,
exceptions, stores, or policy gates to make the mapping convenient.

Native CAGE/CybORG names, gym spaces, action ids, reward arrays, simulator
objects, and leaderboard scores are source facts. They become portable ACES
facts only when the mapping ledger binds them to existing ACES concepts,
contracts, evidence records, derived measures, or disclosed limitations.

### 2. The CAGE-2 mapping is a pinned ledger

The CAGE-2 to ACES SDL mapping must be a ledger over pinned upstream sources.
For each source fact, the ledger records the upstream repository, commit or
release, file path, source selector, optional digest, mapped ACES artifact or
field, mapping rationale, and loss disclosure.

The ledger must account for at least:

- network topology, subnets, hosts, services, accounts, credentials, roles, and
  privileges;
- blue, red, green, backend, evaluator, and participant identities;
- initial knowledge, visibility, observation surfaces, and hidden truth;
- blue defensive actions, red reconnaissance/exploitation/effect actions,
  green/user behavior, sleep/no-op behavior, and action admissibility;
- turn order, fixed step counts, episode termination, red-agent variants,
  randomization, seeds, and stochastic controls;
- reward components, cumulative score, objectives, outcomes, evidence, and
  derived measures.

Every source fact is mapped, explicitly declared out of scope, or
loss-disclosed. A disclosed gap weakens the replication claim; it is not filled
by raw CybORG logs, fixture-local assertions, or prose-only evidence.

### 3. CybORG is a conformant simulator backend

The future CybORG adapter is a simulator backend behind the existing ACES
backend protocol surface:

- `Provisioner` loads and validates target configuration, source pins,
  simulator package/version, mapping-ledger refs, seed policy, and initial
  simulator construction inputs. It returns ACES diagnostics and plans, not
  native simulator objects.
- `Orchestrator` steps the simulator through compiled ACES orchestration and
  action contracts. It reports runtime snapshots, participant histories, and
  operation receipts through ACES contracts.
- `Evaluator` projects reward, objective, terminal-condition, and scoring facts
  into ACES evaluation results, evidence records, and derived measures with
  declared margins and limitations.
- `ParticipantRuntime` mediates blue/red/green participant episodes through
  participant lifecycle, action admission, observation envelopes, behavior
  histories, and context/outcome views.

The adapter must publish a `backend-manifest-v2` through
`backend_manifest_payload()`, declare only evidence-backed capabilities, and
pass `_validate_runtime_target_shape()` before runtime use. Native CybORG
state, gym/PettingZoo tuples, reward vectors, action ids, and simulator object
representations stay adapter-private.

### 4. `sim_adapter_base` is shared adapter plumbing, not authority

The future `sim_adapter_base` package belongs in the adapter monorepo as a
convenience library for simulator drivers. It may factor target factories,
clock/seed controls, action translators, observation projectors, reward
projectors, manifest helpers, redaction helpers, and conformance harness
utilities.

It must consume ACES contracts and published artifacts. It must not define a
new semantic model, schema registry, backend protocol, diagnostic envelope,
exception hierarchy, conformance profile table, fixture corpus, concept
catalog, or policy gate.

### 5. `aces-adapters` isolates adapter projects

The future `aces-adapters` repository is a co-located monorepo of independent
adapter projects. Each adapter owns its own dependency lockfile, virtual
environment, package metadata, tests, and simulator pins. Shared packages are
versioned and consumed like ordinary dependencies.

The root repository may provide orchestration, shared documentation, and a CI
matrix, but it must not impose one resolved dependency graph across all
adapters. The CI matrix must include adapter path, lockfile, Python version,
optional simulator extras, conformance profile, and seed suite so a CybORG pin
cannot constrain unrelated adapters.

### 6. Backend conformance composes existing ACES gates

The CybORG adapter conformance harness must invoke or wrap the existing ACES
conformance runner and published backend profile/fixture corpus. It may add
simulator-specific probes, seeded equivalence checks, and mapping-ledger
coverage checks, but those probes produce ACES diagnostics and evidence. They
do not replace `contracts/profiles/backend/**`, `contracts/fixtures/**`,
`BackendManifestV2Model`, or `run_target_conformance()`.

### 7. Equivalence is tiered evidence

CAGE-2 replication is not bit-for-bit backend identity. It is a tiered evidence
claim over canonical artifacts:

- authored-source equivalence: one ACES SDL scenario and a complete pinned
  CAGE-2 mapping ledger;
- contract equivalence: each backend manifest validates and declares only
  evidence-backed support;
- execution-control equivalence: matched trial length, red-agent variant, seed
  or stochastic-control disclosure, logical step count, turn order, episode
  termination, and participant selection;
- state/observation equivalence: mapped topology, services, privileges,
  visibility, action admissibility, observations, and shared-state transitions
  satisfy declared ACES semantics;
- outcome/evaluation equivalence: reward components, objective results,
  cumulative score, evidence, derived measures, margins, and confidence
  criteria satisfy the declared claim.

If a backend cannot expose a required fact, the result is a weaker disclosed
claim or a failed equivalence check.

### 8. Cross-repo workflow is issue-driven from ACES

ACES issues, requirements, ADRs, and design records are the authority for this
replication program. Downstream `aces-adapters` issues and PRs must reference
the ACES issue, `REP-001`, this ADR, the design record, and the relevant
acceptance evidence. Adapter status must be read from linked downstream issues,
PRs, conformance reports, and evidence artifacts, not from comments or stale
docs in this repository.

### 9. Emulation is out of scope

This decision does not design or reserve a hidden emulation path for CAGE-2.
The first replication target is simulator-only. A future emulation realization
requires a separate requirement, threat/risk review, ADR or amendment, and
evidence plan.

## Implementation Mapping

Issue #635 is satisfied by this ADR, the companion design record
`docs/decisions/cage-2-replication-design.md`, and the preflight note
`docs/decisions/issue-635-rep-001-cage-2-replication-preflight.md`.

Downstream implementation issues must use the design record as their checklist:

- REP-002 stands up the adapter repository and CI isolation.
- REP-003 authors the CAGE-2 ACES SDL scenario and mapping ledger.
- REP-004 implements the CybORG simulator backend and shared adapter base.
- REP-005 drives and validates replicated runs through equivalence evidence.

## Alternatives Considered

### Add CAGE-specific SDL syntax or schemas

Rejected. ACES already has SDL, runtime, participant, evidence, and experiment
surfaces that can carry the required facts. A CAGE-specific fork would make the
first replication target a special case instead of a portability proof.

### Treat CybORG as a direct ACES runtime dependency

Rejected. CybORG is a backend dependency of the adapter, not a core ACES
dependency. ACES core packages must continue to work from published contracts,
manifests, fixtures, and profiles without importing concrete simulator
packages.

### Make `sim_adapter_base` a new protocol authority

Rejected. Shared driver plumbing is useful, but protocol authority already
lives in `aces_backend_protocols`, `aces_contracts`, published schemas,
fixtures, profiles, and conformance runners.

### Use one global adapter lockfile

Rejected. Simulator packages have different dependency and version constraints.
One lockfile would couple unrelated adapters and make the monorepo a hidden
dependency policy authority.

### Define equivalence as one score or CI result

Rejected. Scores and CI runs are evidence inputs. They are not enough to prove
that authored source, contracts, execution controls, observations, state
transitions, outcomes, and limitations align across backends.

### Include emulation realization now

Rejected. The issue explicitly excludes emulation. Mixing simulator and
emulation design here would blur the claim boundary and delay the first
adapter-driven replication.

## Consequences

### Positive

- CAGE-2 becomes a disciplined replication target without changing ACES core
  semantics.
- Downstream adapter work has a concrete boundary, file layout, and evidence
  plan.
- The design preserves independent backend conformance instead of treating
  CybORG as a privileged implementation.
- The equivalence claim is falsifiable because every tier names artifacts and
  disclosures.

### Negative / Costs

- Downstream work must maintain a detailed source mapping ledger before it can
  claim replication.
- The adapter monorepo needs more CI ceremony than a single shared package.
- Some CAGE facts may become disclosed losses rather than exact ACES facts.

### Risks

- Authors may overstate equivalence by treating score similarity as semantic
  replication. Reviews must require the tiered evidence checklist.
- Adapter authors may leak simulator-private state into portable artifacts for
  convenience. Conformance and design review must reject native object reprs,
  raw logs, hidden truth, argv/env dumps, tokens, and full tracebacks.
- Cross-repo work may drift if downstream issues do not link back to ACES
  requirements and design records. The workflow requires linked issues, PRs,
  and evidence readback.
