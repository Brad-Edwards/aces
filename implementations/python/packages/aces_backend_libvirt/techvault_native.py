"""Native libvirt/QEMU TechVault appliance driver.

This driver realizes the ACES-planned TechVault node/network surface as tiny
QEMU guests booted by libvirt from generated initramfs appliances. It is
intentionally independent from APTL's Docker Compose substrate: the only runtime
substrate boundary here is libvirt.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Protocol, cast

from aces_backend_protocols.naming import provider_resource_name
from aces_contracts.diagnostics import Diagnostic, Severity

from .driver import DomainHandle, DomainSpec, DriverResult, NetworkHandle, NetworkSpec, ServiceSpec
from .drivers.libvirt import Connector
from .techvault_appliance import (
    BusyboxInitramfsBuilder,
    InitramfsBuilder,
    copy_kernel_for_libvirt,
    make_libvirt_readable,
)
from .techvault_probe import (
    NativeLibvirtProbe,
    ProbeResult,
    check_native_readiness,
    expected_surface,
    native_soc_readback,
)

_DOMAIN = "runtime"
_CODE_OPERATION_FAILED = "libvirt-backend.techvault-native.operation-failed"
_CODE_UNAVAILABLE = "libvirt-backend.techvault-native.unavailable"
_DEFAULT_CONNECTION_URI = "qemu:///system"
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_SUBSTRATE = "libvirt-qemu-initramfs"
__all__ = [
    "BusyboxInitramfsBuilder",
    "NativeLibvirtProbe",
    "ProbeResult",
    "TechVaultNativeLibvirtDriver",
    "check_native_readiness",
    "expected_surface",
    "native_soc_readback",
]


class _NativeResource(Protocol):
    def create(self) -> None: ...

    def destroy(self) -> None: ...

    def undefine(self) -> None: ...


@dataclass
class TechVaultNativeLibvirtDriver:
    """Realize TechVault domains directly as libvirt/QEMU appliances."""

    driver_mode: ClassVar[str] = "techvault-appliance"

    state_dir: Path
    connection: object | None = None
    connection_uri: str = _DEFAULT_CONNECTION_URI
    connector: Connector | None = None
    name_prefix: str = "aces-techvault"
    kernel_path: Path | None = None
    initramfs_builder: InitramfsBuilder = field(default_factory=BusyboxInitramfsBuilder)
    appliance_memory_mib: int = 128
    define_only: bool = False
    clean_existing: bool = False
    last_snapshot: dict[str, object] = field(default_factory=dict)
    last_matrix: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.connection_uri or not self.connection_uri.strip():
            raise ValueError("TechVaultNativeLibvirtDriver connection_uri must be non-empty.")
        if not self.name_prefix or not self.name_prefix.strip():
            raise ValueError("TechVaultNativeLibvirtDriver name_prefix must be non-empty.")
        self.state_dir = Path(self.state_dir)
        self.kernel_path = Path(self.kernel_path) if self.kernel_path is not None else _default_kernel_path()
        self.name_prefix = _safe_name(self.name_prefix, fallback="aces-techvault", prefix="")
        self.appliance_memory_mib = max(64, int(self.appliance_memory_mib))
        self.connector = self.connector or _default_connector
        self._names: dict[str, str] = {}
        self._realized: set[str] = set()

    def realize(
        self,
        *,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
    ) -> DriverResult:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        matrix = _native_matrix(networks=networks, domains=domains, name_prefix=self.name_prefix)
        self.last_matrix = matrix
        try:
            connection = self._conn()
        except Exception:
            return DriverResult(diagnostics=(_diagnostic(_CODE_UNAVAILABLE, "runtime.libvirt.connection"),))
        if self.clean_existing:
            _destroy_existing_with_prefix(connection, self.name_prefix)

        network_handles, network_diagnostics = self._define_networks(connection, matrix)
        domain_handles, domain_diagnostics = self._define_domains(connection, matrix)
        diagnostics = network_diagnostics + domain_diagnostics
        if diagnostics:
            self._rollback(connection, network_handles, domain_handles)
            return DriverResult(diagnostics=tuple(diagnostics))
        self.last_snapshot = _snapshot_from_matrix(matrix, domain_handles, network_handles)
        return DriverResult(networks=tuple(network_handles), domains=tuple(domain_handles))

    def _define_networks(
        self, connection: object, matrix: Mapping[str, object]
    ) -> tuple[list[NetworkHandle], list[Diagnostic]]:
        handles: list[NetworkHandle] = []
        diagnostics: list[Diagnostic] = []
        for network in _as_sequence(matrix.get("networks")):
            if isinstance(network, Mapping):
                handle = self._define_network(connection, network)
                if isinstance(handle, NetworkHandle):
                    handles.append(handle)
                else:
                    diagnostics.append(handle)
        return handles, diagnostics

    def _define_network(self, connection: object, network: Mapping[str, object]) -> NetworkHandle | Diagnostic:
        address = str(network.get("address", ""))
        try:
            native = _call(connection, "networkDefineXML", _network_xml(network))
            if not self.define_only:
                native.create()
        except Exception:
            return _diagnostic(_CODE_OPERATION_FAILED, address)
        self._names[address] = str(network.get("runtime_name", ""))
        self._realized.add(address)
        return NetworkHandle(address=address, realized=True)

    def _define_domains(
        self, connection: object, matrix: Mapping[str, object]
    ) -> tuple[list[DomainHandle], list[Diagnostic]]:
        handles: list[DomainHandle] = []
        diagnostics: list[Diagnostic] = []
        for domain in _as_sequence(matrix.get("domains")):
            if isinstance(domain, Mapping):
                handle = self._define_domain(connection, domain)
                if isinstance(handle, DomainHandle):
                    handles.append(handle)
                else:
                    diagnostics.append(handle)
        return handles, diagnostics

    def _define_domain(self, connection: object, domain: Mapping[str, object]) -> DomainHandle | Diagnostic:
        address = str(domain.get("address", ""))
        try:
            kernel = copy_kernel_for_libvirt(self.kernel_path, self.state_dir / "kernel" / self.kernel_path.name)
            initrd = self.initramfs_builder.build(
                domain=domain,
                target=self.state_dir / "initramfs" / f"{domain.get('runtime_name')}.cpio.gz",
            )
            make_libvirt_readable(initrd)
            native = _call(connection, "defineXML", _domain_xml(domain, kernel=kernel, initrd=initrd))
            if not self.define_only:
                native.create()
        except Exception:
            return _diagnostic(_CODE_OPERATION_FAILED, address)
        self._names[address] = str(domain.get("runtime_name", ""))
        self._realized.add(address)
        return DomainHandle(address=address, realized=True)

    def destroy(
        self,
        *,
        networks: tuple[str, ...],
        domains: tuple[str, ...],
    ) -> DriverResult:
        try:
            connection = self._conn()
        except Exception:
            return DriverResult(diagnostics=(_diagnostic(_CODE_UNAVAILABLE, "runtime.libvirt.connection"),))
        domain_handles: list[DomainHandle] = []
        network_handles: list[NetworkHandle] = []
        diagnostics: list[Diagnostic] = []
        for address in domains:
            ok = self._destroy_one(connection, "lookupByName", address)
            if not ok:
                diagnostics.append(_diagnostic(_CODE_OPERATION_FAILED, address))
            domain_handles.append(DomainHandle(address=address, realized=not ok))
        for address in networks:
            ok = self._destroy_one(connection, "networkLookupByName", address)
            if not ok:
                diagnostics.append(_diagnostic(_CODE_OPERATION_FAILED, address))
            network_handles.append(NetworkHandle(address=address, realized=not ok))
        return DriverResult(
            networks=tuple(network_handles),
            domains=tuple(domain_handles),
            diagnostics=tuple(diagnostics),
        )

    def realized_addresses(self) -> frozenset[str]:
        return frozenset(self._realized)

    def _conn(self) -> object:
        if self.connection is None:
            assert self.connector is not None
            self.connection = self.connector(self.connection_uri)
        if self.connection is None:
            raise RuntimeError("libvirt connection unavailable")
        return self.connection

    def _destroy_one(self, connection: object, lookup_method: str, address: str) -> bool:
        try:
            native = _call(
                connection, lookup_method, self._names.get(address, _runtime_name(self.name_prefix, address))
            )
            native.destroy()
            native.undefine()
        except Exception:
            return False
        self._realized.discard(address)
        self._names.pop(address, None)
        return True

    def _rollback(
        self,
        connection: object,
        networks: Sequence[NetworkHandle],
        domains: Sequence[DomainHandle],
    ) -> None:
        for handle in domains:
            if handle.realized:
                self._destroy_one(connection, "lookupByName", handle.address)
        for handle in networks:
            if handle.realized:
                self._destroy_one(connection, "networkLookupByName", handle.address)


def _native_matrix(
    *,
    networks: tuple[NetworkSpec, ...],
    domains: tuple[DomainSpec, ...],
    name_prefix: str,
) -> dict[str, object]:
    runtime_networks = [_runtime_network(spec, index, name_prefix) for index, spec in enumerate(networks)]
    runtime_network_by_address = {str(item["address"]): item for item in runtime_networks}
    allocations = _allocate_interfaces(domains, runtime_network_by_address, name_prefix)
    runtime_domains = [
        _runtime_domain(spec, name_prefix=name_prefix, interfaces=allocations.get(spec.address, ())) for spec in domains
    ]
    return {
        "substrate": _SUBSTRATE,
        "networks": runtime_networks,
        "domains": runtime_domains,
    }


def _runtime_network(spec: NetworkSpec, index: int, name_prefix: str) -> dict[str, object]:
    network = _network(spec.cidr, index)
    gateway = _gateway(spec.gateway, network)
    return {
        "address": spec.address,
        "name": spec.name,
        "runtime_name": _runtime_name(name_prefix, spec.address, spec.name),
        "cidr": str(network),
        "gateway": str(gateway),
        "netmask": str(network.netmask),
        "internal": spec.labels.get("internal") == "true",
        "hosts": [],
    }


def _allocate_interfaces(
    domains: tuple[DomainSpec, ...],
    networks: Mapping[str, dict[str, object]],
    name_prefix: str,
) -> dict[str, tuple[dict[str, object], ...]]:
    allocations: dict[str, list[dict[str, object]]] = {domain.address: [] for domain in domains}
    next_host: dict[str, int] = dict.fromkeys(networks, 10)
    for domain in domains:
        for network_address in domain.networks:
            network = networks.get(network_address)
            if network is None:
                continue
            parsed = ipaddress.ip_network(str(network["cidr"]), strict=False)
            offset = next_host[network_address]
            next_host[network_address] = offset + 1
            ip = str(parsed.network_address + offset)
            mac = _mac(domain.address, network_address)
            interface = {
                "network_address": network_address,
                "network_name": network.get("name"),
                "runtime_network": network.get("runtime_name"),
                "ip": ip,
                "cidr_prefix": parsed.prefixlen,
                "gateway": network.get("gateway"),
                "mac": mac,
            }
            allocations[domain.address].append(interface)
            cast(list[dict[str, object]], network["hosts"]).append(
                {"name": _runtime_name(name_prefix, domain.address, domain.name), "mac": mac, "ip": ip}
            )
    return {address: tuple(items) for address, items in allocations.items()}


def _runtime_domain(
    spec: DomainSpec,
    *,
    name_prefix: str,
    interfaces: tuple[dict[str, object], ...],
) -> dict[str, object]:
    services = _services_for_domain(spec)
    return {
        "address": spec.address,
        "name": spec.name,
        "runtime_name": _runtime_name(name_prefix, spec.address, spec.name),
        "memory_mib": max(64, min(spec.memory_mib, 128)),
        "vcpus": max(1, min(spec.vcpus, 2)),
        "interfaces": list(interfaces),
        "services": [service.__dict__ for service in services],
        "role": _role(spec.name),
    }


def _services_for_domain(spec: DomainSpec) -> tuple[ServiceSpec, ...]:
    services = list(spec.services)
    if not services and spec.networks:
        services.append(ServiceSpec(name="aces-health", port=80, protocol="tcp"))
    return tuple(sorted(services, key=lambda item: (item.protocol, item.port, item.name)))


def _network_xml(network: Mapping[str, object]) -> str:
    root = ET.Element("network")
    ET.SubElement(root, "name").text = str(network.get("runtime_name", ""))
    if not network.get("internal"):
        ET.SubElement(root, "forward", {"mode": "nat"})
    ip_node = ET.SubElement(
        root,
        "ip",
        {"address": str(network.get("gateway", "")), "netmask": str(network.get("netmask", ""))},
    )
    dhcp = ET.SubElement(ip_node, "dhcp")
    for host in _as_sequence(network.get("hosts")):
        if isinstance(host, Mapping):
            ET.SubElement(
                dhcp,
                "host",
                {"mac": str(host.get("mac", "")), "name": str(host.get("name", "")), "ip": str(host.get("ip", ""))},
            )
    return ET.tostring(root, encoding="unicode")


def _domain_xml(domain: Mapping[str, object], *, kernel: Path, initrd: Path) -> str:
    root = ET.Element("domain", {"type": "qemu"})
    ET.SubElement(root, "name").text = str(domain.get("runtime_name", ""))
    ET.SubElement(root, "memory", {"unit": "MiB"}).text = str(domain.get("memory_mib", 128))
    ET.SubElement(root, "vcpu").text = str(domain.get("vcpus", 1))
    os_node = ET.SubElement(root, "os")
    ET.SubElement(os_node, "type", {"arch": "x86_64"}).text = "hvm"
    ET.SubElement(os_node, "kernel").text = str(kernel)
    ET.SubElement(os_node, "initrd").text = str(initrd)
    ET.SubElement(os_node, "cmdline").text = "console=ttyS0 panic=-1 aces.appliance=techvault"
    features = ET.SubElement(root, "features")
    ET.SubElement(features, "acpi")
    devices = ET.SubElement(root, "devices")
    ET.SubElement(devices, "emulator").text = "/usr/bin/qemu-system-x86_64"
    serial = ET.SubElement(devices, "serial", {"type": "pty"})
    ET.SubElement(serial, "target", {"port": "0"})
    console = ET.SubElement(devices, "console", {"type": "pty"})
    ET.SubElement(console, "target", {"type": "serial", "port": "0"})
    for interface_spec in _as_sequence(domain.get("interfaces")):
        if not isinstance(interface_spec, Mapping):
            continue
        interface = ET.SubElement(devices, "interface", {"type": "network"})
        ET.SubElement(interface, "mac", {"address": str(interface_spec.get("mac", ""))})
        ET.SubElement(interface, "source", {"network": str(interface_spec.get("runtime_network", ""))})
        ET.SubElement(interface, "model", {"type": "virtio"})
    return ET.tostring(root, encoding="unicode")


def _snapshot_from_matrix(
    matrix: Mapping[str, object],
    domains: Sequence[DomainHandle],
    networks: Sequence[NetworkHandle],
) -> dict[str, object]:
    realized = {handle.address for handle in (*domains, *networks) if handle.realized}
    snapshot = json.loads(json.dumps(matrix))
    snapshot["realized_addresses"] = sorted(realized)
    snapshot["substrate"] = _SUBSTRATE
    snapshot["containers"] = []
    return snapshot


def _default_connector(connection_uri: str) -> object | None:
    import importlib

    libvirt = importlib.import_module("libvirt")
    return libvirt.open(connection_uri)


def _call(connection: object, method_name: str, payload: str) -> _NativeResource:
    method = cast(Callable[[str], _NativeResource], getattr(connection, method_name))
    return method(payload)


def _destroy_existing_with_prefix(connection: object, prefix: str) -> None:
    for native in _list_native(connection, "listAllDomains"):
        if _native_name(native).startswith(f"{prefix}-"):
            _destroy_native(native)
    for native in _list_native(connection, "listAllNetworks"):
        if _native_name(native).startswith(f"{prefix}-"):
            _destroy_native(native)


def _list_native(connection: object, method_name: str) -> tuple[object, ...]:
    method = getattr(connection, method_name, None)
    if not callable(method):
        return ()
    try:
        native = method()
    except Exception:
        return ()
    return tuple(native) if isinstance(native, list | tuple) else ()


def _native_name(native: object) -> str:
    method = getattr(native, "name", None)
    if not callable(method):
        return ""
    try:
        value = method()
    except Exception:
        return ""
    return value if isinstance(value, str) else ""


def _destroy_native(native: object) -> None:
    for method_name in ("destroy", "undefine"):
        method = getattr(native, method_name, None)
        if not callable(method):
            continue
        with suppress(Exception):
            method()


def _default_kernel_path() -> Path:
    running = Path(f"/boot/vmlinuz-{os.uname().release}")
    if running.exists():
        return running
    candidates = sorted(Path("/boot").glob("vmlinuz-*"))
    return candidates[-1] if candidates else Path("/boot/vmlinuz")


def _network(cidr: str | None, index: int) -> ipaddress.IPv4Network:
    if cidr:
        try:
            parsed = ipaddress.ip_network(cidr, strict=False)
            if isinstance(parsed, ipaddress.IPv4Network):
                return parsed
        except ValueError:
            pass
    return ipaddress.ip_network(f"192.168.{100 + index}.0/24")


def _gateway(gateway: str | None, network: ipaddress.IPv4Network) -> ipaddress.IPv4Address:
    if gateway:
        try:
            parsed = ipaddress.ip_address(gateway)
            if isinstance(parsed, ipaddress.IPv4Address):
                return parsed
        except ValueError:
            pass
    return network.network_address + 1


def _role(name: str) -> str:
    role = "enterprise"
    if name in {"misp", "thehive", "cortex"} or name.startswith("shuffle-"):
        role = "soc-case-management"
    elif name.startswith("wazuh") or name == "suricata":
        role = "soc-monitoring"
    elif name in {"kali", "kali-capture"}:
        role = "red-team"
    elif name.startswith("aptl-"):
        role = "observability"
    return role


def _runtime_name(prefix: str, address: str, preferred: str | None = None) -> str:
    del preferred
    return provider_resource_name(address, prefix=prefix)


def _safe_name(candidate: str, *, fallback: str, prefix: str) -> str:
    raw = candidate.strip() or fallback.strip() or "resource"
    normalized = _SAFE_NAME_RE.sub("-", raw).strip("-._")
    if not normalized:
        normalized = _SAFE_NAME_RE.sub("-", fallback).strip("-._") or "resource"
    prefixed = f"{prefix}-{normalized}" if prefix else normalized
    return prefixed[:63].strip("-._") or "resource"


def _mac(domain_address: str, network_address: str) -> str:
    digest = hashlib.sha256(f"{domain_address}|{network_address}".encode()).digest()
    return "52:54:00:" + ":".join(f"{byte:02x}" for byte in digest[:3])


def _as_sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, list | tuple) else ()


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _diagnostic(code: str, address: str) -> Diagnostic:
    message = (
        "Libvirt connection is unavailable for native TechVault realization."
        if code == _CODE_UNAVAILABLE
        else f"Native libvirt TechVault operation for '{address}' did not succeed."
    )
    return Diagnostic(code=code, domain=_DOMAIN, address=address, message=message, severity=Severity.ERROR)
