"""Small self-contained helpers for the native TechVault libvirt drivers."""

from __future__ import annotations

import os
from pathlib import Path


def default_connector(connection_uri: str) -> object | None:
    """Open a real libvirt connection lazily (imports libvirt on demand)."""

    import importlib

    libvirt = importlib.import_module("libvirt")
    return libvirt.open(connection_uri)


def default_kernel_path() -> Path:
    """Return a host kernel image path suitable for booting a generated appliance."""

    running = Path(f"/boot/vmlinuz-{os.uname().release}")
    if running.exists():
        return running
    candidates = sorted(Path("/boot").glob("vmlinuz-*"))
    return candidates[-1] if candidates else Path("/boot/vmlinuz")


__all__ = ["default_connector", "default_kernel_path"]
