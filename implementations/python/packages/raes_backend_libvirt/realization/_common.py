"""Shared payload projection helpers for libvirt plan realization."""

from __future__ import annotations

from collections.abc import Mapping

from raes_backend_protocols.naming import provider_resource_name
from raes_contracts.planning import PlannedResource, PlanOperation, planned_resource_authored_name


def _resource_name(
    resource: PlannedResource | PlanOperation,
    payload: Mapping[str, object] | None = None,
) -> str:
    if isinstance(resource, PlannedResource):
        name = planned_resource_authored_name(resource)
    else:
        operation_payload = payload or {}
        raw_name = operation_payload.get("name") or operation_payload.get("node_name")
        name = raw_name if isinstance(raw_name, str) and raw_name else None
    if name is not None:
        return name
    return provider_resource_name(resource.address, prefix="raes")
