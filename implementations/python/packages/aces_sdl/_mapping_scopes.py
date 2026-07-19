"""Classify SDL mappings whose keys are authored identifiers rather than fields."""

from __future__ import annotations

from enum import Enum


class MappingScope(str, Enum):
    """Key interpretation for one mapping node."""

    STRUCTURAL = "structural"
    LITERAL = "literal"


HASHMAP_SECTIONS = frozenset(
    {
        "nodes",
        "infrastructure",
        "features",
        "conditions",
        "propositions",
        "assertions",
        "vulnerabilities",
        "entities",
        "injects",
        "events",
        "scripts",
        "stories",
        "content",
        "generated_artifacts",
        "persistent_volumes",
        "accounts",
        "identity_domains",
        "relationships",
        "agents",
        "action_contracts",
        "observation_boundaries",
        "outcome_interpretation_rules",
        "behavior_specifications",
        "evidence_requirements",
        "objectives",
        "workflows",
        "variables",
    }
)

NESTED_HASHMAP_FIELDS = frozenset(
    {
        "features",
        "conditions",
        "injects",
        "roles",
        "log_options",
        "labels",
        "driver_options",
        "ipam_options",
        "facts",
        "entities",
        "events",
        "steps",
        "extensions",
        "interactive_access",
        "tool_affordances",
    }
)


def normalize_field_key(key: str) -> str:
    """Return the canonical spelling of an SDL structural field key."""
    return key.lower().replace("-", "_")


def is_literal_map_field(
    key: str,
    *,
    value_is_mapping: bool,
    value_is_sequence: bool,
) -> bool:
    """Return whether a structural field's immediate child keys are literal."""
    if key in HASHMAP_SECTIONS:
        return value_is_mapping
    if key in NESTED_HASHMAP_FIELDS:
        return True
    return key == "properties" and value_is_sequence
