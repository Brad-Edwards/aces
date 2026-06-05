"""Runtime subobject alias helpers for SDL module composition."""

from __future__ import annotations

from collections.abc import Mapping

from ._runtime_service_families import nested_node_runtime_family_aliases
from .scenario import Scenario


def nested_node_runtime_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    """Qualified runtime-family refs rewritten for imported node namespaces."""

    return nested_node_runtime_family_aliases(scenario, node_rename_map)


def nested_node_security_monitoring_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    return nested_node_runtime_family_aliases(
        scenario,
        node_rename_map,
        family_keys=("security-monitoring-managers",),
    )


def nested_node_network_detection_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    return nested_node_runtime_family_aliases(
        scenario,
        node_rename_map,
        family_keys=("network-detection-engines",),
    )


def nested_node_network_sensor_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    return nested_node_runtime_family_aliases(
        scenario,
        node_rename_map,
        family_keys=("network-sensors",),
    )


def nested_node_service_listener_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    return nested_node_runtime_family_aliases(
        scenario,
        node_rename_map,
        family_keys=("service-listeners",),
    )


__all__ = [
    "nested_node_network_detection_aliases",
    "nested_node_network_sensor_aliases",
    "nested_node_runtime_aliases",
    "nested_node_security_monitoring_aliases",
    "nested_node_service_listener_aliases",
]
