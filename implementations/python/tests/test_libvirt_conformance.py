"""Issue #606: libvirt backend conformance (fixture + live target).

Acceptance bar:

1. ``aces conformance backend --profile provisioning-only`` passes with no
   ``unsupported-capability-claim`` / ``unsupported-contract-declaration``
   diagnostics (covered by ``test_backend_conformance_cli.py`` /
   ``run_fixture_suite`` -- asserted green here for the libvirt-relevant profile).
2. ``run_target_conformance`` against the libvirt target passes a real
   *provisioning probe* and asserts *snapshot mutation* -- not manifest /
   contract-surface only. The probe drives ``RuntimeControlPlane`` and proves
   the snapshot gained provisioning entries.
3. A conformance report is captured and committed (drift-guarded here).

The live probe runs daemon-free through an injected ``RecordingLibvirtDriver``
that confirms realization, so the real ``LibvirtProvisioner`` path is exercised
without a libvirt/QEMU daemon.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from aces_backend_libvirt.target import create_libvirt_target
from aces_conformance.conformance import (
    BackendCapabilityProfile,
    run_fixture_suite,
    run_target_conformance,
)
from aces_contracts.planning import RuntimeDomain
from aces_processor.reference import run_reference_processor
from aces_runtime.control_plane import RuntimeControlPlane
from aces_sdl.parser import parse_sdl
from libvirt_conformance_fixtures import RecordingLibvirtDriver
from libvirt_participant_fixtures import NullLibvirtDriver

REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED_REPORT = REPO_ROOT / "docs" / "conformance" / "libvirt-qemu.provisioning-only.report.json"

_PROVISIONING_SCENARIO = dedent(
    """
    name: libvirt-conformance
    nodes:
      vm:
        type: vm
        os: linux
        resources: {ram: 1 gib, cpu: 1}
    """
)


def _provisioning_plan(target):
    scenario = parse_sdl(_PROVISIONING_SCENARIO)
    return run_reference_processor(scenario, target.manifest).execution_plan.provisioning


def _bounded_report_payload(report) -> dict:
    """Bounded, environment-stable projection of a conformance report.

    Keeps only fields that are reproducible across runs and dependency versions:
    profile, pass/fail, per-case identity + pass/fail + stable diagnostic
    *codes*, and gap sets. Free-text diagnostic messages (which carry
    validator-version-specific prose) are intentionally excluded so the
    committed report never drifts on an unrelated dependency bump.
    """

    return {
        "profile": report.profile,
        "passed": report.passed,
        "cases": [
            {
                "name": case.name,
                "contract_name": case.contract_name,
                "valid": case.valid,
                "passed": case.passed,
                "diagnostic_codes": sorted({diag.code for diag in case.diagnostics}),
            }
            for case in report.cases
        ],
        "unsupported_contract_gaps": list(report.unsupported_contract_gaps),
        "unsupported_capability_gaps": list(report.unsupported_capability_gaps),
        "diagnostic_codes": sorted({diag.code for diag in report.diagnostics}),
    }


def _libvirt_conformance_report():
    return run_target_conformance(create_libvirt_target(driver=RecordingLibvirtDriver()))


# ---------------------------------------------------------------------------
# AC1: fixture suite for the libvirt-relevant profile is clean
# ---------------------------------------------------------------------------


def test_provisioning_only_fixture_suite_has_no_unsupported_diagnostics():
    report = run_fixture_suite(profile=BackendCapabilityProfile.PROVISIONING_ONLY)

    assert report.passed is True, [diag.message for diag in report.diagnostics]
    codes = {diag.code for diag in report.diagnostics} | {
        diag.code for case in report.cases for diag in case.diagnostics if not case.passed
    }
    assert "conformance.unsupported-capability-claim" not in codes
    assert "conformance.unsupported-contract-declaration" not in codes


# ---------------------------------------------------------------------------
# AC2: live provisioning probe + real snapshot mutation
# ---------------------------------------------------------------------------


def test_provisioning_only_conformance_runs_live_provisioning_probe():
    report = _libvirt_conformance_report()

    assert report.profile == BackendCapabilityProfile.PROVISIONING_ONLY
    assert report.passed is True, [diag.message for diag in report.diagnostics]
    assert not report.unsupported_contract_gaps
    assert not report.unsupported_capability_gaps

    case_names = {case.name for case in report.cases}
    # Not manifest/contract-surface only: the probe must actually provision and
    # validate a mutated snapshot.
    assert {"live-manifest", "live-provisioning", "live-snapshot"} <= case_names
    for case in report.cases:
        if case.name in {"live-manifest", "live-provisioning", "live-snapshot"}:
            assert case.passed, [diag.message for diag in case.diagnostics]


def test_libvirt_provisioning_mutates_snapshot():
    driver = RecordingLibvirtDriver()
    target = create_libvirt_target(driver=driver)
    control_plane = RuntimeControlPlane(target)

    receipt = control_plane.submit_provisioning(_provisioning_plan(target))
    status = control_plane.get_operation(receipt.operation_id)

    assert status is not None and status.state.value == "succeeded", status
    assert status.changed_addresses, "provisioning must report changed addresses"

    provisioned = {
        address
        for address, entry in control_plane.snapshot.entries.items()
        if entry.domain == RuntimeDomain.PROVISIONING
    }
    assert provisioned, "snapshot must gain provisioning entries (real mutation, not contract-surface)"
    # The real libvirt provisioner path drove the injected driver.
    assert driver.realized_addresses(), "driver must have realized the provisioned addresses"
    assert provisioned & set(driver.realized_addresses())


def test_provisioning_only_conformance_requires_confirmed_realization():
    """A driver that does not confirm realization must fail the live probe.

    Guards the backend-neutral anti-pattern: provisioning-only conformance must
    not pass on ``live-manifest`` alone, and must not accept an empty snapshot.
    """

    report = run_target_conformance(create_libvirt_target(driver=NullLibvirtDriver()))

    assert report.passed is False
    live_provisioning = next((case for case in report.cases if case.name == "live-provisioning"), None)
    assert live_provisioning is not None, "provisioning-only conformance must run a live-provisioning probe"
    assert live_provisioning.passed is False


# ---------------------------------------------------------------------------
# AC3: committed conformance report is captured and kept current
# ---------------------------------------------------------------------------


def test_committed_conformance_report_is_current():
    assert COMMITTED_REPORT.exists(), f"committed conformance report missing at {COMMITTED_REPORT}"
    committed = json.loads(COMMITTED_REPORT.read_text(encoding="utf-8"))
    fresh = _bounded_report_payload(_libvirt_conformance_report())

    assert committed == fresh, (
        "committed libvirt conformance report is stale; regenerate "
        f"{COMMITTED_REPORT.relative_to(REPO_ROOT)} from run_target_conformance"
    )
    assert committed["passed"] is True
