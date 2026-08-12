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

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.planning import ChangeAction, ProvisioningPlan, RuntimeDomain
from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel
from raes_contracts.realization_observation import (
    RealizationObservation,
    RealizationObservationDisclosure,
    bind_compute_substrate_observations,
    compute_substrate_readback_addresses,
    missing_compute_substrate_readbacks,
)
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot, SnapshotEntry

from .driver import DeploymentDriver
from .realization import (
    NETWORK_RESOURCE_TYPE,
    NODE_RESOURCE_TYPE,
    Realization,
    interpret_provisioning_plan,
)


class ReferenceProvisioner:
    """Container-backed provisioner over an injected deployment driver."""

    def __init__(
        self,
        driver: DeploymentDriver,
        realization_envelope: BackendRealizationEnvelopeModel | None = None,
    ) -> None:
        self._driver = driver
        self._realization_envelope = realization_envelope

    @staticmethod
    def validate(plan: ProvisioningPlan) -> list[Diagnostic]:
        realization = interpret_provisioning_plan(plan)
        return list(realization.diagnostics)

    def apply(self, plan: ProvisioningPlan, snapshot: RuntimeSnapshot) -> ApplyResult:
        if plan.realization_constraints and (
            self._realization_envelope is None or plan.realization_envelope != self._realization_envelope.identity
        ):
            return ApplyResult(
                success=False,
                snapshot=snapshot,
                diagnostics=[
                    Diagnostic(
                        code="reference-backend.realization-envelope.mismatch",
                        domain="runtime",
                        address="runtime.reference.provisioning",
                        message="Provisioning plan does not match the selected reference realization envelope.",
                    )
                ],
            )
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

        driver_diagnostics, observations = self._drive(
            plan,
            realization,
            delete_networks,
            delete_containers,
            previous=snapshot.realization_observations,
        )
        diagnostics.extend(driver_diagnostics)
        if self._realization_envelope is not None:
            diagnostics.extend(
                Diagnostic(
                    code="reference-backend.driver.compute-substrate-unobserved",
                    domain="runtime",
                    address=address,
                    message=f"Reference driver did not return fresh substrate readback for '{address}'.",
                )
                for address in missing_compute_substrate_readbacks(
                    plan=plan,
                    observations=observations,
                    envelope=self._realization_envelope,
                    previous=snapshot.realization_observations,
                )
            )
        if any(diag.is_error for diag in diagnostics):
            return ApplyResult(success=False, snapshot=snapshot, diagnostics=diagnostics)

        observation_disclosures = snapshot.realization_observations
        if self._realization_envelope is not None:
            observation_disclosures = bind_compute_substrate_observations(
                plan=plan,
                observations=observations,
                envelope=self._realization_envelope,
                previous=snapshot.realization_observations,
            )
        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(
                entries,
                realization_observations=observation_disclosures,
                realization_envelope=(
                    self._realization_envelope.identity
                    if self._realization_envelope is not None
                    else snapshot.realization_envelope
                ),
            ),
            diagnostics=diagnostics,
            changed_addresses=changed_addresses,
        )

    def _drive(
        self,
        plan: ProvisioningPlan,
        realization: Realization,
        delete_networks: list[str],
        delete_containers: list[str],
        *,
        previous: tuple[RealizationObservationDisclosure, ...],
    ) -> tuple[list[Diagnostic], tuple[RealizationObservation, ...]]:
        diagnostics: list[Diagnostic] = []
        observations: tuple[RealizationObservation, ...] = ()
        active = {op.address for op in plan.operations if op.action in {ChangeAction.CREATE, ChangeAction.UPDATE}}
        networks = tuple(spec for spec in realization.networks if spec.address in active)
        containers = tuple(spec for spec in realization.containers if spec.address in active)
        if networks or containers:
            result = self._driver.realize(networks=networks, containers=containers)
            diagnostics.extend(result.diagnostics)
            observations = result.observations
        if self._realization_envelope is not None:
            readback = (
                set(
                    compute_substrate_readback_addresses(
                        plan=plan,
                        envelope=self._realization_envelope,
                        previous=previous,
                    )
                )
                - active
            )
            readback_containers = tuple(spec for spec in realization.containers if spec.address in readback)
            if readback_containers:
                result = self._driver.observe(containers=readback_containers)
                diagnostics.extend(result.diagnostics)
                observations = (*observations, *result.observations)
        if delete_networks or delete_containers:
            result = self._driver.destroy(
                networks=tuple(delete_networks),
                containers=tuple(delete_containers),
            )
            diagnostics.extend(result.diagnostics)
        return diagnostics, observations
