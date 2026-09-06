#!/usr/bin/env python3
# ruff: noqa: E402, I001
"""Validate the closed, deterministic development artifact policy."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import stat
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.policy.common import (
    PolicyFailure,
    failures_to_json,
    load_bounded_json_object,
    safe_repo_path,
)

TOOLING_ROOT = "implementations/tooling"
ARTIFACT_LOCK_PATH = f"{TOOLING_ROOT}/artifacts.lock.json"
PROFILES_PATH = f"{TOOLING_ROOT}/profiles/development-profiles.json"
ADMISSION_POLICY_PATH = f"{TOOLING_ROOT}/admission-policy.json"
ACTIONS_POLICY_PATH = f"{TOOLING_ROOT}/actions-policy.json"
SELECTOR_BINDINGS_PATH = f"{TOOLING_ROOT}/selector-bindings.json"
INVENTORY_COVERAGE_PATH = f"{TOOLING_ROOT}/inventory-coverage.json"

_POLICY_SCHEMAS = {
    ARTIFACT_LOCK_PATH: f"{TOOLING_ROOT}/schemas/artifact-lock.schema.json",
    PROFILES_PATH: f"{TOOLING_ROOT}/schemas/profiles.schema.json",
    ADMISSION_POLICY_PATH: f"{TOOLING_ROOT}/schemas/admission-policy.schema.json",
    ACTIONS_POLICY_PATH: f"{TOOLING_ROOT}/schemas/actions-policy.schema.json",
    SELECTOR_BINDINGS_PATH: f"{TOOLING_ROOT}/schemas/selector-bindings.schema.json",
    INVENTORY_COVERAGE_PATH: f"{TOOLING_ROOT}/schemas/inventory-coverage.schema.json",
}
_MAX_JSON_BYTES = 2 * 1024 * 1024
_MAX_SCANNED_FILE_BYTES = 2 * 1024 * 1024
_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_ACQUISITION_COMMAND_RE = re.compile(
    r"(?:^|[;&|('\"\n]\s*)(?:command\s+)?(?:sudo\s+)?(?:curl|wget)\b"
    r"|(?:^|[;&|('\"\n]\s*)(?:command\s+)?(?:gh\s+release\s+download|git\s+clone)\b"
    r"|(?:^|[;&|('\"\n]\s*)(?:command\s+)?(?:uv\s+(?:tool|pip)\s+install|pip(?:3)?\s+install)\b"
    r"|(?:^|[;&|('\"\n]\s*)(?:command\s+)?(?:docker|podman)\s+pull\b"
    r"|(?:^|[;&|('\"\n]\s*)(?:command\s+)?skopeo\s+copy\b",
    re.MULTILINE,
)
_SCANNED_SUFFIXES = frozenset({".py", ".sh", ".bash", ".ps1", ".yaml", ".yml", ".toml"})
_SCANNED_NAMES = frozenset({"Dockerfile", "Makefile"})
_FORBIDDEN_EXECUTABLE_KEYS = frozenset(
    {
        "argv",
        "command",
        "commands",
        "exec",
        "hook",
        "hooks",
        "install_command",
        "post_install",
        "pre_install",
        "script",
        "shell",
    }
)
_MUTABLE_SELECTORS = frozenset({"dev", "head", "latest", "main", "master", "nightly", "stable"})
_SECRET_QUERY_KEYS = frozenset(
    {
        "access_token",
        "apikey",
        "api_key",
        "auth",
        "key",
        "password",
        "secret",
        "sig",
        "signature",
        "token",
    }
)
_EXPECTED_INVENTORY_IDS = frozenset(
    {
        *(f"I{index:02d}" for index in range(1, 17)),
        *(f"A{index:02d}" for index in range(1, 8)),
        *(f"O{index:02d}" for index in range(1, 5)),
        *(f"C{index:02d}" for index in range(1, 5)),
        "S01",
        "S02",
        "D01",
    }
)


def _failure(rule_id: str, message: str, path: str | None = None) -> PolicyFailure:
    return PolicyFailure(rule_id, message, path)


def normalize_platform_id(value: str) -> str:
    """Return the canonical OS/architecture identity used by the lock."""

    normalized = value.strip().lower().replace("_", "-")
    parts = [part for part in normalized.split("-") if part]
    os_aliases = {"darwin": "macos", "mac": "macos", "osx": "macos"}
    arch_aliases = {
        "64-bit": "x86-64",
        "aarch64": "arm64",
        "amd64": "x86-64",
        "x64": "x86-64",
        "x86_64": "x86-64",
    }
    if parts:
        parts[0] = os_aliases.get(parts[0], parts[0])
    if len(parts) >= 2:
        arch = "-".join(parts[1:])
        arch = arch_aliases.get(arch, arch)
        parts = [parts[0], arch]
    return "-".join(parts).replace("x86-64", "x86_64")


def _load_documents(
    repo_root: Path,
) -> tuple[dict[str, dict[str, Any]], list[PolicyFailure]]:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ModuleNotFoundError:
        return {}, [
            _failure(
                "tooling-validator-unavailable",
                "the frozen project JSON Schema validator is unavailable",
            )
        ]
    documents: dict[str, dict[str, Any]] = {}
    failures: list[PolicyFailure] = []
    for policy_path, schema_path in _POLICY_SCHEMAS.items():
        unsafe_file = next(
            (
                relative_path
                for relative_path in (policy_path, schema_path)
                if not _is_regular_repo_file(repo_root, relative_path)
            ),
            None,
        )
        if unsafe_file is not None:
            failures.append(
                _failure(
                    "tooling-json-file",
                    "policy authorities must be bounded regular files inside the repository",
                    unsafe_file,
                )
            )
            continue
        try:
            document = load_bounded_json_object(repo_root, policy_path, max_bytes=_MAX_JSON_BYTES)
            schema = load_bounded_json_object(repo_root, schema_path, max_bytes=_MAX_JSON_BYTES)
        except (OSError, UnicodeError, ValueError):
            failures.append(
                _failure(
                    "tooling-json-parse",
                    "policy or schema could not be loaded and parsed safely",
                    policy_path,
                )
            )
            continue
        documents[policy_path] = document
        if _contains_nonlocal_schema_reference(schema):
            failures.append(
                _failure(
                    "tooling-schema-reference",
                    "internal tooling schemas may use only local fragment references",
                    schema_path,
                )
            )
            continue
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for error in sorted(validator.iter_errors(document), key=lambda item: list(item.absolute_path)):
            location = ".".join(str(part) for part in error.absolute_path) or "<root>"
            failures.append(
                _failure(
                    "tooling-schema",
                    f"schema validation failed at {location}: {error.message}",
                    policy_path,
                )
            )
    return documents, failures


def _is_regular_repo_file(repo_root: Path, relative_path: str) -> bool:
    if safe_repo_path(repo_root, relative_path) is None:
        return False
    current = repo_root.resolve()
    parts = Path(relative_path).parts
    for index, part in enumerate(parts):
        current /= part
        try:
            mode = current.lstat().st_mode
        except OSError:
            return False
        if stat.S_ISLNK(mode):
            return False
        if index < len(parts) - 1 and not stat.S_ISDIR(mode):
            return False
    return bool(parts) and stat.S_ISREG(mode)


def _contains_nonlocal_schema_reference(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == "$ref" and (not isinstance(child, str) or not child.startswith("#")):
                return True
            if _contains_nonlocal_schema_reference(child):
                return True
    elif isinstance(value, list):
        return any(_contains_nonlocal_schema_reference(child) for child in value)
    return False


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_set(value: object) -> set[str]:
    return {item for item in _as_list(value) if isinstance(item, str)}


def _policy_join_failures(
    *,
    policy_refs: set[str],
    expected_subjects: set[str],
    provided_evidence: set[str],
    policies: Mapping[str, Mapping[str, Any]],
    path: str,
    context: str,
    require_all_evidence_per_policy: bool,
) -> list[PolicyFailure]:
    failures: list[PolicyFailure] = []
    joined_subjects: set[str] = set()
    joined_evidence: set[str] = set()
    for policy_ref in sorted(policy_refs):
        policy = policies.get(policy_ref)
        if policy is None or policy.get("status") != "active":
            failures.append(
                _failure(
                    "tooling-policy-reference",
                    f"{context} references a missing or inactive admission policy",
                    path,
                )
            )
            continue
        subject = policy.get("subject")
        accepted_evidence = _string_set(policy.get("accepted_evidence"))
        if isinstance(subject, str):
            joined_subjects.add(subject)
        joined_evidence.update(accepted_evidence)
        if subject not in expected_subjects:
            failures.append(
                _failure(
                    "tooling-policy-subject",
                    f"{context} admission policy has an incompatible subject",
                    path,
                )
            )
        evidence_compatible = (
            provided_evidence <= accepted_evidence
            if require_all_evidence_per_policy
            else bool(provided_evidence & accepted_evidence)
        )
        if not evidence_compatible:
            failures.append(
                _failure(
                    "tooling-policy-evidence",
                    f"{context} does not supply evidence accepted by its admission policy",
                    path,
                )
            )
    if expected_subjects - joined_subjects:
        failures.append(
            _failure(
                "tooling-policy-subject",
                f"{context} lacks an active admission policy for every declared subject",
                path,
            )
        )
    if provided_evidence - joined_evidence:
        failures.append(
            _failure(
                "tooling-policy-evidence",
                f"{context} supplies evidence not admitted by its referenced policies",
                path,
            )
        )
    return failures


def _walk_forbidden_keys(value: object, *, path: str = "<root>") -> list[PolicyFailure]:
    failures: list[PolicyFailure] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if isinstance(key, str) and key.lower() in _FORBIDDEN_EXECUTABLE_KEYS:
                failures.append(
                    _failure(
                        "tooling-executable-field",
                        f"declarative policy contains forbidden executable field {key!r}",
                        ARTIFACT_LOCK_PATH,
                    )
                )
            failures.extend(_walk_forbidden_keys(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            failures.extend(_walk_forbidden_keys(child, path=f"{path}[{index}]"))
    return failures


def _has_secret_bearing_locator(locator: str) -> bool:
    if "${{" in locator or "${" in locator or "{{" in locator:
        return True
    try:
        parsed = urlsplit(locator)
    except ValueError:
        return True
    if parsed.username is not None or parsed.password is not None:
        return True
    return any(key.lower() in _SECRET_QUERY_KEYS for key, _value in parse_qsl(parsed.query, keep_blank_values=True))


def _is_portable_relative_manifest_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        value == path.as_posix()
        and not path.is_absolute()
        and "\\" not in value
        and not re.match(r"^[A-Za-z]:", value)
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _artifact_failures(repo_root: Path, documents: Mapping[str, dict[str, Any]]) -> list[PolicyFailure]:
    lock = documents.get(ARTIFACT_LOCK_PATH)
    profiles_document = documents.get(PROFILES_PATH)
    admission = documents.get(ADMISSION_POLICY_PATH)
    if lock is None:
        return []

    failures = _walk_forbidden_keys(lock)
    profiles: dict[str, Mapping[str, Any]] = {}
    for profile in _as_list((profiles_document or {}).get("profiles")):
        if not isinstance(profile, Mapping) or not isinstance(profile.get("profile_id"), str):
            continue
        profile_id = profile["profile_id"]
        if profile_id in profiles:
            failures.append(
                _failure(
                    "tooling-profile-duplicate",
                    "duplicate development profile",
                    PROFILES_PATH,
                )
            )
        profiles[profile_id] = profile
        canonical = _as_mapping(profile.get("platform")).get("canonical_id")
        aliases = _string_set(_as_mapping(profile.get("platform")).get("aliases"))
        if isinstance(canonical, str) and any(
            normalize_platform_id(alias) != normalize_platform_id(canonical) for alias in aliases
        ):
            failures.append(
                _failure(
                    "tooling-profile-alias",
                    f"{profile_id} contains an alias for another platform",
                    PROFILES_PATH,
                )
            )
    policies: dict[str, Mapping[str, Any]] = {}
    for policy in _as_list((admission or {}).get("policies")):
        if not isinstance(policy, Mapping) or not isinstance(policy.get("policy_id"), str):
            continue
        policy_id = policy["policy_id"]
        if policy_id in policies:
            failures.append(
                _failure(
                    "tooling-policy-duplicate",
                    "duplicate admission policy id",
                    ADMISSION_POLICY_PATH,
                )
            )
        policies[policy_id] = policy
    denied_digests = _string_set((admission or {}).get("denied_digests"))
    artifact_ids: list[str] = []
    seen_artifact_ids: set[str] = set()
    dependency_graph: dict[str, set[str]] = {}
    identities: set[tuple[str, str]] = set()

    for artifact in _as_list(lock.get("artifacts")):
        if not isinstance(artifact, Mapping):
            continue
        artifact_id = artifact.get("artifact_id")
        if not isinstance(artifact_id, str):
            continue
        artifact_ids.append(artifact_id)
        if artifact_id in seen_artifact_ids:
            failures.append(
                _failure(
                    "tooling-artifact-duplicate",
                    "duplicate artifact id",
                    ARTIFACT_LOCK_PATH,
                )
            )
        seen_artifact_ids.add(artifact_id)
        dependency_graph.setdefault(artifact_id, set())
        artifact_class = artifact.get("artifact_class")

        for field in ("version",):
            selector = artifact.get(field)
            if isinstance(selector, str) and (
                selector.lower() in _MUTABLE_SELECTORS or selector.lower().startswith("refs/heads/")
            ):
                failures.append(
                    _failure(
                        "tooling-mutable-selector",
                        f"{artifact_id} uses a mutable {field}",
                        ARTIFACT_LOCK_PATH,
                    )
                )
        source = _as_mapping(artifact.get("source"))
        release = source.get("release")
        if isinstance(release, str) and (
            release.lower() in _MUTABLE_SELECTORS or release.lower().startswith("refs/heads/")
        ):
            failures.append(
                _failure(
                    "tooling-mutable-selector",
                    f"{artifact_id} uses a mutable release selector",
                    ARTIFACT_LOCK_PATH,
                )
            )
        repository = source.get("repository")
        if isinstance(repository, str) and _has_secret_bearing_locator(repository):
            failures.append(
                _failure(
                    "tooling-secret-bearing-locator",
                    f"{artifact_id} source locator contains credentials, secret interpolation, or a secret query key",
                    ARTIFACT_LOCK_PATH,
                )
            )
        authenticity = _as_mapping(artifact.get("authenticity"))
        if authenticity.get("status") not in {"verified", "absent-reviewed"}:
            failures.append(
                _failure(
                    "tooling-authenticity-unreviewed",
                    f"{artifact_id} authenticity is not reviewed",
                    ARTIFACT_LOCK_PATH,
                )
            )
        if artifact_class == "source-snapshot":
            artifact_subjects = {"source-snapshot"}
            artifact_evidence = {
                "raw-sha256",
                "installed-sha256",
                "exact-size",
                "checked-in-byte-sha256",
                "incumbent-source-digest",
            }
        elif artifact_class == "oci-image":
            artifact_subjects = {"oci-image"}
            artifact_evidence = {"oci-index-digest", "reviewed-consumer-reference"}
        else:
            artifact_subjects = {"artifact"}
            artifact_evidence = {"raw-sha256", "installed-sha256", "exact-size"}
        if authenticity.get("status") == "absent-reviewed":
            artifact_evidence.add("absent-signature-review")
        failures.extend(
            _policy_join_failures(
                policy_refs=_string_set(artifact.get("policy_refs")),
                expected_subjects=artifact_subjects,
                provided_evidence=artifact_evidence,
                policies=policies,
                path=ARTIFACT_LOCK_PATH,
                context=f"{artifact_id} artifact",
                require_all_evidence_per_policy=True,
            )
        )

        for platform in _as_list(artifact.get("platforms")):
            if not isinstance(platform, Mapping):
                continue
            platform_id = platform.get("platform_id")
            if not isinstance(platform_id, str):
                continue
            identity = (artifact_id, normalize_platform_id(platform_id))
            if identity in identities:
                failures.append(
                    _failure(
                        "tooling-artifact-identity-duplicate",
                        f"duplicate canonical artifact/platform identity for {artifact_id}",
                        ARTIFACT_LOCK_PATH,
                    )
                )
            identities.add(identity)
            for source_url in _as_list(platform.get("source_urls")):
                if isinstance(source_url, str) and _has_secret_bearing_locator(source_url):
                    failures.append(
                        _failure(
                            "tooling-secret-bearing-locator",
                            f"{artifact_id} source URL contains credentials, secret interpolation, or a secret query key",
                            ARTIFACT_LOCK_PATH,
                        )
                    )
            dependencies = _string_set(platform.get("dependencies"))
            dependency_graph[artifact_id].update(dependencies)
            for profile_id in _string_set(platform.get("profile_ids")):
                profile = profiles.get(profile_id)
                if profile is None:
                    failures.append(
                        _failure(
                            "tooling-profile-missing",
                            f"{artifact_id} names an unknown profile",
                            ARTIFACT_LOCK_PATH,
                        )
                    )
                    continue
                canonical = _as_mapping(profile.get("platform")).get("canonical_id")
                if not isinstance(canonical, str) or normalize_platform_id(canonical) != identity[1]:
                    failures.append(
                        _failure(
                            "tooling-profile-platform",
                            f"{artifact_id} profile platform does not match",
                            ARTIFACT_LOCK_PATH,
                        )
                    )
                if artifact_id not in _string_set(profile.get("supported_artifact_ids")):
                    failures.append(
                        _failure(
                            "tooling-profile-support",
                            f"{artifact_id} is not admitted by its profile",
                            ARTIFACT_LOCK_PATH,
                        )
                    )
                locator_ids = {
                    locator.get("locator_id")
                    for locator in _as_list(profile.get("locator_classes"))
                    if isinstance(locator, Mapping) and isinstance(locator.get("locator_id"), str)
                }
                if not _string_set(source.get("locator_refs")) <= locator_ids:
                    failures.append(
                        _failure(
                            "tooling-locator-profile",
                            f"{artifact_id} source locator is not admitted by {profile_id}",
                            ARTIFACT_LOCK_PATH,
                        )
                    )
            for manifest_name in ("raw_manifest", "installed_manifest"):
                for entry in _as_list(platform.get(manifest_name)):
                    manifest_entry = _as_mapping(entry)
                    digest = manifest_entry.get("sha256")
                    relative_path = manifest_entry.get("path")
                    if isinstance(relative_path, str) and not _is_portable_relative_manifest_path(relative_path):
                        failures.append(
                            _failure(
                                "tooling-manifest-path",
                                f"{artifact_id} manifest path is not a normalized portable relative path",
                                ARTIFACT_LOCK_PATH,
                            )
                        )
                    if isinstance(digest, str) and digest in denied_digests:
                        failures.append(
                            _failure(
                                "tooling-digest-denied",
                                f"{artifact_id} uses a denied digest",
                                ARTIFACT_LOCK_PATH,
                            )
                        )
                    if artifact_class == "source-snapshot" and manifest_name == "installed_manifest":
                        expected_size = manifest_entry.get("size")
                        if not isinstance(relative_path, str) or not isinstance(expected_size, int):
                            continue
                        source_path = safe_repo_path(repo_root, relative_path)
                        if (
                            source_path is None
                            or not _is_regular_repo_file(repo_root, relative_path)
                            or source_path.stat().st_size > _MAX_SCANNED_FILE_BYTES
                        ):
                            failures.append(
                                _failure(
                                    "tooling-source-snapshot-missing",
                                    "locked source snapshot is missing",
                                    relative_path,
                                )
                            )
                            continue
                        try:
                            source_bytes = source_path.read_bytes()
                        except OSError:
                            failures.append(
                                _failure(
                                    "tooling-source-snapshot-missing",
                                    "locked source snapshot cannot be read",
                                    relative_path,
                                )
                            )
                            continue
                        actual_digest = hashlib.sha256(source_bytes).hexdigest()
                        if len(source_bytes) != expected_size or actual_digest != digest:
                            failures.append(
                                _failure(
                                    "tooling-source-snapshot-drift",
                                    "locked source snapshot bytes differ",
                                    relative_path,
                                )
                            )

    known_artifacts = set(artifact_ids)
    for profile_id, profile in profiles.items():
        if unknown := _string_set(profile.get("supported_artifact_ids")) - known_artifacts:
            failures.append(
                _failure(
                    "tooling-profile-artifact",
                    f"{profile_id} admits {len(unknown)} unknown artifacts",
                    PROFILES_PATH,
                )
            )
    for artifact_id, dependencies in dependency_graph.items():
        for dependency in dependencies - known_artifacts:
            failures.append(
                _failure(
                    "tooling-dependency-missing",
                    f"{artifact_id} depends on unknown artifact {dependency}",
                    ARTIFACT_LOCK_PATH,
                )
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(artifact_id: str) -> bool:
        if artifact_id in visiting:
            return True
        if artifact_id in visited:
            return False
        visiting.add(artifact_id)
        cyclic = any(
            visit(dependency)
            for dependency in dependency_graph.get(artifact_id, set())
            if dependency in known_artifacts
        )
        visiting.remove(artifact_id)
        visited.add(artifact_id)
        return cyclic

    if any(visit(artifact_id) for artifact_id in sorted(known_artifacts)):
        failures.append(
            _failure(
                "tooling-dependency-cycle",
                "artifact dependency graph contains a cycle",
                ARTIFACT_LOCK_PATH,
            )
        )
    return failures


def _tracked_paths(repo_root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return sorted(path.decode("utf-8") for path in proc.stdout.split(b"\0") if path)


def _walk_mapping_values(value: object, key_name: str) -> tuple[list[str], bool]:
    """Return scalar values for an exact structured key and whether any were invalid."""

    values: list[str] = []
    invalid = False
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == key_name:
                if isinstance(child, str) and child:
                    values.append(child)
                else:
                    invalid = True
            child_values, child_invalid = _walk_mapping_values(child, key_name)
            values.extend(child_values)
            invalid = invalid or child_invalid
    elif isinstance(value, list):
        for child in value:
            child_values, child_invalid = _walk_mapping_values(child, key_name)
            values.extend(child_values)
            invalid = invalid or child_invalid
    return values, invalid


def _safe_text(repo_root: Path, relative_path: str) -> str | None:
    if ".secrets" in Path(relative_path).parts:
        return None
    path = safe_repo_path(repo_root, relative_path)
    if path is None or not _is_regular_repo_file(repo_root, relative_path):
        return None
    if path.stat().st_size > _MAX_SCANNED_FILE_BYTES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _action_failures(
    repo_root: Path,
    documents: Mapping[str, dict[str, Any]],
    tracked_paths: Sequence[str],
) -> list[PolicyFailure]:
    policy = documents.get(ACTIONS_POLICY_PATH)
    if policy is None:
        return []
    failures: list[PolicyFailure] = []
    admission = documents.get(ADMISSION_POLICY_PATH) or {}
    policies = {
        item["policy_id"]: item
        for item in _as_list(admission.get("policies"))
        if isinstance(item, Mapping) and isinstance(item.get("policy_id"), str)
    }
    failures.extend(
        _policy_join_failures(
            policy_refs=_string_set(policy.get("policy_refs")),
            expected_subjects={"action"},
            provided_evidence={"git-commit-sha", "reviewed-workflow-reference"},
            policies=policies,
            path=ACTIONS_POLICY_PATH,
            context="GitHub Action source policy",
            require_all_evidence_per_policy=True,
        )
    )
    declared: set[tuple[str, str]] = set()
    declared_names: set[str] = set()
    for action in _as_list(policy.get("actions")):
        mapping = _as_mapping(action)
        name = mapping.get("action")
        commit = mapping.get("commit")
        if isinstance(name, str) and isinstance(commit, str):
            identity = (name.lower(), commit)
            if identity in declared or name.lower() in declared_names:
                failures.append(
                    _failure(
                        "tooling-action-duplicate",
                        "duplicate action source policy entry",
                        ACTIONS_POLICY_PATH,
                    )
                )
            declared.add(identity)
            declared_names.add(name.lower())
    local_workflows = _string_set(policy.get("local_workflows"))

    workflow_paths = [
        path
        for path in tracked_paths
        if path.startswith(".github/workflows/") and Path(path).suffix in {".yml", ".yaml"}
    ]
    observed: set[tuple[str, str]] = set()
    observed_local_workflows: set[str] = set()
    for path in workflow_paths:
        text = _safe_text(repo_root, path)
        if text is None:
            failures.append(
                _failure(
                    "tooling-action-scan",
                    "workflow action sources could not be read safely",
                    path,
                )
            )
            continue
        try:
            workflow = yaml.safe_load(text)
        except yaml.YAMLError:
            failures.append(
                _failure(
                    "tooling-action-scan",
                    "workflow action sources could not be parsed safely",
                    path,
                )
            )
            continue
        values, invalid_uses = _walk_mapping_values(workflow, "uses")
        if invalid_uses:
            failures.append(
                _failure(
                    "tooling-action-source",
                    "workflow contains a non-scalar or empty action source",
                    path,
                )
            )
        for value in values:
            if value.startswith("./"):
                observed_local_workflows.add(value)
                if value not in local_workflows:
                    failures.append(
                        _failure(
                            "tooling-action-unowned",
                            "local reusable workflow is not policy-owned",
                            path,
                        )
                    )
                continue
            action_name, separator, selector = value.rpartition("@")
            if not action_name or action_name.startswith(("docker://", "http://", "https://")):
                failures.append(
                    _failure(
                        "tooling-action-source",
                        "workflow action source uses an unsupported identity form",
                        path,
                    )
                )
                continue
            observed.add((action_name.lower(), selector))
            if not separator or not _SHA40_RE.fullmatch(selector):
                failures.append(
                    _failure(
                        "tooling-action-mutable",
                        "workflow action is not pinned to a full commit",
                        path,
                    )
                )
            if (action_name.lower(), selector) not in declared:
                failures.append(
                    _failure(
                        "tooling-action-unowned",
                        "workflow action source is not policy-owned",
                        path,
                    )
                )
    for _unused in sorted(declared - observed):
        failures.append(
            _failure(
                "tooling-action-stale",
                "action policy contains an unused source reference",
                ACTIONS_POLICY_PATH,
            )
        )
    for _unused in sorted(local_workflows - observed_local_workflows):
        failures.append(
            _failure(
                "tooling-action-stale",
                "action policy contains an unused local workflow reference",
                ACTIONS_POLICY_PATH,
            )
        )
    return failures


def _selector_failures(
    repo_root: Path,
    documents: Mapping[str, dict[str, Any]],
    tracked_paths: Sequence[str],
) -> list[PolicyFailure]:
    lock = documents.get(ARTIFACT_LOCK_PATH)
    bindings = documents.get(SELECTOR_BINDINGS_PATH)
    if lock is None or bindings is None:
        return []
    versions = {
        artifact.get("artifact_id"): artifact.get("version")
        for artifact in _as_list(lock.get("artifacts"))
        if isinstance(artifact, Mapping)
        and isinstance(artifact.get("artifact_id"), str)
        and isinstance(artifact.get("version"), str)
    }
    failures: list[PolicyFailure] = []
    seen_bindings: set[str] = set()
    for binding in _as_list(bindings.get("bindings")):
        mapping = _as_mapping(binding)
        binding_id = mapping.get("binding_id")
        if isinstance(binding_id, str):
            if binding_id in seen_bindings:
                failures.append(
                    _failure(
                        "tooling-selector-binding-duplicate",
                        "duplicate selector binding",
                        SELECTOR_BINDINGS_PATH,
                    )
                )
            seen_bindings.add(binding_id)
        artifact_id = mapping.get("artifact_id")
        selector = versions.get(artifact_id)
        if not isinstance(selector, str):
            failures.append(
                _failure(
                    "tooling-selector-authority",
                    "selector binding names an unknown artifact",
                    SELECTOR_BINDINGS_PATH,
                )
            )
            continue
        for consumer in _as_list(mapping.get("consumers")):
            consumer_mapping = _as_mapping(consumer)
            path = consumer_mapping.get("path")
            template = consumer_mapping.get("template")
            if not isinstance(path, str) or not isinstance(template, str):
                continue
            text = _safe_text(repo_root, path)
            expected = template.replace("{selector}", selector)
            if text is None or expected not in text:
                failures.append(
                    _failure(
                        "tooling-selector-drift",
                        "consumer selector differs from lock authority",
                        path,
                    )
                )
    failures.extend(_runtime_selection_failures(repo_root, lock, bindings, tracked_paths))
    failures.extend(_tracked_literal_failures(repo_root, bindings, tracked_paths))
    return failures


def _selection_calls(text: str) -> tuple[set[str], bool]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set(), False
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".", maxsplit=1)[0]
                aliases[local] = alias.name if alias.asname else local
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    selection_aliases: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value_name = _ast_name(node.value) if node.value is not None else None
        if value_name is None:
            continue
        first, separator, remainder = value_name.partition(".")
        resolved_value = (
            f"{aliases[first]}.{remainder}" if separator and first in aliases else aliases.get(first, value_name)
        )
        if resolved_value != "tools.tooling_policy_gate.load_tooling_artifact_selection":
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        selection_aliases.update(target.id for target in targets if isinstance(target, ast.Name))
    artifact_ids: set[str] = set()
    valid = True
    required_keywords = {"artifact_id", "version", "platform_id", "profile_id"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _ast_name(node.func)
        if call_name is None:
            continue
        first, separator, remainder = call_name.partition(".")
        resolved_name = (
            f"{aliases[first]}.{remainder}" if separator and first in aliases else aliases.get(first, call_name)
        )
        if resolved_name != "tools.tooling_policy_gate.load_tooling_artifact_selection" and call_name not in {
            "load_tooling_artifact_selection",
            *selection_aliases,
        }:
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg is not None}
        artifact_node = keywords.get("artifact_id")
        if not required_keywords <= keywords.keys() or "policy_root" in keywords:
            valid = False
            continue
        if not isinstance(artifact_node, ast.Constant) or not isinstance(artifact_node.value, str):
            valid = False
            continue
        artifact_ids.add(artifact_node.value)
    return artifact_ids, valid


def _runtime_selection_failures(
    repo_root: Path,
    lock: Mapping[str, Any],
    bindings: Mapping[str, Any],
    tracked_paths: Sequence[str],
) -> list[PolicyFailure]:
    failures: list[PolicyFailure] = []
    locked_artifact_ids = {
        artifact.get("artifact_id")
        for artifact in _as_list(lock.get("artifacts"))
        if isinstance(artifact, Mapping) and isinstance(artifact.get("artifact_id"), str)
    }
    declared: dict[str, set[str]] = {}
    for selection in _as_list(bindings.get("runtime_selections")):
        mapping = _as_mapping(selection)
        artifact_id = mapping.get("artifact_id")
        if not isinstance(artifact_id, str):
            continue
        if artifact_id in declared:
            failures.append(
                _failure(
                    "tooling-runtime-selection-duplicate",
                    "artifact has more than one runtime selection binding",
                    SELECTOR_BINDINGS_PATH,
                )
            )
        declared.setdefault(artifact_id, set()).update(
            path for path in _as_list(mapping.get("consumers")) if isinstance(path, str)
        )

    observed: dict[str, set[str]] = {}
    for path in tracked_paths:
        if Path(path).suffix != ".py":
            continue
        text = _safe_text(repo_root, path)
        if text is None:
            failures.append(
                _failure(
                    "tooling-runtime-selection-scan",
                    "tracked Python source could not be read safely",
                    path,
                )
            )
            continue
        selected_artifact_ids, valid = _selection_calls(text)
        if not valid:
            failures.append(
                _failure(
                    "tooling-runtime-selection-drift",
                    "selection call must use a literal artifact id and all reviewed dimensions",
                    path,
                )
            )
        for artifact_id in selected_artifact_ids:
            observed.setdefault(artifact_id, set()).add(path)

    for artifact_id in sorted(set(declared) | set(observed)):
        if declared.get(artifact_id, set()) != observed.get(artifact_id, set()):
            failures.append(
                _failure(
                    "tooling-runtime-selection-drift",
                    f"{artifact_id} runtime selection consumers differ from tracked calls",
                    SELECTOR_BINDINGS_PATH,
                )
            )
    if set(declared) != locked_artifact_ids or set(observed) != locked_artifact_ids:
        failures.append(
            _failure(
                "tooling-runtime-selection-coverage",
                "every locked artifact must have exactly one runtime selection binding",
                SELECTOR_BINDINGS_PATH,
            )
        )
    return failures


def _tracked_literal_failures(
    repo_root: Path,
    bindings: Mapping[str, Any],
    tracked_paths: Sequence[str],
) -> list[PolicyFailure]:
    failures: list[PolicyFailure] = []
    seen_ids: set[str] = set()
    for tracked_literal in _as_list(bindings.get("tracked_literals")):
        mapping = _as_mapping(tracked_literal)
        selector_id = mapping.get("selector_id")
        authority_path = mapping.get("authority_path")
        authority_template = mapping.get("authority_template")
        consumer_prefix = mapping.get("consumer_prefix")
        if not all(
            isinstance(value, str)
            for value in (
                selector_id,
                authority_path,
                authority_template,
                consumer_prefix,
            )
        ):
            continue
        if selector_id in seen_ids:
            failures.append(
                _failure(
                    "tooling-selector-binding-duplicate",
                    "duplicate tracked literal binding",
                    SELECTOR_BINDINGS_PATH,
                )
            )
        seen_ids.add(selector_id)
        authority_text = _safe_text(repo_root, authority_path)
        prefix, marker, suffix = authority_template.partition("{selector}")
        if authority_text is None or not marker:
            failures.append(
                _failure(
                    "tooling-selector-authority",
                    f"{selector_id} authority cannot be read",
                    authority_path,
                )
            )
            continue
        authority_pattern = re.compile(re.escape(prefix) + r"([^\r\n]+?)" + re.escape(suffix))
        selectors = set(authority_pattern.findall(authority_text))
        if len(selectors) != 1:
            failures.append(
                _failure(
                    "tooling-selector-authority",
                    f"{selector_id} authority must resolve to exactly one selector",
                    authority_path,
                )
            )
            continue
        selector = selectors.pop()
        consumer_pattern = re.compile(re.escape(consumer_prefix) + r"([A-Za-z0-9._+-]+)")
        for path in tracked_paths:
            if Path(path).suffix not in {
                ".bash",
                ".md",
                ".py",
                ".sh",
                ".toml",
                ".yaml",
                ".yml",
            } and Path(path).name not in {"Makefile"}:
                continue
            text = _safe_text(repo_root, path)
            if text is None:
                continue
            if any(value != selector for value in consumer_pattern.findall(text)):
                failures.append(
                    _failure(
                        "tooling-selector-drift",
                        f"{selector_id} literal differs from its authority",
                        path,
                    )
                )
    return failures


def _ast_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _ast_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _command_tokens(call: ast.Call) -> list[str | None]:
    arguments: Sequence[ast.AST] = (
        call.args[0].elts if call.args and isinstance(call.args[0], (ast.List, ast.Tuple)) else call.args
    )
    tokens: list[str | None] = []
    for argument in arguments:
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            tokens.append(argument.value)
        elif _ast_name(argument) == "sys.executable":
            tokens.append("python")
        else:
            tokens.append(None)
    return tokens


def _tokens_are_acquisition(tokens: Sequence[str | None]) -> bool:
    literals = [token.lower() if token is not None else None for token in tokens]
    if not literals:
        return False
    while literals and literals[0] in {"command", "sudo"}:
        literals.pop(0)
    if not literals:
        return False
    executable = literals[0].rsplit("/", maxsplit=1)[-1] if literals[0] is not None else None
    literals[0] = executable
    if literals[0] in {"curl", "wget"} or (len(literals) >= 2 and literals[1] == "pull"):
        return True
    sequences = (
        ("gh", "release", "download"),
        ("git", "clone"),
        ("uv", "tool", "install"),
        ("uv", "pip", "install"),
        ("pip", "install"),
        ("pip3", "install"),
        ("docker", "pull"),
        ("podman", "pull"),
        ("skopeo", "copy"),
    )
    return any(tuple(literals[: len(sequence)]) == sequence for sequence in sequences)


def _is_command_executor(call_name: str) -> bool:
    if call_name in {
        "os.system",
        "subprocess.Popen",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.run",
    }:
        return True
    receiver, separator, method = call_name.rpartition(".")
    return (
        separator == "."
        and method == "run"
        and receiver.rsplit(".", maxsplit=1)[-1]
        in {
            "nox_session",
            "session",
        }
    )


def _tokens_have_unknown_acquisition(tokens: Sequence[str | None]) -> bool:
    if not tokens or tokens[0] is None:
        return True
    literals = [token.lower() if token is not None else None for token in tokens]
    while literals and literals[0] in {"command", "sudo"}:
        literals.pop(0)
    if not literals or literals[0] is None:
        return True
    executable = literals[0].rsplit("/", maxsplit=1)[-1]
    required_prefixes = {
        "docker": 1,
        "gh": 2,
        "git": 1,
        "pip": 1,
        "pip3": 1,
        "podman": 1,
        "skopeo": 1,
        "uv": 2,
    }
    prefix_length = required_prefixes.get(executable)
    if prefix_length is None:
        return False
    return len(literals) <= prefix_length or any(token is None for token in literals[1 : prefix_length + 1])


def _python_contains_acquisition(text: str) -> tuple[int, bool, int]:
    """Return acquisition count, parse-safety, and unknown-executable count."""

    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return 0, False, 0
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".", maxsplit=1)[0]
                aliases[local] = alias.name if alias.asname else local
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    callable_aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value_name = _ast_name(node.value) if node.value is not None else None
        if value_name is None:
            continue
        first, separator, remainder = value_name.partition(".")
        resolved_value = (
            f"{aliases[first]}.{remainder}" if separator and first in aliases else aliases.get(first, value_name)
        )
        if not _is_command_executor(resolved_value) and resolved_value not in {
            "http.client.HTTPConnection",
            "http.client.HTTPSConnection",
            "tools.http_download.download_bytes",
            "urllib.request.urlopen",
        }:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        callable_aliases.update({target.id: resolved_value for target in targets if isinstance(target, ast.Name)})
    aliases.update(callable_aliases)
    url_openers: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or not isinstance(node.value, ast.Call):
            continue
        factory_name = _ast_name(node.value.func)
        if factory_name is None:
            continue
        factory_first, factory_separator, factory_remainder = factory_name.partition(".")
        resolved_factory = (
            f"{aliases[factory_first]}.{factory_remainder}"
            if factory_separator and factory_first in aliases
            else aliases.get(factory_first, factory_name)
        )
        if resolved_factory != "urllib.request.build_opener":
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        url_openers.update(target.id for target in targets if isinstance(target, ast.Name))
    acquisition_count = 0
    unknown_executable_count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _ast_name(node.func)
        if call_name is None:
            continue
        first, separator, remainder = call_name.partition(".")
        resolved_name = (
            f"{aliases[first]}.{remainder}" if separator and first in aliases else aliases.get(first, call_name)
        )
        if isinstance(node.func, ast.Attribute) and node.func.attr == "open" and isinstance(node.func.value, ast.Call):
            factory_name = _ast_name(node.func.value.func)
            if factory_name is not None:
                factory_first, factory_separator, factory_remainder = factory_name.partition(".")
                resolved_factory = (
                    f"{aliases[factory_first]}.{factory_remainder}"
                    if factory_separator and factory_first in aliases
                    else aliases.get(factory_first, factory_name)
                )
                if resolved_factory == "urllib.request.build_opener":
                    acquisition_count += 1
                    continue
        if resolved_name in {
            "http.client.HTTPConnection",
            "http.client.HTTPSConnection",
            "tools.http_download.download_bytes",
            "urllib.request.urlopen",
        }:
            acquisition_count += 1
            continue
        if resolved_name.endswith(".open") and resolved_name.removesuffix(".open") in url_openers:
            acquisition_count += 1
            continue
        if first in aliases and resolved_name in {
            "aiohttp.request",
            "httpx.get",
            "httpx.request",
            "httpx.stream",
            "requests.get",
            "requests.request",
        }:
            acquisition_count += 1
            continue
        if _is_command_executor(resolved_name):
            tokens = _command_tokens(node)
            literal_command = tokens[0] if len(tokens) == 1 else None
            if _tokens_are_acquisition(tokens) or (
                literal_command is not None and _ACQUISITION_COMMAND_RE.search(literal_command)
            ):
                acquisition_count += 1
                continue
            if _tokens_have_unknown_acquisition(tokens):
                unknown_executable_count += 1
    return acquisition_count, True, unknown_executable_count


def _structured_contains_acquisition(text: str, path: str) -> tuple[int, bool, int]:
    suffix = Path(path).suffix
    if suffix == ".py":
        return _python_contains_acquisition(text)
    if suffix in {".yaml", ".yml"}:
        try:
            yaml.safe_load(text)
        except yaml.YAMLError:
            return 0, False, 0
    elif suffix == ".toml":
        try:
            tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return 0, False, 0
    return len(_ACQUISITION_COMMAND_RE.findall(text)), True, 0


def _is_acquisition_scan_candidate(path: str) -> bool:
    candidate = Path(path)
    if candidate.suffix in {".yaml", ".yml"}:
        return (
            path.startswith(".github/workflows/")
            or candidate.name in {"action.yaml", "action.yml", ".pre-commit-config.yaml"}
            or path == ".ground-control.yaml"
        )
    return candidate.suffix in _SCANNED_SUFFIXES or candidate.name in _SCANNED_NAMES


def _inventory_failures(
    repo_root: Path,
    documents: Mapping[str, dict[str, Any]],
    tracked_paths: Sequence[str],
) -> list[PolicyFailure]:
    coverage = documents.get(INVENTORY_COVERAGE_PATH)
    if coverage is None:
        return []
    failures: list[PolicyFailure] = []
    admission = documents.get(ADMISSION_POLICY_PATH) or {}
    policies = {
        item["policy_id"]: item
        for item in _as_list(admission.get("policies"))
        if isinstance(item, Mapping) and isinstance(item.get("policy_id"), str)
    }
    rows = _as_list(coverage.get("rows"))
    ids = [
        row.get("inventory_id") for row in rows if isinstance(row, Mapping) and isinstance(row.get("inventory_id"), str)
    ]
    seen: set[str] = set()
    for inventory_id in ids:
        if inventory_id in seen:
            failures.append(
                _failure(
                    "tooling-inventory-duplicate",
                    "inventory row is covered more than once",
                    INVENTORY_COVERAGE_PATH,
                )
            )
        seen.add(inventory_id)
    for row in rows:
        mapping = _as_mapping(row)
        inventory_id = mapping.get("inventory_id")
        if not isinstance(inventory_id, str):
            continue
        failures.extend(
            _policy_join_failures(
                policy_refs=_string_set(mapping.get("policy_refs")),
                expected_subjects=_string_set(mapping.get("subjects")),
                provided_evidence=_string_set(mapping.get("evidence_refs")),
                policies=policies,
                path=INVENTORY_COVERAGE_PATH,
                context=f"inventory row {inventory_id}",
                require_all_evidence_per_policy=False,
            )
        )
    missing = _EXPECTED_INVENTORY_IDS - seen
    extra = seen - _EXPECTED_INVENTORY_IDS
    if missing:
        failures.append(
            _failure(
                "tooling-inventory-missing",
                f"{len(missing)} package-artifact inventory rows lack coverage",
                INVENTORY_COVERAGE_PATH,
            )
        )
    if extra:
        failures.append(
            _failure(
                "tooling-inventory-extra",
                f"{len(extra)} unknown package-artifact inventory rows are present",
                INVENTORY_COVERAGE_PATH,
            )
        )

    owned_paths: dict[str, int] = {}
    for acquisition in _as_list(coverage.get("acquisition_paths")):
        mapping = _as_mapping(acquisition)
        path = mapping.get("path")
        inventory_id = mapping.get("inventory_id")
        site_count = mapping.get("site_count")
        if isinstance(path, str) and isinstance(inventory_id, str) and inventory_id in seen:
            if path in owned_paths:
                failures.append(
                    _failure(
                        "tooling-acquisition-duplicate",
                        "acquisition path has more than one disposition",
                        path,
                    )
                )
            if isinstance(site_count, int) and not isinstance(site_count, bool):
                owned_paths[path] = site_count
    observed_paths: dict[str, int] = {}
    for path in tracked_paths:
        if not _is_acquisition_scan_candidate(path):
            continue
        text = _safe_text(repo_root, path)
        if text is None:
            failures.append(
                _failure(
                    "tooling-acquisition-scan",
                    "possible acquisition surface could not be read safely",
                    path,
                )
            )
            continue
        acquisition_count, parsed, unknown_executable_count = _structured_contains_acquisition(text, path)
        if not parsed:
            failures.append(
                _failure(
                    "tooling-acquisition-scan",
                    "possible acquisition surface could not be parsed safely",
                    path,
                )
            )
            continue
        observed_count = acquisition_count + unknown_executable_count
        if observed_count:
            observed_paths[path] = observed_count
        if acquisition_count and path not in owned_paths:
            failures.append(
                _failure(
                    "tooling-acquisition-unowned",
                    "artifact acquisition path lacks an inventory disposition",
                    path,
                )
            )
        if unknown_executable_count and path not in owned_paths:
            failures.append(
                _failure(
                    "tooling-acquisition-unknown",
                    "dynamic executable form lacks an explicit inventory disposition",
                    path,
                )
            )
    for path in sorted(set(owned_paths) - set(observed_paths)):
        failures.append(
            _failure(
                "tooling-acquisition-stale",
                "inventory disposition does not match a discovered acquisition surface",
                path,
            )
        )
    for path in sorted(set(owned_paths) & set(observed_paths)):
        if owned_paths[path] != observed_paths[path]:
            failures.append(
                _failure(
                    "tooling-acquisition-drift",
                    "discovered acquisition-site count differs from its explicit disposition",
                    path,
                )
            )
    return failures


def evaluate_tooling_artifact_policy(
    repo_root: Path = REPO_ROOT,
    *,
    tracked_paths: Sequence[str] | None = None,
) -> list[PolicyFailure]:
    """Return deterministic policy failures without performing acquisition."""

    documents, failures = _load_documents(repo_root)
    if tracked_paths is None:
        try:
            paths = _tracked_paths(repo_root)
        except (OSError, UnicodeError, subprocess.SubprocessError):
            failures.append(
                _failure(
                    "tooling-git-scan",
                    "tracked repository paths could not be enumerated",
                )
            )
            paths = []
    else:
        paths = sorted(set(tracked_paths))
    failures.extend(_artifact_failures(repo_root, documents))
    failures.extend(_action_failures(repo_root, documents, paths))
    failures.extend(_selector_failures(repo_root, documents, paths))
    failures.extend(_inventory_failures(repo_root, documents, paths))
    return sorted(set(failures), key=lambda item: (item.path or "", item.rule_id, item.message))


def select_tooling_artifact(
    repo_root: Path,
    *,
    artifact_id: str,
    version: str,
    platform_id: str,
    profile_id: str,
) -> dict[str, Any]:
    """Return one fully validated artifact/platform selection from the lock."""

    failures = evaluate_tooling_artifact_policy(repo_root)
    if failures:
        rendered = "\n".join(failure.render() for failure in failures)
        raise ValueError(f"development artifact policy is invalid:\n{rendered}")
    lock = load_bounded_json_object(repo_root, ARTIFACT_LOCK_PATH, max_bytes=_MAX_JSON_BYTES)
    matches: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    canonical_platform = normalize_platform_id(platform_id)
    for artifact in _as_list(lock.get("artifacts")):
        if (
            not isinstance(artifact, Mapping)
            or artifact.get("artifact_id") != artifact_id
            or artifact.get("version") != version
        ):
            continue
        for platform in _as_list(artifact.get("platforms")):
            if (
                isinstance(platform, Mapping)
                and isinstance(platform.get("platform_id"), str)
                and normalize_platform_id(platform["platform_id"]) == canonical_platform
                and profile_id in _string_set(platform.get("profile_ids"))
            ):
                matches.append((artifact, platform))
    if len(matches) != 1:
        raise ValueError(
            "requested artifact version, platform, and profile must resolve to exactly one reviewed lock entry"
        )
    artifact, platform = matches[0]
    return {
        "artifact_id": artifact["artifact_id"],
        "artifact_class": artifact["artifact_class"],
        "version": artifact["version"],
        "source": artifact["source"],
        "platform": platform,
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true", help="emit structured failures")
    parser.add_argument("--select-artifact")
    parser.add_argument("--version")
    parser.add_argument("--platform-id")
    parser.add_argument("--profile-id")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    selection_args = (
        args.select_artifact,
        args.version,
        args.platform_id,
        args.profile_id,
    )
    if any(selection_args):
        if not all(selection_args):
            print(
                "artifact selection requires artifact, version, platform, and profile",
                file=sys.stderr,
            )
            return 2
        try:
            selection = select_tooling_artifact(
                args.repo_root,
                artifact_id=args.select_artifact,
                version=args.version,
                platform_id=args.platform_id,
                profile_id=args.profile_id,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(selection, sort_keys=True, separators=(",", ":")))
        return 0
    failures = evaluate_tooling_artifact_policy(args.repo_root)
    if not failures:
        return 0
    if args.json:
        print(failures_to_json(failures))
    else:
        for failure in failures:
            print(failure.render(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
