# Participant-Crossing Proof-Tool Decision

Date: 2026-07-29

## Decision Criteria

The selected route must directly decide the exact relation, run
deterministically and noninteractively, admit immutable version/provenance
pinning, expose useful negative behavior, fit CI resource controls, and support
clean independent reproduction. Repository implementation language is not a
selection criterion.

## Compared Routes

| Route | Exact relation fit | Counterexample behavior | CI/reproduction | Disposition |
| --- | --- | --- | --- | --- |
| mCRL2 explicit-state equivalence | `ltscompare` directly supports `dpbranching-bisim` and explicit action hiding. | Bisimulation modes can produce diagnostic formulas; exact divergence-only failures also need an independently checked negative path when no formula is emitted. | Deterministic CLI, explicit formats, version output, offline execution, and immutable archive/container pinning fit the finite carrier. | Selected for the finite equivalence decision. |
| TLC temporal/model checking | Directly explores finite TLA+ state systems and checks safety/liveness properties, but does not decide bisimulation merely because properties agree. | Counterexample traces are useful for deadlock, replay, atomicity, and progress properties. | Mature noninteractive tooling and reproducible finite configurations. | Auxiliary only; a relational product and invariant would need separate justification. |
| Isabelle/HOL coinduction | Can define the relation as a greatest fixed point and check a coinductive theorem in the kernel. | Failed proof obligations are local, but counterexample discovery is not its primary role. | Strong replayability with a larger formalization and maintenance cost. | Future parameterized or unbounded theorem route. |

Official references:

- [mCRL2 `ltscompare`](https://www.mcrl2.org/web/user_manual/tools/release/ltscompare.html)
- [TLA+ tools](https://lamport.azurewebsites.net/tla/tools.html)
- [Isabelle/HOL coinduction](https://isabelle.in.tum.de/dist/library/Doc/Isar_Ref/HOL_Specific.html)

## Selected Contract

Version: mCRL2 `202607.0`.

Fixed command:

```text
ltscompare --equivalence=dpbranching-bisim --tau=internal \
  abstract.aut concrete.aut
```

The model exporter maps only the five governed internal semantic classes to
the checker action `internal`. Both `.aut` inputs are repository-relative and
independently generated.

The child implementation must record and check:

- mCRL2 version and verified archive checksum or immutable container digest;
- fixed command, locale, working directory, CPU/memory/time/output limits, and
  zero verification-time network;
- abstract/concrete model source and generated digests;
- profile, projection, mapping, taxonomy, and source-revision digests;
- complete domain, state, and transition counts;
- positive result or safe negative result;
- every mutation and counterexample digest;
- CI artifact digest, retention, and claim binding; and
- the clean independent reproduction command, environment, expected result,
  and recomputed digests.

The tool is invoked through a fixed allowlisted wrapper without a shell.
Inputs, payloads, policy bodies, credentials, and counterexamples are not
placed in argv, environment variables, filenames, logs, or unrestricted
stderr. Only synthetic bounded identifiers and safe summaries are published.

## Evidence Classification

A positive exhaustive result over the complete selected finite carrier uses
the `model-check` assurance axis. It is not an unbounded mathematical proof.
A successful process exit is not a proof certificate. The positive evidence
surface is the complete pinned input/result bundle plus independent
reproduction.

Any carrier truncation, timeout, sample, missing mutation, mapping drift,
mutable tool pin, or digest mismatch fails closed and blocks the claim.
