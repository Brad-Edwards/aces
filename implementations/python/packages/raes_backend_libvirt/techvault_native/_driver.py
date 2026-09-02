"""Native libvirt/QEMU TechVault appliance driver.

This driver realizes the RAES-planned TechVault node/network surface as tiny
QEMU guests booted by libvirt from generated initramfs appliances. It is
intentionally independent from APTL's Docker Compose substrate: the only runtime
substrate boundary here is libvirt.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

from raes_contracts.diagnostics import Diagnostic

from raes_backend_libvirt._observability import record_suppressed_failure as _record_suppressed_failure

from .._techvault_native_helpers import (
    default_connector as _default_connector,
)
from .._techvault_native_helpers import (
    default_kernel_path as _default_kernel_path,
)
from .._techvault_native_ops import (
    _CODE_OPERATION_FAILED,
    _CODE_OWNERSHIP_CONFLICT,
    _CODE_RESIDUAL_STATE,
    _CODE_UNAVAILABLE,
    _DEFAULT_CONNECTION_URI,
    _artifact_token,
    _diagnostic,
)
from ._finalize import _verify_and_finalize

if TYPE_CHECKING:
    from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel

from ..driver import (
    DomainHandle,
    DomainSpec,
    DriverResult,
    NetworkHandle,
    NetworkSpec,
    RealizationObservation,
)
from ..drivers.libvirt import Connector, _existing_uuid, _raes_uuid
from ..envelopes import load_libvirt_realization_envelope
from ..techvault_appliance import BusyboxInitramfsBuilder, InitramfsBuilder
from ..techvault_concerns import techvault_spec_diagnostics
from ..techvault_lifecycle import (
    NativeOwnershipConflict as _OwnershipConflict,
)
from ..techvault_lifecycle import NativeResolution as _NativeResolution
from ..techvault_lifecycle import (
    deactivate_and_undefine as _deactivate_and_undefine,
)
from ..techvault_lifecycle import (
    resolve_native as _resolve_native,
)
from ..techvault_lifecycle import (
    verify_native_removed as _verify_native_removed,
)
from ..techvault_matrix import (
    domain_xml as _domain_xml,
)
from ..techvault_matrix import (
    native_matrix as _native_matrix,
)
from ..techvault_observation import (
    canonical_digest,
    file_digest,
    native_active,
    substrate_observation,
)
from ._define import define_domain, define_domains, define_network, define_networks
from ._preflight import artifact_preflight_diagnostics, validate_driver_configuration

_CONNECTION_ADDRESS = "runtime.libvirt.connection"


@dataclass
class TechVaultNativeLibvirtDriver:
    """Realize TechVault domains directly as libvirt/QEMU appliances."""

    driver_mode: ClassVar[str] = "techvault-appliance"

    state_dir: Path
    connection: object | None = None
    connection_uri: str = _DEFAULT_CONNECTION_URI
    connector: Connector | None = None
    name_prefix: str = "raes-techvault"
    kernel_path: Path | None = None
    initramfs_builder: InitramfsBuilder = field(default_factory=BusyboxInitramfsBuilder)
    define_only: bool = False
    clean_existing: bool = False
    last_snapshot: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_driver_configuration(
            connection_uri=self.connection_uri,
            name_prefix=self.name_prefix,
            define_only=self.define_only,
            clean_existing=self.clean_existing,
        )
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
        self._begin_operation()
        envelope = load_libvirt_realization_envelope(self.driver_mode)
        diagnostics = self._admission_diagnostics(networks, domains, envelope)
        if not diagnostics:
            diagnostics = self._artifact_preflight_diagnostics(domains)
        if diagnostics:
            result = DriverResult(diagnostics=tuple(diagnostics))
        else:
            matrix = self._build_matrix(networks, domains)
            self.state_dir.mkdir(parents=True, exist_ok=True)
            diagnostics = self._prepare_operation(matrix)
            if diagnostics:
                result = DriverResult(diagnostics=tuple(diagnostics))
            else:
                try:
                    connection = self._conn()
                except Exception as exc:
                    _record_suppressed_failure("realize", exc)
                    result = DriverResult(diagnostics=(_diagnostic(_CODE_UNAVAILABLE, _CONNECTION_ADDRESS),))
                else:
                    result = self._realize_matrix(
                        connection,
                        matrix,
                        networks=networks,
                        domains=domains,
                        envelope_digest=envelope.digest,
                        configuration_digest=envelope.configuration.configuration_digest,
                    )
        return result

    def _realize_matrix(
        self,
        connection: object,
        matrix: Mapping[str, object],
        *,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
        envelope_digest: str,
        configuration_digest: str,
    ) -> DriverResult:
        network_handles, network_diagnostics, network_observations = self._define_networks(connection, matrix)
        if network_diagnostics:
            network_diagnostics.extend(self._rollback(connection, network_handles, ()))
            return DriverResult(diagnostics=tuple(network_diagnostics))
        domain_handles, domain_diagnostics, domain_observations = self._define_domains(connection, matrix)
        if domain_diagnostics:
            domain_diagnostics.extend(self._rollback(connection, network_handles, domain_handles))
            return DriverResult(diagnostics=tuple(domain_diagnostics))
        observations = (*network_observations, *domain_observations)
        return _verify_and_finalize(
            self,
            connection,
            matrix,
            specs=(networks, domains),
            handles=(network_handles, domain_handles),
            observations=observations,
            binding_digests=(envelope_digest, configuration_digest),
        )

    def _admission_diagnostics(
        self,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
        envelope: object,
    ) -> list[Diagnostic]:
        return techvault_spec_diagnostics(
            networks=networks,
            domains=domains,
            envelope=cast("BackendRealizationEnvelopeModel", envelope),
            name_prefix=self.name_prefix,
        )

    def _build_matrix(
        self,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
    ) -> dict[str, object]:
        return _native_matrix(networks=networks, domains=domains, name_prefix=self.name_prefix)

    def _artifact_preflight_diagnostics(self, domains: tuple[DomainSpec, ...]) -> list[Diagnostic]:
        return artifact_preflight_diagnostics(
            domains=domains,
            kernel_path=self.kernel_path,
            initramfs_builder=self.initramfs_builder,
        )

    @staticmethod
    def _begin_operation() -> None:
        """Clear operation-scoped subclass evidence before any admission gate."""

    @staticmethod
    def _prepare_operation(matrix: Mapping[str, object]) -> list[Diagnostic]:
        """Prepare operation-scoped evidence state before opening libvirt."""

        del matrix
        return []

    # Base extension hooks need no instance state; the guest-certified subclass overrides them.
    @staticmethod
    def _render_domain_xml(domain: Mapping[str, object], *, kernel: Path, initrd: Path) -> str:
        return _domain_xml(domain, kernel=kernel, initrd=initrd)

    @staticmethod
    def _guest_stage(
        connection: object,
        matrix: Mapping[str, object],
        specs: tuple[tuple[NetworkSpec, ...], tuple[DomainSpec, ...]],
        observations: tuple[RealizationObservation, ...],
    ) -> tuple[tuple[RealizationObservation, ...], list[Diagnostic]]:
        """Daemon-only modes contribute no guest observations; subclasses override."""

        del connection, matrix, specs, observations
        return (), []

    def _define_networks(
        self, connection: object, matrix: Mapping[str, object]
    ) -> tuple[list[NetworkHandle], list[Diagnostic], list[RealizationObservation]]:
        return define_networks(self, connection, matrix)

    def _define_network(
        self, connection: object, network: Mapping[str, object]
    ) -> tuple[NetworkHandle | None, Diagnostic | None, tuple[RealizationObservation, ...]]:
        return define_network(self, connection, network)

    def _define_domains(
        self, connection: object, matrix: Mapping[str, object]
    ) -> tuple[list[DomainHandle], list[Diagnostic], list[RealizationObservation]]:
        return define_domains(self, connection, matrix)

    def _define_domain(
        self,
        connection: object,
        domain: Mapping[str, object],
        network_addresses: Mapping[str, str],
    ) -> tuple[DomainHandle | None, Diagnostic | None, tuple[RealizationObservation, ...]]:
        return define_domain(self, connection, domain, network_addresses)

    def destroy(
        self,
        *,
        networks: tuple[str, ...],
        domains: tuple[str, ...],
    ) -> DriverResult:
        try:
            connection = self._conn()
        except Exception as exc:
            _record_suppressed_failure("destroy", exc)
            return DriverResult(diagnostics=(_diagnostic(_CODE_UNAVAILABLE, _CONNECTION_ADDRESS),))
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

    def observe(self, *, domains: tuple[DomainSpec, ...]) -> DriverResult:
        """Read current owned domains without defining or restarting them."""

        try:
            connection = self._conn()
        except Exception as exc:
            _record_suppressed_failure("observe", exc)
            return DriverResult(diagnostics=(_diagnostic(_CODE_UNAVAILABLE, _CONNECTION_ADDRESS),))
        envelope = load_libvirt_realization_envelope(self.driver_mode)
        observations: list[RealizationObservation] = []
        handles: list[DomainHandle] = []
        diagnostics: list[Diagnostic] = []
        for spec in domains:
            resolved = self._observed_domain(connection, spec.address)
            if resolved is None:
                diagnostics.append(_diagnostic(_CODE_OPERATION_FAILED, spec.address))
                continue
            if resolved.name is not None:
                self._names[spec.address] = resolved.name
            self._realized.add(spec.address)
            handles.append(DomainHandle(address=spec.address, realized=True))
            observations.append(
                replace(
                    substrate_observation(spec.address),
                    envelope_digest=envelope.digest,
                    configuration_digest=envelope.configuration.configuration_digest,
                    sequence=len(observations),
                )
            )
        return DriverResult(
            domains=tuple(handles),
            diagnostics=tuple(diagnostics),
            observations=tuple(observations),
        )

    def _observed_domain(self, connection: object, address: str) -> _NativeResolution | None:
        try:
            resolved = _resolve_native(
                connection,
                "lookupByName",
                "listAllDomains",
                address,
                known_name=self._names.get(address),
                name_prefix=self.name_prefix,
            )
            native = None if resolved is None else resolved.native
            if native is None or _existing_uuid(native) != _raes_uuid(address) or not native_active(native):
                return None
        except Exception as exc:
            _record_suppressed_failure("_observed_domain", exc)
            return None
        return resolved

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
        resolved = _resolve_native(
            connection,
            lookup_method,
            list_method,
            address,
            known_name=self._names.get(address),
            name_prefix=self.name_prefix,
        )
        cleaned = False
        if resolved is not None:
            if resolved.native is None:
                cleaned = True
            else:
                if _existing_uuid(resolved.native) != _raes_uuid(address):
                    raise _OwnershipConflict(address)
                removed = _deactivate_and_undefine(resolved.native)
                cleaned = removed and _verify_native_removed(
                    connection,
                    list_method,
                    address,
                    resolved.name,
                )
        if cleaned:
            self._record_verified_absence(address)
        return cleaned

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
        return [
            *self._rollback_handles(connection, domains, "lookupByName"),
            *self._rollback_handles(connection, networks, "networkLookupByName"),
        ]

    def _rollback_handles(
        self,
        connection: object,
        handles: Sequence[DomainHandle | NetworkHandle],
        lookup_method: str,
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for handle in handles:
            if handle.realized and not self._try_destroy(connection, lookup_method, handle.address):
                diagnostics.append(_diagnostic(_CODE_RESIDUAL_STATE, handle.address))
        return diagnostics

    def _try_destroy(self, connection: object, lookup_method: str, address: str) -> bool:
        try:
            return self._destroy_one(connection, lookup_method, address)
        except Exception as exc:
            _record_suppressed_failure("_try_destroy", exc)
            return False
