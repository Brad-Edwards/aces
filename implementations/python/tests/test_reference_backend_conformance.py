"""RUN-314: acceptance bar -- full-profile conformance for the reference target."""

from __future__ import annotations

from raes_reference_backend import create_reference_backend_target

from raes_conformance.conformance import (
    BackendCapabilityProfile,
    run_target_conformance,
)


def test_reference_target_passes_full_remote_control_plane_conformance():
    report = run_target_conformance(create_reference_backend_target())

    assert report.profile == BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE
    assert report.passed is True, [diag.message for diag in report.diagnostics]
    assert not report.unsupported_contract_gaps
    assert not report.unsupported_capability_gaps


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


def test_reference_target_conformance_matches_stub_acceptance():
    from raes_backend_stubs.stubs import create_stub_target

    reference_report = run_target_conformance(create_reference_backend_target())
    stub_report = run_target_conformance(create_stub_target())

    assert reference_report.profile == stub_report.profile
    assert reference_report.passed == stub_report.passed is True
    assert {case.name for case in reference_report.cases} == {case.name for case in stub_report.cases}
