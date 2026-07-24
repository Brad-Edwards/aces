"""Pure finite semantic analysis for deterministic live activity."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from .._declarations import DeclarationIndex, build_declaration_index
from ..entities import flatten_entities
from ._live_activity_policy import budget_issues, dependency_issues, evidence_issues
from ._live_activity_types import LiveActivityIssue, activity_issue
from .domain_topology import resolve_section_ref


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _resolve_service(ref: object, nodes: Mapping[str, object]) -> tuple[str, str] | None:
    if not isinstance(ref, str):
        return None
    for node_name, node in nodes.items():
        for service in getattr(node, "services", ()):
            service_name = getattr(service, "name", "")
            if service_name and ref == f"nodes.{node_name}.services.{service_name}":
                return node_name, service_name
    return None


def _participant_bindings(
    agents: Mapping[str, object],
    *,
    entity_declarations: Mapping[str, object],
    accounts: Mapping[str, object],
) -> tuple[set[str], set[str]]:
    entity_ids: set[str] = set()
    account_ids: set[str] = set()
    for agent in agents.values():
        entity_ref = getattr(agent, "entity", "")
        entity_id = resolve_section_ref(entity_ref, "entities", entity_declarations)
        if entity_id is not None:
            entity_ids.add(entity_id)
        account_refs = [
            *getattr(agent, "starting_accounts", ()),
            *(
                access.account_ref
                for access in getattr(agent, "interactive_access", {}).values()
                if access.account_ref is not None
            ),
        ]
        knowledge = getattr(agent, "initial_knowledge", None)
        if knowledge is not None:
            account_refs.extend(getattr(knowledge, "accounts", ()))
        for account_ref in account_refs:
            account_id = resolve_section_ref(account_ref, "accounts", accounts)
            if account_id is not None:
                account_ids.add(account_id)
    return entity_ids, account_ids


def _targetable_addresses(index: DeclarationIndex, reference: str) -> set[str]:
    return {
        address
        for address in index.resolve(reference)
        if (declaration := index.declaration_for(address)) is not None and declaration.targetable
    }


def _baseline_facts(
    profile_name: str,
    profile: object,
    *,
    historical_baselines: Mapping[str, object],
    deployment_tenants: Mapping[str, object],
    deployment_cells: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[list[LiveActivityIssue], object | None, str | None, set[str], set[str]]:
    issues: list[LiveActivityIssue] = []
    baseline_ref = getattr(profile, "historical_baseline_ref", "")
    if is_unresolved(baseline_ref):
        return issues, None, None, set(), set()
    baseline_id = resolve_section_ref(baseline_ref, "historical_baselines", historical_baselines)
    if baseline_id is None:
        issues.append(
            activity_issue(
                "live-activity.baseline-unresolved",
                f"Activity profile '{profile_name}' historical baseline reference does not resolve",
            )
        )
        return issues, None, None, set(), set()
    baseline = historical_baselines[baseline_id]
    tenant_ref = getattr(baseline, "deployment_tenant_ref", "")
    tenant_id = (
        None if is_unresolved(tenant_ref) else resolve_section_ref(tenant_ref, "deployment_tenants", deployment_tenants)
    )
    cell_ref = getattr(baseline, "deployment_cell_ref", "")
    cell_id = None if is_unresolved(cell_ref) else resolve_section_ref(cell_ref, "deployment_cells", deployment_cells)
    cell_nodes = set(getattr(deployment_cells.get(cell_id), "node_refs", ())) if cell_id is not None else set()
    materialization_targets = {
        target_ref
        for binding in getattr(baseline, "materialization_bindings", {}).values()
        if not is_unresolved(target_ref := getattr(binding, "target_service_ref", ""))
    }
    return issues, baseline, tenant_id, cell_nodes, materialization_targets


def _actor_issues(
    profile_name: str,
    profile: object,
    *,
    tenant_id: str | None,
    entities: Mapping[str, object],
    accounts: Mapping[str, object],
    agents: Mapping[str, object],
    declaration_index: DeclarationIndex,
    is_unresolved: Callable[[object], bool],
) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    all_entities = flatten_entities(dict(entities))
    participant_entities, participant_accounts = _participant_bindings(
        agents,
        entity_declarations=all_entities,
        accounts=accounts,
    )
    for actor_id, actor in getattr(profile, "actors", {}).items():
        label = f"Activity actor '{profile_name}.{actor_id}'"
        entity_ref = getattr(actor, "entity_ref", "")
        account_ref = getattr(actor, "account_ref", "")
        actor_tenant_ref = getattr(actor, "deployment_tenant_ref", "")
        if not is_unresolved(entity_ref):
            entity_id = resolve_section_ref(entity_ref, "entities", all_entities)
            if entity_id is None:
                issues.append(
                    activity_issue("live-activity.actor-entity-unresolved", f"{label} entity does not resolve")
                )
            elif entity_id in participant_entities:
                issues.append(
                    activity_issue(
                        "live-activity.actor-participant-entity",
                        f"{label} entity is bound to a participant agent",
                    )
                )
        if not is_unresolved(account_ref):
            account_id = resolve_section_ref(account_ref, "accounts", accounts)
            if account_id is None:
                issues.append(
                    activity_issue("live-activity.actor-account-unresolved", f"{label} account does not resolve")
                )
            elif account_id in participant_accounts:
                issues.append(
                    activity_issue(
                        "live-activity.actor-participant-account",
                        f"{label} account is bound to a participant agent",
                    )
                )
        if not is_unresolved(actor_tenant_ref):
            resolved_tenant = resolve_section_ref(
                actor_tenant_ref,
                "deployment_tenants",
                {tenant_id: object()} if tenant_id is not None else {},
            )
            if resolved_tenant != tenant_id:
                issues.append(
                    activity_issue(
                        "live-activity.actor-tenant-mismatch",
                        f"{label} tenant does not match its historical baseline tenant",
                    )
                )
        for scope_ref in getattr(actor, "operating_scope_refs", ()):
            if not is_unresolved(scope_ref) and len(_targetable_addresses(declaration_index, scope_ref)) != 1:
                issues.append(
                    activity_issue(
                        "live-activity.actor-scope-unresolved",
                        f"{label} operating scope does not resolve to one named existing target",
                    )
                )
    return issues


def _context_issues(
    profile_name: str,
    profile: object,
    *,
    tenant_id: str | None,
    cell_nodes: set[str],
    materialization_targets: set[str],
    accounts: Mapping[str, object],
    nodes: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[list[LiveActivityIssue], dict[str, tuple[str, str]]]:
    issues: list[LiveActivityIssue] = []
    services: dict[str, tuple[str, str]] = {}
    for context_id, context in getattr(profile, "execution_contexts", {}).items():
        label = f"Activity execution context '{profile_name}.{context_id}'"
        context_tenant_ref = getattr(context, "deployment_tenant_ref", "")
        if not is_unresolved(context_tenant_ref):
            context_tenant = resolve_section_ref(
                context_tenant_ref,
                "deployment_tenants",
                {tenant_id: object()} if tenant_id is not None else {},
            )
            if context_tenant != tenant_id:
                issues.append(
                    activity_issue("live-activity.context-tenant-mismatch", f"{label} tenant does not match baseline")
                )
        account_ref = getattr(context, "account_ref", "")
        account_id = None if is_unresolved(account_ref) else resolve_section_ref(account_ref, "accounts", accounts)
        if account_id is None and not is_unresolved(account_ref):
            issues.append(
                activity_issue("live-activity.context-account-unresolved", f"{label} account does not resolve")
            )
        target_ref = getattr(context, "target_service_ref", "")
        service = None if is_unresolved(target_ref) else _resolve_service(target_ref, nodes)
        if service is None and not is_unresolved(target_ref):
            issues.append(
                activity_issue(
                    "live-activity.context-service-unresolved",
                    f"{label} target service does not resolve to a named existing service",
                )
            )
            continue
        if service is None:
            continue
        services[context_id] = service
        node_name, _service_name = service
        if node_name not in cell_nodes:
            issues.append(
                activity_issue(
                    "live-activity.context-cell-mismatch",
                    f"{label} target service is outside the historical baseline deployment cell",
                )
            )
        if account_id is not None and getattr(accounts[account_id], "node", "") != node_name:
            issues.append(
                activity_issue(
                    "live-activity.context-account-target-mismatch",
                    f"{label} account and target service must belong to the same named node",
                )
            )
        if target_ref not in materialization_targets:
            issues.append(
                activity_issue(
                    "live-activity.context-materialization-target-mismatch",
                    f"{label} target service is not governed by a historical baseline materialization binding",
                )
            )
    return issues, services


def _action_issues(
    profile_name: str,
    profile: object,
    *,
    activity_templates: Mapping[str, object],
    accounts: Mapping[str, object],
    historical_baseline_id: str | None,
    declaration_index: DeclarationIndex,
    is_unresolved: Callable[[object], bool],
) -> tuple[list[LiveActivityIssue], dict[str, object]]:
    issues: list[LiveActivityIssue] = []
    templates: dict[str, object] = {}
    actors = getattr(profile, "actors", {})
    contexts = getattr(profile, "execution_contexts", {})
    schedules = getattr(profile, "schedules", {})
    readback_actions = set(getattr(getattr(profile, "readback", None), "action_refs", ()))
    unresolved_readback_actions = readback_actions - set(getattr(profile, "actions", {}))
    if unresolved_readback_actions:
        issues.append(
            activity_issue(
                "live-activity.readback-action-unresolved",
                f"Activity profile '{profile_name}' readback action reference does not resolve",
            )
        )
    for action_id, action in getattr(profile, "actions", {}).items():
        label = f"Activity action '{profile_name}.{action_id}'"
        template_ref = getattr(action, "template_ref", "")
        template_id = (
            None
            if is_unresolved(template_ref)
            else resolve_section_ref(template_ref, "activity_templates", activity_templates)
        )
        if template_id is None and not is_unresolved(template_ref):
            issues.append(activity_issue("live-activity.template-unresolved", f"{label} template does not resolve"))
            continue
        if template_id is None:
            continue
        template = activity_templates[template_id]
        templates[action_id] = template
        actor_ref = getattr(action, "actor_ref", "")
        context_ref = getattr(action, "execution_context_ref", "")
        schedule_ref = getattr(action, "schedule_ref", "")
        for ref, declarations, code, noun in (
            (actor_ref, actors, "live-activity.actor-unresolved", "actor"),
            (context_ref, contexts, "live-activity.context-unresolved", "execution context"),
            (schedule_ref, schedules, "live-activity.schedule-unresolved", "schedule"),
        ):
            if not is_unresolved(ref) and ref not in declarations:
                issues.append(activity_issue(code, f"{label} {noun} reference does not resolve"))
        if context_ref in contexts and not is_unresolved(getattr(contexts[context_ref], "protocol", "")):
            if _enum_value(getattr(contexts[context_ref], "protocol", "")) != template.capability.protocol.value:
                issues.append(
                    activity_issue(
                        "live-activity.protocol-mismatch",
                        f"{label} template capability and execution-context protocol disagree",
                    )
                )
        parameters = getattr(template, "parameters", {})
        bindings = {binding.parameter_ref: binding for binding in getattr(action, "parameter_bindings", ())}
        if set(bindings) - set(parameters):
            issues.append(
                activity_issue("live-activity.parameter-unknown", f"{label} binds an undeclared template parameter")
            )
        missing = {name for name, parameter in parameters.items() if parameter.required} - set(bindings)
        if missing:
            issues.append(
                activity_issue("live-activity.parameter-missing", f"{label} omits required template parameters")
            )
        for parameter_name, binding in bindings.items():
            parameter = parameters.get(parameter_name)
            if parameter is None or is_unresolved(binding.value_ref):
                continue
            expected_kind = {
                "historical_object_ref": "historical-object",
                "content_ref": "content",
                "entity_ref": "entity",
                "account_ref": "accounts",
            }[parameter.kind.value]
            candidates = {
                address
                for address in declaration_index.resolve(binding.value_ref)
                if (declaration := declaration_index.declaration_for(address)) is not None
                and declaration.kind == expected_kind
            }
            if len(candidates) != 1:
                issues.append(
                    activity_issue(
                        "live-activity.parameter-unresolved",
                        f"{label} parameter '{parameter_name}' does not resolve to one "
                        f"{parameter.kind.value} declaration",
                    )
                )
            elif parameter.kind.value == "historical_object_ref":
                prefix = f"historical_baselines.{historical_baseline_id}.objects."
                if historical_baseline_id is None or not next(iter(candidates)).startswith(prefix):
                    issues.append(
                        activity_issue(
                            "live-activity.parameter-baseline-mismatch",
                            f"{label} historical object parameter is outside the selected baseline",
                        )
                    )
        if template.readback_class.value != "none" and action_id not in readback_actions:
            issues.append(
                activity_issue(
                    "live-activity.readback-action-missing",
                    f"{label} requires readback but is absent from the profile readback policy",
                )
            )
        if actor_ref in actors and context_ref in contexts:
            actor = actors[actor_ref]
            context = contexts[context_ref]
            actor_account = resolve_section_ref(actor.account_ref, "accounts", accounts)
            context_account = resolve_section_ref(context.account_ref, "accounts", accounts)
            if actor_account != context_account:
                issues.append(
                    activity_issue(
                        "live-activity.action-actor-account-mismatch",
                        f"{label} execution context does not use its actor account",
                    )
                )
            target_addresses = _targetable_addresses(declaration_index, context.target_service_ref)
            scope_addresses = set().union(
                *(
                    _targetable_addresses(declaration_index, scope_ref)
                    for scope_ref in actor.operating_scope_refs
                    if not is_unresolved(scope_ref)
                )
            )
            if target_addresses and target_addresses.isdisjoint(scope_addresses):
                issues.append(
                    activity_issue(
                        "live-activity.action-scope-mismatch",
                        f"{label} target service is outside its actor operating scope",
                    )
                )
    return issues, templates


def analyze_live_activity(
    scenario: object,
    *,
    is_unresolved: Callable[[object], bool],
) -> tuple[LiveActivityIssue, ...]:
    """Analyze every activity profile without provider or runtime side effects."""

    issues: list[LiveActivityIssue] = []
    declaration_index = build_declaration_index(scenario, raise_on_collision=False)
    for profile_name, profile in getattr(scenario, "activity_profiles", {}).items():
        baseline_issues, baseline, tenant_id, cell_nodes, materialization_targets = _baseline_facts(
            profile_name,
            profile,
            historical_baselines=scenario.historical_baselines,
            deployment_tenants=scenario.deployment_tenants,
            deployment_cells=scenario.deployment_cells,
            is_unresolved=is_unresolved,
        )
        issues.extend(baseline_issues)
        baseline_id = (
            None
            if baseline is None
            else resolve_section_ref(
                profile.historical_baseline_ref,
                "historical_baselines",
                scenario.historical_baselines,
            )
        )
        issues.extend(
            _actor_issues(
                profile_name,
                profile,
                tenant_id=tenant_id,
                entities=scenario.entities,
                accounts=scenario.accounts,
                agents=scenario.agents,
                declaration_index=declaration_index,
                is_unresolved=is_unresolved,
            )
        )
        context_issues, _services = _context_issues(
            profile_name,
            profile,
            tenant_id=tenant_id,
            cell_nodes=cell_nodes,
            materialization_targets=materialization_targets,
            accounts=scenario.accounts,
            nodes=scenario.nodes,
            is_unresolved=is_unresolved,
        )
        issues.extend(context_issues)
        action_issues, _templates = _action_issues(
            profile_name,
            profile,
            activity_templates=scenario.activity_templates,
            accounts=scenario.accounts,
            historical_baseline_id=baseline_id,
            declaration_index=declaration_index,
            is_unresolved=is_unresolved,
        )
        issues.extend(action_issues)
        issues.extend(dependency_issues(profile_name, profile))
        issues.extend(budget_issues(profile_name, profile))
        issues.extend(
            evidence_issues(
                profile_name,
                profile,
                scenario=scenario,
                evidence_requirements=scenario.evidence_requirements,
                is_unresolved=is_unresolved,
            )
        )
    return tuple(issues)


LiveActivityIssue.__module__ = __name__

__all__ = ["LiveActivityIssue", "analyze_live_activity"]
