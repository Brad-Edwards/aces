"""Pure TechVault appliance matrix and structured libvirt XML rendering."""

from __future__ import annotations

import hashlib
import ipaddress
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from aces_backend_protocols.naming import provider_resource_name

from .driver import DomainSpec, NetworkSpec
from .drivers.libvirt import _aces_uuid

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_SUBSTRATE = "libvirt-qemu-initramfs"


def native_matrix(
    *,
    networks: tuple[NetworkSpec, ...],
    domains: tuple[DomainSpec, ...],
    name_prefix: str,
) -> dict[str, object]:
    runtime_networks = [runtime_network(spec, name_prefix) for spec in networks]
    runtime_network_by_address = {str(item["address"]): item for item in runtime_networks}
    allocations = allocate_interfaces(domains, runtime_network_by_address, name_prefix)
    runtime_domains = [
        runtime_domain(spec, name_prefix=name_prefix, interfaces=allocations.get(spec.address, ())) for spec in domains
    ]
    return {
        "substrate": _SUBSTRATE,
        "networks": runtime_networks,
        "domains": runtime_domains,
    }


def runtime_network(spec: NetworkSpec, name_prefix: str) -> dict[str, object]:
    if spec.cidr is None or spec.gateway is None:
        raise ValueError("TechVault network values must be explicit")
    network = ipaddress.ip_network(spec.cidr, strict=True)
    gateway = ipaddress.ip_address(spec.gateway)
    if not isinstance(network, ipaddress.IPv4Network) or not isinstance(gateway, ipaddress.IPv4Address):
        raise ValueError("TechVault appliance supports explicit IPv4 networks only")
    return {
        "address": spec.address,
        "name": spec.name,
        "runtime_name": runtime_name(name_prefix, spec.address, spec.name),
        "cidr": str(network),
        "gateway": str(gateway),
        "netmask": str(network.netmask),
        "internal": spec.labels.get("internal") == "true",
        "hosts": [],
    }


def allocate_interfaces(
    domains: tuple[DomainSpec, ...],
    networks: Mapping[str, dict[str, object]],
    name_prefix: str,
) -> dict[str, tuple[dict[str, object], ...]]:
    allocations: dict[str, list[dict[str, object]]] = {domain.address: [] for domain in domains}
    next_host: dict[str, int] = dict.fromkeys(networks, 10)
    for domain in domains:
        for network_address in domain.networks:
            network = networks[network_address]
            parsed = ipaddress.ip_network(str(network["cidr"]), strict=True)
            offset = next_host[network_address]
            next_host[network_address] = offset + 1
            ip = str(parsed.network_address + offset)
            mac = mac_address(domain.address, network_address)
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
                {"name": runtime_name(name_prefix, domain.address, domain.name), "mac": mac, "ip": ip}
            )
    return {address: tuple(items) for address, items in allocations.items()}


def runtime_domain(
    spec: DomainSpec,
    *,
    name_prefix: str,
    interfaces: tuple[dict[str, object], ...],
) -> dict[str, object]:
    return {
        "address": spec.address,
        "name": spec.name,
        "runtime_name": runtime_name(name_prefix, spec.address, spec.name),
        "memory_mib": spec.memory_mib,
        "vcpus": spec.vcpus,
        "interfaces": list(interfaces),
    }


def network_xml(network: Mapping[str, object]) -> str:
    root = ET.Element("network")
    ET.SubElement(root, "name").text = str(network.get("runtime_name", ""))
    ET.SubElement(root, "uuid").text = _aces_uuid(str(network.get("address", "")))
    if not network.get("internal"):
        ET.SubElement(root, "forward", {"mode": "nat"})
    ip_node = ET.SubElement(
        root,
        "ip",
        {"address": str(network.get("gateway", "")), "netmask": str(network.get("netmask", ""))},
    )
    dhcp = ET.SubElement(ip_node, "dhcp")
    for host in as_sequence(network.get("hosts")):
        if isinstance(host, Mapping):
            ET.SubElement(
                dhcp,
                "host",
                {"mac": str(host.get("mac", "")), "name": str(host.get("name", "")), "ip": str(host.get("ip", ""))},
            )
    return ET.tostring(root, encoding="unicode")


def domain_xml(domain: Mapping[str, object], *, kernel: Path, initrd: Path) -> str:
    root = ET.Element("domain", {"type": "qemu"})
    ET.SubElement(root, "name").text = str(domain.get("runtime_name", ""))
    ET.SubElement(root, "uuid").text = _aces_uuid(str(domain.get("address", "")))
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
    for interface_spec in as_sequence(domain.get("interfaces")):
        if not isinstance(interface_spec, Mapping):
            continue
        interface = ET.SubElement(devices, "interface", {"type": "network"})
        ET.SubElement(interface, "mac", {"address": str(interface_spec.get("mac", ""))})
        ET.SubElement(interface, "source", {"network": str(interface_spec.get("runtime_network", ""))})
        ET.SubElement(interface, "model", {"type": "virtio"})
    return ET.tostring(root, encoding="unicode")


def runtime_name(prefix: str, address: str, preferred: str | None = None) -> str:
    del preferred
    return provider_resource_name(address, prefix=prefix)


def safe_name(candidate: str, *, fallback: str, prefix: str) -> str:
    raw = candidate.strip() or fallback.strip() or "resource"
    normalized = _SAFE_NAME_RE.sub("-", raw).strip("-._")
    if not normalized:
        normalized = _SAFE_NAME_RE.sub("-", fallback).strip("-._") or "resource"
    prefixed = f"{prefix}-{normalized}" if prefix else normalized
    return prefixed[:63].strip("-._") or "resource"


def mac_address(domain_address: str, network_address: str) -> str:
    digest = hashlib.sha256(f"{domain_address}|{network_address}".encode()).digest()
    return "52:54:00:" + ":".join(f"{byte:02x}" for byte in digest[:3])


def as_sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, list | tuple) else ()


__all__ = ["as_sequence", "domain_xml", "native_matrix", "network_xml", "runtime_name", "safe_name"]
