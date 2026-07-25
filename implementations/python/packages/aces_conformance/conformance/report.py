"""Conformance case/report dataclasses, payload projection, and bounded claim."""

from __future__ import annotations

from dataclasses import dataclass, field

from aces_contracts.behavioral_relations import validate_behavioral_claim_binding
from aces_contracts.contracts import BehavioralClaimBindingModel
from aces_contracts.diagnostics import Diagnostic

from aces_conformance.conformance.diagnostics import _diagnostic_payload
from aces_conformance.realization import ExecutionBasis


@dataclass(frozen=True)
class ConformanceCaseResult:
    """Result for one fixture or probe case."""

    name: str
    contract_name: str
    valid: bool
    passed: bool
    diagnostics: tuple[Diagnostic, ...] = ()
    execution_basis: str = ExecutionBasis.FIXTURE_ONLY.value
    outcome: str = "passed"
    probe_kind: str | None = None
    probe_digest: str | None = None
    probe_set_digest: str | None = None
    envelope_digest: str | None = None
    configuration_digest: str | None = None
    target_binding: str | None = None
    expected_operations: tuple[str, ...] = ()
    accounted_operations: tuple[str, ...] = ()
    expected_observation_strengths: tuple[str, ...] = ()
    actual_observation_strengths: tuple[str, ...] = ()
    portable_state_unchanged: bool | None = None
    native_state_unchanged: bool | None = None
    cleanup_verified: bool | None = None
    residual_state: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Keep the closed outcome vocabulary aligned with the gating boolean."""

        if self.outcome == "passed" and not self.passed:
            object.__setattr__(self, "outcome", "failed")


@dataclass(frozen=True)
class BackendConformanceReport:
    """Machine-friendly conformance result.

    ``profile`` is the requested profile id as a string. When the request used
    a :class:`BackendCapabilityProfile` enum member, equality comparisons against
    that member still work because the enum is ``str``-valued. Carrying the
    field as ``str`` lets the runner accept (and report) profile ids that have
    no Python-side enum member.
    """

    profile: str
    passed: bool
    claim: BehavioralClaimBindingModel
    cases: tuple[ConformanceCaseResult, ...] = ()
    contract_versions: dict[str, str] = field(default_factory=dict)
    unsupported_contract_gaps: tuple[str, ...] = ()
    unsupported_capability_gaps: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    probe_set_digest: str | None = None
    native_conformance: bool = False


def backend_conformance_report_payload(report: BackendConformanceReport) -> dict[str, object]:
    """Render the single machine-readable backend conformance report projection."""

    return {
        "profile": report.profile,
        "passed": report.passed,
        "native_conformance": report.native_conformance,
        "probe_set_digest": report.probe_set_digest,
        "claim": report.claim.model_dump(mode="json"),
        "contract_versions": dict(report.contract_versions),
        "unsupported_contract_gaps": list(report.unsupported_contract_gaps),
        "unsupported_capability_gaps": list(report.unsupported_capability_gaps),
        "cases": [
            {
                "name": case.name,
                "contract_name": case.contract_name,
                "valid": case.valid,
                "passed": case.passed,
                "execution_basis": case.execution_basis,
                "outcome": case.outcome,
                "probe_kind": case.probe_kind,
                "probe_digest": case.probe_digest,
                "probe_set_digest": case.probe_set_digest,
                "envelope_digest": case.envelope_digest,
                "configuration_digest": case.configuration_digest,
                "target_binding": case.target_binding,
                "expected_operations": list(case.expected_operations),
                "accounted_operations": list(case.accounted_operations),
                "expected_observation_strengths": list(case.expected_observation_strengths),
                "actual_observation_strengths": list(case.actual_observation_strengths),
                "portable_state_unchanged": case.portable_state_unchanged,
                "native_state_unchanged": case.native_state_unchanged,
                "cleanup_verified": case.cleanup_verified,
                "residual_state": list(case.residual_state),
                "evidence_refs": list(case.evidence_refs),
                "diagnostics": [_diagnostic_payload(diag) for diag in case.diagnostics],
            }
            for case in report.cases
        ],
        "diagnostics": [_diagnostic_payload(diag) for diag in report.diagnostics],
    }


def _bounded_conformance_claim(
    *,
    profile: str,
    cases: tuple[ConformanceCaseResult, ...],
    left_carrier_ref: str,
) -> BehavioralClaimBindingModel:
    """Describe exactly what a conformance report's finite cases establish."""

    evidence_refs = [f"conformance-case:{case.contract_name}:{case.name}" for case in cases]
    binding = BehavioralClaimBindingModel(
        taxonomy_id="aces-behavioral-relations",
        taxonomy_revision="rev2",
        relation_id="bounded-probe-success",
        subject=f"Backend conformance for profile {profile}",
        left_carrier_ref=left_carrier_ref,
        right_carrier_ref=f"backend-profile:{profile}",
        observation_projection_ref="backend-conformance-case-report",
        observation_projection_revision="rev1",
        quantifier_scope="finite-cases",
        evidence_scope="finite",
        evidence_boundary=(
            f"The {len(cases)} named fixture and target-probe cases recorded in this report; "
            "no unexecuted input, trace, scheduler, strategy, or environment is quantified."
        ),
        assurance_status="tested",
        evidence_refs=evidence_refs,
        limitations=[
            "Case results are bounded by the selected profile, corpus revision, target, and execution environment."
        ],
        explicit_non_claims=[
            "Does not establish trace equivalence or bisimulation.",
            "Does not establish strategic, epistemic, probabilistic, timed, or partial-order equivalence.",
            (
                "Finite generated probes do not establish universal realizability "
                "outside the recorded envelope dimensions."
            ),
            "Fixture-only and hermetic-live execution do not establish native-daemon conformance.",
        ],
    )
    return validate_behavioral_claim_binding(binding)
