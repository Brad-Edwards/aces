# Adversarial Participant Control Current-State Assessment

Date: 2026-07-30

Parent issue: [#812](https://github.com/OpenRAE/rae/issues/812).

## Method

The assessment compared primary research and implementation sources with the
current RAES semantic, contract, runtime, backend, experiment, evidence, and
documentation authorities. The canonical structured disposition is in
[`implementation-program.json`](implementation-program.json).

## Primary-source findings

| Source | Adopt | RAES boundary |
| --- | --- | --- |
| [FIDES](https://arxiv.org/abs/2505.23643) | Independent confidentiality/integrity labels, conservative propagation, deterministic action policy, explicit release. | Generalize to typed participants and sinks; do not import its planner or LLM message model. |
| [CaMeL](https://arxiv.org/abs/2503.18813) | Trusted-control/untrusted-data separation, quarantine, typed extraction, capability-restricted flows. | Quarantine and model topology are apparatus capabilities, not portable prompt semantics or endorsement. |
| [SAMOS](https://research.ibm.com/publications/securing-mcp-based-agent-workflows) | Intercept tool calls and retain session flow state so permitted calls cannot compose into leakage. | MCP is optional; RUN-319 and the final effect/disclosure sink own the portable boundary. |
| [AgentDojo](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) | Separate utility and security; use dynamic tasks and adaptive indirect injection. | Reuse experiment contracts; benchmark objects and results remain profile-bounded. |
| [AI Control](https://arxiv.org/abs/2312.06942) | Evaluate intentionally subverting policies, trusted editing, untrusted monitoring, limited trusted labor, audit, and collusion. | Trusted/untrusted are declared roles and assumptions, not proof about a model or human. |
| [ControlArena](https://control-arena.aisi.org.uk/) | Explicit honest/attack modes, main/side objectives, visibility, defer/shutdown protocols, safety/usefulness, and trajectories. | Reuse RAES experiment authorities; do not copy its policy, monitor, scorer, or trajectory hierarchy. |
| [runtime shielding](https://arxiv.org/abs/1501.02573) | Mediate a declared property at runtime before unsafe output is realized. | Only a complete deterministic sink policy may be called shielding; a heuristic monitor is not authorization. |
| [capability authority control](https://doi.org/10.4230/LIPIcs.ECOOP.2017.20) | Give components only required authority and avoid ambient authority. | Reuse action arguments, participant capabilities, identity binding, and API-407; capability restriction does not replace IFC. |

The shared lesson is complete mediation of declared explicit flows at the last
enforceable boundary. None of the sources establishes model alignment, safe
private reasoning, monitor honesty, or protection from undeclared covert
channels.

## Existing RAES coverage

- ADR-085, ADR-095, SEM-230, and SEM-231 define exact-cut
  participant-relative flow, projection, declassification, memory, adaptive
  strategies, supervisor visibility, coalitions, and honest claim boundaries.
- ACT-617, API-409, RUN-310, and action admission separate proposals,
  approvals, denials, direction, intervention, handoff, override,
  cancellation, admission, and execution.
- API-423 and RUN-319 define typed crossing stages, independent gates,
  effective capability support, append-only histories, idempotency, replay,
  and atomic persistence.
- Runtime facts already carry typed observation, derived, tool-result, and
  secret-reference sources, sensitivity, scope, audience, provenance, and sink
  restrictions.
- API-407 separates declared support, effective strength, downgrade,
  realization, and bounded conformance.
- Experiment task, protocol, study, run, apparatus, evidence, measure, and
  traceability contracts can host control evaluations without a new benchmark
  hierarchy.
- ASR-535 already separates bounded semantic falsification, runtime evidence,
  backend conformance, model checking, proof, and nonclaims.

## Gaps

Before issue #812, RAES has no authority that:

1. carries independent confidentiality and integrity coordinates
   conservatively through every relevant typed carrier;
2. distinguishes integrity endorsement from confidentiality declassification
   and both from approval, admission, authentication, and authorization;
3. rechecks effective flow at the final external-action and disclosure sink;
4. treats intentional subversion, policy-aware adaptation, audit-budget
   exhaustion, collusion, and correlated monitor failure as explicit
   evaluation variables; or
5. binds honest/attack mode, objectives, monitor topology, intervention
   protocol, memory, replay, safety, usefulness, cost, uncertainty, and
   limitations in one revisioned evaluation profile.

## Adopted response

ADR-101 and the formal authority add two DRAFT owners:

- SEM-233 owns the participant-neutral flow-policy profile and final-sink
  semantics.
- ASR-536 owns the intentional-subversion evaluation profile.

Issue #812 also opens six ordered implementation issues. It does not alter
published schemas or runtime behavior and does not claim either DRAFT
requirement is satisfied.
