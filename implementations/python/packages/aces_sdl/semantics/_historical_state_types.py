"""Shared types and helpers for authored historical-state analysis."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from ..historical_state import HistoricalMaterializationInterface, HistoricalObjectKind
from ..uri_safety import unsafe_absolute_uri_reason

SEMANTIC_VERSION_RE = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
    r"(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$"
)
QUALIFIED_IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}(?:\.(?:__private|[a-z0-9][a-z0-9_-]{0,63}))*$")
URI_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s<>'\"]+")
UNSAFE_TEXT_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(
        r"\b(?:password|passwd|api[_-]?key|access[_-]?token|bearer|client[_-]?secret)"
        r"\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(r"(?:^|\n)\s*#!\s*/", re.IGNORECASE),
    re.compile(r"<script(?:\s|>)", re.IGNORECASE),
)

INTERFACE_OBJECT_KIND = {
    HistoricalMaterializationInterface.NATIVE_MESSAGE_V1.value: HistoricalObjectKind.MESSAGE.value,
    HistoricalMaterializationInterface.NATIVE_CASE_V1.value: HistoricalObjectKind.CASE.value,
    HistoricalMaterializationInterface.NATIVE_ALERT_V1.value: HistoricalObjectKind.ALERT.value,
    HistoricalMaterializationInterface.NATIVE_TICKET_V1.value: HistoricalObjectKind.TICKET.value,
    HistoricalMaterializationInterface.NATIVE_DASHBOARD_V1.value: HistoricalObjectKind.DASHBOARD.value,
    HistoricalMaterializationInterface.NATIVE_FILE_V1.value: HistoricalObjectKind.FILE.value,
    HistoricalMaterializationInterface.NATIVE_RECORD_V1.value: HistoricalObjectKind.RECORD.value,
}


@dataclass(frozen=True)
class HistoricalStateIssue:
    """Stable machine-readable issue emitted by historical-state admission."""

    code: str
    message: str


def issue(code: str, message: str) -> HistoricalStateIssue:
    return HistoricalStateIssue(code=code, message=message)


def enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def historical_object_ref(baseline_name: str, object_id: str) -> str:
    return f"historical_baselines.{baseline_name}.objects.{object_id}"


def resolve_local_ref(
    ref: object,
    *,
    baseline_name: str,
    collection_name: str,
    declarations: Mapping[str, object],
) -> str | None:
    if not isinstance(ref, str):
        return None
    if ref in declarations:
        return ref
    local_prefix = f"{collection_name}."
    local = ref.removeprefix(local_prefix) if ref.startswith(local_prefix) else ""
    if local in declarations:
        return local
    canonical_prefix = f"historical_baselines.{baseline_name}.{collection_name}."
    canonical = ref.removeprefix(canonical_prefix) if ref.startswith(canonical_prefix) else ""
    return canonical if canonical in declarations else None


def has_cycle(graph: Mapping[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(dependency in graph and visit(dependency) for dependency in graph[node]):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def service_owner(service_ref: object, nodes: Mapping[str, object]) -> str | None:
    if not isinstance(service_ref, str):
        return None
    for node_name, node in nodes.items():
        for service in getattr(node, "services", ()):
            service_name = getattr(service, "name", "")
            if service_name and service_ref == f"nodes.{node_name}.services.{service_name}":
                return node_name
    return None


def unsafe_text_reason(value: str) -> str | None:
    if any(pattern.search(value) for pattern in UNSAFE_TEXT_PATTERNS):
        return "contains forbidden executable or secret-bearing material"
    for candidate in URI_RE.findall(value):
        if unsafe_absolute_uri_reason(candidate.rstrip(".,);]")) is not None:
            return "contains a credential-bearing URI"
    return None
