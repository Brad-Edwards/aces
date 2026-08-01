"""Reference-backend adapter for the governed participant-opacity probes."""

from __future__ import annotations

from raes_backend_protocols.manifest import backend_manifest_payload
from raes_contracts.behavioral_relation_profiles import load_behavioral_relation_profile
from raes_contracts.canonical import canonical_json_digest
from raes_runtime.registry import RuntimeTarget

from raes_conformance.conformance.participant_opacity_probes import (
    ParticipantOpacityProbeCase,
    ParticipantOpacityProbeObservation,
    ParticipantOpacityRealizationOwner,
)

_PROFILE_ID = "participant-opacity-runtime-reference-v1"
_EXPECTED_OBSERVATION = ParticipantOpacityProbeObservation(
    decision="deny",
    failure="uniform-refusal",
    action_availability="denied",
    delivery="withheld",
    omission="recorded-at-governed-opportunity",
    retry="stable-replay",
    logical_timing="logical-bucket:contained",
    logical_order="stable-causal-order",
    policy_release_effect="contained",
    external_effect="none",
    payload_released=False,
)


class ReferenceParticipantOpacityHarness:
    """Supply reference-backend inputs while the generic runner owns verdicts."""

    probe_set_digest = canonical_json_digest({"probe_set": "participant-opacity-backend/rev1"})
    configuration_digest = canonical_json_digest({"configuration": "reference-emulation/default"})
    tool_digest = canonical_json_digest({"tool": "raes-conformance-participant-opacity/rev1"})
    environment_digest = canonical_json_digest({"environment": "in-process-reference"})

    def cases(self, target: RuntimeTarget) -> tuple[ParticipantOpacityProbeCase, ...]:
        profile = load_behavioral_relation_profile(_PROFILE_ID)
        return (
            ParticipantOpacityProbeCase(
                name="complete-observation-transcript",
                profile_id=profile.profile_id,
                profile_revision=profile.profile_revision,
                profile_digest=profile.canonical_digest,
                actual_point_ref="possible-point:runtime-reference-protected",
                alternative_point_ref="possible-point:runtime-reference-complement",
                expected_observation=_EXPECTED_OBSERVATION,
                realization_owner=ParticipantOpacityRealizationOwner.BACKEND_NATIVE,
                execution_basis="hermetic-live",
                manifest_digest=canonical_json_digest(backend_manifest_payload(target.manifest)),
                configuration_digest=self.configuration_digest,
                tool_digest=self.tool_digest,
                environment_digest=self.environment_digest,
                evidence_refs=("conformance:participant-opacity-backend:complete-transcript",),
                limitations=("Limited to the named finite reference profile and probe set.",),
                explicit_non_claims=(
                    "No universal backend opacity, proof, model check, or cross-backend equivalence.",
                ),
            ),
        )

    @staticmethod
    def observe(
        target: RuntimeTarget,
        case: ParticipantOpacityProbeCase,
        point_ref: str,
    ) -> ParticipantOpacityProbeObservation:
        runtime = target.participant_runtime
        if runtime is None:
            raise ValueError("reference participant runtime is unavailable")
        payload = runtime.participant_relation_probe(
            relation_id="participant-predicate-opacity",
            profile_id=case.profile_id,
            profile_revision=case.profile_revision,
            possible_point_ref=point_ref,
        )
        return ParticipantOpacityProbeObservation(**payload)


__all__ = ["ReferenceParticipantOpacityHarness"]
