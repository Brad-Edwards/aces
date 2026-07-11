"""Wire contract for processor-owned runtime addresses."""

from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import AfterValidator, WithJsonSchema

COMPILED_ADDRESS_MAX_LENGTH = 2048
_ADDRESS_SEGMENT = r"(?:[a-z0-9][a-z0-9_-]{0,63}|__private)"
COMPILED_ADDRESS_PATTERN = rf"{_ADDRESS_SEGMENT}(?:\.{_ADDRESS_SEGMENT})+"
_COMPILED_ADDRESS_RE = re.compile(COMPILED_ADDRESS_PATTERN, re.ASCII)
COMPILED_ADDRESS_JSON_SCHEMA: dict[str, Any] = {
    "type": "string",
    "minLength": 3,
    "maxLength": COMPILED_ADDRESS_MAX_LENGTH,
    "pattern": rf"^{COMPILED_ADDRESS_PATTERN}$",
    "not": {"pattern": "[^a-z0-9_.-]"},
}
PLAN_ADDRESS_ROOT_BY_DOMAIN = {
    "provisioning": "provision",
    "orchestration": "orchestration",
    "evaluation": "evaluation",
}
PLAN_RESOURCE_TYPES_BY_DOMAIN = {
    "provisioning": frozenset({"network", "node", "feature-binding", "content-placement", "account-placement"}),
    "orchestration": frozenset({"inject-binding", "inject", "event", "script", "story", "workflow"}),
    "evaluation": frozenset({"condition-binding", "objective"}),
}


def require_compiled_address(value: object, *, field_name: str = "address") -> str:
    if (
        not isinstance(value, str)
        or len(value) > COMPILED_ADDRESS_MAX_LENGTH
        or _COMPILED_ADDRESS_RE.fullmatch(value) is None
    ):
        raise ValueError(f"{field_name} must be a canonical compiled address")
    return value


def require_plan_operation_identity(domain: object, address: object, resource_type: object) -> None:
    """Reject operations outside a plan endpoint's closed identity domain."""

    canonical = require_compiled_address(address)
    domain_value = getattr(domain, "value", domain)
    root = PLAN_ADDRESS_ROOT_BY_DOMAIN.get(domain_value)
    resource_types = PLAN_RESOURCE_TYPES_BY_DOMAIN.get(domain_value)
    if root is None or not canonical.startswith(f"{root}."):
        raise ValueError("Plan operation address must belong to its runtime domain")
    if not isinstance(resource_type, str) or resource_types is None or resource_type not in resource_types:
        raise ValueError("Plan operation resource_type must belong to its runtime domain")


def _validate_compiled_address(value: str) -> str:
    return require_compiled_address(value)


CompiledAddress = Annotated[
    str,
    AfterValidator(_validate_compiled_address),
    WithJsonSchema(COMPILED_ADDRESS_JSON_SCHEMA),
]


def render_compiled_address(*parts: str) -> str:
    address = ".".join(part for part in parts if part)
    return require_compiled_address(address)


__all__ = [
    "COMPILED_ADDRESS_JSON_SCHEMA",
    "COMPILED_ADDRESS_MAX_LENGTH",
    "CompiledAddress",
    "PLAN_ADDRESS_ROOT_BY_DOMAIN",
    "PLAN_RESOURCE_TYPES_BY_DOMAIN",
    "render_compiled_address",
    "require_compiled_address",
    "require_plan_operation_identity",
]
