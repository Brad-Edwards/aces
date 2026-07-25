"""Domain plan construction from reconciled resources and actions."""

from raes_backend_protocols.capabilities import BackendManifest

from ..models import (
    ChangeAction,
    EvaluationOp,
    EvaluationPlan,
    OrchestrationOp,
    OrchestrationPlan,
    PlannedResource,
    ProvisioningPlan,
    ProvisionOp,
    RuntimeDomain,
    RuntimeSnapshot,
    SnapshotEntry,
)
from ..semantics.planner import reconcile_resource_actions
from .ordering import _delete_order, _entry_matches_resource, _topological_order


def _build_operations(
    resources: dict[str, PlannedResource],
    snapshot: RuntimeSnapshot,
) -> tuple[dict[str, ChangeAction], dict[str, SnapshotEntry]]:
    semantic_actions, deleted_entries = reconcile_resource_actions(
        resources,
        snapshot.entries,
        resource_dependencies=lambda resource: resource,
        matches=_entry_matches_resource,
    )
    actions = {address: ChangeAction(action.value) for address, action in semantic_actions.items()}
    return actions, deleted_entries


def _build_provisioning_plan(
    resources: dict[str, PlannedResource],
    actions: dict[str, ChangeAction],
    deleted_entries: dict[str, SnapshotEntry],
    manifest: BackendManifest,
) -> ProvisioningPlan:
    provisioning_resources = {
        address: resource for address, resource in resources.items() if resource.domain == RuntimeDomain.PROVISIONING
    }
    ops: list[ProvisionOp] = []
    for address in _topological_order(provisioning_resources):
        resource = provisioning_resources[address]
        ops.append(
            ProvisionOp(
                action=actions[address],
                address=address,
                resource_type=resource.resource_type,
                payload=resource.payload,
                ordering_dependencies=resource.ordering_dependencies,
                refresh_dependencies=resource.refresh_dependencies,
            )
        )
    for address in _delete_order(
        {address: entry for address, entry in deleted_entries.items() if entry.domain == RuntimeDomain.PROVISIONING}
    ):
        entry = deleted_entries[address]
        ops.append(
            ProvisionOp(
                action=ChangeAction.DELETE,
                address=address,
                resource_type=entry.resource_type,
                payload=entry.payload,
                ordering_dependencies=entry.ordering_dependencies,
                refresh_dependencies=entry.refresh_dependencies,
            )
        )
    return ProvisioningPlan(
        resources=provisioning_resources,
        operations=ops,
        realization_envelope=(
            manifest.realization_envelope.identity if manifest.realization_envelope is not None else None
        ),
    )


def _build_orchestration_plan(
    resources: dict[str, PlannedResource],
    actions: dict[str, ChangeAction],
    deleted_entries: dict[str, SnapshotEntry],
) -> OrchestrationPlan:
    orchestration_resources = {
        address: resource for address, resource in resources.items() if resource.domain == RuntimeDomain.ORCHESTRATION
    }
    startup_order = _topological_order(orchestration_resources)
    ops: list[OrchestrationOp] = []
    for address in startup_order:
        resource = orchestration_resources[address]
        ops.append(
            OrchestrationOp(
                action=actions[address],
                address=address,
                resource_type=resource.resource_type,
                payload=resource.payload,
                ordering_dependencies=resource.ordering_dependencies,
                refresh_dependencies=resource.refresh_dependencies,
            )
        )
    for address in _delete_order(
        {address: entry for address, entry in deleted_entries.items() if entry.domain == RuntimeDomain.ORCHESTRATION}
    ):
        entry = deleted_entries[address]
        ops.append(
            OrchestrationOp(
                action=ChangeAction.DELETE,
                address=address,
                resource_type=entry.resource_type,
                payload=entry.payload,
                ordering_dependencies=entry.ordering_dependencies,
                refresh_dependencies=entry.refresh_dependencies,
            )
        )
    return OrchestrationPlan(
        resources=orchestration_resources,
        operations=ops,
        startup_order=startup_order,
    )


def _build_evaluation_plan(
    resources: dict[str, PlannedResource],
    actions: dict[str, ChangeAction],
    deleted_entries: dict[str, SnapshotEntry],
) -> EvaluationPlan:
    evaluation_resources = {
        address: resource for address, resource in resources.items() if resource.domain == RuntimeDomain.EVALUATION
    }
    startup_order = _topological_order(evaluation_resources)
    ops: list[EvaluationOp] = []
    for address in startup_order:
        resource = evaluation_resources[address]
        ops.append(
            EvaluationOp(
                action=actions[address],
                address=address,
                resource_type=resource.resource_type,
                payload=resource.payload,
                ordering_dependencies=resource.ordering_dependencies,
                refresh_dependencies=resource.refresh_dependencies,
            )
        )
    for address in _delete_order(
        {address: entry for address, entry in deleted_entries.items() if entry.domain == RuntimeDomain.EVALUATION}
    ):
        entry = deleted_entries[address]
        ops.append(
            EvaluationOp(
                action=ChangeAction.DELETE,
                address=address,
                resource_type=entry.resource_type,
                payload=entry.payload,
                ordering_dependencies=entry.ordering_dependencies,
                refresh_dependencies=entry.refresh_dependencies,
            )
        )
    return EvaluationPlan(
        resources=evaluation_resources,
        operations=ops,
        startup_order=startup_order,
    )
