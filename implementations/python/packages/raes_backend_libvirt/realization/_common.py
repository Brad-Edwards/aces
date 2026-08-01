"""Shared payload projection helpers for libvirt plan realization."""

from __future__ import annotations

from collections.abc import Mapping

from raes_backend_protocols.naming import provider_resource_name
from raes_contracts.planning import PlannedResource


def _resource_name(resource: PlannedResource, payload: Mapping[str, object]) -> str:
    name = payload.get("name") or payload.get("node_name")
    if isinstance(name, str) and name:
        return name
    return provider_resource_name(resource.address, prefix="raes")
