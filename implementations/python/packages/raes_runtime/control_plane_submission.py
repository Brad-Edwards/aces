"""Submission-admission diagnostics for the runtime control plane.

These helpers screen provisioning, orchestration, and evaluation plans before
``RuntimeControlPlane`` submits them, mirroring the async submission contract in
``control_plane.py``.
"""

from __future__ import annotations

from collections.abc import Mapping

from raes_backend_protocols.account_features import provisioner_account_features
from raes_backend_protocols.backend_manifest import BackendManifest
from raes_backend_protocols.domain_topology import domain_topology_plan_diagnostics
from raes_backend_protocols.service_materialization import service_materialization_plan_diagnostics
from raes_contracts.apparatus import (
    DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND,
    RUNTIME_REALIZATION_DOMAIN,
)
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.planning import (
    ChangeAction,
    EvaluationPlan,
    OrchestrationPlan,
    PlanOperation,
    ProvisioningPlan,
    RuntimeDomain,
    require_plan_operation_identity,
)
from raes_contracts.runtime_state import RuntimeSnapshot
from raes_processor.planner import account_credential_spec_is_valid, generated_artifact_payload_diagnostic

_STATEFUL_ADMISSION_BY_RESOURCE_TYPE = {
    "generated-artifact": (
        "supports_generated_artifacts",
        "provisioner.generated-artifacts-unsupported",
        "generated artifacts",
    ),
    "persistent-volume": (
        "supports_persistent_volumes",
        "provisioner.persistent-volumes-unsupported",
        "persistent volumes",
    ),
}


def _submitted_plan_diagnostics(
    plan: ProvisioningPlan | OrchestrationPlan | EvaluationPlan,
    domain: RuntimeDomain,
    snapshot: RuntimeSnapshot,
    manifest: BackendManifest | None = None,
) -> list[Diagnostic]:
    admitted = set(snapshot.entries) | {operation.address for operation in plan.operations}
    diagnostics: list[Diagnostic] = []
    for operation in plan.operations:
        diagnostic = _submitted_operation_diagnostic(operation, domain, snapshot, admitted)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
            break
    if not diagnostics and domain is RuntimeDomain.PROVISIONING and isinstance(plan, ProvisioningPlan):
        if manifest is None:
            raise ValueError("provisioning submission admission requires a backend manifest")
        account_diagnostic = _account_credential_submission_diagnostic(plan, manifest)
        if account_diagnostic is not None:
            diagnostics.append(account_diagnostic)
        else:
            stateful_diagnostic = _stateful_submission_diagnostic(plan, manifest)
            if stateful_diagnostic is not None:
                diagnostics.append(stateful_diagnostic)
            else:
                service_materialization_diagnostics = service_materialization_plan_diagnostics(
                    plan,
                    manifest.provisioner,
                    manifest.realization_envelope,
                    manifest.realization_support,
                )
                if service_materialization_diagnostics:
                    diagnostics.extend(service_materialization_diagnostics[:1])
                    return diagnostics
                diagnostics.extend(
                    domain_topology_plan_diagnostics(
                        plan,
                        snapshot=snapshot,
                        supported_domain_profiles=manifest.provisioner.supported_domain_profiles,
                    )[:1]
                )
    return diagnostics


def _account_credential_submission_diagnostic(
    plan: ProvisioningPlan,
    manifest: BackendManifest,
) -> Diagnostic | None:
    """Validate credential-bearing direct-plan account payloads before side effects."""

    for operation in plan.operations:
        if operation.action is ChangeAction.DELETE or operation.resource_type != "account-placement":
            continue
        spec = operation.payload.get("spec")
        if not isinstance(spec, Mapping) or not spec.get("credential_bindings"):
            continue
        if not account_credential_spec_is_valid(spec):
            return Diagnostic(
                code="provisioner.account-credential-binding-invalid",
                domain="provisioning",
                address=operation.address,
                message="Account credential binding payload does not satisfy the canonical account contract.",
            )
        account_name = operation.payload.get("account_name") or operation.payload.get("name")
        if not isinstance(account_name, str) or operation.address != f"provision.account.{account_name}":
            return Diagnostic(
                code="provisioner.account-credential-binding-invalid",
                domain="provisioning",
                address=operation.address,
                message="Account credential binding payload does not match its canonical account address.",
            )
        if not manifest.provisioner.supports_accounts:
            return Diagnostic(
                code="provisioner.accounts-unsupported",
                domain="provisioning",
                address=operation.address,
                message="Provisioner does not support accounts.",
            )
        for feature in sorted(provisioner_account_features(spec)):
            if feature not in manifest.provisioner.supported_account_features:
                return Diagnostic(
                    code="provisioner.unsupported-account-feature",
                    domain="provisioning",
                    address=operation.address,
                    message=f"Provisioner does not support account feature '{feature}'.",
                )
    return None


def _stateful_submission_diagnostic(
    plan: ProvisioningPlan,
    manifest: BackendManifest,
) -> Diagnostic | None:
    diagnostic: Diagnostic | None = None
    exact_supported = any(
        declaration.domain == RUNTIME_REALIZATION_DOMAIN
        and DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND in declaration.supported_exact_requirement_kinds
        for declaration in manifest.realization_support
    )
    for operation in plan.operations:
        admission = _STATEFUL_ADMISSION_BY_RESOURCE_TYPE.get(operation.resource_type)
        if admission is None:
            continue
        capability_attribute, unsupported_code, resource_label = admission
        if not getattr(manifest.provisioner, capability_attribute):
            diagnostic = Diagnostic(
                code=unsupported_code,
                domain="provisioning",
                address=operation.address,
                message=f"Provisioner does not support {resource_label}.",
            )
        elif operation.resource_type == "generated-artifact":
            artifact_diagnostic = generated_artifact_payload_diagnostic(
                address=operation.address,
                spec=operation.payload.get("spec"),
                provisioner=manifest.provisioner,
            )
            if artifact_diagnostic is not None:
                diagnostic = artifact_diagnostic
        if diagnostic is None and not exact_supported:
            diagnostic = Diagnostic(
                code="realization.unsupported-exact-requirement",
                domain="runtime-realization",
                address=operation.address,
                message=(
                    "Backend declares no exact realization support for the submitted "
                    f"{operation.resource_type} resource."
                ),
            )
        if diagnostic is not None:
            break
    return diagnostic


def _submitted_operation_diagnostic(
    operation: PlanOperation,
    domain: RuntimeDomain,
    snapshot: RuntimeSnapshot,
    admitted: set[str],
) -> Diagnostic | None:
    diagnostic: Diagnostic | None = None
    address = f"runtime.control-plane.{domain.value}"
    try:
        require_plan_operation_identity(domain, operation.address, operation.resource_type)
    except ValueError:
        diagnostic = Diagnostic(
            code="runtime.plan-resource-incoherent",
            domain="runtime",
            address=address,
            message="Submitted plan operation disagrees with the endpoint resource identity.",
        )

    dependencies = {*operation.ordering_dependencies, *operation.refresh_dependencies}
    if diagnostic is None and dependencies - admitted:
        diagnostic = Diagnostic(
            code="runtime.plan-dependency-unresolved",
            domain="runtime",
            address=address,
            message="Submitted plan contains a dependency outside its operations and admitted snapshot.",
        )

    existing = snapshot.entries.get(operation.address)
    if (
        diagnostic is None
        and existing is not None
        and (existing.domain is not domain or existing.resource_type != operation.resource_type)
    ):
        diagnostic = Diagnostic(
            code="runtime.plan-resource-incoherent",
            domain="runtime",
            address=address,
            message="Submitted plan disagrees with the admitted snapshot resource identity.",
        )
    return diagnostic
