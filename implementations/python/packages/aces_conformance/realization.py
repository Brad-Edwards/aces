"""Backend-neutral realization-honesty cases for the conformance report family."""

from __future__ import annotations

import hashlib
import json

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.realization_envelope import (
    BackendRealizationEnvelopeModel,
)
from aces_processor.reference import run_reference_processor
from aces_runtime.registry import RuntimeTarget
from aces_sdl.realization_envelope import (
    NegativeProbe,
    PositiveProbe,
    generate_negative_probes,
    generate_positive_probes,
)
from aces_sdl.scenario import Scenario

from ._realization_models import (
    ExecutionBasis,
    ExpectedRealizationObservation,
    ProbeOutcome,
    RealizationConformanceHarness,
    RealizationConformanceRun,
    RealizationProbeCase,
    RealizationProbeEvidence,
    RealizationProbeRequest,
    RealizationTransformation,
)
from ._realization_validation import (
    diagnostic as _diagnostic,
)
from ._realization_validation import (
    observation_diagnostics as _observation_diagnostics,
)
from ._realization_validation import (
    operation_inventory_diagnostics as _operation_inventory_diagnostics,
)
from ._realization_validation import (
    required_strengths as _required_strengths,
)
from ._realization_validation import (
    transformation_diagnostics as _transformation_diagnostics,
)


def _payload_digest(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _probe_set_digest(positives: tuple[PositiveProbe, ...], negatives: tuple[NegativeProbe, ...]) -> str:
    material = [probe.digest for probe in positives] + [_payload_digest(probe.payload) for probe in negatives]
    return _payload_digest({"probe_digests": material})


def _target_binding(target: RuntimeTarget, envelope: BackendRealizationEnvelopeModel) -> str:
    return (
        f"backend-target:{target.manifest.name}@{target.manifest.version};"
        f"mode={envelope.configuration.mode};envelope={envelope.digest};"
        f"configuration={envelope.configuration.configuration_digest}"
    )


def _base_case(
    *,
    name: str,
    basis: ExecutionBasis,
    outcome: ProbeOutcome,
    passed: bool,
    diagnostics: tuple[Diagnostic, ...],
    envelope: BackendRealizationEnvelopeModel,
    target_binding: str,
    probe_set_digest: str | None = None,
) -> RealizationProbeCase:
    return RealizationProbeCase(
        name=name,
        contract_name="realization-envelope-v1",
        valid=True,
        passed=passed,
        diagnostics=diagnostics,
        execution_basis=basis.value,
        outcome=outcome.value,
        probe_set_digest=probe_set_digest,
        envelope_digest=envelope.digest,
        configuration_digest=envelope.configuration.configuration_digest,
        target_binding=target_binding,
    )


def _mismatch_run(
    target: RuntimeTarget,
    offered: BackendRealizationEnvelopeModel,
    selected: BackendRealizationEnvelopeModel,
    basis: ExecutionBasis,
) -> RealizationConformanceRun:
    binding = _target_binding(target, offered)
    case = _base_case(
        name="realization-envelope-binding",
        basis=basis,
        outcome=ProbeOutcome.FAILED,
        passed=False,
        diagnostics=(
            _diagnostic(
                "conformance.realization-envelope-mismatch",
                "runtime.target.realization-envelope",
                "Selected realization envelope does not match the target configuration identity.",
            ),
        ),
        envelope=selected,
        target_binding=binding,
    )
    return RealizationConformanceRun(cases=(case,), target_binding=binding)


def _constructive_failure(
    target: RuntimeTarget,
    envelope: BackendRealizationEnvelopeModel,
    basis: ExecutionBasis,
    diagnostics: tuple[Diagnostic, ...],
) -> RealizationConformanceRun:
    binding = _target_binding(target, envelope)
    case = _base_case(
        name="realization-envelope-constructive",
        basis=basis,
        outcome=ProbeOutcome.UNSUPPORTED,
        passed=False,
        diagnostics=diagnostics,
        envelope=envelope,
        target_binding=binding,
    )
    return RealizationConformanceRun(cases=(case,), target_binding=binding)


def _positive_case(
    *,
    index: int,
    probe: PositiveProbe,
    probe_set_digest: str,
    target: RuntimeTarget,
    envelope: BackendRealizationEnvelopeModel,
    harness: RealizationConformanceHarness,
    basis: ExecutionBasis,
    observer_version: str,
) -> RealizationProbeCase:
    binding = _target_binding(target, envelope)
    try:
        plan = run_reference_processor(
            Scenario.model_validate(probe.payload), target.manifest
        ).execution_plan.provisioning
    except Exception:
        return _base_case(
            name=f"realization-positive-{index}",
            basis=basis,
            outcome=ProbeOutcome.FAILED,
            passed=False,
            diagnostics=(
                _diagnostic(
                    "conformance.positive-probe-plan-failed",
                    probe.path,
                    "The generated positive probe did not pass the ordinary processor and planning boundary.",
                ),
            ),
            envelope=envelope,
            target_binding=binding,
            probe_set_digest=probe_set_digest,
        )
    request = RealizationProbeRequest(
        probe_digest=probe.digest,
        probe_kind="positive",
        payload=probe.payload,
        negative=False,
        provisioning_plan=plan,
        envelope_digest=envelope.digest,
        configuration_digest=envelope.configuration.configuration_digest,
        observer_version=observer_version,
    )
    evidence = harness.execute(request)
    strengths = _required_strengths(envelope)
    diagnostics = list(evidence.diagnostics)
    if not evidence.accepted:
        diagnostics.append(
            _diagnostic(
                "conformance.positive-probe-rejected",
                probe.path,
                "The in-envelope positive probe was rejected.",
            )
        )
    diagnostics.extend(_operation_inventory_diagnostics(plan, evidence, strengths))
    diagnostics.extend(_observation_diagnostics(request, evidence, strengths))
    diagnostics.extend(_transformation_diagnostics(evidence))
    if plan.actionable_operations and evidence.portable_state_before == evidence.portable_state_after:
        diagnostics.append(
            _diagnostic(
                "conformance.positive-portable-state-unchanged",
                "runtime.snapshot",
                "A successful actionable positive probe did not mutate portable state.",
            )
        )
    if not evidence.cleanup_verified:
        diagnostics.append(
            _diagnostic(
                "conformance.cleanup-unverified",
                "runtime.cleanup",
                "Probe cleanup was not independently verified.",
            )
        )
    if evidence.residual_state:
        diagnostics.append(
            _diagnostic(
                "conformance.residual-state",
                "runtime.cleanup",
                "Probe cleanup left residual owned state.",
            )
        )
    expected_operations = tuple(operation.address for operation in plan.actionable_operations)
    return RealizationProbeCase(
        name=f"realization-positive-{index}",
        contract_name="realization-envelope-v1",
        valid=True,
        passed=not diagnostics,
        diagnostics=tuple(diagnostics),
        execution_basis=basis.value,
        outcome=(ProbeOutcome.PASSED if not diagnostics else ProbeOutcome.FAILED).value,
        probe_kind="positive",
        probe_digest=probe.digest,
        probe_set_digest=probe_set_digest,
        envelope_digest=envelope.digest,
        configuration_digest=envelope.configuration.configuration_digest,
        target_binding=binding,
        expected_operations=expected_operations,
        accounted_operations=evidence.accounted_operations,
        expected_observation_strengths=tuple(sorted({strength.value for strength in strengths.values()})),
        actual_observation_strengths=tuple(sorted({item.source.value for item in evidence.observations})),
        portable_state_unchanged=evidence.portable_state_before == evidence.portable_state_after,
        native_state_unchanged=evidence.native_state_before == evidence.native_state_after,
        cleanup_verified=evidence.cleanup_verified,
        residual_state=evidence.residual_state,
        evidence_refs=evidence.evidence_refs,
    )


def _negative_case(
    *,
    index: int,
    probe: NegativeProbe,
    probe_set_digest: str,
    target: RuntimeTarget,
    envelope: BackendRealizationEnvelopeModel,
    harness: RealizationConformanceHarness,
    basis: ExecutionBasis,
    observer_version: str,
) -> RealizationProbeCase:
    digest = _payload_digest(probe.payload)
    request = RealizationProbeRequest(
        probe_digest=digest,
        probe_kind="negative",
        payload=probe.payload,
        negative=True,
        provisioning_plan=None,
        envelope_digest=envelope.digest,
        configuration_digest=envelope.configuration.configuration_digest,
        observer_version=observer_version,
    )
    evidence = harness.execute(request)
    diagnostics = list(evidence.diagnostics)
    if evidence.accepted:
        diagnostics.append(
            _diagnostic(
                "conformance.negative-probe-accepted",
                probe.path,
                "The out-of-envelope probe was accepted.",
            )
        )
    if evidence.driver_invoked:
        diagnostics.append(
            _diagnostic(
                "conformance.negative-driver-invoked",
                probe.path,
                "The out-of-envelope probe reached driver invocation.",
            )
        )
    if evidence.native_mutated:
        diagnostics.append(
            _diagnostic(
                "conformance.negative-native-mutation",
                probe.path,
                "The out-of-envelope probe caused native mutation.",
            )
        )
    portable_unchanged = evidence.portable_state_before == evidence.portable_state_after
    native_unchanged = evidence.native_state_before == evidence.native_state_after
    if not portable_unchanged:
        diagnostics.append(
            _diagnostic(
                "conformance.negative-portable-state-mutated",
                probe.path,
                "The out-of-envelope probe changed portable runtime state.",
            )
        )
    if not native_unchanged:
        diagnostics.append(
            _diagnostic(
                "conformance.negative-native-state-mutated",
                probe.path,
                "The out-of-envelope probe changed independently inventoried native state.",
            )
        )
    if not evidence.cleanup_verified:
        diagnostics.append(
            _diagnostic(
                "conformance.cleanup-unverified",
                "runtime.cleanup",
                "Negative-probe cleanup was not independently verified.",
            )
        )
    if evidence.residual_state:
        diagnostics.append(
            _diagnostic(
                "conformance.residual-state",
                "runtime.cleanup",
                "Negative-probe cleanup left residual owned state.",
            )
        )
    binding = _target_binding(target, envelope)
    return RealizationProbeCase(
        name=f"realization-negative-{index}",
        contract_name="realization-envelope-v1",
        valid=True,
        passed=not diagnostics,
        diagnostics=tuple(diagnostics),
        execution_basis=basis.value,
        outcome=(ProbeOutcome.PASSED if not diagnostics else ProbeOutcome.FAILED).value,
        probe_kind="negative",
        probe_digest=digest,
        probe_set_digest=probe_set_digest,
        envelope_digest=envelope.digest,
        configuration_digest=envelope.configuration.configuration_digest,
        target_binding=binding,
        portable_state_unchanged=portable_unchanged,
        native_state_unchanged=native_unchanged,
        cleanup_verified=evidence.cleanup_verified,
        residual_state=evidence.residual_state,
        evidence_refs=evidence.evidence_refs,
    )


def run_realization_conformance(
    target: RuntimeTarget,
    *,
    harness: RealizationConformanceHarness | None,
    execution_basis: ExecutionBasis,
    envelope: BackendRealizationEnvelopeModel | None = None,
    observer_version: str = "aces-realization-observer/v1",
    native_conformance: bool = False,
) -> RealizationConformanceRun:
    """Return realization-honesty cases for one exact target configuration."""

    offered = target.manifest.realization_envelope
    if offered is None:
        return RealizationConformanceRun()
    selected = envelope or offered
    if selected.identity != offered.identity:
        return _mismatch_run(target, offered, selected, execution_basis)
    positive, positive_diagnostics = generate_positive_probes(selected.expression)
    negative, negative_diagnostics = generate_negative_probes(selected.expression)
    if positive_diagnostics or negative_diagnostics or not positive:
        diagnostics = tuple((*positive_diagnostics, *negative_diagnostics))
        return _constructive_failure(target, selected, execution_basis, diagnostics)
    probe_digest = _probe_set_digest(positive, negative)
    binding = _target_binding(target, selected)
    if harness is None:
        case = _base_case(
            name="realization-harness-required",
            basis=execution_basis,
            outcome=ProbeOutcome.UNSUPPORTED,
            passed=False,
            diagnostics=(
                _diagnostic(
                    "conformance.realization-harness-missing",
                    "runtime.target.realization-conformance",
                    "Realization certification requires an independent execution and observation harness.",
                ),
            ),
            envelope=selected,
            target_binding=binding,
            probe_set_digest=probe_digest,
        )
        return RealizationConformanceRun(cases=(case,), probe_set_digest=probe_digest, target_binding=binding)
    cases = [
        _positive_case(
            index=index,
            probe=probe,
            probe_set_digest=probe_digest,
            target=target,
            envelope=selected,
            harness=harness,
            basis=execution_basis,
            observer_version=observer_version,
        )
        for index, probe in enumerate(positive, start=1)
    ]
    cases.extend(
        _negative_case(
            index=index,
            probe=probe,
            probe_set_digest=probe_digest,
            target=target,
            envelope=selected,
            harness=harness,
            basis=execution_basis,
            observer_version=observer_version,
        )
        for index, probe in enumerate(negative, start=1)
    )
    if native_conformance and execution_basis is not ExecutionBasis.NATIVE_LIVE:
        cases.append(
            _base_case(
                name="native-conformance-basis",
                basis=execution_basis,
                outcome=ProbeOutcome.FAILED,
                passed=False,
                diagnostics=(
                    _diagnostic(
                        "conformance.native-basis-required",
                        "runtime.target.execution-basis",
                        "Only native-live execution may support a native conformance claim.",
                    ),
                ),
                envelope=selected,
                target_binding=binding,
                probe_set_digest=probe_digest,
            )
        )
    passed = all(case.passed for case in cases)
    return RealizationConformanceRun(
        cases=tuple(cases),
        probe_set_digest=probe_digest,
        target_binding=binding,
        native_conformance=native_conformance and execution_basis is ExecutionBasis.NATIVE_LIVE and passed,
    )


__all__ = [
    "ExecutionBasis",
    "ExpectedRealizationObservation",
    "ProbeOutcome",
    "RealizationConformanceHarness",
    "RealizationProbeCase",
    "RealizationProbeEvidence",
    "RealizationProbeRequest",
    "RealizationTransformation",
    "run_realization_conformance",
]
