"""Registered realization concern kinds and runtime payload locations."""

from collections.abc import Iterable, Mapping

_CONCERN_KIND_BY_PATH: dict[tuple[str, str], str] = {
    ("nodes", "type"): "node-type",
    ("nodes", "os"): "os-family",
    ("content", "type"): "content-type",
}

CONCERN_PAYLOAD_PATH: dict[str, tuple[str, ...]] = {
    "os-family": ("os_family",),
    "node-type": ("node_type",),
    "content-type": ("spec", "type"),
    "domain-topology": ("domain_topology",),
    "generated-artifact": ("spec",),
    "persistent-volume": ("spec",),
    "service-content-materialization": ("service_materialization",),
}


def registered_realization_concerns(
    *,
    declaration_names: Mapping[str, Iterable[str]],
) -> tuple[tuple[str, str, str, str], ...]:
    """Enumerate ``(section, declaration, leaf, kind)`` registrations."""

    return tuple(
        (section, declaration_name, leaf_field, concern_kind)
        for (section, leaf_field), concern_kind in _CONCERN_KIND_BY_PATH.items()
        for declaration_name in declaration_names.get(section, ())
    )


def resolve_realization_concern(
    field_path: str,
    *,
    declaration_names: Mapping[str, Iterable[str]],
) -> str | None:
    """Return the registered realization concern kind for a classifier path."""

    for section, declaration_name, leaf_field, concern_kind in registered_realization_concerns(
        declaration_names=declaration_names
    ):
        if field_path == f"{section}.{declaration_name}.{leaf_field}":
            return concern_kind
    return None


__all__ = [
    "CONCERN_PAYLOAD_PATH",
    "registered_realization_concerns",
    "resolve_realization_concern",
]
