"""Shared accessors over RAES provisioning-plan resource payloads.

The low-level, package-internal layer both :mod:`realization` (interpretation)
and :mod:`capability_envelope` (capability-envelope diagnostics) build on, so the
two never duplicate — or diverge on — how a plan payload's node type, OS family,
content type, or spec is read.
"""

from __future__ import annotations

from collections.abc import Mapping

NODE_RESOURCE_TYPE = "node"
NETWORK_RESOURCE_TYPE = "network"
ACCOUNT_PLACEMENT_RESOURCE_TYPE = "account-placement"
CONTENT_PLACEMENT_RESOURCE_TYPE = "content-placement"
DOMAIN_CONTROLLER_PLACEMENT_RESOURCE_TYPE = "domain-controller-placement"
FEATURE_BINDING_RESOURCE_TYPE = "feature-binding"
PLACEMENT_RESOURCE_TYPES = frozenset(
    {
        ACCOUNT_PLACEMENT_RESOURCE_TYPE,
        CONTENT_PLACEMENT_RESOURCE_TYPE,
        DOMAIN_CONTROLLER_PLACEMENT_RESOURCE_TYPE,
        FEATURE_BINDING_RESOURCE_TYPE,
    }
)
SUPPORTED_RESOURCE_TYPES = frozenset({NODE_RESOURCE_TYPE, NETWORK_RESOURCE_TYPE}) | PLACEMENT_RESOURCE_TYPES


def _spec(payload: Mapping[str, object]) -> Mapping[str, object]:
    spec = payload.get("spec")
    return spec if isinstance(spec, Mapping) else {}


def _str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _os_family(payload: Mapping[str, object]) -> str:
    family = payload.get("os_family")
    if isinstance(family, str) and family:
        return family
    node = _spec(payload).get("node")
    node_os = node.get("os") if isinstance(node, Mapping) else None
    return node_os if isinstance(node_os, str) else ""


def _architecture(payload: Mapping[str, object]) -> str:
    architecture = payload.get("architecture")
    if isinstance(architecture, str) and architecture:
        return architecture
    node = _spec(payload).get("node")
    node_architecture = node.get("architecture") if isinstance(node, Mapping) else None
    return node_architecture if isinstance(node_architecture, str) else ""


def _node_type(payload: Mapping[str, object]) -> str:
    node_type = payload.get("node_type")
    if isinstance(node_type, str) and node_type:
        return node_type
    node = _spec(payload).get("node")
    nested = node.get("type") if isinstance(node, Mapping) else None
    return nested if isinstance(nested, str) else ""
