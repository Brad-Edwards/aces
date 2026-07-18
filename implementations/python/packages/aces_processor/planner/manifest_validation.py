"""Backend-manifest capability validation for compiled runtime models."""

from aces_backend_protocols.capabilities import BackendManifest

from ..models import Diagnostic, RuntimeModel
from .capability_domains import _account_features, _resource_count_upper_bound, _validate_node_os_family


def _validate_manifest(model: RuntimeModel, manifest: BackendManifest) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    provisioner = manifest.provisioner

    for resource in [*model.networks.values(), *model.node_deployments.values()]:
        if resource.spec.get("infrastructure", {}).get("acls") and not provisioner.supports_acls:
            diagnostics.append(
                Diagnostic(
                    code="provisioner.acls-unsupported",
                    domain="provisioning",
                    address=resource.address,
                    message="Provisioner does not support ACL declarations.",
                )
            )

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

    if model.generated_artifacts and not provisioner.supports_generated_artifacts:
        diagnostics.append(
            Diagnostic(
                code="provisioner.generated-artifacts-unsupported",
                domain="provisioning",
                address="provision.generated-artifacts",
                message="Provisioner does not support generated artifacts.",
            )
        )
    if model.persistent_volumes and not provisioner.supports_persistent_volumes:
        diagnostics.append(
            Diagnostic(
                code="provisioner.persistent-volumes-unsupported",
                domain="provisioning",
                address="provision.persistent-volumes",
                message="Provisioner does not support persistent volumes.",
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
            orchestration_uses_assertion_refs = any(
                event.assertion_addresses for event in model.events.values()
            ) or any(
                addresses
                for workflow in model.workflows.values()
                for addresses in workflow.step_assertion_addresses.values()
            )
            if orchestration_uses_assertion_refs and not manifest.orchestrator.supports_assertion_refs:
                diagnostics.append(
                    Diagnostic(
                        code="orchestrator.assertion-refs-unsupported",
                        domain="orchestration",
                        address="orchestration.assertion-refs",
                        message=("Orchestrator does not support assertion-gated events or workflow predicates."),
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
        "propositions": bool(model.propositions),
        "assertions": bool(model.assertions),
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
