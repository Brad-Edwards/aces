"""Reference provisioner: portable snapshot reconciliation + driver side effects.

The provisioner preserves planned payloads honestly into snapshot entries
(the portable surface SEM-218 provenance is computed against), sets entry
status, and drives the injected :class:`DeploymentDriver` to realize or
destroy the corresponding emulated infrastructure. Real container
realization is a DRIVER side effect; it never mutates the portable
snapshot. Driver diagnostics are surfaced through ``ApplyResult`` -- never
as a backend-specific exception.
"""

from __future__ import annotations

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.planning import ChangeAction, ProvisioningPlan, RuntimeDomain
from aces_contracts.runtime_state import ApplyResult, RuntimeSnapshot, SnapshotEntry

from .driver import DeploymentDriver
from .realization import (
    NETWORK_RESOURCE_TYPE,
    NODE_RESOURCE_TYPE,
    Realization,
    interpret_provisioning_plan,
)


class ReferenceProvisioner:
    """Container-backed provisioner over an injected deployment driver."""

    def __init__(self, driver: DeploymentDriver) -> None:
        self._driver = driver

    @staticmethod
    def validate(plan: ProvisioningPlan) -> list[Diagnostic]:
        realization = interpret_provisioning_plan(plan)
        return list(realization.diagnostics)

    def apply(self, plan: ProvisioningPlan, snapshot: RuntimeSnapshot) -> ApplyResult:
        realization = interpret_provisioning_plan(plan)
        diagnostics: list[Diagnostic] = list(realization.diagnostics)
        if any(diag.is_error for diag in diagnostics):
            return ApplyResult(success=False, snapshot=snapshot, diagnostics=diagnostics)

        entries = dict(snapshot.entries)
        changed_addresses: list[str] = []
        delete_networks: list[str] = []
        delete_containers: list[str] = []

        for op in plan.operations:
            if op.action == ChangeAction.DELETE:
                entries.pop(op.address, None)
                changed_addresses.append(op.address)
                if op.resource_type == NETWORK_RESOURCE_TYPE:
                    delete_networks.append(op.address)
                elif op.resource_type == NODE_RESOURCE_TYPE:
                    delete_containers.append(op.address)
                continue
            status = "unchanged" if op.action == ChangeAction.UNCHANGED else "applied"
            entries[op.address] = SnapshotEntry(
                address=op.address,
                domain=RuntimeDomain.PROVISIONING,
                resource_type=op.resource_type,
                payload=op.payload,
                ordering_dependencies=op.ordering_dependencies,
                refresh_dependencies=op.refresh_dependencies,
                status=status,
            )
            if op.action != ChangeAction.UNCHANGED:
                changed_addresses.append(op.address)

        driver_diagnostics = self._drive(plan, realization, delete_networks, delete_containers)
        diagnostics.extend(driver_diagnostics)
        if any(diag.is_error for diag in diagnostics):
            return ApplyResult(success=False, snapshot=snapshot, diagnostics=diagnostics)

        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(entries),
            diagnostics=diagnostics,
            changed_addresses=changed_addresses,
        )

    def _drive(
        self,
        plan: ProvisioningPlan,
        realization: Realization,
        delete_networks: list[str],
        delete_containers: list[str],
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        active = {op.address for op in plan.operations if op.action in {ChangeAction.CREATE, ChangeAction.UPDATE}}
        networks = tuple(spec for spec in realization.networks if spec.address in active)
        containers = tuple(spec for spec in realization.containers if spec.address in active)
        if networks or containers:
            result = self._driver.realize(networks=networks, containers=containers)
            diagnostics.extend(result.diagnostics)
        if delete_networks or delete_containers:
            result = self._driver.destroy(
                networks=tuple(delete_networks),
                containers=tuple(delete_containers),
            )
            diagnostics.extend(result.diagnostics)
        return diagnostics
