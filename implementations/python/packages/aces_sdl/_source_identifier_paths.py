"""Source-pointer classification for SDL declaration identities."""

from ._mapping_scopes import HASHMAP_SECTIONS
from ._runtime_service_families import RUNTIME_SERVICE_FAMILIES, RuntimeReferenceChild, RuntimeServiceFamily


def is_declaration_key_path(tokens: list[str]) -> bool:
    return (
        _is_flat_declaration_scope(tokens)
        or _is_nested_entity_scope(tokens)
        or _is_historical_declaration_scope(tokens)
        or _is_activity_declaration_scope(tokens)
    )


def _is_flat_declaration_scope(tokens: list[str]) -> bool:
    if len(tokens) == 1:
        return tokens[0] in HASHMAP_SECTIONS
    if len(tokens) == 3:
        return (tokens[0], tokens[2]) in {
            ("nodes", "roles"),
            ("workflows", "steps"),
            ("variation_points", "alternatives"),
            ("variation_points", "members"),
        }
    return False


def _is_nested_entity_scope(tokens: list[str]) -> bool:
    return (
        bool(tokens)
        and tokens[0] == "entities"
        and tokens[-1] == "entities"
        and all(segment == "entities" for segment in tokens[::2])
    )


def _is_historical_declaration_scope(tokens: list[str]) -> bool:
    return (
        len(tokens) == 3
        and tokens[0] == "historical_baselines"
        and tokens[2]
        in {
            "actors",
            "objects",
            "events",
            "materialization_bindings",
            "readback_requirements",
        }
    )


def _is_activity_declaration_scope(tokens: list[str]) -> bool:
    if len(tokens) != 3:
        return False
    if tokens[0] == "activity_templates":
        return tokens[2] == "parameters"
    return tokens[0] == "activity_profiles" and tokens[2] in {
        "actors",
        "execution_contexts",
        "schedules",
        "actions",
    }


def is_scalar_identifier_path(tokens: list[str]) -> bool:
    if len(tokens) == 3 and tokens[0] == "forwarding_agents" and tokens[1].isdigit():
        return tokens[2] == "forwarding_agent_id"
    if len(tokens) == 5 and tokens[3].isdigit():
        return (tokens[0], tokens[2], tokens[4]) in {
            ("nodes", "services", "name"),
            ("infrastructure", "acls", "name"),
            ("content", "items", "name"),
        }
    return _is_registered_runtime_identifier_path(tokens)


def _is_registered_runtime_identifier_path(tokens: list[str]) -> bool:
    matched = False
    for family in RUNTIME_SERVICE_FAMILIES:
        suffix = _runtime_identifier_suffix(tokens, family)
        if suffix is not None and (not suffix or _matches_runtime_child_path(suffix, family.child_refs)):
            matched = True
            break
    return matched


def _runtime_identifier_suffix(tokens: list[str], family: RuntimeServiceFamily) -> list[str] | None:
    if len(tokens) >= 6:
        node_root = (tokens[0], tokens[2], tokens[3], tokens[5])
        expected = ("nodes", "runtime", family.collection_name, family.id_field)
        if node_root == expected and tokens[4].isdigit():
            return tokens[6:]
    if family.collection_name == "forwarding_agents" and len(tokens) >= 3:
        forwarding_root = (tokens[0], tokens[2])
        if forwarding_root == ("forwarding_agents", family.id_field) and tokens[1].isdigit():
            return tokens[3:]
    return None


def _matches_runtime_child_path(tokens: list[str], child_specs: tuple[RuntimeReferenceChild, ...]) -> bool:
    if len(tokens) < 3 or not tokens[1].isdigit():
        return False
    for child in child_specs:
        if tokens[0] != child.collection_name or tokens[2] != child.id_field:
            continue
        return len(tokens) == 3 or _matches_runtime_child_path(tokens[3:], child.children)
    return False
