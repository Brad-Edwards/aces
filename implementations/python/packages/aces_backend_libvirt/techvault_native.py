"""Native libvirt/QEMU TechVault appliance driver.

This driver realizes the ACES-planned TechVault node/network surface as tiny
QEMU guests booted by libvirt from generated initramfs appliances. It is
intentionally independent from APTL's Docker Compose substrate: the only runtime
substrate boundary here is libvirt.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Protocol, cast
from urllib.parse import urlsplit

from aces_contracts.diagnostics import Diagnostic, Severity

from .driver import (
    DomainHandle,
    DomainSpec,
    DriverResult,
    NetworkHandle,
    NetworkSpec,
    RealizationObservation,
)
from .drivers.libvirt import Connector, _aces_uuid, _error_code, _existing_uuid
from .envelopes import load_libvirt_realization_envelope
from .techvault_appliance import (
    BusyboxInitramfsBuilder,
    InitramfsBuilder,
    copy_kernel_for_libvirt,
    make_libvirt_readable,
)
from .techvault_concerns import techvault_observation_diagnostics, techvault_spec_diagnostics
from .techvault_matrix import (
    as_sequence as _as_sequence,
)
from .techvault_matrix import (
    domain_xml as _domain_xml,
)
from .techvault_matrix import (
    native_matrix as _native_matrix,
)
from .techvault_matrix import (
    network_xml as _network_xml,
)
from .techvault_matrix import (
    runtime_name as _runtime_name,
)
from .techvault_matrix import (
    safe_name as _safe_name,
)
from .techvault_observation import (
    canonical_digest,
    domain_observations,
    file_digest,
    network_observations,
    snapshot_from_observations,
)
from .techvault_probe import (
    NativeLibvirtProbe,
    ProbeResult,
    check_native_readiness,
    expected_surface,
    native_soc_readback,
)

_DOMAIN = "runtime"
_CODE_OPERATION_FAILED = "libvirt-backend.techvault-native.operation-failed"
_CODE_OWNERSHIP_CONFLICT = "libvirt-backend.techvault-native.ownership-conflict"
_CODE_READBACK_FAILED = "libvirt-backend.techvault-native.readback-failed"
_CODE_RESIDUAL_STATE = "libvirt-backend.techvault-native.residual-state"
_CODE_UNAVAILABLE = "libvirt-backend.techvault-native.unavailable"
_DEFAULT_CONNECTION_URI = "qemu:///system"
__all__ = [
    "BusyboxInitramfsBuilder",
    "NativeLibvirtProbe",
    "ProbeResult",
    "TechVaultNativeLibvirtDriver",
    "check_native_readiness",
    "expected_surface",
    "native_soc_readback",
]


class _NativeResource(Protocol):
    def create(self) -> None: ...

    def destroy(self) -> None: ...

    def undefine(self) -> None: ...


class _OwnershipConflict(Exception):
    """A native name is not owned by the requested ACES address."""


@dataclass
class TechVaultNativeLibvirtDriver:
    """Realize TechVault domains directly as libvirt/QEMU appliances."""

    driver_mode: ClassVar[str] = "techvault-appliance"

    state_dir: Path
    connection: object | None = None
    connection_uri: str = _DEFAULT_CONNECTION_URI
    connector: Connector | None = None
    name_prefix: str = "aces-techvault"
    kernel_path: Path | None = None
    initramfs_builder: InitramfsBuilder = field(default_factory=BusyboxInitramfsBuilder)
    define_only: bool = False
    clean_existing: bool = False
    last_snapshot: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.connection_uri or not self.connection_uri.strip():
            raise ValueError("TechVaultNativeLibvirtDriver connection_uri must be non-empty.")
        parsed_uri = urlsplit(self.connection_uri)
        if parsed_uri.username is not None or parsed_uri.password is not None:
            raise ValueError("TechVaultNativeLibvirtDriver connection URI must not carry credentials.")
        if not self.name_prefix or not self.name_prefix.strip():
            raise ValueError("TechVaultNativeLibvirtDriver name_prefix must be non-empty.")
        if self.define_only:
            raise ValueError("TechVaultNativeLibvirtDriver define-only mode cannot make realization claims.")
        if self.clean_existing:
            raise ValueError("TechVaultNativeLibvirtDriver refuses unsafe prefix-wide cleanup.")
        safe_prefix = _safe_name(self.name_prefix, fallback="aces-techvault", prefix="")
        if safe_prefix != self.name_prefix:
            raise ValueError("TechVaultNativeLibvirtDriver name_prefix must already be libvirt-safe.")
        self.state_dir = Path(self.state_dir)
        self.kernel_path = Path(self.kernel_path) if self.kernel_path is not None else _default_kernel_path()
        self.connector = self.connector or _default_connector
        self._names: dict[str, str] = {}
        self._realized: set[str] = set()
        self._artifacts: dict[str, tuple[Path, ...]] = {}

    def realize(
        self,
        *,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
    ) -> DriverResult:
        envelope = load_libvirt_realization_envelope(self.driver_mode)
        spec_diagnostics = techvault_spec_diagnostics(
            networks=networks,
            domains=domains,
            envelope=envelope,
            name_prefix=self.name_prefix,
        )
        if spec_diagnostics:
            return DriverResult(diagnostics=tuple(spec_diagnostics))
        matrix = _native_matrix(networks=networks, domains=domains, name_prefix=self.name_prefix)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            connection = self._conn()
        except Exception:
            return DriverResult(diagnostics=(_diagnostic(_CODE_UNAVAILABLE, "runtime.libvirt.connection"),))
        network_handles, network_diagnostics, network_observations = self._define_networks(connection, matrix)
        if network_diagnostics:
            network_diagnostics.extend(self._rollback(connection, network_handles, ()))
            return DriverResult(diagnostics=tuple(network_diagnostics))
        domain_handles, domain_diagnostics, domain_observations = self._define_domains(connection, matrix)
        if domain_diagnostics:
            domain_diagnostics.extend(self._rollback(connection, network_handles, domain_handles))
            return DriverResult(diagnostics=tuple(domain_diagnostics))
        observations = tuple((*network_observations, *domain_observations))
        observation_diagnostics = techvault_observation_diagnostics(
            networks=networks,
            domains=domains,
            result=DriverResult(observations=observations),
        )
        if observation_diagnostics:
            observation_diagnostics.extend(self._rollback(connection, network_handles, domain_handles))
            return DriverResult(diagnostics=tuple(observation_diagnostics))
        try:
            binding = self._material_binding(envelope.digest, envelope.configuration.configuration_digest)
            snapshot = snapshot_from_observations(matrix, observations, binding=binding)
        except Exception:
            binding_diagnostics = [_diagnostic(_CODE_OPERATION_FAILED, "runtime.libvirt.binding")]
            binding_diagnostics.extend(self._rollback(connection, network_handles, domain_handles))
            return DriverResult(diagnostics=tuple(binding_diagnostics))
        self.last_snapshot = snapshot
        return DriverResult(
            networks=tuple(network_handles),
            domains=tuple(domain_handles),
            observations=observations,
        )

    def _define_networks(
        self, connection: object, matrix: Mapping[str, object]
    ) -> tuple[list[NetworkHandle], list[Diagnostic], list[RealizationObservation]]:
        handles: list[NetworkHandle] = []
        diagnostics: list[Diagnostic] = []
        observations: list[RealizationObservation] = []
        for network in _as_sequence(matrix.get("networks")):
            if isinstance(network, Mapping):
                handle, diagnostic, observed = self._define_network(connection, network)
                if handle is not None:
                    handles.append(handle)
                if diagnostic is not None:
                    diagnostics.append(diagnostic)
                observations.extend(observed)
                if diagnostic is not None:
                    break
        return handles, diagnostics, observations

    def _define_network(
        self, connection: object, network: Mapping[str, object]
    ) -> tuple[NetworkHandle | None, Diagnostic | None, tuple[RealizationObservation, ...]]:
        address = str(network.get("address", ""))
        native: _NativeResource | None = None
        self._names[address] = str(network.get("runtime_name", ""))
        try:
            _ensure_name_available(
                connection,
                "networkLookupByName",
                str(network.get("runtime_name", "")),
                address,
            )
            native = _call(connection, "networkDefineXML", _network_xml(network))
            if not self.define_only:
                native.create()
        except _OwnershipConflict:
            self._names.pop(address, None)
            return None, _diagnostic(_CODE_OWNERSHIP_CONFLICT, address), ()
        except Exception:
            if native is None:
                self._names.pop(address, None)
                return None, _diagnostic(_CODE_OPERATION_FAILED, address), ()
            self._realized.add(address)
            return NetworkHandle(address=address), _diagnostic(_CODE_OPERATION_FAILED, address), ()
        self._realized.add(address)
        handle = NetworkHandle(address=address, realized=True)
        try:
            observations = network_observations(native, network)
        except Exception:
            return handle, _diagnostic(_CODE_READBACK_FAILED, address), ()
        return handle, None, observations

    def _define_domains(
        self, connection: object, matrix: Mapping[str, object]
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
                handle, diagnostic, observed = self._define_domain(connection, domain, network_addresses)
                if handle is not None:
                    handles.append(handle)
                if diagnostic is not None:
                    diagnostics.append(diagnostic)
                observations.extend(observed)
                if diagnostic is not None:
                    break
        return handles, diagnostics, observations

    def _define_domain(
        self,
        connection: object,
        domain: Mapping[str, object],
        network_addresses: Mapping[str, str],
    ) -> tuple[DomainHandle | None, Diagnostic | None, tuple[RealizationObservation, ...]]:
        address = str(domain.get("address", ""))
        native: _NativeResource | None = None
        initrd: Path | None = None
        self._names[address] = str(domain.get("runtime_name", ""))
        try:
            _ensure_name_available(
                connection,
                "lookupByName",
                str(domain.get("runtime_name", "")),
                address,
            )
            kernel = copy_kernel_for_libvirt(
                self.kernel_path,
                self.state_dir / "kernel" / f"{_artifact_token(address)}-{self.kernel_path.name}",
            )
            initrd = self.initramfs_builder.build(
                domain=domain,
                target=self.state_dir / "initramfs" / f"{_artifact_token(address)}.cpio.gz",
            )
            make_libvirt_readable(initrd)
            self._artifacts[address] = (kernel, initrd)
            native = _call(connection, "defineXML", _domain_xml(domain, kernel=kernel, initrd=initrd))
            if not self.define_only:
                native.create()
        except _OwnershipConflict:
            self._names.pop(address, None)
            return None, _diagnostic(_CODE_OWNERSHIP_CONFLICT, address), ()
        except Exception:
            if native is None:
                self._cleanup_artifacts(address)
                self._names.pop(address, None)
                return None, _diagnostic(_CODE_OPERATION_FAILED, address), ()
            self._realized.add(address)
            return DomainHandle(address=address), _diagnostic(_CODE_OPERATION_FAILED, address), ()
        self._realized.add(address)
        handle = DomainHandle(address=address, realized=True)
        try:
            observations = domain_observations(
                native,
                domain,
                network_addresses,
                kernel=kernel,
                initrd=initrd,
            )
        except Exception:
            return handle, _diagnostic(_CODE_READBACK_FAILED, address), ()
        return handle, None, observations

    def destroy(
        self,
        *,
        networks: tuple[str, ...],
        domains: tuple[str, ...],
    ) -> DriverResult:
        try:
            connection = self._conn()
        except Exception:
            return DriverResult(diagnostics=(_diagnostic(_CODE_UNAVAILABLE, "runtime.libvirt.connection"),))
        domain_handles: list[DomainHandle] = []
        network_handles: list[NetworkHandle] = []
        diagnostics: list[Diagnostic] = []
        for address in domains:
            try:
                ok = self._destroy_one(connection, "lookupByName", address)
            except _OwnershipConflict:
                diagnostics.append(_diagnostic(_CODE_OWNERSHIP_CONFLICT, address))
                domain_handles.append(DomainHandle(address=address, realized=True))
                continue
            if not ok:
                diagnostics.append(_diagnostic(_CODE_RESIDUAL_STATE, address))
            domain_handles.append(DomainHandle(address=address, realized=not ok))
        for address in networks:
            try:
                ok = self._destroy_one(connection, "networkLookupByName", address)
            except _OwnershipConflict:
                diagnostics.append(_diagnostic(_CODE_OWNERSHIP_CONFLICT, address))
                network_handles.append(NetworkHandle(address=address, realized=True))
                continue
            if not ok:
                diagnostics.append(_diagnostic(_CODE_RESIDUAL_STATE, address))
            network_handles.append(NetworkHandle(address=address, realized=not ok))
        if (networks or domains) and not diagnostics:
            self.last_snapshot = {}
        return DriverResult(
            networks=tuple(network_handles),
            domains=tuple(domain_handles),
            diagnostics=tuple(diagnostics),
        )

    def realized_addresses(self) -> frozenset[str]:
        return frozenset(self._realized)

    def _conn(self) -> object:
        if self.connection is None:
            assert self.connector is not None
            self.connection = self.connector(self.connection_uri)
        if self.connection is None:
            raise RuntimeError("libvirt connection unavailable")
        return self.connection

    def _destroy_one(self, connection: object, lookup_method: str, address: str) -> bool:
        list_method = "listAllDomains" if lookup_method == "lookupByName" else "listAllNetworks"
        name = self._names.get(address)
        lookup = getattr(connection, lookup_method, None)
        if not callable(lookup):
            return False
        if name is None:
            native_items = _list_native(connection, list_method)
            if native_items is None:
                return False
            owned = [item for item in native_items if _existing_uuid(item) == _aces_uuid(address)]
            if not owned:
                fallback_name = _runtime_name(self.name_prefix, address)
                if any(_native_name(item) == fallback_name for item in native_items):
                    raise _OwnershipConflict(address)
                self._record_verified_absence(address)
                return True
            if len(owned) != 1:
                return False
            native = owned[0]
            name = _native_name(native)
            if not name:
                return False
        else:
            try:
                native = lookup(name)
            except KeyError:
                return self._verify_absence_by_uuid(connection, list_method, address)
            except Exception as exc:
                if _error_code(exc) in {42, 43}:
                    return self._verify_absence_by_uuid(connection, list_method, address)
                return False
        if _existing_uuid(native) != _aces_uuid(address):
            raise _OwnershipConflict(address)
        try:
            native.destroy()
        except Exception as exc:
            if _error_code(exc) not in {42, 43, 55}:
                return False
        try:
            native.undefine()
        except Exception as exc:
            if _error_code(exc) not in {42, 43}:
                return False
        native_items = _list_native(connection, list_method)
        if native_items is None or any(_native_name(item) == name for item in native_items):
            return False
        if any(_existing_uuid(item) == _aces_uuid(address) for item in native_items):
            return False
        self._record_verified_absence(address)
        return True

    def _verify_absence_by_uuid(self, connection: object, list_method: str, address: str) -> bool:
        native_items = _list_native(connection, list_method)
        if native_items is None or any(_existing_uuid(item) == _aces_uuid(address) for item in native_items):
            return False
        self._record_verified_absence(address)
        return True

    def _record_verified_absence(self, address: str) -> None:
        self._realized.discard(address)
        self._names.pop(address, None)
        self._cleanup_artifacts(address)

    def _cleanup_artifacts(self, address: str) -> None:
        token = _artifact_token(address)
        paths = set(self._artifacts.pop(address, ()))
        paths.add(self.state_dir / "initramfs" / f"{token}.cpio.gz")
        paths.update((self.state_dir / "kernel").glob(f"{token}-*"))
        for path in paths:
            with suppress(OSError):
                path.unlink()

    def _material_binding(self, envelope_digest: str, configuration_digest: str) -> dict[str, object]:
        kernel_digests = {address: file_digest(paths[0]) for address, paths in sorted(self._artifacts.items())}
        initramfs_digests = {address: file_digest(paths[1]) for address, paths in sorted(self._artifacts.items())}
        boot_artifacts = {
            "kernel": canonical_digest(kernel_digests),
            "initramfs": canonical_digest(initramfs_digests),
        }
        material = {
            "driver": self.driver_mode,
            "configuration_digest": configuration_digest,
            "boot_artifact_digests": boot_artifacts,
            "connection_uri_digest": canonical_digest(self.connection_uri),
            "name_prefix_digest": canonical_digest(self.name_prefix),
        }
        return {
            **material,
            "realization_envelope_digest": envelope_digest,
            "driver_configuration_digest": canonical_digest(material),
        }

    def _rollback(
        self,
        connection: object,
        networks: Sequence[NetworkHandle],
        domains: Sequence[DomainHandle],
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for handle in domains:
            if handle.realized:
                try:
                    cleaned = self._destroy_one(connection, "lookupByName", handle.address)
                except Exception:
                    cleaned = False
                if not cleaned:
                    diagnostics.append(_diagnostic(_CODE_RESIDUAL_STATE, handle.address))
        for handle in networks:
            if handle.realized:
                try:
                    cleaned = self._destroy_one(connection, "networkLookupByName", handle.address)
                except Exception:
                    cleaned = False
                if not cleaned:
                    diagnostics.append(_diagnostic(_CODE_RESIDUAL_STATE, handle.address))
        return diagnostics


def _default_connector(connection_uri: str) -> object | None:
    import importlib

    libvirt = importlib.import_module("libvirt")
    return libvirt.open(connection_uri)


def _call(connection: object, method_name: str, payload: str) -> _NativeResource:
    method = cast(Callable[[str], _NativeResource], getattr(connection, method_name))
    return method(payload)


def _ensure_name_available(connection: object, method_name: str, name: str, address: str) -> None:
    method = getattr(connection, method_name, None)
    if not callable(method):
        raise RuntimeError("native lookup is unavailable")
    try:
        native = method(name)
    except KeyError:
        return
    except Exception as exc:
        if _error_code(exc) in {42, 43}:
            return
        raise
    if _existing_uuid(native) != _aces_uuid(address):
        raise _OwnershipConflict(address)
    raise RuntimeError("owned native object already exists for CREATE")


def _list_native(connection: object, method_name: str) -> tuple[object, ...] | None:
    method = getattr(connection, method_name, None)
    if not callable(method):
        return None
    try:
        native = method()
    except Exception:
        return None
    return tuple(native) if isinstance(native, list | tuple) else None


def _native_name(native: object) -> str:
    method = getattr(native, "name", None)
    if not callable(method):
        return ""
    try:
        value = method()
    except Exception:
        return ""
    return value if isinstance(value, str) else ""


def _artifact_token(address: str) -> str:
    return _aces_uuid(address).replace("-", "")


def _default_kernel_path() -> Path:
    running = Path(f"/boot/vmlinuz-{os.uname().release}")
    if running.exists():
        return running
    candidates = sorted(Path("/boot").glob("vmlinuz-*"))
    return candidates[-1] if candidates else Path("/boot/vmlinuz")


def _diagnostic(code: str, address: str) -> Diagnostic:
    if code == _CODE_UNAVAILABLE:
        message = "Libvirt connection is unavailable for native TechVault realization."
    elif code == _CODE_RESIDUAL_STATE:
        message = f"Native TechVault rollback could not verify cleanup for '{address}'; residual state may remain."
    elif code == _CODE_OWNERSHIP_CONFLICT:
        message = f"Native object for '{address}' is not owned by that ACES address; refusing mutation."
    elif code == _CODE_READBACK_FAILED:
        message = f"Native libvirt TechVault readback for '{address}' did not succeed."
    else:
        message = f"Native libvirt TechVault operation for '{address}' did not succeed."
    return Diagnostic(code=code, domain=_DOMAIN, address=address, message=message, severity=Severity.ERROR)
