"""Portable pre-mutation checks for plan-owned realization authority."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from .bounded_domains import scalar_in_domain
from .canonical import JsonValue, canonical_json_digest
from .diagnostics import Diagnostic
from .planning import (
    ChangeAction,
    ProvisioningPlan,
    RealizationAuthorityBound,
    RealizationAuthorityMode,
    ResolvedRealizationAuthority,
    planned_realization_authority,
)

_MISSING_REALIZATION_SELECTION = object()


def _planned_pointer_value(value: object, pointer: str) -> object:
    current = value
    for raw_token in pointer.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return _MISSING_REALIZATION_SELECTION
    return current


def _process_resource_limit_identity_digest(value: object) -> str | None:
    """Derive the portable process-limit identity from its projected record."""

    if not isinstance(value, Mapping):
        return None
    resource = value.get("resource", _MISSING_REALIZATION_SELECTION)
    subject = value.get("subject", _MISSING_REALIZATION_SELECTION)
    scope = value.get("scope", _MISSING_REALIZATION_SELECTION)
    if (
        resource is _MISSING_REALIZATION_SELECTION
        or scope is _MISSING_REALIZATION_SELECTION
        or not isinstance(subject, Mapping)
    ):
        return None
    subject_keys = (
        "name",
        "pid",
        "parent_pid",
        "command",
        "command_redacted",
        "role",
        "user",
        "group",
        "working_directory",
    )
    if any(key not in subject for key in subject_keys):
        return None
    try:
        return canonical_json_digest(
            cast(
                JsonValue,
                {
                    "resource": resource,
                    "subject": {key: subject[key] for key in subject_keys},
                    "scope": scope,
                },
            )
        )
    except (TypeError, ValueError):
        return None


def _planned_bound_value(
    selected: object,
    authority: ResolvedRealizationAuthority,
    bound: RealizationAuthorityBound,
) -> object:
    target = selected
    if bound.identity_digest is not None:
        if authority.requirement_kind != "process-resource-limits" or not isinstance(selected, list):
            return _MISSING_REALIZATION_SELECTION
        target = next(
            (item for item in selected if _process_resource_limit_identity_digest(item) == bound.identity_digest),
            _MISSING_REALIZATION_SELECTION,
        )
    return _planned_pointer_value(target, bound.value_pointer)


def planned_realization_selection_diagnostics(plan: ProvisioningPlan) -> list[Diagnostic]:
    """Reject plan values that an adapter may not send to its side-effect driver.

    This is the portable adapter-side complement to registry completeness and
    manifest admission. It deliberately consumes the total authority lookup so
    every concrete value interpreted before mutation is checked against the
    plan-owned closed/constrained boundary.
    """

    operations = {
        operation.address: operation for operation in plan.operations if operation.action is not ChangeAction.DELETE
    }
    for candidate in plan.realization_authority:
        authority = planned_realization_authority(
            plan,
            candidate.address,
            candidate.requirement_kind,
        )
        operation = operations.get(candidate.address)
        if authority is None or operation is None:
            continue
        selected = _planned_pointer_value(operation.payload, authority.payload_pointer)
        if selected is _MISSING_REALIZATION_SELECTION:
            continue
        if authority.mode is RealizationAuthorityMode.CLOSED and selected not in (None, "", [], {}):
            return [_invalid_realization_selection(authority)]
        if authority.mode is not RealizationAuthorityMode.CONSTRAINED:
            continue
        for bound in authority.bounds:
            value = _planned_bound_value(selected, authority, bound)
            if value is _MISSING_REALIZATION_SELECTION or not scalar_in_domain(value, bound.domain):
                return [_invalid_realization_selection(authority)]
    return []


def _invalid_realization_selection(authority: ResolvedRealizationAuthority) -> Diagnostic:
    return Diagnostic(
        code="realization.authority-selection-invalid",
        domain=authority.domain,
        address=authority.address,
        message=(
            "Provisioning adapter cannot materialize a plan value outside resolved "
            f"authority for '{authority.requirement_kind}'."
        ),
    )


__all__ = ["planned_realization_selection_diagnostics"]
