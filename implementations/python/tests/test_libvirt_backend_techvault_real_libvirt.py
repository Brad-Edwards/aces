"""Opt-in real-libvirt certification for the bounded TechVault substrate."""

from __future__ import annotations

import importlib
import json
import os
import shutil
from pathlib import Path

import pytest
from aces_operations.techvault_live import TechVaultLiveConfig, validate_techvault_live
from paths import EXAMPLES_DIR


@pytest.mark.integration
def test_bounded_techvault_real_libvirt_readback_and_cleanup(tmp_path):
    """Certify exact daemon readback and verified cleanup on an operator-selected daemon."""

    connection_uri = os.environ.get("ACES_REAL_LIBVIRT_URI")
    if not connection_uri:
        pytest.skip("set ACES_REAL_LIBVIRT_URI to run real-libvirt certification")
    try:
        libvirt = importlib.import_module("libvirt")
    except ImportError:
        pytest.skip("libvirt-python is unavailable")
    if shutil.which("cpio") is None or not Path("/usr/bin/busybox").is_file():
        pytest.skip("cpio and static BusyBox are required for native appliance certification")
    if not tuple(Path("/boot").glob("vmlinuz-*")):
        pytest.skip("a readable host kernel is required for native appliance certification")

    report = validate_techvault_live(
        scenario_path=EXAMPLES_DIR / "techvault-bounded-native.sdl.yaml",
        project_dir=tmp_path,
        run_id="real-libvirt-certification",
        config=TechVaultLiveConfig(connection_uri=connection_uri),
    )

    assert report.passed, report.render()
    assert report.manifest_path is not None
    manifest = json.loads(Path(report.manifest_path).read_text(encoding="utf-8"))
    assert manifest["cleanup"] == {"source": "driver-reported", "status": "verified"}
    observed = manifest["realization_facts"]["daemon_observed"]
    connection = libvirt.open(connection_uri)
    assert connection is not None
    try:
        remaining_domains = {item.name() for item in connection.listAllDomains()}
        remaining_networks = {item.name() for item in connection.listAllNetworks()}
    finally:
        connection.close()
    assert remaining_domains.isdisjoint(observed["domains"])
    assert remaining_networks.isdisjoint(observed["networks"])
