"""RUN-315: full-profile conformance for the reference simulation target."""

from __future__ import annotations

from aces_reference_simulation_backend import create_reference_simulation_backend_target

from aces.core.runtime.conformance import BackendCapabilityProfile, run_target_conformance


def test_reference_simulation_target_passes_full_remote_control_plane_conformance():
    report = run_target_conformance(create_reference_simulation_backend_target())

    assert report.profile == BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE
    assert report.passed is True, [diag.message for diag in report.diagnostics]
    assert not report.unsupported_contract_gaps
    assert not report.unsupported_capability_gaps


def test_reference_simulation_target_drives_participant_probe_case_set():
    report = run_target_conformance(create_reference_simulation_backend_target())

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
            assert case.passed, [diag.message for diag in case.diagnostics]
