"""Fail-closed provisioning-plan admission for the bounded TechVault appliance.

This module holds the plan/payload admission path — the checks that run against a
:class:`ProvisioningPlan` and its raw operation payloads before snapshot
reconciliation or driver IO. The spec-path and observation gates live in
:mod:`raes_backend_libvirt.techvault_concerns`, whose shared diagnostic
factories and validators this module reuses.
"""

from __future__ import annotations

from collections.abc import Mapping

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.planning import ChangeAction, ProvisioningPlan, ProvisionOp
from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel

from ._payload import (
    ACCOUNT_PLACEMENT_RESOURCE_TYPE,
    CONTENT_PLACEMENT_RESOURCE_TYPE,
    NETWORK_RESOURCE_TYPE,
    NODE_RESOURCE_TYPE,
)
from .realization import (
    _image_ref,
    _infrastructure_spec,
    _memory_mib,
    _node_resources,
    _resource_name,
    _services,
    _vcpus,
)
from .techvault_concerns import (
    _CODE_ACL_UNSUPPORTED,
    _CODE_GUEST_PLACEMENT_UNSUPPORTED,
    _CODE_IMAGE_UNSUPPORTED,
    _CODE_RESOURCE_OUT_OF_ENVELOPE,
    _CODE_SERVICE_UNSUPPORTED,
    _CODE_TRANSACTION_UNSUPPORTED,
    _CODE_UPDATE_UNSUPPORTED,
    _diagnostic,
    _native_name_diagnostics,
    _network_exactness_diagnostic,
    _valid_ipv4_network,
    _within,
)

_GUEST_PLACEMENTS = frozenset(
    {
        ACCOUNT_PLACEMENT_RESOURCE_TYPE,
        CONTENT_PLACEMENT_RESOURCE_TYPE,
        "feature-binding",
    }
)


def techvault_admission_diagnostics(
    plan: ProvisioningPlan,
    envelope: BackendRealizationEnvelopeModel,
    *,
    name_prefix: str,
) -> list[Diagnostic]:
    """Reject every TechVault concern that cannot be applied and observed exactly.

    Direct provisioning-plan submission does not carry compiler-only explicitness
    metadata, so each concrete value is binding at this boundary. Validation is
    intentionally pure and runs before snapshot reconciliation or driver IO.
    """

    diagnostics = _transaction_diagnostics(plan)
    planned_names = _planned_native_names(plan)
    for operation in plan.operations:
        diagnostics.extend(_operation_admission_diagnostics(operation, envelope))
    diagnostics.extend(_native_name_diagnostics(planned_names, name_prefix))
    return diagnostics


def _transaction_diagnostics(plan: ProvisioningPlan) -> list[Diagnostic]:
    mutations = [operation for operation in plan.operations if operation.action is not ChangeAction.UNCHANGED]
    mixes_delete = len(mutations) > 1 and any(operation.action is ChangeAction.DELETE for operation in mutations)
    if not mixes_delete:
        return []
    return [
        _diagnostic(
            _CODE_TRANSACTION_UNSUPPORTED,
            "runtime.libvirt.transaction",
            "TechVault plans cannot combine deletion with another mutation without a verified restore path.",
        )
    ]


def _planned_native_names(plan: ProvisioningPlan) -> list[tuple[str, str]]:
    return [
        (operation.address, _resource_name(operation, operation.payload))
        for operation in plan.operations
        if operation.action is not ChangeAction.DELETE
        and isinstance(operation.payload, Mapping)
        and operation.resource_type in {NETWORK_RESOURCE_TYPE, NODE_RESOURCE_TYPE}
    ]


def _operation_admission_diagnostics(
    operation: ProvisionOp,
    envelope: BackendRealizationEnvelopeModel,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    payload = operation.payload
    if operation.action is ChangeAction.UPDATE:
        diagnostics.append(
            _diagnostic(
                _CODE_UPDATE_UNSUPPORTED,
                operation.address,
                "TechVault appliance updates are not supported without a verified native restore path.",
            )
        )
    elif operation.action not in {ChangeAction.DELETE, ChangeAction.UNCHANGED} and isinstance(payload, Mapping):
        if operation.resource_type in _GUEST_PLACEMENTS:
            diagnostics.append(
                _diagnostic(
                    _CODE_GUEST_PLACEMENT_UNSUPPORTED,
                    operation.address,
                    "TechVault appliance guest placements are unsupported and cannot be silently omitted.",
                )
            )
        elif operation.resource_type == NODE_RESOURCE_TYPE:
            diagnostics.extend(_node_diagnostics(operation.address, payload, envelope))
        elif operation.resource_type == NETWORK_RESOURCE_TYPE:
            diagnostics.extend(_network_diagnostics(operation.address, payload))
    return diagnostics


def _node_diagnostics(
    address: str,
    payload: Mapping[str, object],
    envelope: BackendRealizationEnvelopeModel,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    configuration = envelope.configuration
    resources = _node_resources(payload)
    memory_mib = _memory_mib(resources.get("ram"))
    vcpus = _vcpus(resources.get("cpu"))
    if not _within(memory_mib, configuration.memory_mib.minimum, configuration.memory_mib.maximum) or not _within(
        vcpus, configuration.vcpus.minimum, configuration.vcpus.maximum
    ):
        diagnostics.append(
            _diagnostic(
                _CODE_RESOURCE_OUT_OF_ENVELOPE,
                address,
                "TechVault appliance resource values must be inside the governed envelope and are never clamped.",
            )
        )
    if _image_ref(payload) is not None:
        diagnostics.append(
            _diagnostic(
                _CODE_IMAGE_UNSUPPORTED,
                address,
                "TechVault appliance mode cannot honor a requested image and refuses image substitution.",
            )
        )
    if _services(payload):
        diagnostics.append(
            _diagnostic(
                _CODE_SERVICE_UNSUPPORTED,
                address,
                "TechVault appliance mode does not realize declared guest services.",
            )
        )
    acls = _infrastructure_spec(payload).get("acls")
    if isinstance(acls, list | tuple) and acls:
        diagnostics.append(
            _diagnostic(
                _CODE_ACL_UNSUPPORTED,
                address,
                "TechVault appliance mode does not realize declared network ACLs.",
            )
        )
    return diagnostics


def _network_diagnostics(address: str, payload: Mapping[str, object]) -> list[Diagnostic]:
    properties = _infrastructure_spec(payload).get("properties")
    valid = False
    if isinstance(properties, Mapping):
        valid = isinstance(properties.get("internal"), bool) and _valid_ipv4_network(
            properties.get("cidr"), properties.get("gateway")
        )
    return [] if valid else [_network_exactness_diagnostic(address)]


__all__ = [
    "techvault_admission_diagnostics",
]
