"""NoCloud cloud-init seed media generation for the libvirt driver.

The seed renderer is a host-IO seam: it writes ``user-data``/``meta-data`` into a
per-domain directory under a configured workspace and packages them into a
NoCloud ``cidata`` ISO that the domain XML attaches as a read-only cdrom. The ISO
packaging is delegated to an injectable :class:`SeedBuilder` so default
verification stays hermetic (tests inject a fake builder); the real builder shells
out to ``genisoimage`` only on a host that actually realizes domains.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Protocol

from ..cloudinit import CloudInitSpec, render_meta_data, render_user_data

_SEED_TIMEOUT_SECONDS = 60
_SEED_FILE_MODE = 0o600
# Traversable (o+x) but NOT listable (no o+r): the libvirt/QEMU process — which on
# qemu:///system runs as a different UID than this backend — must traverse the
# workspace and per-domain directory to read the attached seed ISO, yet other
# local users still cannot enumerate the directory, and the private 0o600 source
# files inside remain unreadable to them.
_SEED_DIR_MODE = 0o711
# The seed ISO carries the same rendered cloud-init as the 0o600 source files, so
# it must NOT be world-readable. It is created 0o600 (owner-only); on
# qemu:///system libvirt's dynamic-ownership/security driver relabels the attached
# disk source to the QEMU principal at domain start (and restores it on stop), so
# QEMU — and only QEMU — can read it. Other local users never can.
_SEED_ISO_MODE = 0o600


class SeedBuilder(Protocol):
    """Package the seed files written under ``seed_dir`` into a NoCloud image."""

    def build(self, *, seed_dir: Path) -> Path:
        """Return the path to the realized seed image."""
        ...


def write_seed_files(spec: CloudInitSpec, seed_dir: Path) -> None:
    """Write ``user-data``/``meta-data`` into a freshly created, owner-controlled dir.

    Rendered cloud-init may carry account configuration, so the source files must
    never be exposed to another local principal. ``O_NOFOLLOW`` on the leaf alone is
    not enough: an attacker who can write the workspace could pre-create a regular
    file they own at the deterministic seed path, and an ``O_TRUNC`` open would
    write the secret into *their* file. We therefore (1) remove any pre-existing
    entry at ``seed_dir`` (unlinking a symlink rather than following it), (2)
    create the directory fresh with ``mkdir`` — which fails closed if anything
    races back into the path — (3) confirm the created directory is owned by us
    and is not a symlink, and (4) create each file *exclusively* (``O_EXCL`` |
    ``O_NOFOLLOW``) at ``0o600`` so a pre-positioned file or symlink aborts the
    write instead of receiving the content.

    The directory is ``0o711`` (traversable, not listable): the source files stay
    ``0o600``-private, while the libvirt/QEMU process can still traverse the path to
    read the ``0o644`` seed ISO that :class:`SeedBuilder` later writes here.
    """

    _prepare_private_dir(seed_dir)
    _write_private(seed_dir / "user-data", render_user_data(spec))
    _write_private(seed_dir / "meta-data", render_meta_data(spec))


def _prepare_private_dir(seed_dir: Path) -> None:
    if seed_dir.is_symlink():
        seed_dir.unlink()
    elif seed_dir.is_dir():
        shutil.rmtree(seed_dir)
    elif seed_dir.exists():
        seed_dir.unlink()
    # mkdir (not exist_ok) fails closed if an attacker re-creates the path in the
    # window between the cleanup above and this call.
    seed_dir.mkdir(mode=_SEED_DIR_MODE)
    _verify_owned_private_dir(seed_dir)


def _verify_owned_private_dir(seed_dir: Path) -> None:
    # The directory was just created by mkdir (above), so it is a real directory we
    # own; confirm ownership defensively and force the mode regardless of umask.
    info = os.lstat(seed_dir)
    if info.st_uid != os.getuid():
        raise PermissionError(f"seed directory '{seed_dir}' is not owned by the current user")
    os.chmod(seed_dir, _SEED_DIR_MODE)


def _write_private(path: Path, content: str) -> None:
    # O_EXCL | O_NOFOLLOW: refuse to write if anything already exists at the path,
    # so a pre-positioned regular file or symlink cannot capture the seed content.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(path, flags, _SEED_FILE_MODE)
    try:
        os.write(fd, content.encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(path, _SEED_FILE_MODE)


class GenisoimageSeedBuilder:
    """Package a NoCloud seed ISO with ``genisoimage`` (volume id ``cidata``)."""

    def __init__(self, *, tool: str = "genisoimage", timeout: int = _SEED_TIMEOUT_SECONDS) -> None:
        self._tool = tool
        self._timeout = timeout

    def build(self, *, seed_dir: Path) -> Path:
        seed_iso = seed_dir / "seed.iso"
        # Fixed argv, no shell, bounded timeout, controlled cwd; output captured
        # and discarded so native tool noise never reaches a diagnostic.
        subprocess.run(
            [
                self._tool,
                "-output",
                str(seed_iso),
                "-volid",
                "cidata",
                "-joliet",
                "-rock",
                "user-data",
                "meta-data",
            ],
            cwd=str(seed_dir),
            check=True,
            timeout=self._timeout,
            capture_output=True,
        )
        os.chmod(seed_iso, _SEED_ISO_MODE)
        return seed_iso
