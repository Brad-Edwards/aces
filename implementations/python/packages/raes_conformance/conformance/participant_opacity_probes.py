"""Runner-owned backend realization probes for participant predicate opacity."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Protocol

from raes_backend_protocols.capabilities import resolve_participant_feature_support
from raes_backend_protocols.manifest import backend_manifest_payload
from raes_contracts.behavioral_relation_profiles import load_behavioral_relation_profile
from raes_contracts.behavioral_relations import validate_behavioral_claim_binding
from raes_contracts.canonical import canonical_json_digest
from raes_contracts.contracts import BehavioralClaimBindingModel
from raes_contracts.vocabulary import ParticipantFeatureSupportLevel
from raes_runtime.registry import RuntimeTarget

from raes_conformance.conformance.diagnostics import _diagnostic, sanitized_failure_message
from raes_conformance.conformance.participant_policy_execution import _instrumented_target
from raes_conformance.conformance.report import ConformanceCaseResult

_FEATURE = "participant_predicate_opacity"
_RELATION = "participant-predicate-opacity"


class ParticipantOpacityRealizationOwner(StrEnum):
    """Who actually realizes the measured relation for a case."""

    DECLARATION_ONLY = "declaration-only"
    RUNTIME_MEDIATED = "runtime-mediated"
    BACKEND_NATIVE = "backend-native"


@dataclass(frozen=True)
class ParticipantOpacityProbeObservation:
    """Closed, non-secret observation transcript compared by the runner."""

    decision: str
    failure: str
    action_availability: str
    delivery: str
    omission: str
    retry: str
    logical_timing: str
    logical_order: str
    policy_release_effect: str
    external_effect: str
    payload_released: bool


@dataclass(frozen=True)
class ParticipantOpacityProbeCase:
    """Typed backend-specific inputs; no pass boolean or prebuilt report."""

    name: str
    profile_id: str
    profile_revision: str
    profile_digest: str
    actual_point_ref: str
    alternative_point_ref: str
    expected_observation: ParticipantOpacityProbeObservation
    realization_owner: ParticipantOpacityRealizationOwner
    execution_basis: str
    manifest_digest: str
    configuration_digest: str
    tool_digest: str
    environment_digest: str
    evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    explicit_non_claims: tuple[str, ...]


class ParticipantOpacityProbeHarness(Protocol):
    """Backend setup and observation adapter used by the generic runner."""

    probe_set_digest: str

    def cases(self, target: RuntimeTarget) -> tuple[ParticipantOpacityProbeCase, ...]: ...

    def observe(
        self,
        target: RuntimeTarget,
        case: ParticipantOpacityProbeCase,
        point_ref: str,
    ) -> ParticipantOpacityProbeObservation: ...


def _claim(
    *,
    case: ParticipantOpacityProbeCase,
    target: RuntimeTarget,
    axis: str,
    status: str,
    evidence_scope: str,
    evidence_refs: tuple[str, ...],
) -> BehavioralClaimBindingModel:
    profile = load_behavioral_relation_profile(case.profile_id)
    return validate_behavioral_claim_binding(
        BehavioralClaimBindingModel(
            taxonomy_id=profile.taxonomy_id,
            taxonomy_revision=profile.taxonomy_revision,
            relation_id=_RELATION,
            subject=f"Participant predicate opacity for backend target {target.name}",
            left_carrier_ref=profile.left_carrier_ref,
            observation_projection_ref=profile.observation_projection_ref,
            observation_projection_revision=profile.observation_projection_revision,
            relation_parameter_profile_ref=profile.profile_id,
            relation_parameter_profile_revision=profile.profile_revision,
            quantifier_scope="single-artifact" if evidence_scope == "structural" else "finite-cases",
            evidence_scope=evidence_scope,
            assurance_axis=axis,
            evidence_boundary=(
                "The exact named backend manifest declaration."
                if evidence_scope == "structural"
                else "The exact two finite profile points and complete observation transcript in this case."
            ),
            assurance_status=status,
            evidence_refs=list(evidence_refs),
            limitations=list(case.limitations),
            explicit_non_claims=list(case.explicit_non_claims),
        )
    )


def _declaration_claim(
    case: ParticipantOpacityProbeCase,
    target: RuntimeTarget,
    evidence_refs: tuple[str, ...],
) -> BehavioralClaimBindingModel:
    return _claim(
        case=case,
        target=target,
        axis="backend-declaration",
        status="declared",
        evidence_scope="structural",
        evidence_refs=evidence_refs,
    )


def _unsupported_case(target: RuntimeTarget) -> ConformanceCaseResult:
    profile = load_behavioral_relation_profile("participant-opacity-runtime-reference-v1")
    declaration = next(
        entry
        for entry in target.manifest.participant_runtime.feature_support  # type: ignore[union-attr]
        if entry.feature == _FEATURE
    )
    seed = ParticipantOpacityProbeCase(
        name="participant-opacity-backend-not-executed",
        profile_id=profile.profile_id,
        profile_revision=profile.profile_revision,
        profile_digest=profile.canonical_digest,
        actual_point_ref="possible-point:runtime-reference-protected",
        alternative_point_ref="possible-point:runtime-reference-complement",
        expected_observation=ParticipantOpacityProbeObservation("", "", "", "", "", "", "", "", "", "", False),
        realization_owner=ParticipantOpacityRealizationOwner.DECLARATION_ONLY,
        execution_basis="fixture-only",
        manifest_digest="",
        configuration_digest="",
        tool_digest="",
        environment_digest="",
        evidence_refs=declaration.evidence_refs,
        limitations=(*declaration.limitation_refs, "No backend probe was executed."),
        explicit_non_claims=("No backend realization or conformance is established.",),
    )
    return ConformanceCaseResult(
        name=seed.name,
        contract_name="backend-manifest-v2",
        valid=True,
        passed=False,
        outcome="unsupported",
        capability_feature=_FEATURE,
        declared_support_level=declaration.support_level.value,
        effective_support_level=None,
        evidence_refs=declaration.evidence_refs,
        limitations=seed.limitations,
        explicit_non_claims=seed.explicit_non_claims,
        claim_bindings=(_declaration_claim(seed, target, declaration.evidence_refs),),
        realization_owner=seed.realization_owner.value,
        profile_digest=profile.canonical_digest,
        manifest_digest=canonical_json_digest(backend_manifest_payload(target.manifest)),
    )


def _run_case(
    target: RuntimeTarget,
    harness: ParticipantOpacityProbeHarness,
    case: ParticipantOpacityProbeCase,
) -> ConformanceCaseResult:
    declaration = resolve_participant_feature_support(
        target.manifest,
        _FEATURE,
        required_level=ParticipantFeatureSupportLevel.BOUNDED,
    )
    assert declaration is not None
    profile = load_behavioral_relation_profile(case.profile_id)
    if case.profile_revision != profile.profile_revision or case.profile_digest != profile.canonical_digest:
        raise ValueError("probe profile coordinates do not match the governed profile")
    declared_profile = f"profile:{case.profile_id}@{case.profile_revision}"
    if declared_profile not in declaration.constraint_refs:
        raise ValueError("probe profile is outside the manifest's declared support constraints")
    actual_manifest_digest = canonical_json_digest(backend_manifest_payload(target.manifest))
    if case.manifest_digest != actual_manifest_digest:
        raise ValueError("probe manifest digest does not match the target declaration")
    if case.execution_basis not in {"fixture-only", "hermetic-live", "native-live"}:
        raise ValueError("probe execution basis is unsupported")
    claims = [_declaration_claim(case, target, declaration.evidence_refs)]
    diagnostics = []
    instrumented, counter = _instrumented_target(target)
    observations: list[ParticipantOpacityProbeObservation] = []
    try:
        for point_ref in (case.actual_point_ref, case.alternative_point_ref):
            observations.append(harness.observe(instrumented, case, point_ref))
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "conformance.participant-opacity-probe-rejected",
                case.name,
                sanitized_failure_message(exc),
            )
        )
    backend_calls = counter.calls if counter is not None else 0
    if backend_calls == 0:
        diagnostics.append(
            _diagnostic(
                "conformance.participant-opacity-backend-unobserved",
                case.name,
                "No participant-runtime call was observed; mediation cannot establish backend-native ownership.",
            )
        )
    if case.realization_owner is not ParticipantOpacityRealizationOwner.BACKEND_NATIVE:
        diagnostics.append(
            _diagnostic(
                "conformance.participant-opacity-realization-not-backend-native",
                case.name,
                "Runtime mediation or a declaration alone cannot establish backend-native realization.",
            )
        )
    observations_match = len(observations) == 2 and all(
        observation == case.expected_observation for observation in observations
    )
    if observations and not observations_match:
        diagnostics.append(
            _diagnostic(
                "conformance.participant-opacity-observation-mismatch",
                case.name,
                "The measured complete observation transcript differs across the governed opacity points.",
            )
        )
    passed = not diagnostics and observations_match
    if passed:
        claims.extend(
            (
                _claim(
                    case=case,
                    target=target,
                    axis="backend-realization",
                    status="realized",
                    evidence_scope="finite",
                    evidence_refs=case.evidence_refs,
                ),
                _claim(
                    case=case,
                    target=target,
                    axis="backend-conformance",
                    status="conformant",
                    evidence_scope="finite",
                    evidence_refs=case.evidence_refs,
                ),
            )
        )
    return ConformanceCaseResult(
        name=case.name,
        contract_name="backend-manifest-v2",
        valid=True,
        passed=passed,
        outcome="passed" if passed else "failed",
        probe_kind="participant-opacity-complete-transcript",
        probe_digest=canonical_json_digest(
            {
                "case": case.name,
                "observation_count": len(observations),
                "observations_match": observations_match,
                "backend_calls": backend_calls,
            }
        ),
        probe_set_digest=harness.probe_set_digest,
        configuration_digest=case.configuration_digest,
        evidence_refs=case.evidence_refs,
        capability_feature=_FEATURE,
        declared_support_level=declaration.support_level.value,
        effective_support_level=declaration.support_level.value if passed else None,
        finite_scope="The exact two named possible points and closed observation transcript.",
        limitations=case.limitations,
        explicit_non_claims=case.explicit_non_claims,
        diagnostics=tuple(diagnostics),
        claim_bindings=tuple(claims),
        realization_owner=case.realization_owner.value,
        profile_digest=case.profile_digest,
        manifest_digest=case.manifest_digest,
        tool_digest=case.tool_digest,
        environment_digest=case.environment_digest,
    )


def participant_opacity_cases(
    target: RuntimeTarget,
    harness: ParticipantOpacityProbeHarness | None,
) -> tuple[ConformanceCaseResult, ...]:
    """Run backend opacity probes or retain an explicit unsupported result."""

    capability = target.manifest.participant_runtime
    if capability is None:
        return ()
    declaration = next((entry for entry in capability.feature_support if entry.feature == _FEATURE), None)
    if declaration is None or declaration.support_level is ParticipantFeatureSupportLevel.UNSUPPORTED:
        return ()
    if harness is None:
        return (_unsupported_case(target),)
    try:
        probe_cases = harness.cases(target)
        if not probe_cases:
            case = _unsupported_case(target)
            return (
                replace(
                    case,
                    diagnostics=(
                        _diagnostic(
                            "conformance.participant-opacity-harness-empty",
                            _FEATURE,
                            "The opacity harness supplied no cases for a positive declaration.",
                        ),
                    ),
                ),
            )
        return tuple(_run_case(target, harness, case) for case in probe_cases)
    except Exception as exc:
        case = _unsupported_case(target)
        return (
            replace(
                case,
                diagnostics=(
                    _diagnostic(
                        "conformance.participant-opacity-harness-rejected",
                        _FEATURE,
                        sanitized_failure_message(exc),
                    ),
                ),
                outcome="failed",
            ),
        )


__all__ = [
    "ParticipantOpacityProbeCase",
    "ParticipantOpacityProbeHarness",
    "ParticipantOpacityProbeObservation",
    "ParticipantOpacityRealizationOwner",
    "participant_opacity_cases",
]
