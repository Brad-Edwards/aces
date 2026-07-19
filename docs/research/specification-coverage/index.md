# Standardized Specification Coverage

This directory is the falsification/evidence bundle for issue #164 and
requirement ASR-530. It tests a bounded claim: whether ACES can represent a
preregistered set of cyber-agent evaluation environment requirements through
portable SDL, experiment, and apparatus surfaces without requiring backend
deployment vocabulary in core SDL.

The result is **partial**, not demonstrated. All ten issue-defined
load-bearing concepts passed their owning production boundaries, but three
supplemental concepts have no current typed carrier: participant tool and
affordance declarations, solver-backed constraint satisfiability, and
federated cyber object/event exchange. Those gaps are preserved as evidence;
this run does not repair them.

## Frozen bundle

- [`bundle-manifest.json`](bundle-manifest.json) pins the active protocol,
  snapshot, analysis, and their SHA-256 digests.
- [`protocol-v1.json`](protocol-v1.json) preregisters four source strata, four
  representative requests, sixteen atomic concepts, expected carriers and
  classifications, stage obligations, load-bearing status, classification
  rules, and objective pass/fail criteria.
- [`execution-snapshot-v1.1.json`](execution-snapshot-v1.1.json) pins ACES commit
  `9347f64b26e3bb71d5459759c3d4bd473c76b446`, deterministic digests of the SDL,
  processor, and contract implementation surfaces, exact repository artifacts,
  production entrypoints, typed pointers, diagnostics, and observed outcomes.
- [`analysis-v1.1.json`](analysis-v1.1.json) is recomputed from the protocol and
  bound to the complete snapshot digest, and records the ADR-021 evidence
  status.

The source strata are a cyber-range survey, the CybORG autonomous-agent
benchmark, the VSDL cyber-range DSL, and the SISO Cyber Data Exchange Model.
The protocol stores bounded paraphrases and precise citations; it does not copy
papers, standards, private literature, or compared-system source trees.

## Outcome

| Classification | Count | Interpretation |
| --- | ---: | --- |
| Directly expressible | 10 | Typed SDL or experiment fields preserve the concept at every applicable stage. |
| Profile or manifest constraint | 2 | Apparatus selection and clock context remain outside core SDL in validated contracts. |
| Deliberately backend specific | 1 | Provider provisioning mechanics remain a realization concern. |
| Missing | 3 | No current typed carrier exists; the gap is not approximated through prose or metadata. |

The survey-derived request passes for topology, roles, objectives, workflows,
evidence expectations, and apparatus constraints. The other three requests
remain partial because each contains one missing concept. No unallowed backend
vocabulary occurrence was observed in a directly expressible concept.

This does not prove universal cyber-range coverage, language usability,
scientific adequacy, independent backend implementation, backend substitution,
live realization fidelity, or behavioral equivalence. The execution uses the
pinned reference processor and published contracts; no range, participant,
cloud, hypervisor, or federation was executed.

## Reproduction

Run the focused offline gate with:

```bash
implementations/python/.venv/bin/python tools/check_specification_coverage.py
```

The checker uses bounded duplicate-key-safe JSON loading and repository path
containment, verifies content digests and exact cross-record joins, executes
the pinned SDL artifacts through `parse_sdl_file()`, semantic validation,
`instantiate_scenario()`, `admit_instantiated_scenario()`, and
`compile_runtime_model()`, validates the named experiment/profile contracts,
resolves every passing typed pointer, and rejects stale or dishonest analysis.
It also rejects post-execution reclassification, any non-passing load-bearing
stage, implementation-surface drift, and analysis that is not bound to the
complete snapshot.
It performs no network access, shell evaluation, live backend access, dynamic
plugin loading, or environment-selected semantic binding. The same checker
runs once in the canonical nox contracts graph.

Protocol changes create a new protocol revision. Re-execution against a new
ACES revision creates a new immutable snapshot and analysis. A later product
fix must not overwrite this result or remove a missing concept from the
denominator.
