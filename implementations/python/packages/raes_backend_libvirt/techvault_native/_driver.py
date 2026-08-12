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
from urllib.parse import urlsplit

from raes_contracts.diagnostics import Diagnostic

from .._techvault_native_helpers import default_connector as _default_connector
from .._techvault_native_helpers import default_kernel_path as _default_kernel_path
from .._techvault_native_ops import (
    _CODE_OPERATION_FAILED,
    _CODE_OWNERSHIP_CONFLICT,
    _CODE_RESIDUAL_STATE,
    _CODE_UNAVAILABLE,
    _DEFAULT_CONNECTION_URI,
    _artifact_token,
    _diagnostic,
)

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
from ..techvault_concerns import techvault_observation_diagnostics, techvault_spec_diagnostics
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
from ..techvault_matrix import (
    safe_name as _safe_name,
)
from ..techvault_observation import (
    canonical_digest,
    file_digest,
    native_active,
    snapshot_from_observations,
    substrate_observation,
)
from ._define import define_domain, define_domains, define_network, define_networks


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
        self._validate_connection_uri()
        self._validate_appliance_flags()
        self.state_dir = Path(self.state_dir)
        self.kernel_path = Path(self.kernel_path) if self.kernel_path is not None else _default_kernel_path()
        self.connector = self.connector or _default_connector
        self._names: dict[str, str] = {}
        self._realized: set[str] = set()
        self._artifacts: dict[str, tuple[Path, ...]] = {}

    def _validate_connection_uri(self) -> None:
        if not self.connection_uri or not self.connection_uri.strip():
            raise ValueError("TechVaultNativeLibvirtDriver connection_uri must be non-empty.")
        parsed_uri = urlsplit(self.connection_uri)
        if parsed_uri.username is not None or parsed_uri.password is not None:
            raise ValueError("TechVaultNativeLibvirtDriver connection URI must not carry credentials.")

    def _validate_appliance_flags(self) -> None:
        if not self.name_prefix or not self.name_prefix.strip():
            raise ValueError("TechVaultNativeLibvirtDriver name_prefix must be non-empty.")
        if self.define_only:
            raise ValueError("TechVaultNativeLibvirtDriver define-only mode cannot make realization claims.")
        if self.clean_existing:
            raise ValueError("TechVaultNativeLibvirtDriver refuses unsafe prefix-wide cleanup.")
        safe_prefix = _safe_name(self.name_prefix, fallback="raes-techvault", prefix="")
        if safe_prefix != self.name_prefix:
            raise ValueError("TechVaultNativeLibvirtDriver name_prefix must already be libvirt-safe.")

    def realize(
        self,
        *,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
    ) -> DriverResult:
        envelope = load_libvirt_realization_envelope(self.driver_mode)
        spec_diagnostics = self._admission_diagnostics(networks, domains, envelope)
        if spec_diagnostics:
            return DriverResult(diagnostics=tuple(spec_diagnostics))
        matrix = self._build_matrix(networks, domains)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            connection = self._conn()
        except Exception:
            return DriverResult(diagnostics=(_diagnostic(_CODE_UNAVAILABLE, "runtime.libvirt.connection"),))
        return self._realize_matrix(
            connection,
            matrix,
            networks=networks,
            domains=domains,
            envelope_digest=envelope.digest,
            configuration_digest=envelope.configuration.configuration_digest,
        )

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
        return self._verify_and_finalize(
            connection,
            matrix,
            specs=(networks, domains),
            handles=(network_handles, domain_handles),
            observations=observations,
            envelope_digest=envelope_digest,
            configuration_digest=configuration_digest,
        )

    def _verify_and_finalize(
        self,
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
            guest_observations, diagnostics = self._guest_stage(connection, matrix, specs, observations)
        if diagnostics:
            diagnostics.extend(self._rollback(connection, network_handles, domain_handles))
            return DriverResult(diagnostics=tuple(diagnostics))
        try:
            binding = self._material_binding(envelope_digest, configuration_digest)
            snapshot = snapshot_from_observations(matrix, observations, binding=binding)
        except Exception:
            binding_diagnostics = [_diagnostic(_CODE_OPERATION_FAILED, "runtime.libvirt.binding")]
            binding_diagnostics.extend(self._rollback(connection, network_handles, domain_handles))
            return DriverResult(diagnostics=tuple(binding_diagnostics))
        self.last_snapshot = snapshot
        return DriverResult(
            networks=tuple(network_handles),
            domains=tuple(domain_handles),
            observations=(*observations, *guest_observations),
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

    def observe(self, *, domains: tuple[DomainSpec, ...]) -> DriverResult:
        """Read current owned domains without defining or restarting them."""

        try:
            connection = self._conn()
        except Exception:
            return DriverResult(diagnostics=(_diagnostic(_CODE_UNAVAILABLE, "runtime.libvirt.connection"),))
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
        except Exception:
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
        except Exception:
            return False
