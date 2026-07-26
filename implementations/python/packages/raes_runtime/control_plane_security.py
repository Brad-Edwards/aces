"""Security policy for the per-target runtime control plane."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ControlPlaneRole(str, Enum):
    """Authorization roles for control-plane callers."""

    BACKEND = "backend"
    OPERATOR = "operator"
    AUDITOR = "auditor"


@dataclass(frozen=True)
class ParticipantControlSubjectBinding:
    """One authenticated principal-to-participant/controller binding."""

    participant_address: str
    controller_ref: str

    def __post_init__(self) -> None:
        if not self.participant_address or not self.controller_ref:
            raise ValueError("participant control subject binding fields must be non-empty")


@dataclass(frozen=True)
class ControlPlaneIdentity:
    """Authenticated control-plane principal."""

    identity: str
    roles: frozenset[ControlPlaneRole] = field(default_factory=frozenset)
    target_name: str | None = None
    participant_control_subjects: tuple[ParticipantControlSubjectBinding, ...] = ()


@dataclass(frozen=True)
class ControlPlaneSecurityConfig:
    """Reference security settings for the HTTP/JSON control-plane adapter.

    Header identities are only trustworthy behind an authenticated proxy that
    strips caller-supplied identity headers before setting its own values.
    """

    require_verified_identity: bool = True
    verified_header: str = "x-aces-client-verified"
    identity_header: str = "x-aces-client-identity"
    trust_proxy_identity_headers: bool = False
    max_request_bytes: int = 1_000_000
    trusted_identities: dict[str, ControlPlaneIdentity] = field(default_factory=dict)
    bearer_tokens: dict[str, ControlPlaneIdentity] = field(default_factory=dict)

    @classmethod
    def strict_defaults(cls) -> ControlPlaneSecurityConfig:
        """Return fail-closed defaults with no built-in principals or tokens."""

        return cls(
            require_verified_identity=True,
            trust_proxy_identity_headers=False,
            trusted_identities={},
            bearer_tokens={},
        )
