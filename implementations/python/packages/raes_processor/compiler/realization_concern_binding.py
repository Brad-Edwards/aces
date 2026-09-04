"""Bind registered realization concerns to compiled resource addresses."""

from __future__ import annotations

from raes.nodes import NodeType
from raes.scenario import InstantiatedScenario

from .addresses import _content_address, _network_address, _node_address


def realization_requirement_address(
    scenario: InstantiatedScenario,
    *,
    section_name: str,
    declaration_name: str,
) -> str:
    """Resolve the compiled resource address for a realization-concern path."""

    if section_name == "nodes" and declaration_name in scenario.nodes:
        node = scenario.nodes[declaration_name]
        return _network_address(declaration_name) if node.type == NodeType.SWITCH else _node_address(declaration_name)
    if section_name == "content" and declaration_name in scenario.content:
        return _content_address(declaration_name)
    raise ValueError("realization concern must resolve to one compiled resource address")


__all__ = ["realization_requirement_address"]
