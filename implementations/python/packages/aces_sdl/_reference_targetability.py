"""Canonical policy for SDL declarations accepted by targetable references."""

from __future__ import annotations

NON_TARGETABLE_REFERENCE_SECTIONS = frozenset({"variables", "evidence_requirements", "objectives", "workflows"})


def is_targetable_reference(candidate: str) -> bool:
    """Return whether a qualified declaration can be a generic target."""
    section, separator, _ = candidate.partition(".")
    return bool(separator) and section not in NON_TARGETABLE_REFERENCE_SECTIONS


def is_targetable_section(section: str) -> bool:
    """Return whether declarations in a top-level section are targetable."""
    return section not in NON_TARGETABLE_REFERENCE_SECTIONS
