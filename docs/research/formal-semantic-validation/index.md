# Formal Semantic Validation And Reachability Evidence

This directory is the falsification/evidence gate for issue #168 and
requirement ASR-530. It records exactly what the current ACES parser,
semantic validator, compiler, participant contracts, and existing regression
fixtures demonstrate—and preserves the stronger claims they do not
demonstrate.

The bundle keeps seven literature validation calls separate: schema validity,
semantic consistency, graph reachability, constraint satisfiability,
exploit-path validity, determinism/stability, and counterfactual necessity.
Schema evidence is bounded to the structural cases. Semantic, participant,
workflow-reachability, and parse-to-compile determinism evidence is partial.
Whole-scenario satisfiability, exploit-path validity, and counterfactual
necessity remain `untested` because ACES has no governed solver or executable
protocol for those claims.

## Bundle

- [`bundle-manifest.json`](bundle-manifest.json) selects the exact active
  protocol, corpus, execution snapshot, and analysis.
- [`protocol-v1.json`](protocol-v1.json) freezes the claim boundaries,
  entrypoints, allowed evidence, objective pass/fail rules, and participant
  obligations before interpretation.
- [`corpus/manifest-v1.json`](corpus/manifest-v1.json) carries positive and
  single-defect negative cases for every claim class. Unsupported classes have
  explicit cases with no invented research-only model or fixture semantics.
- [`execution-snapshot-v1.1.json`](execution-snapshot-v1.1.json) pins ACES commit
  `9347f64b26e3bb71d5459759c3d4bd473c76b446`, fixed-argv commands, replay
  digests, structured diagnostic kinds, participant fixture outcomes, and
  limitations.
- [`analysis-v1.1.json`](analysis-v1.1.json) derives ADR-021 evidence status from
  the frozen observations and states the bounded result in plain language.

The participant matrix includes positive and negative fixtures for hidden
world versus participant-visible projection, fail-closed action applicability,
shared-state effects, ordering before causality, evidence-labeled attribution,
participant-local outcome separation, and realization-profile honesty. These
fixtures support selected semantic claims; they are not counterfactual proof
or universal backend-fidelity evidence.

## Reproduction

Run the offline integrity and replay gate with:

```bash
implementations/python/.venv/bin/python tools/check_formal_semantic_validation.py
```

The checker uses bounded duplicate-safe JSON loading, repository-containment
checks, closed shapes, stable ids, complete joins, and production SDL
entrypoints. It reruns supported corpus cases and compares them to the immutable
snapshot. It also binds each participant observation to its declared positive
and negative pytest node ids and executes the complete participant fixture set;
checked-in `passed` labels alone cannot satisfy the gate. The checker prevents
unsupported classes from being promoted by weaker evidence. It performs no
network access, backend deployment, shell evaluation, credential lookup, or
environment-selected corpus loading.

Failed observations are evidence. A later product correction or ACES revision
creates a new execution snapshot and analysis; it does not overwrite this
record.
