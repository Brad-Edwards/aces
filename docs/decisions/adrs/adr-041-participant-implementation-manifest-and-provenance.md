# ADR-041: Participant Implementation Manifest and Provenance Surface

## Status

accepted

## Date

2026-05-29

## Context

API-420, ASR-527, and EXP-733 identify one boundary that the existing runtime
architecture names but did not materially implement: participant
implementations are apparatus, not SDL authored participants, backend
capabilities, processor capabilities, control-plane callers, or participant
episode state.

The repository already has established machinery for adjacent apparatus
surfaces:

- backend and processor manifests use closed `ContractModel` payloads,
  generated JSON Schemas, fixtures, and publication-manifest entries;
- concept-authority and controlled-vocabulary catalogs govern shared claim
  vocabularies;
- conformance reports structured `Diagnostic` objects instead of prose-only
  review results;
- runtime snapshots preserve live state and history, while explanatory docs
  keep participant implementation identity distinct from authored agents.

Without a participant implementation manifest, a run cannot tell whether a
human-control proxy, script, policy, agent, or comparable implementation was
used, which participant contracts it supports, what decision surface it saw, or
which tools and affordances it expected. Without a run-level provenance record,
the implementation and exposure policy actually selected for a run can only be
inferred from backend state, logs, or authored scenario intent, none of which is
the correct authority boundary.

## Decision

Define two versioned contracts:

1. `participant-implementation-manifest-v1` is the participant implementation
   declaration surface. It declares:

   - stable apparatus identity;
   - implementation kind;
   - supported participant implementation contract versions;
   - compatible participant runtime, processor, and backend surfaces;
   - concept bindings and constraints;
   - participant contracts, decision-surface modes, tool-affordance
     expectations, and exposure-policy kinds.

2. `participant-implementation-provenance-v1` is the run/apparatus selection
   record. It preserves, per participant address:

   - implementation identity;
   - selected manifest reference and digest;
   - selected configuration reference and digest when available;
   - selected decision-surface mode;
   - participant contract versions used for the run;
   - selected decision-surface exposure policy;
   - optional processor and backend manifest references for correlation.

Both contracts are closed-world Pydantic models under `aces_contracts`, are
published through generated JSON Schemas, have valid and invalid conformance
fixtures, and are registered with the conformance runner.

The new participant implementation vocabularies live in
`controlled-vocabularies-v1`:

- `participant-implementation-kinds`;
- `participant-implementation-contracts`;
- `participant-decision-surface-modes`;
- `participant-tool-affordance-expectations`;
- `participant-exposure-policy-kinds`.

The participant implementation manifest is separate from
`BackendManifestV2Model` and `ProcessorManifestV2Model`. Backend manifests
declare backend realization capability; processor manifests declare processing
capability; participant implementation manifests declare the apparatus that
chooses or relays participant decisions. The provenance record is separate from
authored SDL `agents`, participant episode lifecycle state, control-plane
identity, backend provenance, processor provenance, and derived evaluation
results.

## Security and Validation Gates

- Contract/model gate: both contracts are closed `ContractModel` payloads with
  generated JSON Schemas, conformance fixtures, and publication-manifest entries.
- Vocabulary gate: implementation kinds, participant implementation contracts,
  decision-surface modes, tool-affordance expectations, and exposure-policy
  kinds resolve through `controlled-vocabularies-v1`.
- Provenance gate: run-level records preserve selected manifest/config refs and
  digests instead of inferring implementation identity from authored SDL agents,
  backend state, or logs.
- Exposure gate: decision-surface mode and exposure-policy kind are explicit
  data so reviewers can distinguish what the participant implementation was
  allowed to see from what the authored scenario intended.
- Secret-handling gate: hidden context, credentials, prompts, and raw
  participant implementation configuration remain outside the portable
  manifest/provenance records; references and digests are the portable surface.
- Schema gate: generated schemas are derived from contract model sources and are
  not edited by hand.
- Conformance gate: valid and invalid fixtures exercise both the manifest and
  provenance contracts through the existing conformance runner.

## Guardrails

- Do not use SDL `agents` as evidence of which participant implementation ran.
- Do not treat backend `participant_runtime` capability or processor capability
  as participant implementation identity.
- Do not place participant implementation manifests under SDL runtime node
  inventory; this is apparatus metadata, not observed node state.
- Do not include hidden prompts, secret credentials, raw configuration payloads,
  or decision-surface contents in the portable manifest/provenance artifacts.
- Do not fork a participant-specific schema publication path; use the existing
  contract/schema/conformance machinery.

## Consequences

### Positive

- API-420 has a concrete apparatus declaration surface.
- ASR-527 can validate participant implementation claims and exposure-policy
  shape through the existing conformance machinery.
- EXP-733 has a typed run/apparatus provenance record for the implementation
  and decision surface actually used.
- Independent participant implementations can publish the same portable
  manifest shape without importing Python runtime internals.

### Negative

- The schema bundle and controlled-vocabulary catalog grow by two contracts and
  five vocabularies.
- Conformance fixtures now include participant implementation artifacts in
  addition to backend, processor, profile, and control-plane artifacts.

### Risks

- Treating SDL `agents` as proof of what implementation ran would weaken run
  provenance. The selected implementation must come from the provenance
  record.
- Treating backend `participant_runtime` capability as participant
  implementation identity would collapse runtime service support into the
  decision-making apparatus.
- Storing hidden context, credentials, prompts, or raw configuration in the
  manifest or provenance record would leak secret material through portable
  artifacts. The contract carries references and digests, not secret values.

## Non-Goals

- Redesign SDL participant framing.
- Redesign participant episode lifecycle contracts.
- Change control-plane authentication or authorization.
- Implement a live external participant runtime protocol.

## References

- [SDL Runtime Architecture](../../explain/sdl/runtime-architecture.md) and
  [SDL Semantic Validation](../../explain/sdl/validation.md).
- [Contract publication manifest](../../../contracts/schema-publication-manifest.json)
  and
  [Controlled vocabularies](../../../contracts/concept-authority/controlled-vocabularies-v1.json).
