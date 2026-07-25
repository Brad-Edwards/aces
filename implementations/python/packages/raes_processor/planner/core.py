"""Top-level planning pipeline that reconciles a runtime model against a snapshot."""

from dataclasses import replace

from raes_backend_protocols.capabilities import BackendManifest
from raes_backend_protocols.capability_admission import (
    participant_autonomous_execution_capability_gaps,
    time_model_capability_gaps,
)
from raes_backend_protocols.domain_topology import domain_topology_plan_diagnostics
from raes_backend_protocols.service_materialization import service_materialization_plan_diagnostics
from raes_contracts.diagnostics import Diagnostic
from raes.realization_envelope import member

from ..compiler.time_model import time_model_contract_model
from ..models import ExecutionPlan, RuntimeModel, RuntimeSnapshot
from ..semantics.realization import (
    ApparatusRealizationDefaultResolver,
    materialize_realization_requirements,
    realization_envelope_diagnostics,
    realization_support_diagnostics,
)
from .manifest_validation import _validate_manifest
from .operations import (
    _build_evaluation_plan,
    _build_operations,
    _build_orchestration_plan,
    _build_provisioning_plan,
)
from .ordering import _ordering_cycle_diagnostics
from .resources import _collect_resources


def _time_model_diagnostics(model: RuntimeModel, manifest: BackendManifest) -> list[Diagnostic]:
    declaration = time_model_contract_model(model.time_model)
    if declaration is None:
        return []
    return [
        Diagnostic(
            code="time.unsupported-capability",
            domain="time",
            address="time.model",
            message=gap,
        )
        for gap in time_model_capability_gaps(manifest, declaration)
    ]


def _participant_execution_diagnostics(
    model: RuntimeModel,
    manifest: BackendManifest,
) -> list[Diagnostic]:
    specifications = tuple(
        specification
        for specification in model.behavior_specifications.values()
        if specification.autonomous_execution is not None
    )
    policies = tuple(specification.autonomous_execution for specification in specifications)
    diagnostics = [
        Diagnostic(
            code="participant.autonomous-execution-unsupported",
            domain="participant",
            address="participant.autonomous-execution",
            message=gap,
        )
        for gap in participant_autonomous_execution_capability_gaps(manifest, policies, model.time_model)
    ]
    capability = manifest.participant_runtime
    supported_features = (
        capability.supported_behavior_features | capability.supported_interaction_features
        if capability is not None
        else frozenset()
    )
    for specification in specifications:
        for feature in sorted(set(specification.backend_feature_support_refs) - supported_features):
            diagnostics.append(
                Diagnostic(
                    code="participant.autonomous-feature-unsupported",
                    domain="participant",
                    address=specification.address,
                    message=f"Backend does not support required participant feature '{feature}'.",
                )
            )
    return diagnostics


def plan(
    model: RuntimeModel,
    manifest: BackendManifest,
    snapshot: RuntimeSnapshot | None = None,
    *,
    target_name: str | None = None,
    apparatus_realization_default: ApparatusRealizationDefaultResolver | None = None,
) -> ExecutionPlan:
    """Reconcile a compiled runtime model against the current snapshot."""

    snapshot = snapshot or RuntimeSnapshot()
    effective_requirements = materialize_realization_requirements(
        model.realization_requirements,
        manifest,
        apparatus_default=apparatus_realization_default,
    )
    effective_model = replace(model, realization_requirements=effective_requirements)
    resources = _collect_resources(effective_model)
    envelope_diagnostics = (
        list(member(effective_model.realization_instance, manifest.realization_envelope.expression).diagnostics)
        if manifest.realization_envelope is not None and effective_model.realization_instance is not None
        else []
    )
    diagnostics = [
        *effective_model.diagnostics,
        *_validate_manifest(effective_model, manifest),
        *_time_model_diagnostics(effective_model, manifest),
        *_participant_execution_diagnostics(effective_model, manifest),
        *realization_support_diagnostics(
            effective_requirements,
            manifest,
        ),
        *realization_envelope_diagnostics(
            effective_requirements,
            manifest,
        ),
        *envelope_diagnostics,
        *_ordering_cycle_diagnostics(resources),
    ]
    actions, deleted_entries = _build_operations(resources, snapshot)

    provisioning = _build_provisioning_plan(resources, actions, deleted_entries, manifest)
    materialization_diagnostics = service_materialization_plan_diagnostics(
        provisioning,
        manifest.provisioner,
        manifest.realization_envelope,
    )
    diagnostics.extend(materialization_diagnostics)
    provisioning.diagnostics.extend(materialization_diagnostics)
    topology_diagnostics = domain_topology_plan_diagnostics(
        provisioning,
        snapshot=snapshot,
        supported_domain_profiles=manifest.provisioner.supported_domain_profiles,
    )
    diagnostics.extend(topology_diagnostics)
    provisioning.diagnostics.extend(topology_diagnostics)
    orchestration = _build_orchestration_plan(resources, actions, deleted_entries)
    evaluation = _build_evaluation_plan(resources, actions, deleted_entries)

    return ExecutionPlan(
        target_name=target_name,
        manifest=manifest,
        base_snapshot=snapshot,
        scenario_name=model.scenario_name,
        model=effective_model,
        provisioning=provisioning,
        orchestration=orchestration,
        evaluation=evaluation,
        diagnostics=diagnostics,
    )
