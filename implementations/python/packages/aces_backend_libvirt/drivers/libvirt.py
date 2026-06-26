"""Lazy libvirt connection adapter for the libvirt/QEMU backend."""

from __future__ import annotations

import importlib
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from typing import Protocol, cast

from aces_contracts.diagnostics import Diagnostic, Severity

from aces_backend_libvirt.driver import (
    DomainHandle,
    DomainSpec,
    DriverResult,
    NetworkHandle,
    NetworkSpec,
)

_DOMAIN = "runtime"
_CODE_OPERATION_FAILED = "libvirt-backend.driver.operation-failed"
_CODE_UNAVAILABLE = "libvirt-backend.driver.unavailable"
_DEFAULT_CONNECTION_URI = "qemu:///system"
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


class _NativeResource(Protocol):
    def create(self) -> None: ...

    def destroy(self) -> None: ...

    def undefine(self) -> None: ...


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
    ) -> None:
        if not connection_uri or not connection_uri.strip():
            raise ValueError("LibvirtDeploymentDriver connection_uri must be non-empty.")
        if not name_prefix or not name_prefix.strip():
            raise ValueError("LibvirtDeploymentDriver name_prefix must be non-empty.")
        self._connection = connection
        self._connection_uri = connection_uri
        self._connector = connector or _default_connector
        self._name_prefix = _safe_name(name_prefix, fallback="aces", prefix="")
        self._names: dict[str, str] = {}
        self._realized: set[str] = set()

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
                native = _call_libvirt(connection, "networkDefineXML", _network_xml(spec, name))
                native.create()
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
                native = _call_libvirt(connection, "defineXML", _domain_xml(spec, name, network_names))
                native.create()
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
            ok = self._destroy_one(connection, "lookupByName", address)
            if ok:
                self._realized.discard(address)
                self._names.pop(address, None)
            else:
                diagnostics.append(_failure(address, _CODE_OPERATION_FAILED))
            domain_handles.append(DomainHandle(address=address, realized=not ok))

        network_handles: list[NetworkHandle] = []
        for address in networks:
            ok = self._destroy_one(connection, "networkLookupByName", address)
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

    def _destroy_one(self, connection: object, lookup_method: str, address: str) -> bool:
        try:
            native = _call_libvirt(connection, lookup_method, self._name_for(address))
            native.destroy()
            native.undefine()
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
    if spec.labels.get("internal") == "true":
        ET.SubElement(root, "forward", {"mode": "nat"})
    return ET.tostring(root, encoding="unicode")


def _domain_xml(spec: DomainSpec, name: str, network_names: tuple[str, ...]) -> str:
    root = ET.Element("domain", {"type": "qemu"})
    ET.SubElement(root, "name").text = name
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
    for network_name in network_names:
        interface = ET.SubElement(devices, "interface", {"type": "network"})
        ET.SubElement(interface, "source", {"network": network_name})
        ET.SubElement(interface, "model", {"type": "virtio"})
    return ET.tostring(root, encoding="unicode")


def _failure(address: str, code: str) -> Diagnostic:
    message = (
        "Libvirt connection is unavailable for this backend operation."
        if code == _CODE_UNAVAILABLE
        else f"Libvirt operation for '{address}' did not succeed."
    )
    return Diagnostic(code=code, domain=_DOMAIN, address=address, message=message, severity=Severity.ERROR)
