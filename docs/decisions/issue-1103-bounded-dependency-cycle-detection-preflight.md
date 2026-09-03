# Issue 1103 Bounded Dependency-Cycle Detection Preflight

Date: 2026-08-11

Issue: #1103. Requirement: RUN-303.

## Gap and Assurance Boundary

`dependency_cycles()` already implements a linear Tarjan traversal, but drives
its depth-first search with Python recursion. Interpreter stack depth therefore
tracks the longest dependency path. A sufficiently deep valid graph raises
`RecursionError` before the planner can return an order or a typed cycle
diagnostic.

The defect is unbounded call-stack consumption, not repeated whole-graph work.
The blocked assurance claim is that RUN-303 planning accepts dependency depth
bounded by available input memory rather than by an unrelated interpreter
recursion setting.

## Existing Surface and Lineage

- `raes_processor.semantics.planner.dependency_graph()` owns normalization and
  excludes unknown dependency references.
- `dependency_cycles()` owns strongly connected component detection and stable
  cycle ordering.
- `resource_dependency_cycles()` adapts compiled resources to those shared
  semantics; `planner.ordering._ordering_cycle_diagnostics()` owns the existing
  domain codes, addresses, and messages.
- `topological_dependency_order()` is iterative, but its residual-node result
  cannot replace the established component grouping and self-cycle behavior.
- The authoring validator's feature-cycle check is an earlier, distinct
  boundary. Moving compiled-resource cycle handling there would leave runtime
  dependency families uncovered.
- RUN-303, `specs/formal/planner/dependency-ordering.md`, and the published plan
  schemas define the existing observable contract. None requires amendment.

This correction extends the canonical planner family. It does not add another
dependency graph, validator, cycle model, or diagnostic surface.

## Literature and Practice

Tarjan defines strongly connected component discovery as a linear graph
algorithm: Robert Tarjan, "Depth-First Search and Linear Graph Algorithms,"
*SIAM Journal on Computing* 1(2), 1972,
<https://doi.org/10.1137/0201010>. Python documents the recursion limit as a
guard against C-stack overflow:
<https://docs.python.org/3/library/sys.html#sys.getrecursionlimit>.

An explicit DFS frame stack preserves Tarjan's index, low-link, and component
stack invariants while moving authored-depth consumption out of the interpreter
call stack. It retains O(V + E) graph work and O(V) auxiliary storage.

## Alternatives

1. **Do nothing or record evidence only.** Rejected because valid deep acyclic
   input can still abort planning without a typed result.
2. **Raise Python's recursion limit.** Rejected because the setting is
   process-global and interpreter-dependent and trades a model limit for C-stack
   risk.
3. **Use only the iterative topological sort.** Rejected because residual nodes
   do not preserve strongly connected components, self-cycle handling, or
   deterministic diagnostic grouping.
4. **Drive the existing Tarjan traversal with explicit frames.** Chosen because
   it removes authored-depth recursion without changing graph ownership or
   observable results.

## Chosen Boundary and Compatibility

Each frame holds the current node and its remaining dependency iterator. The
existing normalized graph, visit indices, low links, component stack, canonical
resource ordering, wrappers, and diagnostic rendering remain authoritative.
Unknown references remain excluded and self-cycles remain reportable.

No SDL model, parser alias, schema, serialized plan, public signature, runtime
lifecycle rule, version, or changelog changes. The unused local `_ordering_graph`
wrapper is removed because the shared semantic adapter already owns that work.

## Verification

- A deliberately simple recursive Tarjan oracle is independent of the explicit
  frame machinery.
- Every simple directed graph with one, two, or three nodes is compared with
  that oracle; a denser Hypothesis strategy extends the differential check to
  18 nodes, six edges per node, and 400 examples.
- Regressions cover unknown references, mapping and edge insertion order,
  self-cycles, multi-node components, a 5,000-edge acyclic chain, and a
  3,000-node cycle.
- Tests assert exact cycles and complete ordering, not machine-dependent timing.
- Planner regressions, branch-instrumented changed-code coverage, Ruff,
  repository policy, requirement governance, and the canonical verification
  graph remain required.

## Non-Goals

- Redefining dependency or refresh semantics.
- Adding an authored graph-size limit or a general graph-algorithm framework.
- Changing cycle diagnostics or topological residual-node behavior.
- Optimizing unrelated scheduler, timeout, control-plane, or backend code.
