"""Generated initramfs appliance support for native TechVault libvirt runs."""

from __future__ import annotations

import gzip
import ipaddress
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class InitramfsBuilder(Protocol):
    """Build a bootable appliance initramfs for one TechVault domain."""

    def build(self, *, domain: Mapping[str, object], target: Path) -> Path:
        """Write and return the initramfs path for ``domain``."""
        ...


@dataclass
class BusyboxInitramfsBuilder:
    """Build the generated BusyBox appliance used by native live validation."""

    busybox_path: Path = Path("/usr/bin/busybox")

    def build(self, *, domain: Mapping[str, object], target: Path) -> Path:
        with tempfile.TemporaryDirectory(prefix="raes-initramfs-") as tmp:
            root = Path(tmp)
            _write_appliance_root(root, self.busybox_path, domain)
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = _cpio_newc(root)
            target.write_bytes(gzip.compress(payload, compresslevel=6))
        return target


_LIBVIRT_BOOT_ARTIFACT_MODE = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH


def copy_kernel_for_libvirt(source: Path, target: Path) -> Path:
    """Copy ``source`` to a libvirt-readable run-local kernel path."""

    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or source.stat().st_mtime_ns != target.stat().st_mtime_ns:
        shutil.copy2(source, target)
    make_libvirt_readable(target)
    return target


def make_libvirt_readable(path: Path) -> None:
    """Set a generated boot artifact mode that the libvirt QEMU user can read."""

    os.chmod(path, _LIBVIRT_BOOT_ARTIFACT_MODE)


def _write_appliance_root(root: Path, busybox_path: Path, domain: Mapping[str, object]) -> None:
    bin_dir = root / "bin"
    etc_dir = root / "etc" / "raes"
    for directory in (bin_dir, etc_dir, root / "proc", root / "sys", root / "dev", root / "tmp", root / "run"):
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(busybox_path, bin_dir / "busybox")
    for applet in ("sh", "mount", "mdev", "ip", "ifconfig", "sleep", "cat", "hostname", "printf"):
        (bin_dir / applet).symlink_to("busybox")
    (etc_dir / "domain.json").write_text(json.dumps(domain, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    paths = _cpio_paths(root)
    for path in paths:
        if "\n" in path:
            raise ValueError(f"initramfs member path contains a newline: {path!r}")
    proc = subprocess.run(
        ["cpio", "-o", "-H", "newc", "--quiet"],
        input=("\n".join(paths) + "\n").encode(),
        cwd=root,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("cpio failed while building native TechVault initramfs")
    return proc.stdout


def _cpio_paths(root: Path) -> list[str]:
    return [str(path.relative_to(root)) for path in sorted(root.rglob("*"))]


def _as_sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, list | tuple) else ()


_MAC_RE = re.compile(r"\A[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\Z")


def _interface_case_lines(interface: Mapping[str, object]) -> list[str]:
    """Render one shell-safe ``case`` arm configuring an interface address.

    ``mac``/``ip``/``cidr_prefix`` are interpolated into a root-run guest init
    script. Each is validated to its structural shape and rejected when
    malformed, then quoted as defense in depth: a field that is not the shape it
    claims to be (a ``mac`` that is not a MAC) is a bug in the plan, not text to
    escape into a command.
    """

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
    if isinstance(value, str) and value.isdigit():
        value = int(value)
    if not isinstance(value, int):
        raise ValueError(f"interface cidr_prefix is not an integer: {value!r}")
    if not 0 <= value <= max_prefix:
        raise ValueError(f"interface cidr_prefix is out of range 0..{max_prefix}: {value!r}")
    return value


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
