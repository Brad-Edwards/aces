"""Canonical policy for SDL declarations accepted by targetable references."""

from __future__ import annotations

NON_TARGETABLE_REFERENCE_SECTIONS = frozenset(
    {
        "variables",
        "evidence_requirements",
        "time_domains",
        "clocks",
        "time_domain_mappings",
        "time_progression_policies",
        "temporal_constraints",
        "objectives",
        "workflows",
    }
)


def is_targetable_section(section: str) -> bool:
    """Return whether top-level declarations in a section are targetable."""

    return section not in NON_TARGETABLE_REFERENCE_SECTIONS
