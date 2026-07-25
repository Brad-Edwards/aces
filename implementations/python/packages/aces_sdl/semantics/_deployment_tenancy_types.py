"""Shared internal types for deployment-tenancy semantic analysis."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class DeploymentTenancyIssue:
    code: str
    message: str


@dataclass
class CellIndex:
    node_cell: dict[str, str]
    cell_tenant: dict[str, str]
    tenant_nodes: defaultdict[str, set[str]]
    issues: list[DeploymentTenancyIssue]


def issue(code: str, message: str) -> DeploymentTenancyIssue:
    return DeploymentTenancyIssue(code=code, message=message)


def enum_value(value: object) -> str:
    return getattr(value, "value", str(value))


def service_owner(service_ref: object, nodes: Mapping[str, object]) -> str | None:
    if not isinstance(service_ref, str):
        return None
    for node_name, node in nodes.items():
        for service in getattr(node, "services", ()):
            name = getattr(service, "name", "")
            if name and service_ref == f"nodes.{node_name}.services.{name}":
                return node_name
    return None


__all__ = ["CellIndex", "DeploymentTenancyIssue", "enum_value", "issue", "service_owner"]
