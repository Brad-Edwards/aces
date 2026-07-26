"""Fail-closed translation of governed node ACLs into host-enforced nwfilter rules.

A node's ``acls`` are network firewall rules (direction, source/destination
network, protocol, ports, allow/deny). This module turns each governed rule into a
portable :class:`~raes_backend_libvirt.driver.NetworkAcl` that the driver renders
as a libvirt ``nwfilter`` referenced from the domain interface.

Translation is **fail-closed**: every field is resolved exactly, and any rule that
cannot be — an unknown action/protocol/direction, an invalid port, or a
*specified* ``from_net``/``to_net`` that does not resolve to a concrete CIDR — is
rejected with an ERROR diagnostic rather than widened into a broader allow than the
plan expressed. An *omitted* endpoint or protocol is the plan's own "any" and is
preserved as such.
"""

from __future__ import annotations

from collections.abc import Mapping

from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.planning import PlannedResource

from .driver import NetworkAcl

_DOMAIN = "runtime"

_ACL_ACTIONS = {"allow": "accept", "accept": "accept", "deny": "drop", "drop": "drop"}
_ACL_WILDCARD_PROTOCOLS = frozenset({"", "all", "any"})
_ACL_DIRECTIONS = frozenset({"in", "out", "inout"})


class _AclRejected(Exception):
    """An ACL entry could not be translated into a fail-closed nwfilter rule."""


def realize_node_acls(
    resource: PlannedResource, raw_acls: object, cidr_lookup: dict[str, str]
) -> tuple[tuple[NetworkAcl, ...], list[Diagnostic]]:
    """Translate a node's raw ``acls`` into nwfilter rules + reject diagnostics."""

    if not isinstance(raw_acls, list | tuple):
        return (), []
    acls: list[NetworkAcl] = []
    diagnostics: list[Diagnostic] = []
    for index, raw in enumerate(raw_acls):
        try:
            acls.append(_network_acl(raw, index, cidr_lookup))
        except _AclRejected as rejection:
            # Fail closed: a rule we cannot translate exactly must NOT be widened
            # into a broad allow. Emit an ERROR so apply fails instead.
            diagnostics.append(_invalid_acl(resource, index, str(rejection)))
    return tuple(acls), diagnostics


def _network_acl(raw: object, index: int, cidr_lookup: dict[str, str]) -> NetworkAcl:
    if not isinstance(raw, Mapping):
        raise _AclRejected("entry is not a mapping")
    name = _as_str(raw.get("name")) or f"acl-{index}"
    protocol = _acl_protocol(raw)
    ports = _acl_ports(raw)
    if ports and protocol == "all":
        # A port scope is only meaningful for tcp/udp. Emitting an all-protocol
        # rule while silently dropping the ports would widen an allow-for-port
        # into allow-everything, so reject rather than fail open.
        raise _AclRejected("ports require protocol 'tcp' or 'udp'")
    return NetworkAcl(
        name=name,
        action=_acl_action(raw),
        direction=_acl_direction(raw),
        protocol=protocol,
        src_cidr=_acl_endpoint(raw, "from_net", cidr_lookup),
        dst_cidr=_acl_endpoint(raw, "to_net", cidr_lookup),
        ports=ports,
    )


def _acl_action(raw: Mapping[str, object]) -> str:
    token = _as_str(raw.get("action")).lower()
    if not token:
        raise _AclRejected("missing 'action'")
    if token not in _ACL_ACTIONS:
        raise _AclRejected(f"unknown action '{token}'")
    return _ACL_ACTIONS[token]


def _acl_protocol(raw: Mapping[str, object]) -> str:
    token = _as_str(raw.get("protocol")).lower()
    if token in {"tcp", "udp"}:
        return token
    if token in _ACL_WILDCARD_PROTOCOLS:
        return "all"
    raise _AclRejected(f"unknown protocol '{token}'")


def _acl_direction(raw: Mapping[str, object]) -> str:
    token = _as_str(raw.get("direction")).lower()
    if not token:
        return "inout"
    if token not in _ACL_DIRECTIONS:
        raise _AclRejected(f"unknown direction '{token}'")
    return token


def _acl_ports(raw: Mapping[str, object]) -> tuple[int, ...]:
    raw_ports = raw.get("ports", ())
    if not isinstance(raw_ports, list | tuple):
        raise _AclRejected("'ports' is not a list")
    ports: list[int] = []
    for port in raw_ports:
        # bool is an int subclass; reject it explicitly so True/False are not ports.
        if not isinstance(port, int) or isinstance(port, bool) or not 0 < port <= 65535:
            raise _AclRejected(f"invalid port {port!r}")
        ports.append(port)
    return tuple(ports)


def _acl_endpoint(raw: Mapping[str, object], key: str, cidr_lookup: dict[str, str]) -> str | None:
    ref = _as_str(raw.get(key))
    if not ref:
        # An omitted endpoint is the plan's own "any"; preserve it.
        return None
    cidr = cidr_lookup.get(ref)
    if cidr is None:
        raise _AclRejected(f"'{key}' references network '{ref}' with no resolvable CIDR")
    return cidr


def _invalid_acl(resource: PlannedResource, index: int, reason: str) -> Diagnostic:
    return Diagnostic(
        code="libvirt-backend.realization.invalid-acl",
        domain=_DOMAIN,
        address=resource.address,
        message=(
            f"Libvirt backend refuses to realize ACL #{index} on node '{resource.address}' "
            f"because it would not translate fail-closed: {reason}."
        ),
        severity=Severity.ERROR,
    )


def _as_str(value: object) -> str:
    return value if isinstance(value, str) else ""
