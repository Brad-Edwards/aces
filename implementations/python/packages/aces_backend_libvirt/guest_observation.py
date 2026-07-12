"""Concern-specific guest observation for guest-certified libvirt runs.

Boot readiness and initialization completion are staged gates that must pass
before any concern fact is trusted; a later stage never repairs an earlier one.
Each accepted fact is read *from inside the realized guest* (its own ``/proc``,
``/sys``, ``/etc`` and link/file/account/service state), not echoed from the
plan, and is carried as a :class:`RealizationObservation` with
``ObservationStrength.GUEST_OBSERVED``. Failures are stable, redacted
:class:`Diagnostic` codes that name the safe ACES address and the observation
level. A fresh per-run challenge proves the report belongs to this boot, not a
cached or prior one.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.realization_envelope import ObservationStrength, RealizationConcern

from .driver import RealizationObservation
from .guest_transport import (
    FAILURE_TIMEOUT,
    FAILURE_UNAVAILABLE,
    GuestFactTransport,
    parse_guest_facts,
)
from .techvault_matrix import as_sequence

_DOMAIN = "runtime"
_CODE_TRANSPORT_UNAVAILABLE = "libvirt-backend.guest.transport-unavailable"
_CODE_BOOT_TIMEOUT = "libvirt-backend.guest.boot-timeout"
_CODE_INIT_INCOMPLETE = "libvirt-backend.guest.init-incomplete"
_CODE_CHALLENGE_MISMATCH = "libvirt-backend.guest.challenge-mismatch"
_CODE_OBSERVATION_MALFORMED = "libvirt-backend.guest.observation-malformed"
_CODE_OBSERVATION_DUPLICATE = "libvirt-backend.guest.observation-duplicate"
_CODE_OBSERVATION_MISSING = "libvirt-backend.guest.observation-missing"
_CODE_OBSERVATION_MISMATCH = "libvirt-backend.guest.observation-mismatch"

_FAILURE_CODES = {FAILURE_UNAVAILABLE: _CODE_TRANSPORT_UNAVAILABLE, FAILURE_TIMEOUT: _CODE_BOOT_TIMEOUT}

_MESSAGES = {
    _CODE_TRANSPORT_UNAVAILABLE: "Guest fact transport was unavailable at the disclosed channel.",
    _CODE_BOOT_TIMEOUT: "Guest did not report boot readiness within the observation deadline.",
    _CODE_INIT_INCOMPLETE: "Guest initialization did not report completion.",
    _CODE_CHALLENGE_MISMATCH: "Guest report did not carry the fresh per-run challenge.",
    _CODE_OBSERVATION_MALFORMED: "Guest report was malformed or missing its bounded fact header.",
    _CODE_OBSERVATION_DUPLICATE: "Guest report carried duplicate observations for a singleton fact.",
    _CODE_OBSERVATION_MISSING: "Guest did not report every concern in the guest-observed inventory.",
    _CODE_OBSERVATION_MISMATCH: "Guest-observed concern values did not match the requested realization.",
}

_Key = tuple[str, str, RealizationConcern]


@dataclass(frozen=True)
class GuestObservationConfig:
    """Per-stage and overall deadlines plus the disclosed probe-policy version."""

    probe_policy: str = "serial-fact-channel/v1"
    transport_deadline_seconds: float = 120.0


@dataclass(frozen=True)
class _GuestOutcome:
    observations: tuple[RealizationObservation, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    facts: Mapping[str, object] = field(default_factory=dict)


def guest_observation(
    address: str, field_path: str, concern: RealizationConcern, value: object
) -> RealizationObservation:
    """Build a bounded guest-observed fact carrier for one concern field."""

    return RealizationObservation(
        address=address,
        field_path=field_path,
        concern=concern,
        source=ObservationStrength.GUEST_OBSERVED,
        value=value,
    )


def observe_guest(
    *,
    matrix: Mapping[str, object],
    transport: GuestFactTransport,
    challenge: str,
    config: GuestObservationConfig,
    fact_channel_path_for: Callable[[str], Path],
) -> _GuestOutcome:
    """Run the staged guest observation for every domain in ``matrix``."""

    observations: list[RealizationObservation] = []
    diagnostics: list[Diagnostic] = []
    facts_by_address: dict[str, object] = {}
    domains = [item for item in as_sequence(matrix.get("domains")) if isinstance(item, Mapping)]
    for domain in domains:
        address = str(domain.get("address", ""))
        parsed, stage_diag = _read_and_validate(domain, transport, challenge, config, fact_channel_path_for)
        if stage_diag is not None:
            diagnostics.append(stage_diag)
            continue
        assert parsed is not None
        observations.extend(_domain_observations(domain, parsed))
        facts_by_address[address] = _bounded_facts(parsed)
    if not diagnostics:
        expected = expected_guest_observations(domains)
        diagnostics.extend(guest_observation_diagnostics(expected=expected, observations=tuple(observations)))
    return _GuestOutcome(tuple(observations), tuple(diagnostics), facts_by_address)


def _read_and_validate(
    domain: Mapping[str, object],
    transport: GuestFactTransport,
    challenge: str,
    config: GuestObservationConfig,
    fact_channel_path_for: Callable[[str], Path],
) -> tuple[Mapping[str, object] | None, Diagnostic | None]:
    address = str(domain.get("address", ""))
    text, failure = transport.read(
        address=address,
        fact_channel_path=fact_channel_path_for(address),
        deadline_seconds=config.transport_deadline_seconds,
    )
    if failure is not None:
        return None, _diagnostic(_FAILURE_CODES.get(failure, _CODE_TRANSPORT_UNAVAILABLE), address)
    parsed = parse_guest_facts(text or "")
    if parsed is None:
        return None, _diagnostic(_CODE_OBSERVATION_MALFORMED, address)
    if parsed.get("duplicate"):
        return None, _diagnostic(_CODE_OBSERVATION_DUPLICATE, address)
    if not parsed.get("init_complete"):
        return None, _diagnostic(_CODE_INIT_INCOMPLETE, address)
    if parsed.get("challenge") != challenge:
        return None, _diagnostic(_CODE_CHALLENGE_MISMATCH, address)
    return parsed, None


def _domain_observations(
    domain: Mapping[str, object], parsed: Mapping[str, object]
) -> tuple[RealizationObservation, ...]:
    address = str(domain.get("address", ""))
    requested_memory = _as_int(domain.get("memory_mib"))
    guest_memory = _as_int(parsed.get("memory_mib"))
    corroborated = requested_memory > 0 and requested_memory // 2 <= guest_memory <= requested_memory
    return (
        guest_observation(
            address, "guest-architecture", RealizationConcern.ARCHITECTURE, str(parsed.get("architecture") or "")
        ),
        guest_observation(address, "guest-vcpus", RealizationConcern.RESOURCE_ALLOCATION, _as_int(parsed.get("vcpus"))),
        guest_observation(address, "guest-memory-corroborated", RealizationConcern.RESOURCE_ALLOCATION, corroborated),
        guest_observation(address, "guest-network", RealizationConcern.NETWORK, _observed_network(parsed)),
        guest_observation(address, "guest-content", RealizationConcern.CONTENT_PLACEMENT, _observed_content(parsed)),
        guest_observation(address, "guest-account", RealizationConcern.ACCOUNT_PLACEMENT, _observed_accounts(parsed)),
        guest_observation(address, "guest-service", RealizationConcern.SERVICE, _observed_services(parsed)),
    )


def expected_guest_observations(domains: Sequence[Mapping[str, object]]) -> dict[_Key, object]:
    """Project the guest-observed inventory the plan requires per domain."""

    expected: dict[_Key, object] = {}
    for domain in domains:
        address = str(domain.get("address", ""))
        expected[(address, "guest-architecture", RealizationConcern.ARCHITECTURE)] = "x86_64"
        expected[(address, "guest-vcpus", RealizationConcern.RESOURCE_ALLOCATION)] = _as_int(domain.get("vcpus"))
        expected[(address, "guest-memory-corroborated", RealizationConcern.RESOURCE_ALLOCATION)] = True
        expected[(address, "guest-network", RealizationConcern.NETWORK)] = _expected_network(domain)
        expected[(address, "guest-content", RealizationConcern.CONTENT_PLACEMENT)] = _expected_content(domain)
        expected[(address, "guest-account", RealizationConcern.ACCOUNT_PLACEMENT)] = _expected_accounts(domain)
        expected[(address, "guest-service", RealizationConcern.SERVICE)] = _expected_services(domain)
    return expected


def guest_observation_diagnostics(
    *,
    expected: Mapping[_Key, object],
    observations: tuple[RealizationObservation, ...],
) -> list[Diagnostic]:
    """Require exactly one matching guest-observed fact per expected concern field."""

    observed: dict[_Key, list[RealizationObservation]] = {}
    for item in observations:
        observed.setdefault((item.address, item.field_path, item.concern), []).append(item)
    missing: set[str] = set()
    mismatched: set[str] = set()
    for key, expected_value in expected.items():
        candidates = observed.get(key, [])
        if not candidates or any(item.source is not ObservationStrength.GUEST_OBSERVED for item in candidates):
            missing.add(key[0])
        elif (
            len(candidates) != 1
            or type(candidates[0].value) is not type(expected_value)
            or candidates[0].value != expected_value
        ):
            mismatched.add(key[0])
    diagnostics = [_diagnostic(_CODE_OBSERVATION_MISSING, address) for address in sorted(missing)]
    diagnostics.extend(_diagnostic(_CODE_OBSERVATION_MISMATCH, address) for address in sorted(mismatched - missing))
    return diagnostics


def correlation_digest(native_identity: str) -> str:
    """Return a redacted sha256 correlation for an ownership-verified native id."""

    return "sha256:" + hashlib.sha256(native_identity.encode("utf-8")).hexdigest()


# --- observed projections (actual guest readings) ------------------------------


def _observed_network(parsed: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(
        sorted(
            f"{item.get('mac')}|{item.get('ipv4')}"
            for item in as_sequence(parsed.get("interfaces"))
            if isinstance(item, Mapping) and item.get("up")
        )
    )


def _observed_content(parsed: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(
        sorted(
            f"{item.get('path')}|{item.get('sha256')}|{_norm_mode(str(item.get('mode', '')))}"
            for item in as_sequence(parsed.get("content"))
            if isinstance(item, Mapping)
        )
    )


def _observed_accounts(parsed: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(
        sorted(_account_token(item) for item in as_sequence(parsed.get("accounts")) if isinstance(item, Mapping))
    )


def _observed_services(parsed: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(
        sorted(
            f"{item.get('name')}|{item.get('port')}|{_flag(item.get('listening'))}|{_flag(item.get('pid_present'))}"
            for item in as_sequence(parsed.get("services"))
            if isinstance(item, Mapping)
        )
    )


# --- expected projections (plan-derived) ---------------------------------------


def _expected_network(domain: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(
        sorted(
            f"{item.get('mac')}|{item.get('ip')}"
            for item in as_sequence(domain.get("interfaces"))
            if isinstance(item, Mapping)
        )
    )


def _expected_content(domain: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(
        sorted(
            f"{item.get('path')}|{_content_digest(str(item.get('content', '')))}|{_norm_mode(str(item.get('mode', '')))}"
            for item in as_sequence(domain.get("content"))
            if isinstance(item, Mapping)
        )
    )


def _expected_accounts(domain: Mapping[str, object]) -> tuple[str, ...]:
    tokens = []
    for item in as_sequence(domain.get("accounts")):
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name", ""))
        home = str(item.get("home") or f"/home/{name}")
        shell = str(item.get("shell") or "/bin/sh")
        groups = ",".join(sorted(str(group) for group in as_sequence(item.get("groups"))))
        tokens.append(f"{name}|{home}|{shell}|{_flag(item.get('disabled'))}|{groups}")
    return tuple(sorted(tokens))


def _expected_services(domain: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(
        sorted(
            f"{item.get('name')}|{item.get('port')}|1|1"
            for item in as_sequence(domain.get("services"))
            if isinstance(item, Mapping)
        )
    )


def _account_token(item: Mapping[str, object]) -> str:
    name = str(item.get("name", ""))
    home = str(item.get("home", ""))
    shell = str(item.get("shell", ""))
    groups = ",".join(sorted(str(group) for group in as_sequence(item.get("groups"))))
    return f"{name}|{home}|{shell}|{_flag(item.get('disabled'))}|{groups}"


def _bounded_facts(parsed: Mapping[str, object]) -> dict[str, object]:
    return {
        "architecture": str(parsed.get("architecture") or ""),
        "vcpus": _as_int(parsed.get("vcpus")),
        "memory_mib": _as_int(parsed.get("memory_mib")),
        "interfaces": _observed_network(parsed),
        "content": _observed_content(parsed),
        "accounts": _observed_accounts(parsed),
        "services": _observed_services(parsed),
    }


def _content_digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _norm_mode(mode: str) -> str:
    return mode.lstrip("0") or "0"


def _flag(value: object) -> str:
    return "1" if value else "0"


def _as_int(value: object) -> int:
    return value if isinstance(value, int) else -1


def _diagnostic(code: str, address: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        domain=_DOMAIN,
        address=address,
        message=_MESSAGES.get(code, "Guest observation did not succeed."),
        severity=Severity.ERROR,
    )


__all__ = [
    "GuestObservationConfig",
    "correlation_digest",
    "expected_guest_observations",
    "guest_observation",
    "guest_observation_diagnostics",
    "observe_guest",
]
