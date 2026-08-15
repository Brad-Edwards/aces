"""Native libvirt driver that certifies realization from inside the guest.

Extends :class:`TechVaultNativeLibvirtDriver` with the guest-observation stage:
after ownership-safe define/create and daemon readback, it boots a
guest-observing appliance, reads concern-specific facts back through the
credential-free fact channel, and refuses to finalize unless the fresh,
challenge-bound guest observations match the requested realization. The
challenge rides the kernel command line (not the appliance image), so the
appliance content digest stays stable across runs while every report is bound to
this boot.
"""

from __future__ import annotations

import re
import secrets
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from raes_contracts.diagnostics import Diagnostic

from raes_backend_libvirt._observability import LOGGER as _LOGGER
from raes_backend_libvirt._observability import NATIVE_FAILURE_LOG as _NATIVE_FAILURE_LOG

from ._techvault_native_ops import _CODE_GUEST_FRESHNESS_UNAVAILABLE, _diagnostic
from .driver import DomainSpec, NetworkSpec, RealizationObservation
from .drivers.libvirt import _raes_uuid
from .guest_appliance import GuestObservingInitramfsBuilder
from .guest_observation import GuestObservationConfig, correlation_digest, observe_guest
from .guest_transport import FileSerialGuestFactTransport, GuestFactTransport
from .techvault_appliance import InitramfsBuilder
from .techvault_concerns import guest_certified_spec_diagnostics
from .techvault_matrix import domain_xml as _domain_xml
from .techvault_matrix import native_matrix as _native_matrix
from .techvault_native import DriverResult, TechVaultNativeLibvirtDriver, _artifact_token

_SAFE_CHALLENGE_RE = re.compile(r"^[a-f0-9]{16,64}$")
_GUEST_FACTS_ADDRESS = "runtime.libvirt.guest-facts"


def _fresh_challenge() -> str:
    return secrets.token_hex(16)


@dataclass
class GuestCertifiedLibvirtDriver(TechVaultNativeLibvirtDriver):
    """Realize TechVault domains and certify concerns from inside the guest."""

    driver_mode: ClassVar[str] = "guest-certified-appliance"

    initramfs_builder: InitramfsBuilder = field(default_factory=GuestObservingInitramfsBuilder)
    guest_transport: GuestFactTransport = field(default_factory=FileSerialGuestFactTransport)
    guest_config: GuestObservationConfig = field(default_factory=GuestObservationConfig)
    challenge_factory: Callable[[], str] = field(default=_fresh_challenge, repr=False)
    challenge: str | None = field(default=None, init=False)
    last_guest_observations: tuple[RealizationObservation, ...] = ()
    last_guest_facts: dict[str, object] = field(default_factory=dict)
    last_guest_binding: dict[str, object] = field(default_factory=dict)
    _used_challenges: set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        if not callable(self.challenge_factory):
            raise ValueError("guest-certified challenge_factory must be callable")

    def _admission_diagnostics(
        self,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
        envelope: object,
    ) -> list[Diagnostic]:
        from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel

        assert isinstance(envelope, BackendRealizationEnvelopeModel)
        return guest_certified_spec_diagnostics(
            networks=networks,
            domains=domains,
            envelope=envelope,
            name_prefix=self.name_prefix,
        )

    def _build_matrix(
        self,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
    ) -> dict[str, object]:
        return _native_matrix(
            networks=networks,
            domains=domains,
            name_prefix=self.name_prefix,
            include_placements=True,
        )

    def _prepare_operation(self, matrix: Mapping[str, object]) -> list[Diagnostic]:
        """Rotate freshness state and remove every prior fact before libvirt I/O."""

        self._begin_operation()
        diagnostics: list[Diagnostic] = []
        try:
            candidate = self.challenge_factory()
        except Exception as exc:
            _LOGGER.debug(_NATIVE_FAILURE_LOG, "_prepare_operation", exc_info=exc)
            candidate = None
        if (
            not isinstance(candidate, str)
            or not _SAFE_CHALLENGE_RE.match(candidate)
            or candidate in self._used_challenges
        ):
            diagnostics.append(_diagnostic(_CODE_GUEST_FRESHNESS_UNAVAILABLE, _GUEST_FACTS_ADDRESS))
        else:
            diagnostics.extend(self._clear_prior_fact_channels(matrix))
        if not diagnostics:
            assert isinstance(candidate, str)
            self.challenge = candidate
            self._used_challenges.add(candidate)
        return diagnostics

    def _clear_prior_fact_channels(self, matrix: Mapping[str, object]) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for domain in matrix.get("domains", ()):
            if not isinstance(domain, Mapping):
                continue
            channel = self._fact_channel_path(str(domain.get("address", "")))
            try:
                channel.parent.mkdir(parents=True, exist_ok=True)
                if channel.is_symlink() or (channel.exists() and not channel.is_dir()):
                    channel.unlink()
                elif channel.exists():
                    diagnostics.append(_diagnostic(_CODE_GUEST_FRESHNESS_UNAVAILABLE, _GUEST_FACTS_ADDRESS))
                    break
            except OSError:
                diagnostics.append(_diagnostic(_CODE_GUEST_FRESHNESS_UNAVAILABLE, _GUEST_FACTS_ADDRESS))
                break
        return diagnostics

    def _begin_operation(self) -> None:
        """Prevent prior guest evidence from surviving into a new attempt."""

        self.challenge = None
        self.last_guest_observations = ()
        self.last_guest_facts = {}
        self.last_guest_binding = {}

    def _render_domain_xml(self, domain: Mapping[str, object], *, kernel: Path, initrd: Path) -> str:
        address = str(domain.get("address", ""))
        fact_channel = self._fact_channel_path(address)
        fact_channel.parent.mkdir(parents=True, exist_ok=True)
        return _domain_xml(
            domain,
            kernel=kernel,
            initrd=initrd,
            appliance="guest-certified",
            challenge=self.challenge,
            fact_channel_path=fact_channel,
        )

    def _guest_stage(
        self,
        connection: object,
        matrix: Mapping[str, object],
        specs: tuple[tuple[NetworkSpec, ...], tuple[DomainSpec, ...]],
        observations: tuple[RealizationObservation, ...],
    ) -> tuple[tuple[RealizationObservation, ...], list[Diagnostic]]:
        del connection, specs, observations
        assert self.challenge is not None
        outcome = observe_guest(
            matrix=matrix,
            transport=self.guest_transport,
            challenge=self.challenge,
            config=self.guest_config,
            fact_channel_path_for=self._fact_channel_path,
        )
        if outcome.diagnostics:
            return (), list(outcome.diagnostics)
        self.last_guest_observations = outcome.observations
        self.last_guest_facts = dict(outcome.facts)
        self.last_guest_binding = self._guest_binding(matrix)
        return outcome.observations, []

    def destroy(self, *, networks: tuple[str, ...], domains: tuple[str, ...]) -> DriverResult:
        result = super().destroy(networks=networks, domains=domains)
        if (networks or domains) and not result.diagnostics:
            self.last_guest_observations = ()
            self.last_guest_facts = {}
            self.last_guest_binding = {}
        return result

    def _cleanup_artifacts(self, address: str) -> None:
        super()._cleanup_artifacts(address)
        with suppress(OSError):
            self._fact_channel_path(address).unlink()

    def _fact_channel_path(self, address: str) -> Path:
        return self.state_dir / "guest-facts" / f"{_artifact_token(address)}.facts"

    def _guest_binding(self, matrix: Mapping[str, object]) -> dict[str, object]:
        domains = [item for item in matrix.get("domains", ()) if isinstance(item, Mapping)]
        correlations = {
            str(domain.get("address", "")): correlation_digest(_raes_uuid(str(domain.get("address", ""))))
            for domain in domains
        }
        return {
            "challenge": self.challenge,
            "probe_policy": self.guest_config.probe_policy,
            "memory_tolerance_mib": self.guest_config.memory_tolerance_mib,
            "correlations": correlations,
        }


__all__ = ["GuestCertifiedLibvirtDriver"]
