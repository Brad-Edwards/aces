"""Define-stage helpers for the native TechVault libvirt driver.

Pure lifecycle helpers behind the driver's ``_define_*`` method seams: ownership
checked network/domain definition, readback, and artifact staging. Kept separate
from :mod:`._driver` only for the ADR-015 size cap; the driver delegates to these
and the subclass override points (``_render_domain_xml``) still dispatch through
the passed ``driver`` instance.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from raes_contracts.diagnostics import Diagnostic

from raes_backend_libvirt._observability import LOGGER as _LOGGER
from raes_backend_libvirt._observability import NATIVE_FAILURE_LOG as _NATIVE_FAILURE_LOG

from .._techvault_native_ops import (
    _CODE_OPERATION_FAILED,
    _CODE_OWNERSHIP_CONFLICT,
    _CODE_READBACK_FAILED,
    _artifact_token,
    _call,
    _diagnostic,
    _ensure_name_available,
    _NativeResource,
)
from ..driver import DomainHandle, NetworkHandle, RealizationObservation
from ..techvault_appliance import copy_kernel_for_libvirt, make_libvirt_readable
from ..techvault_lifecycle import NativeOwnershipConflict as _OwnershipConflict
from ..techvault_matrix import as_sequence as _as_sequence
from ..techvault_matrix import network_xml as _network_xml
from ..techvault_observation import domain_observations, network_observations

if TYPE_CHECKING:
    from ._driver import TechVaultNativeLibvirtDriver


def define_networks(
    driver: TechVaultNativeLibvirtDriver, connection: object, matrix: Mapping[str, object]
) -> tuple[list[NetworkHandle], list[Diagnostic], list[RealizationObservation]]:
    handles: list[NetworkHandle] = []
    diagnostics: list[Diagnostic] = []
    observations: list[RealizationObservation] = []
    for network in _as_sequence(matrix.get("networks")):
        if isinstance(network, Mapping):
            handle, diagnostic, observed = driver._define_network(connection, network)
            if handle is not None:
                handles.append(handle)
            if diagnostic is not None:
                diagnostics.append(diagnostic)
            observations.extend(observed)
            if diagnostic is not None:
                break
    return handles, diagnostics, observations


def define_network(
    driver: TechVaultNativeLibvirtDriver, connection: object, network: Mapping[str, object]
) -> tuple[NetworkHandle | None, Diagnostic | None, tuple[RealizationObservation, ...]]:
    address = str(network.get("address", ""))
    native: _NativeResource | None = None
    handle: NetworkHandle | None = None
    diagnostic: Diagnostic | None = None
    observations: tuple[RealizationObservation, ...] = ()
    driver._names[address] = str(network.get("runtime_name", ""))
    try:
        _ensure_name_available(
            connection,
            "networkLookupByName",
            str(network.get("runtime_name", "")),
            address,
        )
        native = _call(connection, "networkDefineXML", _network_xml(network))
        if not driver.define_only:
            native.create()
    except _OwnershipConflict:
        driver._names.pop(address, None)
        diagnostic = _diagnostic(_CODE_OWNERSHIP_CONFLICT, address)
    except Exception as exc:
        _LOGGER.debug(_NATIVE_FAILURE_LOG, "define_network", exc_info=exc)
        if native is None:
            driver._names.pop(address, None)
        else:
            driver._realized.add(address)
            handle = NetworkHandle(address=address)
        diagnostic = _diagnostic(_CODE_OPERATION_FAILED, address)
    else:
        driver._realized.add(address)
        handle = NetworkHandle(address=address, realized=True)
        try:
            observations = network_observations(native, network)
        except Exception as exc:
            _LOGGER.debug(_NATIVE_FAILURE_LOG, "define_network", exc_info=exc)
            diagnostic = _diagnostic(_CODE_READBACK_FAILED, address)
    return handle, diagnostic, observations


def define_domains(
    driver: TechVaultNativeLibvirtDriver, connection: object, matrix: Mapping[str, object]
) -> tuple[list[DomainHandle], list[Diagnostic], list[RealizationObservation]]:
    handles: list[DomainHandle] = []
    diagnostics: list[Diagnostic] = []
    observations: list[RealizationObservation] = []
    network_addresses = {
        str(item.get("runtime_name", "")): str(item.get("address", ""))
        for item in _as_sequence(matrix.get("networks"))
        if isinstance(item, Mapping)
    }
    for domain in _as_sequence(matrix.get("domains")):
        if isinstance(domain, Mapping):
            handle, diagnostic, observed = driver._define_domain(connection, domain, network_addresses)
            if handle is not None:
                handles.append(handle)
            if diagnostic is not None:
                diagnostics.append(diagnostic)
            observations.extend(observed)
            if diagnostic is not None:
                break
    return handles, diagnostics, observations


def define_domain(
    driver: TechVaultNativeLibvirtDriver,
    connection: object,
    domain: Mapping[str, object],
    network_addresses: Mapping[str, str],
) -> tuple[DomainHandle | None, Diagnostic | None, tuple[RealizationObservation, ...]]:
    address = str(domain.get("address", ""))
    native: _NativeResource | None = None
    handle: DomainHandle | None = None
    diagnostic: Diagnostic | None = None
    observations: tuple[RealizationObservation, ...] = ()
    driver._names[address] = str(domain.get("runtime_name", ""))
    try:
        _ensure_name_available(
            connection,
            "lookupByName",
            str(domain.get("runtime_name", "")),
            address,
        )
        kernel = copy_kernel_for_libvirt(
            driver.kernel_path,
            driver.state_dir / "kernel" / f"{_artifact_token(address)}-{driver.kernel_path.name}",
        )
        initrd = driver.initramfs_builder.build(
            domain=domain,
            target=driver.state_dir / "initramfs" / f"{_artifact_token(address)}.cpio.gz",
        )
        make_libvirt_readable(initrd)
        driver._artifacts[address] = (kernel, initrd)
        native = _call(connection, "defineXML", driver._render_domain_xml(domain, kernel=kernel, initrd=initrd))
        if not driver.define_only:
            native.create()
    except _OwnershipConflict:
        driver._names.pop(address, None)
        diagnostic = _diagnostic(_CODE_OWNERSHIP_CONFLICT, address)
    except Exception as exc:
        _LOGGER.debug(_NATIVE_FAILURE_LOG, "define_domain", exc_info=exc)
        if native is None:
            driver._cleanup_artifacts(address)
            driver._names.pop(address, None)
        else:
            driver._realized.add(address)
            handle = DomainHandle(address=address)
        diagnostic = _diagnostic(_CODE_OPERATION_FAILED, address)
    else:
        driver._realized.add(address)
        handle = DomainHandle(address=address, realized=True)
        try:
            observations = domain_observations(
                native,
                domain,
                network_addresses,
                kernel=kernel,
                initrd=initrd,
            )
        except Exception as exc:
            _LOGGER.debug(_NATIVE_FAILURE_LOG, "define_domain", exc_info=exc)
            diagnostic = _diagnostic(_CODE_READBACK_FAILED, address)
    return handle, diagnostic, observations
