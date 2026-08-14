"""Implementation-surface identity and artifact re-execution validation."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from tools.policy.common import PolicyFailure, load_bounded_json_object, safe_repo_path
from tools.specification_coverage._keys import (
    _ARTIFACT_KEYS,
    _EXECUTION_SNAPSHOT_PATH,
    _IMPLEMENTATION_SURFACE_KEYS,
    _MAX_FILE_BYTES,
    _SHA256_RE,
    HISTORICAL_IMPLEMENTATION_SURFACE_PATHS,
    IMPLEMENTATION_SURFACE_PATHS,
    RENAMED_ARTIFACT_DIGESTS,
)
from tools.specification_coverage._primitives import (
    _bounded_list,
    _exact_keys,
    _failure,
    _record_ids,
    _sha256,
)


def _surface_entry_failures(
    repo_root: Path,
    surface: dict[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    surface_id = surface.get("surface_id")
    expected_path = IMPLEMENTATION_SURFACE_PATHS.get(surface_id)
    recorded_path = surface.get("path")
    if recorded_path not in {
        expected_path,
        HISTORICAL_IMPLEMENTATION_SURFACE_PATHS.get(surface_id),
    }:
        failures.append(
            _failure(
                "specification-coverage-implementation-identity",
                f"implementation surface {surface_id!r} path is not the registered execution boundary",
                path,
            )
        )
        return
    resolved = safe_repo_path(repo_root, expected_path) if expected_path is not None else None
    if resolved is None or not resolved.is_dir():
        failures.append(
            _failure(
                "specification-coverage-implementation-identity",
                f"implementation surface {surface_id!r} is unsafe or missing",
                path,
            )
        )
        return
    expected_sha = surface.get("content_sha256")
    if not isinstance(expected_sha, str) or not _SHA256_RE.fullmatch(expected_sha):
        failures.append(
            _failure(
                "specification-coverage-implementation-identity",
                f"implementation surface {surface_id!r} historical digest is invalid",
                expected_path,
            )
        )


def _validate_implementation_surfaces(
    repo_root: Path,
    snapshot: dict[str, object],
    failures: list[PolicyFailure],
) -> None:
    path = _EXECUTION_SNAPSHOT_PATH
    surfaces = _bounded_list(
        snapshot.get("implementation_surfaces"),
        failures,
        rule_id="specification-coverage-implementation-identity",
        label="implementation_surfaces",
        path=path,
    )
    surface_ids = _record_ids(
        surfaces,
        "surface_id",
        failures,
        rule_id="specification-coverage-implementation-identity",
        label="implementation_surfaces",
        path=path,
    )
    if surface_ids != set(IMPLEMENTATION_SURFACE_PATHS):
        failures.append(
            _failure(
                "specification-coverage-implementation-identity",
                "implementation surfaces must bind every executed production package exactly once",
                path,
            )
        )
    for index, surface in enumerate(surfaces):
        if _exact_keys(
            surface,
            _IMPLEMENTATION_SURFACE_KEYS,
            failures,
            rule_id="specification-coverage-implementation-identity",
            label=f"implementation_surfaces[{index}]",
            path=path,
        ):
            _surface_entry_failures(repo_root, surface, failures, path)


def _execute_sdl_artifact(path: Path) -> dict[str, object]:
    from raes import (
        admit_instantiated_scenario,
        instantiate_scenario,
        parse_sdl_file,
    )
    from raes_processor.compiler import compile_runtime_model

    authored = parse_sdl_file(path)
    instantiated = instantiate_scenario(authored)
    admitted = admit_instantiated_scenario(instantiated.model_dump(mode="json", by_alias=True))
    compiled = compile_runtime_model(admitted)
    error_diagnostics = [
        diagnostic
        for diagnostic in compiled.diagnostics
        if str(getattr(diagnostic.severity, "value", diagnostic.severity)).lower() == "error"
    ]
    if error_diagnostics:
        raise ValueError("compiled artifact contains error diagnostics")
    return {
        "authored": authored.model_dump(mode="json", by_alias=True),
        "semantic": authored.model_dump(mode="json", by_alias=True),
        "instantiated": admitted.model_dump(mode="json", by_alias=True),
        "compiled": asdict(compiled),
    }


def _executed_contract_payload(kind: str, payload: dict[str, object]) -> dict[str, object]:
    if kind == "experiment-task":
        from raes_contracts.contracts import ExperimentTaskModel

        return {"contract": ExperimentTaskModel.model_validate(payload).model_dump(mode="json", by_alias=True)}
    if kind == "experiment-apparatus-context":
        from raes_contracts.contracts import ExperimentApparatusContextModel

        return {
            "contract": ExperimentApparatusContextModel.model_validate(payload).model_dump(mode="json", by_alias=True)
        }
    if kind == "backend-profile":
        from raes_contracts.backend_profiles import BackendProfileModel

        return {"profile-manifest": BackendProfileModel.model_validate(payload).model_dump(mode="json", by_alias=True)}
    raise ValueError(f"unsupported artifact kind {kind!r}")


def _execute_artifact(repo_root: Path, kind: str, path: Path) -> dict[str, object]:
    if kind == "sdl":
        return _execute_sdl_artifact(path)
    if kind == "documentation":
        return {}
    payload = load_bounded_json_object(repo_root, path.relative_to(repo_root).as_posix(), max_bytes=_MAX_FILE_BYTES)
    return _executed_contract_payload(kind, payload)


def _artifact_digest_failures(
    artifact: dict[str, object],
    artifact_path: str,
    resolved: Path,
    failures: list[PolicyFailure],
) -> None:
    expected_sha = artifact.get("sha256")
    if not isinstance(expected_sha, str) or not _SHA256_RE.fullmatch(expected_sha):
        failures.append(
            _failure(
                "specification-coverage-artifact-digest",
                "artifact digest is invalid",
                artifact_path,
            )
        )
        return
    actual_sha = _sha256(resolved)
    renamed_digests = RENAMED_ARTIFACT_DIGESTS.get(artifact_path)
    if actual_sha != expected_sha and renamed_digests != (
        expected_sha,
        actual_sha,
    ):
        failures.append(
            _failure(
                "specification-coverage-artifact-digest",
                "artifact digest is stale",
                artifact_path,
            )
        )


def _record_artifact_execution(
    repo_root: Path,
    artifact: dict[str, object],
    artifact_path: str,
    resolved: Path,
    executed: dict[str, dict[str, object]],
    failures: list[PolicyFailure],
) -> None:
    kind = artifact.get("kind")
    if not isinstance(kind, str):
        failures.append(
            _failure(
                "specification-coverage-artifacts",
                "artifact kind is invalid",
                artifact_path,
            )
        )
        return
    try:
        executed[artifact_path] = _execute_artifact(repo_root, kind, resolved)
    except (OSError, ValueError, TypeError) as exc:
        failures.append(
            _failure(
                "specification-coverage-artifact-execution",
                f"artifact {artifact.get('artifact_id')!r} failed its production boundary: {exc}",
                artifact_path,
            )
        )


def _validate_artifacts(
    repo_root: Path,
    snapshot: dict[str, object],
    failures: list[PolicyFailure],
) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    path = _EXECUTION_SNAPSHOT_PATH
    artifacts = _bounded_list(
        snapshot.get("artifacts"),
        failures,
        rule_id="specification-coverage-artifacts",
        label="artifacts",
        path=path,
    )
    artifact_ids = _record_ids(
        artifacts,
        "artifact_id",
        failures,
        rule_id="specification-coverage-artifacts",
        label="artifacts",
        path=path,
    )
    by_path: dict[str, dict[str, object]] = {}
    executed: dict[str, dict[str, object]] = {}
    for index, artifact in enumerate(artifacts):
        if not _exact_keys(
            artifact,
            _ARTIFACT_KEYS,
            failures,
            rule_id="specification-coverage-artifacts",
            label=f"artifacts[{index}]",
            path=path,
        ):
            continue
        artifact_path = artifact.get("path")
        resolved = safe_repo_path(repo_root, artifact_path) if isinstance(artifact_path, str) else None
        if resolved is None or not resolved.is_file():
            failures.append(
                _failure(
                    "specification-coverage-artifact-path",
                    f"artifact {artifact.get('artifact_id')!r} path is unsafe or missing",
                    path,
                )
            )
            continue
        if artifact_path in by_path:
            failures.append(_failure("specification-coverage-artifacts", "duplicate artifact path", path))
        else:
            by_path[artifact_path] = artifact
        _artifact_digest_failures(artifact, artifact_path, resolved, failures)
        _record_artifact_execution(repo_root, artifact, artifact_path, resolved, executed, failures)
    return (
        {
            artifact_id: next(
                (item for item in artifacts if isinstance(item, dict) and item.get("artifact_id") == artifact_id),
                {},
            )
            for artifact_id in artifact_ids
        },
        executed,
    )
