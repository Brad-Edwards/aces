"""Opt-in real-libvirt certification for guest-observed realization probes.

This is the native-proof gate: it boots the guest-observing appliance through the
production apply path against an operator-selected real libvirt/QEMU daemon, reads
concern facts back from inside the guest, and verifies teardown. It is skipped
unless ``ACES_REAL_LIBVIRT_URI`` is set and the host has libvirt-python, cpio,
BusyBox, and a readable kernel. Hermetic fake-driver tests cannot satisfy this
gate.
"""

from __future__ import annotations

import importlib
import os
import shutil
from pathlib import Path

import pytest
from raes_operations.libvirt_evidence_run import (
    LibvirtEvidenceRunConfig,
    run_libvirt_evidence_run,
    validate_libvirt_evidence_run_artifact,
)
from paths import EXAMPLES_DIR


@pytest.mark.integration
def test_guest_certified_real_libvirt_readback_and_cleanup(tmp_path):
    """Certify guest-observed realization and verified cleanup on a real daemon."""

    connection_uri = os.environ.get("ACES_REAL_LIBVIRT_URI")
    if not connection_uri:
        pytest.skip("set ACES_REAL_LIBVIRT_URI to run real-libvirt guest certification")
    try:
        libvirt = importlib.import_module("libvirt")
    except ImportError:
        pytest.skip("libvirt-python is unavailable")
    if shutil.which("cpio") is None or not Path("/usr/bin/busybox").is_file():
        pytest.skip("cpio and BusyBox are required for guest-observing appliance certification")
    if not tuple(Path("/boot").glob("vmlinuz-*")):
        pytest.skip("a readable host kernel is required for guest-observing appliance certification")

    report = run_libvirt_evidence_run(
        scenario_path=EXAMPLES_DIR / "techvault-guest-certified.sdl.yaml",
        project_dir=tmp_path,
        run_id="real-libvirt-guest-certification",
        config=LibvirtEvidenceRunConfig(evidence_source_mode="guest-certified", connection_uri=connection_uri),
    )

    assert report.passed, report.render()
    artifact = report.artifact
    assert artifact is not None
    assert validate_libvirt_evidence_run_artifact(artifact) == []
    guest = artifact["realization_facts"]["guest_observed"]
    assert guest["source"] == "guest-observed"
    assert guest["operation_ref"].startswith("sha256:")
    # The production driver (no injected factory) yields a certifying artifact.
    assert guest["certifying"] is True
    assert guest["domains"]

    daemon = artifact["realization_facts"]["daemon_observed"]
    observed_domains = {str(item.get("name")) for item in daemon["domains"]}
    observed_networks = {str(item.get("name")) for item in daemon["networks"]}
    connection = libvirt.open(connection_uri)
    assert connection is not None
    try:
        remaining_domains = {item.name() for item in connection.listAllDomains()}
        remaining_networks = {item.name() for item in connection.listAllNetworks()}
    finally:
        connection.close()
    assert remaining_domains.isdisjoint(observed_domains)
    assert remaining_networks.isdisjoint(observed_networks)
