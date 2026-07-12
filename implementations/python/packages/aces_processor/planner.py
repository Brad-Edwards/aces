"""Planner for compiled SDL runtime models."""

from aces_backend_protocols.account_features import provisioner_account_features
from aces_backend_protocols.capabilities import BackendManifest
from aces_sdl.infrastructure import MINIMUM_NODE_COUNT
from aces_sdl.nodes import OSFamily
from aces_sdl.realization_envelope import member
from aces_sdl.value_parsing import extract_variable_name, parse_enum_or_var, parse_int_or_var

from .models import (
    ChangeAction,
    CompiledCapabilityConstraint,
    Diagnostic,
    EvaluationOp,
    EvaluationPlan,
    ExecutionPlan,
    OrchestrationOp,
    OrchestrationPlan,
    PlannedResource,
    ProvisioningPlan,
    ProvisionOp,
    RuntimeDomain,
    RuntimeModel,
    RuntimeSnapshot,
    SnapshotEntry,
    resource_payload,
)
from .semantics.planner import (
    DependencyKind,
    dependency_graph_for_resources,
    reconcile_resource_actions,
    resource_delete_order,
    resource_dependency_cycles,
    resource_topological_order,
)
from .semantics.realization import realization_disclosure, realization_support_diagnostics

__all__ = ["plan", "realization_disclosure", "snapshot_delete_order"]


def _planned_resource(address: str, domain: RuntimeDomain, resource_type: str, resource) -> PlannedResource:
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

    for address, resource in model.networks.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.PROVISIONING,
            "network",
            resource,
        )
    for address, resource in model.node_deployments.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.PROVISIONING,
            "node",
            resource,
        )
    for address, resource in model.feature_bindings.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.PROVISIONING,
            "feature-binding",
            resource,
        )
    for address, resource in model.content_placements.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.PROVISIONING,
            "content-placement",
            resource,
        )
    for address, resource in model.account_placements.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.PROVISIONING,
            "account-placement",
            resource,
        )
    for address, resource in model.inject_bindings.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.ORCHESTRATION,
            "inject-binding",
            resource,
        )
    for address, resource in model.injects.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.ORCHESTRATION,
            "inject",
            resource,
        )
    for address, resource in model.events.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.ORCHESTRATION,
            "event",
            resource,
        )
    for address, resource in model.scripts.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.ORCHESTRATION,
            "script",
            resource,
        )
    for address, resource in model.stories.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.ORCHESTRATION,
            "story",
            resource,
        )
    for address, resource in model.workflows.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.ORCHESTRATION,
            "workflow",
            resource,
        )
    for address, resource in model.condition_bindings.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.EVALUATION,
            "condition-binding",
            resource,
        )
    for address, resource in model.objectives.items():
        resources[address] = _planned_resource(
            address,
            RuntimeDomain.EVALUATION,
            "objective",
            resource,
        )

    return resources


def _ordering_graph(resources: dict[str, PlannedResource]) -> dict[str, tuple[str, ...]]:
    return dependency_graph_for_resources(resources, kind=DependencyKind.ORDERING)


def _ordering_cycles(resources: dict[str, PlannedResource]) -> list[tuple[str, ...]]:
    return resource_dependency_cycles(resources)


def _ordering_cycle_diagnostics(
    resources: dict[str, PlannedResource],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    for domain in RuntimeDomain:
        domain_resources = {address: resource for address, resource in resources.items() if resource.domain == domain}
        for cycle in _ordering_cycles(domain_resources):
            rendered = ", ".join(cycle)
            diagnostics.append(
                Diagnostic(
                    code=f"{domain.value}.ordering-cycle",
                    domain=domain.value,
                    address=cycle[0],
                    message=(
                        f"{domain.value.capitalize()} ordering dependencies "
                        f"must be acyclic; detected cycle: {rendered}."
                    ),
                )
            )

    return diagnostics


def _topological_order(resources: dict[str, PlannedResource]) -> list[str]:
    return resource_topological_order(resources)


def _entry_matches_resource(entry: SnapshotEntry, resource: PlannedResource) -> bool:
    return (
        entry.domain == resource.domain
        and entry.resource_type == resource.resource_type
        and entry.payload == resource.payload
        and entry.ordering_dependencies == resource.ordering_dependencies
        and entry.refresh_dependencies == resource.refresh_dependencies
    )


def _capability_constraint(
    model: RuntimeModel,
    *,
    address: str,
    concern: str,
) -> CompiledCapabilityConstraint | None:
    return next(
        (
            constraint
            for constraint in model.capability_constraints
            if constraint.address == address and constraint.concern == concern
        ),
        None,
    )


def _error_diagnostic(code: str, address: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        domain="provisioning",
        address=address,
        message=message,
    )


def _validate_os_allowed_values(
    variable_name: str,
    allowed_values: tuple[str | int | float | bool, ...],
    *,
    address: str,
) -> tuple[tuple[str, ...] | None, Diagnostic | None]:
    validated_values: list[str] = []
    for raw_value in allowed_values:
        try:
            parsed = parse_enum_or_var(raw_value, OSFamily, field_name="os")
        except ValueError as exc:
            return None, _error_diagnostic(
                "provisioner.os-family-variable-domain-invalid",
                address,
                (f"Variable '{variable_name}' allowed_values contain value {raw_value!r} invalid for nodes.os: {exc}."),
            )
        if extract_variable_name(parsed) is not None:
            return None, _error_diagnostic(
                "provisioner.os-family-variable-domain-invalid",
                address,
                f"Variable '{variable_name}' has a non-concrete nodes.os domain.",
            )
        if isinstance(parsed, OSFamily):
            validated_values.append(parsed.value)
            continue
        return None, _error_diagnostic(
            "provisioner.os-family-variable-domain-invalid",
            address,
            (
                "Variable "
                f"'{variable_name}' allowed_values contain value {raw_value!r} "
                "that could not be validated for nodes.os."
            ),
        )

    return tuple(validated_values), None


def _validate_node_os_family(
    model: RuntimeModel,
    node,
    supported_os_families: frozenset[str],
) -> list[Diagnostic]:
    if not node.os_family:
        return []

    constraint = _capability_constraint(model, address=node.address, concern="nodes.os")
    if constraint is None:
        unresolved = extract_variable_name(node.os_family)
        if unresolved is not None:
            return [
                _error_diagnostic(
                    "provisioner.os-family-variable-ref-unbound",
                    node.address,
                    (
                        "Provisioner capability validation cannot resolve undeclared "
                        f"variable '{unresolved}' referenced by nodes.os."
                    ),
                )
            ]
        if node.os_family in supported_os_families:
            return []
        return [
            Diagnostic(
                code="provisioner.unsupported-os-family",
                domain="provisioning",
                address=node.address,
                message=f"Provisioner does not support OS family '{node.os_family}'.",
            )
        ]
    variable_name = ".".join(constraint.parameter)
    finite_domain, domain_error = _validate_os_allowed_values(
        variable_name,
        constraint.allowed_values,
        address=node.address,
    )
    if domain_error is not None:
        return [domain_error]
    if finite_domain is not None:
        unsupported_values = sorted({value for value in finite_domain if value not in supported_os_families})
        if unsupported_values:
            rendered = ", ".join(repr(value) for value in unsupported_values)
            return [
                Diagnostic(
                    code="provisioner.unsupported-os-family",
                    domain="provisioning",
                    address=node.address,
                    message=(
                        "Provisioner does not support all OS families allowed by "
                        f"variable '{variable_name}': {rendered}."
                    ),
                )
            ]
        return []

    return []


def _validate_count_allowed_values(
    variable_name: str,
    allowed_values: tuple[str | int | float | bool, ...],
    *,
    address: str,
) -> tuple[int | None, Diagnostic | None]:
    validated_values: list[int] = []
    for raw_value in allowed_values:
        try:
            parsed = parse_int_or_var(
                raw_value,
                minimum=MINIMUM_NODE_COUNT,
                field_name="count",
            )
        except ValueError as exc:
            return None, _error_diagnostic(
                "provisioner.count-variable-domain-invalid",
                address,
                (
                    "Variable "
                    f"'{variable_name}' allowed_values contain value {raw_value!r} "
                    f"invalid for infrastructure.count: {exc}."
                ),
            )
        if extract_variable_name(parsed) is not None:
            return None, _error_diagnostic(
                "provisioner.count-variable-domain-invalid",
                address,
                f"Variable '{variable_name}' has a non-concrete infrastructure.count domain.",
            )
        if isinstance(parsed, int):
            validated_values.append(parsed)
            continue
        return None, _error_diagnostic(
            "provisioner.count-variable-domain-invalid",
            address,
            (
                "Variable "
                f"'{variable_name}' allowed_values contain value {raw_value!r} "
                "that could not be validated for infrastructure.count."
            ),
        )

    return max(validated_values), None


def _resource_count_upper_bound(
    model: RuntimeModel,
    resource,
) -> tuple[int | None, Diagnostic | None]:
    count = resource.spec.get("infrastructure", {}).get("count", 1)

    constraint = _capability_constraint(
        model,
        address=resource.address,
        concern="infrastructure.count",
    )
    if constraint is None:
        if isinstance(count, int):
            return count, None
        unresolved = extract_variable_name(count) if isinstance(count, str) else None
        if unresolved is None:
            return None, None
        return None, _error_diagnostic(
            "provisioner.count-variable-ref-unbound",
            resource.address,
            (
                "Provisioner capability validation cannot resolve undeclared "
                f"variable '{unresolved}' referenced by infrastructure.count."
            ),
        )

    variable_name = ".".join(constraint.parameter)
    finite_upper_bound, domain_error = _validate_count_allowed_values(
        variable_name,
        constraint.allowed_values,
        address=resource.address,
    )
    if domain_error is not None:
        return None, domain_error
    if finite_upper_bound is not None:
        return finite_upper_bound, None

    return None, None


def _account_features(account_spec: dict[str, object]) -> set[str]:
    # Delegates to the shared canonical extractor so the planner gate and the
    # libvirt backend's capability-envelope diagnostics never diverge (issue #605).
    return set(provisioner_account_features(account_spec))


def _validate_manifest(model: RuntimeModel, manifest: BackendManifest) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    provisioner = manifest.provisioner

    for network in model.networks.values():
        if "switch" not in provisioner.supported_node_types:
            diagnostics.append(
                Diagnostic(
                    code="provisioner.unsupported-node-type",
                    domain="provisioning",
                    address=network.address,
                    message="Provisioner does not support switch/network nodes.",
                )
            )
        if network.spec.get("infrastructure", {}).get("acls") and not provisioner.supports_acls:
            diagnostics.append(
                Diagnostic(
                    code="provisioner.acls-unsupported",
                    domain="provisioning",
                    address=network.address,
                    message="Provisioner does not support ACL declarations.",
                )
            )

    for node in model.node_deployments.values():
        if node.node_type and node.node_type not in provisioner.supported_node_types:
            diagnostics.append(
                Diagnostic(
                    code="provisioner.unsupported-node-type",
                    domain="provisioning",
                    address=node.address,
                    message=f"Provisioner does not support node type '{node.node_type}'.",
                )
            )
        diagnostics.extend(
            _validate_node_os_family(
                model,
                node,
                provisioner.supported_os_families,
            )
        )

    total_nodes = 0
    if provisioner.max_total_nodes is not None:
        for resource in [*model.networks.values(), *model.node_deployments.values()]:
            count_upper_bound, warning = _resource_count_upper_bound(model, resource)
            if warning is not None:
                diagnostics.append(warning)
            if count_upper_bound is not None:
                total_nodes += count_upper_bound

    if provisioner.max_total_nodes is not None and total_nodes > provisioner.max_total_nodes:
        diagnostics.append(
            Diagnostic(
                code="provisioner.max-total-nodes-exceeded",
                domain="provisioning",
                address="provision",
                message=(
                    f"Scenario requires {total_nodes} deployable nodes/networks, "
                    f"but provisioner maximum is {provisioner.max_total_nodes}."
                ),
            )
        )

    for content in model.content_placements.values():
        content_type = str(content.spec.get("type", ""))
        if content_type and content_type not in provisioner.supported_content_types:
            diagnostics.append(
                Diagnostic(
                    code="provisioner.unsupported-content-type",
                    domain="provisioning",
                    address=content.address,
                    message=f"Provisioner does not support content type '{content_type}'.",
                )
            )

    if model.account_placements and not provisioner.supports_accounts:
        diagnostics.append(
            Diagnostic(
                code="provisioner.accounts-unsupported",
                domain="provisioning",
                address="provision.accounts",
                message="Provisioner does not support accounts.",
            )
        )
    elif provisioner.supports_accounts:
        for account in model.account_placements.values():
            for feature in sorted(_account_features(account.spec)):
                if feature not in provisioner.supported_account_features:
                    diagnostics.append(
                        Diagnostic(
                            code="provisioner.unsupported-account-feature",
                            domain="provisioning",
                            address=account.address,
                            message=f"Provisioner does not support account feature '{feature}'.",
                        )
                    )

    orchestration_sections = {
        "injects": bool(model.injects or model.inject_bindings),
        "events": bool(model.events),
        "scripts": bool(model.scripts),
        "stories": bool(model.stories),
        "workflows": bool(model.workflows),
    }
    if any(orchestration_sections.values()):
        if manifest.orchestrator is None:
            diagnostics.append(
                Diagnostic(
                    code="orchestrator.missing",
                    domain="orchestration",
                    address="orchestration",
                    message="Scenario requires orchestration support, but no orchestrator is configured.",
                )
            )
        else:
            for section, used in orchestration_sections.items():
                if used and section not in manifest.orchestrator.supported_sections:
                    diagnostics.append(
                        Diagnostic(
                            code="orchestrator.unsupported-section",
                            domain="orchestration",
                            address=f"orchestration.{section}",
                            message=f"Orchestrator does not support '{section}'.",
                        )
                    )
            if model.workflows and not manifest.orchestrator.supports_workflows:
                diagnostics.append(
                    Diagnostic(
                        code="orchestrator.workflows-unsupported",
                        domain="orchestration",
                        address="orchestration.workflows",
                        message="Orchestrator does not support workflows.",
                    )
                )
            workflow_features = sorted(
                {feature for workflow in model.workflows.values() for feature in workflow.required_features},
                key=lambda feature: feature.value,
            )
            for feature in workflow_features:
                if feature in manifest.orchestrator.supported_workflow_features:
                    continue
                diagnostics.append(
                    Diagnostic(
                        code="orchestrator.workflow-feature-unsupported",
                        domain="orchestration",
                        address="orchestration.workflows",
                        message=(f"Orchestrator does not support workflow feature '{feature.value}'."),
                    )
                )
            orchestration_uses_condition_refs = any(
                event.condition_addresses for event in model.events.values()
            ) or any(
                addresses
                for workflow in model.workflows.values()
                for addresses in workflow.step_condition_addresses.values()
            )
            if orchestration_uses_condition_refs and not manifest.orchestrator.supports_condition_refs:
                diagnostics.append(
                    Diagnostic(
                        code="orchestrator.condition-refs-unsupported",
                        domain="orchestration",
                        address="orchestration.condition-refs",
                        message=("Orchestrator does not support condition-gated events or workflow predicates."),
                    )
                )
            required_state_predicate_features = sorted(
                {
                    feature
                    for workflow in model.workflows.values()
                    for feature in workflow.required_state_predicate_features
                },
                key=lambda feature: feature.value,
            )
            for feature in required_state_predicate_features:
                if feature in manifest.orchestrator.supported_workflow_state_predicates:
                    continue
                diagnostics.append(
                    Diagnostic(
                        code="orchestrator.step-state-predicate-feature-unsupported",
                        domain="orchestration",
                        address="orchestration.workflows",
                        message=(f"Orchestrator does not support workflow state predicate feature '{feature.value}'."),
                    )
                )
            if model.inject_bindings and not manifest.orchestrator.supports_inject_bindings:
                diagnostics.append(
                    Diagnostic(
                        code="orchestrator.inject-bindings-unsupported",
                        domain="orchestration",
                        address="orchestration.injects",
                        message="Orchestrator does not support node-bound injects.",
                    )
                )

    evaluation_sections = {
        "conditions": bool(model.condition_bindings),
        "objectives": bool(model.objectives),
    }
    if any(evaluation_sections.values()):
        if not manifest.has_evaluator:
            diagnostics.append(
                Diagnostic(
                    code="evaluator.missing",
                    domain="evaluation",
                    address="evaluation",
                    message="Scenario requires evaluation support, but no evaluator is configured.",
                )
            )
        else:
            supported_sections = manifest.evaluator_supported_sections
            for section, used in evaluation_sections.items():
                if used and section not in supported_sections:
                    diagnostics.append(
                        Diagnostic(
                            code="evaluator.unsupported-section",
                            domain="evaluation",
                            address=f"evaluation.{section}",
                            message=f"Evaluator does not support '{section}'.",
                        )
                    )
            if model.objectives and not manifest.supports_objectives:
                diagnostics.append(
                    Diagnostic(
                        code="evaluator.objectives-unsupported",
                        domain="evaluation",
                        address="evaluation.objectives",
                        message="Evaluator does not support objectives.",
                    )
                )

    return diagnostics


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


def _delete_order(entries: dict[str, SnapshotEntry]) -> list[str]:
    resources = {
        address: PlannedResource(
            address=entry.address,
            domain=entry.domain,
            resource_type=entry.resource_type,
            payload=entry.payload,
            ordering_dependencies=entry.ordering_dependencies,
            refresh_dependencies=entry.refresh_dependencies,
        )
        for address, entry in entries.items()
    }
    return resource_delete_order(resources)


def snapshot_delete_order(entries: dict[str, SnapshotEntry]) -> list[str]:
    """Return delete order for existing snapshot entries."""

    return _delete_order(entries)


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


def plan(
    model: RuntimeModel,
    manifest: BackendManifest,
    snapshot: RuntimeSnapshot | None = None,
    *,
    target_name: str | None = None,
) -> ExecutionPlan:
    """Reconcile a compiled runtime model against the current snapshot."""

    snapshot = snapshot or RuntimeSnapshot()
    resources = _collect_resources(model)
    envelope_diagnostics = (
        list(member(model.realization_instance, manifest.realization_envelope.expression).diagnostics)
        if manifest.realization_envelope is not None and model.realization_instance is not None
        else []
    )
    diagnostics = [
        *model.diagnostics,
        *_validate_manifest(model, manifest),
        *realization_support_diagnostics(model.realization_requirements, manifest),
        *envelope_diagnostics,
        *_ordering_cycle_diagnostics(resources),
    ]
    actions, deleted_entries = _build_operations(resources, snapshot)

    provisioning = _build_provisioning_plan(resources, actions, deleted_entries, manifest)
    orchestration = _build_orchestration_plan(resources, actions, deleted_entries)
    evaluation = _build_evaluation_plan(resources, actions, deleted_entries)

    return ExecutionPlan(
        target_name=target_name,
        manifest=manifest,
        base_snapshot=snapshot,
        scenario_name=model.scenario_name,
        model=model,
        provisioning=provisioning,
        orchestration=orchestration,
        evaluation=evaluation,
        diagnostics=diagnostics,
    )
