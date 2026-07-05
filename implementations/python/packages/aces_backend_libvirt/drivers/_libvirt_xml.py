"""Pure libvirt XML rendering for the libvirt/QEMU backend driver.

These builders are deliberately free of connection, ownership, and IO concerns:
each takes an already-resolved runtime name and, where ownership must be stamped,
the caller-derived owner UUID. Keeping rendering in a leaf module lets the driver
module stay focused on native side effects, convergence, and teardown.
"""

from __future__ import annotations

import ipaddress
import xml.etree.ElementTree as ET
from pathlib import Path

from aces_backend_libvirt.driver import DomainSpec, NetworkAcl, NetworkSpec


def _network_xml(spec: NetworkSpec, name: str, owner_uuid: str) -> str:
    root = ET.Element("network")
    ET.SubElement(root, "name").text = name
    # Deterministic per-address UUID stamps ACES ownership for safe convergence.
    ET.SubElement(root, "uuid").text = owner_uuid
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
    owner_uuid: str,
    filter_name: str | None = None,
) -> str:
    root = ET.Element("domain", {"type": "qemu"})
    ET.SubElement(root, "name").text = name
    # Deterministic per-address UUID stamps ACES ownership for safe convergence.
    ET.SubElement(root, "uuid").text = owner_uuid
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
