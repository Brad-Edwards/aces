# Runtime Contract Semantics

This directory holds the formal artifacts for portable runtime result contracts.

## Scope

- typed workflow execution envelopes
- typed workflow step execution state
- typed evaluator result envelopes
- typed evaluator history streams
- backend participant capability declarations
- manager-side validation of backend workflow results
- manager-side validation of backend evaluator results

## API-405 - Backend Participant Capability Declarations

`API-405` requires backend manifests to declare the participant roles,
behavior features, and interaction features a participant runtime supports.
The declaration lives on `backend-manifest/v2`
`capabilities.participant_runtime`, because the support claim belongs to the
backend apparatus, not to authored participant assignments, control-plane
caller roles, or mutable episode state.

The standard vocabulary is intentionally lineage-bound:

- participant roles reuse the existing exercise-role surface (`white`,
  `green`, `red`, and `blue`) from declarative participant framing;
- behavior features name the ACES participant-semantics surfaces established
  by `lineage.md`, ADR-022, and `specs/formal/participant-semantics/`:
  action contracts, preconditions, effects, observation boundaries, behavior
  history, state transitions, failure classes, attribution support, temporal
  contracts, and outcome interpretation;
- interaction features match the SEM-209 classes: coordination, contention,
  interference, and shared-state change.

This follows the primary and adjacent literature without adopting one external
API as the authority. Gym/Gymnasium, PettingZoo, OpenSpiel, POMDP/POSG work,
CybORG, CyberBattleSim, CyGIL, CALDERA, and benchmark-methodology critiques
motivate explicit action, observation, episode, role, interaction,
provenance, and outcome surfaces. Backend manifests therefore make a checkable
support claim instead of implying support from runtime presence alone.

The controlled vocabulary extension policy is governed extension. Backend
specific role or feature terms must use an `x-<owner>:<term>` identifier and
remain bound through `concept_bindings`.

## Implementation Mapping

- shared result constraints: `implementations/python/packages/aces_processor/semantics/workflow.py`
- typed result models: `implementations/python/packages/aces_processor/models.py`
- manager contract validation: `implementations/python/packages/aces_processor/manager.py`
- backend example: `implementations/python/packages/aces_backend_stubs/stubs.py`
- participant capability contract model:
  `implementations/python/packages/aces_contracts/contracts.py`
- participant capability runtime declaration:
  `implementations/python/packages/aces_backend_protocols/capabilities.py`
- backend manifest renderer:
  `implementations/python/packages/aces_backend_protocols/manifest.py`
- governed vocabulary authority:
  `contracts/concept-authority/controlled-vocabularies-v1.json`

## Tests

- `implementations/python/tests/test_runtime_manager.py`
- `implementations/python/tests/test_runtime_models.py`
- `implementations/python/tests/test_runtime_contracts.py`
- `implementations/python/tests/test_backend_manifest.py`
