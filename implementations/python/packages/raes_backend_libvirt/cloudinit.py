"""Pure NoCloud cloud-init rendering for the libvirt/QEMU backend.

Turns portable, driver-neutral realization intent (accounts, content files,
feature packages) into deterministic NoCloud ``user-data`` and ``meta-data``
documents. This module is pure: no IO, no driver, no host state. The
interpreter (:mod:`raes_backend_libvirt.realization`) builds a domain's
:class:`CloudInitSpec` from the provisioning plan, and the driver renders seed
media from the same data, so plan interpretation can be validated without
realizing anything.

The cloud-config body is emitted as ``#cloud-config`` followed by JSON. JSON is
a subset of the YAML cloud-init parses, so the document is valid cloud-config
while being deterministic (``sort_keys=True``) and safe for arbitrary string
content (JSON escaping) without a YAML dependency.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

CLOUD_CONFIG_HEADER = "#cloud-config"

_UNSAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._-]")


def safe_path_component(value: str, *, fallback: str) -> str:
    """Reduce a plan-controlled value to one safe path-filename component.

    Descriptor filenames interpolate plan-controlled identifiers (account name,
    feature/content name). A value such as ``../../cron.d/aces`` must never let an
    interpolated ``write_files`` path escape its intended directory, so this maps
    anything outside ``[A-Za-z0-9._-]`` to ``_`` and strips leading/trailing
    ``.``/``_``/``-`` (neutralizing ``.``/``..``). The result is always a single,
    separator-free component; an empty result falls back to ``fallback``.
    """

    cleaned = _UNSAFE_COMPONENT_RE.sub("_", value).strip("._-")
    return cleaned or fallback


@dataclass(frozen=True)
class CloudInitUser:
    """A guest OS account realized via the cloud-init ``users`` directive."""

    name: str
    groups: tuple[str, ...] = ()
    shell: str = ""
    home: str = ""
    lock_passwd: bool = False
    ssh_authorized_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class CloudInitFile:
    """A guest file realized via the cloud-init ``write_files`` directive."""

    path: str
    content: str = ""
    permissions: str = "0644"


@dataclass(frozen=True)
class CloudInitSpec:
    """Aggregated cloud-init realization intent for a single domain.

    ``runcmd`` entries are argv lists, not shell strings: cloud-init executes
    list-form ``runcmd`` entries directly (no shell), so plan-derived paths and
    package names cannot inject shell commands into the root-run guest config.
    """

    hostname: str = ""
    users: tuple[CloudInitUser, ...] = ()
    write_files: tuple[CloudInitFile, ...] = ()
    packages: tuple[str, ...] = ()
    runcmd: tuple[tuple[str, ...], ...] = ()

    @property
    def is_empty(self) -> bool:
        """True when there is nothing to realize beyond a bare hostname."""

        return not (self.users or self.write_files or self.packages or self.runcmd or self.hostname)


def _user_entry(user: CloudInitUser) -> dict[str, object]:
    entry: dict[str, object] = {"name": user.name}
    if user.groups:
        entry["groups"] = list(user.groups)
    if user.shell:
        entry["shell"] = user.shell
    if user.home:
        entry["homedir"] = user.home
    if user.lock_passwd:
        entry["lock_passwd"] = True
    if user.ssh_authorized_keys:
        entry["ssh_authorized_keys"] = list(user.ssh_authorized_keys)
    return entry


def _file_entry(file: CloudInitFile) -> dict[str, object]:
    return {"path": file.path, "content": file.content, "permissions": file.permissions}


def render_user_data(spec: CloudInitSpec) -> str:
    """Render the NoCloud ``user-data`` document for ``spec``."""

    config: dict[str, object] = {}
    if spec.hostname:
        config["hostname"] = spec.hostname
    if spec.users:
        config["users"] = [_user_entry(user) for user in spec.users]
    if spec.packages:
        config["packages"] = list(spec.packages)
    if spec.write_files:
        config["write_files"] = [_file_entry(file) for file in spec.write_files]
    if spec.runcmd:
        config["runcmd"] = [list(command) for command in spec.runcmd]
    body = json.dumps(config, indent=2, sort_keys=True)
    return f"{CLOUD_CONFIG_HEADER}\n{body}\n"


def render_meta_data(spec: CloudInitSpec) -> str:
    """Render the NoCloud ``meta-data`` document for ``spec``.

    ``instance-id`` is derived deterministically from the *rendered seed content*
    (hostname prefix + a hash of ``user-data``): identical content yields an
    identical id (a re-applied unchanged plan does not re-run cloud-init), while
    any change to users/files/packages/runcmd yields a new id. Cloud-init caches
    by instance-id, so a converged UPDATE with changed content is genuinely
    re-applied in the guest rather than treated as already consumed.
    """

    digest = hashlib.sha256(render_user_data(spec).encode("utf-8")).hexdigest()[:16]
    prefix = spec.hostname or "aces"
    meta: dict[str, object] = {"instance-id": f"{prefix}-{digest}"}
    if spec.hostname:
        meta["local-hostname"] = spec.hostname
    return json.dumps(meta, indent=2, sort_keys=True) + "\n"
