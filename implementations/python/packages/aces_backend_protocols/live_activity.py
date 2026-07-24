"""Backend capability declaration for deterministic live activity."""

from __future__ import annotations

from dataclasses import dataclass

LIVE_ACTIVITY_CONTRACT_PROFILES = frozenset({"aces-live-activity/v1"})
LIVE_ACTIVITY_SCHEDULE_PROFILES = frozenset({"finite-logical-schedule/v1"})
LIVE_ACTIVITY_READBACK_PROFILES = frozenset({"evidence-readback/v1"})
LIVE_ACTIVITY_LIFECYCLE_PROFILES = frozenset({"range-lifecycle/v1"})
LIVE_ACTIVITY_RESOURCE_DIMENSIONS = frozenset({"operations", "bytes", "connections", "cpu_milliseconds"})
LIVE_ACTIVITY_DEPENDENCY_KINDS = frozenset({"ordering", "refresh"})
LIVE_ACTIVITY_PROTOCOLS = frozenset({"http_api", "smtp", "imap", "ldap", "database", "file_service"})
LIVE_ACTIVITY_OPERATIONS = frozenset(
    {"create", "read", "update", "delete", "send", "receive", "query", "list", "authenticate"}
)


def _unknown(label: str, values: frozenset[str], allowed: frozenset[str]) -> None:
    unknown = values - allowed
    if unknown:
        raise ValueError(f"{label} contains unknown values: {', '.join(sorted(unknown))}")


@dataclass(frozen=True)
class LiveActivityCapabilities:
    """Exact provider-neutral live-activity execution support."""

    supported_contract_profiles: frozenset[str] = frozenset()
    supported_operation_profiles: frozenset[str] = frozenset()
    supported_schedule_profiles: frozenset[str] = frozenset()
    supported_readback_profiles: frozenset[str] = frozenset()
    supported_lifecycle_profiles: frozenset[str] = frozenset()
    supported_resource_dimensions: frozenset[str] = frozenset()
    supported_dependency_kinds: frozenset[str] = frozenset()
    supports_bounded_retry: bool = False
    supports_generation_lifecycle: bool = False
    supports_participant_reservation: bool = False
    supports_readback_provenance: bool = False

    def __post_init__(self) -> None:
        _unknown(
            "LiveActivityCapabilities.supported_contract_profiles",
            self.supported_contract_profiles,
            LIVE_ACTIVITY_CONTRACT_PROFILES,
        )
        _unknown(
            "LiveActivityCapabilities.supported_schedule_profiles",
            self.supported_schedule_profiles,
            LIVE_ACTIVITY_SCHEDULE_PROFILES,
        )
        _unknown(
            "LiveActivityCapabilities.supported_readback_profiles",
            self.supported_readback_profiles,
            LIVE_ACTIVITY_READBACK_PROFILES,
        )
        _unknown(
            "LiveActivityCapabilities.supported_lifecycle_profiles",
            self.supported_lifecycle_profiles,
            LIVE_ACTIVITY_LIFECYCLE_PROFILES,
        )
        _unknown(
            "LiveActivityCapabilities.supported_resource_dimensions",
            self.supported_resource_dimensions,
            LIVE_ACTIVITY_RESOURCE_DIMENSIONS,
        )
        _unknown(
            "LiveActivityCapabilities.supported_dependency_kinds",
            self.supported_dependency_kinds,
            LIVE_ACTIVITY_DEPENDENCY_KINDS,
        )
        for value in self.supported_operation_profiles:
            parts = value.split(":")
            if len(parts) != 3 or parts[0] != "protocol-operation/v1":
                raise ValueError(
                    "live activity operation profiles must use protocol-operation/v1:<protocol>:<operation>"
                )
            if parts[1] not in LIVE_ACTIVITY_PROTOCOLS or parts[2] not in LIVE_ACTIVITY_OPERATIONS:
                raise ValueError(f"live activity operation profile is not governed: {value!r}")


__all__ = [
    "LIVE_ACTIVITY_CONTRACT_PROFILES",
    "LIVE_ACTIVITY_DEPENDENCY_KINDS",
    "LIVE_ACTIVITY_LIFECYCLE_PROFILES",
    "LIVE_ACTIVITY_OPERATIONS",
    "LIVE_ACTIVITY_PROTOCOLS",
    "LIVE_ACTIVITY_READBACK_PROFILES",
    "LIVE_ACTIVITY_RESOURCE_DIMENSIONS",
    "LIVE_ACTIVITY_SCHEDULE_PROFILES",
    "LiveActivityCapabilities",
]
