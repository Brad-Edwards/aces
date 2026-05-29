"""Runtime subobject alias helpers for SDL module composition."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .scenario import Scenario


def _prefixed_runtimes(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> Iterable[tuple[str, str, object]]:
    for node_name, node in scenario.nodes.items():
        prefixed_node = node_rename_map.get(node_name, node_name)
        if prefixed_node == node_name:
            continue
        runtime = getattr(node, "runtime", None)
        if runtime is not None:
            yield node_name, prefixed_node, runtime


def _collection_aliases(
    *,
    bare_base: str,
    prefixed_base: str,
    collection: Iterable[object],
    collection_name: str,
    id_field: str,
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for item in collection:
        item_id = getattr(item, id_field, "")
        if item_id:
            aliases[f"{bare_base}.{collection_name}.{item_id}"] = f"{prefixed_base}.{collection_name}.{item_id}"
    return aliases


def _security_monitoring_manager_aliases(
    *,
    node_name: str,
    prefixed_node: str,
    manager: object,
) -> dict[str, str]:
    manager_id = getattr(manager, "manager_id", "")
    if not manager_id:
        return {}
    bare_base = f"nodes.{node_name}.runtime.security_monitoring_managers.{manager_id}"
    prefixed_base = f"nodes.{prefixed_node}.runtime.security_monitoring_managers.{manager_id}"
    aliases: dict[str, str] = {bare_base: prefixed_base}
    for collection_name, id_field in (
        ("listeners", "listener_id"),
        ("components", "component_id"),
        ("agents", "agent_id"),
        ("agent_groups", "group_id"),
        ("content_sets", "content_id"),
        ("settings", "setting_id"),
    ):
        aliases.update(
            _collection_aliases(
                bare_base=bare_base,
                prefixed_base=prefixed_base,
                collection=getattr(manager, collection_name, []),
                collection_name=collection_name,
                id_field=id_field,
            )
        )
    return aliases


def nested_node_security_monitoring_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node_name, prefixed_node, runtime in _prefixed_runtimes(scenario, node_rename_map):
        for manager in getattr(runtime, "security_monitoring_managers", []):
            aliases.update(
                _security_monitoring_manager_aliases(
                    node_name=node_name,
                    prefixed_node=prefixed_node,
                    manager=manager,
                )
            )
    return aliases


def _network_detection_engine_aliases(
    *,
    node_name: str,
    prefixed_node: str,
    engine: object,
) -> dict[str, str]:
    engine_id = getattr(engine, "engine_id", "")
    if not engine_id:
        return {}
    bare_base = f"nodes.{node_name}.runtime.network_detection_engines.{engine_id}"
    prefixed_base = f"nodes.{prefixed_node}.runtime.network_detection_engines.{engine_id}"
    aliases: dict[str, str] = {bare_base: prefixed_base}
    for collection_name, id_field in (
        ("rule_sources", "source_id"),
        ("network_sets", "set_id"),
        ("output_streams", "stream_id"),
        ("control_channels", "channel_id"),
    ):
        aliases.update(
            _collection_aliases(
                bare_base=bare_base,
                prefixed_base=prefixed_base,
                collection=getattr(engine, collection_name, []),
                collection_name=collection_name,
                id_field=id_field,
            )
        )
    return aliases


def nested_node_network_detection_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node_name, prefixed_node, runtime in _prefixed_runtimes(scenario, node_rename_map):
        for engine in getattr(runtime, "network_detection_engines", []):
            aliases.update(
                _network_detection_engine_aliases(
                    node_name=node_name,
                    prefixed_node=prefixed_node,
                    engine=engine,
                )
            )
    return aliases


def nested_node_network_sensor_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node_name, prefixed_node, runtime in _prefixed_runtimes(scenario, node_rename_map):
        for sensor in getattr(runtime, "network_sensors", []):
            sensor_id = getattr(sensor, "sensor_id", "")
            if sensor_id:
                aliases[f"nodes.{node_name}.runtime.network_sensors.{sensor_id}"] = (
                    f"nodes.{prefixed_node}.runtime.network_sensors.{sensor_id}"
                )
    return aliases


def nested_node_service_listener_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node_name, prefixed_node, runtime in _prefixed_runtimes(scenario, node_rename_map):
        for listener in getattr(runtime, "service_listeners", []):
            listener_id = getattr(listener, "listener_id", "")
            if listener_id:
                aliases[f"nodes.{node_name}.runtime.service_listeners.{listener_id}"] = (
                    f"nodes.{prefixed_node}.runtime.service_listeners.{listener_id}"
                )
    return aliases
