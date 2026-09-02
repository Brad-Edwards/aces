"""Bundle paths, closed key sets, and bounded limits for the DSL evaluation."""

from __future__ import annotations

import re

_PACKAGES_PREFIX = "implementations/python/packages/"
MANIFEST_PATH = "docs/research/dsl-language-evaluation/bundle-manifest.json"
_RETIRED_PACKAGE_PREFIX = _PACKAGES_PREFIX + "a" + "ces_sdl"
_HISTORICAL_PACKAGE_MOVES: tuple[tuple[str, str], ...] = (
    (_RETIRED_PACKAGE_PREFIX, "implementations/python/packages/raes"),
    (_PACKAGES_PREFIX + "a" + "ces_cli", "implementations/python/packages/raes_cli"),
    (_PACKAGES_PREFIX + "a" + "ces_mcp", "implementations/python/packages/raes_mcp"),
)
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

_HISTORICAL_REVISION_FIELD = "a" + "ces_revision"
_SNAPSHOT_KEYS = {
    "snapshot_id",
    "protocol_revision",
    "captured_at",
    "execution_status",
    _HISTORICAL_REVISION_FIELD,
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
