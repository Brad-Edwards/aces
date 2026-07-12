"""Canonical identity and bounded byte binding for associated artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, BinaryIO

import rfc8785
from aces_sdl import canonical_sdl_digest
from aces_sdl.scenario import Scenario
from blake3 import blake3

from .contracts import (
    AssociatedArtifactManifestModel,
    ExperimentApparatusContextModel,
    ExperimentRunModel,
    ExperimentSpecModel,
    ExperimentStudyModel,
    ExperimentTaskModel,
)
from .diagnostics import Diagnostic, Severity

_DOMAIN = "associated-artifact"
_CHUNK_SIZE = 64 * 1024


@dataclass(frozen=True)
class AssociatedArtifactValidationLimits:
    """Caller policy limits for one manifest validation."""

    max_artifacts: int = 1024
    max_artifact_bytes: int = 1024 * 1024 * 1024
    max_total_bytes: int = 4 * 1024 * 1024 * 1024

    def __post_init__(self) -> None:
        if self.max_artifacts < 1 or self.max_artifact_bytes < 0 or self.max_total_bytes < 0:
            raise ValueError("associated-artifact validation limits must be non-negative and allow an artifact")


def _normalized_canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {key: _normalized_canonical_value(item) for key, item in value.items()}
        checksum = normalized.get("checksum")
        if isinstance(checksum, dict) and isinstance(checksum.get("value"), str):
            checksum["value"] = checksum["value"].casefold()
        if isinstance(normalized.get("ref_digest"), str):
            normalized["ref_digest"] = normalized["ref_digest"].casefold()
        return normalized
    if isinstance(value, list):
        return [_normalized_canonical_value(item) for item in value]
    return value


def associated_artifact_set_bytes(manifest: AssociatedArtifactManifestModel) -> bytes:
    """Return RFC 8785 bytes for the abstract parent-plus-reference set."""

    projection = {
        "profile": manifest.canonicalization_profile,
        "scope": manifest.scope,
        "parent_ref": manifest.parent_ref.model_dump(mode="json", exclude_none=True),
        "artifacts": {
            artifact_id: artifact.model_dump(mode="json", exclude_none=True)
            for artifact_id, artifact in manifest.artifacts.items()
        },
    }
    try:
        return rfc8785.dumps(_normalized_canonical_value(projection))
    except rfc8785.CanonicalizationError as exc:
        raise ValueError("associated-artifact set canonicalization failed") from exc


def associated_artifact_set_digest(manifest: AssociatedArtifactManifestModel) -> str:
    """Derive the v1 lowercase SHA-256 identity for a manifest's artifact set."""

    digest = hashlib.sha256(associated_artifact_set_bytes(manifest)).hexdigest()
    return f"sha256:{digest}"


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def load_associated_artifact_manifest_json(source: str | bytes | bytearray) -> AssociatedArtifactManifestModel:
    """Parse one manifest while rejecting duplicate JSON members before construction."""

    payload = json.loads(source, object_pairs_hook=_reject_duplicate_members)
    return AssociatedArtifactManifestModel.model_validate(payload)


def _diagnostic(code: str, address: str, message: str) -> Diagnostic:
    return Diagnostic(code=code, domain=_DOMAIN, address=address, message=message, severity=Severity.ERROR)


def _parent_matches(manifest: AssociatedArtifactManifestModel, parent: object) -> bool:
    reference = manifest.parent_ref
    if reference.ref_kind in {"scenario", "scenario-snapshot"}:
        if not isinstance(parent, Scenario) or parent.name != reference.ref_id:
            return False
        if reference.ref_kind == "scenario":
            return True
        if reference.ref_version is not None and parent.version != reference.ref_version:
            return False
        if reference.ref_digest is not None:
            return canonical_sdl_digest(parent).value.casefold() == reference.ref_digest.casefold()
        return True

    parent_shapes: dict[str, tuple[type[object], str, str]] = {
        "task": (ExperimentTaskModel, "task_id", "task_version"),
        "authoring-input": (ExperimentSpecModel, "spec_id", "spec_version"),
        "apparatus-context": (ExperimentApparatusContextModel, "apparatus_context_id", "context_version"),
        "run": (ExperimentRunModel, "run_id", "run_version"),
        "study": (ExperimentStudyModel, "study_id", "study_version"),
    }
    expected_type, id_field, version_field = parent_shapes[reference.ref_kind]
    if not isinstance(parent, expected_type) or getattr(parent, id_field) != reference.ref_id:
        return False
    return reference.ref_version is None or getattr(parent, version_field) == reference.ref_version


def _read_and_hash(reader: BinaryIO, algorithm: str, declared_size: int) -> tuple[int, str] | None:
    if algorithm == "blake3":
        digest = blake3()
    else:
        try:
            digest = hashlib.new(algorithm)
        except ValueError:
            return None
    total = 0
    while total <= declared_size:
        chunk = reader.read(min(_CHUNK_SIZE, declared_size + 1 - total))
        if not isinstance(chunk, bytes):
            raise TypeError("artifact reader must return bytes")
        if not chunk:
            break
        digest.update(chunk)
        total += len(chunk)
    return total, digest.hexdigest()


def validate_associated_artifact_manifest(
    manifest: AssociatedArtifactManifestModel,
    *,
    parent: object,
    artifact_readers: Mapping[str, BinaryIO],
    limits: AssociatedArtifactValidationLimits | None = None,
) -> tuple[Diagnostic, ...]:
    """Validate parent/set identity and every payload through bounded readers.

    The caller acquires and immutably stages payloads. This function performs no
    URI fetching, directory traversal, archive extraction, or ambient lookup.
    """

    effective_limits = limits or AssociatedArtifactValidationLimits()
    diagnostics: list[Diagnostic] = []
    if len(manifest.artifacts) > effective_limits.max_artifacts:
        diagnostics.append(
            _diagnostic(
                "associated-artifact.resource-limit-exceeded",
                "#/artifacts",
                "artifact count exceeds the caller-supplied validation limit",
            )
        )
    declared_total = sum(artifact.size_bytes for artifact in manifest.artifacts.values())
    oversized = [
        artifact_id
        for artifact_id, artifact in manifest.artifacts.items()
        if artifact.size_bytes > effective_limits.max_artifact_bytes
    ]
    if oversized or declared_total > effective_limits.max_total_bytes:
        diagnostics.append(
            _diagnostic(
                "associated-artifact.resource-limit-exceeded",
                "#/artifacts",
                "declared artifact bytes exceed the caller-supplied validation limits",
            )
        )
    if diagnostics:
        return tuple(diagnostics)

    if not _parent_matches(manifest, parent):
        diagnostics.append(
            _diagnostic(
                "associated-artifact.parent-mismatch",
                "#/parent_ref",
                "the supplied concrete parent does not match parent_ref",
            )
        )
    if associated_artifact_set_digest(manifest) != manifest.set_digest:
        diagnostics.append(
            _diagnostic(
                "associated-artifact.set-digest-mismatch",
                "#/set_digest",
                "set_digest does not match the canonical parent-plus-artifact-reference set",
            )
        )

    manifest_ids = set(manifest.artifacts)
    supplied_ids = set(artifact_readers)
    for artifact_id in sorted(manifest_ids - supplied_ids):
        diagnostics.append(
            _diagnostic(
                "associated-artifact.payload-binding-missing",
                f"#/artifacts/{artifact_id}",
                "no concrete byte reader was supplied for this artifact",
            )
        )
    for artifact_id in sorted(supplied_ids - manifest_ids):
        diagnostics.append(
            _diagnostic(
                "associated-artifact.payload-binding-unexpected",
                "#/artifacts",
                f"a byte reader was supplied for undeclared artifact id {artifact_id!r}",
            )
        )

    for artifact_id in sorted(manifest_ids & supplied_ids):
        artifact = manifest.artifacts[artifact_id]
        reader = artifact_readers[artifact_id]
        if not hasattr(reader, "read"):
            diagnostics.append(
                _diagnostic(
                    "associated-artifact.payload-binding-invalid",
                    f"#/artifacts/{artifact_id}",
                    "the supplied binding is not a concrete byte reader",
                )
            )
            continue
        try:
            result = _read_and_hash(reader, artifact.checksum.algorithm, artifact.size_bytes)
        except (OSError, TypeError, ValueError):
            diagnostics.append(
                _diagnostic(
                    "associated-artifact.payload-binding-invalid",
                    f"#/artifacts/{artifact_id}",
                    "the concrete byte reader failed without yielding a valid bounded byte stream",
                )
            )
            continue
        if result is None:
            diagnostics.append(
                _diagnostic(
                    "associated-artifact.checksum-algorithm-unsupported",
                    f"#/artifacts/{artifact_id}/checksum/algorithm",
                    "the checksum algorithm is unavailable to this validator",
                )
            )
            continue
        actual_size, actual_checksum = result
        if actual_size != artifact.size_bytes:
            diagnostics.append(
                _diagnostic(
                    "associated-artifact.payload-size-mismatch",
                    f"#/artifacts/{artifact_id}/size_bytes",
                    "concrete payload size does not match size_bytes",
                )
            )
        if actual_checksum.casefold() != artifact.checksum.value.casefold():
            diagnostics.append(
                _diagnostic(
                    "associated-artifact.payload-checksum-mismatch",
                    f"#/artifacts/{artifact_id}/checksum",
                    "concrete payload bytes do not match the declared checksum",
                )
            )
    return tuple(diagnostics)


__all__ = [
    "AssociatedArtifactValidationLimits",
    "associated_artifact_set_bytes",
    "associated_artifact_set_digest",
    "load_associated_artifact_manifest_json",
    "validate_associated_artifact_manifest",
]
