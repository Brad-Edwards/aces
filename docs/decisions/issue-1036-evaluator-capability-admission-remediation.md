# Issue 1036 Evaluator Capability Admission Remediation

Date: 2026-08-11

Issue: #1036. Requirement: API-413.

This note records the narrow remediation for evaluator capability admission. It
does not add predicate families, evidence-channel kinds, truth outcomes, or an
SDL time-domain field.

## Gap Claim

Planner admission checked only evaluation sections and objective support. A
backend could therefore declare a narrow proposition evaluator and still admit
compiled propositions outside its predicate, quantifier, evidence-channel, or
time-domain surface. Runtime refusal remained conformant, but the plan falsely
suggested that the target could realize the scoring chain.

## Existing Surface Audit

- `EvaluatorCapabilities` already requires proposition evaluators to declare
  predicate families, quantifiers, all portable truth outcomes, evidence
  channels, time domains, and binding-provenance preservation.
- The compiler already emitted predicate kind, evaluation basis, and evidence
  requirement ids, but not quantifier or resolved channel kind.
- Authored `EvidenceRequirement.channel_refs` are opaque references, not
  evidence-channel kinds. Treating their identifiers as kinds would create a
  second, unsound resolution rule.
- An observed decided `PropositionTruthResultModel` requires governed temporal
  context. The current v1 evaluator manifests declare `scenario_time`; SDL does
  not yet carry a per-proposition evaluator time-domain requirement.
- The capability constructor already closes truth outcomes and provenance, so
  duplicating those invariant checks in the planner would add no scenario-
  dependent admission information.

## Lineage And Precedent

ADR-079 and
`specs/formal/objectives/proposition-and-assertion-semantics.md` require
unsupported evaluator semantics to be reported rather than weakened. The
provisioner and orchestrator planner gates already compare compiled, typed
requirements with manifest capability sets. This remediation follows that
boundary: compiler projection owns scenario requirements; planner admission
owns target comparison.

## Literature And Practice

The repository's issue-725 review grounds proposition evaluation in runtime
verification and W3C PROV: a monitor may decide only the predicate and evidence
semantics it actually implements, and provenance does not substitute for that
capability. Capability negotiation must therefore compare requested semantics
before execution rather than infer support from a coarse subsystem flag.

## Alternatives Considered

1. **Do nothing and rely on runtime `unsupported`.** Rejected because the
   planner would continue approving a known mismatch.
2. **Parse generic `PropositionRuntime.spec` dictionaries in the planner.**
   Rejected because it duplicates compiler interpretation and leaves channel
   references unresolved.
3. **Treat `channel_refs` as channel kinds.** Rejected because reference
   identity and modality are different contracts.
4. **Add a new SDL proposition time-domain field now.** Rejected as an
   unrequested language/schema change requiring a new governed profile.
5. **Compile a small typed capability projection and compare it in the
   planner.** Chosen because it reuses incumbent models and keeps the gate
   deterministic and backend-neutral.

## Chosen Architecture

`PropositionRuntime` carries the proposition quantifier, distinct evidence
channel kinds, unresolved evidence requirement ids, and the required evaluator
time domain. Compilation obtains channel kinds only from explicit
`EvidenceRequirement.channel` values. A cited requirement without an explicit
kind fails closed at planner admission.

For the existing v1 observed-truth contract, compilation projects
`scenario_time`; declared-state propositions carry no temporal requirement.
This binds the incumbent reference/stub manifest declaration without inventing
wall-clock semantics. A future authored per-proposition domain requires a
separate SDL/profile decision and will replace this v1 projection explicitly.

Fine-grained diagnostics run only when the evaluator admits the proposition
section; an unsupported section remains the controlling failure and is not
expanded into misleading per-field failures.

## Documentation Defense

The normative proposition specification now names the exact admission
comparison and the v1 temporal projection. API-413 traces the compiler,
planner, decision, and tests. No published wire schema changes because the new
fields are processor-internal compiled metadata.

## Verification Plan

- Compile an observed numeric/`any`/`log` proposition and prove that a
  Boolean/`all`/`api_response`/non-scenario-time evaluator receives four stable
  diagnostics.
- Prove the compiler projection retains the exact quantifier, channel, and
  time domain used by admission.
- Prove an opaque channel reference fails closed even when every other
  evaluator capability matches.
- Run the complete planner tests, policy checks, lint, and repository
  completion verification.
