"""Generated initramfs appliance support for native TechVault libvirt runs."""

from __future__ import annotations

import gzip
import json
import os
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
        with tempfile.TemporaryDirectory(prefix="aces-initramfs-") as tmp:
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

    os.chmod(path, _LIBVIRT_BOOT_ARTIFACT_MODE)  # NOSONAR: generated boot artifacts contain no secrets.


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
        '  [ "$iface" = lo ] && continue',
        '  mac=$(cat "$iface_path/address")',
        '  ip link set "$iface" up',
        '  case "$mac" in',
    ]
    for interface in _as_sequence(domain.get("interfaces")):
        if not isinstance(interface, Mapping):
            continue
        lines.extend(
            [
                f"    {interface.get('mac')})",
                f'      ip addr add {interface.get("ip")}/{interface.get("cidr_prefix")} dev "$iface"',
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
    return proc.stdout


def _cpio_paths(root: Path) -> list[str]:
    return [str(path.relative_to(root)) for path in sorted(root.rglob("*"))]


def _as_sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, list | tuple) else ()


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
