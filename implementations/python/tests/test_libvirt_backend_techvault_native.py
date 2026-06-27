"""Native TechVault libvirt realization and live-gate coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aces_backend_libvirt import create_libvirt_target
from aces_backend_libvirt.techvault_native import (
    BusyboxInitramfsBuilder,
    ProbeResult,
    TechVaultNativeLibvirtDriver,
    expected_surface,
)
from aces_operations import techvault_live
from aces_operations.techvault_live import validate_techvault_live
from paths import EXAMPLES_DIR

from aces.core.runtime.control_plane import RuntimeControlPlane
from aces.core.runtime.manager import RuntimeManager
from aces.core.sdl import parse_sdl


class _NativeObject:
    def __init__(self, name: str = "") -> None:
        self._name = name
        self.created = False
        self.destroyed = False
        self.undefined = False

    def name(self):
        return self._name

    def create(self):
        self.created = True

    def destroy(self):
        self.destroyed = True

    def undefine(self):
        self.undefined = True


class _FakeConnection:
    def __init__(self) -> None:
        self.network_xml: list[str] = []
        self.domain_xml: list[str] = []
        self.networks: dict[str, _NativeObject] = {}
        self.domains: dict[str, _NativeObject] = {}

    def networkDefineXML(self, xml: str):  # noqa: N802 - mirrors libvirt API
        self.network_xml.append(xml)
        name = _name_from_xml(xml)
        native = _NativeObject(name)
        self.networks[name] = native
        return native

    def defineXML(self, xml: str):  # noqa: N802 - mirrors libvirt API
        self.domain_xml.append(xml)
        name = _name_from_xml(xml)
        native = _NativeObject(name)
        self.domains[name] = native
        return native

    def networkLookupByName(self, name: str):  # noqa: N802 - mirrors libvirt API
        return self.networks[name]

    def lookupByName(self, name: str):  # noqa: N802 - mirrors libvirt API
        return self.domains[name]

    def listAllDomains(self):  # noqa: N802 - mirrors libvirt API
        return list(self.domains.values())

    def listAllNetworks(self):  # noqa: N802 - mirrors libvirt API
        return list(self.networks.values())


class _Builder:
    def build(self, *, domain, target: Path):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"initramfs")
        return target


class _Probe:
    def ping(self, ip: str):
        return ProbeResult(True)

    def tcp(self, ip: str, port: int):
        return ProbeResult(True)


def _name_from_xml(xml: str) -> str:
    start = xml.index("<name>") + len("<name>")
    end = xml.index("</name>")
    return xml[start:end]


def _apply_native_scenario(path: Path, tmp_path: Path):
    connection = _FakeConnection()
    kernel = tmp_path / "vmlinuz"
    kernel.write_bytes(b"kernel")
    driver = TechVaultNativeLibvirtDriver(
        state_dir=tmp_path / "state",
        connection=connection,
        kernel_path=kernel,
        name_prefix="native-test",
        initramfs_builder=_Builder(),
    )
    target = create_libvirt_target(driver=driver, name_prefix="native-test")
    manager = RuntimeManager(target)
    scenario = parse_sdl(path.read_text(encoding="utf-8"))
    execution_plan = manager.plan(scenario)
    control_plane = RuntimeControlPlane(target)
    receipt = control_plane.submit_provisioning(execution_plan.provisioning)
    status = control_plane.get_operation(receipt.operation_id)
    assert status is not None
    assert status.state.value == "succeeded", status.diagnostics
    return driver, connection


def test_operational_techvault_realizes_native_libvirt_domains_without_compose(tmp_path):
    driver, connection = _apply_native_scenario(EXAMPLES_DIR / "techvault-operational.sdl.yaml", tmp_path)

    surface = expected_surface(driver.last_snapshot)
    assert surface["substrate"] == "libvirt-qemu-initramfs"
    assert len(surface["domains"]) == 30
    assert len(surface["networks"]) == 4
    assert "thehive" in surface["domains"]
    assert "misp" in surface["domains"]
    assert "suricata" in surface["domains"]
    assert "docker" not in json.dumps(driver.last_snapshot).lower()
    assert "compose" not in json.dumps(driver.last_snapshot).lower()
    assert len(connection.domain_xml) == 30
    assert len(connection.network_xml) == 4
    assert all("<kernel>" in xml and "<initrd>" in xml for xml in connection.domain_xml)


@pytest.mark.parametrize(
    ("filename", "domain_count", "network_count"),
    (
        ("techvault-observability-core.sdl.yaml", 3, 1),
        ("techvault-defensive-min.sdl.yaml", 6, 1),
        ("techvault-enterprise-web.sdl.yaml", 9, 3),
        ("techvault-attacker-target.sdl.yaml", 8, 3),
    ),
)
def test_curated_variants_drive_distinct_native_surfaces(filename, domain_count, network_count, tmp_path):
    driver, _connection = _apply_native_scenario(EXAMPLES_DIR / filename, tmp_path)

    surface = expected_surface(driver.last_snapshot)
    assert len(surface["domains"]) == domain_count
    assert len(surface["networks"]) == network_count
    assert surface["service_count"] > 0


def test_validate_techvault_live_records_native_manifest(tmp_path):
    scenario = EXAMPLES_DIR / "techvault-attacker-target.sdl.yaml"

    def _driver_factory():
        kernel = tmp_path / "vmlinuz-live"
        kernel.write_bytes(b"kernel")
        return TechVaultNativeLibvirtDriver(
            state_dir=tmp_path / "state",
            connection=_FakeConnection(),
            kernel_path=kernel,
            name_prefix="live-test",
            initramfs_builder=_Builder(),
        )

    report = validate_techvault_live(
        scenario_path=scenario,
        project_dir=tmp_path,
        run_id="native-live",
        driver_factory=_driver_factory,
        probe=_Probe(),
        boot_timeout_seconds=1,
    )

    assert report.passed, report.render()
    manifest = tmp_path / "runs" / "native-live" / "live-gate" / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["schema"] == "aces.libvirt.techvault-native-live-gate/v1"
    assert payload["aces_libvirt"]["substrate"] == "libvirt-qemu-initramfs"
    assert payload["snapshot"]["containers"] == []
    assert "kali" in payload["aces_libvirt"]["surface"]["domains"]
    assert "victim" in payload["aces_libvirt"]["surface"]["domains"]


def test_live_gate_has_no_aptl_or_docker_probe_dependency():
    source = Path(techvault_live.__file__).read_text(encoding="utf-8")
    assert "TechVaultComposeDriver" not in source
    assert "docker" not in source.lower()
    assert "aptl" not in source.lower()


def test_native_driver_clean_boot_removes_previous_prefixed_resources(tmp_path):
    connection = _FakeConnection()
    old_domain = _NativeObject("native-test-old-domain")
    old_network = _NativeObject("native-test-old-network")
    connection.domains[old_domain.name()] = old_domain
    connection.networks[old_network.name()] = old_network
    kernel = tmp_path / "vmlinuz"
    kernel.write_bytes(b"kernel")
    driver = TechVaultNativeLibvirtDriver(
        state_dir=tmp_path / "state",
        connection=connection,
        kernel_path=kernel,
        name_prefix="native-test",
        initramfs_builder=_Builder(),
        clean_existing=True,
    )

    result = driver.realize(networks=(), domains=())

    assert not result.diagnostics
    assert old_domain.destroyed is True
    assert old_domain.undefined is True
    assert old_network.destroyed is True
    assert old_network.undefined is True


def test_busybox_initramfs_builder_writes_gzip_cpio(tmp_path):
    domain = {
        "name": "webapp",
        "role": "enterprise",
        "interfaces": [{"mac": "52:54:00:00:00:01", "ip": "192.0.2.10", "cidr_prefix": 24}],
        "services": [{"name": "http", "port": 8080, "protocol": "tcp"}],
    }

    target = BusyboxInitramfsBuilder().build(domain=domain, target=tmp_path / "webapp.cpio.gz")

    assert target.read_bytes().startswith(b"\x1f\x8b")
    assert target.stat().st_size > 1000
