"""Module/import expansion for multi-file SDL scenarios."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ._base import is_variable_ref
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
    resolved_import_record as _resolved_import_record,
)
from ._errors import SDLInstantiationError, SDLParseDiagnostic, SDLParseError
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
from .phase_contracts import (
    CapabilityConstraint,
    ExpansionProvenance,
    ExplicitnessProvenanceRecord,
    ResolvedImportProvenance,
)
from .scenario import ExpandedScenario, ImportDecl, ModuleDescriptor, ScenarioContent


def _prefix(namespace: str, name: str) -> str:
    return QualifiedName.parse(name).prefixed(namespace).render() if namespace else QualifiedName.parse(name).render()


def _private_prefix(namespace: str, name: str) -> str:
    return QualifiedName.parse(name).prefixed(namespace, private=True).render()


def _maybe_rename(name: str, name_map: Mapping[str, str]) -> str:
    if not name or is_variable_ref(name):
        return name
    return name_map.get(name, name)


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


def _rewrite_workflow(payload: dict[str, Any], symbols: dict[str, dict[str, str] | set[str]]) -> None:
    for step in payload.get("steps", {}).values():
        if not isinstance(step, dict):
            continue
        if step.get("objective"):
            step["objective"] = _maybe_rename(str(step["objective"]), symbols["objectives"])
        if step.get("workflow"):
            step["workflow"] = _maybe_rename(str(step["workflow"]), symbols["workflows"])
        if step.get("compensate_with"):
            step["compensate_with"] = _maybe_rename(str(step["compensate_with"]), symbols["workflows"])
        when = step.get("when")
        if isinstance(when, dict):
            when["conditions"] = [_maybe_rename(name, symbols["conditions"]) for name in when.get("conditions", [])]
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

    for node in namespaced.get("nodes", {}).values():
        if isinstance(node, dict):
            _rewrite_node(node, symbols)
    for infra in namespaced.get("infrastructure", {}).values():
        if isinstance(infra, dict):
            _rewrite_infrastructure(infra, symbols)
    for feature in namespaced.get("features", {}).values():
        if isinstance(feature, dict):
            _rewrite_feature(feature, symbols)
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
            event["conditions"] = [_maybe_rename(name, symbols["conditions"]) for name in event.get("conditions", [])]
            event["injects"] = [_maybe_rename(name, symbols["injects"]) for name in event.get("injects", [])]
    for script in namespaced.get("scripts", {}).values():
        if isinstance(script, dict):
            script["events"] = {
                _maybe_rename(name, symbols["events"]): value for name, value in script.get("events", {}).items()
            }
    for story in namespaced.get("stories", {}).values():
        if isinstance(story, dict):
            story["scripts"] = [_maybe_rename(name, symbols["scripts"]) for name in story.get("scripts", [])]
    for content in namespaced.get("content", {}).values():
        if isinstance(content, dict) and content.get("target"):
            content["target"] = _maybe_rename(str(content["target"]), symbols["nodes"])
    for account in namespaced.get("accounts", {}).values():
        if isinstance(account, dict) and account.get("node"):
            account["node"] = _maybe_rename(str(account["node"]), symbols["nodes"])
    for relationship in namespaced.get("relationships", {}).values():
        if isinstance(relationship, dict):
            if relationship.get("source"):
                relationship["source"] = _maybe_rename(str(relationship["source"]), symbols["named"])
            if relationship.get("target"):
                relationship["target"] = _maybe_rename(str(relationship["target"]), symbols["named"])
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
            agent["starting_conditions"] = [
                _maybe_rename(name, symbols["named"]) for name in agent.get("starting_conditions", [])
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
            success["conditions"] = [
                _maybe_rename(name, symbols["conditions"]) for name in success.get("conditions", [])
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
            _rewrite_workflow(workflow, symbols)

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
    namespaced.pop("variables", None)
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
            import_path.read_text(encoding="utf-8"),
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
            bound = _bind_scenario_content(imported_scenario, import_decl.parameters)
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
        )

    provenance = ExpansionProvenance(
        imports=tuple(import_records),
        capability_constraints=tuple(capability_constraints),
        explicitness=tuple(explicitness_records),
    )
    merged.pop("imports", None)
    merged.pop("module", None)
    merged["expansion_provenance"] = provenance.model_dump(mode="python")
    return merged, provenance
