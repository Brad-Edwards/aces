"""Target conformance orchestration and profile inference."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from aces_backend_protocols.capabilities import (
    BackendManifest,
    observation_capability_contract_gaps,
    participant_runtime_capability_contract_gaps,
)
from aces_contracts.diagnostics import Diagnostic
from aces_contracts.realization_envelope import BackendRealizationEnvelopeModel
from aces_processor.reference import ScenarioInput
from aces_runtime.registry import RuntimeTarget

from aces_conformance.conformance.diagnostics import _diagnostic
from aces_conformance.conformance.fixture_suite import run_fixture_suite
from aces_conformance.conformance.profiles import (
    BackendCapabilityProfile,
    BackendProfileSelector,
    _resolve_required_contracts,
    _to_known_profile,
    _to_profile_id,
)
from aces_conformance.conformance.report import (
    BackendConformanceReport,
    ConformanceCaseResult,
    _bounded_conformance_claim,
)
from aces_conformance.conformance.target_probes import _target_adapter_cases
from aces_conformance.realization import (
    ExecutionBasis,
    RealizationConformanceHarness,
    RealizationProbeCase,
    run_realization_conformance,
)


def profile_for_manifest(manifest: BackendManifest) -> BackendCapabilityProfile:
    """Infer the nearest conformance profile for a backend manifest.

    A backend that declares orchestrator, evaluator, AND participant
    runtime capabilities is treated as ``FULL_REMOTE_CONTROL_PLANE``,
    so the default ``run_target_conformance`` path automatically
    validates the active target against the participant-episode contract
    family (RUN-311). Backends that only declare orchestrator/evaluator
    fall back to ``ORCHESTRATION_EVALUATION``; orchestrator-only
    declarations fall back to ``ORCHESTRATION_CAPABLE``; provisioner-only
    backends remain at ``PROVISIONING_ONLY``.
    """

    if manifest.has_orchestrator and manifest.has_evaluator and manifest.has_participant_runtime:
        profile = BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE
    elif manifest.has_orchestrator and manifest.has_evaluator:
        profile = BackendCapabilityProfile.ORCHESTRATION_EVALUATION
    elif manifest.has_orchestrator:
        profile = BackendCapabilityProfile.ORCHESTRATION_CAPABLE
    else:
        profile = BackendCapabilityProfile.PROVISIONING_ONLY
    return profile


def _capability_gaps(
    profile: BackendProfileSelector,
    target: RuntimeTarget,
) -> tuple[str, ...]:
    """Report runtime-surface gaps for known capability profiles only.

    Capability-gap checking depends on knowing the runtime surface contract
    for the profile (which roles must be present). For an unknown profile id
    — e.g. a freshly-published artifact whose runtime surface this
    implementation does not yet understand — we conservatively report no
    gaps and let the published contract set drive validation. This keeps the
    JSON corpus end-to-end authoritative for new profiles without requiring
    Python edits up front.
    """

    known = _to_known_profile(profile)
    if known is None:
        return ()
    gaps: list[str] = []
    if (
        known
        in {
            BackendCapabilityProfile.ORCHESTRATION_CAPABLE,
            BackendCapabilityProfile.ORCHESTRATION_EVALUATION,
            BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE,
        }
        and target.orchestrator is None
    ):
        gaps.append("orchestrator")
    if (
        known
        in {
            BackendCapabilityProfile.ORCHESTRATION_EVALUATION,
            BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE,
        }
        and target.evaluator is None
    ):
        gaps.append("evaluator")
    if known == BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE and target.participant_runtime is None:
        gaps.append("participant_runtime")
    return tuple(gaps)


def _declared_contract_gaps(
    profile: BackendProfileSelector,
    manifest: BackendManifest,
    *,
    profiles_root: Path | None = None,
) -> tuple[str, ...]:
    """Return the contract ids declared by ``profile`` that ``manifest`` is missing.

    Uses :func:`_resolve_required_contracts` so a missing/malformed/mislabeled
    profile artifact cannot raise out of the conformance boundary. When the
    profile fails to load, ``required`` is empty and the gap set is empty —
    the profile-load diagnostic is surfaced separately on the report by
    :func:`run_fixture_suite`, which the only caller (``run_target_conformance``)
    invokes for the same profile.
    """

    required, _profile_diagnostics = _resolve_required_contracts(profile, profiles_root=profiles_root)
    return tuple(sorted(required - manifest.supported_contract_versions))


@dataclass(frozen=True)
class _TargetConformanceOptions:
    profile: BackendProfileSelector | None = None
    root: Path | None = None
    profiles_root: Path | None = None
    reference_scenario: ScenarioInput | None = None
    realization_harness: RealizationConformanceHarness | None = None
    execution_basis: ExecutionBasis = ExecutionBasis.HERMETIC_LIVE
    realization_envelope: BackendRealizationEnvelopeModel | None = None
    observer_version: str = "aces-realization-observer/v1"
    native_conformance: bool = False


def _unknown_profile_report(
    target: RuntimeTarget,
    profile: BackendProfileSelector,
    fixture_report: BackendConformanceReport,
) -> BackendConformanceReport:
    profile_id = _to_profile_id(profile)
    diagnostics = (
        *fixture_report.diagnostics,
        _diagnostic(
            "conformance.profile-runtime-surface-unknown",
            profile_id,
            (
                f"Target conformance cannot certify profile {profile_id!r}: this "
                "implementation does not know the runtime-surface contract for the "
                "profile. Known runtime surfaces: "
                + ", ".join(sorted(item.value for item in BackendCapabilityProfile))
                + ". Use run_fixture_suite() for fixture-only validation, or extend "
                "BackendCapabilityProfile to declare this profile's runtime surfaces."
            ),
        ),
    )
    return BackendConformanceReport(
        profile=profile_id,
        passed=False,
        claim=_bounded_conformance_claim(
            profile=profile_id,
            cases=fixture_report.cases,
            left_carrier_ref=f"backend-target:{target.name}",
        ),
        cases=fixture_report.cases,
        contract_versions=dict(fixture_report.contract_versions),
        diagnostics=diagnostics,
    )


def _gap_diagnostics(
    target: RuntimeTarget,
    profile: BackendProfileSelector,
    contract_gaps: tuple[str, ...],
    surface_gaps: tuple[str, ...],
    claim_gaps: tuple[str, ...],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if contract_gaps:
        diagnostics.append(
            _diagnostic(
                "conformance.unsupported-contract-declaration",
                target.name,
                f"Target does not declare required contracts for {_to_profile_id(profile)}: {', '.join(contract_gaps)}",
            )
        )
    if surface_gaps:
        diagnostics.append(
            _diagnostic(
                "conformance.unsupported-surface",
                target.name,
                "Target is missing required runtime surfaces: " + ", ".join(surface_gaps),
            )
        )
    if claim_gaps:
        diagnostics.append(
            _diagnostic(
                "conformance.unsupported-capability-claim",
                target.name,
                "Target declares participant capability claims without required contract surfaces: "
                + "; ".join(claim_gaps),
            )
        )
    return diagnostics


def _known_profile_report(
    target: RuntimeTarget,
    profile: BackendProfileSelector,
    fixture_report: BackendConformanceReport,
    options: _TargetConformanceOptions,
) -> BackendConformanceReport:
    contract_gaps = _declared_contract_gaps(profile, target.manifest, profiles_root=options.profiles_root)
    surface_gaps = _capability_gaps(profile, target)
    claim_gaps = (
        *participant_runtime_capability_contract_gaps(target.manifest),
        *observation_capability_contract_gaps(target.manifest),
    )
    capability_gaps = (*surface_gaps, *claim_gaps)
    diagnostics = [
        *fixture_report.diagnostics,
        *_gap_diagnostics(target, profile, contract_gaps, surface_gaps, claim_gaps),
    ]
    adapter_cases = _target_adapter_cases(
        target,
        profile,
        reference_scenario=options.reference_scenario,
    )
    if target.manifest.realization_envelope is not None:
        adapter_cases = adapter_cases[:1]
    target_cases = tuple(replace(case, execution_basis=options.execution_basis.value) for case in adapter_cases)
    realization_run = run_realization_conformance(
        target,
        harness=options.realization_harness,
        execution_basis=options.execution_basis,
        envelope=options.realization_envelope,
        observer_version=options.observer_version,
        native_conformance=options.native_conformance,
    )
    realization_cases = tuple(_realization_case_result(case) for case in realization_run.cases)
    cases = (*fixture_report.cases, *target_cases, *realization_cases)
    passed = (
        fixture_report.passed
        and not contract_gaps
        and not capability_gaps
        and all(case.passed for case in (*target_cases, *realization_cases))
    )
    profile_id = _to_profile_id(profile)
    return BackendConformanceReport(
        profile=profile_id,
        passed=passed,
        claim=_bounded_conformance_claim(
            profile=profile_id,
            cases=cases,
            left_carrier_ref=realization_run.target_binding or f"backend-target:{target.name}",
        ),
        cases=cases,
        contract_versions=dict(fixture_report.contract_versions),
        unsupported_contract_gaps=contract_gaps,
        unsupported_capability_gaps=capability_gaps,
        diagnostics=tuple(diagnostics),
        probe_set_digest=realization_run.probe_set_digest,
        native_conformance=passed and realization_run.native_conformance,
    )


def run_target_conformance(target: RuntimeTarget, **option_values: Any) -> BackendConformanceReport:
    """Run fixture conformance for a target's declared runtime surface.

    ``root`` overrides the fixtures tree and ``profiles_root`` overrides the
    backend profile tree; both default to the canonical published roots.

    ``reference_scenario`` selects the scenario the hermetic target-adapter
    provisioning/snapshot probes drive (issue #663). It defaults to a generic linux-vm scenario
    (``_DEFAULT_CONFORMANCE_SCENARIO``). A fixed-topology emulation or bounded
    simulation backend that cannot realize the generic default supplies a
    scenario it *can* realize here, instead of being wrongly failed for not
    realizing an arbitrary hard-coded scenario; the probe still requires full
    realization (issue #606 mutation guard) of whichever scenario is selected.
    This is a temporary runner-parameter bridge superseded by the
    realizability-envelope design (#667/#668).
    """

    options = _TargetConformanceOptions(**option_values)
    effective_profile = options.profile or profile_for_manifest(target.manifest)
    fixture_report = run_fixture_suite(
        profile=effective_profile,
        root=options.root,
        profiles_root=options.profiles_root,
    )
    if any(diag.code == "conformance.profile-load-failed" for diag in fixture_report.diagnostics):
        return fixture_report
    if _to_known_profile(effective_profile) is None:
        return _unknown_profile_report(target, effective_profile, fixture_report)
    return _known_profile_report(target, effective_profile, fixture_report, options)


def _realization_case_result(case: RealizationProbeCase) -> ConformanceCaseResult:
    """Project the internal realization case into the one report case family."""

    return ConformanceCaseResult(**case.__dict__)
