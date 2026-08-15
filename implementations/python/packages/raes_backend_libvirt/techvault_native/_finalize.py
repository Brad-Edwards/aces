"""Post-realization verification and snapshot finalization for the native driver."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING

from raes_backend_libvirt._observability import LOGGER as _LOGGER
from raes_backend_libvirt._observability import NATIVE_FAILURE_LOG as _NATIVE_FAILURE_LOG

from .._techvault_native_ops import _CODE_OPERATION_FAILED, _diagnostic
from ..driver import (
    DomainHandle,
    DomainSpec,
    DriverResult,
    NetworkHandle,
    NetworkSpec,
    RealizationObservation,
)
from ..techvault_concerns import techvault_observation_diagnostics
from ..techvault_observation import snapshot_from_observations

if TYPE_CHECKING:
    from ._driver import TechVaultNativeLibvirtDriver


def _verify_and_finalize(
    driver: TechVaultNativeLibvirtDriver,
    connection: object,
    matrix: Mapping[str, object],
    *,
    specs: tuple[tuple[NetworkSpec, ...], tuple[DomainSpec, ...]],
    handles: tuple[list[NetworkHandle], list[DomainHandle]],
    observations: tuple[RealizationObservation, ...],
    envelope_digest: str,
    configuration_digest: str,
) -> DriverResult:
    networks, domains = specs
    network_handles, domain_handles = handles
    observations = tuple(
        replace(
            observation,
            envelope_digest=envelope_digest,
            configuration_digest=configuration_digest,
        )
        if observation.concern.value == "compute-substrate"
        else observation
        for observation in observations
    )
    diagnostics = techvault_observation_diagnostics(
        networks=networks,
        domains=domains,
        result=DriverResult(observations=observations),
    )
    # Staged: the guest observation runs only after the daemon gate passes and a
    # later stage never repairs an earlier one.
    guest_observations: tuple[RealizationObservation, ...] = ()
    if not diagnostics:
        guest_observations, diagnostics = driver._guest_stage(connection, matrix, specs, observations)
    if diagnostics:
        diagnostics.extend(driver._rollback(connection, network_handles, domain_handles))
        return DriverResult(diagnostics=tuple(diagnostics))
    try:
        binding = driver._material_binding(envelope_digest, configuration_digest)
        snapshot = snapshot_from_observations(matrix, observations, binding=binding)
    except Exception as exc:
        _LOGGER.debug(_NATIVE_FAILURE_LOG, "_verify_and_finalize", exc_info=exc)
        binding_diagnostics = [_diagnostic(_CODE_OPERATION_FAILED, "runtime.libvirt.binding")]
        binding_diagnostics.extend(driver._rollback(connection, network_handles, domain_handles))
        return DriverResult(diagnostics=tuple(binding_diagnostics))
    driver.last_snapshot = snapshot
    return DriverResult(
        networks=tuple(network_handles),
        domains=tuple(domain_handles),
        observations=(*observations, *guest_observations),
    )
