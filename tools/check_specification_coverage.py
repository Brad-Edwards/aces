#!/usr/bin/env python3
"""Validate the standardized specification-coverage evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.policy.common import (  # noqa: E402
    PolicyFailure,
    load_bounded_json_object,
    safe_repo_path,
)

MANIFEST_PATH = "docs/research/specification-coverage/bundle-manifest.json"
PROTOCOL_PATH = "docs/research/specification-coverage/protocol-v1.json"
EXPECTED_CLASSIFICATIONS = {
    "directly-expressible",
    "profile-or-manifest-constraint",
    "deliberately-backend-specific",
    "missing",
}
EXPECTED_STRATA = {
    "cyber-range-survey",
    "agent-benchmark",
    "scenario-dsl",
    "simulation-emulation-platform",
}
IMPLEMENTATION_SURFACE_PATHS = {
    "contract-models": "implementations/python/packages/aces_contracts",
    "processor-pipeline": "implementations/python/packages/aces_processor",
    "sdl-pipeline": "implementations/python/packages/aces_sdl",
}

_MAX_FILE_BYTES = 2 * 1024 * 1024
_MAX_CATALOG_ITEMS = 256
_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "client_secret",
    "key",
    "password",
    "secret",
    "sig",
    "signature",
    "token",
}

_MANIFEST_KEYS = {
    "bundle_id",
    "revision",
    "protocol_path",
    "protocol_sha256",
    "snapshot_path",
    "snapshot_sha256",
    "analysis_path",
    "analysis_sha256",
}
_PROTOCOL_KEYS = {
    "protocol_id",
    "revision",
    "registered_at",
    "title",
    "claim",
    "research_question",
    "evidence_status_values",
    "classification_rules",
    "coverage_strata",
    "artifact_stages",
    "sources",
    "requests",
    "carriers",
    "concepts",
    "execution_rules",
    "objective_pass_criteria",
    "objective_fail_criteria",
    "validity_threats",
    "amendment_log",
}
_STRATUM_KEYS = {"stratum_id", "label", "minimum_sources"}
_STAGE_KEYS = {"stage_id", "canonical_entrypoint"}
_SOURCE_KEYS = {
    "source_id",
    "stratum_id",
    "kind",
    "title",
    "locator",
    "version",
    "revision",
    "artifact_path",
    "content_sha256",
}
_REQUEST_KEYS = {
    "request_id",
    "stratum_id",
    "source_refs",
    "title",
    "paraphrase",
    "concept_ids",
}
_CARRIER_KEYS = {"carrier_id", "kind", "artifact_id", "portable", "description"}
_CONCEPT_KEYS = {
    "concept_id",
    "request_id",
    "title",
    "meaning",
    "atomic",
    "load_bearing",
    "expected_classification",
    "expected_carrier_id",
    "artifact_stage_ids",
    "success_rule",
    "fail_rule",
}
_EXECUTION_RULE_KEYS = {
    "stage_outcomes",
    "validation_strength_values",
    "missing_concepts_force_partial",
    "load_bearing_failure_forces_refuted",
    "unallowed_backend_leakage_forces_refuted",
    "normal_execution_network_access",
}

_SNAPSHOT_KEYS = {
    "snapshot_id",
    "snapshot_revision",
    "protocol_revision",
    "protocol_sha256",
    "captured_at",
    "aces_revision",
    "implementation_surfaces",
    "execution_status",
    "artifacts",
    "concept_results",
    "deviations",
    "limitations",
}
_IMPLEMENTATION_SURFACE_KEYS = {"surface_id", "path", "content_sha256"}
_ARTIFACT_KEYS = {"artifact_id", "kind", "path", "sha256", "validator"}
_CONCEPT_RESULT_KEYS = {
    "concept_id",
    "classification",
    "typed_pointer",
    "rationale",
    "stage_results",
    "backend_vocabulary_occurrences",
    "completeness_disposition",
    "backend_support",
}
_STAGE_RESULT_KEYS = {
    "stage_id",
    "outcome",
    "artifact_path",
    "pointer",
    "diagnostic_codes",
    "validation_strength",
    "note",
}
_BACKEND_OCCURRENCE_KEYS = {"term", "artifact_path", "pointer", "reason", "allowed"}

_ANALYSIS_KEYS = {
    "analysis_id",
    "protocol_revision",
    "snapshot_id",
    "snapshot_sha256",
    "generated_at",
    "execution_status",
    "classification_counts",
    "load_bearing_results",
    "request_results",
    "backend_leakage",
    "evidence_status",
    "claim",
    "plain_language_outcome",
    "limitations",
}
_REQUEST_RESULT_KEYS = {
    "request_id",
    "status",
    "concept_count",
    "missing_count",
    "failed_stage_count",
}
_CLAIM_KEYS = {
    "claim_id",
    "statement",
    "threats_to_validity",
    "falsification_protocol",
    "objective_pass_criteria",
    "objective_fail_criteria",
    "allowed_evidence",
    "disallowed_evidence",
    "evidence_artifacts",
}


def _failure(rule_id: str, message: str, path: str | None = None) -> PolicyFailure:
    return PolicyFailure(rule_id, message, path)


def _exact_keys(
    value: object,
    expected: set[str],
    failures: list[PolicyFailure],
    *,
    rule_id: str,
    label: str,
    path: str,
) -> bool:
    if not isinstance(value, dict):
        failures.append(_failure(rule_id, f"{label} must be an object", path))
        return False
    actual = set(value)
    if actual != expected:
        failures.append(
            _failure(
                rule_id,
                f"{label} fields must exactly match {sorted(expected)}; got {sorted(actual)}",
                path,
            )
        )
        return False
    return True


def _bounded_list(
    value: object,
    failures: list[PolicyFailure],
    *,
    rule_id: str,
    label: str,
    path: str,
    maximum: int = _MAX_CATALOG_ITEMS,
) -> list[object]:
    if not isinstance(value, list):
        failures.append(_failure(rule_id, f"{label} must be a list", path))
        return []
    if len(value) > maximum:
        failures.append(_failure(rule_id, f"{label} exceeds {maximum} entries", path))
        return []
    return value


def _bounded_text(value: object, *, maximum: int = 6000) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def _valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def _record_ids(
    records: Sequence[object],
    field: str,
    failures: list[PolicyFailure],
    *,
    rule_id: str,
    label: str,
    path: str,
) -> set[str]:
    result: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        value = record.get(field)
        if not _valid_id(value):
            failures.append(_failure(rule_id, f"{label}[{index}].{field} is invalid", path))
        elif value in result:
            failures.append(_failure(rule_id, f"duplicate {label} id {value!r}", path))
        else:
            result.add(value)
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_python_tree(path: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(candidate for candidate in path.rglob("*.py") if candidate.is_file())
    if not files:
        raise ValueError(f"implementation surface {path} contains no Python files")
    for candidate in files:
        if candidate.is_symlink():
            raise ValueError(f"implementation surface contains symlink {candidate}")
        relative = candidate.relative_to(path).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        with candidate.open("rb") as handle:
            for block in iter(lambda: handle.read(64 * 1024), b""):
                digest.update(block)
        digest.update(b"\0")
    return digest.hexdigest()


def _json_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_https_locator(locator: object) -> bool:
    if not isinstance(locator, str) or len(locator) > 2048:
        return False
    parsed = urlsplit(locator)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    return not any(key.lower() in _SENSITIVE_QUERY_KEYS for key, _ in parse_qsl(parsed.query))


def _json_pointer_get(payload: object, pointer: object) -> tuple[bool, object | None]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return False, None
    current = payload
    for raw_segment in pointer[1:].split("/"):
        segment = raw_segment.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if segment not in current:
                return False, None
            current = current[segment]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            if not segment.isdigit() or int(segment) >= len(current):
                return False, None
            current = current[int(segment)]
        else:
            return False, None
    return True, current


def _validate_protocol(
    repo_root: Path,
    protocol: dict[str, object],
    failures: list[PolicyFailure],
) -> dict[str, object]:
    path = "docs/research/specification-coverage/protocol-v1.json"
    if not _exact_keys(
        protocol,
        _PROTOCOL_KEYS,
        failures,
        rule_id="specification-coverage-protocol-shape",
        label="protocol",
        path=path,
    ):
        return {}

    for field in (
        "protocol_id",
        "revision",
        "registered_at",
        "title",
        "claim",
        "research_question",
        "objective_pass_criteria",
        "objective_fail_criteria",
    ):
        if not _bounded_text(protocol.get(field)):
            failures.append(_failure("specification-coverage-protocol-shape", f"{field} is invalid", path))

    classification_rules = protocol.get("classification_rules")
    if not isinstance(classification_rules, dict) or set(classification_rules) != EXPECTED_CLASSIFICATIONS:
        failures.append(
            _failure(
                "specification-coverage-classifications",
                f"classification rules must be exactly {sorted(EXPECTED_CLASSIFICATIONS)}",
                path,
            )
        )

    strata = _bounded_list(
        protocol.get("coverage_strata"),
        failures,
        rule_id="specification-coverage-strata",
        label="coverage_strata",
        path=path,
    )
    for index, stratum in enumerate(strata):
        _exact_keys(
            stratum,
            _STRATUM_KEYS,
            failures,
            rule_id="specification-coverage-strata",
            label=f"coverage_strata[{index}]",
            path=path,
        )
    stratum_ids = _record_ids(
        strata,
        "stratum_id",
        failures,
        rule_id="specification-coverage-strata",
        label="coverage_strata",
        path=path,
    )
    if stratum_ids != EXPECTED_STRATA:
        failures.append(
            _failure(
                "specification-coverage-strata",
                f"coverage strata must be exactly {sorted(EXPECTED_STRATA)}; got {sorted(stratum_ids)}",
                path,
            )
        )

    stages = _bounded_list(
        protocol.get("artifact_stages"),
        failures,
        rule_id="specification-coverage-stage-catalog",
        label="artifact_stages",
        path=path,
    )
    for index, stage in enumerate(stages):
        _exact_keys(
            stage,
            _STAGE_KEYS,
            failures,
            rule_id="specification-coverage-stage-catalog",
            label=f"artifact_stages[{index}]",
            path=path,
        )
    stage_ids = _record_ids(
        stages,
        "stage_id",
        failures,
        rule_id="specification-coverage-stage-catalog",
        label="artifact_stages",
        path=path,
    )

    sources = _bounded_list(
        protocol.get("sources"),
        failures,
        rule_id="specification-coverage-sources",
        label="sources",
        path=path,
    )
    for index, source in enumerate(sources):
        if not _exact_keys(
            source,
            _SOURCE_KEYS,
            failures,
            rule_id="specification-coverage-sources",
            label=f"sources[{index}]",
            path=path,
        ):
            continue
        if source.get("stratum_id") not in stratum_ids:
            failures.append(_failure("specification-coverage-sources", "source has unknown stratum", path))
        if not _validate_https_locator(source.get("locator")):
            failures.append(
                _failure(
                    "specification-coverage-source-locator",
                    f"source {source.get('source_id')!r} has an unsafe or secret-bearing locator",
                    path,
                )
            )
        sha = source.get("content_sha256")
        if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
            failures.append(_failure("specification-coverage-sources", "source digest is invalid", path))
        artifact_path = source.get("artifact_path")
        if artifact_path is not None:
            resolved = safe_repo_path(repo_root, artifact_path) if isinstance(artifact_path, str) else None
            if resolved is None or not resolved.is_file():
                failures.append(
                    _failure("specification-coverage-source-path", "source path is unsafe or missing", path)
                )
            elif isinstance(sha, str) and _SHA256_RE.fullmatch(sha) and _sha256(resolved) != sha:
                failures.append(
                    _failure("specification-coverage-source-digest", "source digest is stale", artifact_path)
                )
    source_ids = _record_ids(
        sources,
        "source_id",
        failures,
        rule_id="specification-coverage-sources",
        label="sources",
        path=path,
    )
    counts = Counter(source.get("stratum_id") for source in sources if isinstance(source, dict))
    for stratum in strata:
        if not isinstance(stratum, dict):
            continue
        minimum = stratum.get("minimum_sources")
        if not isinstance(minimum, int) or minimum < 1 or counts[stratum.get("stratum_id")] < minimum:
            failures.append(
                _failure(
                    "specification-coverage-strata",
                    f"stratum {stratum.get('stratum_id')!r} does not meet its source floor",
                    path,
                )
            )

    requests = _bounded_list(
        protocol.get("requests"),
        failures,
        rule_id="specification-coverage-requests",
        label="requests",
        path=path,
    )
    for index, request in enumerate(requests):
        if not _exact_keys(
            request,
            _REQUEST_KEYS,
            failures,
            rule_id="specification-coverage-requests",
            label=f"requests[{index}]",
            path=path,
        ):
            continue
        refs = request.get("source_refs")
        if not isinstance(refs, list) or not refs or not all(ref in source_ids for ref in refs):
            failures.append(_failure("specification-coverage-requests", "request source refs are invalid", path))
        if request.get("stratum_id") not in stratum_ids:
            failures.append(_failure("specification-coverage-requests", "request has unknown stratum", path))
        for ref in refs if isinstance(refs, list) else []:
            source = next((item for item in sources if isinstance(item, dict) and item.get("source_id") == ref), None)
            if source is not None and source.get("stratum_id") != request.get("stratum_id"):
                failures.append(_failure("specification-coverage-requests", "request/source stratum mismatch", path))
    request_ids = _record_ids(
        requests,
        "request_id",
        failures,
        rule_id="specification-coverage-requests",
        label="requests",
        path=path,
    )

    carriers = _bounded_list(
        protocol.get("carriers"),
        failures,
        rule_id="specification-coverage-carriers",
        label="carriers",
        path=path,
    )
    for index, carrier in enumerate(carriers):
        _exact_keys(
            carrier,
            _CARRIER_KEYS,
            failures,
            rule_id="specification-coverage-carriers",
            label=f"carriers[{index}]",
            path=path,
        )
    carrier_ids = _record_ids(
        carriers,
        "carrier_id",
        failures,
        rule_id="specification-coverage-carriers",
        label="carriers",
        path=path,
    )
    carriers_by_id = {
        item["carrier_id"]: item for item in carriers if isinstance(item, dict) and _valid_id(item.get("carrier_id"))
    }

    concepts = _bounded_list(
        protocol.get("concepts"),
        failures,
        rule_id="specification-coverage-concepts",
        label="concepts",
        path=path,
    )
    for index, concept in enumerate(concepts):
        if not _exact_keys(
            concept,
            _CONCEPT_KEYS,
            failures,
            rule_id="specification-coverage-concepts",
            label=f"concepts[{index}]",
            path=path,
        ):
            continue
        if concept.get("atomic") is not True:
            failures.append(
                _failure(
                    "specification-coverage-concept-atomicity",
                    f"concept {concept.get('concept_id')!r} must be explicitly atomic",
                    path,
                )
            )
        if concept.get("request_id") not in request_ids:
            failures.append(_failure("specification-coverage-concepts", "concept has unknown request", path))
        if concept.get("expected_carrier_id") not in carrier_ids:
            failures.append(_failure("specification-coverage-concepts", "concept has unknown carrier", path))
        expected_classification = concept.get("expected_classification")
        carrier = carriers_by_id.get(concept.get("expected_carrier_id"))
        allowed_by_kind = {
            "sdl": {"directly-expressible"},
            "contract": {"directly-expressible", "profile-or-manifest-constraint"},
            "profile": {"profile-or-manifest-constraint", "deliberately-backend-specific"},
            "missing": {"missing"},
        }
        if expected_classification not in EXPECTED_CLASSIFICATIONS:
            failures.append(
                _failure(
                    "specification-coverage-classification-boundary",
                    f"concept {concept.get('concept_id')!r} has an invalid expected classification",
                    path,
                )
            )
        elif not isinstance(carrier, dict) or expected_classification not in allowed_by_kind.get(
            carrier.get("kind"), set()
        ):
            failures.append(
                _failure(
                    "specification-coverage-classification-boundary",
                    f"concept {concept.get('concept_id')!r} classification is incompatible with its carrier",
                    path,
                )
            )
        elif expected_classification == "deliberately-backend-specific" and carrier.get("portable") is not False:
            failures.append(
                _failure(
                    "specification-coverage-classification-boundary",
                    f"concept {concept.get('concept_id')!r} marks a portable carrier as backend-specific",
                    path,
                )
            )
        if concept.get("load_bearing") is True and expected_classification not in {
            "directly-expressible",
            "profile-or-manifest-constraint",
        }:
            failures.append(
                _failure(
                    "specification-coverage-classification-boundary",
                    f"load-bearing concept {concept.get('concept_id')!r} must preregister typed coverage",
                    path,
                )
            )
        concept_stages = concept.get("artifact_stage_ids")
        if (
            not isinstance(concept_stages, list)
            or not concept_stages
            or len(concept_stages) != len(set(concept_stages))
            or any(stage not in stage_ids for stage in concept_stages)
        ):
            failures.append(_failure("specification-coverage-concepts", "concept stages are invalid", path))
        if not isinstance(concept.get("load_bearing"), bool):
            failures.append(_failure("specification-coverage-concepts", "load_bearing must be boolean", path))
    concept_ids = _record_ids(
        concepts,
        "concept_id",
        failures,
        rule_id="specification-coverage-concepts",
        label="concepts",
        path=path,
    )
    declared: list[str] = []
    for request in requests:
        if not isinstance(request, dict) or not isinstance(request.get("concept_ids"), list):
            continue
        declared.extend(request["concept_ids"])
        for concept_id in request["concept_ids"]:
            concept = next(
                (item for item in concepts if isinstance(item, dict) and item.get("concept_id") == concept_id),
                None,
            )
            if concept is None or concept.get("request_id") != request.get("request_id"):
                failures.append(_failure("specification-coverage-concepts", "request/concept join is invalid", path))
    if len(declared) != len(set(declared)) or set(declared) != concept_ids:
        failures.append(_failure("specification-coverage-concepts", "request concept coverage is not exact", path))

    rules = protocol.get("execution_rules")
    if (
        _exact_keys(
            rules,
            _EXECUTION_RULE_KEYS,
            failures,
            rule_id="specification-coverage-execution-rules",
            label="execution_rules",
            path=path,
        )
        and rules.get("normal_execution_network_access") is not False
    ):
        failures.append(_failure("specification-coverage-execution-rules", "normal execution must be offline", path))

    return {
        "stratum_ids": stratum_ids,
        "stage_ids": stage_ids,
        "source_ids": source_ids,
        "request_ids": request_ids,
        "carrier_ids": carrier_ids,
        "carriers": carriers_by_id,
        "concept_ids": concept_ids,
        "concepts": {
            item["concept_id"]: item
            for item in concepts
            if isinstance(item, dict) and _valid_id(item.get("concept_id"))
        },
    }


def _validate_implementation_surfaces(
    repo_root: Path,
    snapshot: dict[str, object],
    failures: list[PolicyFailure],
) -> None:
    path = "docs/research/specification-coverage/execution-snapshot-v1.json"
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
        if not _exact_keys(
            surface,
            _IMPLEMENTATION_SURFACE_KEYS,
            failures,
            rule_id="specification-coverage-implementation-identity",
            label=f"implementation_surfaces[{index}]",
            path=path,
        ):
            continue
        surface_id = surface.get("surface_id")
        expected_path = IMPLEMENTATION_SURFACE_PATHS.get(surface_id)
        if surface.get("path") != expected_path:
            failures.append(
                _failure(
                    "specification-coverage-implementation-identity",
                    f"implementation surface {surface_id!r} path is not the registered execution boundary",
                    path,
                )
            )
            continue
        resolved = safe_repo_path(repo_root, expected_path) if expected_path is not None else None
        if resolved is None or not resolved.is_dir():
            failures.append(
                _failure(
                    "specification-coverage-implementation-identity",
                    f"implementation surface {surface_id!r} is unsafe or missing",
                    path,
                )
            )
            continue
        expected_sha = surface.get("content_sha256")
        try:
            actual_sha = _sha256_python_tree(resolved)
        except (OSError, ValueError) as exc:
            failures.append(
                _failure(
                    "specification-coverage-implementation-identity",
                    f"implementation surface {surface_id!r} cannot be hashed: {exc}",
                    path,
                )
            )
            continue
        if not isinstance(expected_sha, str) or not _SHA256_RE.fullmatch(expected_sha) or expected_sha != actual_sha:
            failures.append(
                _failure(
                    "specification-coverage-implementation-identity",
                    f"implementation surface {surface_id!r} digest is stale",
                    expected_path,
                )
            )


def _execute_artifact(repo_root: Path, kind: str, path: Path) -> dict[str, object]:
    if kind == "sdl":
        from aces_processor.compiler import compile_runtime_model
        from aces_sdl import admit_instantiated_scenario, instantiate_scenario, parse_sdl_file

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
    if kind == "documentation":
        return {}
    payload = load_bounded_json_object(repo_root, path.relative_to(repo_root).as_posix(), max_bytes=_MAX_FILE_BYTES)
    if kind == "experiment-task":
        from aces_contracts.contracts import ExperimentTaskModel

        model = ExperimentTaskModel.model_validate(payload)
        return {"contract": model.model_dump(mode="json", by_alias=True)}
    if kind == "experiment-apparatus-context":
        from aces_contracts.contracts import ExperimentApparatusContextModel

        model = ExperimentApparatusContextModel.model_validate(payload)
        return {"contract": model.model_dump(mode="json", by_alias=True)}
    if kind == "backend-profile":
        from aces_contracts.backend_profiles import BackendProfileModel

        model = BackendProfileModel.model_validate(payload)
        return {"profile-manifest": model.model_dump(mode="json", by_alias=True)}
    raise ValueError(f"unsupported artifact kind {kind!r}")


def _validate_artifacts(
    repo_root: Path,
    snapshot: dict[str, object],
    failures: list[PolicyFailure],
) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    path = "docs/research/specification-coverage/execution-snapshot-v1.json"
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
        expected_sha = artifact.get("sha256")
        if not isinstance(expected_sha, str) or not _SHA256_RE.fullmatch(expected_sha):
            failures.append(
                _failure("specification-coverage-artifact-digest", "artifact digest is invalid", artifact_path)
            )
        elif _sha256(resolved) != expected_sha:
            failures.append(
                _failure("specification-coverage-artifact-digest", "artifact digest is stale", artifact_path)
            )
        kind = artifact.get("kind")
        if not isinstance(kind, str):
            failures.append(_failure("specification-coverage-artifacts", "artifact kind is invalid", artifact_path))
            continue
        try:
            executed[artifact_path] = _execute_artifact(repo_root, kind, resolved)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            failures.append(
                _failure(
                    "specification-coverage-artifact-execution",
                    f"artifact {artifact.get('artifact_id')!r} failed its production boundary: {exc}",
                    artifact_path,
                )
            )
    return (
        {
            artifact_id: next(
                (item for item in artifacts if isinstance(item, dict) and item.get("artifact_id") == artifact_id), {}
            )
            for artifact_id in artifact_ids
        },
        executed,
    )


def _validate_snapshot(
    repo_root: Path,
    protocol: dict[str, object],
    snapshot: dict[str, object],
    catalogs: dict[str, object],
    failures: list[PolicyFailure],
) -> None:
    path = "docs/research/specification-coverage/execution-snapshot-v1.json"
    if not _exact_keys(
        snapshot,
        _SNAPSHOT_KEYS,
        failures,
        rule_id="specification-coverage-snapshot-shape",
        label="snapshot",
        path=path,
    ):
        return
    if snapshot.get("protocol_revision") != protocol.get("revision"):
        failures.append(_failure("specification-coverage-snapshot-join", "snapshot protocol revision is stale", path))
    protocol_path = safe_repo_path(repo_root, PROTOCOL_PATH)
    if protocol_path is None or snapshot.get("protocol_sha256") != _sha256(protocol_path):
        failures.append(_failure("specification-coverage-snapshot-join", "snapshot protocol digest is stale", path))
    if snapshot.get("execution_status") != "complete":
        failures.append(_failure("specification-coverage-snapshot-status", "execution snapshot must be complete", path))
    if not isinstance(snapshot.get("aces_revision"), str) or not re.fullmatch(
        r"[0-9a-f]{40}", snapshot["aces_revision"]
    ):
        failures.append(_failure("specification-coverage-snapshot-shape", "aces_revision is invalid", path))

    _validate_implementation_surfaces(repo_root, snapshot, failures)

    artifacts_by_id, executed = _validate_artifacts(repo_root, snapshot, failures)
    carrier_artifacts = {
        item.get("artifact_id")
        for item in protocol.get("carriers", [])
        if isinstance(item, dict) and item.get("artifact_id") is not None
    }
    if not carrier_artifacts.issubset(artifacts_by_id):
        failures.append(_failure("specification-coverage-carriers", "carrier artifact is absent from snapshot", path))

    results = _bounded_list(
        snapshot.get("concept_results"),
        failures,
        rule_id="specification-coverage-concept-results",
        label="concept_results",
        path=path,
    )
    result_ids = _record_ids(
        results,
        "concept_id",
        failures,
        rule_id="specification-coverage-concept-results",
        label="concept_results",
        path=path,
    )
    if result_ids != catalogs.get("concept_ids", set()):
        failures.append(
            _failure(
                "specification-coverage-concept-results",
                "concept results must join every protocol concept exactly once",
                path,
            )
        )
    concepts = catalogs.get("concepts", {})
    rules = protocol.get("execution_rules") if isinstance(protocol.get("execution_rules"), dict) else {}
    valid_outcomes = set(rules.get("stage_outcomes", []))
    valid_strengths = set(rules.get("validation_strength_values", []))
    for index, result in enumerate(results):
        if not _exact_keys(
            result,
            _CONCEPT_RESULT_KEYS,
            failures,
            rule_id="specification-coverage-concept-results",
            label=f"concept_results[{index}]",
            path=path,
        ):
            continue
        concept_id = result.get("concept_id")
        concept = concepts.get(concept_id) if isinstance(concepts, dict) else None
        if not isinstance(concept, dict):
            continue
        classification = result.get("classification")
        if classification not in EXPECTED_CLASSIFICATIONS:
            failures.append(
                _failure("specification-coverage-classifications", "result classification is invalid", path)
            )
        if classification != concept.get("expected_classification"):
            failures.append(
                _failure(
                    "specification-coverage-classification-boundary",
                    f"{concept_id!r} observed classification differs from the preregistered boundary",
                    path,
                )
            )
        pointer = result.get("typed_pointer")
        if classification in {"directly-expressible", "profile-or-manifest-constraint"} and (
            not isinstance(pointer, str) or not pointer.startswith("/")
        ):
            failures.append(
                _failure(
                    "specification-coverage-typed-evidence",
                    f"{concept_id!r} claims typed coverage without a typed pointer",
                    path,
                )
            )
        if classification == "missing" and pointer is not None:
            failures.append(
                _failure("specification-coverage-typed-evidence", "missing concept has a typed pointer", path)
            )

        stages = _bounded_list(
            result.get("stage_results"),
            failures,
            rule_id="specification-coverage-stage-coverage",
            label=f"concept_results[{index}].stage_results",
            path=path,
        )
        stage_ids: list[object] = []
        for stage_index, stage in enumerate(stages):
            if not _exact_keys(
                stage,
                _STAGE_RESULT_KEYS,
                failures,
                rule_id="specification-coverage-stage-coverage",
                label=f"concept_results[{index}].stage_results[{stage_index}]",
                path=path,
            ):
                continue
            stage_id = stage.get("stage_id")
            stage_ids.append(stage_id)
            outcome = stage.get("outcome")
            if outcome not in valid_outcomes:
                failures.append(_failure("specification-coverage-stage-coverage", "stage outcome is invalid", path))
            if stage.get("validation_strength") not in valid_strengths:
                failures.append(
                    _failure("specification-coverage-stage-coverage", "validation strength is invalid", path)
                )
            artifact_path = stage.get("artifact_path")
            if not isinstance(artifact_path, str) or artifact_path not in executed:
                failures.append(
                    _failure(
                        "specification-coverage-artifact-path",
                        f"stage result for {concept_id!r} references an unknown artifact",
                        path,
                    )
                )
            if outcome == "passed":
                payload = executed.get(artifact_path, {}).get(stage_id)
                exists, _ = _json_pointer_get(payload, stage.get("pointer"))
                if payload is None or not exists:
                    failures.append(
                        _failure(
                            "specification-coverage-typed-evidence",
                            f"{concept_id!r} stage {stage_id!r} does not resolve its declared pointer",
                            artifact_path if isinstance(artifact_path, str) else path,
                        )
                    )
            if classification in {"directly-expressible", "profile-or-manifest-constraint"} and outcome != "passed":
                failures.append(
                    _failure(
                        "specification-coverage-stage-coverage",
                        f"typed concept {concept_id!r} has non-passing stage {stage_id!r}",
                        path,
                    )
                )
            if classification == "missing" and outcome not in {"unsupported", "not_run"}:
                failures.append(
                    _failure("specification-coverage-stage-coverage", "missing concept outcome is dishonest", path)
                )
            if concept.get("load_bearing") is True and outcome != "passed":
                failures.append(
                    _failure(
                        "specification-coverage-load-bearing-stages",
                        f"load-bearing concept {concept_id!r} has non-passing stage {stage_id!r}",
                        path,
                    )
                )
        expected_stages = concept.get("artifact_stage_ids")
        if (
            not isinstance(expected_stages, list)
            or len(stage_ids) != len(set(stage_ids))
            or set(stage_ids) != set(expected_stages)
        ):
            failures.append(
                _failure(
                    "specification-coverage-stage-coverage",
                    f"{concept_id!r} does not have rectangular preregistered stage coverage",
                    path,
                )
            )

        occurrences = _bounded_list(
            result.get("backend_vocabulary_occurrences"),
            failures,
            rule_id="specification-coverage-backend-leakage",
            label=f"concept_results[{index}].backend_vocabulary_occurrences",
            path=path,
        )
        for occurrence_index, occurrence in enumerate(occurrences):
            if not _exact_keys(
                occurrence,
                _BACKEND_OCCURRENCE_KEYS,
                failures,
                rule_id="specification-coverage-backend-leakage",
                label=f"backend occurrence {occurrence_index}",
                path=path,
            ):
                continue
            if occurrence.get("allowed") is not True or classification == "directly-expressible":
                failures.append(
                    _failure(
                        "specification-coverage-backend-leakage",
                        f"{concept_id!r} contains unallowed backend vocabulary",
                        path,
                    )
                )
            occurrence_path = occurrence.get("artifact_path")
            if isinstance(occurrence_path, str) and not occurrence_path.startswith("source:"):
                resolved = safe_repo_path(repo_root, occurrence_path)
                if resolved is None:
                    failures.append(
                        _failure("specification-coverage-artifact-path", "backend occurrence path is unsafe", path)
                    )


def recompute_analysis(
    protocol: dict[str, object],
    snapshot: dict[str, object],
    analysis: dict[str, object],
) -> dict[str, object]:
    """Return the analysis with every outcome-bearing field recomputed."""

    result = deepcopy(analysis)
    result["snapshot_sha256"] = _json_sha256(snapshot)
    concept_by_id = {
        item["concept_id"]: item
        for item in protocol.get("concepts", [])
        if isinstance(item, dict) and isinstance(item.get("concept_id"), str)
    }
    result_by_id = {
        item["concept_id"]: item
        for item in snapshot.get("concept_results", [])
        if isinstance(item, dict) and isinstance(item.get("concept_id"), str)
    }
    counts = Counter(
        item.get("classification") for item in snapshot.get("concept_results", []) if isinstance(item, dict)
    )
    result["classification_counts"] = {
        classification: counts[classification]
        for classification in (
            "directly-expressible",
            "profile-or-manifest-constraint",
            "deliberately-backend-specific",
            "missing",
        )
    }

    load_bearing = [item for item in concept_by_id.values() if item.get("load_bearing") is True]
    load_missing = 0
    load_failed = 0
    load_passed = 0
    for concept in load_bearing:
        observed = result_by_id.get(concept["concept_id"], {})
        if observed.get("classification") == "missing":
            load_missing += 1
        elif observed.get("classification") != concept.get("expected_classification") or any(
            stage.get("outcome") != "passed" for stage in observed.get("stage_results", []) if isinstance(stage, dict)
        ):
            load_failed += 1
        else:
            load_passed += 1
    result["load_bearing_results"] = {
        "total": len(load_bearing),
        "passed": load_passed,
        "failed": load_failed,
        "missing": load_missing,
    }

    request_results: list[dict[str, object]] = []
    any_noncritical_failure = False
    for request in protocol.get("requests", []):
        if not isinstance(request, dict):
            continue
        observed = [result_by_id.get(concept_id, {}) for concept_id in request.get("concept_ids", [])]
        missing_count = sum(item.get("classification") == "missing" for item in observed)
        failed_stage_count = sum(
            stage.get("outcome") in {"failed", "not_run", "tool_failed"}
            for item in observed
            for stage in item.get("stage_results", [])
            if isinstance(stage, dict)
        )
        critical_bad = any(
            concept_by_id.get(item.get("concept_id"), {}).get("load_bearing") is True
            and (
                item.get("classification") == "missing"
                or item.get("classification")
                != concept_by_id.get(item.get("concept_id"), {}).get("expected_classification")
                or any(
                    stage.get("outcome") != "passed"
                    for stage in item.get("stage_results", [])
                    if isinstance(stage, dict)
                )
            )
            for item in observed
        )
        status = "refuted" if critical_bad else "partial" if missing_count or failed_stage_count else "demonstrated"
        any_noncritical_failure = any_noncritical_failure or bool(missing_count or failed_stage_count)
        request_results.append(
            {
                "request_id": request.get("request_id"),
                "status": status,
                "concept_count": len(observed),
                "missing_count": missing_count,
                "failed_stage_count": failed_stage_count,
            }
        )
    result["request_results"] = request_results

    leakage: list[dict[str, object]] = []
    for concept_result in snapshot.get("concept_results", []):
        if not isinstance(concept_result, dict):
            continue
        for occurrence in concept_result.get("backend_vocabulary_occurrences", []):
            if isinstance(occurrence, dict) and occurrence.get("allowed") is not True:
                leakage.append({"concept_id": concept_result.get("concept_id"), **occurrence})
    result["backend_leakage"] = leakage

    if load_missing or load_failed or leakage:
        evidence_status = "refuted"
    elif any_noncritical_failure:
        evidence_status = "partial"
    else:
        evidence_status = "demonstrated"
    result["execution_status"] = snapshot.get("execution_status")
    result["evidence_status"] = evidence_status
    return result


def _validate_analysis(
    protocol: dict[str, object],
    snapshot: dict[str, object],
    analysis: dict[str, object],
    failures: list[PolicyFailure],
) -> None:
    path = "docs/research/specification-coverage/analysis-v1.json"
    if not _exact_keys(
        analysis,
        _ANALYSIS_KEYS,
        failures,
        rule_id="specification-coverage-analysis-shape",
        label="analysis",
        path=path,
    ):
        return
    if analysis.get("protocol_revision") != protocol.get("revision") or analysis.get("snapshot_id") != snapshot.get(
        "snapshot_id"
    ):
        failures.append(_failure("specification-coverage-analysis-join", "analysis joins are stale", path))
    if analysis.get("snapshot_sha256") != _json_sha256(snapshot):
        failures.append(
            _failure(
                "specification-coverage-analysis-join",
                "analysis is not bound to the complete execution snapshot",
                path,
            )
        )
    counts = analysis.get("classification_counts")
    if not isinstance(counts, dict) or set(counts) != EXPECTED_CLASSIFICATIONS:
        failures.append(_failure("specification-coverage-analysis-shape", "classification_counts is invalid", path))
    load_results = analysis.get("load_bearing_results")
    if not isinstance(load_results, dict) or set(load_results) != {"total", "passed", "failed", "missing"}:
        failures.append(_failure("specification-coverage-analysis-shape", "load_bearing_results is invalid", path))
    request_results = analysis.get("request_results")
    if not isinstance(request_results, list):
        failures.append(_failure("specification-coverage-analysis-shape", "request_results must be a list", path))
    else:
        for index, request_result in enumerate(request_results):
            _exact_keys(
                request_result,
                _REQUEST_RESULT_KEYS,
                failures,
                rule_id="specification-coverage-analysis-shape",
                label=f"request_results[{index}]",
                path=path,
            )
    _exact_keys(
        analysis.get("claim"),
        _CLAIM_KEYS,
        failures,
        rule_id="specification-coverage-analysis-shape",
        label="claim",
        path=path,
    )
    if analysis != recompute_analysis(protocol, snapshot, analysis):
        failures.append(
            _failure(
                "specification-coverage-analysis-stale",
                "analysis outcome fields do not match the protocol-derived snapshot result",
                path,
            )
        )


def validate_bundle(
    repo_root: Path,
    protocol: dict[str, object],
    snapshot: dict[str, object],
    analysis: dict[str, object],
) -> list[PolicyFailure]:
    """Validate bundle shape, execution evidence, joins, and claim honesty."""

    failures: list[PolicyFailure] = []
    catalogs = _validate_protocol(repo_root, protocol, failures)
    _validate_snapshot(repo_root, protocol, snapshot, catalogs, failures)
    _validate_analysis(protocol, snapshot, analysis, failures)
    return failures


def load_bundle(
    repo_root: Path = REPO_ROOT,
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    manifest = load_bounded_json_object(repo_root, MANIFEST_PATH, max_bytes=_MAX_FILE_BYTES)
    if set(manifest) != _MANIFEST_KEYS:
        raise ValueError(
            f"{MANIFEST_PATH!r} fields must exactly match {sorted(_MANIFEST_KEYS)}; got {sorted(manifest)}"
        )
    loaded: list[dict[str, object]] = []
    for label in ("protocol", "snapshot", "analysis"):
        path_value = manifest[f"{label}_path"]
        sha_value = manifest[f"{label}_sha256"]
        resolved = safe_repo_path(repo_root, path_value) if isinstance(path_value, str) else None
        if resolved is None or not resolved.is_file():
            raise ValueError(f"{MANIFEST_PATH!r} contains unsafe or missing {label}_path")
        if not isinstance(sha_value, str) or not _SHA256_RE.fullmatch(sha_value):
            raise ValueError(f"{MANIFEST_PATH!r} contains invalid {label}_sha256")
        if _sha256(resolved) != sha_value:
            raise ValueError(f"{MANIFEST_PATH!r} contains stale {label}_sha256")
        loaded.append(load_bounded_json_object(repo_root, path_value, max_bytes=_MAX_FILE_BYTES))
    return manifest, loaded[0], loaded[1], loaded[2]


def evaluate(repo_root: Path = REPO_ROOT) -> list[PolicyFailure]:
    try:
        _, protocol, snapshot, analysis = load_bundle(repo_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [_failure("specification-coverage-bundle-invalid", str(exc), MANIFEST_PATH)]
    return validate_bundle(repo_root, protocol, snapshot, analysis)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON")
    args = parser.parse_args()
    failures = evaluate(REPO_ROOT)
    if args.json:
        print(
            json.dumps(
                [
                    {"rule_id": failure.rule_id, "message": failure.message, "path": failure.path}
                    for failure in failures
                ],
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for failure in failures:
            print(failure.render())
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
