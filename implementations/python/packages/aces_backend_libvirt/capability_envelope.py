"""Typed capability-envelope diagnostics for the libvirt backend (issue #605).

A provisioning plan may ask the backend to realize a node type, OS family,
content type, or account feature outside the selected manifest's declared
:class:`ProvisionerCapabilities` envelope (an ungoverned/extension term the
backend does not realize). This module surfaces those as blocking, typed
``Diagnostic`` values so the backend fails closed instead of silently or
partially realizing them — the backend-side sibling of the processor's
``planner._validate_manifest`` concrete-capability checks.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass

from aces_backend_protocols.account_features import provisioner_account_features
from aces_backend_protocols.capabilities import ProvisionerCapabilities
from aces_backend_protocols.domain_topology import domain_topology_profile
from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import ChangeAction, ProvisioningPlan, RuntimeDomain

from ._payload import (
    ACCOUNT_PLACEMENT_RESOURCE_TYPE,
    CONTENT_PLACEMENT_RESOURCE_TYPE,
    NETWORK_RESOURCE_TYPE,
    NODE_RESOURCE_TYPE,
    _node_type,
    _os_family,
    _spec,
    _str,
)

_DOMAIN = "runtime"

# A network resource is realized as a libvirt switch, so its node-type envelope
# term is fixed.
_SWITCH_NODE_TYPE = "switch"

_CODE_UNSUPPORTED_NODE_TYPE = "libvirt-backend.realization.unsupported-node-type"
_CODE_UNSUPPORTED_OS_FAMILY = "libvirt-backend.realization.unsupported-os-family"
_CODE_UNSUPPORTED_CONTENT_TYPE = "libvirt-backend.realization.unsupported-content-type"
_CODE_UNSUPPORTED_ACCOUNT_FEATURE = "libvirt-backend.realization.unsupported-account-feature"
_CODE_UNSUPPORTED_DOMAIN_PROFILE = "libvirt-backend.realization.unsupported-domain-profile"


@dataclass(frozen=True)
class _EnvelopeDimension:
    """One capability dimension checked against the manifest envelope.

    ``extract`` yields the concrete term(s) a payload declares for this dimension
    (empty terms are ignored); ``supported`` selects the manifest's declared set
    for the dimension. Adding a future dimension is one row here, not a new
    allowlist scattered across the interpreter and provisioner.
    """

    resource_types: frozenset[str]
    code: str
    noun: str
    extract: Callable[[Mapping[str, object]], tuple[str, ...]]
    supported: Callable[[ProvisionerCapabilities], frozenset[str]]


_ENVELOPE_DIMENSIONS: tuple[_EnvelopeDimension, ...] = (
    _EnvelopeDimension(
        resource_types=frozenset({NODE_RESOURCE_TYPE}),
        code=_CODE_UNSUPPORTED_NODE_TYPE,
        noun="node type",
        extract=lambda payload: (_node_type(payload),),
        supported=lambda caps: caps.supported_node_types,
    ),
    _EnvelopeDimension(
        resource_types=frozenset({NODE_RESOURCE_TYPE}),
        code=_CODE_UNSUPPORTED_OS_FAMILY,
        noun="OS family",
        extract=lambda payload: (_os_family(payload),),
        supported=lambda caps: caps.supported_os_families,
    ),
    _EnvelopeDimension(
        resource_types=frozenset({NETWORK_RESOURCE_TYPE}),
        code=_CODE_UNSUPPORTED_NODE_TYPE,
        noun="node type",
        extract=lambda payload: (_SWITCH_NODE_TYPE,),
        supported=lambda caps: caps.supported_node_types,
    ),
    _EnvelopeDimension(
        resource_types=frozenset({CONTENT_PLACEMENT_RESOURCE_TYPE}),
        code=_CODE_UNSUPPORTED_CONTENT_TYPE,
        noun="content type",
        extract=lambda payload: (_str(_spec(payload).get("type")),),
        supported=lambda caps: caps.supported_content_types,
    ),
    _EnvelopeDimension(
        resource_types=frozenset({ACCOUNT_PLACEMENT_RESOURCE_TYPE}),
        code=_CODE_UNSUPPORTED_ACCOUNT_FEATURE,
        noun="account feature",
        extract=lambda payload: tuple(sorted(provisioner_account_features(_spec(payload)))),
        supported=lambda caps: caps.supported_account_features,
    ),
    _EnvelopeDimension(
        resource_types=frozenset({NODE_RESOURCE_TYPE, ACCOUNT_PLACEMENT_RESOURCE_TYPE}),
        code=_CODE_UNSUPPORTED_DOMAIN_PROFILE,
        noun="identity-domain profile",
        extract=lambda payload: _requested_domain_profiles(payload),
        supported=lambda caps: caps.supported_domain_profiles,
    ),
)


def _requested_domain_profiles(payload: Mapping[str, object]) -> tuple[str, ...]:
    profile = domain_topology_profile(payload)
    return (profile,) if profile else ()


def capability_envelope_diagnostics(
    plan: ProvisioningPlan,
    capabilities: ProvisionerCapabilities,
) -> list[Diagnostic]:
    """Blocking diagnostics for plan terms outside the backend capability envelope.

    Covers the full materialization surface — plan resources *and* non-DELETE
    operations, since either can persist a snapshot entry or request driver work
    from a divergent payload — deduplicated by ``(code, address, term)`` so a
    resource and its matching operation do not double-report the same term. A
    DELETE never realizes a term, so its payload is not gated.
    """

    deduped: dict[tuple[str, str, str], Diagnostic] = {}
    for address, resource_type, payload in _materialized_payloads(plan):
        for key, diagnostic in _out_of_envelope_terms(address, resource_type, payload, capabilities):
            deduped.setdefault(key, diagnostic)
    return list(deduped.values())


def _out_of_envelope_terms(
    address: str,
    resource_type: str,
    payload: Mapping[str, object],
    capabilities: ProvisionerCapabilities,
) -> Iterator[tuple[tuple[str, str, str], Diagnostic]]:
    """Yield ``((code, address, term), diagnostic)`` for each unsupported term of a payload."""

    for dimension in _ENVELOPE_DIMENSIONS:
        if resource_type not in dimension.resource_types:
            continue
        supported = dimension.supported(capabilities)
        for term in dimension.extract(payload):
            if term and term not in supported:
                yield (dimension.code, address, term), _envelope_diagnostic(dimension, address, term)


def _materialized_payloads(plan: ProvisioningPlan) -> Iterator[tuple[str, str, Mapping[str, object]]]:
    """Yield ``(address, resource_type, payload)`` for every gated provisioning surface."""

    for resource in plan.resources.values():
        if resource.domain != RuntimeDomain.PROVISIONING:
            continue
        if isinstance(resource.payload, Mapping):
            yield resource.address, resource.resource_type, resource.payload
    for op in plan.operations:
        if op.action is ChangeAction.DELETE:
            continue
        if isinstance(op.payload, Mapping):
            yield op.address, op.resource_type, op.payload


def _envelope_diagnostic(dimension: _EnvelopeDimension, address: str, term: str) -> Diagnostic:
    return Diagnostic(
        code=dimension.code,
        domain=_DOMAIN,
        address=address,
        message=(
            f"Libvirt backend does not realize {dimension.noun} '{term}' for '{address}': "
            "it is outside the declared manifest capability envelope."
        ),
        severity=Severity.ERROR,
    )
