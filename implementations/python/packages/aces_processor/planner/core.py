"""Top-level planning pipeline that reconciles a runtime model against a snapshot."""

from dataclasses import replace

from aces_backend_protocols.capabilities import BackendManifest
from aces_backend_protocols.capability_admission import time_model_capability_gaps
from aces_backend_protocols.domain_topology import domain_topology_plan_diagnostics
from aces_contracts.diagnostics import Diagnostic
from aces_sdl.realization_envelope import member

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
