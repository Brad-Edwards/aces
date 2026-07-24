"""Backend capability declaration for authored historical-state materialization."""

from __future__ import annotations

from dataclasses import dataclass

HISTORICAL_MATERIALIZATION_INTERFACE_PROFILES = frozenset(
    {
        "native-message/v1",
        "native-case/v1",
        "native-alert/v1",
        "native-ticket/v1",
        "native-dashboard/v1",
        "native-file/v1",
        "native-record/v1",
    }
)
HISTORICAL_MATERIALIZATION_OBJECT_KINDS = frozenset(
    {"message", "case", "alert", "ticket", "dashboard", "file", "record"}
)
HISTORICAL_MATERIALIZATION_KIND_BY_INTERFACE = {
    "native-message/v1": "message",
    "native-case/v1": "case",
    "native-alert/v1": "alert",
    "native-ticket/v1": "ticket",
    "native-dashboard/v1": "dashboard",
    "native-file/v1": "file",
    "native-record/v1": "record",
}


@dataclass(frozen=True)
class HistoricalStateCapabilities:
    """Exact provider-neutral authored historical-state support."""

    supported_interface_profiles: frozenset[str] = frozenset()
    supported_object_kinds: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.supported_interface_profiles:
            raise ValueError("HistoricalStateCapabilities.supported_interface_profiles must not be empty")
        if not self.supported_object_kinds:
            raise ValueError("HistoricalStateCapabilities.supported_object_kinds must not be empty")
        unknown_profiles = self.supported_interface_profiles - HISTORICAL_MATERIALIZATION_INTERFACE_PROFILES
        if unknown_profiles:
            raise ValueError(
                "HistoricalStateCapabilities.supported_interface_profiles contains unknown profiles: "
                + ", ".join(sorted(unknown_profiles))
            )
        unknown_kinds = self.supported_object_kinds - HISTORICAL_MATERIALIZATION_OBJECT_KINDS
        if unknown_kinds:
            raise ValueError(
                "HistoricalStateCapabilities.supported_object_kinds contains unknown kinds: "
                + ", ".join(sorted(unknown_kinds))
            )
        expected_kinds = {
            HISTORICAL_MATERIALIZATION_KIND_BY_INTERFACE[profile] for profile in self.supported_interface_profiles
        }
        if self.supported_object_kinds != expected_kinds:
            raise ValueError(
                "HistoricalStateCapabilities interface profiles and object kinds must declare "
                "the same exact support pairs"
            )


__all__ = [
    "HISTORICAL_MATERIALIZATION_INTERFACE_PROFILES",
    "HISTORICAL_MATERIALIZATION_KIND_BY_INTERFACE",
    "HISTORICAL_MATERIALIZATION_OBJECT_KINDS",
    "HistoricalStateCapabilities",
]
