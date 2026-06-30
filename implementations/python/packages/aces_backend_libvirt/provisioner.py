"""Provisioner implementation for the libvirt/QEMU backend."""

from __future__ import annotations

from dataclasses import dataclass

from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import ChangeAction, ProvisioningPlan, ProvisionOp, RuntimeDomain
from aces_contracts.runtime_state import ApplyResult, RuntimeSnapshot, SnapshotEntry

from .driver import DriverResult, LibvirtDriver
from .realization import NETWORK_RESOURCE_TYPE, NODE_RESOURCE_TYPE, Realization, interpret_provisioning_plan

_DOMAIN = "runtime"
INVALID_PLAN_CODE = "libvirt-backend.invalid-plan"
UNCONFIRMED_DESTROY_CODE = "libvirt-backend.driver.unconfirmed-destroy"
UNCONFIRMED_REALIZATION_CODE = "libvirt-backend.driver.unconfirmed-realization"


@dataclass
class _SnapshotReconciliation:
    entries: dict[str, SnapshotEntry]
    changed_addresses: list[str]
    delete_networks: list[str]
    delete_domains: list[str]


class LibvirtProvisioner:
    """Provisioning-only backend that realizes plans through a libvirt driver."""

    def __init__(self, driver: LibvirtDriver | None = None) -> None:
        self._driver = driver if driver is not None else _default_driver()

    @staticmethod
    def validate(plan: ProvisioningPlan) -> list[Diagnostic]:
        if not isinstance(plan, ProvisioningPlan):
            return [_invalid_plan_diagnostic()]
        realization = interpret_provisioning_plan(plan)
        return list(realization.diagnostics)

    def apply(self, plan: ProvisioningPlan, snapshot: RuntimeSnapshot) -> ApplyResult:
        if not isinstance(plan, ProvisioningPlan):
            result = ApplyResult(success=False, snapshot=snapshot, diagnostics=[_invalid_plan_diagnostic()])
        else:
            result = self._apply_provisioning_plan(plan, snapshot)
        return result

    def _apply_provisioning_plan(self, plan: ProvisioningPlan, snapshot: RuntimeSnapshot) -> ApplyResult:
        realization = interpret_provisioning_plan(plan)
        diagnostics: list[Diagnostic] = list(realization.diagnostics)
        if _has_error(diagnostics):
            return ApplyResult(success=False, snapshot=snapshot, diagnostics=diagnostics)

        reconciliation = _reconcile_snapshot(plan, snapshot)
        driver_diagnostics = self._drive(
            plan,
            realization,
            reconciliation.delete_networks,
            reconciliation.delete_domains,
        )
        diagnostics.extend(driver_diagnostics)

        if _has_error(diagnostics):
            return ApplyResult(success=False, snapshot=snapshot, diagnostics=diagnostics)

        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(reconciliation.entries),
            diagnostics=diagnostics,
            changed_addresses=reconciliation.changed_addresses,
        )

    def _drive(
        self,
        plan: ProvisioningPlan,
        realization: Realization,
        delete_networks: list[str],
        delete_domains: list[str],
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        active = {op.address for op in plan.operations if op.action in {ChangeAction.CREATE, ChangeAction.UPDATE}}
        # A changed placement must realize its target domain even when the node
        # itself is UNCHANGED: the domain's seed now carries different cloud-init.
        for placement_address, node_address in realization.placement_targets.items():
            if placement_address in active:
                active.add(node_address)
        networks = tuple(spec for spec in realization.networks if spec.address in active)
        domains = tuple(spec for spec in realization.domains if spec.address in active)
        if networks or domains:
            result = self._driver.realize(networks=networks, domains=domains)
            diagnostics.extend(result.diagnostics)
            diagnostics.extend(
                _unconfirmed_realization_diagnostics(
                    result,
                    requested=tuple(spec.address for spec in (*networks, *domains)),
                )
            )
        if delete_networks or delete_domains:
            result = self._driver.destroy(networks=tuple(delete_networks), domains=tuple(delete_domains))
            diagnostics.extend(result.diagnostics)
            diagnostics.extend(
                _unconfirmed_destroy_diagnostics(
                    result,
                    requested=(*delete_networks, *delete_domains),
                )
            )
        return diagnostics


def validate(plan: ProvisioningPlan) -> list[Diagnostic]:
    """Validate a provisioning plan with the default libvirt provisioner."""

    return LibvirtProvisioner().validate(plan)


def apply(plan: ProvisioningPlan, snapshot: RuntimeSnapshot) -> ApplyResult:
    """Apply a provisioning plan with the default libvirt provisioner."""

    return LibvirtProvisioner().apply(plan, snapshot)


def _default_driver() -> LibvirtDriver:
    from .drivers.libvirt import LibvirtDeploymentDriver

    return LibvirtDeploymentDriver()


def _reconcile_snapshot(plan: ProvisioningPlan, snapshot: RuntimeSnapshot) -> _SnapshotReconciliation:
    reconciliation = _SnapshotReconciliation(
        entries=dict(snapshot.entries),
        changed_addresses=[],
        delete_networks=[],
        delete_domains=[],
    )
    for op in plan.operations:
        _reconcile_operation(reconciliation, op)
    return reconciliation


def _reconcile_operation(reconciliation: _SnapshotReconciliation, op: ProvisionOp) -> None:
    if op.action == ChangeAction.DELETE:
        _record_delete(reconciliation, op)
        return
    _record_snapshot_entry(reconciliation, op)


def _record_delete(reconciliation: _SnapshotReconciliation, op: ProvisionOp) -> None:
    reconciliation.entries.pop(op.address, None)
    reconciliation.changed_addresses.append(op.address)
    delete_targets = {
        NETWORK_RESOURCE_TYPE: reconciliation.delete_networks,
        NODE_RESOURCE_TYPE: reconciliation.delete_domains,
    }
    target = delete_targets.get(op.resource_type)
    if target is not None:
        target.append(op.address)


def _record_snapshot_entry(reconciliation: _SnapshotReconciliation, op: ProvisionOp) -> None:
    status = "unchanged" if op.action == ChangeAction.UNCHANGED else "applied"
    reconciliation.entries[op.address] = SnapshotEntry(
        address=op.address,
        domain=RuntimeDomain.PROVISIONING,
        resource_type=op.resource_type,
        payload=op.payload,
        ordering_dependencies=op.ordering_dependencies,
        refresh_dependencies=op.refresh_dependencies,
        status=status,
    )
    if op.action != ChangeAction.UNCHANGED:
        reconciliation.changed_addresses.append(op.address)


def _has_error(diagnostics: list[Diagnostic]) -> bool:
    return any(diag.is_error for diag in diagnostics)


def _invalid_plan_diagnostic() -> Diagnostic:
    return Diagnostic(
        code=INVALID_PLAN_CODE,
        domain=_DOMAIN,
        address="runtime.libvirt.provisioning",
        message="Libvirt provisioner accepts only aces_contracts.planning.ProvisioningPlan inputs.",
        severity=Severity.ERROR,
    )


def _unconfirmed_realization_diagnostics(result: DriverResult, *, requested: tuple[str, ...]) -> list[Diagnostic]:
    confirmed = {handle.address for handle in (*result.networks, *result.domains) if handle.realized}
    errored = {diag.address for diag in result.diagnostics if diag.is_error}
    return [
        _driver_confirmation_diagnostic(address, code=UNCONFIRMED_REALIZATION_CODE)
        for address in requested
        if address not in confirmed and address not in errored
    ]


def _unconfirmed_destroy_diagnostics(result: DriverResult, *, requested: tuple[str, ...]) -> list[Diagnostic]:
    confirmed_destroyed = {handle.address for handle in (*result.networks, *result.domains) if not handle.realized}
    errored = {diag.address for diag in result.diagnostics if diag.is_error}
    return [
        _driver_confirmation_diagnostic(address, code=UNCONFIRMED_DESTROY_CODE)
        for address in requested
        if address not in confirmed_destroyed and address not in errored
    ]


def _driver_confirmation_diagnostic(address: str, *, code: str) -> Diagnostic:
    action = "destroy" if code == UNCONFIRMED_DESTROY_CODE else "realization"
    return Diagnostic(
        code=code,
        domain=_DOMAIN,
        address=address,
        message=f"Libvirt driver did not confirm {action} for '{address}'.",
        severity=Severity.ERROR,
    )
