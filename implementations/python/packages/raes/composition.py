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
from .participant_inject_delivery import participant_inject_delivery_reference
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


def _rewrite_node_or_service_ref(name: str, node_map: Mapping[str, str]) -> str:
    """Rewrite a node ref while preserving an optional named-service suffix."""

    if not name or is_variable_ref(name):
        return name
    for local_name, qualified_name in sorted(node_map.items(), key=lambda item: len(item[0]), reverse=True):
        service_prefix = f"nodes.{local_name}.services."
        if name.startswith(service_prefix):
            return f"nodes.{qualified_name}.services.{name.removeprefix(service_prefix)}"
    return _rewrite_section_ref(name, "nodes", node_map)


def _rewrite_participant_resource_budget(
    payload: object,
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    """Rewrite kind-specific owner references in an autonomous budget policy."""

    if not isinstance(payload, dict):
        return
    owners = payload.get("owners")
    if not isinstance(owners, dict):
        return
    for owner in owners.values():
        if not isinstance(owner, dict) or not owner.get("ref"):
            continue
        reference = str(owner["ref"])
        owner_kind = owner.get("kind")
        if owner_kind == "participant":
            owner["ref"] = _rewrite_section_ref(reference, "agents", symbols["agents"])
        elif owner_kind == "deployment_tenant":
            owner["ref"] = _rewrite_section_ref(
                reference,
                "deployment_tenants",
                symbols["deployment_tenants"],
            )
        elif owner_kind == "shared_service":
            owner["ref"] = _rewrite_node_or_service_ref(reference, symbols["nodes"])


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


def _rewrite_time_clocks(
    namespaced: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for clock in namespaced.get("clocks", {}).values():
        if isinstance(clock, dict) and clock.get("time_domain_ref"):
            clock["time_domain_ref"] = _maybe_rename(
                str(clock["time_domain_ref"]),
                symbols["time_domains"],
            )


def _rewrite_time_mappings(
    namespaced: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for mapping in namespaced.get("time_domain_mappings", {}).values():
        if not isinstance(mapping, dict):
            continue
        for field_name in ("source_domain_ref", "target_domain_ref"):
            if mapping.get(field_name):
                mapping[field_name] = _maybe_rename(
                    str(mapping[field_name]),
                    symbols["time_domains"],
                )


def _rewrite_time_progression(
    namespaced: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for policy in namespaced.get("time_progression_policies", {}).values():
        if isinstance(policy, dict) and policy.get("clock_ref"):
            policy["clock_ref"] = _maybe_rename(
                str(policy["clock_ref"]),
                symbols["clocks"],
            )


def _rewrite_time_constraints(
    namespaced: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for constraint in namespaced.get("temporal_constraints", {}).values():
        if not isinstance(constraint, dict):
            continue
        if constraint.get("clock_ref"):
            constraint["clock_ref"] = _maybe_rename(
                str(constraint["clock_ref"]),
                symbols["clocks"],
            )
        constraint["subject_refs"] = [
            _maybe_rename(name, symbols["named"]) for name in constraint.get("subject_refs", [])
        ]


def _rewrite_time_model(
    namespaced: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    _rewrite_time_clocks(namespaced, symbols)
    _rewrite_time_mappings(namespaced, symbols)
    _rewrite_time_progression(namespaced, symbols)
    _rewrite_time_constraints(namespaced, symbols)


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


def _rewrite_participant_inject_delivery(
    binding: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    binding["participant_ref"] = _maybe_rename(str(binding.get("participant_ref", "")), symbols["agents"])
    binding["inject_ref"] = _maybe_rename(str(binding.get("inject_ref", "")), symbols["injects"])
    occurrence = binding.get("occurrence")
    if isinstance(occurrence, dict):
        for field_name, section_name in (
            ("event_ref", "events"),
            ("script_ref", "scripts"),
            ("story_ref", "stories"),
        ):
            if occurrence.get(field_name):
                occurrence[field_name] = _maybe_rename(str(occurrence[field_name]), symbols[section_name])
    for field_name in ("source_item_ref", "result_item_ref"):
        if binding.get(field_name):
            binding[field_name] = _maybe_rename(str(binding[field_name]), symbols["named"])
    binding["observation_boundary_ref"] = _maybe_rename(
        str(binding.get("observation_boundary_ref", "")),
        symbols["observation_boundaries"],
    )
    binding["temporal_constraint_refs"] = [
        _maybe_rename(ref, symbols["temporal_constraints"]) for ref in binding.get("temporal_constraint_refs", [])
    ]
    binding["evidence_requirement_refs"] = [
        _maybe_rename(ref, symbols["evidence_requirements"]) for ref in binding.get("evidence_requirement_refs", [])
    ]
    controller_ref = binding.get("controller_ref")
    if controller_ref and controller_ref != "self":
        binding["controller_ref"] = _maybe_rename(str(controller_ref), symbols["agents"])
    binding["control_authority_scope_refs"] = [
        _maybe_rename(ref, symbols["named"]) for ref in binding.get("control_authority_scope_refs", [])
    ]
    binding["control_evidence_refs"] = [
        _maybe_rename(ref, symbols["named"]) for ref in binding.get("control_evidence_refs", [])
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


def _behavior_reference_maps(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
    namespace: str,
) -> tuple[dict[str, str], dict[str, str]]:
    tool_affordances: dict[str, str] = {}
    inject_deliveries: dict[str, str] = {}
    for spec_name, behavior_spec in payload.get("behavior_specifications", {}).items():
        if not isinstance(behavior_spec, dict):
            continue
        namespaced_name = symbols["behavior_specifications"].get(
            spec_name,
            _prefix(namespace, spec_name),
        )
        for affordance_id in behavior_spec.get("tool_affordances", {}):
            tool_affordances[tool_affordance_reference(spec_name, affordance_id)] = tool_affordance_reference(
                namespaced_name,
                affordance_id,
            )
        for binding_id in behavior_spec.get("participant_inject_deliveries", {}):
            inject_deliveries[participant_inject_delivery_reference(spec_name, binding_id)] = (
                participant_inject_delivery_reference(namespaced_name, binding_id)
            )
    named_symbols = symbols["named"]
    if isinstance(named_symbols, dict):
        named_symbols.update(tool_affordances)
        named_symbols.update(inject_deliveries)
    return tool_affordances, inject_deliveries


def _rewrite_foundational_sections(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for node in payload.get("nodes", {}).values():
        if isinstance(node, dict):
            _rewrite_node(node, symbols)
    for infrastructure in payload.get("infrastructure", {}).values():
        if isinstance(infrastructure, dict):
            _rewrite_infrastructure(infrastructure, symbols)
    for feature in payload.get("features", {}).values():
        if isinstance(feature, dict):
            _rewrite_feature(feature, symbols)
    for entity in payload.get("entities", {}).values():
        if isinstance(entity, dict):
            _rewrite_entity(entity, symbols)


def _rewrite_proposition_sections(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for condition in payload.get("conditions", {}).values():
        if isinstance(condition, dict) and condition.get("proposition"):
            condition["proposition"] = _maybe_rename(str(condition["proposition"]), symbols["propositions"])
    for proposition in payload.get("propositions", {}).values():
        if isinstance(proposition, dict):
            proposition["subjects"] = [
                _maybe_rename(name, symbols["named"]) for name in proposition.get("subjects", [])
            ]
            proposition["evidence_requirements"] = [
                _maybe_rename(name, symbols["evidence_requirements"])
                for name in proposition.get("evidence_requirements", [])
            ]
    for assertion in payload.get("assertions", {}).values():
        if isinstance(assertion, dict) and assertion.get("proposition"):
            assertion["proposition"] = _maybe_rename(str(assertion["proposition"]), symbols["propositions"])


def _rewrite_narrative_sections(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for inject in payload.get("injects", {}).values():
        if isinstance(inject, dict):
            if inject.get("from_entity"):
                inject["from_entity"] = _maybe_rename(str(inject["from_entity"]), symbols["entities"])
            inject["to_entities"] = [_maybe_rename(name, symbols["entities"]) for name in inject.get("to_entities", [])]
    for event in payload.get("events", {}).values():
        if isinstance(event, dict):
            event["assertions"] = [_maybe_rename(name, symbols["assertions"]) for name in event.get("assertions", [])]
            event["injects"] = [_maybe_rename(name, symbols["injects"]) for name in event.get("injects", [])]
    for script in payload.get("scripts", {}).values():
        if isinstance(script, dict):
            script["events"] = {
                _maybe_rename(name, symbols["events"]): value for name, value in script.get("events", {}).items()
            }
    for story in payload.get("stories", {}).values():
        if isinstance(story, dict):
            story["scripts"] = [_maybe_rename(name, symbols["scripts"]) for name in story.get("scripts", [])]


def _rewrite_observation_boundaries(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
    tool_affordance_refs: Mapping[str, str],
) -> None:
    for boundary in payload.get("observation_boundaries", {}).values():
        if not isinstance(boundary, dict):
            continue
        for field_name in ("observable_refs", "hidden_refs", "evidence_refs"):
            boundary[field_name] = [
                tool_affordance_refs.get(ref, _maybe_rename(ref, symbols["named"]))
                for ref in boundary.get(field_name, [])
            ]
        for field_name in ("view_rules", "view_transitions"):
            for item in boundary.get(field_name, []):
                if isinstance(item, dict) and isinstance(item.get("information_ref"), str):
                    information_ref = item["information_ref"]
                    item["information_ref"] = tool_affordance_refs.get(
                        information_ref,
                        _maybe_rename(information_ref, symbols["named"]),
                    )


def _rewrite_service_materialization(
    materialization: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    if materialization.get("target_service_ref"):
        materialization["target_service_ref"] = _rewrite_node_or_service_ref(
            str(materialization["target_service_ref"]),
            symbols["nodes"],
        )
    if materialization.get("shared_service_relationship_ref"):
        materialization["shared_service_relationship_ref"] = _rewrite_section_ref(
            str(materialization["shared_service_relationship_ref"]),
            "relationships",
            symbols["relationships"],
        )
    for field_name, section_name in (
        ("ordering_content_refs", "content"),
        ("readback_assertion_refs", "assertions"),
        ("evidence_requirement_refs", "evidence_requirements"),
        ("observation_boundary_refs", "observation_boundaries"),
    ):
        materialization[field_name] = [
            _rewrite_section_ref(reference, section_name, symbols[section_name])
            for reference in materialization.get(field_name, [])
        ]


def _rewrite_content_sections(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for content in payload.get("content", {}).values():
        if not isinstance(content, dict):
            continue
        if content.get("target"):
            content["target"] = _rewrite_section_ref(str(content["target"]), "nodes", symbols["nodes"])
        materialization = content.get("service_materialization")
        if isinstance(materialization, dict):
            _rewrite_service_materialization(materialization, symbols)


def _rewrite_resource_consumers(
    resource: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for consumer in resource.get("consumers", []):
        if isinstance(consumer, dict) and consumer.get("node"):
            consumer["node"] = _maybe_rename(str(consumer["node"]), symbols["nodes"])


def _rewrite_resource_dependencies(
    resource: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
    *,
    owner: str,
) -> None:
    for dependency_field in ("ordering_dependencies", "refresh_dependencies"):
        resource[dependency_field] = [
            _rewrite_stateful_dependency_ref(reference, symbols, owner=owner)
            for reference in resource.get(dependency_field, [])
        ]


def _rewrite_stateful_resource(
    resource: Any,
    symbols: dict[str, dict[str, str] | set[str]],
    *,
    owner: str,
) -> None:
    if isinstance(resource, dict):
        _rewrite_resource_consumers(resource, symbols)
        _rewrite_resource_dependencies(resource, symbols, owner=owner)


def _rewrite_stateful_resources(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for section_name in ("generated_artifacts", "persistent_volumes"):
        for resource_name, resource in payload.get(section_name, {}).items():
            _rewrite_stateful_resource(resource, symbols, owner=f"{section_name}.{resource_name}")


def _rewrite_account(
    account: Any,
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    if not isinstance(account, dict):
        return
    if account.get("node"):
        account["node"] = _maybe_rename(str(account["node"]), symbols["nodes"])
    if account.get("domain_ref"):
        account["domain_ref"] = _maybe_rename(str(account["domain_ref"]), symbols["identity_domains"])


def _rewrite_identity_domain(
    domain: Any,
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    if isinstance(domain, dict) and domain.get("authority_account_ref"):
        domain["authority_account_ref"] = _maybe_rename(
            str(domain["authority_account_ref"]),
            symbols["accounts"],
        )


def _rewrite_identity_forest(
    forest: Any,
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    if not isinstance(forest, dict):
        return
    if forest.get("root_domain_ref"):
        forest["root_domain_ref"] = _maybe_rename(
            str(forest["root_domain_ref"]),
            symbols["identity_domains"],
        )
    forest["domain_refs"] = [_maybe_rename(name, symbols["identity_domains"]) for name in forest.get("domain_refs", [])]


def _rewrite_account_and_domain_sections(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for account in payload.get("accounts", {}).values():
        _rewrite_account(account, symbols)
    for domain in payload.get("identity_domains", {}).values():
        _rewrite_identity_domain(domain, symbols)
    for forest in payload.get("identity_forests", {}).values():
        _rewrite_identity_forest(forest, symbols)


def _rewrite_deployment_sections(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for facade in payload.get("identity_facades", {}).values():
        if isinstance(facade, dict) and facade.get("service_ref"):
            facade["service_ref"] = _maybe_rename(str(facade["service_ref"]), symbols["named"])
    for cell in payload.get("deployment_cells", {}).values():
        if not isinstance(cell, dict):
            continue
        if cell.get("tenant_ref"):
            cell["tenant_ref"] = _maybe_rename(str(cell["tenant_ref"]), symbols["deployment_tenants"])
        cell["node_refs"] = [_maybe_rename(name, symbols["nodes"]) for name in cell.get("node_refs", [])]


def _rewrite_relationship_sections(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for relationship in payload.get("relationships", {}).values():
        if not isinstance(relationship, dict):
            continue
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


def _rewrite_agent_access(
    agent: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for access in agent.get("interactive_access", {}).values():
        if not isinstance(access, dict):
            continue
        if access.get("target_ref"):
            access["target_ref"] = _rewrite_section_ref(str(access["target_ref"]), "nodes", symbols["nodes"])
        if access.get("account_ref"):
            access["account_ref"] = _rewrite_section_ref(
                str(access["account_ref"]),
                "accounts",
                symbols["accounts"],
            )


def _rewrite_agent_knowledge(
    agent: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    knowledge = agent.get("initial_knowledge")
    if not isinstance(knowledge, dict):
        return
    for field_name, symbol_key in (
        ("hosts", "nodes"),
        ("subnets", "infrastructure"),
        ("accounts", "accounts"),
    ):
        knowledge[field_name] = [_maybe_rename(name, symbols[symbol_key]) for name in knowledge.get(field_name, [])]


def _rewrite_agent(
    agent: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    if agent.get("entity"):
        agent["entity"] = _maybe_rename(str(agent["entity"]), symbols["entities"])
    for field_name, symbol_key in (
        ("starting_accounts", "accounts"),
        ("actions", "action_contracts"),
        ("observation_boundaries", "observation_boundaries"),
        ("allowed_subnets", "infrastructure"),
        ("starting_assertions", "assertions"),
        ("authority_anchors", "named"),
        ("operating_scope", "named"),
    ):
        agent[field_name] = [_maybe_rename(name, symbols[symbol_key]) for name in agent.get(field_name, [])]
    _rewrite_agent_access(agent, symbols)
    _rewrite_agent_knowledge(agent, symbols)


def _rewrite_agent_sections(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for agent in payload.get("agents", {}).values():
        if isinstance(agent, dict):
            _rewrite_agent(agent, symbols)


def _rewrite_behavior_specification(
    behavior_spec: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for field_name, symbol_key in (
        ("participant_refs", "agents"),
        ("action_contract_refs", "action_contracts"),
        ("observation_boundary_refs", "observation_boundaries"),
        ("outcome_interpretation_rule_refs", "outcome_interpretation_rules"),
        ("authority_scope_refs", "named"),
    ):
        behavior_spec[field_name] = [
            _maybe_rename(name, symbols[symbol_key]) for name in behavior_spec.get(field_name, [])
        ]
    autonomous_execution = behavior_spec.get("autonomous_execution")
    if isinstance(autonomous_execution, dict):
        _rewrite_participant_resource_budget(autonomous_execution.get("resource_budget"), symbols)
    _rewrite_mixed_control(behavior_spec.get("mixed_control"), symbols)
    for binding in behavior_spec.get("tool_affordances", {}).values():
        if isinstance(binding, dict):
            _rewrite_tool_affordance(binding, symbols)
    for binding in behavior_spec.get("participant_inject_deliveries", {}).values():
        if isinstance(binding, dict):
            _rewrite_participant_inject_delivery(binding, symbols)


def _rewrite_behavior_sections(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for behavior_spec in payload.get("behavior_specifications", {}).values():
        if isinstance(behavior_spec, dict):
            _rewrite_behavior_specification(behavior_spec, symbols)
    for requirement in payload.get("evidence_requirements", {}).values():
        if isinstance(requirement, dict):
            _rewrite_evidence_requirement(requirement, symbols)


def _rewrite_objective_window(
    window: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    for field_name, symbol_key in (
        ("stories", "stories"),
        ("scripts", "scripts"),
        ("events", "events"),
        ("workflows", "workflows"),
    ):
        window[field_name] = [_maybe_rename(name, symbols[symbol_key]) for name in window.get(field_name, [])]
    window["steps"] = [_rewrite_objective_window_ref(name, symbols["workflows"]) for name in window.get("steps", [])]


def _rewrite_objective(
    objective: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
) -> None:
    if objective.get("agent"):
        objective["agent"] = _maybe_rename(str(objective["agent"]), symbols["agents"])
    if objective.get("entity"):
        objective["entity"] = _maybe_rename(str(objective["entity"]), symbols["entities"])
    objective["targets"] = [_maybe_rename(name, symbols["named"]) for name in objective.get("targets", [])]
    objective["depends_on"] = [_maybe_rename(name, symbols["objectives"]) for name in objective.get("depends_on", [])]
    success = objective.get("success")
    if isinstance(success, dict):
        success["assertions"] = [_maybe_rename(name, symbols["assertions"]) for name in success.get("assertions", [])]
    window = objective.get("window")
    if isinstance(window, dict):
        _rewrite_objective_window(window, symbols)


def _rewrite_terminal_sections(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
    tool_affordance_refs: Mapping[str, str],
) -> None:
    _rewrite_time_model(payload, symbols)
    for objective in payload.get("objectives", {}).values():
        if isinstance(objective, dict):
            _rewrite_objective(objective, symbols)
    for workflow in payload.get("workflows", {}).values():
        if isinstance(workflow, dict):
            _rewrite_workflow(workflow, symbols, tool_affordance_refs)
    for variation_point in payload.get("variation_points", {}).values():
        if isinstance(variation_point, dict):
            _rewrite_variation_point(variation_point, symbols)


def _namespace_declaration_keys(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
    namespace: str,
) -> None:
    for section_name in _HASHMAP_SECTIONS:
        section_payload = payload.get(section_name)
        if isinstance(section_payload, dict):
            payload[section_name] = {
                symbols[section_name].get(name, _prefix(namespace, name)): value
                for name, value in section_payload.items()
            }


def _namespace_forwarding_agents(
    payload: dict[str, Any],
    symbols: dict[str, dict[str, str] | set[str]],
    namespace: str,
) -> None:
    forwarding_agents = payload.get(FORWARDING_AGENTS_SECTION, [])
    if not isinstance(forwarding_agents, list):
        return
    for agent in forwarding_agents:
        if isinstance(agent, dict) and isinstance(agent.get("forwarding_agent_id"), str):
            identifier = agent["forwarding_agent_id"]
            agent["forwarding_agent_id"] = symbols[FORWARDING_AGENTS_SECTION].get(
                identifier,
                _private_prefix(namespace, identifier),
            )


def _strip_composition_fields(payload: dict[str, Any]) -> None:
    for field_name in ("module", "imports", "expansion_provenance", "instantiation_provenance"):
        payload.pop(field_name, None)


def _rewrite_payload_with_symbols(
    payload: dict[str, Any],
    *,
    symbols: dict[str, dict[str, str] | set[str]],
    namespace: str = "",
    strip_composition_fields: bool = False,
) -> dict[str, Any]:
    """Rewrite declarations and references through one canonical symbol map.

    Module composition and semantic transformations share this implementation
    so new reference-bearing SDL fields cannot drift between the two surfaces.
    The caller supplies an isolated ``model_dump`` payload; this function never
    receives or mutates a caller-owned scenario model.
    """

    namespaced = dict(payload)
    tool_affordance_refs, _ = _behavior_reference_maps(namespaced, symbols, namespace)
    _rewrite_foundational_sections(namespaced, symbols)
    _rewrite_proposition_sections(namespaced, symbols)
    _rewrite_narrative_sections(namespaced, symbols)
    _rewrite_observation_boundaries(namespaced, symbols, tool_affordance_refs)
    _rewrite_content_sections(namespaced, symbols)
    _rewrite_stateful_resources(namespaced, symbols)
    _rewrite_account_and_domain_sections(namespaced, symbols)
    _rewrite_deployment_sections(namespaced, symbols)
    _rewrite_relationship_sections(namespaced, symbols)
    _rewrite_agent_sections(namespaced, symbols)
    _rewrite_behavior_sections(namespaced, symbols)
    _rewrite_terminal_sections(namespaced, symbols, tool_affordance_refs)

    rewritten = _rewrite_variable_tokens(namespaced, symbols["variables"])
    if not isinstance(rewritten, dict):
        raise TypeError("variable rewriting returned a non-object payload")
    namespaced = rewritten
    _namespace_declaration_keys(namespaced, symbols, namespace)
    _namespace_forwarding_agents(namespaced, symbols, namespace)
    if strip_composition_fields:
        _strip_composition_fields(namespaced)
    return namespaced


def _namespace_payload(
    payload: dict[str, Any],
    imported: ScenarioContent,
    namespace: str,
    descriptor: ModuleDescriptor,
) -> dict[str, Any]:
    _validate_descriptor_exports(imported, descriptor)
    symbols = _symbol_index(
        imported,
        namespace=namespace,
        descriptor=descriptor,
        restrict_to_descriptor=True,
    )
    return _rewrite_payload_with_symbols(
        payload,
        symbols=symbols,
        namespace=namespace,
        strip_composition_fields=True,
    )


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
