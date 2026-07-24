"""Composition rewriting for deterministic live-activity references."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

_Symbols = Mapping[str, Mapping[str, str] | set[str]]
_Rename = Callable[[str, Mapping[str, str]], str]


def _symbol_map(symbols: _Symbols, name: str) -> Mapping[str, str]:
    value = symbols[name]
    return value if isinstance(value, Mapping) else {}


def _rewrite_actor(actor: dict[str, Any], symbols: _Symbols, rename: _Rename) -> None:
    actor["entity_ref"] = rename(actor.get("entity_ref", ""), _symbol_map(symbols, "entities"))
    actor["account_ref"] = rename(actor.get("account_ref", ""), _symbol_map(symbols, "accounts"))
    actor["deployment_tenant_ref"] = rename(
        actor.get("deployment_tenant_ref", ""),
        _symbol_map(symbols, "deployment_tenants"),
    )
    actor["operating_scope_refs"] = [
        rename(ref, _symbol_map(symbols, "named")) for ref in actor.get("operating_scope_refs", [])
    ]


def _rewrite_context(context: dict[str, Any], symbols: _Symbols, rename: _Rename) -> None:
    context["deployment_tenant_ref"] = rename(
        context.get("deployment_tenant_ref", ""),
        _symbol_map(symbols, "deployment_tenants"),
    )
    context["account_ref"] = rename(
        context.get("account_ref", ""),
        _symbol_map(symbols, "accounts"),
    )
    context["target_service_ref"] = rename(
        context.get("target_service_ref", ""),
        _symbol_map(symbols, "named"),
    )


def _rewrite_action(action: dict[str, Any], symbols: _Symbols, rename: _Rename) -> None:
    action["template_ref"] = rename(
        action.get("template_ref", ""),
        _symbol_map(symbols, "activity_templates"),
    )
    for binding in action.get("parameter_bindings", []):
        if isinstance(binding, dict):
            binding["value_ref"] = rename(binding.get("value_ref", ""), _symbol_map(symbols, "named"))


def _rewrite_evidence_policy(policy: dict[str, Any], symbols: _Symbols, rename: _Rename) -> None:
    policy["observability_refs"] = [
        rename(ref, _symbol_map(symbols, "named")) for ref in policy.get("observability_refs", [])
    ]
    policy["evidence_requirement_refs"] = [
        rename(ref, _symbol_map(symbols, "evidence_requirements"))
        for ref in policy.get("evidence_requirement_refs", [])
    ]


def _dictionary_values(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, dict):
        return ()
    return tuple(item for item in value.values() if isinstance(item, dict))


def _rewrite_profile(profile: dict[str, Any], symbols: _Symbols, rename: _Rename) -> None:
    profile["historical_baseline_ref"] = rename(
        profile.get("historical_baseline_ref", ""),
        _symbol_map(symbols, "historical_baselines"),
    )
    for actor in _dictionary_values(profile.get("actors")):
        _rewrite_actor(actor, symbols, rename)
    for context in _dictionary_values(profile.get("execution_contexts")):
        _rewrite_context(context, symbols, rename)
    for action in _dictionary_values(profile.get("actions")):
        _rewrite_action(action, symbols, rename)
    for policy_name in ("readback", "telemetry"):
        policy = profile.get(policy_name)
        if isinstance(policy, dict):
            _rewrite_evidence_policy(policy, symbols, rename)


def rewrite_live_activity_references(
    payload: dict[str, Any],
    symbols: _Symbols,
    *,
    rename: _Rename,
) -> None:
    for profile in _dictionary_values(payload.get("activity_profiles")):
        _rewrite_profile(profile, symbols, rename)


__all__ = ["rewrite_live_activity_references"]
