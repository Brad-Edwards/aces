# CAGE Challenge 2 (Scenario2) — ACES SDL

`cage-2-scenario2.sdl.yaml` authors the TTCP CAGE Challenge 2 (Scenario2)
scenario as a single ACES SDL document. It is the **authored source of truth**
for the CAGE-2 replication program (REP-003, ADR-069,
`docs/decisions/cage-2-replication-design.md`): the one scenario both backends
(the CybORG simulator adapter and the ACES reference backend) realize in
REP-005. It is a positive, reusable corpus example — not a benchmark, backend
profile, conformance fixture, mapping ledger, or replication claim.

The document uses only existing SDL surfaces. No CAGE/CybORG-specific SDL
sections, schemas, vocabularies, or keys are introduced (ADR-069 §1). CAGE
action ids, gym spaces, reward vectors, and simulator object names are source
facts; they become ACES facts only through existing surfaces or are recorded as
loss disclosures below.

## Topology

Three subnets model the three CAGE-2 subnet roles:

- `user-net` (10.0.1.0/24) — the user host subnet, `User0`–`User4`. Holds the
  red foothold.
- `enterprise-net` (10.0.2.0/24) — the enterprise server subnet, `Enterprise0`,
  `Enterprise1`, `Enterprise2`, and `Defender` (the blue Velociraptor server).
- `operational-net` (10.0.3.0/24) — the critical operational/OT subnet,
  `Op_Server0` (the mission-critical OT service host) plus `Op_Host0`–`Op_Host2`.

CAGE-2 reachability is encoded structurally:

- `Enterprise0` bridges `user-net` ⇄ `enterprise-net` (the user→enterprise
  gateway).
- `Op_Host0` bridges `enterprise-net` ⇄ `operational-net` (the
  enterprise→operational gateway).
- `operational-net` carries ACLs that **deny inbound traffic from `user-net`**
  and allow it from `enterprise-net`, so red cannot reach the OT subnet directly
  from the user subnet and must pivot through enterprise.

`Op_Server0` carries the named `ot-service` and an `asset_value` of **high
availability / medium confidentiality / medium integrity**, matching CAGE-2's
rating of the operational server (High Availability, Medium Confidentiality).

## Identities and participants

CAGE identities are kept distinct (ADR-069): an SDL `agent` is authored
participant intent, not a participant implementation manifest, simulator policy
object, backend identity, or evaluator identity.

- **Entities** (`red-team`, `blue-team`, `green-users`, `evaluator`) carry the
  four CAGE roles: red, blue, green, and the white/evaluator cell.
- **Red** starts with a privileged (`SYSTEM`) foothold session on `User0`
  (`accounts.red-foothold`). Three red policy variants are authored as separate
  agents — `red-bline` (beeline to the OT server), `red-meander` (exploratory),
  and `red-sleep` (no-op) — mapping the CAGE `B_lineAgent`, `RedMeanderAgent`,
  and `SleepAgent`. All red variants share the `User0` foothold; exactly one
  runs per CAGE episode.
- **Blue** (`blue-defender`) knows the full topology and carries the CAGE blue
  action vocabulary (Monitor, Analyse, Remove, Restore, the Decoy* actions, and
  Sleep).
- **Green** (`green-agent`) generates benign user activity across the user and
  operational hosts.

Red action names (`DiscoverRemoteSystems`, `DiscoverNetworkServices`,
`ExploitRemoteService`, `PrivilegeEscalate`, `Impact`) and the blue/green action
names are authored as the agents' declared action labels, reflecting the CAGE
action set. The `exploitable-remote-service` (CWE-284) and
`privilege-escalation-weakness` (CWE-269) vulnerabilities place the red
discover→exploit→escalate→impact path onto concrete hosts.

## Objectives and scoring

The scoring pipeline (`conditions → metrics → evaluations → tlos → goals`)
scores blue's defense of the operational subnet: `ot-availability` and
`op-server-integrity` roll up into the `operational-defense` evaluation, the
`protect-operational-service` TLO, and the `cage2-blue-success` goal. Two
declarative `objectives` bind the actors to targets and success criteria:
`red-impact-op-server` (red reaches and impacts `Op_Server0`) and
`blue-protect-op-server` (blue keeps the OT service available and evicts red).
Red success is scored by the separate red-positive `op-server-compromise`
metric, so red is never credited by the defensive integrity state.

Reward, cumulative score, objective satisfaction, and replication equivalence
are distinct concepts and are **not** conflated here (ADR-069 §7); the numeric
CAGE reward projection is downstream evaluator work.

## CAGE-2 → ACES name mapping

CAGE host names are preserved verbatim as SDL node keys. CAGE subnet roles are
given ACES-idiomatic switch names:

| CAGE-2 fact | ACES SDL |
|---|---|
| User subnet | `user-net` (switch) |
| Enterprise subnet | `enterprise-net` (switch) |
| Operational subnet | `operational-net` (switch) |
| `User0`..`User4` | nodes `User0`..`User4` |
| `Enterprise0`..`Enterprise2`, `Defender` | nodes of the same name |
| `Op_Server0`, `Op_Host0`..`Op_Host2` | nodes of the same name |
| `OTService` on the operational server | `nodes.Op_Server0.services.ot-service` |
| Red `SYSTEM` foothold on `User0` | `accounts.red-foothold` |
| `B_lineAgent` / `RedMeanderAgent` / `SleepAgent` | agents `red-bline` / `red-meander` / `red-sleep` |
| Blue agent | agent `blue-defender` |
| Green agent | agent `green-agent` |

## Source pins

Topology authored from the pinned upstream CAGE-2 sources recorded in ADR-069:

- `github.com/cage-challenge/cage-challenge-2` @
  `26ce1c1253fa9e2e73f25e6a7f2da32860c11257`,
  `CybORG/CybORG/Shared/Scenarios/Scenario2.yaml` — subnets, hosts, host↔subnet
  membership, the `Op_Server0` OTService, the red `User0` foothold, and the
  User→Operational reachability restriction.
- The CAGE Challenge 2 paper, `arxiv.org/abs/2309.07388` — red-agent variants
  and the challenge narrative.

The digest-bearing CAGE-to-ACES source-mapping ledger (per-fact source path,
selector, and content digest) lives downstream in `aces-adapters` per the
REP-001 design layout; it is not an SDL parser input and is not committed here.

## Loss disclosures

Facts authored as ACES modelling choices where CAGE encodes them elsewhere or
does not enumerate them:

- **Per-host service ports/protocols** (SMB 445, SSH 22, HTTP 8080, OT 5020,
  Velociraptor 8000): CAGE encodes host services via image definitions rather
  than inline in `Scenario2.yaml`. The ACES bindings are role-appropriate
  authored values, not verbatim CAGE ports.
- **Subnet CIDRs / IP plan** (10.0.1–3.0/24): authored addressing; CAGE assigns
  addresses dynamically at instantiation.
- **Vulnerability CWE classes**: authored classifications that place the CAGE
  exploit/escalate abilities onto concrete hosts; CAGE models exploitability via
  action success, not CWE identifiers.
- **Trial length, turn order, seeds, red-variant selection, and the numeric
  reward calculator** are execution-control facts owned by REP-005 experiment
  artifacts, not the authored scenario. The reward-calculator label
  (`HybridAvailabilityConfidentiality`) is recorded on the red agents as an
  authored hint only.

## Commands

Run from `implementations/python/`:

```bash
uv run aces sdl resolve        ../../examples/scenarios/cage-2-scenario2.sdl.yaml
uv run aces sdl verify-imports ../../examples/scenarios/cage-2-scenario2.sdl.yaml
# publish resolves paths relative to the module root; pass an absolute SDL path:
uv run aces sdl publish "$PWD/../../examples/scenarios/cage-2-scenario2.sdl.yaml" --output-dir /tmp/cage2-dist
```

`resolve` writes a directory-scoped `aces.lock.json` next to the scenario; it is
a transient (no lockfiles are committed to this repo) and should not be staged.
The scenario declares no imports. Loading and published-schema conformance are
exercised automatically by `tests/test_scenarios.py` and
`tests/test_example_schema_conformance.py`.

## Limitations

- Proves SDL parsing, semantic validation, published-schema conformance, module
  resolution, and OCI publication of the CAGE-2 scenario. It does not run CAGE-2
  through any backend.
- Does not implement the CybORG adapter, `sim_adapter_base`, `aces-adapters`,
  backend conformance probes, or replication/equivalence evidence.
- Makes no replication, equivalence, or CAGE-score claim; a high CAGE score is
  not, by itself, semantic equivalence (ADR-069 §7).
- Does not realize CAGE-2 on an emulation backend (explicitly deferred).

## Links

- Requirement: REP-003 (issue Brad-Edwards/aces#637).
- Program architecture: REP-001 (issue Brad-Edwards/aces#635), ADR-069, and
  `docs/decisions/cage-2-replication-design.md`.
- Downstream realization: REP-004 (CybORG adapter + `sim_adapter_base`) and
  REP-005 (replicated runs and equivalence evidence), in `aces-adapters`.
