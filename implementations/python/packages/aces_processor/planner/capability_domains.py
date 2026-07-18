"""Finite-variable capability-domain validation for provisioner gates."""

from aces_backend_protocols.account_features import provisioner_account_features
from aces_sdl.infrastructure import MINIMUM_NODE_COUNT
from aces_sdl.nodes import OSFamily
from aces_sdl.value_parsing import extract_variable_name, parse_enum_or_var, parse_int_or_var

from ..models import CompiledCapabilityConstraint, Diagnostic, RuntimeModel

_COUNT_DOMAIN_INVALID = "provisioner.count-variable-domain-invalid"
_OS_FAMILY_DOMAIN_INVALID = "provisioner.os-family-variable-domain-invalid"


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
                _OS_FAMILY_DOMAIN_INVALID,
                address,
                (f"Variable '{variable_name}' allowed_values contain value {raw_value!r} invalid for nodes.os: {exc}."),
            )
        if extract_variable_name(parsed) is not None:
            return None, _error_diagnostic(
                _OS_FAMILY_DOMAIN_INVALID,
                address,
                f"Variable '{variable_name}' has a non-concrete nodes.os domain.",
            )
        if isinstance(parsed, OSFamily):
            validated_values.append(parsed.value)
            continue
        return None, _error_diagnostic(
            _OS_FAMILY_DOMAIN_INVALID,
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
                _COUNT_DOMAIN_INVALID,
                address,
                (
                    "Variable "
                    f"'{variable_name}' allowed_values contain value {raw_value!r} "
                    f"invalid for infrastructure.count: {exc}."
                ),
            )
        if extract_variable_name(parsed) is not None:
            return None, _error_diagnostic(
                _COUNT_DOMAIN_INVALID,
                address,
                f"Variable '{variable_name}' has a non-concrete infrastructure.count domain.",
            )
        if isinstance(parsed, int):
            validated_values.append(parsed)
            continue
        return None, _error_diagnostic(
            _COUNT_DOMAIN_INVALID,
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
