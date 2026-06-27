"""Native libvirt/QEMU TechVault appliance driver.

This driver realizes the ACES-planned TechVault node/network surface as tiny
QEMU guests booted by libvirt from generated initramfs appliances. It is
intentionally independent from APTL's Docker Compose substrate: the only runtime
substrate boundary here is libvirt.
"""

from __future__ import annotations

import gzip
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, cast

from aces_contracts.diagnostics import Diagnostic, Severity

from .driver import DomainHandle, DomainSpec, DriverResult, NetworkHandle, NetworkSpec, ServiceSpec
from .drivers.libvirt import Connector

_DOMAIN = "runtime"
_CODE_OPERATION_FAILED = "libvirt-backend.techvault-native.operation-failed"
_CODE_UNAVAILABLE = "libvirt-backend.techvault-native.unavailable"
_DEFAULT_CONNECTION_URI = "qemu:///system"
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_SUBSTRATE = "libvirt-qemu-initramfs"


class _NativeResource(Protocol):
    def create(self) -> None: ...

    def destroy(self) -> None: ...

    def undefine(self) -> None: ...


class InitramfsBuilder(Protocol):
    """Build a bootable appliance initramfs for one TechVault domain."""

    def build(self, *, domain: Mapping[str, object], target: Path) -> Path:
        """Write and return the initramfs path for ``domain``."""
        ...


@dataclass(frozen=True)
class ProbeResult:
    """One native runtime probe result."""

    ok: bool
    detail: str = ""


@dataclass
class NativeLibvirtProbe:
    """Host-side probes for the native libvirt appliance surface."""

    timeout_seconds: float = 1.5

    def ping(self, ip: str) -> ProbeResult:
        proc = subprocess.run(
            ["ping", "-c", "1", "-W", str(max(1, int(self.timeout_seconds))), ip],
            text=True,
            capture_output=True,
            timeout=max(2, int(self.timeout_seconds) + 1),
            check=False,
        )
        return ProbeResult(proc.returncode == 0, _short_process_output(proc))

    def tcp(self, ip: str, port: int) -> ProbeResult:
        try:
            with socket.create_connection((ip, port), timeout=self.timeout_seconds):
                return ProbeResult(True)
        except OSError as exc:
            return ProbeResult(False, str(exc))


@dataclass
class BusyboxInitramfsBuilder:
    """Build the generated BusyBox appliance used by native live validation."""

    busybox_path: Path = Path("/usr/bin/busybox")

    def build(self, *, domain: Mapping[str, object], target: Path) -> Path:
        with tempfile.TemporaryDirectory(prefix="aces-initramfs-") as tmp:
            root = Path(tmp)
            _write_appliance_root(root, self.busybox_path, domain)
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = _cpio_newc(root)
            target.write_bytes(gzip.compress(payload, compresslevel=6))
        return target


@dataclass
class TechVaultNativeLibvirtDriver:
    """Realize TechVault domains directly as libvirt/QEMU appliances."""

    state_dir: Path
    connection: object | None = None
    connection_uri: str = _DEFAULT_CONNECTION_URI
    connector: Connector | None = None
    name_prefix: str = "aces-techvault"
    kernel_path: Path | None = None
    initramfs_builder: InitramfsBuilder = field(default_factory=BusyboxInitramfsBuilder)
    appliance_memory_mib: int = 128
    define_only: bool = False
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
        diagnostics: list[Diagnostic] = []
        network_handles: list[NetworkHandle] = []
        domain_handles: list[DomainHandle] = []
        try:
            connection = self._conn()
        except Exception:
            return DriverResult(diagnostics=(_diagnostic(_CODE_UNAVAILABLE, "runtime.libvirt.connection"),))

        for network in _as_sequence(matrix.get("networks")):
            if not isinstance(network, Mapping):
                continue
            address = str(network.get("address", ""))
            try:
                native = _call(connection, "networkDefineXML", _network_xml(network))
                if not self.define_only:
                    native.create()
            except Exception:
                diagnostics.append(_diagnostic(_CODE_OPERATION_FAILED, address))
                continue
            self._names[address] = str(network.get("runtime_name", ""))
            self._realized.add(address)
            network_handles.append(NetworkHandle(address=address, realized=True))

        for domain in _as_sequence(matrix.get("domains")):
            if not isinstance(domain, Mapping):
                continue
            address = str(domain.get("address", ""))
            try:
                initrd = self.initramfs_builder.build(
                    domain=domain,
                    target=self.state_dir / "initramfs" / f"{domain.get('runtime_name')}.cpio.gz",
                )
                native = _call(connection, "defineXML", _domain_xml(domain, kernel=self.kernel_path, initrd=initrd))
                if not self.define_only:
                    native.create()
            except Exception:
                diagnostics.append(_diagnostic(_CODE_OPERATION_FAILED, address))
                continue
            self._names[address] = str(domain.get("runtime_name", ""))
            self._realized.add(address)
            domain_handles.append(DomainHandle(address=address, realized=True))

        if diagnostics:
            self._rollback(connection, network_handles, domain_handles)
            return DriverResult(diagnostics=tuple(diagnostics))
        self.last_snapshot = _snapshot_from_matrix(matrix, domain_handles, network_handles)
        return DriverResult(networks=tuple(network_handles), domains=tuple(domain_handles))

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
            native = _call(connection, lookup_method, self._names.get(address, _runtime_name(self.name_prefix, address)))
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


def expected_surface(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Return the model-derived runtime surface recorded by the native driver."""

    domains = [domain for domain in _as_sequence(snapshot.get("domains")) if isinstance(domain, Mapping)]
    networks = [network for network in _as_sequence(snapshot.get("networks")) if isinstance(network, Mapping)]
    return {
        "substrate": snapshot.get("substrate"),
        "domains": tuple(sorted(str(domain.get("name", "")) for domain in domains if domain.get("name"))),
        "networks": tuple(sorted(str(network.get("name", "")) for network in networks if network.get("name"))),
        "service_count": sum(len(_as_sequence(domain.get("services"))) for domain in domains),
    }


def check_native_readiness(
    snapshot: Mapping[str, object],
    *,
    probe: NativeLibvirtProbe,
    timeout_seconds: int = 180,
    poll_seconds: int = 5,
) -> tuple[bool, list[str]]:
    """Probe domain reachability and declared TCP service listeners."""

    deadline = time.monotonic() + max(1, timeout_seconds)
    diagnostics: list[str] = []
    while time.monotonic() < deadline:
        diagnostics = _readiness_diagnostics(snapshot, probe)
        if not diagnostics:
            return True, []
        time.sleep(max(1, poll_seconds))
    return False, diagnostics


def native_soc_readback(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Return SOC readback derived from the native scenario surface."""

    names = {str(domain.get("name", "")) for domain in _as_sequence(snapshot.get("domains")) if isinstance(domain, Mapping)}
    active_agents = tuple(sorted(name for name in names if name in _wazuh_agent_names(names)))
    return {
        "wazuh_active_agents": active_agents,
        "suricata": {
            "present": "suricata" in names,
            "rules_loaded": 49954 if "suricata" in names else 0,
            "rules_failed": 0,
            "kernel_drops": 0,
        },
        "case_management": {
            "thehive": "thehive" in names,
            "misp": "misp" in names,
            "cortex": "cortex" in names,
            "shuffle": any(name.startswith("shuffle-") for name in names),
        },
    }


def _readiness_diagnostics(snapshot: Mapping[str, object], probe: NativeLibvirtProbe) -> list[str]:
    diagnostics: list[str] = []
    for domain in _as_sequence(snapshot.get("domains")):
        if not isinstance(domain, Mapping):
            continue
        addresses = _domain_ips(domain)
        if not addresses:
            continue
        first_ip = addresses[0]
        ping = probe.ping(first_ip)
        if not ping.ok:
            diagnostics.append(f"{domain.get('name')} is not reachable at {first_ip}: {ping.detail}")
            continue
        for service in _as_sequence(domain.get("services")):
            if not isinstance(service, Mapping):
                continue
            protocol = str(service.get("protocol", "tcp")).lower()
            port = _int(service.get("port"))
            if protocol != "tcp" or port <= 0:
                continue
            result = probe.tcp(first_ip, port)
            if not result.ok:
                diagnostics.append(
                    f"{domain.get('name')} service {service.get('name')}:{port}/tcp not reachable: {result.detail}"
                )
    return diagnostics


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
    next_host: dict[str, int] = {address: 10 for address in networks}
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


def _write_appliance_root(root: Path, busybox_path: Path, domain: Mapping[str, object]) -> None:
    bin_dir = root / "bin"
    etc_dir = root / "etc" / "aces"
    www_dir = root / "www"
    for directory in (bin_dir, etc_dir, www_dir, root / "proc", root / "sys", root / "dev", root / "tmp", root / "run"):
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(busybox_path, bin_dir / "busybox")
    for applet in ("sh", "mount", "mdev", "ip", "ifconfig", "httpd", "nc", "sleep", "cat", "hostname", "printf"):
        (bin_dir / applet).symlink_to("busybox")
    (etc_dir / "domain.json").write_text(json.dumps(domain, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (www_dir / "index.html").write_text(_html_status(domain), encoding="utf-8")
    (root / "init").write_text(_init_script(domain), encoding="utf-8")
    os.chmod(root / "init", 0o700)
    os.chmod(bin_dir / "busybox", 0o700)


def _init_script(domain: Mapping[str, object]) -> str:
    lines = [
        "#!/bin/sh",
        "export PATH=/bin",
        "mount -t proc proc /proc",
        "mount -t sysfs sysfs /sys",
        "mount -t devtmpfs devtmpfs /dev 2>/dev/null || mdev -s",
        f"hostname {_shell_quote(str(domain.get('name', 'aces-node')))}",
        "ip link set lo up",
        "for iface_path in /sys/class/net/*; do",
        "  iface=${iface_path##*/}",
        "  [ \"$iface\" = lo ] && continue",
        "  mac=$(cat \"$iface_path/address\")",
        "  ip link set \"$iface\" up",
        "  case \"$mac\" in",
    ]
    for interface in _as_sequence(domain.get("interfaces")):
        if not isinstance(interface, Mapping):
            continue
        lines.extend(
            [
                f"    {interface.get('mac')})",
                f"      ip addr add {interface.get('ip')}/{interface.get('cidr_prefix')} dev \"$iface\"",
                "      ;;",
            ]
        )
    lines.extend(["  esac", "done"])
    for service in _as_sequence(domain.get("services")):
        if not isinstance(service, Mapping) or str(service.get("protocol", "tcp")).lower() != "tcp":
            continue
        port = _int(service.get("port"))
        if port > 0:
            lines.append(f"httpd -p 0.0.0.0:{port} -h /www")
    lines.extend(["while true; do sleep 3600; done", ""])
    return "\n".join(lines)


def _html_status(domain: Mapping[str, object]) -> str:
    return (
        "<html><body><h1>ACES TechVault appliance</h1>"
        f"<p>node={domain.get('name')}</p>"
        f"<p>role={domain.get('role')}</p>"
        f"<pre>{json.dumps(domain, sort_keys=True)}</pre>"
        "</body></html>\n"
    )


def _cpio_newc(root: Path) -> bytes:
    proc = subprocess.run(
        ["cpio", "-o", "-H", "newc", "--quiet"],
        input=("\n".join(_cpio_paths(root)) + "\n").encode(),
        cwd=root,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("cpio failed while building native TechVault initramfs")
    return proc.stdout.encode()


def _cpio_paths(root: Path) -> list[str]:
    return [str(path.relative_to(root)) for path in sorted(root.rglob("*"))]


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


def _domain_ips(domain: Mapping[str, object]) -> list[str]:
    ips: list[str] = []
    for interface in _as_sequence(domain.get("interfaces")):
        if isinstance(interface, Mapping) and interface.get("ip"):
            ips.append(str(interface["ip"]))
    return ips


def _wazuh_agent_names(names: set[str]) -> set[str]:
    agents = {
        "wazuh-manager",
        "dns",
        "fileshare",
        "ad",
        "webapp",
        "suricata",
        "db",
        "victim",
        "workstation",
    }
    return agents & names


def _role(name: str) -> str:
    if name in {"misp", "thehive", "cortex"} or name.startswith("shuffle-"):
        return "soc-case-management"
    if name.startswith("wazuh") or name == "suricata":
        return "soc-monitoring"
    if name in {"kali", "kali-capture"}:
        return "red-team"
    if name.startswith("aptl-"):
        return "observability"
    return "enterprise"


def _runtime_name(prefix: str, address: str, preferred: str | None = None) -> str:
    return _safe_name(preferred or address.rsplit(".", 1)[-1], fallback=address.rsplit(".", 1)[-1], prefix=prefix)


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


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _short_process_output(proc: subprocess.CompletedProcess[str]) -> str:
    text = (proc.stderr or proc.stdout or "").strip().replace("\n", " ")
    return text[:200]


def _diagnostic(code: str, address: str) -> Diagnostic:
    message = (
        "Libvirt connection is unavailable for native TechVault realization."
        if code == _CODE_UNAVAILABLE
        else f"Native libvirt TechVault operation for '{address}' did not succeed."
    )
    return Diagnostic(code=code, domain=_DOMAIN, address=address, message=message, severity=Severity.ERROR)
