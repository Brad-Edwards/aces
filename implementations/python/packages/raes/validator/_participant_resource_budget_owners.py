"""Semantic validation for authored participant resource-budget owners."""

from collections.abc import Callable, Mapping


def participant_resource_budget_owner_errors(
    behavior_specifications: Mapping[str, object],
    action_contracts: Mapping[str, object],
    deployment_tenants: Mapping[str, object],
    deployment_cells: Mapping[str, object],
    relationships: Mapping[str, object],
    split_node_service_ref: Callable[[str], object | None],
) -> tuple[str, ...]:
    """Return errors for resource owners outside their declared SDL scope."""

    errors: list[str] = []
    for spec_name, behavior_spec in behavior_specifications.items():
        policy = getattr(behavior_spec, "autonomous_execution", None)
        budget = getattr(policy, "resource_budget", None)
        if budget is None:
            continue
        participant_refs = {str(ref).removeprefix("agents.") for ref in getattr(behavior_spec, "participant_refs", ())}
        action_refs = tuple(getattr(policy, "action_order", ())) or tuple(
            getattr(candidate, "action_ref", "") for candidate in getattr(policy, "action_candidates", {}).values()
        )
        action_targets = {
            str(target)
            for action_ref in action_refs
            for effect in getattr(
                action_contracts.get(str(action_ref).removeprefix("action_contracts.")), "effects", ()
            )
            for target in getattr(effect, "target_refs", ())
        }
        target_nodes = {
            str(target).removeprefix("nodes.").split(".services.", 1)[0]
            for target in action_targets
            if str(target).startswith("nodes.")
        }
        target_tenants = {
            str(getattr(cell, "tenant_ref", "")).removeprefix("deployment_tenants.")
            for cell in deployment_cells.values()
            if target_nodes & {str(node_ref).removeprefix("nodes.") for node_ref in getattr(cell, "node_refs", ())}
        }
        declared_tenants = {
            str(owner.ref).removeprefix("deployment_tenants.")
            for owner in budget.owners.values()
            if getattr(owner.kind, "value", owner.kind) == "deployment_tenant"
        }
        shared_permissions = {
            (
                str(getattr(relationship, "source", "")).removeprefix("deployment_tenants."),
                str(getattr(relationship, "target", "")),
            )
            for relationship in relationships.values()
            if getattr(getattr(relationship, "type", ""), "value", getattr(relationship, "type", ""))
            == "uses_shared_service"
        }
        target_tenants.update(tenant for tenant, target in shared_permissions if target in action_targets)
        for owner_id, owner in budget.owners.items():
            kind = getattr(owner.kind, "value", owner.kind)
            ref = str(owner.ref)
            label = f"Behavior specification '{spec_name}' resource-budget owner '{owner_id}'"
            if kind == "participant" and ref.removeprefix("agents.") not in participant_refs:
                errors.append(f"{label} participant ref '{ref}' is outside the policy participant scope")
            elif kind == "deployment_tenant":
                tenant_ref = ref.removeprefix("deployment_tenants.")
                if tenant_ref not in deployment_tenants:
                    errors.append(f"{label} deployment tenant ref '{ref}' is undefined")
                elif tenant_ref not in target_tenants:
                    errors.append(f"{label} deployment tenant ref '{ref}' does not own an authorized action target")
            elif kind == "shared_service":
                if split_node_service_ref(ref) is None:
                    errors.append(f"{label} shared service ref '{ref}' is undefined")
                elif ref not in action_targets:
                    errors.append(f"{label} shared service ref '{ref}' is not an exact execution target")
                elif not any((tenant, ref) in shared_permissions for tenant in declared_tenants):
                    errors.append(
                        f"{label} shared service ref '{ref}' lacks an authorized tenant uses_shared_service edge"
                    )
    return tuple(errors)


__all__ = ["participant_resource_budget_owner_errors"]
