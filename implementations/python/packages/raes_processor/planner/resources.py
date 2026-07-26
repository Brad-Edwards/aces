"""Resource collection from a compiled runtime model."""

from ..models import PlannedResource, ResolvedResource, RuntimeDomain, RuntimeModel, resource_payload


def _planned_resource(
    address: str, domain: RuntimeDomain, resource_type: str, resource: ResolvedResource
) -> PlannedResource:
    return PlannedResource(
        address=address,
        domain=domain,
        resource_type=resource_type,
        payload=resource_payload(resource),
        ordering_dependencies=resource.ordering_dependencies,
        refresh_dependencies=resource.refresh_dependencies,
    )


def _collect_resources(model: RuntimeModel) -> dict[str, PlannedResource]:
    resources: dict[str, PlannedResource] = {}

    resource_groups = (
        (model.networks, RuntimeDomain.PROVISIONING, "network"),
        (model.node_deployments, RuntimeDomain.PROVISIONING, "node"),
        (model.feature_bindings, RuntimeDomain.PROVISIONING, "feature-binding"),
        (model.content_placements, RuntimeDomain.PROVISIONING, "content-placement"),
        (
            model.domain_controller_placements,
            RuntimeDomain.PROVISIONING,
            "domain-controller-placement",
        ),
        (model.account_placements, RuntimeDomain.PROVISIONING, "account-placement"),
        (model.generated_artifacts, RuntimeDomain.PROVISIONING, "generated-artifact"),
        (model.persistent_volumes, RuntimeDomain.PROVISIONING, "persistent-volume"),
        (model.inject_bindings, RuntimeDomain.ORCHESTRATION, "inject-binding"),
        (model.injects, RuntimeDomain.ORCHESTRATION, "inject"),
        (model.events, RuntimeDomain.ORCHESTRATION, "event"),
        (model.scripts, RuntimeDomain.ORCHESTRATION, "script"),
        (model.stories, RuntimeDomain.ORCHESTRATION, "story"),
        (model.workflows, RuntimeDomain.ORCHESTRATION, "workflow"),
        (model.condition_bindings, RuntimeDomain.EVALUATION, "condition-binding"),
        (model.propositions, RuntimeDomain.EVALUATION, "proposition"),
        (model.assertions, RuntimeDomain.EVALUATION, "assertion"),
        (model.objectives, RuntimeDomain.EVALUATION, "objective"),
    )
    for group, domain, resource_type in resource_groups:
        for address, resource in group.items():
            resources[address] = _planned_resource(address, domain, resource_type, resource)

    return resources
