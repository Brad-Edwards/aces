"""Module/import expansion for multi-file SDL scenarios."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ._base import VARIABLE_TOKEN_RE, is_variable_ref
from ._composition_budget import CompositionBudget, CompositionTraversal
from ._composition_provenance import (
    prefixed_constraint as _prefixed_constraint,
)
from ._composition_provenance import (
    prefixed_explicitness as _prefixed_explicitness,
)
from ._composition_provenance import (
    prefixed_import_record as _prefixed_import_record,
)
from ._composition_provenance import (
    prefixed_realization_designation as _prefixed_realization_designation,
)
from ._composition_provenance import (
    resolved_import_record as _resolved_import_record,
)
from ._errors import SDLInstantiationError, SDLParseDiagnostic, SDLParseError, SDLValidationError
from ._identifiers import QualifiedName
from ._module_symbols import FORWARDING_AGENTS_SECTION
from ._module_symbols import HASHMAP_SECTIONS as _HASHMAP_SECTIONS
from ._module_symbols import (
    rewrite_objective_window_ref as _rewrite_objective_window_ref,
)
from ._module_symbols import (
    symbol_index as _symbol_index,
)
from ._source_profile import (
    DEFAULT_PARSER_LIMITS,
    SDL_SOURCE_FORMAT,
    SDLMigrationPolicy,
    SDLParserLimits,
    SDLSourceParseOptions,
)
from .entities import flatten_entities
from .instantiate import _bind_scenario_content
from .module_registry import (
    load_lockfile,
    load_trust_policy,
    resolve_import,
)
from .parser import _load_normalized_data
from .participant_behavior_specification import tool_affordance_reference
from .phase_contracts import (
    CapabilityConstraint,
    ExpansionProvenance,
    ExplicitnessProvenanceRecord,
    ResolvedImportProvenance,
)
from .realization_designation import RealizationDesignation, RealizationDesignationRecord, designation_records
from .scenario import ExpandedScenario, ImportDecl, ModuleDescriptor, ScenarioContent
from .variation import COLLECTION_TARGET_SPECS, REFERENCE_TARGET_SPECS, TIMING_TARGET_SPECS

_REFERENCE_TARGET_SPECS_BY_VALUE = {slot.value: spec for slot, spec in REFERENCE_TARGET_SPECS.items()}
_COLLECTION_TARGET_SPECS_BY_VALUE = {slot.value: spec for slot, spec in COLLECTION_TARGET_SPECS.items()}
_TIMING_TARGET_SPECS_BY_VALUE = {slot.value: spec for slot, spec in TIMING_TARGET_SPECS.items()}


def _prefix(namespace: str, name: str) -> str:
    return QualifiedName.parse(name).prefixed(namespace).render() if namespace else QualifiedName.parse(name).render()


def _private_prefix(namespace: str, name: str) -> str:
    return QualifiedName.parse(name).prefixed(namespace, private=True).render()


def _maybe_rename(name: str, name_map: Mapping[str, str]) -> str:
    if not name or is_variable_ref(name):
        return name
    return name_map.get(name, name)


def _rewrite_section_ref(name: str, section: str, name_map: Mapping[str, str]) -> str:
    """Rewrite a bare or explicitly section-qualified reference."""

    if not name or is_variable_ref(name):
        return name
    prefix = f"{section}."
    if name.startswith(prefix):
        local_name = name.removeprefix(prefix)
        return f"{prefix}{name_map.get(local_name, local_name)}"
    return name_map.get(name, name)


def _rewrite_stateful_dependency_ref(
    reference: str,
    symbols: dict[str, dict[str, str] | set[str]],
    *,
    owner: str,
) -> str:
    """Rewrite through the resource section that owns the dependency."""

    matching_sections: list[str] = []
    for section in ("generated_artifacts", "persistent_volumes"):
        section_map = symbols[section]
        if not isinstance(section_map, Mapping):
            continue
        if reference.startswith(f"{section}."):
            return _rewrite_section_ref(reference, section, section_map)
        if reference in section_map:
            matching_sections.append(section)

    if len(matching_sections) > 1:
        choices = ", ".join(f"{section}.{reference}" for section in matching_sections)
        raise SDLValidationError([f"{owner} dependency reference {reference!r} is ambiguous; use one of: {choices}"])
    if matching_sections:
        section = matching_sections[0]
        section_map = symbols[section]
        assert isinstance(section_map, Mapping)
        return _rewrite_section_ref(reference, section, section_map)
    return reference


def _validate_descriptor_exports(
    scenario: ScenarioContent,
    descriptor: ModuleDescriptor,
) -> None:
    for section_name, exported_names in descriptor.exports.items():
        if section_name not in {*_HASHMAP_SECTIONS, FORWARDING_AGENTS_SECTION}:
            raise SDLParseError(f"Module '{descriptor.id}' exports unknown SDL section '{section_name}'")
        for exported_name in exported_names:
            QualifiedName.parse(exported_name)
        if section_name == FORWARDING_AGENTS_SECTION:
            available_names = {agent.forwarding_agent_id for agent in scenario.forwarding_agents}
        elif section_name == "entities":
            available_names = set(flatten_entities(scenario.entities))
        else:
            section_payload = getattr(scenario, section_name, None)
            available_names = set(section_payload.keys()) if isinstance(section_payload, Mapping) else set()
        undefined = sorted(set(exported_names) - available_names)
        if undefined:
            raise SDLParseError(f"Module '{descriptor.id}' exports undefined {section_name}: " + ", ".join(undefined))


def _rewrite_node(payload: dict[str, Any], symbols: dict[str, dict[str, str] | set[str]]) -> None:
    payload["features"] = {
        _maybe_rename(name, symbols["features"]): role for name, role in payload.get("features", {}).items()
    }
    payload["conditions"] = {
        _maybe_rename(name, symbols["conditions"]): role for name, role in payload.get("conditions", {}).items()
    }
    payload["injects"] = {
        _maybe_rename(name, symbols["injects"]): role for name, role in payload.get("injects", {}).items()
    }
    payload["vulnerabilities"] = [
        _maybe_rename(name, symbols["vulnerabilities"]) for name in payload.get("vulnerabilities", [])
    ]
    for role in payload.get("roles", {}).values():
        if isinstance(role, dict):
            role["entities"] = [_maybe_rename(name, symbols["entities"]) for name in role.get("entities", [])]
    runtime = payload.get("runtime")
    container = runtime.get("container") if isinstance(runtime, dict) else None
    namespaces = container.get("namespaces") if isinstance(container, dict) else None
    network = namespaces.get("network") if isinstance(namespaces, dict) else None
    if isinstance(network, dict) and network.get("target_node_ref"):
        network["target_node_ref"] = _rewrite_section_ref(
            str(network["target_node_ref"]),
            "nodes",
            symbols["nodes"],
        )


def _rewrite_infrastructure(payload: dict[str, Any], symbols: dict[str, dict[str, str] | set[str]]) -> None:
    payload["dependencies"] = [_maybe_rename(name, symbols["named"]) for name in payload.get("dependencies", [])]
    payload["links"] = [_maybe_rename(name, symbols["named"]) for name in payload.get("links", [])]
    properties = payload.get("properties")
    if isinstance(properties, list):
        rewritten: list[dict[str, Any]] = []
        for item in properties:
            if isinstance(item, dict):
                rewritten.append({_maybe_rename(name, symbols["named"]): value for name, value in item.items()})
            else:
                rewritten.append(item)
        payload["properties"] = rewritten


def _rewrite_feature(payload: dict[str, Any], symbols: dict[str, dict[str, str] | set[str]]) -> None:
    payload["dependencies"] = [_maybe_rename(name, symbols["features"]) for name in payload.get("dependencies", [])]
    payload["vulnerabilities"] = [
        _maybe_rename(name, symbols["vulnerabilities"]) for name in payload.get("vulnerabilities", [])
    ]


def _rewrite_entity(payload: dict[str, Any], symbols: dict[str, dict[str, str] | set[str]]) -> None:
    payload["vulnerabilities"] = [
        _maybe_rename(name, symbols["vulnerabilities"]) for name in payload.get("vulnerabilities", [])
    ]
    payload["events"] = [_maybe_rename(name, symbols["events"]) for name in payload.get("events", [])]
    for child in payload.get("entities", {}).values():
        if isinstance(child, dict):
            _rewrite_entity(child, symbols)


def _rewrite_workflow(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
    tool_affordance_ref_map: dict[str, str],
) -> None:
    for step in payload.get("steps", {}).values():
        if not isinstance(step, dict):
            continue
        if step.get("objective"):
            step["objective"] = _maybe_rename(str(step["objective"]), symbols["objectives"])
        if step.get("procedure_ref"):
            step["procedure_ref"] = _maybe_rename(str(step["procedure_ref"]), symbols["action_contracts"])
        step["scaffold_refs"] = [
            _maybe_rename(name, symbols["observation_boundaries"]) for name in step.get("scaffold_refs", [])
        ]
        step["allowed_action_families"] = [
            _maybe_rename(name, symbols["action_contracts"]) for name in step.get("allowed_action_families", [])
        ]
        step["tool_affordance_refs"] = [
            tool_affordance_ref_map.get(name, name) for name in step.get("tool_affordance_refs", [])
        ]
        if step.get("workflow"):
            step["workflow"] = _maybe_rename(str(step["workflow"]), symbols["workflows"])
        if step.get("compensate_with"):
            step["compensate_with"] = _maybe_rename(str(step["compensate_with"]), symbols["workflows"])
        when = step.get("when")
        if isinstance(when, dict):
            when["assertions"] = [_maybe_rename(name, symbols["assertions"]) for name in when.get("assertions", [])]
            when["objectives"] = [_maybe_rename(name, symbols["objectives"]) for name in when.get("objectives", [])]


def _rewrite_evidence_requirement(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for field_name in ("source_refs", "scope_refs", "channel_refs"):
        payload[field_name] = [_maybe_rename(name, symbols["named"]) for name in payload.get(field_name, [])]
    for field_name in ("trigger_ref", "boundary_ref"):
        if payload.get(field_name):
            payload[field_name] = _maybe_rename(str(payload[field_name]), symbols["named"])


def _rewrite_mixed_control_state(
    state: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    controller_ref = state.get("controller_ref")
    if controller_ref and controller_ref != "self":
        state["controller_ref"] = _maybe_rename(str(controller_ref), symbols["agents"])
    for field_name in ("authority_basis_refs", "scope_refs", "evidence_refs"):
        state[field_name] = [_maybe_rename(name, symbols["named"]) for name in state.get(field_name, [])]


def _rewrite_mixed_control_transition(
    transition: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for field_name in ("evidence_refs", "completion_evidence_refs"):
        transition[field_name] = [_maybe_rename(name, symbols["named"]) for name in transition.get(field_name, [])]


def _rewrite_mixed_control(
    mixed_control: object,
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    if not isinstance(mixed_control, dict):
        return
    if mixed_control.get("participant_ref"):
        mixed_control["participant_ref"] = _maybe_rename(
            str(mixed_control["participant_ref"]),
            symbols["agents"],
        )
    for state in mixed_control.get("controller_states", {}).values():
        if isinstance(state, dict):
            _rewrite_mixed_control_state(state, symbols)
    for transition in mixed_control.get("transitions", {}).values():
        if isinstance(transition, dict):
            _rewrite_mixed_control_transition(transition, symbols)


def _rewrite_tool_affordance(
    binding: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    if binding.get("tool_ref"):
        binding["tool_ref"] = _maybe_rename(str(binding["tool_ref"]), symbols["content"])
    binding["action_contract_refs"] = [
        _maybe_rename(name, symbols["action_contracts"]) for name in binding.get("action_contract_refs", [])
    ]
    binding["observation_boundary_refs"] = [
        _maybe_rename(name, symbols["observation_boundaries"]) for name in binding.get("observation_boundary_refs", [])
    ]


def _rewrite_variation_reference(
    reference: str,
    section: str,
    symbols: dict[str, dict[str, str] | set[str]],
) -> str:
    return _maybe_rename(reference, symbols["named"] if section == "targetable" else symbols[section])


def _variation_slot(target: dict[str, Any]) -> str:
    raw_slot = target.get("slot", "")
    return str(getattr(raw_slot, "value", raw_slot))


def _rewrite_variation_target(
    kind: object,
    target: object,
    symbols: dict[str, dict[str, str] | set[str]],
) -> str | None:
    target_section: str | None = None
    if isinstance(target, dict):
        if kind == "parameter" and isinstance(target.get("variable"), str):
            target["variable"] = _maybe_rename(str(target["variable"]), symbols["variables"])
        slot = _variation_slot(target)
        owner_spec = (
            _REFERENCE_TARGET_SPECS_BY_VALUE.get(slot)
            or _COLLECTION_TARGET_SPECS_BY_VALUE.get(slot)
            or _TIMING_TARGET_SPECS_BY_VALUE.get(slot)
        )
        if owner_spec is not None and isinstance(target.get("owner"), str):
            target["owner"] = _rewrite_variation_reference(str(target["owner"]), owner_spec[0], symbols)
        target_section = _variation_target_section(kind, slot)
    return target_section


def _variation_target_section(kind: object, slot: str) -> str | None:
    spec: tuple[str, str] | None = None
    if kind in {"governed-reference", "alternative"}:
        spec = _REFERENCE_TARGET_SPECS_BY_VALUE.get(slot)
    elif kind in {"subset", "order"}:
        spec = _COLLECTION_TARGET_SPECS_BY_VALUE.get(slot)
    return spec[1] if spec is not None else None


def _rewrite_variation_domain(
    payload: dict[str, Any],
    target_section: str | None,
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    domain = payload.get("domain")
    if payload.get("kind") == "governed-reference" and target_section is not None and isinstance(domain, dict):
        domain["allowed_refs"] = [
            _rewrite_variation_reference(reference, target_section, symbols)
            for reference in domain.get("allowed_refs", [])
        ]


def _rewrite_member_relations(
    member: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for relation_field in ("requires", "excludes"):
        for relation in member.get(relation_field, []):
            if isinstance(relation, dict) and isinstance(relation.get("point"), str):
                relation["point"] = _maybe_rename(str(relation["point"]), symbols["variation_points"])


def _rewrite_variation_members(
    payload: dict[str, Any],
    target_section: str | None,
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    member_field = "alternatives" if payload.get("kind") == "alternative" else "members"
    members = payload.get(member_field)
    if isinstance(members, dict):
        for member in members.values():
            if not isinstance(member, dict):
                continue
            if target_section is not None and isinstance(member.get("reference"), str):
                member["reference"] = _rewrite_variation_reference(
                    str(member["reference"]),
                    target_section,
                    symbols,
                )
            _rewrite_member_relations(member, symbols)


def _rewrite_variation_point(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    kind = payload.get("kind")
    target = payload.get("target")
    target_section = _rewrite_variation_target(kind, target, symbols)
    _rewrite_variation_domain(payload, target_section, symbols)
    _rewrite_variation_members(payload, target_section, symbols)


def _rewrite_variable_tokens(value: object, variables: Mapping[str, str]) -> object:
    """Namespace preserved authoring-variable tokens in imported content."""

    rewritten: object
    if isinstance(value, str):
        rewritten = VARIABLE_TOKEN_RE.sub(
            lambda match: "${" + variables.get(match.group(1), match.group(1)) + "}",
            value,
        )
    elif isinstance(value, dict):
        rewritten = {key: _rewrite_variable_tokens(item, variables) for key, item in value.items()}
    elif isinstance(value, list):
        rewritten = [_rewrite_variable_tokens(item, variables) for item in value]
    elif isinstance(value, tuple):
        rewritten = tuple(_rewrite_variable_tokens(item, variables) for item in value)
    else:
        rewritten = value
    return rewritten


def _namespace_payload(
    payload: dict[str, Any],
    imported: ScenarioContent,
    namespace: str,
    descriptor: ModuleDescriptor,
) -> dict[str, Any]:
    namespaced = dict(payload)
    _validate_descriptor_exports(imported, descriptor)
    symbols = _symbol_index(
        imported,
        namespace=namespace,
        descriptor=descriptor,
        restrict_to_descriptor=True,
    )
    tool_affordance_ref_map: dict[str, str] = {}
    for spec_name, behavior_spec in namespaced.get("behavior_specifications", {}).items():
        if not isinstance(behavior_spec, dict):
            continue
        namespaced_spec_name = symbols["behavior_specifications"].get(
            spec_name,
            _prefix(namespace, spec_name),
        )
        for affordance_id in behavior_spec.get("tool_affordances", {}):
            tool_affordance_ref_map[tool_affordance_reference(spec_name, affordance_id)] = tool_affordance_reference(
                namespaced_spec_name, affordance_id
            )

    for node in namespaced.get("nodes", {}).values():
        if isinstance(node, dict):
            _rewrite_node(node, symbols)
    for infra in namespaced.get("infrastructure", {}).values():
        if isinstance(infra, dict):
            _rewrite_infrastructure(infra, symbols)
    for feature in namespaced.get("features", {}).values():
        if isinstance(feature, dict):
            _rewrite_feature(feature, symbols)
    for condition in namespaced.get("conditions", {}).values():
        if isinstance(condition, dict) and condition.get("proposition"):
            condition["proposition"] = _maybe_rename(str(condition["proposition"]), symbols["propositions"])
    for proposition in namespaced.get("propositions", {}).values():
        if isinstance(proposition, dict):
            proposition["subjects"] = [
                _maybe_rename(name, symbols["named"]) for name in proposition.get("subjects", [])
            ]
            proposition["evidence_requirements"] = [
                _maybe_rename(name, symbols["evidence_requirements"])
                for name in proposition.get("evidence_requirements", [])
            ]
    for assertion in namespaced.get("assertions", {}).values():
        if isinstance(assertion, dict) and assertion.get("proposition"):
            assertion["proposition"] = _maybe_rename(str(assertion["proposition"]), symbols["propositions"])
    for entity in namespaced.get("entities", {}).values():
        if isinstance(entity, dict):
            _rewrite_entity(entity, symbols)
    for inject in namespaced.get("injects", {}).values():
        if isinstance(inject, dict):
            if inject.get("from_entity"):
                inject["from_entity"] = _maybe_rename(str(inject["from_entity"]), symbols["entities"])
            inject["to_entities"] = [_maybe_rename(name, symbols["entities"]) for name in inject.get("to_entities", [])]
    for event in namespaced.get("events", {}).values():
        if isinstance(event, dict):
            event["assertions"] = [_maybe_rename(name, symbols["assertions"]) for name in event.get("assertions", [])]
            event["injects"] = [_maybe_rename(name, symbols["injects"]) for name in event.get("injects", [])]
    for script in namespaced.get("scripts", {}).values():
        if isinstance(script, dict):
            script["events"] = {
                _maybe_rename(name, symbols["events"]): value for name, value in script.get("events", {}).items()
            }
    for story in namespaced.get("stories", {}).values():
        if isinstance(story, dict):
            story["scripts"] = [_maybe_rename(name, symbols["scripts"]) for name in story.get("scripts", [])]
    for boundary in namespaced.get("observation_boundaries", {}).values():
        if not isinstance(boundary, dict):
            continue
        for field_name in ("observable_refs", "hidden_refs", "evidence_refs"):
            boundary[field_name] = [tool_affordance_ref_map.get(ref, ref) for ref in boundary.get(field_name, [])]
        for field_name in ("view_rules", "view_transitions"):
            for item in boundary.get(field_name, []):
                if not isinstance(item, dict):
                    continue
                information_ref = item.get("information_ref")
                if isinstance(information_ref, str):
                    item["information_ref"] = tool_affordance_ref_map.get(
                        information_ref,
                        information_ref,
                    )
    for content in namespaced.get("content", {}).values():
        if isinstance(content, dict) and content.get("target"):
            content["target"] = _maybe_rename(str(content["target"]), symbols["nodes"])
    for section_name in ("generated_artifacts", "persistent_volumes"):
        for resource_name, resource in namespaced.get(section_name, {}).items():
            if not isinstance(resource, dict):
                continue
            for consumer in resource.get("consumers", []):
                if isinstance(consumer, dict) and consumer.get("node"):
                    consumer["node"] = _maybe_rename(str(consumer["node"]), symbols["nodes"])
            for dependency_field in (
                "ordering_dependencies",
                "refresh_dependencies",
            ):
                resource[dependency_field] = [
                    _rewrite_stateful_dependency_ref(
                        reference,
                        symbols,
                        owner=f"{section_name}.{resource_name}",
                    )
                    for reference in resource.get(dependency_field, [])
                ]
    for account in namespaced.get("accounts", {}).values():
        if isinstance(account, dict):
            if account.get("node"):
                account["node"] = _maybe_rename(str(account["node"]), symbols["nodes"])
            if account.get("domain_ref"):
                account["domain_ref"] = _maybe_rename(
                    str(account["domain_ref"]),
                    symbols["identity_domains"],
                )
    for identity_domain in namespaced.get("identity_domains", {}).values():
        if isinstance(identity_domain, dict) and identity_domain.get("authority_account_ref"):
            identity_domain["authority_account_ref"] = _maybe_rename(
                str(identity_domain["authority_account_ref"]),
                symbols["accounts"],
            )
    for identity_forest in namespaced.get("identity_forests", {}).values():
        if not isinstance(identity_forest, dict):
            continue
        if identity_forest.get("root_domain_ref"):
            identity_forest["root_domain_ref"] = _maybe_rename(
                str(identity_forest["root_domain_ref"]),
                symbols["identity_domains"],
            )
        identity_forest["domain_refs"] = [
            _maybe_rename(name, symbols["identity_domains"]) for name in identity_forest.get("domain_refs", [])
        ]
    for identity_facade in namespaced.get("identity_facades", {}).values():
        if isinstance(identity_facade, dict) and identity_facade.get("service_ref"):
            identity_facade["service_ref"] = _maybe_rename(
                str(identity_facade["service_ref"]),
                symbols["named"],
            )
    for deployment_cell in namespaced.get("deployment_cells", {}).values():
        if not isinstance(deployment_cell, dict):
            continue
        if deployment_cell.get("tenant_ref"):
            deployment_cell["tenant_ref"] = _maybe_rename(
                str(deployment_cell["tenant_ref"]),
                symbols["deployment_tenants"],
            )
        deployment_cell["node_refs"] = [
            _maybe_rename(name, symbols["nodes"]) for name in deployment_cell.get("node_refs", [])
        ]
    for relationship in namespaced.get("relationships", {}).values():
        if isinstance(relationship, dict):
            if relationship.get("source"):
                relationship["source"] = _maybe_rename(str(relationship["source"]), symbols["named"])
            if relationship.get("target"):
                relationship["target"] = _maybe_rename(str(relationship["target"]), symbols["named"])
            domain_join = relationship.get("domain_join")
            if isinstance(domain_join, dict):
                domain_join["controller_refs"] = [
                    _maybe_rename(name, symbols["nodes"]) for name in domain_join.get("controller_refs", [])
                ]
            shared_service = relationship.get("shared_service")
            if isinstance(shared_service, dict):
                shared_service["mutable_state_refs"] = [
                    _maybe_rename(name, symbols["persistent_volumes"])
                    for name in shared_service.get("mutable_state_refs", [])
                ]
            forwarding_edge = relationship.get("forwarding_edge")
            if isinstance(forwarding_edge, dict) and forwarding_edge.get("forwarder_ref"):
                forwarding_edge["forwarder_ref"] = _maybe_rename(
                    str(forwarding_edge["forwarder_ref"]),
                    symbols[FORWARDING_AGENTS_SECTION],
                )
    for agent in namespaced.get("agents", {}).values():
        if isinstance(agent, dict):
            if agent.get("entity"):
                agent["entity"] = _maybe_rename(str(agent["entity"]), symbols["entities"])
            agent["starting_accounts"] = [
                _maybe_rename(name, symbols["accounts"]) for name in agent.get("starting_accounts", [])
            ]
            agent["actions"] = [_maybe_rename(name, symbols["action_contracts"]) for name in agent.get("actions", [])]
            agent["observation_boundaries"] = [
                _maybe_rename(name, symbols["observation_boundaries"])
                for name in agent.get("observation_boundaries", [])
            ]
            for access in agent.get("interactive_access", {}).values():
                if not isinstance(access, dict):
                    continue
                if access.get("target_ref"):
                    access["target_ref"] = _rewrite_section_ref(
                        str(access["target_ref"]),
                        "nodes",
                        symbols["nodes"],
                    )
                if access.get("account_ref"):
                    access["account_ref"] = _rewrite_section_ref(
                        str(access["account_ref"]),
                        "accounts",
                        symbols["accounts"],
                    )
            knowledge = agent.get("initial_knowledge")
            if isinstance(knowledge, dict):
                knowledge["hosts"] = [_maybe_rename(name, symbols["nodes"]) for name in knowledge.get("hosts", [])]
                knowledge["subnets"] = [
                    _maybe_rename(name, symbols["infrastructure"]) for name in knowledge.get("subnets", [])
                ]
                knowledge["accounts"] = [
                    _maybe_rename(name, symbols["accounts"]) for name in knowledge.get("accounts", [])
                ]
            agent["allowed_subnets"] = [
                _maybe_rename(name, symbols["infrastructure"]) for name in agent.get("allowed_subnets", [])
            ]
            # ADR-020 §6 accepts bare or section-qualified condition refs.
            # symbols["named"] carries both forms after the symbol-index
            # update, so a single rename handles `health` and
            # `conditions.health` symmetrically.
            agent["starting_assertions"] = [
                _maybe_rename(name, symbols["assertions"]) for name in agent.get("starting_assertions", [])
            ]
            agent["authority_anchors"] = [
                _maybe_rename(name, symbols["named"]) for name in agent.get("authority_anchors", [])
            ]
            agent["operating_scope"] = [
                _maybe_rename(name, symbols["named"]) for name in agent.get("operating_scope", [])
            ]
    for behavior_spec in namespaced.get("behavior_specifications", {}).values():
        if isinstance(behavior_spec, dict):
            behavior_spec["participant_refs"] = [
                _maybe_rename(name, symbols["agents"]) for name in behavior_spec.get("participant_refs", [])
            ]
            behavior_spec["action_contract_refs"] = [
                _maybe_rename(name, symbols["action_contracts"])
                for name in behavior_spec.get("action_contract_refs", [])
            ]
            behavior_spec["observation_boundary_refs"] = [
                _maybe_rename(name, symbols["observation_boundaries"])
                for name in behavior_spec.get("observation_boundary_refs", [])
            ]
            behavior_spec["outcome_interpretation_rule_refs"] = [
                _maybe_rename(name, symbols["outcome_interpretation_rules"])
                for name in behavior_spec.get("outcome_interpretation_rule_refs", [])
            ]
            behavior_spec["authority_scope_refs"] = [
                _maybe_rename(name, symbols["named"]) for name in behavior_spec.get("authority_scope_refs", [])
            ]
            _rewrite_mixed_control(behavior_spec.get("mixed_control"), symbols)
            for binding in behavior_spec.get("tool_affordances", {}).values():
                if isinstance(binding, dict):
                    _rewrite_tool_affordance(binding, symbols)
    for requirement in namespaced.get("evidence_requirements", {}).values():
        if isinstance(requirement, dict):
            _rewrite_evidence_requirement(requirement, symbols)
    for objective in namespaced.get("objectives", {}).values():
        if not isinstance(objective, dict):
            continue
        if objective.get("agent"):
            objective["agent"] = _maybe_rename(str(objective["agent"]), symbols["agents"])
        if objective.get("entity"):
            objective["entity"] = _maybe_rename(str(objective["entity"]), symbols["entities"])
        objective["targets"] = [_maybe_rename(name, symbols["named"]) for name in objective.get("targets", [])]
        objective["depends_on"] = [
            _maybe_rename(name, symbols["objectives"]) for name in objective.get("depends_on", [])
        ]
        success = objective.get("success")
        if isinstance(success, dict):
            success["assertions"] = [
                _maybe_rename(name, symbols["assertions"]) for name in success.get("assertions", [])
            ]
        window = objective.get("window")
        if isinstance(window, dict):
            for field_name, symbol_key in (
                ("stories", "stories"),
                ("scripts", "scripts"),
                ("events", "events"),
                ("workflows", "workflows"),
            ):
                window[field_name] = [_maybe_rename(name, symbols[symbol_key]) for name in window.get(field_name, [])]
            window["steps"] = [
                _rewrite_objective_window_ref(name, symbols["workflows"]) for name in window.get("steps", [])
            ]
    for workflow in namespaced.get("workflows", {}).values():
        if isinstance(workflow, dict):
            _rewrite_workflow(workflow, symbols, tool_affordance_ref_map)
    for variation_point in namespaced.get("variation_points", {}).values():
        if isinstance(variation_point, dict):
            _rewrite_variation_point(variation_point, symbols)

    namespaced = _rewrite_variable_tokens(namespaced, symbols["variables"])

    for section_name in _HASHMAP_SECTIONS:
        section_payload = namespaced.get(section_name)
        if not isinstance(section_payload, dict):
            continue
        namespaced[section_name] = {
            symbols[section_name].get(name, _prefix(namespace, name)): value for name, value in section_payload.items()
        }
    forwarding_agents = namespaced.get(FORWARDING_AGENTS_SECTION, [])
    if isinstance(forwarding_agents, list):
        for agent in forwarding_agents:
            if not isinstance(agent, dict):
                continue
            identifier = agent.get("forwarding_agent_id")
            if isinstance(identifier, str):
                agent["forwarding_agent_id"] = symbols[FORWARDING_AGENTS_SECTION].get(
                    identifier,
                    _private_prefix(namespace, identifier),
                )
    namespaced.pop("module", None)
    namespaced.pop("imports", None)
    namespaced.pop("expansion_provenance", None)
    namespaced.pop("instantiation_provenance", None)
    return namespaced


def _merge_sections(
    root: dict[str, Any],
    incoming: dict[str, Any],
    *,
    path: Path,
) -> dict[str, Any]:
    merged = dict(root)
    for section_name in _HASHMAP_SECTIONS:
        current = dict(merged.get(section_name, {}))
        additions = dict(incoming.get(section_name, {}))
        collisions = sorted(set(current).intersection(additions))
        if collisions:
            raise SDLParseError(f"Import from {path} collides on {section_name}: {', '.join(collisions)}")
        current.update(additions)
        merged[section_name] = current
    current_agents = list(merged.get(FORWARDING_AGENTS_SECTION, []))
    incoming_agents = list(incoming.get(FORWARDING_AGENTS_SECTION, []))
    current_ids = {agent.get("forwarding_agent_id") for agent in current_agents if isinstance(agent, dict)}
    incoming_ids = {agent.get("forwarding_agent_id") for agent in incoming_agents if isinstance(agent, dict)}
    collisions = sorted(identifier for identifier in current_ids.intersection(incoming_ids) if identifier)
    if collisions:
        raise SDLParseError(f"Import from {path} collides on {FORWARDING_AGENTS_SECTION}: {', '.join(collisions)}")
    merged[FORWARDING_AGENTS_SECTION] = [*current_agents, *incoming_agents]
    merged["imports"] = []
    return merged


def _import_decl(value: Any) -> ImportDecl:
    if isinstance(value, ImportDecl):
        return value
    return ImportDecl.model_validate(value)


def expand_sdl_modules(
    data: dict[str, Any],
    *,
    path: Path,
    source_format: str = SDL_SOURCE_FORMAT,
    migration_policy: SDLMigrationPolicy | str = SDLMigrationPolicy.REJECT,
    limits: SDLParserLimits = DEFAULT_PARSER_LIMITS,
    source_diagnostics: list[SDLParseDiagnostic] | None = None,
    _traversal: CompositionTraversal | None = None,
) -> tuple[dict[str, Any], ExpansionProvenance]:
    """Expand trusted imports into executable content and portable evidence."""

    traversal = _traversal or CompositionTraversal(
        seen=frozenset(),
        budget=CompositionBudget(limits),
        depth=0,
    )
    budget = traversal.budget
    budget.check_depth(traversal.depth, path=path)
    budget.add_document(data, path=path)
    resolved_path = path.resolve()
    if resolved_path in traversal.seen:
        raise SDLParseError(f"Import cycle detected at {resolved_path}", path=path)
    child_traversal = traversal.descend_from(resolved_path)

    merged = dict(data)
    merged.setdefault("imports", [])
    merged.setdefault("version", "*")
    import_records: list[ResolvedImportProvenance] = []
    capability_constraints: list[CapabilityConstraint] = []
    explicitness_records: list[ExplicitnessProvenanceRecord] = []
    realization_records: list[RealizationDesignationRecord] = []
    raw_designation = merged.get("realization")
    if raw_designation is not None:
        try:
            realization_records.extend(designation_records(RealizationDesignation.model_validate(raw_designation)))
        except ValidationError as exc:
            raise SDLParseError("Realization designation is structurally invalid", path=path) from exc
    lockfile = load_lockfile(resolved_path.parent)
    trust_policy = load_trust_policy(resolved_path.parent)

    for raw_import in list(merged.get("imports", [])):
        budget.add_import(path=path)
        import_decl = _import_decl(raw_import)
        if "__private." in import_decl.namespace:
            raise SDLParseError(
                "Import namespaces may not contain the reserved '__private' segment",
                path=path,
            )
        resolved_import = resolve_import(
            import_decl,
            base_dir=resolved_path.parent,
            lockfile=lockfile,
            trust_policy=trust_policy,
            source_options=SDLSourceParseOptions(
                source_format=source_format,
                migration_policy=migration_policy,
                limits=limits,
            ),
            source_diagnostics=source_diagnostics,
        )
        import_path = resolved_import.root_file
        imported_raw = _load_normalized_data(
            resolved_import.source_document.text,
            path=import_path,
            source_format=source_format,
            migration_policy=migration_policy,
            limits=limits,
            source_diagnostics=source_diagnostics,
        )
        imported_expanded, inner_provenance = expand_sdl_modules(
            imported_raw,
            path=import_path,
            source_format=source_format,
            migration_policy=migration_policy,
            limits=limits,
            source_diagnostics=source_diagnostics,
            _traversal=child_traversal,
        )
        try:
            imported_scenario = ExpandedScenario.model_validate(imported_expanded)
            bound = _bind_scenario_content(
                imported_scenario,
                import_decl.parameters,
                preserve_variation_variables=True,
            )
        except ValidationError as exc:
            raise SDLParseError("Imported SDL unit is structurally invalid", path=import_path) from exc
        except SDLInstantiationError as exc:
            raise SDLParseError(str(exc), path=import_path) from exc
        namespace = import_decl.namespace
        descriptor = resolved_import.module_descriptor
        symbols = _symbol_index(
            bound.content,
            namespace=namespace,
            descriptor=descriptor,
            restrict_to_descriptor=True,
        )

        namespaced_payload = _namespace_payload(
            bound.content.model_dump(mode="python", by_alias=True),
            bound.content,
            namespace,
            descriptor,
        )
        budget.check_namespaces(namespaced_payload, path=import_path)
        merged = _merge_sections(merged, namespaced_payload, path=import_path)

        import_records.append(_resolved_import_record(resolved_import, requested=import_decl, bindings=bound))
        import_records.extend(_prefixed_import_record(record, namespace) for record in inner_provenance.imports)
        capability_constraints.extend(
            _prefixed_constraint(
                constraint,
                namespace=namespace,
                symbols=symbols,
            )
            for constraint in bound.capability_constraints
        )
        explicitness_records.extend(
            _prefixed_explicitness(
                record,
                namespace=namespace,
                imported=bound.content,
                symbols=symbols,
            )
            for record in bound.explicitness
            if any(record.model_path.startswith(f"{section_name}.") for section_name in _HASHMAP_SECTIONS)
        )
        realization_records.extend(
            _prefixed_realization_designation(
                record,
                namespace=namespace,
                symbols=symbols,
            )
            for record in inner_provenance.realization_designations
        )

    provenance = ExpansionProvenance(
        imports=tuple(import_records),
        capability_constraints=tuple(capability_constraints),
        explicitness=tuple(explicitness_records),
        realization_designations=tuple(realization_records),
    )
    merged.pop("imports", None)
    merged.pop("module", None)
    merged.pop("realization", None)
    merged["expansion_provenance"] = provenance.model_dump(mode="python")
    return merged, provenance
