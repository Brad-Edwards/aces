# Prior Art And Design Criteria For Scenario Variation And Trial Realization

Date: 2026-07-15

Issue: #652

Requirement: SCE-002

## Research Question And Method

The question is not merely how to substitute values in YAML. It is how ACES
can describe a bounded family of valid cyber-range scenarios, select trials as
part of an experiment, realize every selected trial deterministically, and
preserve enough provenance to make scientific claims without allowing a
scheduler, backend, or mutable runtime state to become a second source of
scenario meaning.

The review prioritizes normative specifications, official project
documentation, and original papers. Secondary surveys were used only to locate
primary work. The transfer question for every source is explicit: which
property is useful to ACES, and which authority boundary must not be imported
with it?

## Typed Configuration And Module Languages

### CUE: constraints as values

The [CUE language specification](https://cuelang.org/docs/reference/spec/)
models values in a lattice and defines unification as commutative,
associative, and idempotent. That makes evaluation order irrelevant for the
core constraint operation. Disjunction supplies a typed alternative surface,
while closed structures and concrete-value checks distinguish a constraint
from a completed configuration.

Useful transfer:

- a declared domain and a selected concrete value should be different phases;
- intersection of constraints should be deterministic and fail with no value
  when the intersection is empty; and
- alternatives should be members of a closed union rather than callbacks or
  arbitrary document patches.

Limit: ACES does not adopt CUE evaluation, comprehensions, interpolation, or a
general constraint language. SDL remains the normative language, and the
selected scenario must pass its ordinary semantic validator.

### Dhall: total configuration and import integrity

The [Dhall Language Tour](https://docs.dhall-lang.org/tutorials/Language-Tour.html)
describes a total, strongly typed configuration language with typed records,
unions, functions, imports, semantic hashes, and normalization. Dhall's import
hashes demonstrate that reproducible composition requires the imported
content and resolution semantics to be identified, not just an author-provided
path.

Useful transfer: preserve trusted, digest-pinned module resolution before
selection, and make normalized artifacts independent of checkout location.
Limit: functions and arbitrary normalization are deliberately outside the SDL
variation surface. ADR-053 and ADR-078 already own the narrower ACES import and
phase model.

### Jsonnet: programmable generation is powerful but changes the trust model

The [Jsonnet specification](https://jsonnet.org/ref/spec.html) defines a lazy,
pure functional configuration language with objects, inheritance, local
bindings, comprehensions, and functions. It shows why a configuration program
can generate families compactly, but also why adopting one would move
authorship, termination, diagnostics, and review into another evaluator.

Useful transfer: distinguish reusable declarations from their manifested JSON
result. Limit: ACES rejects an embedded configuration program; scenario
variation must remain finite or otherwise explicitly bounded, typed, and
reviewable without executing author code.

### Terraform: stable instance keys matter

Terraform separates
[declared input variables](https://developer.hashicorp.com/terraform/language/values/variables)
from resource instances, and its
[`for_each` meta-argument](https://developer.hashicorp.com/terraform/language/meta-arguments/for_each)
uses map keys or set members to identify instances. This is a useful warning:
positional expansion or value-derived names make identity churn when an
unrelated item is inserted or a parameter changes.

Useful transfer: variation-point ids, logical trial coordinates, and selected
declaration ids must be stable symbols. Limit: ACES does not inherit
Terraform's resource state, provider lifecycle, or plan/apply semantics.

### Common Workflow Language: explicit scatter products

The [CWL Workflow specification](https://www.commonwl.org/v1.2/Workflow.html)
makes scatter expansion explicit and distinguishes dot-product,
flat-cross-product, and nested-cross-product methods. This prevents a list of
factors from silently implying a product shape.

Useful transfer: an experiment selection policy must state whether it
enumerates, zips, samples, blocks, or crosses domains, and it must assign
stable logical coordinates before execution. Limit: ACES trial compilation is
not a dataflow workflow engine, and scheduler concurrency cannot influence the
expansion result.

### Language-design conclusion

The strongest shared lesson is phase separation:

```text
declaration + bounded domain -> validated family -> concrete selection
```

Generic template or evaluation languages offer expressiveness by allowing
authors to compute structure. ACES instead needs inspectability, boundedness,
portable diagnostics, and stable identity. The appropriate seam is therefore
a closed variation-point union and a separate experiment selection policy,
not a second language runtime.

## Simulation Experiment And Model Separation

### MIASE and SED-ML

The original
[MIASE paper](https://doi.org/10.1371/journal.pcbi.1001122) distinguishes the
models used by a simulation from the simulation procedures, their order,
intermediate processing, and outputs. It also distinguishes reproducibility
of an experiment from identical numerical results. The
[SED-ML specifications](https://sed-ml.org/specifications.html) operationalize
the same separation with model references, simulation descriptions, tasks,
repeated tasks, data generators, and outputs.

Useful transfer:

- the SDL scenario family is not the experiment design;
- parameter scans, allocation, repetition, and stochastic policy belong to an
  experiment artifact that references the model/family;
- the selected procedure and transformations must be preserved alongside the
  selected values; and
- replay support is a claim bounded by preserved inputs, algorithms,
  apparatus, and unavailable external state.

Limit: ACES is not claiming SED-ML or MIASE conformance, numerical equivalence
across backends, or a particular simulation algorithm.

### SSP and FMI

The Modelica Association's
[System Structure and Parameterization specification](https://ssp-standard.org/docs/main/)
separates system structure, component references, connections, and parameter
bindings. The
[Functional Mock-up Interface 3.0.2 specification](https://fmi-standard.org/docs/3.0.2/)
defines a portable execution interface with variables, causality, variability,
clocks, state, and co-simulation/model-exchange roles.

Useful transfer: parameter binding should target declared typed locations,
and a backend execution interface should consume an already-defined model
rather than reinterpret its experimental design. Limit: FMI variables and SSP
parameter sets do not define ACES scenario identity, experiment allocation, or
cyber-range backend feasibility.

### Experimental frames

Zeigler's work on
[modular separation between models and experimental frames](https://doi.org/10.1080/03081078408934871)
treats the conditions under which a model is observed or exercised as a
separate concern. This supports ACES's existing scenario/task/apparatus split:
the scenario states possible world meaning, while task, experiment, and
apparatus artifacts state how that meaning is exercised and observed.

Limit: ACES does not adopt DEVS as its execution semantics. The transfer is the
separation principle, not the formalism.

## Reproducible Random Streams And Parallel Execution

### A seed does not identify an algorithm

The [NumPy random design](https://numpy.org/doc/stable/reference/random/)
separates a bit generator from distribution transforms and documents multiple
parallel-generation patterns. Its
[compatibility policy](https://numpy.org/doc/stable/reference/random/compatibility.html)
and [NEP 19](https://numpy.org/neps/nep-0019-rng-policy.html) are especially
important: a reproducibility promise must say which layer is stable. A seed
alone omits the generator, seed-to-state mixing, bit interpretation,
distribution transformation, and library/version behavior.

Therefore an ACES random-stream profile must identify:

1. generator family and version;
2. seed value and canonical seed encoding;
3. canonical semantic-address encoding and derivation function;
4. integer/real conversion and distribution/sampling transformation versions;
5. rejection/exhaustion semantics; and
6. the compatibility promise for that complete profile.

### Streams must follow semantic coordinates

L'Ecuyer and colleagues' original
[streams and substreams work](https://doi.org/10.1287/opre.50.6.1073.358)
shows how independently addressable streams support simulation organization.
NumPy's
[`SeedSequence`](https://numpy.org/doc/stable/reference/random/bit_generators/generated/numpy.random.SeedSequence.html)
mixes entropy reproducibly and derives child streams through a spawn key.
These are useful mechanisms, but a spawn sequence tied to worker creation order
would still be wrong for ACES.

An ACES stream address must instead be a canonical tuple of immutable semantic
coordinates, for example:

```text
(explicit randomness namespace,
 logical trial coordinate,
 policy or variation-point id,
 draw purpose,
 local draw coordinate)
```

Worker id, process id, thread id, host, queue position, wall time, completion
order, retry number, and map iteration order are forbidden address inputs.
The aggregate experiment-spec identity/digest is also forbidden: an unrelated
metadata edit would otherwise re-key every stream. The experiment instead owns
a stable randomness namespace and root seed. Retaining them requests common
random numbers at unchanged addresses; an independent randomization explicitly
rotates the namespace or seed. Adding a draw for one variation point must not
perturb another point.

### Counter-based generation is the reference design shape

The original
[Random123 paper](https://www.thesalmons.org/john/random123/papers/random123sc11.pdf)
and [project](https://random123.com/) describe counter-based generators where
a random block is a stateless function of a counter and key. This shape makes
random access and parallel evaluation natural: scheduling does not advance a
shared mutable state.

ACES need not select Random123 in this design issue. It should, however, require
the same externally visible property: a draw is determined from its governed
profile and semantic address, never from how many draws happened to occur on a
worker. A future implementation may use a counter-based generator or a
carefully specified derivation of independent stateful streams, provided it
passes the schedule-permutation and non-interference properties.

## Experimental Coverage And Sampling

NIST's
[combinatorial coverage measurement](https://www.nist.gov/publications/combinatorial-coverage-measurement)
measures which t-way combinations of parameter values a test set covers. It
supports a useful distinction between a scenario-family domain and a policy
that chooses a subset of that domain. Pairwise or t-way coverage is a selection
objective, not part of scenario validity and not proof of behavioral coverage.

A selection policy may therefore enumerate, sample, block, stratify, or target
combinatorial coverage. It must record the domain version, policy version,
logical coordinates, exclusions, and achieved/target coverage disclosure. A
backend may reject an unrealizable point, but may not replace it with a nearby
point and claim the original coverage.

## Cyber Playbooks, CTI, And Range Generation

### CACAO, ATT&CK, STIX, and Attack Flow

[CACAO Security Playbooks 2.0](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.pdf)
defines a portable playbook vocabulary with workflow steps, commands,
variables, targets, and control flow. It is useful alignment material for
declared attack/defense procedures, but a CACAO playbook is neither an ACES
topology nor an experiment allocation.

[STIX 2.1](https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html)
is a CTI object and relationship language. MITRE states that the
[ATT&CK STIX dataset](https://attack.mitre.org/resources/attack-data-and-tools/)
is its most granular machine-readable representation. The
[ATT&CK Navigator](https://github.com/mitre-attack/attack-navigator) annotates
and visualizes matrices and coverage, while
[Attack Flow](https://github.com/center-for-threat-informed-defense/attack-flow)
represents how ATT&CK techniques are composed into attacks.

Useful transfer:

- retain external object ids, revisions, mappings, and source digests;
- represent logical technique/action order explicitly when it has scenario
  meaning;
- measure ATT&CK coverage against revision-pinned technique sets; and
- treat CTI/layers/flows as evidence-bearing candidate inputs, not as trusted
  executable SDL or runtime selectors.

Limit: ATT&CK membership does not supply preconditions, effects, infrastructure,
credentials, concrete commands, success criteria, evidence requirements, or
backend feasibility. An automated mapping must emit candidates that pass the
ordinary authoring, trust, semantic-validation, and trial-admission gates.

### CALDERA and Atomic Red Team

MITRE CALDERA distinguishes abilities, adversary profiles, operations, agents,
facts, and objectives in its
[terminology](https://caldera.readthedocs.io/en/2.7/Learning-the-terminology.html)
and [objective model](https://caldera.readthedocs.io/en/latest/Objectives.html).
Facts can feed ability variables during an operation. This demonstrates useful
late binding, but it also demonstrates the authority risk: discovered runtime
facts must not silently become pre-run factor selection or scenario topology.

[Atomic Red Team](https://github.com/redcanaryco/atomic-red-team) publishes
small ATT&CK-mapped tests with explicit input arguments, dependencies, execute
commands, and cleanup commands. It demonstrates the value of bounded,
inspectable inputs and reusable atomic actions. It does not supply a scientific
trial compiler or an ACES campaign composition model.

### Planning and cyber-range generation

The [PDDL reference](https://ipc06.icaps-conference.org/deterministic/pddl.html)
separates a planning domain from a problem instance and makes action
preconditions/effects explicit. Cyber-range work including
[VSDL](https://arxiv.org/abs/2001.06681) and
[CRACK](https://doi.org/10.1016/j.cose.2020.101837) uses DSLs, model
verification, generation, and automated testing to reduce scenario-authoring
cost.

Useful transfer: generation should produce a reviewable candidate with a
declared constraint/model basis, followed by independent validation and
admission. Limit: a planner, LLM, CTI mapper, or generator is not SDL semantic
authority. It cannot mint imports, bypass trust, invent unbounded values, or
turn a failed candidate into a different admitted trial through hidden search.

## Adaptive Difficulty And Benchmark Validity

Hunicke and Chapman's
[Hamlet](https://www.cs.northwestern.edu/~hunicke/pubs/Hamlet.pdf) models
dynamic difficulty adjustment as a control problem driven by predicted player
performance. The lesson is not a particular controller; it is that adaptation
has a policy, observations, trigger, intervention, and outcome that must be
separable and inspectable.

For training, an adaptive intervention may be desirable. For benchmarking, it
changes the treatment received and can destroy comparability if hidden. ACES
must therefore preserve the admitted baseline trial and record any adaptive
intervention as a later run event with policy identity, observation basis,
trigger, action, timing, and effect disclosure. A derived follow-up trial needs
a new admitted run identity linked to the source run. Runtime performance may
never retroactively rewrite baseline factors, snapshot identity, or random
streams.

## Rejected Architecture Families

### Arbitrary templates, expressions, callbacks, or patches

Rejected because they can compute unbounded structure, target unstable document
paths, hide dependencies, weaken static review, and require another evaluator
and security model. JSON Patch also lets selected values mutate identity-bearing
fields unless a second semantic access-control language is invented.

### Ambient or worker-local randomness

Rejected because OS entropy, process-global RNG state, worker allocation, retry
count, and traversal order make the trial set depend on scheduling. Recording a
seed after the fact does not repair an unspecified generator/draw contract.

### One shared mutable parameter or fact store

Rejected because reads become time-dependent, authorization and redaction
boundaries blur, retries can observe different values, and runtime discoveries
can retroactively change experiment meaning. Pre-run selections belong in a
sealed admitted plan; runtime observations may fill only typed late-bound sinks.

### Backend-directed selection or resampling

Rejected because feasibility and selection are different authorities. A
backend envelope can prove or refute realizability of a selected point; it may
not choose the scientific treatment. Failure must remain visible.

### Trial as a second archival root

Rejected because ADR-068 and ADR-065 already make one execution one
`experiment-run-v1` record. The plan entry preallocates that run identity; it
does not create a parallel trial provenance graph.

## Derived Design Criteria

The research yields the following criteria for the binding design:

1. **One phase, one authority.** Composition, family validity, experiment
   selection, trial admission, instantiation, runtime fact binding, backend
   realization, scheduling, and archival provenance have named owners.
2. **Composition closes first.** All imports are trusted, resolved, namespace
   qualified, and digested before any trial selection.
3. **Stable symbols.** Declaration, variation-point, policy, and logical-trial
   ids do not depend on selected values, source paths, or worker order.
4. **Closed bounded variation.** Scalar/reference domains, alternatives,
   subsets, constrained order, and logical timing are closed discriminated
   kinds with explicit bounds.
5. **Independent validity.** Every structural alternative must be semantically
   valid when selected; a family declaration is not permission to emit an
   invalid intermediate scenario.
6. **Selection is experiment design.** Enumeration, crossing, sampling,
   allocation, blocking, and coverage belong to experiment policies, not SDL
   composition or backend behavior.
7. **Scenario and backend domains differ.** Scenario membership is checked
   before realization-envelope membership/subsumption.
8. **Profile the full RNG stack.** Generator, seed encoding, address
   derivation, canonical input, transformations, and exhaustion are versioned.
9. **Semantic stream addressing.** Streams derive from an explicit stable
   randomness namespace plus trial/policy/purpose coordinates, never the
   aggregate experiment digest.
10. **Stream non-interference.** A draw added to one concern cannot perturb
    another concern's selected value.
11. **Schedule independence.** Serial, parallel, batched, reordered, retried,
    and cross-process compilation produces byte-identical admitted plans.
12. **Fail closed.** Empty domains, exhausted constraints, invalid choices,
    duplicate coordinates, and apparatus mismatch produce no plan.
13. **One planned/executed identity.** A plan entry's preallocated run id
    becomes the archival run id when execution starts.
14. **Immutable intent.** The admitted plan seals refs/digests, coordinates,
    selections, factors, profiles, apparatus intent, and admission evidence.
15. **Ordinary instantiation.** Realization calls the public SDL phase APIs and
    reuses their validation and provenance; no private binder mints results.
16. **Typed late binding only.** Runtime facts fill declared sinks with source,
    type, scope, freshness, sensitivity, and evidence metadata.
17. **Secrets remain references.** Secret values never enter factors, stream
    addresses, identities, digests, plan summaries, diagnostics, or logs.
18. **Scheduler is a consumer.** It may place, delay, pause, retry transport,
    and enforce isolation; it cannot select, instantiate, score, or resample.
19. **Adaptation is an intervention.** It never rewrites the admitted baseline
    and is disclosed for validity/comparability review.
20. **Generation is candidate production.** CTI, ATT&CK layers, playbooks,
    planners, and AI systems enter through normal trust, validation, and
    admission gates.
21. **Compatibility is monotone.** Existing static SDL is a singleton family;
    current variable-only SDL retains its meaning; existing run/study records
    remain archival authority.
22. **Claims remain bounded.** A deterministic plan is not proof of backend
    equivalence, artifact availability, hidden-state recreation, or exact
    replay from a seed alone.

These criteria are adopted by ADR-084 and restated as formal invariants in
`specs/formal/scenario-variation-trial-realization/README.md`.

## References

Language and workflow specifications:

- CUE, [The CUE Language Specification](https://cuelang.org/docs/reference/spec/).
- Dhall, [Language Tour](https://docs.dhall-lang.org/tutorials/Language-Tour.html).
- Jsonnet, [Language Specification](https://jsonnet.org/ref/spec.html).
- HashiCorp, [Input Variables](https://developer.hashicorp.com/terraform/language/values/variables)
  and [`for_each`](https://developer.hashicorp.com/terraform/language/meta-arguments/for_each).
- Common Workflow Language,
  [Workflow Description v1.2.1](https://www.commonwl.org/v1.2/Workflow.html).

Simulation, experiment, and random-stream sources:

- Waltemath et al.,
  [Minimum Information About a Simulation Experiment](https://doi.org/10.1371/journal.pcbi.1001122),
  *PLoS Computational Biology* 7(4), 2011.
- COMBINE, [SED-ML specifications](https://sed-ml.org/specifications.html).
- Modelica Association,
  [System Structure and Parameterization](https://ssp-standard.org/docs/main/)
  and [FMI 3.0.2](https://fmi-standard.org/docs/3.0.2/).
- Zeigler,
  [Theory of Discrete Event Specified Models](https://doi.org/10.1080/03081078408934871),
  *International Journal of General Systems* 10(1), 1984.
- NumPy, [Random sampling](https://numpy.org/doc/stable/reference/random/),
  [compatibility policy](https://numpy.org/doc/stable/reference/random/compatibility.html),
  [NEP 19](https://numpy.org/neps/nep-0019-rng-policy.html), and
  [`SeedSequence`](https://numpy.org/doc/stable/reference/random/bit_generators/generated/numpy.random.SeedSequence.html).
- L'Ecuyer et al.,
  [An Object-Oriented Random-Number Package with Many Long Streams and Substreams](https://doi.org/10.1287/opre.50.6.1073.358),
  *Operations Research* 50(6), 2002.
- Salmon et al.,
  [Parallel Random Numbers: As Easy as 1, 2, 3](https://www.thesalmons.org/john/random123/papers/random123sc11.pdf),
  SC11, 2011.
- NIST,
  [Combinatorial Coverage Measurement](https://www.nist.gov/publications/combinatorial-coverage-measurement).

Cyber and adaptive-system sources:

- OASIS,
  [CACAO Security Playbooks 2.0](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.pdf)
  and [STIX 2.1](https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html).
- MITRE ATT&CK,
  [Data and Tools](https://attack.mitre.org/resources/attack-data-and-tools/)
  and [ATT&CK Navigator](https://github.com/mitre-attack/attack-navigator).
- Center for Threat-Informed Defense,
  [Attack Flow](https://github.com/center-for-threat-informed-defense/attack-flow).
- MITRE CALDERA,
  [Terminology](https://caldera.readthedocs.io/en/2.7/Learning-the-terminology.html)
  and [Objectives](https://caldera.readthedocs.io/en/latest/Objectives.html).
- Red Canary, [Atomic Red Team](https://github.com/redcanaryco/atomic-red-team).
- International Planning Competition,
  [PDDL reference](https://ipc06.icaps-conference.org/deterministic/pddl.html).
- Costa, Russo, and Armando,
  [Automating the Generation of Cyber Range Virtual Scenarios with VSDL](https://arxiv.org/abs/2001.06681),
  2020.
- Russo, Costa, and Armando,
  [Building Next Generation Cyber Ranges with CRACK](https://doi.org/10.1016/j.cose.2020.101837),
  *Computers & Security* 95, 2020.
- Hunicke and Chapman,
  [AI for Dynamic Difficulty Adjustment in Games](https://www.cs.northwestern.edu/~hunicke/pubs/Hamlet.pdf),
  AAAI workshop, 2004.
