"""Plan-conformance gate for a provisioning backend's realized snapshot.

The snapshot-contract checks in :mod:`raes_runtime.backend_calls` validate a
returned snapshot against its own shape and the baseline it evolved from; this
module closes the issue-158 falsification matrix by additionally holding the
result to the *submitted plan*. A backend claim is refused when it realizes an
address the plan never authorized, relabels a planned resource's type, files a
planned resource under a different domain, or mutates state it does not
disclose in ``changed_addresses``.
"""

from __future__ import annotations

from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.planning import ChangeAction, ProvisioningPlan, RuntimeDomain
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot

_BACKEND_CONTRACT_INVALID = "runtime.backend-contract-invalid"


def _conformance_diagnostic(address: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=_BACKEND_CONTRACT_INVALID,
        domain="runtime",
        address=address,
        message=message,
        severity=Severity.ERROR,
    )


def _entry_conformance_message(
    entry: object,
    operation: object,
    expected_domain: RuntimeDomain,
) -> str | None:
    if entry.resource_type != operation.resource_type:
        return (
            f"Backend misreported the resource type at '{entry.address}': the plan requires "
            f"'{operation.resource_type}' but the backend claims '{entry.resource_type}'."
        )
    if entry.domain is not expected_domain:
        claimed = getattr(entry.domain, "value", entry.domain)
        return (
            f"Backend filed '{entry.address}' under domain '{claimed}'; the provisioning plan "
            f"authorizes '{expected_domain.value}'."
        )
    return None


def _expected_domain(plan: ProvisioningPlan, address: str) -> RuntimeDomain:
    planned_resource = plan.resources.get(address)
    return planned_resource.domain if planned_resource is not None else RuntimeDomain.PROVISIONING


def plan_conformance_diagnostics(
    result: ApplyResult,
    baseline_snapshot: RuntimeSnapshot,
    plan: ProvisioningPlan,
) -> list[Diagnostic]:
    """Refuse realized entries the submitted provisioning plan never authorized.

    Applies to successful claims only: a failed apply already returns a
    non-authoritative result, and its partial snapshot is preserved for
    forensics rather than being replaced by the baseline.
    """

    if not result.success:
        return []
    operations = {operation.address: operation for operation in plan.operations}
    diagnostics: list[Diagnostic] = []
    disclosed = set(result.changed_addresses)
    for address, entry in result.snapshot.entries.items():
        baseline_entry = baseline_snapshot.entries.get(address)
        operation = operations.get(address)
        changed = baseline_entry is None or entry != baseline_entry
        if operation is None:
            if changed:
                verb = "realized" if baseline_entry is None else "mutated"
                diagnostics.append(
                    _conformance_diagnostic(
                        address,
                        f"Backend {verb} '{address}', an address absent from the provisioning plan.",
                    )
                )
            continue
        if operation.action is ChangeAction.DELETE:
            continue
        message = _entry_conformance_message(entry, operation, _expected_domain(plan, address))
        if message is not None:
            diagnostics.append(_conformance_diagnostic(address, message))
        elif changed and address not in disclosed and operation.action is not ChangeAction.UNCHANGED:
            diagnostics.append(
                _conformance_diagnostic(
                    address,
                    f"Backend changed '{address}' without disclosing it in changed_addresses.",
                )
            )
    return diagnostics
