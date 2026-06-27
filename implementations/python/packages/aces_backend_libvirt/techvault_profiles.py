"""TechVault profile selection for the libvirt operational driver."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

CORE_PROFILES = ("otel",)
_IDENTIFIER_SEPARATORS = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ComposeServiceInfo:
    """Profile-relevant metadata for one Compose service."""

    name: str
    aliases: frozenset[str]
    profiles: frozenset[str]
    dependencies: frozenset[str]
    steady_state: bool


@dataclass(frozen=True)
class ComposeProfileIndex:
    """Compose services indexed by normalized ACES/APTL aliases."""

    alias_to_profiles: dict[str, frozenset[str]]
    alias_to_services: dict[str, frozenset[str]]
    services: dict[str, ComposeServiceInfo]

    def profiles_for_aliases(self, aliases: Iterable[str]) -> frozenset[str]:
        profiles: set[str] = set()
        for alias in aliases:
            profiles.update(self.alias_to_profiles.get(alias, frozenset()))
        return frozenset(profiles)

    def services_for_aliases(self, aliases: Iterable[str]) -> frozenset[str]:
        services: set[str] = set()
        for alias in aliases:
            services.update(self.alias_to_services.get(alias, frozenset()))
        return frozenset(services)

    def dependency_closure_for_services(self, service_names: Iterable[str]) -> frozenset[str]:
        closure = set(service_names)
        pending = list(service_names)
        while pending:
            service_name = pending.pop()
            service = self.services.get(service_name)
            if service is None:
                continue
            for dependency in service.dependencies:
                if dependency in closure:
                    continue
                closure.add(dependency)
                pending.append(dependency)
        return frozenset(closure)

    def profiles_for_services(self, service_names: Iterable[str]) -> frozenset[str]:
        profiles: set[str] = set()
        for service_name in service_names:
            service = self.services.get(service_name)
            if service is not None:
                profiles.update(service.profiles)
        return frozenset(profiles)

    def steady_state_container_names(self, profiles: Iterable[str]) -> tuple[str, ...]:
        selected = set(profiles)
        names: list[str] = []
        for service in self.services.values():
            if not service.steady_state:
                continue
            if service.profiles and not (service.profiles & selected):
                continue
            names.append(_container_name(service))
        return tuple(sorted(names))


@dataclass(frozen=True)
class ProfileSelection:
    """Resolved Compose profile selection for an ACES node surface."""

    profiles: tuple[str, ...]
    mapped_nodes: dict[str, tuple[str, ...]]
    unmapped_nodes: tuple[str, ...]


def load_compose_profile_index(project_dir: Path) -> ComposeProfileIndex:
    """Load the Compose profile index from ``project_dir/docker-compose.yml``."""

    services = _load_compose_services(project_dir)
    alias_to_profiles: dict[str, set[str]] = {}
    alias_to_services: dict[str, set[str]] = {}
    service_infos: dict[str, ComposeServiceInfo] = {}
    for service_name, service_def in services.items():
        info = _service_info(str(service_name), service_def)
        if info is None:
            continue
        service_infos[info.name] = info
        for alias in info.aliases:
            alias_to_services.setdefault(alias, set()).add(info.name)
            alias_to_profiles.setdefault(alias, set()).update(info.profiles)
    return ComposeProfileIndex(
        alias_to_profiles={alias: frozenset(profiles) for alias, profiles in alias_to_profiles.items()},
        alias_to_services={alias: frozenset(names) for alias, names in alias_to_services.items()},
        services=service_infos,
    )


def select_profiles_for_nodes(project_dir: Path, node_names: Iterable[str]) -> ProfileSelection:
    """Resolve the APTL profiles required by ``node_names``."""

    index = load_compose_profile_index(project_dir)
    config_profiles = _public_start_profiles(project_dir)
    mapped_nodes: dict[str, tuple[str, ...]] = {}
    unmapped_nodes: list[str] = []
    selected_profiles: set[str] = set(CORE_PROFILES)

    for node_name in sorted(set(node_names)):
        aliases = normalized_identifier_aliases(node_name)
        services = index.services_for_aliases(aliases)
        if services:
            services = index.dependency_closure_for_services(services)
        profiles = index.profiles_for_services(services) | index.profiles_for_aliases(aliases)
        if not profiles:
            unmapped_nodes.append(node_name)
            continue
        mapped_nodes[node_name] = tuple(sorted(profiles))
        selected_profiles.update(profiles)

    profiles = tuple(profile for profile in config_profiles if profile in selected_profiles)
    return ProfileSelection(profiles=profiles, mapped_nodes=mapped_nodes, unmapped_nodes=tuple(unmapped_nodes))


def normalized_identifier_aliases(raw: str) -> set[str]:
    """Return normalized aliases for one service or ACES identifier."""

    normalized = normalize_identifier(raw)
    if not normalized:
        return set()
    aliases = {normalized}
    if normalized.startswith("aptl-"):
        aliases.add(normalized.removeprefix("aptl-"))
    return aliases


def normalize_identifier(raw: str) -> str:
    """Normalize punctuation and case for loose ACES/APTL matching."""

    lowered = raw.strip().lower()
    return _IDENTIFIER_SEPARATORS.sub("-", lowered).strip("-")


def _load_compose_services(project_dir: Path) -> Mapping[str, object]:
    compose_path = project_dir / "docker-compose.yml"
    if not compose_path.exists():
        raise ValueError(f"docker-compose.yml not found under {project_dir}")
    data = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, Mapping):
        raise ValueError(f"{compose_path} must contain a YAML mapping")
    services = data.get("services") or {}
    if not isinstance(services, Mapping):
        raise ValueError(f"{compose_path} services section must be a mapping")
    return services


def _service_info(service_name: str, service_def: object) -> ComposeServiceInfo | None:
    if not isinstance(service_def, Mapping):
        return None
    aliases = {service_name}
    for alias_key in ("container_name", "hostname"):
        alias = service_def.get(alias_key)
        if isinstance(alias, str) and alias.strip():
            aliases.add(alias)
    return ComposeServiceInfo(
        name=service_name,
        aliases=frozenset(alias for raw in aliases for alias in normalized_identifier_aliases(raw)),
        profiles=frozenset(_string_values(service_def.get("profiles"))),
        dependencies=frozenset(_service_dependencies(service_def.get("depends_on"))),
        steady_state=str(service_def.get("restart", "")).lower() not in {"no", "false"},
    )


def _service_dependencies(raw: object) -> set[str]:
    if isinstance(raw, Mapping):
        return {str(name) for name in raw if str(name).strip()}
    return _string_values(raw)


def _string_values(raw: object) -> set[str]:
    if isinstance(raw, str):
        return {raw} if raw.strip() else set()
    if isinstance(raw, list | tuple | set | frozenset):
        return {str(value) for value in raw if str(value).strip()}
    return set()


def _public_start_profiles(project_dir: Path) -> tuple[str, ...]:
    profiles = list(_configured_profiles(project_dir))
    for profile in CORE_PROFILES:
        if profile not in profiles:
            profiles.append(profile)
    return tuple(profiles)


def _configured_profiles(project_dir: Path) -> tuple[str, ...]:
    config_path = project_dir / "aptl.json"
    if not config_path.exists():
        return ()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    containers = data.get("containers", {}) if isinstance(data, Mapping) else {}
    if not isinstance(containers, Mapping):
        return ()
    return tuple(str(name) for name, enabled in containers.items() if enabled is True)


def _container_name(service: ComposeServiceInfo) -> str:
    for alias in sorted(service.aliases):
        if alias.startswith("aptl-"):
            return alias
    return service.name
