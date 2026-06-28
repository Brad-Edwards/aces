"""Issue #601: TechVault scenarios drive libvirt provisioning."""

from __future__ import annotations

from collections import Counter

from aces_backend_libvirt import create_libvirt_target
from aces_backend_libvirt.driver import DomainHandle, DriverResult, NetworkHandle
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
    assert domain_by_name["thehive"].services[0].name == "thehive-api"
    assert domain_by_name["thehive"].services[0].port == 9000
    assert domain_by_name["misp"].services[0].port == 443
    security = {spec.name: spec for spec in networks}["security-net"]
    assert security.cidr == "172.20.0.0/24"
    assert security.gateway == "172.20.0.1"

    snapshot = control_plane.snapshot
    assert len(snapshot.entries) == 34
    assert driver.realized_addresses() == frozenset(snapshot.entries)
