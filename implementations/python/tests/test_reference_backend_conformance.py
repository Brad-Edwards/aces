"""RUN-314: acceptance bar -- full-profile conformance for the reference target."""

from __future__ import annotations

from raes_conformance.conformance import (
    BackendCapabilityProfile,
    run_target_conformance,
)
from raes_reference_backend import create_reference_backend_target


def test_reference_target_requires_opacity_probe_for_positive_declaration():
    report = run_target_conformance(create_reference_backend_target())

    assert report.profile == BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE
    assert report.passed is False
    opacity = next(case for case in report.cases if case.capability_feature == "participant_predicate_opacity")
    assert opacity.outcome == "unsupported"
    assert not report.unsupported_contract_gaps
    assert not report.unsupported_capability_gaps


def test_adapter_probes_pass_for_every_hermetic_backend():
    """The provisioning/snapshot adapter probes must stay envelope-neutral.

    An authored ``os`` in the default probe scenario becomes an exact SEM-218
    realization requirement no hermetic in-process backend can corroborate,
    which silently failed these probes for every honest backend when authored
    OS identity started carrying through realization. Pinning them keeps the
    default probe admissible on every declared envelope (issue #663's runner
    parameter stays the escape hatch for bounded backends).
    """

    from raes_backend_stubs.stubs import create_stub_target

    for target in (create_reference_backend_target(), create_stub_target()):
        report = run_target_conformance(target)
        cases = {case.name: case for case in report.cases}
        for name in ("target-provisioning", "target-snapshot"):
            assert cases[name].passed, (
                f"{name} must pass for an honest hermetic backend; "
                f"diagnostics: {[diag.message for diag in cases[name].diagnostics]}"
            )


def test_reference_target_drives_full_participant_probe_case_set():
    report = run_target_conformance(create_reference_backend_target())

    case_names = {case.name for case in report.cases}
    expected = {
        "participant-initialize",
        "participant-reset",
        "participant-terminate",
        "participant-restart",
        "participant-snapshot-consistent",
    }
    assert expected.issubset(case_names)
    for case in report.cases:
        if case.name in expected:
            assert case.passed, (
                f"participant probe case {case.name!r} must pass for the reference backend; "
                f"diagnostics: {[diag.message for diag in case.diagnostics]}"
            )


def test_reference_and_stub_realization_declarations_both_fail_closed_when_non_constructive():
    from raes_backend_stubs.stubs import create_stub_target

    reference_report = run_target_conformance(create_reference_backend_target())
    stub_report = run_target_conformance(create_stub_target())

    assert reference_report.profile == stub_report.profile
    assert reference_report.passed is False
    assert stub_report.passed is False
    assert any(case.name == "realization-envelope-constructive" for case in stub_report.cases)
    assert {case.name for case in reference_report.cases} - {case.name for case in stub_report.cases} == {
        "participant-opacity-backend-not-executed"
    }
