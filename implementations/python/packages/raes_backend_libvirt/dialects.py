"""OS-family-aware cloud-init realization dialects.

Cloud-init's ``users``, ``write_files``, and (on Linux/BSD) ``packages``
directives are interpreted natively by cloud-init (Linux/BSD) and cloudbase-init
(Windows), so account and file realization is cross-OS without a dialect. Service
enablement and mail aliasing, however, use OS-specific tooling. Each
:class:`GuestDialect` emits the native mechanism for one OS family as injection-
safe argv-list ``runcmd`` entries and ``write_files``; where a family has no
generic mechanism (e.g. Windows mail is Exchange/AD), the dialect records a
portable descriptor — the maximum a generic host realizes — rather than a
Linux primitive applied blindly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .cloudinit import CloudInitFile, safe_path_component

LINUX = "linux"
WINDOWS = "windows"
MACOS = "macos"
FREEBSD = "freebsd"
OTHER = "other"


@dataclass(frozen=True)
class GuestEmit:
    """A portable bundle of cloud-init contributions from one realization step."""

    packages: tuple[str, ...] = ()
    write_files: tuple[CloudInitFile, ...] = ()
    runcmd: tuple[tuple[str, ...], ...] = ()


def _descriptor(path: str, body: dict[str, object]) -> CloudInitFile:
    return CloudInitFile(path=path, content=json.dumps(body, indent=2, sort_keys=True) + "\n")


class GuestDialect:
    """Default dialect: realize what is portable, descriptor-record the rest."""

    os_family = OTHER

    def enable_feature(self, package: str) -> GuestEmit:
        safe = safe_path_component(package, fallback="feature")
        body = {"os_family": self.os_family, "service": package}
        return GuestEmit(write_files=(_descriptor(f"/etc/raes/features/{safe}.json", body),))

    def mail_alias(self, username: str, mail: str) -> GuestEmit:
        safe = safe_path_component(username, fallback="user")
        body = {"os_family": self.os_family, "user": username, "mail": mail}
        return GuestEmit(write_files=(_descriptor(f"/etc/raes/mail/{safe}.json", body),))


class LinuxDialect(GuestDialect):
    os_family = LINUX

    def enable_feature(self, package: str) -> GuestEmit:
        return GuestEmit(packages=(package,), runcmd=(("systemctl", "enable", "--now", package),))

    def mail_alias(self, username: str, mail: str) -> GuestEmit:
        safe = safe_path_component(username, fallback="user")
        return GuestEmit(
            write_files=(CloudInitFile(path=f"/etc/aliases.d/raes-{safe}", content=f"{username}: {mail}\n"),),
            runcmd=(("newaliases",),),
        )


class FreeBsdDialect(GuestDialect):
    os_family = FREEBSD

    def enable_feature(self, package: str) -> GuestEmit:
        return GuestEmit(
            packages=(package,),
            runcmd=(("sysrc", f"{package}_enable=YES"), ("service", package, "start")),
        )

    def mail_alias(self, username: str, mail: str) -> GuestEmit:
        safe = safe_path_component(username, fallback="user")
        return GuestEmit(
            write_files=(CloudInitFile(path=f"/etc/raes/mail/{safe}", content=f"{username}: {mail}\n"),),
            runcmd=(("newaliases",),),
        )


class WindowsDialect(GuestDialect):
    os_family = WINDOWS

    def enable_feature(self, package: str) -> GuestEmit:
        # cloudbase-init has no `packages:` directive; use Chocolatey + sc.exe,
        # both of which take the package/service name as a discrete argv token.
        return GuestEmit(
            runcmd=(
                ("choco", "install", "-y", "--no-progress", package),
                ("sc.exe", "config", package, "start=", "auto"),
                ("sc.exe", "start", package),
            )
        )


class MacOsDialect(GuestDialect):
    os_family = MACOS

    def enable_feature(self, package: str) -> GuestEmit:
        return GuestEmit(runcmd=(("brew", "install", package), ("brew", "services", "start", package)))


_DIALECTS: dict[str, GuestDialect] = {
    dialect.os_family: dialect for dialect in (LinuxDialect(), FreeBsdDialect(), WindowsDialect(), MacOsDialect())
}


def dialect_for(os_family: str) -> GuestDialect:
    """Return the dialect for ``os_family``; the portable default for unknowns."""

    return _DIALECTS.get((os_family or "").lower(), GuestDialect())
