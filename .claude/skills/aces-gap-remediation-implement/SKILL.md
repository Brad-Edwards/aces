---
name: aces-gap-remediation-implement
description: Architecture-first overlay for remediating ACES/APTL gaps, especially gaps found by the ACES asset inventory capture methodology. Use before normal Ground Control /implement work when a gap may require new or changed SDL/runtime semantics, schemas, validators, ADRs, docs, capture mappings, or cross-repo ACES/APTL behavior. Forces whole-surface review, lineage and primary-literature grounding, peer-review-grade justification, and then delegates to the repo's standard Ground Control implement workflow.
---

# ACES Gap Remediation Implement

Use this skill as an overlay before the normal Ground Control implementation
lane. It does not replace `/implement`; it supplies the architecture and
documentation obligations that must be carried into `/implement`.

The expected review bar is academic peer review for tier-1 publication: a
reviewer must be able to reconstruct why the remediation exists, why existing
surfaces were insufficient, why the chosen design is not duplicative, and how
the implementation follows established ACES lineage and relevant external
practice.

## Operating Rule

Do not edit files before issue and branch hygiene is satisfied.

- If no GitHub issue or Ground Control requirement exists, create or request one
  before implementation work.
- Branch from the repo's configured base branch, not from an unrelated in-flight
  PR branch.
- Use the repo's `AGENTS.md`, `.ground-control.yaml`, and normal Ground Control
  `/implement <issue>` workflow for status labels, plans, reviews, verification,
  commits, PR body, CI/Sonar, traceability, and final reporting.
- Carry the remediation brief below into the implementation plan, ADR/docs, and
  PR traceability. Do not leave it only in chat.

## Remediation Brief

Before invoking `/implement`, produce or add to the issue a brief with these
sections:

1. **Gap Claim**: captured fact, discovery vantage, evidence paths, affected
   scenario/asset, and the assurance claim that current ACES/APTL cannot make.
2. **Existing Surface Audit**: SDL sections, runtime subdomains, schemas,
   validators, parser aliases, module refs, docs, examples, and related issues
   checked. State why each near match is insufficient.
3. **Lineage and Precedent**: relevant ACES lineage, precedents, ADRs, prior
   issues/PRs, and downstream APTL usage. Explain whether the gap extends an
   existing family or requires a new one.
4. **Literature and Practice**: primary literature and core/adjacent practice
   reviewed for the semantic family. Prefer standards, papers, vendor-neutral
   specs, and canonical project docs over secondary summaries. Include citations
   or stable links in the issue or docs.
5. **Alternatives**: at least two plausible encodings or designs, including the
   "do nothing / evidence-only" option. Reject local force-fits explicitly.
6. **Chosen Architecture**: the minimal canonical remediation, ownership
   boundary, naming, identity model, validation rules, and compatibility impact.
7. **Documentation Defense**: ADR/docs that must explain the choice, rejected
   alternatives, limitations, validation gates, lineage, and evidence boundary.
8. **Verification Plan**: tests, schema generation, semantic validation,
   examples, capture-ledger impact, and traceability links required for review.

## Whole-Surface Gate

Run this gate before choosing a design.

- Search existing SDL sections, runtime modules, validators, generated schemas,
  module alias/ref machinery, examples, docs, ADRs, lineage, precedents, open
  issues, and recently merged PRs.
- Inspect adjacent domains, not just the local file that seems convenient. For
  inventory gaps, include runtime identity, software, filesystem, network,
  service, sensor, manager, content, evidence, and source/provenance families as
  applicable.
- Check whether the fact is scenario state, delivery infrastructure, evidence,
  control-plane machinery, downstream APTL consumption, or an ACES SDL
  expression gap.
- Treat duplicate parallel surfaces as a design failure. Extend the established
  family when the semantics belong there; create a new family only when the
  lineage and literature justify a distinct boundary.

## Anti-Local-Optimization Gates

Reject an implementation plan if any gate fails.

- **No smuggling**: do not hide typed semantics in descriptions, tags, settings,
  generic relationships, or arbitrary key/value fields.
- **No shallow schema pass**: do not choose the representation that validates
  while changing the meaning of the captured fact.
- **No downstream-only fix**: do not patch APTL consumption when ACES lacks the
  needed expression surface.
- **No docs-free surface**: every new or changed semantic surface needs public
  rationale in ADR/docs, not just tests.
- **No duplicate family**: do not add a second model for a concept already owned
  by an existing section without documenting why extension is impossible.

## Delegation to Ground Control

After the remediation brief is ready:

1. Invoke the normal Ground Control `/implement` workflow for the issue or UID.
2. Feed the brief into architecture preflight and the implementation plan.
3. During implementation, update the public docs/ADRs so the brief's reasoning
   survives outside the chat.
4. Verify with the repo's configured completion command and required review
   gates.
5. Ensure PR traceability names the issue/requirement, code, tests, specs, and
   ADR/docs that implement and justify the remediation.
6. At the end, surface workflow-improvement recommendations to the user. Include
   repeated friction, missing policy/tooling, confusing docs, review gaps, and
   places where the capture or remediation workflow caused avoidable rework.
   Keep these recommendations separate from the implementation summary so the
   user can decide whether to file follow-up work.

If the normal `/implement` workflow conflicts with this skill, the repo policy
and Ground Control workflow control mechanics; this skill controls the
architecture and review-standard content that must accompany them.

## Documentation Bar

For semantic remediation, docs must answer:

- What fact or assurance claim was blocked?
- Which existing surfaces were checked?
- What lineage, prior art, and external practice informed the boundary?
- Why is the chosen surface canonical rather than a local workaround?
- What alternatives were rejected and why?
- What does the surface intentionally not claim?
- Which validation gates keep future encodings from drifting?

Do not finish with only code/tests if a peer reviewer would still need chat
history to understand the design.
