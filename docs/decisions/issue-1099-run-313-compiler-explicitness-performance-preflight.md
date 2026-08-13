# Issue 1099 RUN-313 Compiler Explicitness Performance Preflight

Date: 2026-08-11

Issue: #1099.

Requirement: RUN-313.

This note records the measured performance boundary and semantic guardrails for
materializing SEM-218 explicitness once during realization compilation. It does
not change explicitness classification, instantiation provenance, public SDL or
processor contracts, schemas, CLI startup, manifests, or backend behavior.

## Measured Gap

The representative input is
`examples/scenarios/hospital-ransomware-surgery-day.sdl.yaml`, a 33,774-byte
shipped scenario already used by the pipeline-determinism suite. On
`origin/dev` at `5c210d520e884cca0c08ad201b033fae920ce0c2`, realization compilation
enumerated 185 registered concerns. Each call to
`_compiled_registered_realization()` evaluated
`InstantiatedScenario.explicitness`, reconstructing all 1,461 path-keyed
records from instantiation provenance.

The prior audit measured about 148 ms for compilation and 233 ms for the full
parse/instantiate/compile/plan pipeline. A fresh Python 3.13.5 run on the
implementation host was slower in absolute terms: after three warmups, the
median of 15 runs was 347 ms for compilation and 549 ms for the full pipeline.
Across 25 runs, 185 isolated explicitness reconstructions took a median 207 ms.
The exact latency is host- and load-dependent; the 185 full reconstructions are
the portable defect signal.

## Binding Sources And Existing Surfaces

- RUN-313 and the issue #196 preflight keep the repository reference processor
  on the existing parse, instantiate, compile, and plan seams.
- SEM-218 issues #72, #489, and #490 define classifier, instantiation, compiler,
  and planner fidelity. Issues #760 and #767 preserve provenance and establish
  the path-keyed instantiated mapping as the downstream contract.
- Issue #985 expanded the registered realization concern surface; the compiler
  must continue to enumerate that registry in stable order.
- `InstantiatedScenario.explicitness` is a public convenience projection. Its
  fresh-return behavior and caller mutation isolation are not changed here.
- `_compile_realization()` owns one ordered realization-lowering pass and is the
  narrow lifetime for a pass-local snapshot.
- The compiler-package preflight for issue #41 already directs domain compilers
  to consume explicit prerequisite mappings and semantic analyses.

LLVM's official New Pass Manager documentation describes analysis managers
caching analysis results for reuse within compiler pipelines:
<https://llvm.org/docs/NewPassManager.html>. Python's `property` documentation
specifies getter invocation on attribute access and supplies no implicit
memoization: <https://docs.python.org/3/library/functions.html#property>.

## Chosen Boundary

`_compile_realization()` evaluates `scenario.explicitness` once before concern
enumeration and passes the resulting mapping to
`_compiled_registered_realization()`. The helper treats the mapping as
read-only. For `E` explicitness records and `C` registered concerns, this makes
the mapping work O(E + C) for the pass instead of O(E * C).

The snapshot lifetime is exactly one realization compile. It is not stored on
the scenario, shared across compile calls, placed in global state, or exposed
as a new public cache. This avoids mutation/invalidation questions and ensures
each separately admitted compile observes its own provenance.

## Semantic Invariants

- Admission, declaration-index construction, domain analysis, compiler order,
  registry order, diagnostic order, and `RuntimeModel` construction do not
  change.
- Every lookup uses the same `ExplicitnessRecord` values that the pre-change
  helper obtained from a freshly reconstructed but semantically identical map.
- Exact, constrained, open, provenance, designation, governing scope,
  delegation, verification, and planner behavior remain unchanged.
- No schema, serialized payload, public signature, manifest, CLI, runtime, or
  backend surface changes.
- The optimization adds no environment input, filesystem or network access,
  logging, persistence, secret handling, or new error path.

## Alternatives Rejected

- Leaving the repeated reconstruction in place preserves output but makes the
  reference processor scale with the product of two independently growing
  collections.
- Caching on `InstantiatedScenario` broadens lifetime and changes a public
  projection's isolation contract.
- Returning provenance records directly changes downstream types.
- A reduced or second explicitness index risks semantic drift from the
  canonical SEM-218 projection.

## Verification Boundary

Correctness is defended by a property test that compares complete
`RuntimeModel` values and execution plans against a reference path which
reconstructs explicitness for every concern. A separate complex-scenario test
patches the property getter and requires exactly one access per compile. The
call-count assertion is deterministic and fails if the nested reconstruction
returns; CI does not enforce a wall-clock threshold.

Existing SEM-218 fidelity, pipeline determinism, repository policy,
requirement-governance, and canonical verification suites remain required. A
same-host paired run supplied the following supporting evidence:

| Path | Repeated reconstruction | Pass-local snapshot | Median reduction |
| --- | ---: | ---: | ---: |
| Compile | 149.549 ms | 10.213 ms | 93.2% |
| Parse / instantiate / compile / plan | 240.079 ms | 99.707 ms | 58.5% |

The Python 3.13.5 measurement alternated the two modes over 15 paired runs
after two warmups. Both modes used the same helper wrapper: the reference mode
requested a fresh `scenario.explicitness` mapping for every concern, while the
optimized mode used the mapping passed by the realization coordinator. The
reference mode conservatively also paid for the coordinator's unused initial
snapshot; its 149.549 ms compile median nevertheless agrees with the independent
148 ms pre-change audit. Latency remains supporting evidence rather than the
regression oracle.

## Non-Goals

- Caching other scenario projections or compiler analyses.
- Optimizing schema-bundle construction or CLI startup.
- Changing the realization registry or adding realization concerns.
- Changing SDL, SEM-218, runtime, planner, backend, or conformance semantics.
- Adding a general compiler cache, benchmark framework, or performance SLA.
