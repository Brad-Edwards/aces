"""Generated initramfs appliance support for native TechVault libvirt runs."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ._initramfs import (
    InitramfsPreflight,
    atomic_copy_by_digest,
    atomic_write,
    deterministic_gzip,
    encode_newc,
    resolve_static_busybox,
)

_LIBVIRT_BOOT_ARTIFACT_MODE = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH


class InitramfsBuilder(Protocol):
    """Build a bootable appliance initramfs for one TechVault domain."""

    def build(self, *, domain: Mapping[str, object], target: Path) -> Path:
        """Write and return the initramfs path for ``domain``."""
        ...


@dataclass
class BusyboxInitramfsBuilder:
    """Build the generated BusyBox appliance used by native live validation."""

    busybox_path: Path | None = None
    search_path: str | None = None

    def preflight(self) -> InitramfsPreflight:
        """Resolve and validate the static target BusyBox before mutation."""

        return resolve_static_busybox(self.busybox_path, search_path=self.search_path)

    def build(self, *, domain: Mapping[str, object], target: Path) -> Path:
        busybox_path = self.preflight().require_executable()
        with tempfile.TemporaryDirectory(prefix="raes-initramfs-") as tmp:
            root = Path(tmp)
            _write_appliance_root(root, busybox_path, domain)
            payload = deterministic_gzip(_cpio_newc(root), compresslevel=6)
            return atomic_write(target, payload, mode=_LIBVIRT_BOOT_ARTIFACT_MODE)


def copy_kernel_for_libvirt(source: Path, target: Path) -> Path:
    """Digest-validate and atomically cache a libvirt-readable kernel."""

    return atomic_copy_by_digest(source, target, mode=_LIBVIRT_BOOT_ARTIFACT_MODE)


def make_libvirt_readable(path: Path) -> None:
    """Set a generated boot artifact mode that the libvirt QEMU user can read."""

    os.chmod(path, _LIBVIRT_BOOT_ARTIFACT_MODE)


def _write_appliance_root(root: Path, busybox_path: Path, domain: Mapping[str, object]) -> None:
    bin_dir = root / "bin"
    etc_dir = root / "etc" / "raes"
    for directory in (bin_dir, etc_dir, root / "proc", root / "sys", root / "dev", root / "tmp", root / "run"):
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(busybox_path, bin_dir / "busybox")
    for applet in ("sh", "mount", "mdev", "ip", "ifconfig", "sleep", "cat", "hostname", "printf"):
        (bin_dir / applet).symlink_to("busybox")
    domain_path = etc_dir / "domain.json"
    domain_path.write_text(json.dumps(domain, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    init_path = root / "init"
    init_path.write_text(_init_script(domain), encoding="utf-8")
    os.chmod(domain_path, 0o644)
    os.chmod(init_path, 0o700)
    os.chmod(bin_dir / "busybox", 0o700)


def _init_script(domain: Mapping[str, object]) -> str:
    lines = [
        "#!/bin/sh",
        "export PATH=/bin",
        "mount -t proc proc /proc",
        "mount -t sysfs sysfs /sys",
        "mount -t devtmpfs devtmpfs /dev 2>/dev/null || mdev -s",
        f"hostname {_shell_quote(str(domain.get('name', 'raes-node')))}",
        "ip link set lo up",
        "for iface_path in /sys/class/net/*; do",
        "  iface=${iface_path##*/}",
        '  [ "$iface" = lo ] && continue',
        '  mac=$(cat "$iface_path/address")',
        '  ip link set "$iface" up',
        '  case "$mac" in',
    ]
    for interface in _as_sequence(domain.get("interfaces")):
        if not isinstance(interface, Mapping):
            continue
        lines.extend(_interface_case_lines(interface))
    lines.extend(["  esac", "done"])
    lines.extend(["while true; do sleep 3600; done", ""])
    return "\n".join(lines)


def _cpio_newc(root: Path) -> bytes:
    return encode_newc(root)


def _as_sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, list | tuple) else ()


_MAC_RE = re.compile(r"\A[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\Z")


def _interface_case_lines(interface: Mapping[str, object]) -> list[str]:
    """Render one structurally validated, shell-safe interface case arm."""

    mac = _validated_mac(interface.get("mac"))
    address = _validated_interface_address(interface.get("ip"), interface.get("cidr_prefix"))
    return [
        f"    {_shell_quote(mac)})",
        f'      ip addr add {_shell_quote(address)} dev "$iface"',
        "      ;;",
    ]


def _validated_mac(value: object) -> str:
    if isinstance(value, str) and _MAC_RE.match(value):
        return value
    raise ValueError(f"interface mac is not a MAC address: {value!r}")


def _validated_interface_address(ip: object, cidr_prefix: object) -> str:
    if not isinstance(ip, str):
        raise ValueError(f"interface ip is not an IP address: {ip!r}")
    try:
        parsed = ipaddress.ip_address(ip)
    except ValueError as error:
        raise ValueError(f"interface ip is not an IP address: {ip!r}") from error
    return f"{ip}/{_validated_cidr_prefix(cidr_prefix, parsed.max_prefixlen)}"


def _validated_cidr_prefix(value: object, max_prefix: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"interface cidr_prefix is not an integer: {value!r}")
    if isinstance(value, str) and value.isdecimal():
        value = int(value)
    if not isinstance(value, int):
        raise ValueError(f"interface cidr_prefix is not an integer: {value!r}")
    if not 0 <= value <= max_prefix:
        raise ValueError(f"interface cidr_prefix is out of range 0..{max_prefix}: {value!r}")
    return value


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
