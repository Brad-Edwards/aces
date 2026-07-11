"""Source-pointer classification for SDL declaration identities."""

from typing import Any

from ._mapping_scopes import HASHMAP_SECTIONS
from ._runtime_service_families import RUNTIME_SERVICE_FAMILIES


def is_declaration_key_path(tokens: list[str]) -> bool:
    if len(tokens) == 1 and tokens[0] in HASHMAP_SECTIONS:
        return True
    if len(tokens) == 3 and tokens[0] == "nodes" and tokens[2] == "roles":
        return True
    if len(tokens) == 3 and tokens[0] == "workflows" and tokens[2] == "steps":
        return True
    if not tokens or tokens[0] != "entities" or tokens[-1] != "entities":
        return False
    return all(segment == "entities" for segment in tokens[::2])


def is_scalar_identifier_path(tokens: list[str]) -> bool:
    if len(tokens) == 3 and tokens[0] == "forwarding_agents" and tokens[1].isdigit():
        return tokens[2] == "forwarding_agent_id"
    if len(tokens) == 5 and tokens[:1] == ["nodes"] and tokens[2] == "services" and tokens[3].isdigit():
        return tokens[4] == "name"
    if len(tokens) == 5 and tokens[:1] == ["infrastructure"] and tokens[2] == "acls" and tokens[3].isdigit():
        return tokens[4] == "name"
    if len(tokens) == 5 and tokens[:1] == ["content"] and tokens[2] == "items" and tokens[3].isdigit():
        return tokens[4] == "name"
    return _is_registered_runtime_identifier_path(tokens)


def _is_registered_runtime_identifier_path(tokens: list[str]) -> bool:
    for family in RUNTIME_SERVICE_FAMILIES:
        if (
            len(tokens) >= 6
            and tokens[0] == "nodes"
            and tokens[2] == "runtime"
            and tokens[3] == family.collection_name
            and tokens[4].isdigit()
            and tokens[5] == family.id_field
        ):
            return len(tokens) == 6 or _matches_runtime_child_path(tokens[6:], family.child_refs)
        if (
            family.collection_name == "forwarding_agents"
            and len(tokens) >= 3
            and tokens[0] == "forwarding_agents"
            and tokens[1].isdigit()
            and tokens[2] == family.id_field
        ):
            return len(tokens) == 3 or _matches_runtime_child_path(tokens[3:], family.child_refs)
    return False


def _matches_runtime_child_path(tokens: list[str], child_specs: tuple[Any, ...]) -> bool:
    if len(tokens) < 3 or not tokens[1].isdigit():
        return False
    for child in child_specs:
        if tokens[0] != child.collection_name or tokens[2] != child.id_field:
            continue
        return len(tokens) == 3 or _matches_runtime_child_path(tokens[3:], child.children)
    return False
