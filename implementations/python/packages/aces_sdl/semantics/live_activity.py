"""Pure finite semantic analysis for deterministic live activity."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .._declarations import DeclarationIndex, build_declaration_index
from ..entities import flatten_entities
from ._live_activity_actions import ActionAnalysis, action_issues
from ._live_activity_policy import budget_issues, dependency_issues, evidence_issues
from ._live_activity_types import LiveActivityIssue, activity_issue
from .domain_topology import resolve_section_ref


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


@dataclass(frozen=True)
class _ActorAnalysis:
    tenant_id: str | None
    entities: Mapping[str, object]
    accounts: Mapping[str, object]
    participant_entities: set[str]
    participant_accounts: set[str]
    declaration_index: DeclarationIndex
    is_unresolved: Callable[[object], bool]


def _actor_identity_issues(label: str, actor: object, analysis: _ActorAnalysis) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    bindings = (
        (
            getattr(actor, "entity_ref", ""),
            "entities",
            analysis.entities,
            analysis.participant_entities,
            "live-activity.actor-entity-unresolved",
            "live-activity.actor-participant-entity",
            "entity",
        ),
        (
            getattr(actor, "account_ref", ""),
            "accounts",
            analysis.accounts,
            analysis.participant_accounts,
            "live-activity.actor-account-unresolved",
            "live-activity.actor-participant-account",
            "account",
        ),
    )
    for ref, section, declarations, participant_bindings, unresolved_code, participant_code, noun in bindings:
        if analysis.is_unresolved(ref):
            continue
        declaration_id = resolve_section_ref(ref, section, declarations)
        if declaration_id is None:
            issues.append(activity_issue(unresolved_code, f"{label} {noun} does not resolve"))
        elif declaration_id in participant_bindings:
            issues.append(activity_issue(participant_code, f"{label} {noun} is bound to a participant agent"))
    return issues


def _actor_tenancy_issues(label: str, actor: object, analysis: _ActorAnalysis) -> list[LiveActivityIssue]:
    tenant_ref = getattr(actor, "deployment_tenant_ref", "")
    if not analysis.is_unresolved(tenant_ref):
        resolved_tenant = resolve_section_ref(
            tenant_ref,
            "deployment_tenants",
            {analysis.tenant_id: object()} if analysis.tenant_id is not None else {},
        )
        if resolved_tenant != analysis.tenant_id:
            return [
                activity_issue(
                    "live-activity.actor-tenant-mismatch",
                    f"{label} tenant does not match its historical baseline tenant",
                )
            ]
    return []


def _actor_scope_issues(label: str, actor: object, analysis: _ActorAnalysis) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    for scope_ref in getattr(actor, "operating_scope_refs", ()):
        if (
            not analysis.is_unresolved(scope_ref)
            and len(_targetable_addresses(analysis.declaration_index, scope_ref)) != 1
        ):
            issues.append(
                activity_issue(
                    "live-activity.actor-scope-unresolved",
                    f"{label} operating scope does not resolve to one named existing target",
                )
            )
    return issues


def _actor_issues(profile_name: str, profile: object, analysis: _ActorAnalysis) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    for actor_id, actor in getattr(profile, "actors", {}).items():
        label = f"Activity actor '{profile_name}.{actor_id}'"
        issues.extend(_actor_identity_issues(label, actor, analysis))
        issues.extend(_actor_tenancy_issues(label, actor, analysis))
        issues.extend(_actor_scope_issues(label, actor, analysis))
    return issues


@dataclass(frozen=True)
class _ContextAnalysis:
    tenant_id: str | None
    cell_nodes: set[str]
    materialization_targets: set[str]
    accounts: Mapping[str, object]
    nodes: Mapping[str, object]
    is_unresolved: Callable[[object], bool]


def _context_tenant_issues(label: str, context: object, analysis: _ContextAnalysis) -> list[LiveActivityIssue]:
    tenant_ref = getattr(context, "deployment_tenant_ref", "")
    if not analysis.is_unresolved(tenant_ref):
        context_tenant = resolve_section_ref(
            tenant_ref,
            "deployment_tenants",
            {analysis.tenant_id: object()} if analysis.tenant_id is not None else {},
        )
        if context_tenant != analysis.tenant_id:
            return [
                activity_issue(
                    "live-activity.context-tenant-mismatch",
                    f"{label} tenant does not match baseline",
                )
            ]
    return []


def _context_account(
    label: str,
    context: object,
    analysis: _ContextAnalysis,
) -> tuple[str | None, list[LiveActivityIssue]]:
    account_ref = getattr(context, "account_ref", "")
    account_id = (
        None if analysis.is_unresolved(account_ref) else resolve_section_ref(account_ref, "accounts", analysis.accounts)
    )
    issues = []
    if account_id is None and not analysis.is_unresolved(account_ref):
        issues.append(activity_issue("live-activity.context-account-unresolved", f"{label} account does not resolve"))
    return account_id, issues


def _context_service(
    label: str,
    context: object,
    analysis: _ContextAnalysis,
) -> tuple[tuple[str, str] | None, list[LiveActivityIssue]]:
    target_ref = getattr(context, "target_service_ref", "")
    service = None if analysis.is_unresolved(target_ref) else _resolve_service(target_ref, analysis.nodes)
    issues = []
    if service is None and not analysis.is_unresolved(target_ref):
        issues.append(
            activity_issue(
                "live-activity.context-service-unresolved",
                f"{label} target service does not resolve to a named existing service",
            )
        )
    return service, issues


def _context_service_issues(
    label: str,
    context: object,
    account_id: str | None,
    service: tuple[str, str],
    analysis: _ContextAnalysis,
) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    node_name, _service_name = service
    if node_name not in analysis.cell_nodes:
        issues.append(
            activity_issue(
                "live-activity.context-cell-mismatch",
                f"{label} target service is outside the historical baseline deployment cell",
            )
        )
    if account_id is not None and getattr(analysis.accounts[account_id], "node", "") != node_name:
        issues.append(
            activity_issue(
                "live-activity.context-account-target-mismatch",
                f"{label} account and target service must belong to the same named node",
            )
        )
    if getattr(context, "target_service_ref", "") not in analysis.materialization_targets:
        issues.append(
            activity_issue(
                "live-activity.context-materialization-target-mismatch",
                f"{label} target service is not governed by a historical baseline materialization binding",
            )
        )
    return issues


def _context_issues(profile_name: str, profile: object, analysis: _ContextAnalysis) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    for context_id, context in getattr(profile, "execution_contexts", {}).items():
        label = f"Activity execution context '{profile_name}.{context_id}'"
        issues.extend(_context_tenant_issues(label, context, analysis))
        account_id, account_issues = _context_account(label, context, analysis)
        issues.extend(account_issues)
        service, service_issues = _context_service(label, context, analysis)
        issues.extend(service_issues)
        if service is not None:
            issues.extend(_context_service_issues(label, context, account_id, service, analysis))
    return issues


def analyze_live_activity(
    scenario: object,
    *,
    is_unresolved: Callable[[object], bool],
) -> tuple[LiveActivityIssue, ...]:
    """Analyze every activity profile without provider or runtime side effects."""

    issues: list[LiveActivityIssue] = []
    declaration_index = build_declaration_index(scenario, raise_on_collision=False)
    all_entities = flatten_entities(dict(scenario.entities))
    participant_entities, participant_accounts = _participant_bindings(
        scenario.agents,
        entity_declarations=all_entities,
        accounts=scenario.accounts,
    )
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
                _ActorAnalysis(
                    tenant_id=tenant_id,
                    entities=all_entities,
                    accounts=scenario.accounts,
                    participant_entities=participant_entities,
                    participant_accounts=participant_accounts,
                    declaration_index=declaration_index,
                    is_unresolved=is_unresolved,
                ),
            )
        )
        issues.extend(
            _context_issues(
                profile_name,
                profile,
                _ContextAnalysis(
                    tenant_id=tenant_id,
                    cell_nodes=cell_nodes,
                    materialization_targets=materialization_targets,
                    accounts=scenario.accounts,
                    nodes=scenario.nodes,
                    is_unresolved=is_unresolved,
                ),
            )
        )
        issues.extend(
            action_issues(
                profile_name,
                profile,
                ActionAnalysis(
                    activity_templates=scenario.activity_templates,
                    accounts=scenario.accounts,
                    historical_baseline_id=baseline_id,
                    declaration_index=declaration_index,
                    is_unresolved=is_unresolved,
                ),
            )
        )
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
