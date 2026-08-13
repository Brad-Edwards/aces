"""Coupled operating-system capability-domain validation."""

from collections.abc import Callable
from dataclasses import dataclass

from raes.nodes import OSFamily
from raes.operating_systems import normalize_os_distribution, normalize_os_version
from raes.value_parsing import extract_variable_name, parse_enum_or_var
from raes_backend_protocols.capabilities import ProvisionerCapabilities

from ..models import CompiledCapabilityConstraint, Diagnostic, NodeRuntime, RuntimeModel

_OS_DISTRIBUTION_DOMAIN_INVALID = "provisioner.os-distribution-variable-domain-invalid"
_OS_VERSION_DOMAIN_INVALID = "provisioner.os-version-variable-domain-invalid"


@dataclass(frozen=True)
class FeasibleOperatingSystemDomains:
    """Coupled apparatus choices remaining after authored-domain intersection."""

    families: tuple[str, ...]
    distributions: tuple[str, ...]
    versions: tuple[str, ...]

    def values_for(self, requirement_kind: str) -> tuple[str, ...]:
        return {
            "os-family": self.families,
            "os-distribution": self.distributions,
            "os-version": self.versions,
        }[requirement_kind]


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
    return Diagnostic(code=code, domain="provisioning", address=address, message=message)


def _family_domain(
    model: RuntimeModel,
    node: NodeRuntime,
) -> tuple[tuple[str, ...] | None, Diagnostic | None]:
    constraint = _capability_constraint(model, address=node.address, concern="nodes.os")
    if constraint is None:
        unresolved = extract_variable_name(node.os_family)
        if unresolved is not None:
            return None, _error_diagnostic(
                "provisioner.os-family-variable-ref-unbound",
                node.address,
                f"Provisioner capability validation cannot resolve undeclared variable '{unresolved}' "
                "referenced by nodes.os.",
            )
        return ((node.os_family,) if node.os_family else None), None

    variable_name = ".".join(constraint.parameter)
    validated: list[str] = []
    for raw_value in constraint.allowed_values:
        try:
            parsed = parse_enum_or_var(raw_value, OSFamily, field_name="os")
        except ValueError as exc:
            message = (
                f"Variable '{variable_name}' allowed_values contain value {raw_value!r} invalid for nodes.os: {exc}."
            )
        else:
            if extract_variable_name(parsed) is not None:
                message = f"Variable '{variable_name}' has a non-concrete nodes.os domain."
            elif isinstance(parsed, OSFamily):
                validated.append(parsed.value)
                continue
            else:
                message = f"Variable '{variable_name}' contains an invalid nodes.os value."
        return None, _error_diagnostic("provisioner.os-family-variable-domain-invalid", node.address, message)
    return tuple(validated), None


def _scalar_domain_or_open(
    model: RuntimeModel,
    node: NodeRuntime,
    *,
    concern: str,
    value: str,
    field_name: str,
    invalid_code: str,
    normalizer: Callable[[object], object],
) -> tuple[tuple[str, ...] | None, Diagnostic | None]:
    if not value and _capability_constraint(model, address=node.address, concern=concern) is None:
        return None, None
    return _validated_scalar_domain(
        model,
        node,
        concern=concern,
        value=value,
        field_name=field_name,
        invalid_code=invalid_code,
        normalizer=normalizer,
    )


def _validated_scalar_domain(
    model: RuntimeModel,
    node: NodeRuntime,
    *,
    concern: str,
    value: str,
    field_name: str,
    invalid_code: str,
    normalizer: Callable[[object], object],
) -> tuple[tuple[str, ...] | None, Diagnostic | None]:
    constraint = _capability_constraint(model, address=node.address, concern=concern)
    variable_name = extract_variable_name(value)
    if constraint is None:
        if variable_name is not None:
            return None, _error_diagnostic(
                f"provisioner.{field_name}-variable-ref-unbound",
                node.address,
                f"Provisioner capability validation cannot resolve undeclared variable '{variable_name}' "
                f"referenced by nodes.{field_name}.",
            )
        raw_values: tuple[object, ...] = (value,)
    else:
        variable_name = ".".join(constraint.parameter)
        raw_values = constraint.allowed_values

    validated: list[str] = []
    for raw_value in raw_values:
        try:
            parsed = normalizer(raw_value)
        except (TypeError, ValueError) as exc:
            return None, _error_diagnostic(
                invalid_code,
                node.address,
                f"Variable '{variable_name or field_name}' allowed_values contain value {raw_value!r} "
                f"invalid for nodes.{field_name}: {exc}.",
            )
        if extract_variable_name(parsed) is not None:
            return None, _error_diagnostic(
                invalid_code,
                node.address,
                f"Variable '{variable_name or field_name}' has a non-concrete nodes.{field_name} domain.",
            )
        token = getattr(parsed, "value", parsed)
        if not isinstance(token, str) or not token:
            return None, _error_diagnostic(
                invalid_code,
                node.address,
                f"Variable '{variable_name or field_name}' contains an invalid nodes.{field_name} value.",
            )
        validated.append(token)
    return tuple(validated), None


def feasible_operating_system_domains(
    model: RuntimeModel,
    node: NodeRuntime,
    provisioner: ProvisionerCapabilities,
) -> tuple[FeasibleOperatingSystemDomains | None, Diagnostic | None]:
    """Intersect exact, constrained, and open OS intent with coupled rows."""

    os_requirements = {
        requirement.requirement_kind
        for requirement in model.realization_requirements
        if requirement.address == node.address
        and requirement.requirement_kind in {"os-family", "os-distribution", "os-version"}
    }
    if not os_requirements:
        return None, None
    family_domain, family_error = _family_domain(model, node)
    if family_error is not None:
        return None, family_error
    distribution_domain, distribution_error = _scalar_domain_or_open(
        model,
        node,
        concern="nodes.os_distribution",
        value=node.os_distribution,
        field_name="os_distribution",
        invalid_code=_OS_DISTRIBUTION_DOMAIN_INVALID,
        normalizer=normalize_os_distribution,
    )
    if distribution_error is not None:
        return None, distribution_error
    version_domain, version_error = _scalar_domain_or_open(
        model,
        node,
        concern="nodes.os_version",
        value=node.os_version,
        field_name="os_version",
        invalid_code=_OS_VERSION_DOMAIN_INVALID,
        normalizer=normalize_os_version,
    )
    if version_error is not None:
        return None, version_error

    feasible = {
        (row.family, row.distribution, version)
        for row in provisioner.operating_systems
        if family_domain is None or row.family in family_domain
        if distribution_domain is None or row.distribution in distribution_domain
        for version in row.versions
        if version_domain is None or version in version_domain
    }
    if not feasible:
        return None, _error_diagnostic(
            "provisioner.unsupported-operating-system",
            node.address,
            "Provisioner has no coupled operating-system compatibility row intersecting the authored "
            "exact, constrained, and open OS domains.",
        )
    return (
        FeasibleOperatingSystemDomains(
            families=tuple(sorted({family for family, _, _ in feasible})),
            distributions=tuple(sorted({distribution for _, distribution, _ in feasible})),
            versions=tuple(sorted({version for _, _, version in feasible})),
        ),
        None,
    )


def validate_node_operating_system(
    model: RuntimeModel,
    node: NodeRuntime,
    provisioner: ProvisionerCapabilities,
) -> list[Diagnostic]:
    """Reject only an empty intersection with the coupled capability rows."""

    _, diagnostic = feasible_operating_system_domains(model, node, provisioner)
    return [diagnostic] if diagnostic is not None else []
