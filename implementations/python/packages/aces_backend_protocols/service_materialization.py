"""Shared fail-closed admission for service-owned content placements."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from aces_contracts.addressing import require_compiled_address
from aces_contracts.diagnostics import Diagnostic
from aces_contracts.planning import ChangeAction, ProvisioningPlan
from aces_contracts.realization_envelope import (
    BackendRealizationEnvelopeModel,
    ConcernDisposition,
    ObservationStrength,
    RealizationConcern,
)

from .capabilities import ProvisionerCapabilities

_DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_PROFILE = "service-content"
_VERSION = "1"
_PROFILE_TERM = "service-content-v1"
_REQUIREMENTS = {
    "operation": "ensure-owned-items",
    "conflict_policy": "reject-unowned-collision",
    "readback": "canonical-content-digest",
}
_BINDING_FIELDS = {
    "target_service_address",
    "interface_profile",
    "profile_version",
    "content_type",
    "operation",
    "conflict_policy",
    "readback",
    "canonical_content_digest",
    "shared_service_relationship_ref",
    "consumer_tenant_ref",
    "mutable_state_owner",
    "reset_generation_owner",
    "readback_assertion_addresses",
    "evidence_requirement_refs",
    "observation_boundary_addresses",
}


def service_materialization_plan_diagnostics(
    plan: ProvisioningPlan,
    capabilities: ProvisionerCapabilities,
    envelope: BackendRealizationEnvelopeModel | None,
) -> list[Diagnostic]:
    """Validate exact profile, ownership, target, and readback before backend I/O."""

    diagnostics: list[Diagnostic] = []
    for operation in plan.operations:
        if operation.resource_type != "content-placement" or operation.action is ChangeAction.DELETE:
            continue
        binding = operation.payload.get("service_materialization")
        if binding is None:
            continue
        message = _binding_violation(operation.payload, binding)
        if message is not None:
            diagnostics.append(
                _diagnostic("provisioner.service-materialization-contract-invalid", operation.address, message)
            )
            continue
        if _PROFILE_TERM not in capabilities.supported_service_materialization_profiles:
            diagnostics.append(
                _diagnostic(
                    "provisioner.unsupported-service-materialization-profile",
                    operation.address,
                    f"Provisioner does not support service materialization profile '{_PROFILE_TERM}'.",
                )
            )
            continue
        if not _independent_readback_supported(envelope):
            diagnostics.append(
                _diagnostic(
                    "provisioner.service-materialization-readback-unsupported",
                    operation.address,
                    "Backend realization envelope does not provide independent native readback for service materialization.",
                )
            )
    return diagnostics


def _binding_violation(payload: Mapping[str, object], binding: object) -> str | None:
    if not isinstance(binding, Mapping) or set(binding) != _BINDING_FIELDS:
        return "Service materialization binding is missing required closed contract fields."
    if binding.get("interface_profile") != _PROFILE or binding.get("profile_version") != _VERSION:
        return "Service materialization profile identity is unsupported or incomplete."
    if any(binding.get(field) != expected for field, expected in _REQUIREMENTS.items()):
        return "Service materialization exact operation requirements are unsupported or incomplete."
    content_type = binding.get("content_type")
    spec = payload.get("spec")
    if not isinstance(spec, Mapping) or content_type != spec.get("type"):
        return "Service materialization content type does not match the content placement."
    target_address = payload.get("target_address")
    service_address = binding.get("target_service_address")
    if not _service_belongs_to_target(target_address, service_address):
        return "Service materialization target service does not belong to the content target node."
    digest = binding.get("canonical_content_digest")
    if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
        return "Service materialization canonical content digest is invalid."
    if not _readback_refs_valid(binding):
        return "Service materialization readback assertions, evidence, and observation boundaries are required."
    if not _ownership_valid(binding):
        return "Service materialization shared-state and reset ownership is incomplete or inconsistent."
    return None


def _service_belongs_to_target(target_address: object, service_address: object) -> bool:
    if not isinstance(target_address, str) or not isinstance(service_address, str):
        return False
    try:
        require_compiled_address(target_address)
        require_compiled_address(service_address)
    except ValueError:
        return False
    return service_address.startswith(f"{target_address}.service.")


def _readback_refs_valid(binding: Mapping[str, object]) -> bool:
    checks = (
        ("readback_assertion_addresses", "evaluation.assertion."),
        ("observation_boundary_addresses", "participant.observation-boundary."),
    )
    for field, prefix in checks:
        values = binding.get(field)
        if not _unique_non_empty_sequence(values) or any(not str(value).startswith(prefix) for value in values):
            return False
    return _unique_non_empty_sequence(binding.get("evidence_requirement_refs"))


def _unique_non_empty_sequence(value: object) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        return False
    rendered = [str(item) for item in value]
    return all(item.strip() for item in rendered) and len(rendered) == len(set(rendered))


def _ownership_valid(binding: Mapping[str, object]) -> bool:
    relationship = binding.get("shared_service_relationship_ref")
    if relationship == "":
        return all(
            binding.get(field) == ""
            for field in ("consumer_tenant_ref", "mutable_state_owner", "reset_generation_owner")
        )
    return (
        isinstance(relationship, str)
        and bool(relationship.strip())
        and isinstance(binding.get("consumer_tenant_ref"), str)
        and bool(str(binding.get("consumer_tenant_ref")).strip())
        and binding.get("mutable_state_owner") in {"consumer_tenant", "shared_service"}
        and binding.get("reset_generation_owner") == binding.get("mutable_state_owner")
    )


def _independent_readback_supported(envelope: BackendRealizationEnvelopeModel | None) -> bool:
    if envelope is None:
        return False
    disclosure = next(
        (item for item in envelope.concerns if item.concern is RealizationConcern.CONTENT_PLACEMENT),
        None,
    )
    return (
        disclosure is not None
        and disclosure.disposition is ConcernDisposition.REALIZED
        and disclosure.observation_strength in {ObservationStrength.DAEMON_OBSERVED, ObservationStrength.GUEST_OBSERVED}
    )


def _diagnostic(code: str, address: str, message: str) -> Diagnostic:
    return Diagnostic(code=code, domain="provisioning", address=address, message=message)


__all__ = ["service_materialization_plan_diagnostics"]
