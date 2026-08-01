"""Placement-to-cloud-init aggregation for libvirt plan realization."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.planning import PlannedResource

from .._payload import (
    ACCOUNT_PLACEMENT_RESOURCE_TYPE,
    CONTENT_PLACEMENT_RESOURCE_TYPE,
    DOMAIN_CONTROLLER_PLACEMENT_RESOURCE_TYPE,
    _spec,
    _str,
)
from ..cloudinit import CloudInitFile, CloudInitSpec, CloudInitUser, safe_path_component
from ..dialects import GuestDialect, GuestEmit, dialect_for
from ._common import _resource_name
from ._diagnostics import _unbound_placement


@dataclass
class _CloudInitAccumulator:
    """Mutable per-domain cloud-init contributions, aggregated across placements."""

    users: list[CloudInitUser] = field(default_factory=list)
    write_files: list[CloudInitFile] = field(default_factory=list)
    packages: list[str] = field(default_factory=list)
    runcmd: list[tuple[str, ...]] = field(default_factory=list)

    def build(self, *, hostname: str) -> CloudInitSpec:
        return CloudInitSpec(
            hostname=hostname,
            users=tuple(sorted(self.users, key=lambda user: user.name)),
            write_files=tuple(sorted(self.write_files, key=lambda file: file.path)),
            packages=tuple(dict.fromkeys(self.packages)),
            runcmd=tuple(self.runcmd),
        )


def _aggregate_cloud_init(
    placement_resources: list[tuple[PlannedResource, Mapping[str, object]]],
    node_lookup: dict[str, str],
    node_os: dict[str, str],
    node_addresses: set[str],
) -> tuple[dict[str, _CloudInitAccumulator], list[Diagnostic], dict[str, str]]:
    """Fold each placement into its target domain's cloud-init contributions.

    Service and mail realization is routed through the target node's OS dialect
    so a Windows or BSD guest gets its native mechanism, not a Linux primitive.

    A placement whose target cannot be resolved to a node in this plan is *not*
    silently dropped: it yields an ERROR diagnostic so apply fails closed rather
    than reporting success while leaving the placement unrealized.

    Also returns a ``placement address -> node address`` map so the provisioner
    can realize a domain whose cloud-init changed because a placement changed.
    """

    accumulators: dict[str, _CloudInitAccumulator] = {}
    diagnostics: list[Diagnostic] = []
    placement_targets: dict[str, str] = {}
    for resource, payload in placement_resources:
        target = _placement_target(payload, node_lookup)
        if target is None or target not in node_addresses:
            diagnostics.append(_unbound_placement(resource, target))
            continue
        placement_targets[resource.address] = target
        dialect = dialect_for(node_os.get(target, ""))
        accumulator = accumulators.setdefault(target, _CloudInitAccumulator())
        if resource.resource_type == ACCOUNT_PLACEMENT_RESOURCE_TYPE:
            _realize_account(accumulator, payload, dialect)
        elif resource.resource_type == CONTENT_PLACEMENT_RESOURCE_TYPE:
            _realize_content(accumulator, resource, payload)
        elif resource.resource_type == DOMAIN_CONTROLLER_PLACEMENT_RESOURCE_TYPE:
            # This generic carrier intentionally emits no provider- or
            # product-specific bootstrap commands.
            pass
        else:
            _realize_feature(accumulator, resource, payload, dialect)
    return accumulators, diagnostics, placement_targets


def _merge_emit(accumulator: _CloudInitAccumulator, emit: GuestEmit) -> None:
    accumulator.packages.extend(emit.packages)
    accumulator.write_files.extend(emit.write_files)
    accumulator.runcmd.extend(emit.runcmd)


def _placement_target(payload: Mapping[str, object], node_lookup: dict[str, str]) -> str | None:
    for key in ("target_address", "node_address", "target_node", "node_name", "node", "target"):
        ref = payload.get(key)
        if isinstance(ref, str) and ref:
            return node_lookup.get(ref, ref)
    return None


def _realize_account(accumulator: _CloudInitAccumulator, payload: Mapping[str, object], dialect: GuestDialect) -> None:
    spec = _spec(payload)
    username = _str(spec.get("username")) or _str(payload.get("account_name")) or _str(payload.get("name"))
    if not username:
        return
    groups = tuple(str(group) for group in spec.get("groups", ()) if isinstance(group, str) and group)
    disabled = _truthy(spec.get("disabled"))
    # A disabled account installs no usable credential; otherwise key material is
    # the only credential we render, so password login is always locked.
    ssh_keys = () if disabled else _ssh_authorized_keys(spec)
    # Fail closed on credentials: we never provision a password, so lock_passwd
    # stays True for every account. Unlocking a password account without a hash
    # would leave a known (often privileged) username reachable with no secret —
    # potentially a blank-password login. Key-based auth still works via the
    # rendered authorized keys, which do not require an unlocked password.
    accumulator.users.append(
        CloudInitUser(
            name=username,
            groups=groups,
            shell=_str(spec.get("shell")),
            home=_str(spec.get("home")),
            lock_passwd=True,
            ssh_authorized_keys=ssh_keys,
        )
    )
    mail = _str(spec.get("mail"))
    if mail:
        _merge_emit(accumulator, dialect.mail_alias(username, mail))
    spn = _str(spec.get("spn"))
    if spn:
        # A real Kerberos SPN needs an AD/realm join; absent a domain, the
        # portable maximum is a host-side principal descriptor the guest can join with.
        safe_user = safe_path_component(username, fallback="user")
        accumulator.write_files.append(
            CloudInitFile(path=f"/etc/raes/spn/{safe_user}", content=f"{spn}\n", permissions="0600")
        )


def _realize_content(
    accumulator: _CloudInitAccumulator,
    resource: PlannedResource,
    payload: Mapping[str, object],
) -> None:
    spec = _spec(payload)
    content_type = _str(spec.get("type"))
    if content_type == "file":
        path = _str(spec.get("path"))
        if not path:
            return
        text = spec.get("text")
        if isinstance(text, str):
            accumulator.write_files.append(CloudInitFile(path=path, content=text))
        else:
            accumulator.runcmd.append(("mkdir", "-p", _dirname(path)))
            accumulator.write_files.append(_content_descriptor(resource, payload, path))
    elif content_type == "directory":
        destination = _str(spec.get("destination"))
        if not destination:
            return
        accumulator.runcmd.append(("mkdir", "-p", destination))
        accumulator.write_files.append(_content_descriptor(resource, payload, destination))
    elif content_type == "dataset":
        accumulator.write_files.append(_content_descriptor(resource, payload, None))


def _realize_feature(
    accumulator: _CloudInitAccumulator,
    resource: PlannedResource,
    payload: Mapping[str, object],
    dialect: GuestDialect,
) -> None:
    spec = _spec(payload)
    template = spec.get("template")
    template = template if isinstance(template, Mapping) else {}
    feature_type = _str(template.get("type"))
    source = template.get("source")
    package = _str(source.get("name")) if isinstance(source, Mapping) else ""
    name = _resource_name(resource)
    if feature_type == "service" and package:
        _merge_emit(accumulator, dialect.enable_feature(package))
    else:
        destination = _str(template.get("destination"))
        if destination:
            accumulator.runcmd.append(("mkdir", "-p", _dirname(destination)))
        accumulator.write_files.append(
            CloudInitFile(
                path=f"/etc/raes/features/{safe_path_component(name, fallback='feature')}.json",
                content=_descriptor_body({"feature": name, "type": feature_type, "destination": destination}),
                permissions="0644",
            )
        )


def _content_descriptor(
    resource: PlannedResource,
    payload: Mapping[str, object],
    location: str | None,
) -> CloudInitFile:
    spec = _spec(payload)
    name = _resource_name(resource)
    descriptor = {
        "content": name,
        "type": _str(spec.get("type")),
        "location": location or "",
    }
    safe_name = safe_path_component(name, fallback="content")
    return CloudInitFile(path=f"/etc/raes/content/{safe_name}.json", content=_descriptor_body(descriptor))


def _descriptor_body(descriptor: Mapping[str, object]) -> str:
    return json.dumps(dict(descriptor), indent=2, sort_keys=True) + "\n"


def _ssh_authorized_keys(spec: Mapping[str, object]) -> tuple[str, ...]:
    """Collect any authorized SSH keys the account placement carries."""

    keys: list[str] = []
    for key in ("ssh_authorized_keys", "ssh_keys", "authorized_keys"):
        raw = spec.get(key)
        if isinstance(raw, str) and raw:
            keys.append(raw)
        elif isinstance(raw, list | tuple):
            keys.extend(entry for entry in raw if isinstance(entry, str) and entry)
        if keys:
            break
    return tuple(keys)


def _truthy(value: object) -> bool:
    return value is True


def _dirname(path: str) -> str:
    head = path.rsplit("/", 1)[0]
    return head or "/"
