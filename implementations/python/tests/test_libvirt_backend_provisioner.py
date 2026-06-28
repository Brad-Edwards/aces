"""Issue #601: libvirt provisioning backend protocol behavior."""

from __future__ import annotations

from aces_backend_libvirt import LibvirtProvisioner
from aces_backend_libvirt.driver import DomainHandle, DriverResult, NetworkHandle
from aces_contracts.planning import (
    ChangeAction,
    EvaluationPlan,
    PlannedResource,
    ProvisioningPlan,
    ProvisionOp,
    RuntimeDomain,
)
from aces_contracts.runtime_state import RuntimeSnapshot, SnapshotEntry


class _RecordingDriver:
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


def _node_resource(address: str = "provision.node.web") -> PlannedResource:
    return PlannedResource(
        address=address,
        domain=RuntimeDomain.PROVISIONING,
        resource_type="node",
        payload={
            "name": "web",
            "node_name": "web",
            "node_type": "vm",
            "os_family": "linux",
            "spec": {
                "node": {
                    "type": "vm",
                    "source": {"name": "/var/lib/libvirt/images/base.qcow2"},
                    "resources": {"ram": 1073741824, "cpu": 2},
                },
                "infrastructure": {"networks": ["lan"]},
            },
        },
    )


def _network_resource(address: str = "provision.network.lan") -> PlannedResource:
    return PlannedResource(
        address=address,
        domain=RuntimeDomain.PROVISIONING,
        resource_type="network",
        payload={"name": "lan", "spec": {"infrastructure": {"properties": {"internal": True}}}},
    )


def _plan(*resources: PlannedResource, action: ChangeAction = ChangeAction.CREATE) -> ProvisioningPlan:
    return ProvisioningPlan(
        resources={resource.address: resource for resource in resources},
        operations=[
            ProvisionOp(
                action=action,
                address=resource.address,
                resource_type=resource.resource_type,
                payload=resource.payload,
                ordering_dependencies=resource.ordering_dependencies,
                refresh_dependencies=resource.refresh_dependencies,
            )
            for resource in resources
        ],
    )


def test_validate_rejects_non_provisioning_plan_with_invalid_plan_diagnostic():
    diagnostics = LibvirtProvisioner(_RecordingDriver()).validate(EvaluationPlan())  # type: ignore[arg-type]

    assert [diag.code for diag in diagnostics] == ["libvirt-backend.invalid-plan"]
    assert diagnostics[0].address == "runtime.libvirt.provisioning"


def test_apply_rejects_non_provisioning_plan_without_mutating_snapshot():
    snapshot = RuntimeSnapshot()

    result = LibvirtProvisioner(_RecordingDriver()).apply(EvaluationPlan(), snapshot)  # type: ignore[arg-type]

    assert result.success is False
    assert result.snapshot is snapshot
    assert [diag.code for diag in result.diagnostics] == ["libvirt-backend.invalid-plan"]


def test_apply_reconciles_snapshot_and_drives_libvirt_driver_for_create():
    driver = _RecordingDriver()
    plan = _plan(_network_resource(), _node_resource())

    result = LibvirtProvisioner(driver).apply(plan, RuntimeSnapshot())

    assert result.success is True
    assert sorted(result.changed_addresses) == ["provision.network.lan", "provision.node.web"]
    assert result.snapshot.entries["provision.node.web"].status == "applied"
    assert result.snapshot.entries["provision.node.web"].payload["os_family"] == "linux"
    assert driver.realize_calls
    domains = driver.realize_calls[0]["domains"]
    networks = driver.realize_calls[0]["networks"]
    assert [spec.address for spec in domains] == ["provision.node.web"]
    assert [spec.address for spec in networks] == ["provision.network.lan"]


def test_apply_delete_removes_snapshot_entry_and_drives_destroy():
    driver = _RecordingDriver()
    snapshot = RuntimeSnapshot(
        entries={
            "provision.node.web": SnapshotEntry(
                address="provision.node.web",
                domain=RuntimeDomain.PROVISIONING,
                resource_type="node",
                payload={},
            )
        }
    )
    plan = ProvisioningPlan(
        operations=[
            ProvisionOp(
                action=ChangeAction.DELETE,
                address="provision.node.web",
                resource_type="node",
                payload={},
            )
        ]
    )

    result = LibvirtProvisioner(driver).apply(plan, snapshot)

    assert result.success is True
    assert "provision.node.web" not in result.snapshot.entries
    assert driver.destroy_calls == [{"networks": (), "domains": ("provision.node.web",)}]


def test_apply_fails_closed_when_driver_omits_realization_confirmation():
    class _SilentRealizeDriver(_RecordingDriver):
        def realize(self, *, networks, domains):
            self.realize_calls.append({"networks": networks, "domains": domains})
            return DriverResult()

    snapshot = RuntimeSnapshot()
    plan = _plan(_node_resource())

    result = LibvirtProvisioner(_SilentRealizeDriver()).apply(plan, snapshot)

    assert result.success is False
    assert result.snapshot is snapshot
    assert [diag.code for diag in result.diagnostics] == ["libvirt-backend.driver.unconfirmed-realization"]
    assert result.diagnostics[0].address == "provision.node.web"


def test_apply_fails_closed_when_driver_omits_destroy_confirmation():
    class _SilentDestroyDriver(_RecordingDriver):
        def destroy(self, *, networks, domains):
            self.destroy_calls.append({"networks": networks, "domains": domains})
            return DriverResult()

    snapshot = RuntimeSnapshot(
        entries={
            "provision.node.web": SnapshotEntry(
                address="provision.node.web",
                domain=RuntimeDomain.PROVISIONING,
                resource_type="node",
                payload={},
            )
        }
    )
    plan = ProvisioningPlan(
        operations=[
            ProvisionOp(
                action=ChangeAction.DELETE,
                address="provision.node.web",
                resource_type="node",
                payload={},
            )
        ]
    )

    result = LibvirtProvisioner(_SilentDestroyDriver()).apply(plan, snapshot)

    assert result.success is False
    assert result.snapshot is snapshot
    assert "provision.node.web" in result.snapshot.entries
    assert [diag.code for diag in result.diagnostics] == ["libvirt-backend.driver.unconfirmed-destroy"]
