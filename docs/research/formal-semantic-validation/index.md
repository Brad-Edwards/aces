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
The immutable issue-168 v1 record keeps whole-scenario satisfiability,
exploit-path validity, and counterfactual necessity `untested` at its pinned
revision. ADR-086 and issue #826 add a revisioned satisfiability supplement:
the exact finite-domain profile is now `demonstrated` by production
satisfiable, unsatisfiable, and fail-closed unsupported controls. Issue #827
adds a bounded typed exploit-path analyzer and published evidence contract for
`aces-exploit-path-analysis-v1`; that result is valid only for its admitted
snapshot, normalized attack graph, query, and search profile. It does not
demonstrate arbitrary-SDL or real-world exploit validity, and counterfactual
necessity remains `untested`.

## Bundle

- [`bundle-manifest.json`](bundle-manifest.json) is a stable index over
  immutable records in `bundles/`. Base evidence and supplements advance in
  separate files, then the checker composes their highest revisions
  deterministically. Adding a supplement no longer rewrites the base bundle.
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
- [`satisfiability-analysis-v1.json`](satisfiability-analysis-v1.json) is the
  issue-826 supplement. It binds positive, negative, and unsupported source
  controls to production outcomes and normalized-model digests. The checker
  recomputes and replays each full evidence envelope; checked-in outcome labels
  alone cannot satisfy the gate.
- [`satisfiability-execution-snapshot-v1.json`](satisfiability-execution-snapshot-v1.json)
  records fixed-argv, network-disabled commands and source/model/configuration
  digest observations for those controls. The supplement analysis joins this
  execution id and revision rather than rewriting the issue-168 v1 snapshot.
- [`live-activity-replay-v1.json`](live-activity-replay-v1.json) publishes the
  DSL-437 profile and occurrence domain bytes, canonical payload digests, and
  replay identities for the normative example. Focused contract tests
  recompute every value through the production parser and compiler.

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
snapshot. It separately executes the governed satisfiability analyzer, verifies
the complete three-control matrix and digest pins, and replays each envelope.
It also binds each participant observation to its declared positive
and negative pytest node ids and executes the complete participant fixture set;
checked-in `passed` labels alone cannot satisfy the gate. The checker prevents
unsupported classes from being promoted by weaker evidence. It performs no
network access, backend deployment, shell evaluation, credential lookup, or
environment-selected corpus loading.

Failed observations are evidence. A later product correction or ACES revision
creates a new execution snapshot and analysis; it does not overwrite this
record.
