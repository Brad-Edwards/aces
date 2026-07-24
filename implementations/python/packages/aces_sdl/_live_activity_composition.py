"""Composition rewriting for deterministic live-activity references."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def rewrite_live_activity_references(
    payload: dict[str, Any],
    symbols: Mapping[str, Mapping[str, str] | set[str]],
    *,
    rename: Callable[[str, Mapping[str, str]], str],
) -> None:
    def symbol_map(name: str) -> Mapping[str, str]:
        value = symbols[name]
        return value if isinstance(value, Mapping) else {}

    named = symbol_map("named")
    for profile in payload.get("activity_profiles", {}).values():
        if not isinstance(profile, dict):
            continue
        profile["historical_baseline_ref"] = rename(
            profile.get("historical_baseline_ref", ""),
            symbol_map("historical_baselines"),
        )
        for actor in profile.get("actors", {}).values():
            if not isinstance(actor, dict):
                continue
            actor["entity_ref"] = rename(actor.get("entity_ref", ""), symbol_map("entities"))
            actor["account_ref"] = rename(actor.get("account_ref", ""), symbol_map("accounts"))
            actor["deployment_tenant_ref"] = rename(
                actor.get("deployment_tenant_ref", ""),
                symbol_map("deployment_tenants"),
            )
            actor["operating_scope_refs"] = [rename(ref, named) for ref in actor.get("operating_scope_refs", [])]
        for context in profile.get("execution_contexts", {}).values():
            if not isinstance(context, dict):
                continue
            context["deployment_tenant_ref"] = rename(
                context.get("deployment_tenant_ref", ""),
                symbol_map("deployment_tenants"),
            )
            context["account_ref"] = rename(
                context.get("account_ref", ""),
                symbol_map("accounts"),
            )
            context["target_service_ref"] = rename(
                context.get("target_service_ref", ""),
                named,
            )
        for action in profile.get("actions", {}).values():
            if not isinstance(action, dict):
                continue
            action["template_ref"] = rename(
                action.get("template_ref", ""),
                symbol_map("activity_templates"),
            )
            for binding in action.get("parameter_bindings", []):
                if isinstance(binding, dict):
                    binding["value_ref"] = rename(binding.get("value_ref", ""), named)
        for policy_name in ("readback", "telemetry"):
            policy = profile.get(policy_name)
            if not isinstance(policy, dict):
                continue
            policy["observability_refs"] = [rename(ref, named) for ref in policy.get("observability_refs", [])]
            policy["evidence_requirement_refs"] = [
                rename(ref, symbol_map("evidence_requirements")) for ref in policy.get("evidence_requirement_refs", [])
            ]


__all__ = ["rewrite_live_activity_references"]
