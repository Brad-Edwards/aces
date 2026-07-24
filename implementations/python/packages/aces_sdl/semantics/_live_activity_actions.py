"""Action-level semantic checks for deterministic live activity."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .._declarations import DeclarationIndex
from ._live_activity_types import LiveActivityIssue, activity_issue
from .domain_topology import resolve_section_ref


@dataclass(frozen=True)
class ActionAnalysis:
    activity_templates: Mapping[str, object]
    accounts: Mapping[str, object]
    historical_baseline_id: str | None
    declaration_index: DeclarationIndex
    is_unresolved: Callable[[object], bool]


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _targetable_addresses(index: DeclarationIndex, reference: str) -> set[str]:
    return {
        address
        for address in index.resolve(reference)
        if (declaration := index.declaration_for(address)) is not None and declaration.targetable
    }


def _reference_issues(
    label: str,
    action: object,
    actors: Mapping[str, object],
    contexts: Mapping[str, object],
    schedules: Mapping[str, object],
    analysis: ActionAnalysis,
) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    references = (
        (getattr(action, "actor_ref", ""), actors, "live-activity.actor-unresolved", "actor"),
        (
            getattr(action, "execution_context_ref", ""),
            contexts,
            "live-activity.context-unresolved",
            "execution context",
        ),
        (getattr(action, "schedule_ref", ""), schedules, "live-activity.schedule-unresolved", "schedule"),
    )
    for ref, declarations, code, noun in references:
        if not analysis.is_unresolved(ref) and ref not in declarations:
            issues.append(activity_issue(code, f"{label} {noun} reference does not resolve"))
    return issues


def _protocol_issues(
    label: str,
    template: object,
    context_ref: str,
    contexts: Mapping[str, object],
    analysis: ActionAnalysis,
) -> list[LiveActivityIssue]:
    if context_ref in contexts and not analysis.is_unresolved(getattr(contexts[context_ref], "protocol", "")):
        if _enum_value(getattr(contexts[context_ref], "protocol", "")) != template.capability.protocol.value:
            return [
                activity_issue(
                    "live-activity.protocol-mismatch",
                    f"{label} template capability and execution-context protocol disagree",
                )
            ]
    return []


def _parameter_binding_issues(
    label: str,
    template: object,
    action: object,
    analysis: ActionAnalysis,
) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    parameters = getattr(template, "parameters", {})
    bindings = {binding.parameter_ref: binding for binding in getattr(action, "parameter_bindings", ())}
    if set(bindings) - set(parameters):
        issues.append(
            activity_issue(
                "live-activity.parameter-unknown",
                f"{label} binds an undeclared template parameter",
            )
        )
    required = {name for name, parameter in parameters.items() if parameter.required}
    if required - set(bindings):
        issues.append(activity_issue("live-activity.parameter-missing", f"{label} omits required template parameters"))
    for parameter_name, binding in bindings.items():
        parameter = parameters.get(parameter_name)
        if parameter is not None:
            issues.extend(_bound_parameter_issues(label, parameter_name, parameter, binding, analysis))
    return issues


def _bound_parameter_issues(
    label: str,
    parameter_name: str,
    parameter: object,
    binding: object,
    analysis: ActionAnalysis,
) -> list[LiveActivityIssue]:
    if analysis.is_unresolved(binding.value_ref):
        return []
    expected_kind = {
        "historical_object_ref": "historical-object",
        "content_ref": "content",
        "entity_ref": "entity",
        "account_ref": "accounts",
    }[parameter.kind.value]
    candidates = {
        address
        for address in analysis.declaration_index.resolve(binding.value_ref)
        if (declaration := analysis.declaration_index.declaration_for(address)) is not None
        and declaration.kind == expected_kind
    }
    if len(candidates) != 1:
        return [
            activity_issue(
                "live-activity.parameter-unresolved",
                f"{label} parameter '{parameter_name}' does not resolve to one {parameter.kind.value} declaration",
            )
        ]
    issues: list[LiveActivityIssue] = []
    if parameter.kind.value == "historical_object_ref":
        prefix = f"historical_baselines.{analysis.historical_baseline_id}.objects."
        if analysis.historical_baseline_id is None or not next(iter(candidates)).startswith(prefix):
            issues.append(
                activity_issue(
                    "live-activity.parameter-baseline-mismatch",
                    f"{label} historical object parameter is outside the selected baseline",
                )
            )
    return issues


def _actor_context_issues(
    label: str,
    actor: object,
    context: object,
    analysis: ActionAnalysis,
) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    actor_account = resolve_section_ref(actor.account_ref, "accounts", analysis.accounts)
    context_account = resolve_section_ref(context.account_ref, "accounts", analysis.accounts)
    if actor_account != context_account:
        issues.append(
            activity_issue(
                "live-activity.action-actor-account-mismatch",
                f"{label} execution context does not use its actor account",
            )
        )
    target_addresses = _targetable_addresses(analysis.declaration_index, context.target_service_ref)
    scope_addresses = set().union(
        *(
            _targetable_addresses(analysis.declaration_index, scope_ref)
            for scope_ref in actor.operating_scope_refs
            if not analysis.is_unresolved(scope_ref)
        )
    )
    if target_addresses and target_addresses.isdisjoint(scope_addresses):
        issues.append(
            activity_issue(
                "live-activity.action-scope-mismatch",
                f"{label} target service is outside its actor operating scope",
            )
        )
    return issues


def _single_action_issues(
    profile_name: str,
    action_id: str,
    action: object,
    profile: object,
    analysis: ActionAnalysis,
) -> list[LiveActivityIssue]:
    label = f"Activity action '{profile_name}.{action_id}'"
    template_ref = getattr(action, "template_ref", "")
    template_id = (
        None
        if analysis.is_unresolved(template_ref)
        else resolve_section_ref(template_ref, "activity_templates", analysis.activity_templates)
    )
    if template_id is None:
        if not analysis.is_unresolved(template_ref):
            return [activity_issue("live-activity.template-unresolved", f"{label} template does not resolve")]
        return []
    template = analysis.activity_templates[template_id]
    actors = getattr(profile, "actors", {})
    contexts = getattr(profile, "execution_contexts", {})
    schedules = getattr(profile, "schedules", {})
    actor_ref = getattr(action, "actor_ref", "")
    context_ref = getattr(action, "execution_context_ref", "")
    issues = _reference_issues(label, action, actors, contexts, schedules, analysis)
    issues.extend(_protocol_issues(label, template, context_ref, contexts, analysis))
    issues.extend(_parameter_binding_issues(label, template, action, analysis))
    readback_actions = set(getattr(getattr(profile, "readback", None), "action_refs", ()))
    if template.readback_class.value != "none" and action_id not in readback_actions:
        issues.append(
            activity_issue(
                "live-activity.readback-action-missing",
                f"{label} requires readback but is absent from the profile readback policy",
            )
        )
    if actor_ref in actors and context_ref in contexts:
        issues.extend(_actor_context_issues(label, actors[actor_ref], contexts[context_ref], analysis))
    return issues


def action_issues(
    profile_name: str,
    profile: object,
    analysis: ActionAnalysis,
) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    actions = getattr(profile, "actions", {})
    readback_actions = set(getattr(getattr(profile, "readback", None), "action_refs", ()))
    if readback_actions - set(actions):
        issues.append(
            activity_issue(
                "live-activity.readback-action-unresolved",
                f"Activity profile '{profile_name}' readback action reference does not resolve",
            )
        )
    for action_id, action in actions.items():
        issues.extend(_single_action_issues(profile_name, action_id, action, profile, analysis))
    return issues


__all__ = ["ActionAnalysis", "action_issues"]
