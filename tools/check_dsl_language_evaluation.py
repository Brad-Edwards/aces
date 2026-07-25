#!/usr/bin/env python3
"""Validate the preregistered ACES SDL language-evaluation evidence bundle."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import product
from pathlib import Path
from statistics import median
from urllib.parse import parse_qsl, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.policy.common import (  # noqa: E402
    PolicyFailure,
    load_bounded_json_object,
    safe_repo_path,
)

MANIFEST_PATH = "docs/research/dsl-language-evaluation/bundle-manifest.json"
_HISTORICAL_PACKAGE_PREFIX = "implementations/python/packages/aces_sdl"
_CURRENT_PACKAGE_PREFIX = "implementations/python/packages/raes"
_MAX_FILE_BYTES = 2 * 1024 * 1024
_MAX_CATALOG_ITEMS = 128
_MAX_EXECUTION_RECORDS = 20_000

REQUIRED_DIMENSION_IDS = {
    "expressiveness",
    "usability-comprehension",
    "effectiveness-productivity",
    "maintainability-evolution",
    "ambiguity",
    "diagnostic-quality",
    "reviewability",
    "semantic-traceability",
}
REQUIRED_PERSONA_IDS = {
    "benchmark-designer",
    "scenario-author",
    "participant-model-author",
    "backend-implementer",
    "evaluator-reviewer",
    "assurance-auditor",
}
REQUIRED_TASK_KINDS = {
    "positive",
    "negative",
    "underspecified",
    "ambiguous",
    "round-trip",
    "mutation",
    "maintenance",
    "independent-review",
}
EVIDENCE_STATUSES = {"untested", "partial", "demonstrated", "refuted"}
ATTEMPT_OUTCOMES = {"completed", "failed", "abandoned", "tool_failed", "missing", "withdrawn"}
OBSERVATION_OUTCOMES = {"completed", "failed", "abandoned", "tool_failed", "missing"}

_MANIFEST_KEYS = {
    "bundle_id",
    "revision",
    "protocol_path",
    "snapshot_path",
    "analysis_path",
    "claim_binding",
    "supplemental_bundles",
}
_BUNDLE_ENTRY_KEYS = _MANIFEST_KEYS - {"supplemental_bundles"}
_CLAIM_BINDING_KEYS = {"claim_id", "scope", "strata"}
_STRATUM_GROUP_KEYS = {
    "group_id",
    "role",
    "partition_by",
    "persona_ids",
    "experience_band_ids",
    "tooling_condition_ids",
}
_STRATUM_PARTITION_AXES = {"persona_id", "experience_band", "tooling_condition_id"}
_STRATUM_ROLES = {"gating", "comparison"}
_PROTOCOL_KEYS = {
    "protocol_id",
    "revision",
    "registered_at",
    "title",
    "claim",
    "research_question",
    "evidence_status_values",
    "dimensions",
    "personas",
    "tooling_conditions",
    "artifact_stages",
    "sources",
    "tasks",
    "variants",
    "measures",
    "sampling_plan",
    "execution_plan",
    "thresholds",
    "ethics_and_privacy",
    "disagreement_policy",
    "validity_threats",
    "analysis_plan",
    "amendment_log",
}
_DIMENSION_KEYS = {"dimension_id", "label", "construct", "pass_rule", "fail_rule"}
_PERSONA_KEYS = {"persona_id", "label", "qualification", "minimum_completed_subjects"}
_CONDITION_KEYS = {"condition_id", "label", "allowed_surface", "assistance"}
_STAGE_KEYS = {"stage_id", "label", "canonical_entrypoint"}
_SOURCE_KEYS = {
    "source_id",
    "kind",
    "title",
    "authors",
    "year",
    "locator",
    "version",
    "revision",
    "artifact_path",
    "primary",
}
_TASK_KEYS = {
    "task_id",
    "title",
    "kind",
    "persona_ids",
    "dimension_ids",
    "source_refs",
    "intended_semantics_ref",
    "artifact_stage_ids",
    "tooling_condition_ids",
    "variant_ids",
    "success_rule",
    "failure_rule",
}
_VARIANT_KEYS = {"variant_id", "task_id", "kind", "expected_relation", "description"}
_MEASURE_KEYS = {
    "measure_id",
    "task_ids",
    "dimension_ids",
    "stage_applicability",
    "unit",
    "aggregation",
    "direction",
    "capture_rule",
}
_STAGE_APPLICABILITY_KEYS = {"task_id", "variant_ids", "artifact_stage_ids"}
_SAMPLING_KEYS = {
    "target_total",
    "minimum_per_persona",
    "experience_bands",
    "inclusion_rule",
    "exclusion_rule",
}
_EXECUTION_PLAN_KEYS = {
    "unit_of_analysis",
    "attempts_per_subject",
    "subject_task_requirements",
    "task_order",
    "blinding",
    "stopping_rule",
    "missing_data_rule",
    "withdrawal_rule",
}
_SUBJECT_TASK_REQUIREMENT_KEYS = {
    "requirement_id",
    "minimum_assigned_attempts",
    "task_kinds",
}
_THRESHOLD_KEYS = {"dimension_id", "logic", "conditions"}
_THRESHOLD_CONDITION_KEYS = {"measure_id", "operator", "target"}
_ETHICS_KEYS = {
    "review_status_required",
    "consent_required",
    "committed_data_rule",
    "prohibited_data",
}

_SNAPSHOT_KEYS = {
    "snapshot_id",
    "protocol_revision",
    "captured_at",
    "execution_status",
    "aces_revision",
    "public_surface",
    "ethics_review",
    "subjects",
    "attempts",
    "observations",
    "reviews",
    "deviations",
    "withdrawals",
    "disagreements",
}
_SURFACE_KEYS = {"surface_id", "kind", "artifact", "version", "parameters"}
_ETHICS_REVIEW_KEYS = {
    "status",
    "protocol_identifier",
    "approved_population",
    "approved_data_boundary",
}
_SUBJECT_KEYS = {"subject_id", "persona_id", "experience_band", "consent_status"}
_ATTEMPT_KEYS = {
    "attempt_id",
    "study_run_id",
    "task_id",
    "persona_id",
    "subject_id",
    "tooling_condition_id",
    "variant_id",
    "outcome",
    "observation_ids",
    "started_at",
    "ended_at",
}
_OBSERVATION_KEYS = {
    "observation_id",
    "protocol_revision",
    "study_run_id",
    "task_id",
    "persona_id",
    "subject_id",
    "tooling_condition_id",
    "attempt_id",
    "variant_id",
    "artifact_stage",
    "dimension_ids",
    "measure_id",
    "value",
    "outcome",
    "evidence_refs",
}
_REVIEW_KEYS = {
    "review_id",
    "attempt_id",
    "reviewer_subject_id",
    "task_id",
    "variant_id",
    "judgment",
    "confidence",
    "rationale_code",
    "fixed_at",
}
_DEVIATION_KEYS = {"deviation_id", "scope", "severity", "disposition", "rationale"}
_WITHDRAWAL_KEYS = {"subject_id", "recorded_at", "retained_aggregate_only"}
_DISAGREEMENT_KEYS = {
    "disagreement_id",
    "review_ids",
    "status",
    "adjudication",
    "originals_preserved",
}

_ANALYSIS_KEYS = {
    "analysis_id",
    "protocol_revision",
    "snapshot_id",
    "generated_at",
    "execution_status",
    "measure_results",
    "dimension_results",
    "stratum_results",
    "evidence_status",
    "claim",
    "plain_language_outcome",
    "limitations",
}
_STRATUM_RESULT_KEYS = {
    "stratum_id",
    "role",
    "measure_results",
    "dimension_results",
}
_DIMENSION_RESULT_KEYS = {
    "dimension_id",
    "status",
    "threshold_result",
    "condition_results",
    "supporting_observation_ids",
}
_MEASURE_RESULT_KEYS = {
    "measure_id",
    "status",
    "statistic",
    "numerator",
    "denominator",
    "opportunity_count",
    "observed_count",
    "missing_count",
    "abandoned_count",
    "tool_failed_count",
    "withdrawn_count",
    "value",
    "supporting_observation_ids",
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
    "scope",
}
_CLAIM_SCOPE_KEYS = {
    "persona_ids",
    "task_ids",
    "tooling_condition_ids",
    "variant_ids",
    "artifact_stage_ids",
    "dimension_ids",
    "measure_ids",
}

_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
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


def _failure(rule_id: str, message: str, path: str | None = None) -> PolicyFailure:
    return PolicyFailure(rule_id, message, path)


def _resolve_repository_artifact(repo_root: Path, artifact_path: str) -> Path | None:
    """Resolve an immutable evidence locator through the SDL package move."""

    resolved_path = artifact_path
    if artifact_path == _HISTORICAL_PACKAGE_PREFIX or artifact_path.startswith(f"{_HISTORICAL_PACKAGE_PREFIX}/"):
        resolved_path = f"{_CURRENT_PACKAGE_PREFIX}{artifact_path[len(_HISTORICAL_PACKAGE_PREFIX) :]}"
    return safe_repo_path(repo_root, resolved_path)


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
    limit: int,
    failures: list[PolicyFailure],
    *,
    rule_id: str,
    label: str,
    path: str,
) -> list[object]:
    if not isinstance(value, list):
        failures.append(_failure(rule_id, f"{label} must be a list", path))
        return []
    if len(value) > limit:
        failures.append(_failure(rule_id, f"{label} exceeds the {limit}-entry limit", path))
        return []
    return value


def _valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def _bounded_text(value: object, *, maximum: int = 6000) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def _string_list(value: object, *, non_empty: bool = False) -> list[str] | None:
    if not isinstance(value, list) or (non_empty and not value):
        return None
    if not all(isinstance(item, str) for item in value):
        return None
    return value


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
    duplicates: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            continue
        value = record.get(field)
        if not _valid_id(value):
            failures.append(_failure(rule_id, f"{label} has invalid {field} {value!r}", path))
            continue
        if value in result:
            duplicates.add(value)
        result.add(value)
    if duplicates:
        failures.append(_failure(rule_id, f"duplicate {label} ids: {sorted(duplicates)}", path))
    return result


def _validate_https_locator(locator: object, failures: list[PolicyFailure], source_id: object) -> None:
    if not isinstance(locator, str):
        failures.append(_failure("dsl-evaluation-source-locator", f"{source_id}: locator must be text"))
        return
    parsed = urlsplit(locator)
    if parsed.scheme != "https" or not parsed.netloc:
        failures.append(
            _failure(
                "dsl-evaluation-source-locator",
                f"{source_id}: locator must be absolute HTTPS",
            )
        )
    if parsed.username is not None or parsed.password is not None:
        failures.append(
            _failure(
                "dsl-evaluation-source-secret",
                f"{source_id}: locator contains URI userinfo",
            )
        )
    query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    sensitive = sorted(query_keys & _SENSITIVE_QUERY_KEYS)
    if sensitive:
        failures.append(
            _failure(
                "dsl-evaluation-source-secret",
                f"{source_id}: locator contains secret-bearing query keys {sensitive}",
            )
        )


def _protocol_records_by_id(
    protocol: Mapping[str, object],
    field: str,
    id_field: str,
) -> dict[str, Mapping[str, object]]:
    records = protocol.get(field, [])
    if not isinstance(records, list):
        return {}
    return {
        record[id_field]: record
        for record in records
        if isinstance(record, Mapping) and isinstance(record.get(id_field), str)
    }


def _full_claim_scope(catalogs: Mapping[str, set[str]]) -> dict[str, set[str]]:
    return {
        "persona_ids": set(catalogs.get("persona_ids", set())),
        "task_ids": set(catalogs.get("task_ids", set())),
        "tooling_condition_ids": set(catalogs.get("condition_ids", set())),
        "variant_ids": set(catalogs.get("variant_ids", set())),
        "artifact_stage_ids": set(catalogs.get("stage_ids", set())),
        "dimension_ids": set(catalogs.get("dimension_ids", set())),
        "measure_ids": set(catalogs.get("measure_ids", set())),
    }


def _attempt_matches_scope(
    attempt: Mapping[str, object],
    scope: Mapping[str, set[str]],
) -> bool:
    return (
        attempt.get("task_id") in scope.get("task_ids", set())
        and attempt.get("persona_id") in scope.get("persona_ids", set())
        and attempt.get("tooling_condition_id") in scope.get("tooling_condition_ids", set())
        and attempt.get("variant_id") in scope.get("variant_ids", set())
    )


def _validate_claim_scope(
    protocol: Mapping[str, object],
    analysis: Mapping[str, object],
    catalogs: Mapping[str, set[str]],
    failures: list[PolicyFailure],
    *,
    path: str = "docs/research/dsl-language-evaluation/analysis-v1.json",
) -> dict[str, set[str]]:
    """Validate and resolve the exact catalog slice owned by one claim."""

    fallback = _full_claim_scope(catalogs)
    claim = analysis.get("claim")
    scope = claim.get("scope") if isinstance(claim, Mapping) else None
    if not _exact_keys(
        scope,
        _CLAIM_SCOPE_KEYS,
        failures,
        rule_id="dsl-evaluation-claim-scope",
        label="claim scope",
        path=path,
    ):
        return fallback

    catalog_fields = {
        "persona_ids": "persona_ids",
        "task_ids": "task_ids",
        "tooling_condition_ids": "condition_ids",
        "variant_ids": "variant_ids",
        "artifact_stage_ids": "stage_ids",
        "dimension_ids": "dimension_ids",
        "measure_ids": "measure_ids",
    }
    resolved: dict[str, set[str]] = {}
    for field, catalog_field in catalog_fields.items():
        values = _string_list(scope[field], non_empty=True)
        known = catalogs.get(catalog_field, set())
        if values is None or len(values) != len(set(values)) or not set(values).issubset(known):
            failures.append(
                _failure(
                    "dsl-evaluation-claim-scope",
                    f"claim scope {field} must be a non-empty unique subset of the protocol catalog",
                    path,
                )
            )
            resolved[field] = set(values or []) & known
        else:
            resolved[field] = set(values)

    tasks = _protocol_records_by_id(protocol, "tasks", "task_id")
    measures = _protocol_records_by_id(protocol, "measures", "measure_id")
    for task_id in resolved["task_ids"]:
        task = tasks.get(task_id, {})
        joins = (
            ("persona_ids", "persona_ids"),
            ("tooling_condition_ids", "tooling_condition_ids"),
            ("variant_ids", "variant_ids"),
            ("artifact_stage_ids", "artifact_stage_ids"),
        )
        if any(
            not (set(_string_list(task.get(task_field), non_empty=True) or []) & resolved[scope_field])
            for task_field, scope_field in joins
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-claim-scope",
                    f"{task_id}: claim scope must retain an eligible persona, condition, variant, and stage",
                    path,
                )
            )
        if not any(
            task_id in (_string_list(measures[measure_id].get("task_ids"), non_empty=True) or [])
            for measure_id in resolved["measure_ids"]
            if measure_id in measures
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-claim-scope",
                    f"{task_id}: claim scope has no applicable measure",
                    path,
                )
            )

    thresholds = {
        threshold.get("dimension_id"): threshold
        for threshold in protocol.get("thresholds", [])
        if isinstance(threshold, Mapping) and isinstance(threshold.get("dimension_id"), str)
    }
    for dimension_id in resolved["dimension_ids"]:
        threshold = thresholds.get(dimension_id)
        conditions = threshold.get("conditions", []) if isinstance(threshold, Mapping) else []
        required_measures = {
            condition.get("measure_id")
            for condition in conditions
            if isinstance(condition, Mapping) and isinstance(condition.get("measure_id"), str)
        }
        if not required_measures or not required_measures.issubset(resolved["measure_ids"]):
            failures.append(
                _failure(
                    "dsl-evaluation-claim-scope",
                    f"{dimension_id}: claim scope must include every threshold measure",
                    path,
                )
            )
    return resolved


def _validate_claim_binding(
    protocol: Mapping[str, object],
    analysis: Mapping[str, object],
    claim_binding: object,
    catalogs: Mapping[str, set[str]],
    scope: Mapping[str, set[str]],
    failures: list[PolicyFailure],
    *,
    path: str,
) -> list[dict[str, object]]:
    """Bind one stable claim to its immutable scope and reporting strata."""

    if not _exact_keys(
        claim_binding,
        _CLAIM_BINDING_KEYS,
        failures,
        rule_id="dsl-evaluation-claim-binding",
        label="claim binding",
        path=path,
    ):
        return []
    assert isinstance(claim_binding, dict)
    claim = analysis.get("claim")
    claim_id = claim.get("claim_id") if isinstance(claim, Mapping) else None
    if not _valid_id(claim_binding["claim_id"]) or claim_binding["claim_id"] != claim_id:
        failures.append(
            _failure(
                "dsl-evaluation-claim-binding",
                "manifest claim binding must name the analysis claim_id exactly",
                path,
            )
        )

    bound_scope = claim_binding["scope"]
    if _exact_keys(
        bound_scope,
        _CLAIM_SCOPE_KEYS,
        failures,
        rule_id="dsl-evaluation-claim-binding",
        label="claim binding scope",
        path=path,
    ):
        assert isinstance(bound_scope, dict)
        for field in _CLAIM_SCOPE_KEYS:
            values = _string_list(bound_scope[field], non_empty=True)
            if values is None or len(values) != len(set(values)) or set(values) != scope.get(field, set()):
                failures.append(
                    _failure(
                        "dsl-evaluation-claim-binding",
                        f"analysis claim scope {field} must exactly match its manifest binding",
                        path,
                    )
                )

    groups = _bounded_list(
        claim_binding["strata"],
        16,
        failures,
        rule_id="dsl-evaluation-claim-strata",
        label="claim binding strata",
        path=path,
    )
    group_ids = _record_ids(
        groups,
        "group_id",
        failures,
        rule_id="dsl-evaluation-claim-strata",
        label="claim stratum group",
        path=path,
    )
    experience_bands = set()
    sampling_plan = protocol.get("sampling_plan")
    if isinstance(sampling_plan, Mapping):
        experience_bands = set(_string_list(sampling_plan.get("experience_bands"), non_empty=True) or [])

    expanded: list[dict[str, object]] = []
    for index, group in enumerate(groups):
        if not _exact_keys(
            group,
            _STRATUM_GROUP_KEYS,
            failures,
            rule_id="dsl-evaluation-claim-strata",
            label=f"claim binding strata[{index}]",
            path=path,
        ):
            continue
        assert isinstance(group, dict)
        group_id = group["group_id"]
        role = group["role"]
        partition_by = _string_list(group["partition_by"])
        persona_ids = _string_list(group["persona_ids"], non_empty=True)
        band_ids = _string_list(group["experience_band_ids"], non_empty=True)
        condition_ids = _string_list(group["tooling_condition_ids"], non_empty=True)
        valid = (
            _valid_id(group_id)
            and role in _STRATUM_ROLES
            and partition_by is not None
            and len(partition_by) == len(set(partition_by))
            and set(partition_by).issubset(_STRATUM_PARTITION_AXES)
            and persona_ids is not None
            and len(persona_ids) == len(set(persona_ids))
            and set(persona_ids).issubset(scope.get("persona_ids", set()))
            and band_ids is not None
            and len(band_ids) == len(set(band_ids))
            and set(band_ids).issubset(experience_bands)
            and condition_ids is not None
            and len(condition_ids) == len(set(condition_ids))
            and set(condition_ids).issubset(scope.get("tooling_condition_ids", set()))
        )
        if not valid:
            failures.append(
                _failure(
                    "dsl-evaluation-claim-strata",
                    f"claim stratum group {group_id!r} has invalid role, partition axes, or catalog filters",
                    path,
                )
            )
            continue

        assert isinstance(group_id, str)
        assert isinstance(role, str)
        assert partition_by is not None
        assert persona_ids is not None
        assert band_ids is not None
        assert condition_ids is not None
        axis_values = {
            "persona_id": persona_ids,
            "experience_band": band_ids,
            "tooling_condition_id": condition_ids,
        }
        split_axes = [
            axis for axis in ("persona_id", "experience_band", "tooling_condition_id") if axis in partition_by
        ]
        combinations = product(*(axis_values[axis] for axis in split_axes)) if split_axes else [()]
        for combination in combinations:
            selected = dict(zip(split_axes, combination, strict=True))
            stratum_id = "-".join([group_id, *(str(selected[axis]) for axis in split_axes)])
            stratum_personas = {str(selected["persona_id"])} if "persona_id" in selected else set(persona_ids)
            stratum_bands = {str(selected["experience_band"])} if "experience_band" in selected else set(band_ids)
            stratum_conditions = (
                {str(selected["tooling_condition_id"])} if "tooling_condition_id" in selected else set(condition_ids)
            )
            stratum_scope = _derive_stratum_scope(
                protocol,
                scope,
                persona_ids=stratum_personas,
                experience_band_ids=stratum_bands,
                tooling_condition_ids=stratum_conditions,
            )
            if (
                not _valid_id(stratum_id)
                or not stratum_scope["task_ids"]
                or not stratum_scope["measure_ids"]
                or not stratum_scope["dimension_ids"]
            ):
                failures.append(
                    _failure(
                        "dsl-evaluation-claim-strata",
                        f"claim stratum {stratum_id!r} has no complete task/measure/dimension slice",
                        path,
                    )
                )
                continue
            expanded.append({"stratum_id": stratum_id, "role": role, "scope": stratum_scope})

    expanded_ids = [str(item["stratum_id"]) for item in expanded]
    if len(group_ids) != len(groups) or len(expanded_ids) != len(set(expanded_ids)) or not expanded:
        failures.append(
            _failure(
                "dsl-evaluation-claim-strata",
                "claim binding requires unique groups and expanded stratum ids",
                path,
            )
        )
    if not any(item["role"] == "gating" for item in expanded):
        failures.append(_failure("dsl-evaluation-claim-strata", "claim binding requires a gating stratum", path))
    if len(expanded) > _MAX_CATALOG_ITEMS:
        failures.append(
            _failure(
                "dsl-evaluation-claim-strata",
                f"claim binding expands beyond {_MAX_CATALOG_ITEMS} strata",
                path,
            )
        )
        return expanded[:_MAX_CATALOG_ITEMS]
    return expanded


def _derive_stratum_scope(
    protocol: Mapping[str, object],
    claim_scope: Mapping[str, set[str]],
    *,
    persona_ids: set[str],
    experience_band_ids: set[str],
    tooling_condition_ids: set[str],
) -> dict[str, set[str]]:
    """Derive the protocol-applicable claim slice for one preregistered stratum."""

    tasks = _protocol_records_by_id(protocol, "tasks", "task_id")
    selected_tasks = {
        task_id
        for task_id, task in tasks.items()
        if task_id in claim_scope.get("task_ids", set())
        and set(_string_list(task.get("persona_ids"), non_empty=True) or []) & persona_ids
        and set(_string_list(task.get("tooling_condition_ids"), non_empty=True) or []) & tooling_condition_ids
    }
    variants = _protocol_records_by_id(protocol, "variants", "variant_id")
    selected_variants = {
        variant_id
        for variant_id, variant in variants.items()
        if variant_id in claim_scope.get("variant_ids", set()) and variant.get("task_id") in selected_tasks
    }
    measures = _protocol_records_by_id(protocol, "measures", "measure_id")
    selected_measures = {
        measure_id
        for measure_id, measure in measures.items()
        if measure_id in claim_scope.get("measure_ids", set())
        and set(_string_list(measure.get("task_ids"), non_empty=True) or []) & selected_tasks
    }
    thresholds = {
        threshold.get("dimension_id"): threshold
        for threshold in protocol.get("thresholds", [])
        if isinstance(threshold, Mapping) and isinstance(threshold.get("dimension_id"), str)
    }
    selected_dimensions = set()
    for dimension_id in claim_scope.get("dimension_ids", set()):
        threshold = thresholds.get(dimension_id)
        conditions = threshold.get("conditions", []) if isinstance(threshold, Mapping) else []
        required_measures = {
            condition.get("measure_id")
            for condition in conditions
            if isinstance(condition, Mapping) and isinstance(condition.get("measure_id"), str)
        }
        if required_measures and required_measures.issubset(selected_measures):
            selected_dimensions.add(dimension_id)
    return {
        "persona_ids": set(persona_ids),
        "experience_band_ids": set(experience_band_ids),
        "task_ids": selected_tasks,
        "tooling_condition_ids": set(tooling_condition_ids),
        "variant_ids": selected_variants,
        "artifact_stage_ids": set(claim_scope.get("artifact_stage_ids", set())),
        "dimension_ids": selected_dimensions,
        "measure_ids": selected_measures,
    }


def resolve_claim_strata(
    protocol: Mapping[str, object],
    analysis: Mapping[str, object],
    claim_binding: Mapping[str, object],
) -> list[dict[str, object]]:
    """Resolve a validated manifest binding for recomputation and fixtures."""

    catalogs = {
        "persona_ids": set(_protocol_records_by_id(protocol, "personas", "persona_id")),
        "task_ids": set(_protocol_records_by_id(protocol, "tasks", "task_id")),
        "condition_ids": set(_protocol_records_by_id(protocol, "tooling_conditions", "condition_id")),
        "variant_ids": set(_protocol_records_by_id(protocol, "variants", "variant_id")),
        "stage_ids": set(_protocol_records_by_id(protocol, "artifact_stages", "stage_id")),
        "dimension_ids": set(_protocol_records_by_id(protocol, "dimensions", "dimension_id")),
        "measure_ids": set(_protocol_records_by_id(protocol, "measures", "measure_id")),
    }
    failures: list[PolicyFailure] = []
    scope = _validate_claim_scope(protocol, analysis, catalogs, failures, path=MANIFEST_PATH)
    strata = _validate_claim_binding(
        protocol,
        analysis,
        claim_binding,
        catalogs,
        scope,
        failures,
        path=MANIFEST_PATH,
    )
    if failures:
        raise ValueError("; ".join(f"{failure.rule_id}: {failure.message}" for failure in failures))
    return strata


def _measure_stage_ids(
    measure: Mapping[str, object],
    task_id: str,
    variant_id: str,
) -> list[str]:
    """Return the single preregistered stage set for a task/variant/measure."""

    declarations = measure.get("stage_applicability", [])
    if not isinstance(declarations, list):
        raise ValueError(f"{measure.get('measure_id')}: stage applicability must be a list")
    matches: list[list[str]] = []
    for declaration in declarations:
        if not isinstance(declaration, Mapping) or declaration.get("task_id") != task_id:
            continue
        variant_ids = _string_list(declaration.get("variant_ids"), non_empty=True)
        stage_ids = _string_list(declaration.get("artifact_stage_ids"), non_empty=True)
        if variant_ids is not None and variant_id in variant_ids and stage_ids is not None:
            matches.append(stage_ids)
    if len(matches) != 1:
        raise ValueError(f"{measure.get('measure_id')}: expected one stage declaration for {task_id}/{variant_id}")
    return matches[0]


def _measure_opportunities(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    scope: Mapping[str, Sequence[str] | set[str]] | None = None,
) -> tuple[
    dict[str, Mapping[str, object]],
    list[tuple[Mapping[str, object], Mapping[str, object], str, bool]],
    dict[tuple[str, str, str], Mapping[str, object]],
]:
    """Derive every attempt-measure-stage opportunity and frozen observation."""

    tasks = _protocol_records_by_id(protocol, "tasks", "task_id")
    measures = _protocol_records_by_id(protocol, "measures", "measure_id")
    scope_sets = {field: set(values) for field, values in scope.items()} if scope is not None else None
    if scope_sets is not None:
        measures = {
            measure_id: measure
            for measure_id, measure in measures.items()
            if measure_id in scope_sets.get("measure_ids", set())
        }
    attempts = snapshot.get("attempts", [])
    observations = snapshot.get("observations", [])
    withdrawals = snapshot.get("withdrawals", [])
    subjects = snapshot.get("subjects", [])
    subjects_by_id = {
        subject.get("subject_id"): subject
        for subject in subjects
        if isinstance(subject, Mapping) and isinstance(subject.get("subject_id"), str)
    }
    if not isinstance(attempts, list) or not isinstance(observations, list) or not isinstance(withdrawals, list):
        raise ValueError("snapshot execution records must be lists")

    withdrawn_subjects = {
        withdrawal["subject_id"]
        for withdrawal in withdrawals
        if isinstance(withdrawal, Mapping) and isinstance(withdrawal.get("subject_id"), str)
    }
    observation_by_opportunity: dict[tuple[str, str, str], Mapping[str, object]] = {}
    for observation in observations:
        if not isinstance(observation, Mapping):
            continue
        attempt_id = observation.get("attempt_id")
        measure_id = observation.get("measure_id")
        artifact_stage = observation.get("artifact_stage")
        if not isinstance(attempt_id, str) or not isinstance(measure_id, str) or not isinstance(artifact_stage, str):
            continue
        key = (attempt_id, measure_id, artifact_stage)
        if key in observation_by_opportunity:
            raise ValueError(f"duplicate observation opportunity {attempt_id}/{measure_id}/{artifact_stage}")
        observation_by_opportunity[key] = observation

    opportunities: list[tuple[Mapping[str, object], Mapping[str, object], str, bool]] = []
    expected_keys: set[tuple[str, str, str]] = set()
    selected_attempt_ids: set[str] = set()
    for attempt in attempts:
        if not isinstance(attempt, Mapping):
            continue
        attempt_id = attempt.get("attempt_id")
        task_id = attempt.get("task_id")
        subject_id = attempt.get("subject_id")
        variant_id = attempt.get("variant_id")
        if not isinstance(attempt_id, str) or not isinstance(task_id, str) or not isinstance(variant_id, str):
            continue
        task = tasks.get(task_id)
        if task is None:
            continue
        if scope_sets is not None and not _attempt_matches_scope(attempt, scope_sets):
            continue
        if scope_sets is not None and "experience_band_ids" in scope_sets:
            subject = subjects_by_id.get(subject_id)
            if (
                not isinstance(subject, Mapping)
                or subject.get("experience_band") not in scope_sets["experience_band_ids"]
            ):
                continue
        selected_attempt_ids.add(attempt_id)
        withdrawn = (isinstance(subject_id, str) and subject_id in withdrawn_subjects) or attempt.get(
            "outcome"
        ) == "withdrawn"
        for measure in measures.values():
            task_ids = _string_list(measure.get("task_ids"), non_empty=True)
            if task_ids is None or task_id not in task_ids:
                continue
            measure_id = measure.get("measure_id")
            if not isinstance(measure_id, str):
                continue
            for artifact_stage in _measure_stage_ids(measure, task_id, variant_id):
                if scope_sets is not None and artifact_stage not in scope_sets.get("artifact_stage_ids", set()):
                    continue
                opportunities.append((attempt, measure, artifact_stage, withdrawn))
                expected_keys.add((attempt_id, measure_id, artifact_stage))

    observed_keys = set(observation_by_opportunity)
    if scope_sets is not None:
        observed_keys = {
            key
            for key in observed_keys
            if key[0] in selected_attempt_ids
            and key[1] in scope_sets.get("measure_ids", set())
            and key[2] in scope_sets.get("artifact_stage_ids", set())
        }
    extras = sorted(observed_keys - expected_keys)
    if extras:
        raise ValueError(f"observations without protocol-declared opportunities: {extras[:5]}")
    return measures, opportunities, observation_by_opportunity


def recompute_measure_results(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    *,
    scope: Mapping[str, Sequence[str] | set[str]] | None = None,
) -> dict[str, dict[str, object]]:
    """Recompute measures from the complete protocol-derived opportunity matrix."""

    measures, opportunities, observation_by_opportunity = _measure_opportunities(protocol, snapshot, scope)
    results: dict[str, dict[str, object]] = {}
    for measure_id, measure in measures.items():
        aggregation = measure.get("aggregation")
        if aggregation not in {"proportion", "median", "count"}:
            raise ValueError(f"invalid measure aggregation for {measure_id!r}")

        matching = [item for item in opportunities if item[1].get("measure_id") == measure_id]
        opportunity_count = len(matching)
        withdrawn_count = sum(withdrawn for _, _, _, withdrawn in matching)
        eligible = [(attempt, artifact_stage) for attempt, _, artifact_stage, withdrawn in matching if not withdrawn]
        denominator = len(eligible)
        values: list[int | float] = []
        supporting_ids: list[str] = []
        missing_count = 0
        abandoned_count = 0
        tool_failed_count = 0

        for attempt, artifact_stage in eligible:
            attempt_id = attempt.get("attempt_id")
            if not isinstance(attempt_id, str):
                missing_count += 1
                continue
            observation = observation_by_opportunity.get((attempt_id, measure_id, artifact_stage))
            if observation is None:
                missing_count += 1
                continue
            observation_id = observation.get("observation_id")
            if not isinstance(observation_id, str):
                raise ValueError(f"{measure_id}: observations require ids")
            supporting_ids.append(observation_id)
            outcome = observation.get("outcome")
            if outcome == "missing":
                missing_count += 1
            elif outcome == "abandoned":
                abandoned_count += 1
            elif outcome == "tool_failed":
                tool_failed_count += 1
            value = observation.get("value")
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{measure_id}: observation values must be numeric or null")
            if aggregation == "proportion" and value not in {0, 1}:
                raise ValueError(f"{measure_id}: proportion observations must be 0 or 1")
            values.append(value)

        observed_count = len(values)
        numerator: int | float | None = None
        value: int | float | None = None
        if denominator > 0 and observed_count == denominator:
            if aggregation == "proportion":
                numerator = sum(values)
                value = numerator / denominator
            elif aggregation == "median":
                value = float(median(values))
            else:
                numerator = sum(values)
                value = numerator
        results[measure_id] = {
            "statistic": aggregation,
            "numerator": numerator,
            "denominator": denominator,
            "opportunity_count": opportunity_count,
            "observed_count": observed_count,
            "missing_count": missing_count,
            "abandoned_count": abandoned_count,
            "tool_failed_count": tool_failed_count,
            "withdrawn_count": withdrawn_count,
            "value": value,
            "supporting_observation_ids": supporting_ids,
        }
    return results


def recompute_dimension_results(
    protocol: Mapping[str, object],
    measure_results: Mapping[str, Mapping[str, object]],
    *,
    dimension_ids: Sequence[str] | set[str] | None = None,
) -> dict[str, dict[str, object]]:
    """Apply protocol-declared threshold conditions to recomputed measures."""

    operators = {
        ">=": lambda actual, target: actual >= target,
        "<=": lambda actual, target: actual <= target,
        "==": lambda actual, target: actual == target,
    }
    results: dict[str, dict[str, object]] = {}
    selected_dimensions = set(dimension_ids) if dimension_ids is not None else None
    for threshold in protocol.get("thresholds", []):
        if not isinstance(threshold, Mapping):
            continue
        dimension_id = threshold.get("dimension_id")
        conditions = threshold.get("conditions")
        if (
            not isinstance(dimension_id, str)
            or threshold.get("logic") != "all"
            or not isinstance(conditions, list)
            or not conditions
        ):
            raise ValueError(f"invalid threshold for {dimension_id!r}")
        if selected_dimensions is not None and dimension_id not in selected_dimensions:
            continue
        resolved: list[tuple[Mapping[str, object], Mapping[str, object]]] = []
        for condition in conditions:
            if not isinstance(condition, Mapping):
                raise ValueError(f"{dimension_id}: threshold condition must be an object")
            measure_id = condition.get("measure_id")
            operator = condition.get("operator")
            target = condition.get("target")
            measure = measure_results.get(measure_id) if isinstance(measure_id, str) else None
            if operator not in operators or isinstance(target, bool) or not isinstance(target, (int, float)):
                raise ValueError(f"{dimension_id}: invalid threshold operator or target")
            if measure is None:
                raise ValueError(f"{dimension_id}: threshold references unknown measure {measure_id!r}")
            resolved.append((condition, measure))
        if any(measure.get("value") is None for _, measure in resolved):
            results[dimension_id] = {
                "status": "not_evaluated",
                "threshold_result": "not_evaluated",
                "condition_results": [],
                "supporting_observation_ids": [],
            }
            continue
        condition_results: list[dict[str, object]] = []
        supporting_ids: list[str] = []
        for condition, measure in resolved:
            actual = measure["value"]
            operator = condition["operator"]
            target = condition["target"]
            if isinstance(actual, bool) or not isinstance(actual, (int, float)):
                raise ValueError(f"{dimension_id}: measure value must be numeric")
            passed = operators[operator](actual, target)
            condition_results.append(
                {
                    "measure_id": condition["measure_id"],
                    "operator": operator,
                    "target": target,
                    "actual": actual,
                    "passed": passed,
                }
            )
            refs = measure.get("supporting_observation_ids", [])
            if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
                raise ValueError(f"{dimension_id}: measure observation refs must be text ids")
            for observation_id in refs:
                if observation_id not in supporting_ids:
                    supporting_ids.append(observation_id)
        results[dimension_id] = {
            "status": "evaluated",
            "threshold_result": "pass" if all(item["passed"] for item in condition_results) else "fail",
            "condition_results": condition_results,
            "supporting_observation_ids": supporting_ids,
        }
    return results


def recompute_stratum_results(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    strata: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Recompute independently persisted results for every bound claim stratum."""

    results: list[dict[str, object]] = []
    for stratum in strata:
        stratum_id = stratum.get("stratum_id")
        role = stratum.get("role")
        scope = stratum.get("scope")
        if not isinstance(stratum_id, str) or role not in _STRATUM_ROLES or not isinstance(scope, Mapping):
            raise ValueError("invalid resolved claim stratum")
        measures = recompute_measure_results(protocol, snapshot, scope=scope)
        measure_results = [
            {
                "measure_id": measure_id,
                "status": (
                    "not_evaluated"
                    if result["denominator"] == 0
                    else "incomplete"
                    if result["observed_count"] != result["denominator"]
                    else "evaluated"
                ),
                **result,
            }
            for measure_id, result in measures.items()
        ]
        dimensions = recompute_dimension_results(
            protocol,
            measures,
            dimension_ids=scope.get("dimension_ids", set()),
        )
        dimension_results = [{"dimension_id": dimension_id, **result} for dimension_id, result in dimensions.items()]
        results.append(
            {
                "stratum_id": stratum_id,
                "role": role,
                "measure_results": measure_results,
                "dimension_results": dimension_results,
            }
        )
    return results


def _validate_protocol(
    repo_root: Path,
    protocol: dict[str, object],
    failures: list[PolicyFailure],
    *,
    path: str = "docs/research/dsl-language-evaluation/protocol-v1.json",
) -> dict[str, set[str]]:
    if not _exact_keys(
        protocol,
        _PROTOCOL_KEYS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="protocol",
        path=path,
    ):
        return {}

    dimensions = _bounded_list(
        protocol["dimensions"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="dimensions",
        path=path,
    )
    personas = _bounded_list(
        protocol["personas"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="personas",
        path=path,
    )
    conditions = _bounded_list(
        protocol["tooling_conditions"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="tooling_conditions",
        path=path,
    )
    stages = _bounded_list(
        protocol["artifact_stages"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="artifact_stages",
        path=path,
    )
    sources = _bounded_list(
        protocol["sources"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="sources",
        path=path,
    )
    tasks = _bounded_list(
        protocol["tasks"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="tasks",
        path=path,
    )
    variants = _bounded_list(
        protocol["variants"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="variants",
        path=path,
    )
    measures = _bounded_list(
        protocol["measures"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="measures",
        path=path,
    )
    thresholds = _bounded_list(
        protocol["thresholds"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="thresholds",
        path=path,
    )

    dimension_ids = _record_ids(
        dimensions,
        "dimension_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="dimension",
        path=path,
    )
    persona_ids = _record_ids(
        personas,
        "persona_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="persona",
        path=path,
    )
    condition_ids = _record_ids(
        conditions,
        "condition_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="tooling condition",
        path=path,
    )
    stage_ids = _record_ids(
        stages,
        "stage_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="artifact stage",
        path=path,
    )
    source_ids = _record_ids(
        sources,
        "source_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="source",
        path=path,
    )
    task_ids = _record_ids(
        tasks,
        "task_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="task",
        path=path,
    )
    variant_ids = _record_ids(
        variants,
        "variant_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="variant",
        path=path,
    )
    measure_ids = _record_ids(
        measures,
        "measure_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="measure",
        path=path,
    )

    if not REQUIRED_DIMENSION_IDS.issubset(dimension_ids):
        failures.append(
            _failure(
                "dsl-evaluation-dimension-coverage",
                f"missing required dimensions: {sorted(REQUIRED_DIMENSION_IDS - dimension_ids)}",
                path,
            )
        )
    if not REQUIRED_PERSONA_IDS.issubset(persona_ids):
        failures.append(
            _failure(
                "dsl-evaluation-persona-coverage",
                f"missing required personas: {sorted(REQUIRED_PERSONA_IDS - persona_ids)}",
                path,
            )
        )
    if protocol["evidence_status_values"] != [
        "untested",
        "partial",
        "demonstrated",
        "refuted",
    ]:
        failures.append(
            _failure(
                "dsl-evaluation-status-vocabulary",
                "evidence statuses must preserve ADR-021 order and vocabulary",
                path,
            )
        )

    for index, record in enumerate(dimensions):
        _exact_keys(
            record,
            _DIMENSION_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"dimensions[{index}]",
            path=path,
        )
    for index, record in enumerate(personas):
        if not _exact_keys(
            record,
            _PERSONA_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"personas[{index}]",
            path=path,
        ):
            continue
        if (
            not isinstance(record["minimum_completed_subjects"], int)
            or isinstance(record["minimum_completed_subjects"], bool)
            or record["minimum_completed_subjects"] < 0
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-sampling-plan",
                    f"{record['persona_id']}: minimum_completed_subjects must be non-negative",
                    path,
                )
            )
    for index, record in enumerate(conditions):
        _exact_keys(
            record,
            _CONDITION_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"tooling_conditions[{index}]",
            path=path,
        )
    for index, record in enumerate(stages):
        _exact_keys(
            record,
            _STAGE_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"artifact_stages[{index}]",
            path=path,
        )

    for index, source in enumerate(sources):
        if not _exact_keys(
            source,
            _SOURCE_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"sources[{index}]",
            path=path,
        ):
            continue
        source_id = source["source_id"]
        _validate_https_locator(source["locator"], failures, source_id)
        if source["primary"] is not True:
            failures.append(
                _failure(
                    "dsl-evaluation-source-primary",
                    f"{source_id}: source must be primary",
                    path,
                )
            )
        if source["kind"] == "repository-internal":
            revision = source["revision"]
            artifact_path = source["artifact_path"]
            if not isinstance(revision, str) or not _SHA_RE.fullmatch(revision):
                failures.append(
                    _failure(
                        "dsl-evaluation-source-pin",
                        f"{source_id}: invalid Git revision",
                        path,
                    )
                )
            elif isinstance(source["locator"], str) and revision not in source["locator"]:
                failures.append(
                    _failure(
                        "dsl-evaluation-source-pin",
                        f"{source_id}: locator does not bind the declared Git revision",
                        path,
                    )
                )
            if not isinstance(artifact_path, str):
                failures.append(
                    _failure(
                        "dsl-evaluation-source-path",
                        f"{source_id}: missing artifact path",
                        path,
                    )
                )
            else:
                resolved = _resolve_repository_artifact(repo_root, artifact_path)
                if resolved is None or not resolved.exists():
                    failures.append(
                        _failure(
                            "dsl-evaluation-source-path",
                            f"{source_id}: unsafe or missing path",
                            path,
                        )
                    )
        elif source["revision"] is not None or source["artifact_path"] is not None:
            failures.append(
                _failure(
                    "dsl-evaluation-source-shape",
                    f"{source_id}: publication must not claim a repository revision/path",
                    path,
                )
            )

    task_kinds: set[str] = set()
    variants_by_task: dict[str, set[str]] = {task_id: set() for task_id in task_ids}
    for index, variant in enumerate(variants):
        if not _exact_keys(
            variant,
            _VARIANT_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"variants[{index}]",
            path=path,
        ):
            continue
        task_id = variant["task_id"]
        if not isinstance(task_id, str) or task_id not in task_ids:
            failures.append(
                _failure(
                    "dsl-evaluation-variant-join",
                    f"{variant['variant_id']}: unknown task",
                    path,
                )
            )
        else:
            variant_id = variant["variant_id"]
            if isinstance(variant_id, str):
                variants_by_task[task_id].add(variant_id)
    for index, task in enumerate(tasks):
        if not _exact_keys(
            task,
            _TASK_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"tasks[{index}]",
            path=path,
        ):
            continue
        task_id = task["task_id"]
        if not isinstance(task_id, str):
            failures.append(_failure("dsl-evaluation-protocol-id", "task id must be text", path))
            continue
        task_kind = task["kind"]
        if isinstance(task_kind, str):
            task_kinds.add(task_kind)
        else:
            failures.append(
                _failure(
                    "dsl-evaluation-task-kind-coverage",
                    f"{task_id}: task kind must be text",
                    path,
                )
            )
        joins = (
            ("persona_ids", persona_ids),
            ("dimension_ids", dimension_ids),
            ("source_refs", source_ids),
            ("artifact_stage_ids", stage_ids),
            ("tooling_condition_ids", condition_ids),
            ("variant_ids", variant_ids),
        )
        for field, allowed in joins:
            values = task[field]
            value_ids = _string_list(values, non_empty=True)
            if value_ids is None or not set(value_ids).issubset(allowed):
                failures.append(
                    _failure(
                        "dsl-evaluation-task-join",
                        f"{task_id}: invalid or empty {field}",
                        path,
                    )
                )
        task_variant_ids = task["variant_ids"]
        valid_task_variant_ids = _string_list(task_variant_ids)
        if valid_task_variant_ids is not None and set(valid_task_variant_ids) != variants_by_task.get(task_id, set()):
            failures.append(
                _failure(
                    "dsl-evaluation-task-variant-coverage",
                    f"{task_id}: task and variant catalogs disagree",
                    path,
                )
            )
    if not REQUIRED_TASK_KINDS.issubset(task_kinds):
        failures.append(
            _failure(
                "dsl-evaluation-task-kind-coverage",
                f"missing required task kinds: {sorted(REQUIRED_TASK_KINDS - task_kinds)}",
                path,
            )
        )

    tasks_by_id = _protocol_records_by_id(protocol, "tasks", "task_id")
    for index, measure in enumerate(measures):
        if not _exact_keys(
            measure,
            _MEASURE_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"measures[{index}]",
            path=path,
        ):
            continue
        measure_dimensions = _string_list(measure["dimension_ids"], non_empty=True)
        if measure_dimensions is None or not set(measure_dimensions).issubset(dimension_ids):
            failures.append(
                _failure(
                    "dsl-evaluation-measure-join",
                    f"{measure['measure_id']}: invalid dimension ids",
                    path,
                )
            )
        measure_tasks = _string_list(measure["task_ids"], non_empty=True)
        if measure_tasks is None or not set(measure_tasks).issubset(task_ids):
            failures.append(
                _failure(
                    "dsl-evaluation-measure-join",
                    f"{measure['measure_id']}: invalid task ids",
                    path,
                )
            )
        elif not all(
            set(measure_dimensions or []) & set(task["dimension_ids"])
            for task in tasks
            if isinstance(task, Mapping)
            and task.get("task_id") in measure_tasks
            and _string_list(task.get("dimension_ids"), non_empty=True) is not None
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-measure-join",
                    f"{measure['measure_id']}: task applicability must share a measured dimension",
                    path,
                )
            )
        applicability = _bounded_list(
            measure["stage_applicability"],
            _MAX_CATALOG_ITEMS,
            failures,
            rule_id="dsl-evaluation-measure-stage-applicability",
            label=f"measures[{index}].stage_applicability",
            path=path,
        )
        actual_stage_pairs: set[tuple[str, str]] = set()
        duplicate_stage_pairs: set[tuple[str, str]] = set()
        for applicability_index, declaration in enumerate(applicability):
            if not _exact_keys(
                declaration,
                _STAGE_APPLICABILITY_KEYS,
                failures,
                rule_id="dsl-evaluation-measure-stage-applicability",
                label=(f"measures[{index}].stage_applicability[{applicability_index}]"),
                path=path,
            ):
                continue
            task_id = declaration["task_id"]
            task = tasks_by_id.get(task_id) if isinstance(task_id, str) else None
            declaration_variants = _string_list(declaration["variant_ids"], non_empty=True)
            declaration_stages = _string_list(declaration["artifact_stage_ids"], non_empty=True)
            task_variants = (
                set(_string_list(task.get("variant_ids"), non_empty=True) or []) if task is not None else set()
            )
            task_stages = (
                set(_string_list(task.get("artifact_stage_ids"), non_empty=True) or []) if task is not None else set()
            )
            if (
                task is None
                or measure_tasks is None
                or task_id not in measure_tasks
                or declaration_variants is None
                or not set(declaration_variants).issubset(task_variants)
                or declaration_stages is None
                or not set(declaration_stages).issubset(task_stages)
            ):
                failures.append(
                    _failure(
                        "dsl-evaluation-measure-stage-applicability",
                        f"{measure['measure_id']}: invalid task, variant, or stage applicability",
                        path,
                    )
                )
                continue
            for variant_id in declaration_variants:
                pair = (task_id, variant_id)
                if pair in actual_stage_pairs:
                    duplicate_stage_pairs.add(pair)
                actual_stage_pairs.add(pair)
        expected_stage_pairs = {
            (task_id, variant_id)
            for task_id in (measure_tasks or [])
            for variant_id in (_string_list(tasks_by_id.get(task_id, {}).get("variant_ids"), non_empty=True) or [])
        }
        if actual_stage_pairs != expected_stage_pairs or duplicate_stage_pairs:
            failures.append(
                _failure(
                    "dsl-evaluation-measure-stage-coverage",
                    f"{measure['measure_id']}: every task/variant requires one stage declaration",
                    path,
                )
            )
    threshold_ids = _record_ids(
        thresholds,
        "dimension_id",
        failures,
        rule_id="dsl-evaluation-threshold-id",
        label="threshold",
        path=path,
    )
    for index, threshold in enumerate(thresholds):
        if not _exact_keys(
            threshold,
            _THRESHOLD_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"thresholds[{index}]",
            path=path,
        ):
            continue
        conditions = _bounded_list(
            threshold["conditions"],
            16,
            failures,
            rule_id="dsl-evaluation-threshold-shape",
            label=f"thresholds[{index}].conditions",
            path=path,
        )
        if threshold["logic"] != "all" or not conditions:
            failures.append(
                _failure(
                    "dsl-evaluation-threshold-shape",
                    f"{threshold['dimension_id']}: threshold requires non-empty all conditions",
                    path,
                )
            )
        for condition_index, condition in enumerate(conditions):
            if not _exact_keys(
                condition,
                _THRESHOLD_CONDITION_KEYS,
                failures,
                rule_id="dsl-evaluation-threshold-shape",
                label=f"thresholds[{index}].conditions[{condition_index}]",
                path=path,
            ):
                continue
            if (
                not isinstance(condition["measure_id"], str)
                or condition["measure_id"] not in measure_ids
                or not isinstance(condition["operator"], str)
                or condition["operator"] not in {">=", "<=", "=="}
                or isinstance(condition["target"], bool)
                or not isinstance(condition["target"], (int, float))
            ):
                failures.append(
                    _failure(
                        "dsl-evaluation-threshold-join",
                        f"{threshold['dimension_id']}: invalid measure, operator, or target",
                        path,
                    )
                )
    if threshold_ids != dimension_ids:
        failures.append(
            _failure(
                "dsl-evaluation-threshold-coverage",
                "every dimension requires exactly one preregistered threshold",
                path,
            )
        )

    if _exact_keys(
        protocol["sampling_plan"],
        _SAMPLING_KEYS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="sampling_plan",
        path=path,
    ):
        sampling = protocol["sampling_plan"]
        minimum = sampling["minimum_per_persona"]
        target = sampling["target_total"]
        if not isinstance(minimum, int) or minimum < 1 or not isinstance(target, int):
            failures.append(_failure("dsl-evaluation-sampling-plan", "invalid sample sizes", path))
        elif target < sum(
            item.get("minimum_completed_subjects", 0)
            for item in personas
            if isinstance(item, Mapping) and isinstance(item.get("minimum_completed_subjects"), int)
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-sampling-plan",
                    "target_total cannot cover the required per-persona minimum",
                    path,
                )
            )
    if _exact_keys(
        protocol["execution_plan"],
        _EXECUTION_PLAN_KEYS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="execution_plan",
        path=path,
    ):
        execution_plan = protocol["execution_plan"]
        requirements = _bounded_list(
            execution_plan["subject_task_requirements"],
            16,
            failures,
            rule_id="dsl-evaluation-subject-workload-plan",
            label="execution_plan.subject_task_requirements",
            path=path,
        )
        requirement_ids = _record_ids(
            requirements,
            "requirement_id",
            failures,
            rule_id="dsl-evaluation-subject-workload-plan",
            label="subject task requirement",
            path=path,
        )
        declared_kinds: set[str] = set()
        duplicate_kinds: set[str] = set()
        for index, requirement in enumerate(requirements):
            if not _exact_keys(
                requirement,
                _SUBJECT_TASK_REQUIREMENT_KEYS,
                failures,
                rule_id="dsl-evaluation-subject-workload-plan",
                label=f"execution_plan.subject_task_requirements[{index}]",
                path=path,
            ):
                continue
            task_kind_values = _string_list(requirement["task_kinds"], non_empty=True)
            minimum = requirement["minimum_assigned_attempts"]
            if (
                task_kind_values is None
                or not set(task_kind_values).issubset(REQUIRED_TASK_KINDS)
                or isinstance(minimum, bool)
                or not isinstance(minimum, int)
                or minimum < 1
            ):
                failures.append(
                    _failure(
                        "dsl-evaluation-subject-workload-plan",
                        f"{requirement['requirement_id']}: invalid task kinds or minimum",
                        path,
                    )
                )
                continue
            overlap = declared_kinds & set(task_kind_values)
            duplicate_kinds.update(overlap)
            declared_kinds.update(task_kind_values)
            for persona_id in persona_ids:
                if not any(
                    task.get("kind") in task_kind_values
                    and persona_id in (_string_list(task.get("persona_ids"), non_empty=True) or [])
                    for task in tasks_by_id.values()
                ):
                    failures.append(
                        _failure(
                            "dsl-evaluation-subject-workload-plan",
                            f"{requirement['requirement_id']}: no eligible task for {persona_id}",
                            path,
                        )
                    )
        if not requirement_ids or declared_kinds != REQUIRED_TASK_KINDS or duplicate_kinds:
            failures.append(
                _failure(
                    "dsl-evaluation-subject-workload-plan",
                    "subject task requirements must partition every required task kind",
                    path,
                )
            )
    _exact_keys(
        protocol["ethics_and_privacy"],
        _ETHICS_KEYS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="ethics_and_privacy",
        path=path,
    )
    if not protocol["validity_threats"] or not protocol["analysis_plan"]:
        failures.append(
            _failure(
                "dsl-evaluation-preregistration",
                "validity threats and the analysis plan must be preregistered",
                path,
            )
        )
    if not isinstance(protocol["amendment_log"], list):
        failures.append(_failure("dsl-evaluation-protocol-shape", "amendment_log must be a list", path))
    return {
        "dimension_ids": dimension_ids,
        "persona_ids": persona_ids,
        "condition_ids": condition_ids,
        "stage_ids": stage_ids,
        "task_ids": task_ids,
        "variant_ids": variant_ids,
        "measure_ids": measure_ids,
    }


def _validate_snapshot(
    repo_root: Path,
    protocol: Mapping[str, object],
    snapshot: dict[str, object],
    catalogs: Mapping[str, set[str]],
    scope: Mapping[str, set[str]],
    failures: list[PolicyFailure],
    *,
    path: str = "docs/research/dsl-language-evaluation/execution-snapshot-v1.json",
) -> set[str]:
    if not _exact_keys(
        snapshot,
        _SNAPSHOT_KEYS,
        failures,
        rule_id="dsl-evaluation-snapshot-shape",
        label="snapshot",
        path=path,
    ):
        return set()
    if snapshot["protocol_revision"] != protocol.get("revision"):
        failures.append(_failure("dsl-evaluation-snapshot-join", "protocol revision mismatch", path))
    if not isinstance(snapshot["aces_revision"], str) or not _SHA_RE.fullmatch(snapshot["aces_revision"]):
        failures.append(
            _failure(
                "dsl-evaluation-snapshot-pin",
                "ACES revision must be full Git SHA",
                path,
            )
        )
    if snapshot["execution_status"] not in {"not_started", "in_progress", "complete"}:
        failures.append(_failure("dsl-evaluation-snapshot-status", "invalid execution status", path))

    surfaces = _bounded_list(
        snapshot["public_surface"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-snapshot-shape",
        label="public_surface",
        path=path,
    )
    _record_ids(
        surfaces,
        "surface_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="public surface",
        path=path,
    )
    for index, surface in enumerate(surfaces):
        if not _exact_keys(
            surface,
            _SURFACE_KEYS,
            failures,
            rule_id="dsl-evaluation-snapshot-shape",
            label=f"public_surface[{index}]",
            path=path,
        ):
            continue
        artifact = surface["artifact"]
        resolved = _resolve_repository_artifact(repo_root, artifact) if isinstance(artifact, str) else None
        if resolved is None or not resolved.exists():
            failures.append(
                _failure(
                    "dsl-evaluation-public-surface-path",
                    f"{surface['surface_id']}: unsafe or missing artifact",
                    path,
                )
            )
    _exact_keys(
        snapshot["ethics_review"],
        _ETHICS_REVIEW_KEYS,
        failures,
        rule_id="dsl-evaluation-snapshot-shape",
        label="ethics_review",
        path=path,
    )

    record_fields = {
        "subjects": _SUBJECT_KEYS,
        "attempts": _ATTEMPT_KEYS,
        "observations": _OBSERVATION_KEYS,
        "reviews": _REVIEW_KEYS,
        "deviations": _DEVIATION_KEYS,
        "withdrawals": _WITHDRAWAL_KEYS,
        "disagreements": _DISAGREEMENT_KEYS,
    }
    records: dict[str, list[object]] = {}
    for field, keys in record_fields.items():
        records[field] = _bounded_list(
            snapshot[field],
            _MAX_EXECUTION_RECORDS,
            failures,
            rule_id="dsl-evaluation-snapshot-shape",
            label=field,
            path=path,
        )
        for index, record in enumerate(records[field]):
            _exact_keys(
                record,
                keys,
                failures,
                rule_id="dsl-evaluation-snapshot-shape",
                label=f"{field}[{index}]",
                path=path,
            )
    if snapshot["execution_status"] == "not_started":
        populated = sorted(field for field, value in records.items() if value)
        if populated:
            failures.append(
                _failure(
                    "dsl-evaluation-not-started-observations",
                    f"not-started snapshot contains execution records: {populated}",
                    path,
                )
            )
        ethics = snapshot["ethics_review"]
        if isinstance(ethics, Mapping) and ethics.get("status") not in {
            "pending",
            "not_required",
        }:
            failures.append(
                _failure(
                    "dsl-evaluation-ethics-state",
                    "not-started snapshot must remain pending or explicitly not-required",
                    path,
                )
            )
        return set()

    subjects = records["subjects"]
    attempts = records["attempts"]
    observations = records["observations"]
    reviews = records["reviews"]
    withdrawals = records["withdrawals"]
    tasks = _protocol_records_by_id(protocol, "tasks", "task_id")
    variants = _protocol_records_by_id(protocol, "variants", "variant_id")
    measures = _protocol_records_by_id(protocol, "measures", "measure_id")

    _record_ids(
        subjects,
        "subject_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="subject",
        path=path,
    )
    attempt_ids = _record_ids(
        attempts,
        "attempt_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="attempt",
        path=path,
    )
    observation_ids = _record_ids(
        observations,
        "observation_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="observation",
        path=path,
    )
    review_ids = _record_ids(
        reviews,
        "review_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="review",
        path=path,
    )
    withdrawal_subject_ids = _record_ids(
        withdrawals,
        "subject_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="withdrawal",
        path=path,
    )

    subjects_by_id = {
        subject["subject_id"]: subject
        for subject in subjects
        if isinstance(subject, Mapping) and set(subject) == _SUBJECT_KEYS and isinstance(subject.get("subject_id"), str)
    }
    sampling_plan = protocol.get("sampling_plan")
    experience_bands = set()
    if isinstance(sampling_plan, Mapping):
        experience_bands = set(_string_list(sampling_plan.get("experience_bands"), non_empty=True) or [])
    for subject_id, subject in subjects_by_id.items():
        if subject.get("persona_id") not in catalogs.get("persona_ids", set()):
            failures.append(_failure("dsl-evaluation-subject-join", f"{subject_id}: unknown persona", path))
        if subject.get("consent_status") not in {"consented", "withdrawn"}:
            failures.append(_failure("dsl-evaluation-consent-status", f"{subject_id}: invalid consent status", path))
        if (
            not _bounded_text(subject.get("experience_band"), maximum=200)
            or subject.get("experience_band") not in experience_bands
        ):
            failures.append(_failure("dsl-evaluation-subject-shape", f"{subject_id}: invalid experience band", path))
    declared_withdrawn_subjects = {
        subject_id for subject_id, subject in subjects_by_id.items() if subject.get("consent_status") == "withdrawn"
    }
    if withdrawal_subject_ids != declared_withdrawn_subjects:
        failures.append(
            _failure(
                "dsl-evaluation-withdrawal-join",
                "withdrawal records must exactly match subjects with withdrawn consent",
                path,
            )
        )
    for withdrawal in withdrawals:
        if not isinstance(withdrawal, Mapping) or set(withdrawal) != _WITHDRAWAL_KEYS:
            continue
        if (
            not _bounded_text(withdrawal.get("recorded_at"), maximum=100)
            or withdrawal.get("retained_aggregate_only") is not True
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-withdrawal-shape",
                    f"{withdrawal.get('subject_id')}: withdrawal must retain aggregate counts only",
                    path,
                )
            )

    attempts_by_id: dict[str, Mapping[str, object]] = {}
    for attempt in attempts:
        if not isinstance(attempt, Mapping) or set(attempt) != _ATTEMPT_KEYS:
            continue
        attempt_id = attempt.get("attempt_id")
        if not isinstance(attempt_id, str):
            continue
        attempts_by_id[attempt_id] = attempt
        task_id = attempt.get("task_id")
        task = tasks.get(task_id) if isinstance(task_id, str) else None
        subject_id = attempt.get("subject_id")
        subject = subjects_by_id.get(subject_id) if isinstance(subject_id, str) else None
        outcome = attempt.get("outcome")
        if outcome not in ATTEMPT_OUTCOMES:
            failures.append(_failure("dsl-evaluation-attempt-outcome", f"{attempt_id}: invalid outcome", path))
        if task is None or subject is None:
            failures.append(_failure("dsl-evaluation-attempt-join", f"{attempt_id}: unknown task or subject", path))
            continue
        task_personas = _string_list(task.get("persona_ids"), non_empty=True) or []
        task_conditions = _string_list(task.get("tooling_condition_ids"), non_empty=True) or []
        task_variants = _string_list(task.get("variant_ids"), non_empty=True) or []
        if (
            attempt.get("persona_id") != subject.get("persona_id")
            or attempt.get("persona_id") not in task_personas
            or attempt.get("tooling_condition_id") not in task_conditions
            or attempt.get("variant_id") not in task_variants
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-attempt-join",
                    f"{attempt_id}: subject, persona, task, condition, or variant mismatch",
                    path,
                )
            )
        variant = variants.get(attempt.get("variant_id"))
        if variant is None or variant.get("task_id") != task_id:
            failures.append(
                _failure("dsl-evaluation-attempt-join", f"{attempt_id}: variant belongs to another task", path)
            )
        withdrawn = subject_id in withdrawal_subject_ids
        if withdrawn != (outcome == "withdrawn"):
            failures.append(
                _failure(
                    "dsl-evaluation-withdrawal-join",
                    f"{attempt_id}: withdrawn subject and attempt outcome disagree",
                    path,
                )
            )
        if not _valid_id(attempt.get("study_run_id")):
            failures.append(_failure("dsl-evaluation-attempt-identity", f"{attempt_id}: invalid study run id", path))
        if not _bounded_text(attempt.get("started_at"), maximum=100) or not _bounded_text(
            attempt.get("ended_at"), maximum=100
        ):
            failures.append(_failure("dsl-evaluation-attempt-identity", f"{attempt_id}: timestamps must be text", path))
        if _string_list(attempt.get("observation_ids")) is None:
            failures.append(
                _failure("dsl-evaluation-attempt-observation-join", f"{attempt_id}: invalid observation ids", path)
            )

    observations_by_opportunity: dict[tuple[str, str, str], Mapping[str, object]] = {}
    child_observations: dict[str, set[str]] = {attempt_id: set() for attempt_id in attempt_ids}
    for observation in observations:
        if not isinstance(observation, Mapping) or set(observation) != _OBSERVATION_KEYS:
            continue
        observation_id = observation.get("observation_id")
        attempt_id = observation.get("attempt_id")
        measure_id = observation.get("measure_id")
        artifact_stage = observation.get("artifact_stage")
        if (
            not isinstance(observation_id, str)
            or not isinstance(attempt_id, str)
            or not isinstance(measure_id, str)
            or not isinstance(artifact_stage, str)
        ):
            failures.append(
                _failure("dsl-evaluation-observation-identity", "observation identity fields must be text", path)
            )
            continue
        opportunity = (attempt_id, measure_id, artifact_stage)
        observation_dimensions = _string_list(observation.get("dimension_ids"), non_empty=True)
        if opportunity in observations_by_opportunity:
            failures.append(
                _failure(
                    "dsl-evaluation-observation-identity",
                    f"duplicate attempt-measure-stage observation at {observation_id}",
                    path,
                )
            )
        observations_by_opportunity[opportunity] = observation
        child_observations.setdefault(attempt_id, set()).add(observation_id)
        attempt = attempts_by_id.get(attempt_id)
        measure = measures.get(measure_id)
        task = tasks.get(observation.get("task_id"))
        if attempt is None or measure is None or task is None:
            failures.append(
                _failure(
                    "dsl-evaluation-observation-join",
                    f"{observation_id}: unknown parent attempt, task, or measure",
                    path,
                )
            )
            continue
        parent_fields = (
            "study_run_id",
            "task_id",
            "persona_id",
            "subject_id",
            "tooling_condition_id",
            "variant_id",
            "outcome",
        )
        if observation.get("protocol_revision") != protocol.get("revision") or any(
            observation.get(field) != attempt.get(field) for field in parent_fields
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-observation-parent-join",
                    f"{observation_id}: observation does not match its parent attempt",
                    path,
                )
            )
        task_stages = _string_list(task.get("artifact_stage_ids"), non_empty=True) or []
        measure_tasks = _string_list(measure.get("task_ids"), non_empty=True) or []
        task_dimensions = set(_string_list(task.get("dimension_ids"), non_empty=True) or [])
        measure_dimensions = set(_string_list(measure.get("dimension_ids"), non_empty=True) or [])
        expected_dimensions = task_dimensions & measure_dimensions
        parent_task_id = attempt.get("task_id")
        parent_variant_id = attempt.get("variant_id")
        try:
            applicable_stages = (
                _measure_stage_ids(measure, parent_task_id, parent_variant_id)
                if isinstance(parent_task_id, str) and isinstance(parent_variant_id, str)
                else []
            )
        except ValueError:
            applicable_stages = []
        if (
            artifact_stage not in task_stages
            or artifact_stage not in applicable_stages
            or observation.get("task_id") not in measure_tasks
            or observation_dimensions is None
            or set(observation_dimensions) != expected_dimensions
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-observation-task-join",
                    f"{observation_id}: stage, measure, or dimensions are not declared for the task",
                    path,
                )
            )
        outcome = observation.get("outcome")
        value = observation.get("value")
        if outcome not in OBSERVATION_OUTCOMES:
            failures.append(_failure("dsl-evaluation-observation-outcome", f"{observation_id}: invalid outcome", path))
        if measure_id == "task-completion":
            expected_value = 1 if outcome == "completed" else 0
            valid_value = value == expected_value and not isinstance(value, bool)
        elif outcome in {"completed", "failed"}:
            valid_value = not isinstance(value, bool) and isinstance(value, (int, float))
        else:
            valid_value = value is None
        if not valid_value:
            failures.append(
                _failure(
                    "dsl-evaluation-observation-value",
                    f"{observation_id}: value does not represent its attempt outcome",
                    path,
                )
            )
        refs = _string_list(observation.get("evidence_refs"))
        if refs is None or any(safe_repo_path(repo_root, ref) is None for ref in refs):
            failures.append(
                _failure(
                    "dsl-evaluation-observation-evidence",
                    f"{observation_id}: evidence refs must be repository-confined paths",
                    path,
                )
            )

    expected_opportunities: set[tuple[str, str, str]] = set()
    withdrawn_opportunities: set[tuple[str, str, str]] = set()
    for attempt_id, attempt in attempts_by_id.items():
        task_id = attempt.get("task_id")
        variant_id = attempt.get("variant_id")
        for measure_id, measure in measures.items():
            measure_tasks = _string_list(measure.get("task_ids"), non_empty=True) or []
            if task_id not in measure_tasks or not isinstance(task_id, str) or not isinstance(variant_id, str):
                continue
            try:
                applicable_stages = _measure_stage_ids(measure, task_id, variant_id)
            except ValueError:
                continue
            for artifact_stage in applicable_stages:
                opportunity = (attempt_id, measure_id, artifact_stage)
                if attempt.get("outcome") == "withdrawn":
                    withdrawn_opportunities.add(opportunity)
                else:
                    expected_opportunities.add(opportunity)
    actual_opportunities = set(observations_by_opportunity)
    if actual_opportunities != expected_opportunities or actual_opportunities & withdrawn_opportunities:
        failures.append(
            _failure(
                "dsl-evaluation-opportunity-coverage",
                "observations must exactly cover every non-withdrawn protocol-declared attempt-measure-stage opportunity",
                path,
            )
        )
    for attempt_id, attempt in attempts_by_id.items():
        stored_ids = _string_list(attempt.get("observation_ids"))
        if stored_ids is not None and set(stored_ids) != child_observations.get(attempt_id, set()):
            failures.append(
                _failure(
                    "dsl-evaluation-attempt-observation-join",
                    f"{attempt_id}: observation ids do not match child records",
                    path,
                )
            )

    reviews_by_attempt: Counter[str] = Counter()
    for review in reviews:
        if not isinstance(review, Mapping) or set(review) != _REVIEW_KEYS:
            continue
        review_id = review.get("review_id")
        attempt_id = review.get("attempt_id")
        attempt = attempts_by_id.get(attempt_id) if isinstance(attempt_id, str) else None
        reviewer_id = review.get("reviewer_subject_id")
        reviewer = subjects_by_id.get(reviewer_id) if isinstance(reviewer_id, str) else None
        if attempt is None or reviewer is None:
            failures.append(_failure("dsl-evaluation-review-join", f"{review_id}: unknown attempt or reviewer", path))
            continue
        task = tasks.get(attempt.get("task_id"))
        task_stages = _string_list(task.get("artifact_stage_ids"), non_empty=True) if task else None
        task_personas = _string_list(task.get("persona_ids"), non_empty=True) if task else None
        if (
            review.get("task_id") != attempt.get("task_id")
            or review.get("variant_id") != attempt.get("variant_id")
            or reviewer_id == attempt.get("subject_id")
            or reviewer.get("consent_status") != "consented"
            or task_stages is None
            or "review-judgment" not in task_stages
            or task_personas is None
            or reviewer.get("persona_id") not in task_personas
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-review-join",
                    f"{review_id}: review does not match an eligible independent reviewer and parent task",
                    path,
                )
            )
        if (
            not _bounded_text(review.get("judgment"), maximum=500)
            or isinstance(review.get("confidence"), bool)
            or not isinstance(review.get("confidence"), (int, float))
            or not 0 <= review["confidence"] <= 1
            or not _valid_id(review.get("rationale_code"))
            or not _bounded_text(review.get("fixed_at"), maximum=100)
        ):
            failures.append(_failure("dsl-evaluation-review-shape", f"{review_id}: invalid fixed judgment", path))
        reviews_by_attempt[attempt_id] += 1

    for disagreement in records["disagreements"]:
        if not isinstance(disagreement, Mapping) or set(disagreement) != _DISAGREEMENT_KEYS:
            continue
        disagreement_review_ids = _string_list(disagreement["review_ids"], non_empty=True)
        linked_reviews = [
            review
            for review in reviews
            if isinstance(review, Mapping)
            and disagreement_review_ids is not None
            and review.get("review_id") in disagreement_review_ids
        ]
        linked_attempts = {review.get("attempt_id") for review in linked_reviews}
        if (
            disagreement_review_ids is None
            or len(disagreement_review_ids) < 2
            or not set(disagreement_review_ids).issubset(review_ids)
            or len(linked_attempts) != 1
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-disagreement-join",
                    f"{disagreement['disagreement_id']}: reviews must share one parent attempt",
                    path,
                )
            )
        if disagreement["originals_preserved"] is not True:
            failures.append(
                _failure(
                    "dsl-evaluation-disagreement-preservation",
                    f"{disagreement['disagreement_id']}: originals must be preserved",
                    path,
                )
            )

    if snapshot["execution_status"] == "complete":
        nonwithdrawn_subject_ids = {
            subject_id
            for subject_id, subject in subjects_by_id.items()
            if subject.get("consent_status") == "consented"
            and subject.get("persona_id") in scope.get("persona_ids", set())
        }
        active_subject_ids = {
            subject_id
            for subject_id in nonwithdrawn_subject_ids
            if any(
                attempt.get("subject_id") == subject_id
                and attempt.get("outcome") != "withdrawn"
                and _attempt_matches_scope(attempt, scope)
                for attempt in attempts_by_id.values()
            )
        }
        persona_minimums = {
            item["persona_id"]: item["minimum_completed_subjects"]
            for item in protocol.get("personas", [])
            if isinstance(item, Mapping)
            and isinstance(item.get("persona_id"), str)
            and isinstance(item.get("minimum_completed_subjects"), int)
            and item["persona_id"] in scope.get("persona_ids", set())
        }
        persona_counts = Counter(subjects_by_id[subject_id]["persona_id"] for subject_id in active_subject_ids)
        missing_personas = sorted(
            persona_id for persona_id, minimum in persona_minimums.items() if persona_counts[persona_id] < minimum
        )
        expected_task_shapes = {
            (task["task_id"], condition_id, variant_id)
            for task in tasks.values()
            if task["task_id"] in scope.get("task_ids", set())
            for condition_id in (_string_list(task.get("tooling_condition_ids"), non_empty=True) or [])
            if condition_id in scope.get("tooling_condition_ids", set())
            for variant_id in (_string_list(task.get("variant_ids"), non_empty=True) or [])
            if variant_id in scope.get("variant_ids", set())
        }
        actual_task_shapes = {
            (attempt.get("task_id"), attempt.get("tooling_condition_id"), attempt.get("variant_id"))
            for attempt in attempts_by_id.values()
            if attempt.get("outcome") != "withdrawn" and _attempt_matches_scope(attempt, scope)
        }
        review_required_attempts = {
            attempt_id
            for attempt_id, attempt in attempts_by_id.items()
            if _attempt_matches_scope(attempt, scope)
            if "review-judgment"
            in (_string_list(tasks.get(attempt.get("task_id"), {}).get("artifact_stage_ids"), non_empty=True) or [])
            and attempt.get("outcome") != "withdrawn"
        }
        sampling_plan = protocol.get("sampling_plan", {})
        target_total = sampling_plan.get("target_total") if isinstance(sampling_plan, Mapping) else None
        ethics = snapshot["ethics_review"]
        ethics_approved = isinstance(ethics, Mapping) and ethics.get("status") == "approved"
        execution_plan = protocol.get("execution_plan", {})
        subject_task_requirements = (
            execution_plan.get("subject_task_requirements", []) if isinstance(execution_plan, Mapping) else []
        )
        missing_subject_workloads: list[tuple[str, str]] = []
        if isinstance(subject_task_requirements, list):
            for subject_id in nonwithdrawn_subject_ids:
                subject_attempts = [
                    attempt
                    for attempt in attempts_by_id.values()
                    if attempt.get("subject_id") == subject_id
                    and attempt.get("outcome") != "withdrawn"
                    and _attempt_matches_scope(attempt, scope)
                ]
                for requirement in subject_task_requirements:
                    if not isinstance(requirement, Mapping):
                        continue
                    task_kind_values = _string_list(requirement.get("task_kinds"), non_empty=True)
                    minimum = requirement.get("minimum_assigned_attempts")
                    requirement_id = requirement.get("requirement_id")
                    if (
                        task_kind_values is None
                        or not isinstance(minimum, int)
                        or isinstance(minimum, bool)
                        or not isinstance(requirement_id, str)
                    ):
                        continue
                    assigned = sum(
                        tasks.get(attempt.get("task_id"), {}).get("kind") in task_kind_values
                        for attempt in subject_attempts
                    )
                    if assigned < minimum:
                        missing_subject_workloads.append((subject_id, requirement_id))
        if missing_subject_workloads:
            failures.append(
                _failure(
                    "dsl-evaluation-subject-workload",
                    "complete execution does not satisfy every active subject's assigned task groups",
                    path,
                )
            )
        if (
            not ethics_approved
            or missing_personas
            or not isinstance(target_total, int)
            or len(active_subject_ids) < target_total
            or not expected_task_shapes.issubset(actual_task_shapes)
            or any(reviews_by_attempt[attempt_id] == 0 for attempt_id in review_required_attempts)
            or missing_subject_workloads
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-completion-coverage",
                    "complete execution lacks approved ethics, subject workload/minima, task/condition/variant coverage, or required independent reviews",
                    path,
                )
            )
    return observation_ids


def _validate_analysis(
    repo_root: Path,
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    analysis: dict[str, object],
    catalogs: Mapping[str, set[str]],
    scope: Mapping[str, set[str]],
    strata: Sequence[Mapping[str, object]],
    observation_ids: set[str],
    failures: list[PolicyFailure],
    *,
    path: str = "docs/research/dsl-language-evaluation/analysis-v1.json",
) -> None:
    if not _exact_keys(
        analysis,
        _ANALYSIS_KEYS,
        failures,
        rule_id="dsl-evaluation-analysis-shape",
        label="analysis",
        path=path,
    ):
        return
    if analysis["protocol_revision"] != protocol.get("revision"):
        failures.append(_failure("dsl-evaluation-analysis-join", "protocol revision mismatch", path))
    if analysis["snapshot_id"] != snapshot.get("snapshot_id"):
        failures.append(_failure("dsl-evaluation-analysis-join", "snapshot id mismatch", path))
    if analysis["execution_status"] != snapshot.get("execution_status"):
        failures.append(_failure("dsl-evaluation-analysis-join", "execution status mismatch", path))
    if analysis["evidence_status"] not in EVIDENCE_STATUSES:
        failures.append(_failure("dsl-evaluation-evidence-status", "invalid evidence status", path))

    measure_results = _bounded_list(
        analysis["measure_results"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-analysis-shape",
        label="measure_results",
        path=path,
    )
    measure_result_ids = _record_ids(
        measure_results,
        "measure_id",
        failures,
        rule_id="dsl-evaluation-analysis-id",
        label="measure result",
        path=path,
    )
    if measure_result_ids != scope.get("measure_ids", set()):
        failures.append(
            _failure(
                "dsl-evaluation-analysis-measure-coverage",
                "analysis must contain one result for every claim-scoped measure",
                path,
            )
        )
    try:
        recomputed_measures = recompute_measure_results(protocol, snapshot, scope=scope)
    except ValueError as exc:
        failures.append(_failure("dsl-evaluation-observation-value", str(exc), path))
        recomputed_measures = {}
    for index, result in enumerate(measure_results):
        if not _exact_keys(
            result,
            _MEASURE_RESULT_KEYS,
            failures,
            rule_id="dsl-evaluation-analysis-shape",
            label=f"measure_results[{index}]",
            path=path,
        ):
            continue
        expected = recomputed_measures.get(result["measure_id"])
        if expected and expected["denominator"] == 0:
            expected_status = "not_evaluated"
        elif expected and expected["observed_count"] != expected["denominator"]:
            expected_status = "incomplete"
        else:
            expected_status = "evaluated"
        if expected is None or result != {
            "measure_id": result["measure_id"],
            "status": expected_status,
            **expected,
        }:
            failures.append(
                _failure(
                    "dsl-evaluation-analysis-measure-drift",
                    f"{result['measure_id']}: stored aggregate does not match frozen observations",
                    path,
                )
            )

    try:
        recomputed_dimensions = recompute_dimension_results(
            protocol,
            recomputed_measures,
            dimension_ids=scope.get("dimension_ids", set()),
        )
    except ValueError as exc:
        failures.append(_failure("dsl-evaluation-threshold-evaluation", str(exc), path))
        recomputed_dimensions = {}

    results = _bounded_list(
        analysis["dimension_results"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-analysis-shape",
        label="dimension_results",
        path=path,
    )
    result_ids = _record_ids(
        results,
        "dimension_id",
        failures,
        rule_id="dsl-evaluation-analysis-id",
        label="dimension result",
        path=path,
    )
    if result_ids != scope.get("dimension_ids", set()):
        failures.append(
            _failure(
                "dsl-evaluation-analysis-dimension-coverage",
                "analysis must contain one result for every claim-scoped dimension",
                path,
            )
        )
    for index, result in enumerate(results):
        if not _exact_keys(
            result,
            _DIMENSION_RESULT_KEYS,
            failures,
            rule_id="dsl-evaluation-analysis-shape",
            label=f"dimension_results[{index}]",
            path=path,
        ):
            continue
        refs = _string_list(result["supporting_observation_ids"])
        if refs is None or not set(refs).issubset(observation_ids):
            failures.append(
                _failure(
                    "dsl-evaluation-analysis-observation-join",
                    f"{result['dimension_id']}: unknown supporting observations",
                    path,
                )
            )
        expected_dimension = recomputed_dimensions.get(result["dimension_id"])
        if expected_dimension is None or result != {
            "dimension_id": result["dimension_id"],
            **expected_dimension,
        }:
            failures.append(
                _failure(
                    "dsl-evaluation-analysis-dimension-drift",
                    f"{result['dimension_id']}: stored threshold result does not match recomputed measures",
                    path,
                )
            )

    stored_strata = _bounded_list(
        analysis["stratum_results"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-analysis-shape",
        label="stratum_results",
        path=path,
    )
    expected_strata: list[dict[str, object]] = []
    if snapshot.get("execution_status") == "not_started":
        if stored_strata:
            failures.append(
                _failure(
                    "dsl-evaluation-stratum-drift",
                    "not-started analysis cannot persist derived stratum results",
                    path,
                )
            )
    else:
        try:
            expected_strata = recompute_stratum_results(protocol, snapshot, strata)
        except ValueError as exc:
            failures.append(_failure("dsl-evaluation-stratum-drift", str(exc), path))
        expected_by_id = {item["stratum_id"]: item for item in expected_strata}
        stored_ids = _record_ids(
            stored_strata,
            "stratum_id",
            failures,
            rule_id="dsl-evaluation-analysis-id",
            label="stratum result",
            path=path,
        )
        if stored_ids != set(expected_by_id):
            failures.append(
                _failure(
                    "dsl-evaluation-stratum-coverage",
                    "analysis must persist one independently recomputed result for every bound stratum",
                    path,
                )
            )
        for index, result in enumerate(stored_strata):
            if not _exact_keys(
                result,
                _STRATUM_RESULT_KEYS,
                failures,
                rule_id="dsl-evaluation-analysis-shape",
                label=f"stratum_results[{index}]",
                path=path,
            ):
                continue
            assert isinstance(result, dict)
            if result != expected_by_id.get(result["stratum_id"]):
                failures.append(
                    _failure(
                        "dsl-evaluation-stratum-drift",
                        f"{result['stratum_id']}: stored stratum result does not match frozen observations",
                        path,
                    )
                )
    claim = analysis["claim"]
    if _exact_keys(
        claim,
        _CLAIM_KEYS,
        failures,
        rule_id="dsl-evaluation-analysis-shape",
        label="claim",
        path=path,
    ):
        evidence_artifacts = claim["evidence_artifacts"]
        if not isinstance(evidence_artifacts, list) or len(evidence_artifacts) != 3:
            failures.append(
                _failure(
                    "dsl-evaluation-claim-evidence",
                    "claim must name protocol, snapshot, and analysis artifacts",
                    path,
                )
            )
        else:
            for artifact in evidence_artifacts:
                resolved = safe_repo_path(repo_root, artifact) if isinstance(artifact, str) else None
                if resolved is None or not resolved.is_file():
                    failures.append(
                        _failure(
                            "dsl-evaluation-claim-evidence-path",
                            f"unsafe or missing claim evidence artifact {artifact!r}",
                            path,
                        )
                    )
    status = analysis["evidence_status"]
    if snapshot.get("execution_status") == "not_started":
        if status != "untested":
            failures.append(
                _failure(
                    "dsl-evaluation-evidence-status",
                    "not-started execution must remain untested",
                    path,
                )
            )
        for result in results:
            if not isinstance(result, Mapping):
                continue
            expected = {
                "status": "not_evaluated",
                "threshold_result": "not_evaluated",
                "condition_results": [],
                "supporting_observation_ids": [],
            }
            if any(result.get(field) != value for field, value in expected.items()):
                failures.append(
                    _failure(
                        "dsl-evaluation-not-started-analysis",
                        f"{result.get('dimension_id')}: not-started result contains derived evidence",
                        path,
                    )
                )
    gating_strata = [item for item in expected_strata if item.get("role") == "gating"]
    gating_dimensions = [
        item.get("dimension_results", []) for item in gating_strata if isinstance(item.get("dimension_results"), list)
    ]
    all_pass = (
        bool(gating_strata)
        and len(gating_dimensions) == len(gating_strata)
        and all(
            dimension_results
            and all(
                isinstance(result, Mapping)
                and result.get("status") == "evaluated"
                and result.get("threshold_result") == "pass"
                for result in dimension_results
            )
            for dimension_results in gating_dimensions
        )
    )
    any_fail = any(
        isinstance(result, Mapping) and result.get("status") == "evaluated" and result.get("threshold_result") == "fail"
        for dimension_results in gating_dimensions
        for result in dimension_results
    )
    unresolved = any(
        isinstance(item, Mapping) and item.get("status") == "unresolved" for item in snapshot.get("disagreements", [])
    )
    invalidating_deviation = any(
        isinstance(item, Mapping) and item.get("severity") == "invalidating" for item in snapshot.get("deviations", [])
    )
    execution_complete = snapshot.get("execution_status") == "complete"
    qualifies_demonstrated = execution_complete and all_pass and not unresolved and not invalidating_deviation
    qualifies_refuted = execution_complete and any_fail
    execution_records_present = any(
        isinstance(snapshot.get(field), list) and bool(snapshot[field])
        for field in ("subjects", "attempts", "observations", "reviews", "deviations", "withdrawals")
    )
    if status == "demonstrated" and not qualifies_demonstrated:
        failures.append(
            _failure(
                "dsl-evaluation-evidence-status",
                "demonstrated requires every bound gating stratum to pass without unresolved critical disagreement or invalidating deviation",
                path,
            )
        )
    elif status == "refuted" and not qualifies_refuted:
        failures.append(
            _failure(
                "dsl-evaluation-evidence-status",
                "refuted requires a complete execution with at least one gating-stratum dimension failure",
                path,
            )
        )
    elif status == "partial" and (
        snapshot.get("execution_status") == "not_started"
        or not execution_records_present
        or qualifies_demonstrated
        or qualifies_refuted
    ):
        failures.append(
            _failure(
                "dsl-evaluation-evidence-status",
                "partial requires relevant execution evidence that is not yet a demonstrated or refuted result",
                path,
            )
        )
    elif status == "untested" and snapshot.get("execution_status") != "not_started":
        failures.append(
            _failure(
                "dsl-evaluation-evidence-status",
                "untested is reserved for a not-started execution without evidence records",
                path,
            )
        )


def validate_bundle(
    repo_root: Path,
    protocol: dict[str, object],
    snapshot: dict[str, object],
    analysis: dict[str, object],
    *,
    artifact_paths: Mapping[str, object] | None = None,
) -> list[PolicyFailure]:
    """Validate closed shapes, preregistration, joins, and evidence-status honesty."""

    failures: list[PolicyFailure] = []
    paths = artifact_paths or {}
    protocol_path = paths.get("protocol_path")
    snapshot_path = paths.get("snapshot_path")
    analysis_path = paths.get("analysis_path")
    claim_binding = paths.get("claim_binding")
    if claim_binding is None:
        claim = analysis.get("claim")
        claim_id = claim.get("claim_id") if isinstance(claim, Mapping) else None
        try:
            claim_binding = next(
                entry[0]["claim_binding"]
                for entry in load_bundles(repo_root)
                if isinstance(entry[0].get("claim_binding"), Mapping)
                and entry[0]["claim_binding"].get("claim_id") == claim_id
            )
        except (OSError, ValueError, json.JSONDecodeError, StopIteration):
            claim_binding = None
    catalogs = _validate_protocol(
        repo_root,
        protocol,
        failures,
        path=protocol_path
        if isinstance(protocol_path, str)
        else "docs/research/dsl-language-evaluation/protocol-v1.json",
    )
    scope = _validate_claim_scope(
        protocol,
        analysis,
        catalogs,
        failures,
        path=analysis_path
        if isinstance(analysis_path, str)
        else "docs/research/dsl-language-evaluation/analysis-v1.json",
    )
    strata = _validate_claim_binding(
        protocol,
        analysis,
        claim_binding,
        catalogs,
        scope,
        failures,
        path=analysis_path
        if isinstance(analysis_path, str)
        else "docs/research/dsl-language-evaluation/analysis-v1.json",
    )
    observation_ids = _validate_snapshot(
        repo_root,
        protocol,
        snapshot,
        catalogs,
        scope,
        failures,
        path=(
            snapshot_path
            if isinstance(snapshot_path, str)
            else "docs/research/dsl-language-evaluation/execution-snapshot-v1.json"
        ),
    )
    _validate_analysis(
        repo_root,
        protocol,
        snapshot,
        analysis,
        catalogs,
        scope,
        strata,
        observation_ids,
        failures,
        path=analysis_path
        if isinstance(analysis_path, str)
        else "docs/research/dsl-language-evaluation/analysis-v1.json",
    )
    return failures


def load_bundle(
    repo_root: Path = REPO_ROOT,
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    """Load the primary compatibility bundle selected by the manifest."""

    return load_bundles(repo_root)[0]


def _load_bundle_entry(
    repo_root: Path,
    entry: dict[str, object],
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    if set(entry) != _BUNDLE_ENTRY_KEYS:
        raise ValueError(f"bundle entry fields must exactly match {sorted(_BUNDLE_ENTRY_KEYS)}; got {sorted(entry)}")
    paths: list[str] = []
    for field in ("protocol_path", "snapshot_path", "analysis_path"):
        value = entry[field]
        if not isinstance(value, str) or safe_repo_path(repo_root, value) is None:
            raise ValueError(f"bundle entry contains unsafe {field}")
        paths.append(value)
    protocol, snapshot, analysis = (
        load_bounded_json_object(repo_root, path, max_bytes=_MAX_FILE_BYTES) for path in paths
    )
    return entry, protocol, snapshot, analysis


def load_bundles(
    repo_root: Path = REPO_ROOT,
) -> list[tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]]:
    """Load every independently revisioned claim bundle named by the manifest."""

    manifest = load_bounded_json_object(repo_root, MANIFEST_PATH, max_bytes=_MAX_FILE_BYTES)
    if set(manifest) != _MANIFEST_KEYS:
        raise ValueError(
            f"{MANIFEST_PATH!r} fields must exactly match {sorted(_MANIFEST_KEYS)}; got {sorted(manifest)}"
        )
    supplemental = manifest["supplemental_bundles"]
    if not isinstance(supplemental, list) or len(supplemental) > 32:
        raise ValueError(f"{MANIFEST_PATH!r} supplemental_bundles must be a list with at most 32 entries")
    primary = {field: manifest[field] for field in _BUNDLE_ENTRY_KEYS}
    entries = [primary]
    for index, entry in enumerate(supplemental):
        if not isinstance(entry, dict):
            raise ValueError(f"{MANIFEST_PATH!r} supplemental_bundles[{index}] must be an object")
        entries.append(entry)
    bundle_ids = [entry.get("bundle_id") for entry in entries]
    if any(not _valid_id(bundle_id) for bundle_id in bundle_ids) or len(bundle_ids) != len(set(bundle_ids)):
        raise ValueError(f"{MANIFEST_PATH!r} bundle ids must be unique stable ids")
    return [_load_bundle_entry(repo_root, entry) for entry in entries]


def evaluate(repo_root: Path = REPO_ROOT) -> list[PolicyFailure]:
    try:
        bundles = load_bundles(repo_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [_failure("dsl-evaluation-bundle-invalid", str(exc), MANIFEST_PATH)]
    failures: list[PolicyFailure] = []
    for entry, protocol, snapshot, analysis in bundles:
        failures.extend(validate_bundle(repo_root, protocol, snapshot, analysis, artifact_paths=entry))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON")
    args = parser.parse_args()
    failures = evaluate(REPO_ROOT)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "rule_id": failure.rule_id,
                        "message": failure.message,
                        "path": failure.path,
                    }
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
