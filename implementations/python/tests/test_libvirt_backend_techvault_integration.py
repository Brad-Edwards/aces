"""Issue #601: TechVault scenarios drive libvirt provisioning."""

from __future__ import annotations

from collections import Counter

from aces_backend_libvirt import create_libvirt_target
from aces_backend_libvirt.driver import DomainHandle, DriverResult, NetworkHandle
from aces_backend_libvirt.techvault_driver import TechVaultComposeDriver, TechVaultLifecycleResult
from paths import EXAMPLES_DIR

from aces.core.runtime.control_plane import RuntimeControlPlane
from aces.core.runtime.manager import RuntimeManager
from aces.core.sdl import parse_sdl

_TECHVAULT_PARAMETERS = {
    "app_py_sha256": "a" * 64,
    "requirements_sha256": "b" * 64,
    "style_css_sha256": "c" * 64,
    "webapp_conf_sha256": "d" * 64,
    "wazuh_conf_sha256": "e" * 64,
}


class _RecordingLibvirtDriver:
    def __init__(self) -> None:
        self.realize_calls: list[dict[str, object]] = []
        self.destroy_calls: list[dict[str, object]] = []
        self._realized: set[str] = set()

    def realize(self, *, networks, domains):
        self.realize_calls.append({"networks": networks, "domains": domains})
        self._realized.update(spec.address for spec in networks)
        self._realized.update(spec.address for spec in domains)
        return DriverResult(
            networks=tuple(NetworkHandle(address=spec.address) for spec in networks),
            domains=tuple(DomainHandle(address=spec.address) for spec in domains),
        )

    def destroy(self, *, networks, domains):
        self.destroy_calls.append({"networks": networks, "domains": domains})
        self._realized.difference_update(networks)
        self._realized.difference_update(domains)
        return DriverResult(
            networks=tuple(NetworkHandle(address=address, realized=False) for address in networks),
            domains=tuple(DomainHandle(address=address, realized=False) for address in domains),
        )

    def realized_addresses(self):
        return frozenset(self._realized)


class _RecordingTechVaultRunner:
    def __init__(self) -> None:
        self.start_calls: list[dict[str, object]] = []
        self.stop_calls: list[dict[str, object]] = []

    def start(self, *, project_dir, profiles, clean_volumes, scenario_path):
        self.start_calls.append(
            {
                "project_dir": project_dir,
                "profiles": profiles,
                "clean_volumes": clean_volumes,
                "scenario_path": scenario_path,
            }
        )
        return TechVaultLifecycleResult(
            success=True,
            profiles=profiles,
            snapshot={"containers": [{"name": "aptl-kali", "status": "Up", "health": "healthy", "networks": {}}]},
        )

    def stop(self, *, project_dir, profiles, remove_volumes):
        self.stop_calls.append({"project_dir": project_dir, "profiles": profiles, "remove_volumes": remove_volumes})
        return TechVaultLifecycleResult(success=True, profiles=profiles)


def test_techvault_scenario_plans_and_applies_through_libvirt_provisioning():
    driver = _RecordingLibvirtDriver()
    target = create_libvirt_target(driver=driver, name_prefix="techvault-test")
    manager = RuntimeManager(target)
    scenario = parse_sdl((EXAMPLES_DIR / "techvault.sdl.yaml").read_text(encoding="utf-8"))

    execution_plan = manager.plan(scenario, parameters=_TECHVAULT_PARAMETERS)

    assert execution_plan.is_valid
    assert execution_plan.model.scenario_name == "techvault-runtime-parity"
    assert len(execution_plan.model.node_deployments) == 1
    assert len(execution_plan.model.networks) == 2
    assert Counter(resource.resource_type for resource in execution_plan.provisioning.resources.values()) == Counter(
        {"network": 2, "node": 1}
    )

    control_plane = RuntimeControlPlane(target)
    receipt = control_plane.submit_provisioning(execution_plan.provisioning)
    status = control_plane.get_operation(receipt.operation_id)

    assert status is not None
    assert status.state.value == "succeeded"
    assert not status.diagnostics
    assert len(driver.realize_calls) == 1
    networks = driver.realize_calls[0]["networks"]
    domains = driver.realize_calls[0]["domains"]
    assert [spec.address for spec in networks] == [
        "provision.network.aptl-dmz",
        "provision.network.aptl-internal",
    ]
    assert [spec.address for spec in domains] == ["provision.node.techvault-webapp"]
    assert domains[0].image_ref == "techvault-webapp"
    assert domains[0].memory_mib == 1024
    assert domains[0].vcpus == 1
    assert domains[0].networks == (
        "provision.network.aptl-dmz",
        "provision.network.aptl-internal",
    )

    snapshot = control_plane.snapshot
    assert set(snapshot.entries) == {
        "provision.network.aptl-dmz",
        "provision.network.aptl-internal",
        "provision.node.techvault-webapp",
    }
    rendered_snapshot = repr(snapshot.entries["provision.node.techvault-webapp"].payload)
    assert "${" not in rendered_snapshot
    assert _TECHVAULT_PARAMETERS["app_py_sha256"] in rendered_snapshot
    assert _TECHVAULT_PARAMETERS["webapp_conf_sha256"] in rendered_snapshot
    assert driver.realized_addresses() == frozenset(snapshot.entries)


def test_techvault_operational_scenario_drives_full_libvirt_surface():
    driver = _RecordingLibvirtDriver()
    target = create_libvirt_target(driver=driver, name_prefix="techvault-operational")
    manager = RuntimeManager(target)
    scenario = parse_sdl((EXAMPLES_DIR / "techvault-operational.sdl.yaml").read_text(encoding="utf-8"))

    execution_plan = manager.plan(scenario)

    assert execution_plan.is_valid
    assert execution_plan.model.scenario_name == "techvault"
    assert len(execution_plan.model.node_deployments) == 30
    assert len(execution_plan.model.networks) == 4
    assert Counter(resource.resource_type for resource in execution_plan.provisioning.resources.values()) == Counter(
        {"node": 30, "network": 4}
    )

    control_plane = RuntimeControlPlane(target)
    receipt = control_plane.submit_provisioning(execution_plan.provisioning)
    status = control_plane.get_operation(receipt.operation_id)

    assert status is not None
    assert status.state.value == "succeeded"
    assert not status.diagnostics
    assert len(driver.realize_calls) == 1
    networks = driver.realize_calls[0]["networks"]
    domains = driver.realize_calls[0]["domains"]
    assert [spec.address for spec in networks] == [
        "provision.network.dmz-net",
        "provision.network.internal-net",
        "provision.network.redteam-net",
        "provision.network.security-net",
    ]
    domain_by_name = {spec.name: spec for spec in domains}
    assert set(domain_by_name) == {
        "ad",
        "aptl-grafana-otel",
        "aptl-otel-collector",
        "aptl-tempo",
        "cortex",
        "db",
        "dns",
        "fileshare",
        "kali",
        "kali-capture",
        "misp",
        "misp-db",
        "misp-redis",
        "misp-suricata-sync",
        "shuffle-backend",
        "shuffle-frontend",
        "shuffle-opensearch",
        "shuffle-orborus",
        "suricata",
        "thehive",
        "thehive-cassandra",
        "thehive-es",
        "victim",
        "wazuh-dashboard",
        "wazuh-indexer",
        "wazuh-manager",
        "wazuh-sidecar-db",
        "wazuh-sidecar-suricata",
        "webapp",
        "workstation",
    }
    assert domain_by_name["wazuh-manager"].networks == (
        "provision.network.security-net",
        "provision.network.dmz-net",
        "provision.network.internal-net",
    )
    assert domain_by_name["kali"].networks == (
        "provision.network.redteam-net",
        "provision.network.dmz-net",
        "provision.network.internal-net",
    )
    assert domain_by_name["suricata"].networks == (
        "provision.network.security-net",
        "provision.network.dmz-net",
        "provision.network.internal-net",
    )
    assert domain_by_name["webapp"].networks == (
        "provision.network.dmz-net",
        "provision.network.internal-net",
    )

    snapshot = control_plane.snapshot
    assert len(snapshot.entries) == 34
    assert driver.realized_addresses() == frozenset(snapshot.entries)


def test_techvault_operational_scenario_starts_selected_profiles_through_driver(tmp_path):
    runner = _RecordingTechVaultRunner()
    _write_operational_compose_fixture(tmp_path)
    scenario_path = EXAMPLES_DIR / "techvault-operational.sdl.yaml"
    driver = TechVaultComposeDriver(
        project_dir=tmp_path,
        scenario_path=scenario_path,
        clean_boot=True,
        runner=runner,
    )
    target = create_libvirt_target(driver=driver, name_prefix="techvault-operational")
    manager = RuntimeManager(target)
    scenario = parse_sdl(scenario_path.read_text(encoding="utf-8"))

    execution_plan = manager.plan(scenario)
    control_plane = RuntimeControlPlane(target)
    receipt = control_plane.submit_provisioning(execution_plan.provisioning)
    status = control_plane.get_operation(receipt.operation_id)

    assert execution_plan.is_valid
    assert status is not None
    assert status.state.value == "succeeded"
    assert not status.diagnostics
    assert len(runner.start_calls) == 1
    assert runner.start_calls[0]["clean_volumes"] is True
    assert runner.start_calls[0]["scenario_path"] == scenario_path
    assert runner.start_calls[0]["profiles"] == (
        "wazuh",
        "victim",
        "kali",
        "enterprise",
        "soc",
        "fileshare",
        "dns",
        "otel",
    )
    assert driver.last_selection is not None
    assert driver.last_selection.unmapped_nodes == ()
    assert len(driver.last_selection.mapped_nodes) == 30


def _write_operational_compose_fixture(tmp_path):
    profiles = {
        "wazuh-manager": "wazuh",
        "wazuh-indexer": "wazuh",
        "wazuh-dashboard": "wazuh",
        "kali": "kali",
        "kali-capture": "kali",
        "aptl-otel-collector": "otel",
        "aptl-tempo": "otel",
        "aptl-grafana-otel": "otel",
        "fileshare": "fileshare",
        "dns": "dns",
        "victim": "victim",
        "webapp": "enterprise",
        "ad": "enterprise",
        "db": "enterprise",
        "workstation": "enterprise",
    }
    nodes = {
        "ad",
        "aptl-grafana-otel",
        "aptl-otel-collector",
        "aptl-tempo",
        "cortex",
        "db",
        "dns",
        "fileshare",
        "kali",
        "kali-capture",
        "misp",
        "misp-db",
        "misp-redis",
        "misp-suricata-sync",
        "shuffle-backend",
        "shuffle-frontend",
        "shuffle-opensearch",
        "shuffle-orborus",
        "suricata",
        "thehive",
        "thehive-cassandra",
        "thehive-es",
        "victim",
        "wazuh-dashboard",
        "wazuh-indexer",
        "wazuh-manager",
        "wazuh-sidecar-db",
        "wazuh-sidecar-suricata",
        "webapp",
        "workstation",
    }
    (tmp_path / "aptl.json").write_text(
        """
{
  "containers": {
    "wazuh": true,
    "victim": true,
    "kali": true,
    "reverse": false,
    "enterprise": true,
    "soc": true,
    "mail": false,
    "fileshare": true,
    "dns": true
  }
}
""",
        encoding="utf-8",
    )
    services = ["services:"]
    for node in sorted(nodes):
        profile = profiles.get(node, "soc")
        service_name = node.replace("-", ".") if node.startswith("wazuh-") else node
        services.extend(
            [
                f"  {service_name}:",
                f"    profiles: [\"{profile}\"]",
                f"    container_name: aptl-{node}",
                f"    hostname: {node}",
            ]
        )
    (tmp_path / "docker-compose.yml").write_text("\n".join(services) + "\n", encoding="utf-8")
