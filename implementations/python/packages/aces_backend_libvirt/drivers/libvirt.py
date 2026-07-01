"""Lazy libvirt connection adapter for the libvirt/QEMU backend."""

from __future__ import annotations

import contextlib
import importlib
import ipaddress
import os
import re
import shutil
import tempfile
import uuid
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, cast

from aces_contracts.diagnostics import Diagnostic, Severity

from aces_backend_libvirt.driver import (
    DomainHandle,
    DomainSpec,
    DriverResult,
    NetworkAcl,
    NetworkHandle,
    NetworkSpec,
)

from .seed import _SEED_DIR_MODE, GenisoimageSeedBuilder, SeedBuilder, write_seed_files

_DOMAIN = "runtime"
_CODE_OPERATION_FAILED = "libvirt-backend.driver.operation-failed"
_CODE_UNAVAILABLE = "libvirt-backend.driver.unavailable"
_CODE_OWNERSHIP_CONFLICT = "libvirt-backend.driver.ownership-conflict"
_DEFAULT_CONNECTION_URI = "qemu:///system"
_WORKSPACE_PREFIX = "aces-libvirt-"
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
# Fixed namespace for deriving a per-address libvirt UUID. The UUID proves an
# existing host object was realized by ACES for *this* address, so convergence
# never destroys a foreign or another-address object that merely shares a name.
_ACES_UUID_NAMESPACE = uuid.UUID("ace50000-0000-5000-8000-000000000001")


class _OwnershipConflict(Exception):
    """An existing host object at this name is not the ACES object for this address."""


def _aces_uuid(address: str) -> str:
    return str(uuid.uuid5(_ACES_UUID_NAMESPACE, address))


def _filter_owner_uuid(address: str) -> str:
    """Owner UUID for a domain's nwfilter (namespaced so it never equals the domain UUID)."""

    return str(uuid.uuid5(_ACES_UUID_NAMESPACE, f"nwfilter:{address}"))


class _NativeResource(Protocol):
    def create(self) -> None: ...

    def destroy(self) -> None: ...

    def undefine(self) -> None: ...


def _existing_uuid(native: object) -> str | None:
    """Return an existing object's UUID string, or None when it cannot be read.

    A missing/unreadable UUID is treated as "not ours" by the caller, so an
    object we cannot prove ownership of is never destroyed.
    """

    reader = getattr(native, "UUIDString", None)
    if reader is None:
        return None
    try:
        return reader()
    except Exception:
        return None


class _LibvirtModule(Protocol):
    def open(self, connection_uri: str) -> object | None: ...


Connector = Callable[[str], object | None]


class LibvirtDeploymentDriver:
    """Realize portable specs against a libvirt connection."""

    def __init__(
        self,
        *,
        connection: object | None = None,
        connection_uri: str = _DEFAULT_CONNECTION_URI,
        connector: Connector | None = None,
        name_prefix: str = "aces",
        workspace: str | Path | None = None,
        seed_builder: SeedBuilder | None = None,
    ) -> None:
        if not connection_uri or not connection_uri.strip():
            raise ValueError("LibvirtDeploymentDriver connection_uri must be non-empty.")
        if not name_prefix or not name_prefix.strip():
            raise ValueError("LibvirtDeploymentDriver name_prefix must be non-empty.")
        self._connection = connection
        self._connection_uri = connection_uri
        self._connector = connector or _default_connector
        self._name_prefix = _safe_name(name_prefix, fallback="aces", prefix="")
        self._workspace = Path(workspace) if workspace is not None else None
        self._seed_builder = seed_builder if seed_builder is not None else GenisoimageSeedBuilder()
        self._names: dict[str, str] = {}
        self._realized: set[str] = set()
        self._seeds: dict[str, Path] = {}
        self._filters: dict[str, str] = {}

    def realize(
        self,
        *,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
    ) -> DriverResult:
        diagnostics: list[Diagnostic] = []
        network_handles: list[NetworkHandle] = []
        domain_handles: list[DomainHandle] = []
        try:
            connection = self._conn()
        except Exception:
            return DriverResult(diagnostics=(_failure("runtime.libvirt.connection", _CODE_UNAVAILABLE),))

        for spec in networks:
            name = self._runtime_name(spec.address, spec.name)
            try:
                # The provisioner only dispatches CREATE/UPDATE specs (UNCHANGED is
                # filtered upstream), so a spec that reaches the driver must be
                # (re)applied to enforce its desired state. Converge any object a
                # prior apply left behind — stop it and drop its stale definition —
                # before redefining, so the new state is genuinely enforced rather
                # than recorded-but-skipped, and no duplicate is ever created.
                self._converge_existing(connection, "networkLookupByName", name, spec.address)
                native = _call_libvirt(connection, "networkDefineXML", _network_xml(spec, name))
                native.create()
            except _OwnershipConflict:
                diagnostics.append(_failure(spec.address, _CODE_OWNERSHIP_CONFLICT))
                continue
            except Exception:
                diagnostics.append(_failure(spec.address, _CODE_OPERATION_FAILED))
                continue
            self._names[spec.address] = name
            self._realized.add(spec.address)
            network_handles.append(NetworkHandle(address=spec.address, realized=True))

        for spec in domains:
            name = self._runtime_name(spec.address, spec.name)
            network_names = tuple(self._name_for(address) for address in spec.networks)
            try:
                # Converge first so a tightened ACL, a disabled account, a changed
                # seed/image, or an existing-but-inactive domain is actually applied
                # — never silently skipped while reporting realized.
                self._converge_existing(connection, "lookupByName", name, spec.address)
                seed_path = self._build_seed(spec, name)
                filter_name = self._define_nwfilter(connection, spec, name)
                xml = _domain_xml(spec, name, network_names, seed_path, filter_name)
                native = _call_libvirt(connection, "defineXML", xml)
                native.create()
            except _OwnershipConflict:
                diagnostics.append(_failure(spec.address, _CODE_OWNERSHIP_CONFLICT))
                continue
            except Exception:
                diagnostics.append(_failure(spec.address, _CODE_OPERATION_FAILED))
                continue
            self._names[spec.address] = name
            self._realized.add(spec.address)
            domain_handles.append(DomainHandle(address=spec.address, realized=True))

        result = DriverResult(
            networks=tuple(network_handles),
            domains=tuple(domain_handles),
            diagnostics=tuple(diagnostics),
        )
        if result.diagnostics:
            self._rollback(network_handles, domain_handles)
            return DriverResult(diagnostics=result.diagnostics)
        return result

    def destroy(
        self,
        *,
        networks: tuple[str, ...],
        domains: tuple[str, ...],
    ) -> DriverResult:
        diagnostics: list[Diagnostic] = []
        try:
            connection = self._conn()
        except Exception:
            return DriverResult(diagnostics=(_failure("runtime.libvirt.connection", _CODE_UNAVAILABLE),))

        domain_handles: list[DomainHandle] = []
        for address in domains:
            try:
                ok = self._destroy_one(connection, "lookupByName", address)
            except _OwnershipConflict:
                # Never delete an object this plan does not own (name collision).
                diagnostics.append(_failure(address, _CODE_OWNERSHIP_CONFLICT))
                domain_handles.append(DomainHandle(address=address, realized=True))
                continue
            if ok:
                self._realized.discard(address)
                self._names.pop(address, None)
                self._cleanup_seed(address)
                self._undefine_nwfilter(connection, address)
            else:
                diagnostics.append(_failure(address, _CODE_OPERATION_FAILED))
            domain_handles.append(DomainHandle(address=address, realized=not ok))

        network_handles: list[NetworkHandle] = []
        for address in networks:
            try:
                ok = self._destroy_one(connection, "networkLookupByName", address)
            except _OwnershipConflict:
                diagnostics.append(_failure(address, _CODE_OWNERSHIP_CONFLICT))
                network_handles.append(NetworkHandle(address=address, realized=True))
                continue
            if ok:
                self._realized.discard(address)
                self._names.pop(address, None)
            else:
                diagnostics.append(_failure(address, _CODE_OPERATION_FAILED))
            network_handles.append(NetworkHandle(address=address, realized=not ok))

        return DriverResult(
            networks=tuple(network_handles),
            domains=tuple(domain_handles),
            diagnostics=tuple(diagnostics),
        )

    def realized_addresses(self) -> frozenset[str]:
        return frozenset(self._realized)

    def _conn(self) -> object:
        if self._connection is None:
            self._connection = self._connector(self._connection_uri)
        if self._connection is None:
            raise RuntimeError("libvirt connection unavailable")
        return self._connection

    def _runtime_name(self, address: str, preferred: str) -> str:
        return _safe_name(preferred, fallback=address.rsplit(".", 1)[-1], prefix=self._name_prefix)

    def _name_for(self, address: str) -> str:
        return self._names.get(address, self._runtime_name(address, address.rsplit(".", 1)[-1]))

    def _build_seed(self, spec: DomainSpec, name: str) -> Path | None:
        cloud_init = spec.cloud_init
        if cloud_init is None or cloud_init.is_empty:
            return None
        seed_dir = self._seed_workspace() / name
        write_seed_files(cloud_init, seed_dir)
        seed_path = self._seed_builder.build(seed_dir=seed_dir)
        self._seeds[spec.address] = seed_path
        return seed_path

    def _seed_workspace(self) -> Path:
        if self._workspace is None:
            # mkdtemp atomically creates an unpredictable directory; relax it to
            # 0o711 (traversable, not listable) so the libvirt/QEMU process can
            # reach the attached seed ISO while other local users still cannot
            # enumerate it or read the 0o600 source files inside.
            self._workspace = Path(tempfile.mkdtemp(prefix=_WORKSPACE_PREFIX))
            os.chmod(self._workspace, _SEED_DIR_MODE)
        else:
            # A configured workspace is attacker-influenceable, so verify it
            # resolves to a directory we own and is not a symlink before trusting
            # it to hold rendered seed content.
            workspace = self._workspace
            if workspace.is_symlink():
                raise PermissionError(f"seed workspace '{workspace}' is a symlink")
            workspace.mkdir(parents=True, exist_ok=True)
            info = os.lstat(workspace)
            if info.st_uid != os.getuid():
                raise PermissionError(f"seed workspace '{workspace}' is not owned by the current user")
            os.chmod(workspace, _SEED_DIR_MODE)
        return self._workspace

    def _cleanup_seed(self, address: str) -> None:
        seed_path = self._seeds.pop(address, None)
        if seed_path is not None:
            shutil.rmtree(seed_path.parent, ignore_errors=True)

    def _define_nwfilter(self, connection: object, spec: DomainSpec, name: str) -> str | None:
        if not spec.network_acls:
            return None
        filter_name = _safe_name(f"{name}-acl", fallback="acl", prefix="")
        owner = _filter_owner_uuid(spec.address)
        # nwfilters are host-global and named-only, so — like domains/networks —
        # refuse to redefine a filter at this name unless it is owner-stamped for
        # this ACES address. A foreign filter (or one for another address that
        # normalizes to the same name) is never overwritten; apply fails closed.
        existing = _lookup(connection, "nwfilterLookupByName", filter_name)
        if existing is not None and _existing_uuid(existing) != owner:
            raise _OwnershipConflict(filter_name)
        define = getattr(connection, "nwfilterDefineXML", None)
        if define is not None:
            # nwfilterDefineXML is upsert: redefining replaces our own filter in
            # place, so a tightened/loosened ACL on re-apply is genuinely enforced.
            define(_nwfilter_xml(filter_name, owner, spec.network_acls))
        self._filters[spec.address] = filter_name
        return filter_name

    @staticmethod
    def _converge_existing(connection: object, lookup_method: str, name: str, address: str) -> None:
        """Stop and undefine the ACES object this apply owns at ``name``.

        Convergence is destructive, so it only proceeds when the existing object's
        UUID proves it is the ACES realization of *this* ``address``. A name hit
        whose UUID is absent or different — a foreign object, or one realized for a
        different ACES address that merely normalizes to the same name — raises
        :class:`_OwnershipConflict` so the apply fails closed instead of replacing
        an object it does not own. A running object we own is stopped first;
        ``destroy()`` on an inactive object raises and is benignly suppressed.
        """

        native = _lookup(connection, lookup_method, name)
        if native is None:
            return
        if _existing_uuid(native) != _aces_uuid(address):
            raise _OwnershipConflict(name)
        with contextlib.suppress(Exception):
            cast(_NativeResource, native).destroy()
        cast(_NativeResource, native).undefine()

    def _undefine_nwfilter(self, connection: object, address: str) -> None:
        filter_name = self._filters.pop(address, None)
        if filter_name is None:
            return
        native = _lookup(connection, "nwfilterLookupByName", filter_name)
        if native is None:
            return
        if _existing_uuid(native) != _filter_owner_uuid(address):
            # A filter at this name we do not own must never be undefined.
            return
        # Best-effort cleanup of our own filter: a filter that cannot be undefined
        # (in use, missing) must not fail the destroy.
        with contextlib.suppress(Exception):
            cast(_NativeResource, native).undefine()

    def _destroy_one(self, connection: object, lookup_method: str, address: str) -> bool:
        native = _lookup(connection, lookup_method, self._name_for(address))
        if native is None:
            return False
        # Apply the same ownership invariant as convergence: never destroy an
        # object whose UUID does not prove it is the ACES object for this address.
        if _existing_uuid(native) != _aces_uuid(address):
            raise _OwnershipConflict(address)
        try:
            with contextlib.suppress(Exception):
                cast(_NativeResource, native).destroy()
            cast(_NativeResource, native).undefine()
        except Exception:
            return False
        return True

    def _rollback(self, networks: list[NetworkHandle], domains: list[DomainHandle]) -> None:
        realized_domains = tuple(handle.address for handle in domains if handle.realized)
        realized_networks = tuple(handle.address for handle in networks if handle.realized)
        if realized_domains or realized_networks:
            self.destroy(networks=realized_networks, domains=realized_domains)


def _default_connector(connection_uri: str) -> object | None:
    libvirt = cast(_LibvirtModule, importlib.import_module("libvirt"))
    return libvirt.open(connection_uri)


def _call_libvirt(connection: object, method_name: str, payload: str) -> _NativeResource:
    method = cast(Callable[[str], _NativeResource], getattr(connection, method_name))
    return method(payload)


def _lookup(connection: object, method_name: str, name: str) -> object | None:
    """Return an existing native resource by name, or None when absent.

    Any lookup failure (not-found or otherwise) returns None so the caller
    attempts a define; a genuine define-time conflict is then surfaced as a
    redacted diagnostic rather than a duplicate resource.
    """

    method = getattr(connection, method_name, None)
    if method is None:
        return None
    try:
        return method(name)
    except Exception:
        return None


def _safe_name(candidate: str, *, fallback: str, prefix: str) -> str:
    raw = candidate.strip() or fallback.strip() or "resource"
    normalized = _SAFE_NAME_RE.sub("-", raw).strip("-._")
    if not normalized:
        normalized = _SAFE_NAME_RE.sub("-", fallback).strip("-._") or "resource"
    prefixed = f"{prefix}-{normalized}" if prefix else normalized
    return prefixed[:63].strip("-._") or "resource"


def _network_xml(spec: NetworkSpec, name: str) -> str:
    root = ET.Element("network")
    ET.SubElement(root, "name").text = name
    # Deterministic per-address UUID stamps ACES ownership for safe convergence.
    ET.SubElement(root, "uuid").text = _aces_uuid(spec.address)
    if spec.labels.get("internal") == "true":
        ET.SubElement(root, "forward", {"mode": "nat"})
    _append_network_ip(root, spec)
    return ET.tostring(root, encoding="unicode")


def _append_network_ip(root: ET.Element, spec: NetworkSpec) -> None:
    """Realize CIDR/gateway into a libvirt ``<ip>`` block with a DHCP range."""

    if not spec.cidr:
        return
    try:
        network = ipaddress.ip_network(spec.cidr, strict=False)
    except ValueError:
        return
    if not isinstance(network, ipaddress.IPv4Network) or network.num_addresses < 4:
        return
    host_ip = spec.gateway or str(network.network_address + 1)
    ip_node = ET.SubElement(root, "ip", {"address": host_ip, "netmask": str(network.netmask)})
    dhcp = ET.SubElement(ip_node, "dhcp")
    ET.SubElement(
        dhcp,
        "range",
        {"start": str(network.network_address + 2), "end": str(network.broadcast_address - 1)},
    )


def _nwfilter_xml(filter_name: str, owner_uuid: str, acls: tuple[NetworkAcl, ...]) -> str:
    root = ET.Element("filter", {"name": filter_name, "chain": "root"})
    # Owner UUID stamps ACES ownership so convergence/cleanup never touches a
    # foreign filter that merely shares this name.
    ET.SubElement(root, "uuid").text = owner_uuid
    priority = 400
    for acl in acls:
        for rule in _acl_rules(acl, priority):
            root.append(rule)
        priority += 10
    return ET.tostring(root, encoding="unicode")


def _acl_rules(acl: NetworkAcl, priority: int) -> list[ET.Element]:
    protocol = acl.protocol if acl.protocol in {"tcp", "udp"} else "all"
    ports: tuple[int | None, ...] = acl.ports if (acl.ports and protocol != "all") else (None,)
    rules: list[ET.Element] = []
    for port in ports:
        rule = ET.Element("rule", {"action": acl.action, "direction": acl.direction, "priority": str(priority)})
        match = ET.SubElement(rule, protocol)
        if acl.src_cidr:
            address, mask = _cidr_address_mask(acl.src_cidr)
            match.set("srcipaddr", address)
            match.set("srcipmask", mask)
        if acl.dst_cidr:
            address, mask = _cidr_address_mask(acl.dst_cidr)
            match.set("dstipaddr", address)
            match.set("dstipmask", mask)
        if port is not None:
            match.set("dstportstart", str(port))
            match.set("dstportend", str(port))
        rules.append(rule)
    return rules


def _cidr_address_mask(cidr: str) -> tuple[str, str]:
    network = ipaddress.ip_network(cidr, strict=False)
    return str(network.network_address), str(network.netmask)


def _domain_xml(
    spec: DomainSpec,
    name: str,
    network_names: tuple[str, ...],
    seed_path: Path | None,
    filter_name: str | None = None,
) -> str:
    root = ET.Element("domain", {"type": "qemu"})
    ET.SubElement(root, "name").text = name
    # Deterministic per-address UUID stamps ACES ownership for safe convergence.
    ET.SubElement(root, "uuid").text = _aces_uuid(spec.address)
    ET.SubElement(root, "memory", {"unit": "MiB"}).text = str(spec.memory_mib)
    ET.SubElement(root, "vcpu").text = str(spec.vcpus)
    os_node = ET.SubElement(root, "os")
    ET.SubElement(os_node, "type", {"arch": "x86_64"}).text = "hvm"
    devices = ET.SubElement(root, "devices")
    if spec.image_ref:
        disk = ET.SubElement(devices, "disk", {"type": "file", "device": "disk"})
        ET.SubElement(disk, "driver", {"name": "qemu", "type": "qcow2"})
        ET.SubElement(disk, "source", {"file": spec.image_ref})
        ET.SubElement(disk, "target", {"dev": "vda", "bus": "virtio"})
    if seed_path is not None:
        cdrom = ET.SubElement(devices, "disk", {"type": "file", "device": "cdrom"})
        ET.SubElement(cdrom, "driver", {"name": "qemu", "type": "raw"})
        ET.SubElement(cdrom, "source", {"file": str(seed_path)})
        # libvirt requires the target dev prefix to match the bus (sd*→sata).
        ET.SubElement(cdrom, "target", {"dev": "sda", "bus": "sata"})
        ET.SubElement(cdrom, "readonly")
    for network_name in network_names:
        interface = ET.SubElement(devices, "interface", {"type": "network"})
        ET.SubElement(interface, "source", {"network": network_name})
        ET.SubElement(interface, "model", {"type": "virtio"})
        if filter_name is not None:
            ET.SubElement(interface, "filterref", {"filter": filter_name})
    return ET.tostring(root, encoding="unicode")


_FAILURE_MESSAGES = {
    _CODE_UNAVAILABLE: "Libvirt connection is unavailable for this backend operation.",
    _CODE_OWNERSHIP_CONFLICT: (
        "Libvirt object for '{address}' already exists under the same name but is not "
        "owned by this ACES address; refusing to converge an object this plan does not own."
    ),
}


def _failure(address: str, code: str) -> Diagnostic:
    template = _FAILURE_MESSAGES.get(code, "Libvirt operation for '{address}' did not succeed.")
    return Diagnostic(
        code=code, domain=_DOMAIN, address=address, message=template.format(address=address), severity=Severity.ERROR
    )
