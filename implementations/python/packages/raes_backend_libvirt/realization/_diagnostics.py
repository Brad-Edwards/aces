"""Ordered diagnostics for libvirt plan realization."""

from __future__ import annotations

from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.planning import PlannedResource

_DOMAIN = "runtime"
_NETWORK_NAMESPACE_UNSUPPORTED = "libvirt-backend.network-namespace-unsupported"


def _unsupported_resource(resource: PlannedResource) -> Diagnostic:
    return Diagnostic(
        code="libvirt-backend.realization.unsupported-resource",
        domain=_DOMAIN,
        address=resource.address,
        message=(
            "Libvirt backend does not realize provisioning resource type "
            f"'{resource.resource_type}' for '{resource.address}'."
        ),
        severity=Severity.ERROR,
    )


def _network_namespace_unsupported(address: str) -> Diagnostic:
    return Diagnostic(
        code=_NETWORK_NAMESPACE_UNSUPPORTED,
        domain=_DOMAIN,
        address=address,
        message=(f"Libvirt backend cannot realize exact container network namespace sharing for '{address}'."),
        severity=Severity.ERROR,
    )


def _unbound_placement(resource: PlannedResource, target: str | None) -> Diagnostic:
    detail = (
        "carries no resolvable target node reference"
        if target is None
        else f"names target node '{target}', which is not present in this plan"
    )
    return Diagnostic(
        code="libvirt-backend.realization.unbound-placement",
        domain=_DOMAIN,
        address=resource.address,
        message=(
            f"Libvirt backend cannot realize placement '{resource.address}' of type "
            f"'{resource.resource_type}': it {detail}."
        ),
        severity=Severity.ERROR,
    )


def _invalid_payload(resource: PlannedResource) -> Diagnostic:
    return Diagnostic(
        code="libvirt-backend.realization.invalid-payload",
        domain=_DOMAIN,
        address=resource.address,
        message=(
            f"Libvirt backend expected provisioning resource '{resource.address}' "
            f"of type '{resource.resource_type}' to carry a mapping payload."
        ),
        severity=Severity.ERROR,
    )
