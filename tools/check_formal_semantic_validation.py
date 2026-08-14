#!/usr/bin/env python3
"""Validate and replay the issue-168 semantic-validation evidence bundle."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, TypeGuard

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.evidence_bundle_index import load_index_records, revision_key  # noqa: E402
from tools.policy.common import (  # noqa: E402
    PolicyFailure,
    load_bounded_json_object,
    safe_repo_path,
)

MANIFEST_PATH = "docs/research/formal-semantic-validation/bundle-manifest.json"
MANIFEST_SCHEMA_VERSION = "formal-semantic-validation-bundle-index/v2"
_MAX_FILE_BYTES = 512 * 1024
_MAX_CASES = 128
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_JsonObject = dict[str, object]

REQUIRED_CLAIM_CLASS_IDS = {
    "schema-validity",
    "semantic-consistency",
    "graph-reachability",
    "constraint-satisfiability",
    "exploit-path-validity",
    "determinism-stability",
    "counterfactual-necessity",
}
REQUIRED_PARTICIPANT_OBLIGATION_IDS = {
    "hidden-vs-visible-projection",
    "fail-closed-action-applicability",
    "shared-state-effects",
    "ordering-before-causality",
    "evidence-labeled-attribution",
    "participant-local-outcome-separation",
    "realization-profile-honesty",
}
EVIDENCE_STATUSES = {"untested", "partial", "demonstrated", "refuted"}
REPLAY_MODES = {"parse", "compile-stability", "compile-distinguish", "unsupported"}
PRODUCTION_EVIDENCE_REPLAY_MODES = {"satisfiability", "exploit-path"}


@dataclasses.dataclass
class EvidenceRelease:
    """One atomically selected and digest-pinned evidence release."""

    manifest_path: str
    manifest: dict[str, object]
    protocol: dict[str, object]
    corpus: dict[str, object]
    snapshot: dict[str, object]
    analysis: dict[str, object]


class ParticipantTestRunner(Protocol):
    """Callable boundary used to replay the participant test evidence."""

    def __call__(self, repo_root: Path, test_refs: list[str]) -> tuple[bool, str]: ...


_MANIFEST_KEYS = {
    "bundle_id",
    "revision",
    "protocol_path",
    "corpus_path",
    "snapshot_path",
    "analysis_path",
    "satisfiability_snapshot_path",
    "satisfiability_analysis_path",
}
_RELEASE_MANIFEST_KEYS = {
    "bundle_id",
    "revision",
    "protocol_path",
    "protocol_sha256",
    "corpus_path",
    "corpus_sha256",
    "snapshot_path",
    "snapshot_sha256",
    "analysis_path",
    "analysis_sha256",
    "artifacts",
}
_RELEASE_ARTIFACT_PIN_KEYS = {"artifact_id", "kind", "path", "sha256"}
_PROTOCOL_KEYS = {
    "protocol_id",
    "revision",
    "registered_at",
    "title",
    "issue_number",
    "requirement_uid",
    "research_question",
    "claim_classes",
    "participant_obligations",
    "evidence_status_values",
    "gate_outcome_values",
    "analysis_rules",
    "amendment_log",
}
_CLAIM_CLASS_KEYS = {
    "claim_class_id",
    "label",
    "boundary",
    "artifact_stage",
    "entrypoint_id",
    "objective_pass_criteria",
    "objective_fail_criteria",
    "allowed_evidence",
    "disallowed_evidence",
    "expected_evidence_status",
}
_PARTICIPANT_KEYS = {
    "obligation_id",
    "label",
    "positive_test_ref",
    "negative_test_ref",
}
_ANALYSIS_RULE_KEYS = {
    "case_coverage",
    "participant_coverage",
    "unsupported_policy",
    "failure_policy",
    "immutability_policy",
}
_CORPUS_KEYS = {"corpus_id", "revision", "cases"}
_CASE_KEYS = {
    "case_id",
    "claim_class_id",
    "polarity",
    "title",
    "artifact_stage",
    "entrypoint_id",
    "fixture_path",
    "comparison_fixture_path",
    "replay_mode",
    "expected_outcome",
    "limitation",
}
_HISTORICAL_REVISION_FIELD = "a" + "ces_revision"
_HISTORICAL_BUNDLE_ID = "a" + "ces-formal-semantic-validation"
_HISTORICAL_SATISFIABILITY_ANALYSIS_PROFILE = "a" + "ces-formal-satisfiability-analysis/v1"
_HISTORICAL_SATISFIABILITY_EXECUTION_PROFILE = "a" + "ces-formal-satisfiability-execution/v1"
_HISTORICAL_SATISFIABILITY_PROFILE = "a" + "ces-finite-domain-satisfiability-v1"
_HISTORICAL_CLI = "implementations/python/.venv/bin/" + "a" + "ces"
_CURRENT_SATISFIABILITY_PROFILE = "raes-finite-domain-satisfiability-v1"
_RENAMED_FORMAL_REPLAY_DIGESTS = {
    "semantic-resolved-objective": (
        "ba0ecbfcb3090ffd6b660cb51324fafcd47ca8dedbbb985e98b6e7f64f8cc25b",
        "5332666a0299d2c303d7a7da4b56dfd309cebf021af187b063ef597cf81bf40a",
    ),
    "compile-repeatability-control": (
        "23b9d84fa757bd80436357ed52569b5445b0e4161641598e4b15c3b18cf6e668",
        "4bb77034a8f2b1a577700ad03772a80acc0f4515a6831c8a35ac1bf50482d760",
    ),
    "compile-non-vacuity-control": (
        "2e92bdb90a218c29201312052b64b7fb88e8a65e887f05168e2273d9710a5080",
        "6cdc44529a87fb9addaf4040795c7f9ae702c5f6ae30e29a5086ee60072ded73",
    ),
}
_HISTORICAL_VM_REPLAY_INPUTS = {
    (
        "semantic-resolved-objective",
        "docs/research/formal-semantic-validation/corpus/semantic-valid.sdl.yaml",
    ): "a074d75b1b420a47a740703deaff45c20ec1c5d846f660412929bc69ab0efb19",
    (
        "semantic-ambiguous-reference",
        "docs/research/formal-semantic-validation/corpus/semantic-invalid-ambiguous-ref.sdl.yaml",
    ): "653cbd2fd62e220d49fb86f80133884207df5ae6752846345ae3085b93f6e4ed",
    (
        "compile-repeatability-control",
        "docs/research/formal-semantic-validation/corpus/determinism-a.sdl.yaml",
    ): "0bc40900d598c1af7a405d798ca19710405e53ced262d8733081abf12edf89fe",
    (
        "compile-non-vacuity-control",
        "docs/research/formal-semantic-validation/corpus/determinism-a.sdl.yaml",
    ): "0bc40900d598c1af7a405d798ca19710405e53ced262d8733081abf12edf89fe",
    (
        "compile-non-vacuity-control",
        "docs/research/formal-semantic-validation/corpus/determinism-b.sdl.yaml",
    ): "d85338f89f20a45515b12da8640173c1a52e47eb17ca0f4f6b4f8f3306e863a1",
}
_RENAMED_SATISFIABILITY_MODEL_DIGESTS = {
    "finite-domain-satisfiable": (
        "sha256:32ac029d9279e6c7ea4cd9082435eb6fa455122bba57498923b8371818ef708c",
        "sha256:fbd664cb97b3f95d89220c967af0c9c55b3bcb60ff755442b54007dad6971423",
    ),
    "finite-domain-unsatisfiable": (
        "sha256:3a061baa67090e312abc4bca7a3ed24cc9458487b67f2fc37b3b7abcac2ecf1b",
        "sha256:525d1520b96cc8a606dcfbc16d4c8c833ef00d6e258aed0a9bd47ba986b33e61",
    ),
    "finite-domain-unsupported": (
        "sha256:2f0f762771dc329419ab739766f684c18261aba28c2fbc50a26ee8ad80224ba5",
        "sha256:9cb311dac08cb20ed21d48d8cd5a4d49c51eb1036a0c6ba97e6f56a88d05ccfa",
    ),
}
_MIGRATED_PRODUCTION_EVIDENCE_DIGESTS = {
    "finite-domain-satisfiable-v2": (
        "sha256:03925bfe0b209c3c77069c97061aa63e8795389be7ed7b78376020b7dc87853c",
        "sha256:60495371aecdd9dff463726e54af424359e09429f8283cd31c1de847bbc38cba",
    ),
    "finite-domain-unsatisfiable-v2": (
        "sha256:c2dc067c406ee9c26837e9565b6b52f8a6268e06e95dbc5937a455700b0c8109",
        "sha256:8816c3a2898193280321559545cfacd462f38172fe7fbe7b005610401563b629",
    ),
    "typed-exploit-path-valid-v2": (
        "sha256:0683b55cd2a52ba626bb5cfbf10de109798d8d31ba467aabd13d4930df204798",
        "sha256:00a7d75ddaf8e21fb82de2ecbff3dfafc29660d0e60829610fcb607d3da5ef0f",
    ),
    "typed-exploit-path-invalid-v2": (
        "sha256:1ec2ff4423088ad2ac6328aba7fbced5cd89b1569cff057e44ad30ef5c5befc0",
        "sha256:74db3e5df9c19fe7a9a203ad3440656229af9df56164d63ec90f0c55e0aab8f2",
    ),
}
_RENAMED_SOLVER_CONFIGURATION_DIGEST = (
    "sha256:63e58f4637dbd8328d84a286e1e5af1f3a69557e5209f683909ce22f39838e7d",
    "sha256:1204635e17e759e9ad3bd6be2ecb28c6de05c07ead6dfdd15936ed5d3d5b81b2",
)
_RETAINED_CASE_TEXT_REPLACEMENTS = {
    "A" + "CES has no governed whole-scenario constraint theory or solver entrypoint.": (
        "The issue-168 baseline has no governed whole-scenario constraint theory or solver entrypoint."
    ),
}

_SNAPSHOT_KEYS = {
    "execution_id",
    "protocol_revision",
    "corpus_revision",
    "captured_at",
    "execution_status",
    _HISTORICAL_REVISION_FIELD,
    "configuration_id",
    "commands",
    "observations",
    "participant_observations",
    "deviations",
}
_COMMAND_KEYS = {"command_id", "argv", "network"}
_OBSERVATION_KEYS = {
    "case_id",
    "execution_id",
    "configuration_id",
    "replayable",
    "actual_outcome",
    "diagnostic_kind",
    "result_digest",
    "evidence_refs",
    "limitations",
}
_OBSERVATION_V2_KEYS = _OBSERVATION_KEYS | {
    "evidence_profile",
    "analysis_profile",
    "configuration_digest",
    "evidence_digest",
    "evidence_artifact_path",
    "evidence_artifact_sha256",
    "source_digest",
}
_PARTICIPANT_OBSERVATION_KEYS = {
    "obligation_id",
    "execution_id",
    "positive_outcome",
    "negative_outcome",
    "evidence_refs",
    "limitations",
}
_ANALYSIS_KEYS = {
    "analysis_id",
    "protocol_revision",
    "corpus_revision",
    "execution_id",
    "generated_at",
    "claim_results",
    "evidence_status",
    "claim",
    "plain_language_outcome",
    "limitations",
}
_SNAPSHOT_V2_KEYS = (_SNAPSHOT_KEYS - {_HISTORICAL_REVISION_FIELD}) | {
    "baseline",
    "raes_revision",
    "versions",
}
_VERSION_KEYS = {"python", "raes", "z3_solver", "z3_engine"}
_BASELINE_KEYS = {
    "release_path",
    "release_sha256",
    "release_revision",
    "execution_id",
}
_DEVIATION_KEYS = {
    "case_id",
    "changed_fields",
    "baseline",
    "retest",
    "disposition",
    "category",
    "rationale",
}
_CLAIM_RESULT_KEYS = {
    "claim_class_id",
    "evidence_status",
    "case_count",
    "matching_case_count",
    "replayable_case_count",
    "unsupported_case_count",
    "participant_obligation_count",
    "limitations",
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
_SATISFIABILITY_ANALYSIS_KEYS = {
    "profile",
    "revision",
    "execution_id",
    "snapshot_revision",
    "issue_number",
    "requirement_uid",
    "analysis_profile",
    "claim_class_id",
    "evidence_status",
    "scope",
    "cases",
    "limitations",
}
_SATISFIABILITY_SNAPSHOT_KEYS = {
    "profile",
    "revision",
    "execution_id",
    "captured_at",
    "analysis_profile",
    "solver_configuration_digest",
    "commands",
    "observations",
    "deviations",
}
_SATISFIABILITY_OBSERVATION_KEYS = {
    "case_id",
    "actual_outcome",
    "source_byte_digest",
    "normalized_model_digest",
    "evidence_profile",
    "replayable",
    "limitation",
}
_SATISFIABILITY_CASE_KEYS = {
    "case_id",
    "control",
    "fixture_path",
    "expected_outcome",
    "expected_normalized_model_digest",
    "limitation",
}
_SATISFIABILITY_CONTROL_OUTCOMES = {
    "positive": "satisfiable",
    "negative": "unsatisfiable",
    "unsupported": "unsupported",
}


def _failure(rule_id: str, message: str, path: str | None = None) -> PolicyFailure:
    return PolicyFailure(rule_id, message, path)


def _is_sequence(value: object) -> TypeGuard[Sequence[object]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _closed_object(
    value: object,
    expected_keys: set[str],
    *,
    rule_id: str,
    label: str,
    failures: list[PolicyFailure],
    path: str,
) -> bool:
    if not isinstance(value, Mapping):
        failures.append(_failure(rule_id, f"{label} must be an object", path))
        return False
    keys = set(value)
    if keys != expected_keys:
        failures.append(
            _failure(
                rule_id,
                f"{label} must use the closed key set; missing={sorted(expected_keys - keys)!r}, "
                f"unknown={sorted(keys - expected_keys)!r}",
                path,
            )
        )
        return False
    return True


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: object, *, nonempty: bool = True) -> bool:
    return _is_sequence(value) and (not nonempty or bool(value)) and all(_nonempty_string(item) for item in value)


def _stable_ids(items: object, key: str) -> tuple[set[str], bool]:
    if not _is_sequence(items):
        return set(), False
    values: list[str] = []
    for item in items:
        if not isinstance(item, Mapping) or not _nonempty_string(item.get(key)):
            return set(), False
        value = str(item[key])
        if not _ID_RE.fullmatch(value):
            return set(), False
        values.append(value)
    return set(values), len(values) == len(set(values))


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _diagnostic_payload(exc: Exception, repo_root: Path) -> object:
    errors = getattr(exc, "errors", None)
    payload: object = errors if errors is not None else str(exc)
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return rendered.replace(str(repo_root.resolve()), "<repo>")


def replay_case(repo_root: Path, case: Mapping[str, object]) -> dict[str, str | None]:
    """Replay one supported case through its declared production boundary."""
    fixture_value = case.get("fixture_path")
    fixture = safe_repo_path(repo_root, str(fixture_value)) if _nonempty_string(fixture_value) else None
    if fixture is None or not fixture.is_file():
        raise ValueError(f"missing or unsafe replay fixture {fixture_value!r}")

    replay_mode = case.get("replay_mode")
    if replay_mode == "parse":
        return _replay_parse_case(repo_root, case, fixture)
    if replay_mode == "compile-stability":
        first = _compiled_case_digest(repo_root, case, fixture)
        second = _compiled_case_digest(repo_root, case, fixture)
        return {
            "actual_outcome": "stable" if first == second else "drifted",
            "diagnostic_kind": None,
            "result_digest": _digest([first, second]),
        }
    if replay_mode == "compile-distinguish":
        return _replay_compile_distinguish(repo_root, case, fixture)
    raise ValueError(f"case {case.get('case_id')!r} is not replayable")


def _migration_policy_for_case(repo_root: Path, case: Mapping[str, object], path: Path) -> object:
    from raes import SDLMigrationPolicy

    relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    expected_digest = _HISTORICAL_VM_REPLAY_INPUTS.get((str(case.get("case_id")), relative))
    if expected_digest is not None and _sha256_file(path) == expected_digest:
        return SDLMigrationPolicy.ACCEPT
    return SDLMigrationPolicy.REJECT


def _replay_parse_case(
    repo_root: Path,
    case: Mapping[str, object],
    fixture: Path,
) -> dict[str, str | None]:
    from raes import SDLError, parse_sdl_file

    try:
        scenario = parse_sdl_file(
            fixture,
            migration_policy=_migration_policy_for_case(repo_root, case, fixture),
        )
    except SDLError as exc:
        return {
            "actual_outcome": "rejected",
            "diagnostic_kind": type(exc).__name__,
            "result_digest": _digest(_diagnostic_payload(exc, repo_root)),
        }
    return {
        "actual_outcome": "accepted",
        "diagnostic_kind": None,
        "result_digest": _digest(scenario.model_dump(mode="json")),
    }


def _compiled_case_digest(repo_root: Path, case: Mapping[str, object], path: Path) -> str:
    from raes import instantiate_scenario, parse_sdl_file
    from raes_processor.compiler import compile_runtime_model

    scenario = parse_sdl_file(
        path,
        migration_policy=_migration_policy_for_case(repo_root, case, path),
    )
    instantiated = instantiate_scenario(scenario, parameters={})
    return _digest(dataclasses.asdict(compile_runtime_model(instantiated)))


def _replay_compile_distinguish(
    repo_root: Path,
    case: Mapping[str, object],
    fixture: Path,
) -> dict[str, str | None]:
    comparison_value = case.get("comparison_fixture_path")
    comparison = safe_repo_path(repo_root, str(comparison_value)) if _nonempty_string(comparison_value) else None
    if comparison is None or not comparison.is_file():
        raise ValueError(f"missing or unsafe comparison fixture {comparison_value!r}")
    first = _compiled_case_digest(repo_root, case, fixture)
    second = _compiled_case_digest(repo_root, case, comparison)
    return {
        "actual_outcome": "distinguishable" if first != second else "indistinguishable",
        "diagnostic_kind": None,
        "result_digest": _digest([first, second]),
    }


def _replay_observation_matches(
    case_id: object,
    observation: Mapping[str, object],
    replayed: Mapping[str, object],
) -> bool:
    digest_pair = (observation.get("result_digest"), replayed.get("result_digest"))
    return (
        observation.get("actual_outcome") == replayed.get("actual_outcome")
        and observation.get("diagnostic_kind") == replayed.get("diagnostic_kind")
        and (
            observation.get("result_digest") == replayed.get("result_digest")
            or _RENAMED_FORMAL_REPLAY_DIGESTS.get(str(case_id)) == digest_pair
        )
    )


def _validate_test_ref(repo_root: Path, value: object) -> bool:
    if not _nonempty_string(value):
        return False
    path_value, separator, node_id = str(value).partition("::")
    if not separator or not node_id or "[" in node_id or "/" in node_id:
        return False
    path = safe_repo_path(repo_root, path_value)
    if path is None or not path.is_file() or path.suffix != ".py":
        return False
    function_name = node_id.rsplit("::", 1)[-1]
    return (
        re.search(
            rf"^def {re.escape(function_name)}\s*\(",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        is not None
    )


def _participant_test_refs(protocol: Mapping[str, object]) -> list[str]:
    refs: list[str] = []
    for obligation in protocol.get("participant_obligations", []):
        if not isinstance(obligation, Mapping):
            continue
        for key in ("positive_test_ref", "negative_test_ref"):
            value = obligation.get(key)
            if _nonempty_string(value):
                refs.append(str(value))
    return refs


def _replay_participant_tests(repo_root: Path, test_refs: list[str]) -> tuple[bool, str]:
    """Run the declared participant fixtures without trusting snapshot labels."""
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *test_refs],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"participant fixture replay could not complete: {exc}"
    if completed.returncode != 0:
        return (
            False,
            f"participant fixture replay exited with status {completed.returncode}",
        )
    return True, ""


def recompute_claim_results(
    protocol: Mapping[str, object],
    corpus: Mapping[str, object],
    snapshot: Mapping[str, object],
) -> list[dict[str, object]]:
    claim_classes = protocol.get("claim_classes", [])
    cases = corpus.get("cases", [])
    observations = snapshot.get("observations", [])
    participant_observations = snapshot.get("participant_observations", [])
    if not all(_is_sequence(value) for value in (claim_classes, cases, observations, participant_observations)):
        return []

    observations_by_case = {item.get("case_id"): item for item in observations if isinstance(item, Mapping)}
    participant_count = len(participant_observations)
    results: list[dict[str, object]] = []
    derive_from_supported_controls = protocol.get("revision") == "2.0.0"
    status_rank = {"untested": 0, "partial": 1, "demonstrated": 2}
    for declaration in claim_classes:
        if not isinstance(declaration, Mapping):
            continue
        claim_class_id = declaration.get("claim_class_id")
        class_cases = [
            item for item in cases if isinstance(item, Mapping) and item.get("claim_class_id") == claim_class_id
        ]
        matching = sum(
            1
            for case in class_cases
            if isinstance(observations_by_case.get(case.get("case_id")), Mapping)
            and observations_by_case[case.get("case_id")].get("actual_outcome") == case.get("expected_outcome")
        )
        expected_status = declaration.get("expected_evidence_status")
        supported_cases = [item for item in class_cases if item.get("replay_mode") != "unsupported"]
        supported_matching = sum(
            1
            for case in supported_cases
            if isinstance(observations_by_case.get(case.get("case_id")), Mapping)
            and observations_by_case[case.get("case_id")].get("actual_outcome") == case.get("expected_outcome")
        )
        if not derive_from_supported_controls:
            status = expected_status if matching == len(class_cases) and class_cases else "refuted"
        elif matching != len(class_cases) or supported_matching != len(supported_cases):
            status = "refuted"
        elif not supported_cases:
            status = "untested"
        else:
            observed_status = "demonstrated"
            status = min(
                (observed_status, str(expected_status)),
                key=lambda value: status_rank.get(value, -1),
            )
        results.append(
            {
                "claim_class_id": claim_class_id,
                "evidence_status": status,
                "case_count": len(class_cases),
                "matching_case_count": matching,
                "replayable_case_count": len(supported_cases),
                "unsupported_case_count": sum(1 for item in class_cases if item.get("replay_mode") == "unsupported"),
                "participant_obligation_count": participant_count if claim_class_id == "semantic-consistency" else 0,
            }
        )
    return results


def _validate_protocol(repo_root: Path, protocol: _JsonObject, failures: list[PolicyFailure], path: str) -> None:
    if not _closed_object(
        protocol,
        _PROTOCOL_KEYS,
        rule_id="formal-validation-protocol-shape",
        label="protocol",
        failures=failures,
        path=path,
    ):
        return
    expected_issue = {"1.0.0": 168, "2.0.0": 828}.get(protocol.get("revision"))
    if (
        expected_issue is None
        or protocol.get("issue_number") != expected_issue
        or protocol.get("requirement_uid") != "ASR-530"
    ):
        failures.append(
            _failure(
                "formal-validation-protocol-scope",
                "protocol must bind a supported revision to its issue and ASR-530",
                path,
            )
        )
    if set(protocol.get("evidence_status_values", [])) != EVIDENCE_STATUSES:
        failures.append(
            _failure(
                "formal-validation-evidence-status",
                "protocol must use the ADR-021 evidence statuses",
                path,
            )
        )
    _closed_object(
        protocol.get("analysis_rules"),
        _ANALYSIS_RULE_KEYS,
        rule_id="formal-validation-analysis-rules",
        label="analysis_rules",
        failures=failures,
        path=path,
    )

    claim_ids, unique_claim_ids = _stable_ids(protocol.get("claim_classes"), "claim_class_id")
    if claim_ids != REQUIRED_CLAIM_CLASS_IDS or not unique_claim_ids:
        failures.append(
            _failure(
                "formal-validation-claim-coverage",
                "protocol must contain each required claim class exactly once",
                path,
            )
        )
    for item in protocol.get("claim_classes", []):
        if not _closed_object(
            item,
            _CLAIM_CLASS_KEYS,
            rule_id="formal-validation-claim-shape",
            label="claim class",
            failures=failures,
            path=path,
        ):
            continue
        if item.get("expected_evidence_status") not in EVIDENCE_STATUSES:
            failures.append(
                _failure(
                    "formal-validation-evidence-status",
                    f"invalid expected status for {item.get('claim_class_id')!r}",
                    path,
                )
            )
        for key in ("allowed_evidence", "disallowed_evidence"):
            if not _string_list(item.get(key)):
                failures.append(
                    _failure(
                        "formal-validation-claim-evidence",
                        f"{item.get('claim_class_id')!r} needs non-empty {key}",
                        path,
                    )
                )

    obligation_ids, unique_obligation_ids = _stable_ids(protocol.get("participant_obligations"), "obligation_id")
    if obligation_ids != REQUIRED_PARTICIPANT_OBLIGATION_IDS or not unique_obligation_ids:
        failures.append(
            _failure(
                "formal-validation-participant-coverage",
                "protocol must contain every participant-semantics obligation exactly once",
                path,
            )
        )
    for item in protocol.get("participant_obligations", []):
        if not _closed_object(
            item,
            _PARTICIPANT_KEYS,
            rule_id="formal-validation-participant-shape",
            label="participant obligation",
            failures=failures,
            path=path,
        ):
            continue
        positive = item.get("positive_test_ref")
        negative = item.get("negative_test_ref")
        if (
            positive == negative
            or not _validate_test_ref(repo_root, positive)
            or not _validate_test_ref(repo_root, negative)
        ):
            failures.append(
                _failure(
                    "formal-validation-participant-fixtures",
                    f"{item.get('obligation_id')!r} needs distinct existing positive and negative test refs",
                    path,
                )
            )


def _validate_corpus(
    repo_root: Path,
    protocol: _JsonObject,
    corpus: _JsonObject,
    failures: list[PolicyFailure],
    path: str,
) -> dict[str, Mapping[str, object]]:
    if not _closed_object(
        corpus,
        _CORPUS_KEYS,
        rule_id="formal-validation-corpus-shape",
        label="corpus",
        failures=failures,
        path=path,
    ):
        return {}
    cases = corpus.get("cases")
    if not _is_sequence(cases) or not cases or len(cases) > _MAX_CASES:
        failures.append(
            _failure(
                "formal-validation-case-count",
                f"corpus cases must contain 1..{_MAX_CASES} entries",
                path,
            )
        )
        return {}
    case_ids, unique_case_ids = _stable_ids(cases, "case_id")
    if not unique_case_ids:
        failures.append(_failure("formal-validation-case-ids", "case ids must be unique stable ids", path))
    claim_ids = {item.get("claim_class_id") for item in protocol.get("claim_classes", []) if isinstance(item, Mapping)}
    cases_by_id: dict[str, Mapping[str, object]] = {}
    polarities: dict[object, set[object]] = {claim_id: set() for claim_id in claim_ids}
    for item in cases:
        if not _closed_object(
            item,
            _CASE_KEYS,
            rule_id="formal-validation-case-shape",
            label="case",
            failures=failures,
            path=path,
        ):
            continue
        case_id = item.get("case_id")
        if isinstance(case_id, str):
            cases_by_id[case_id] = item
        claim_id = item.get("claim_class_id")
        if claim_id not in claim_ids:
            failures.append(
                _failure(
                    "formal-validation-case-claim",
                    f"case {case_id!r} references unknown claim class",
                    path,
                )
            )
        else:
            polarities[claim_id].add(item.get("polarity"))
        if item.get("polarity") not in {"positive", "negative"}:
            failures.append(
                _failure(
                    "formal-validation-case-polarity",
                    f"case {case_id!r} has invalid polarity",
                    path,
                )
            )
        replay_mode = item.get("replay_mode")
        if replay_mode not in REPLAY_MODES | PRODUCTION_EVIDENCE_REPLAY_MODES:
            failures.append(
                _failure(
                    "formal-validation-replay-mode",
                    f"case {case_id!r} has invalid replay mode",
                    path,
                )
            )
        fixture_value = item.get("fixture_path")
        comparison_value = item.get("comparison_fixture_path")
        if replay_mode == "unsupported":
            if (
                fixture_value is not None
                or comparison_value is not None
                or item.get("expected_outcome") != "unsupported"
            ):
                failures.append(
                    _failure(
                        "formal-validation-unsupported-case",
                        f"unsupported case {case_id!r} must have no fixture and outcome unsupported",
                        path,
                    )
                )
        else:
            fixture = safe_repo_path(repo_root, str(fixture_value)) if _nonempty_string(fixture_value) else None
            if fixture is None or not fixture.is_file():
                failures.append(
                    _failure(
                        "formal-validation-case-path",
                        f"case {case_id!r} has a missing or unsafe fixture",
                        path,
                    )
                )
            if replay_mode == "compile-distinguish":
                comparison = (
                    safe_repo_path(repo_root, str(comparison_value)) if _nonempty_string(comparison_value) else None
                )
                if comparison is None or not comparison.is_file():
                    failures.append(
                        _failure(
                            "formal-validation-case-path",
                            f"case {case_id!r} has a missing or unsafe comparison fixture",
                            path,
                        )
                    )
            elif comparison_value is not None:
                failures.append(
                    _failure(
                        "formal-validation-case-path",
                        f"case {case_id!r} has an unexpected comparison fixture",
                        path,
                    )
                )
        if not _nonempty_string(item.get("limitation")):
            failures.append(
                _failure(
                    "formal-validation-case-limit",
                    f"case {case_id!r} must record a limitation",
                    path,
                )
            )
    for claim_id, values in polarities.items():
        if values != {"positive", "negative"}:
            failures.append(
                _failure(
                    "formal-validation-case-polarity",
                    f"claim class {claim_id!r} needs positive and negative cases",
                    path,
                )
            )
    if len(case_ids) != len(cases_by_id):
        return cases_by_id
    return cases_by_id


def _validate_snapshot(
    repo_root: Path,
    protocol: _JsonObject,
    corpus: _JsonObject,
    snapshot: _JsonObject,
    cases_by_id: dict[str, Mapping[str, object]],
    failures: list[PolicyFailure],
    path: str,
    *,
    replay_cases: bool = True,
) -> None:
    if not _closed_object(
        snapshot,
        _SNAPSHOT_KEYS,
        rule_id="formal-validation-snapshot-shape",
        label="snapshot",
        failures=failures,
        path=path,
    ):
        return
    _validate_snapshot_header(protocol, corpus, snapshot, failures, path)
    _validate_snapshot_commands(protocol, snapshot, failures, path)

    observations = snapshot.get("observations")
    if not _is_sequence(observations):
        failures.append(
            _failure(
                "formal-validation-observations",
                "snapshot observations must be a list",
                path,
            )
        )
        observations = []
    observation_ids: list[object] = []
    for item in observations:
        accepted, case_id = _validate_snapshot_observation(
            repo_root,
            snapshot,
            cases_by_id,
            item,
            failures,
            path,
            replay_cases=replay_cases,
        )
        if accepted:
            observation_ids.append(case_id)
    if set(observation_ids) != set(cases_by_id) or len(observation_ids) != len(set(observation_ids)):
        failures.append(
            _failure(
                "formal-validation-observation-coverage",
                "snapshot must contain exactly one observation per corpus case",
                path,
            )
        )

    participant_observations = snapshot.get("participant_observations")
    if not _is_sequence(participant_observations):
        failures.append(
            _failure(
                "formal-validation-participant-observations",
                "participant observations must be a list",
                path,
            )
        )
        participant_observations = []
    obligation_ids = {
        item.get("obligation_id") for item in protocol.get("participant_obligations", []) if isinstance(item, Mapping)
    }
    obligations_by_id = {
        item.get("obligation_id"): item
        for item in protocol.get("participant_obligations", [])
        if isinstance(item, Mapping)
    }
    observed_obligations: list[object] = []
    for item in participant_observations:
        accepted, obligation_id = _validate_snapshot_participant_observation(
            snapshot,
            obligation_ids,
            obligations_by_id,
            item,
            failures,
            path,
        )
        if accepted:
            observed_obligations.append(obligation_id)
    if set(observed_obligations) != obligation_ids or len(observed_obligations) != len(set(observed_obligations)):
        failures.append(
            _failure(
                "formal-validation-participant-observation-coverage",
                "snapshot must contain exactly one observation per participant obligation",
                path,
            )
        )


def _validate_snapshot_observation(
    repo_root: Path,
    snapshot: Mapping[str, object],
    cases_by_id: Mapping[str, Mapping[str, object]],
    item: object,
    failures: list[PolicyFailure],
    path: str,
    *,
    replay_cases: bool,
) -> tuple[bool, object]:
    if not _closed_object(
        item,
        _OBSERVATION_KEYS,
        rule_id="formal-validation-observation-shape",
        label="observation",
        failures=failures,
        path=path,
    ):
        return False, None
    case_id = item.get("case_id")
    case = cases_by_id.get(str(case_id))
    if case is None:
        failures.append(
            _failure(
                "formal-validation-observation-case",
                f"observation references unknown case {case_id!r}",
                path,
            )
        )
        return True, case_id
    if item.get("execution_id") != snapshot.get("execution_id") or item.get("configuration_id") != snapshot.get(
        "configuration_id"
    ):
        failures.append(
            _failure(
                "formal-validation-observation-join",
                f"observation {case_id!r} must bind the snapshot execution and configuration",
                path,
            )
        )
    expected_replayable = case.get("replay_mode") != "unsupported"
    if item.get("replayable") is not expected_replayable:
        failures.append(
            _failure(
                "formal-validation-observation-replayable",
                f"observation {case_id!r} misstates replayability",
                path,
            )
        )
    if not _string_list(item.get("evidence_refs")) or not _string_list(item.get("limitations")):
        failures.append(
            _failure(
                "formal-validation-observation-evidence",
                f"observation {case_id!r} needs evidence refs and limitations",
                path,
            )
        )
    _validate_snapshot_replay(repo_root, case, item, failures, path, replay_cases=replay_cases)
    return True, case_id


def _validate_snapshot_replay(
    repo_root: Path,
    case: Mapping[str, object],
    item: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
    *,
    replay_cases: bool,
) -> None:
    case_id = item.get("case_id")
    replayable = case.get("replay_mode") != "unsupported"
    if replayable and replay_cases:
        try:
            replayed = replay_case(repo_root, case)
        except (ValueError, OSError) as exc:
            failures.append(
                _failure(
                    "formal-validation-replay-error",
                    f"could not replay {case_id!r}: {exc}",
                    path,
                )
            )
        else:
            if not _replay_observation_matches(case_id, item, replayed):
                failures.append(
                    _failure(
                        "formal-validation-replay-drift",
                        f"observation {case_id!r} drifted from replay",
                        path,
                    )
                )
    elif not replayable and (
        item.get("actual_outcome") != "unsupported"
        or item.get("diagnostic_kind") is not None
        or item.get("result_digest") is not None
    ):
        failures.append(
            _failure(
                "formal-validation-unsupported-observation",
                f"unsupported observation {case_id!r} must not synthesize diagnostics or results",
                path,
            )
        )


def _validate_snapshot_participant_observation(
    snapshot: Mapping[str, object],
    obligation_ids: set[object],
    obligations_by_id: Mapping[object, object],
    item: object,
    failures: list[PolicyFailure],
    path: str,
) -> tuple[bool, object]:
    if not _closed_object(
        item,
        _PARTICIPANT_OBSERVATION_KEYS,
        rule_id="formal-validation-participant-observation-shape",
        label="participant observation",
        failures=failures,
        path=path,
    ):
        return False, None
    obligation_id = item.get("obligation_id")
    if obligation_id not in obligation_ids:
        failures.append(
            _failure(
                "formal-validation-participant-observation-join",
                f"unknown participant obligation {obligation_id!r}",
                path,
            )
        )
    if item.get("execution_id") != snapshot.get("execution_id"):
        failures.append(
            _failure(
                "formal-validation-participant-observation-join",
                "participant observation must bind the snapshot execution",
                path,
            )
        )
    obligation = obligations_by_id.get(obligation_id)
    expected_refs = (
        [obligation.get("positive_test_ref"), obligation.get("negative_test_ref")]
        if isinstance(obligation, Mapping)
        else []
    )
    if item.get("evidence_refs") != expected_refs:
        failures.append(
            _failure(
                "formal-validation-participant-observation-evidence",
                f"participant obligation {obligation_id!r} must bind its declared positive and negative refs",
                path,
            )
        )
    if item.get("positive_outcome") != "passed" or item.get("negative_outcome") != "passed":
        failures.append(
            _failure(
                "formal-validation-participant-result",
                f"participant obligation {obligation_id!r} did not preserve passing fixtures",
                path,
            )
        )
    if not _valid_participant_evidence(item):
        failures.append(
            _failure(
                "formal-validation-participant-observation-evidence",
                f"participant obligation {obligation_id!r} needs two evidence refs and limitations",
                path,
            )
        )
    return True, obligation_id


def _valid_participant_evidence(item: Mapping[str, object]) -> bool:
    evidence_refs = item.get("evidence_refs")
    return bool(
        _string_list(evidence_refs, nonempty=True) and len(evidence_refs) == 2 and _string_list(item.get("limitations"))
    )


def _validate_snapshot_header(
    protocol: Mapping[str, object],
    corpus: Mapping[str, object],
    snapshot: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    if snapshot.get("protocol_revision") != protocol.get("revision") or snapshot.get("corpus_revision") != corpus.get(
        "revision"
    ):
        failures.append(
            _failure(
                "formal-validation-snapshot-revision",
                "snapshot must bind the selected protocol and corpus revisions",
                path,
            )
        )
    if snapshot.get("execution_status") != "complete":
        failures.append(
            _failure(
                "formal-validation-execution-status",
                "snapshot must preserve a complete execution",
                path,
            )
        )
    historical_revision = snapshot.get(_HISTORICAL_REVISION_FIELD)
    if not isinstance(historical_revision, str) or not _COMMIT_RE.fullmatch(historical_revision):
        failures.append(
            _failure(
                "formal-validation-revision-pin",
                "historical revision must be a full immutable Git commit",
                path,
            )
        )


def _validate_snapshot_commands(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    commands = snapshot.get("commands")
    if not _is_sequence(commands) or not commands:
        failures.append(
            _failure(
                "formal-validation-commands",
                "snapshot must record fixed-argv reproduction commands",
                path,
            )
        )
        return
    command_ids, unique_command_ids = _stable_ids(commands, "command_id")
    if not command_ids or not unique_command_ids:
        failures.append(_failure("formal-validation-commands", "command ids must be unique stable ids", path))
    for item in commands:
        _validate_snapshot_command(item, failures, path)
    _validate_snapshot_participant_command(protocol, commands, failures, path)


def _validate_snapshot_command(item: object, failures: list[PolicyFailure], path: str) -> None:
    if not _closed_object(
        item,
        _COMMAND_KEYS,
        rule_id="formal-validation-command-shape",
        label="command",
        failures=failures,
        path=path,
    ):
        return
    if not _string_list(item.get("argv")) or item.get("network") != "disabled":
        failures.append(
            _failure(
                "formal-validation-commands",
                f"command {item.get('command_id')!r} must use non-empty argv and disabled network",
                path,
            )
        )


def _validate_snapshot_participant_command(
    protocol: Mapping[str, object],
    commands: Sequence[object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    expected_argv = [
        "implementations/python/.venv/bin/pytest",
        "-q",
        *_participant_test_refs(protocol),
    ]
    participant_commands = [
        item for item in commands if isinstance(item, Mapping) and item.get("command_id") == "participant-fixtures"
    ]
    if len(participant_commands) != 1 or participant_commands[0].get("argv") != expected_argv:
        failures.append(
            _failure(
                "formal-validation-participant-command",
                "snapshot must bind the participant replay command to every declared positive and negative test ref",
                path,
            )
        )


def _validate_analysis(
    repo_root: Path,
    protocol: _JsonObject,
    corpus: _JsonObject,
    snapshot: _JsonObject,
    analysis: _JsonObject,
    failures: list[PolicyFailure],
    path: str,
) -> None:
    if not _closed_object(
        analysis,
        _ANALYSIS_KEYS,
        rule_id="formal-validation-analysis-shape",
        label="analysis",
        failures=failures,
        path=path,
    ):
        return
    if (
        analysis.get("protocol_revision") != protocol.get("revision")
        or analysis.get("corpus_revision") != corpus.get("revision")
        or analysis.get("execution_id") != snapshot.get("execution_id")
    ):
        failures.append(
            _failure(
                "formal-validation-analysis-join",
                "analysis must bind the selected protocol, corpus, and execution",
                path,
            )
        )
    recomputed = recompute_claim_results(protocol, corpus, snapshot)
    expected_by_id = {item["claim_class_id"]: item for item in recomputed}
    results = analysis.get("claim_results")
    if not _is_sequence(results):
        failures.append(
            _failure(
                "formal-validation-analysis-results",
                "claim_results must be a list",
                path,
            )
        )
        results = []
    result_ids: list[object] = []
    for item in results:
        if not _closed_object(
            item,
            _CLAIM_RESULT_KEYS,
            rule_id="formal-validation-claim-result-shape",
            label="claim result",
            failures=failures,
            path=path,
        ):
            continue
        claim_class_id = item.get("claim_class_id")
        result_ids.append(claim_class_id)
        expected = expected_by_id.get(claim_class_id)
        if expected is None:
            failures.append(
                _failure(
                    "formal-validation-analysis-result-join",
                    f"unknown claim result {claim_class_id!r}",
                    path,
                )
            )
            continue
        for key in (
            "evidence_status",
            "case_count",
            "matching_case_count",
            "replayable_case_count",
            "unsupported_case_count",
            "participant_obligation_count",
        ):
            if item.get(key) != expected[key]:
                failures.append(
                    _failure(
                        "formal-validation-analysis-drift",
                        f"claim result {claim_class_id!r} field {key} does not match frozen observations",
                        path,
                    )
                )
                break
        if expected["evidence_status"] in {"untested", "refuted"} and item.get("evidence_status") in {
            "partial",
            "demonstrated",
        }:
            failures.append(
                _failure(
                    "formal-validation-unsupported-overclaim",
                    f"unproven or refuted class {claim_class_id!r} cannot be promoted",
                    path,
                )
            )
        if not _string_list(item.get("limitations")):
            failures.append(
                _failure(
                    "formal-validation-claim-limitations",
                    f"claim result {claim_class_id!r} needs limitations",
                    path,
                )
            )
    if set(result_ids) != set(expected_by_id) or len(result_ids) != len(set(result_ids)):
        failures.append(
            _failure(
                "formal-validation-analysis-result-coverage",
                "analysis must contain exactly one result per claim class",
                path,
            )
        )

    statuses = {item["evidence_status"] for item in recomputed}
    if "refuted" in statuses:
        overall = "refuted"
    elif statuses & {"partial", "demonstrated"}:
        overall = "partial"
    else:
        overall = "untested"
    if analysis.get("evidence_status") != overall:
        failures.append(
            _failure(
                "formal-validation-analysis-drift",
                "overall evidence status does not match claim results",
                path,
            )
        )
    if not _closed_object(
        analysis.get("claim"),
        _CLAIM_KEYS,
        rule_id="formal-validation-claim-record",
        label="claim",
        failures=failures,
        path=path,
    ):
        return
    claim = analysis["claim"]
    for key in (
        "threats_to_validity",
        "allowed_evidence",
        "disallowed_evidence",
        "evidence_artifacts",
    ):
        if not _string_list(claim.get(key)):
            failures.append(
                _failure(
                    "formal-validation-claim-record",
                    f"claim needs non-empty {key}",
                    path,
                )
            )
    for artifact in claim.get("evidence_artifacts", []):
        resolved = safe_repo_path(repo_root, artifact) if isinstance(artifact, str) else None
        if resolved is None or not resolved.is_file():
            failures.append(
                _failure(
                    "formal-validation-claim-artifact",
                    f"claim references missing or unsafe artifact {artifact!r}",
                    path,
                )
            )
    if not _string_list(analysis.get("limitations")) or not _nonempty_string(analysis.get("plain_language_outcome")):
        failures.append(
            _failure(
                "formal-validation-analysis-disclosure",
                "analysis needs a plain-language outcome and limitations",
                path,
            )
        )


def load_release_bundles(repo_root: Path = REPO_ROOT) -> list[EvidenceRelease]:
    """Load every atomically indexed evidence release in semantic order."""

    records = load_index_records(
        repo_root,
        index_path=MANIFEST_PATH,
        schema_version=MANIFEST_SCHEMA_VERSION,
        directory_key="bundles_directory",
        max_bytes=_MAX_FILE_BYTES,
    )
    releases: list[EvidenceRelease] = []
    for manifest_path, manifest in records:
        revision_key(manifest.get("revision"))
        loaded: list[dict[str, object]] = []
        for label in ("protocol", "corpus", "snapshot", "analysis"):
            path_value = manifest.get(f"{label}_path")
            path = safe_repo_path(repo_root, path_value) if isinstance(path_value, str) else None
            if path is None or not path.is_file():
                raise ValueError(f"{manifest_path!r} contains unsafe or missing {label}_path")
            loaded.append(load_bounded_json_object(repo_root, path_value, max_bytes=_MAX_FILE_BYTES))
        releases.append(
            EvidenceRelease(
                manifest_path=manifest_path,
                manifest=manifest,
                protocol=loaded[0],
                corpus=loaded[1],
                snapshot=loaded[2],
                analysis=loaded[3],
            )
        )
    return sorted(
        releases,
        key=lambda item: (
            revision_key(item.manifest.get("revision")),
            item.manifest_path,
        ),
    )


def load_retest_bundle(
    repo_root: Path = REPO_ROOT,
) -> tuple[
    EvidenceRelease,
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    """Load the latest coherent issue-828 retest release."""

    releases = [item for item in load_release_bundles(repo_root) if item.protocol.get("revision") == "2.0.0"]
    if not releases:
        raise ValueError("the formal semantic-validation index selects no v2 retest release")
    release = max(releases, key=lambda item: revision_key(item.manifest.get("revision")))
    return release, release.protocol, release.corpus, release.snapshot, release.analysis


def validate_release_bundle(repo_root: Path, release: EvidenceRelease) -> list[PolicyFailure]:
    """Validate one atomic release record, all digest pins, and its evidence."""

    failures: list[PolicyFailure] = []
    manifest = release.manifest
    path = release.manifest_path
    if not _closed_object(
        manifest,
        _RELEASE_MANIFEST_KEYS,
        rule_id="formal-validation-release-shape",
        label="release manifest",
        failures=failures,
        path=path,
    ):
        return failures
    try:
        revision_key(manifest.get("revision"))
    except ValueError:
        failures.append(
            _failure(
                "formal-validation-release-revision",
                "release revision must be semantic",
                path,
            )
        )

    for label in ("protocol", "corpus", "snapshot", "analysis"):
        path_value = manifest.get(f"{label}_path")
        digest_value = manifest.get(f"{label}_sha256")
        resolved = safe_repo_path(repo_root, path_value) if isinstance(path_value, str) else None
        if (
            resolved is None
            or not resolved.is_file()
            or not isinstance(digest_value, str)
            or not _SHA256_RE.fullmatch(digest_value)
            or _sha256_file(resolved) != digest_value
        ):
            failures.append(
                _failure(
                    "formal-validation-release-digest",
                    f"release {label} path or SHA-256 pin is stale",
                    path,
                )
            )

    artifacts = manifest.get("artifacts")
    if not _is_sequence(artifacts):
        failures.append(
            _failure(
                "formal-validation-release-artifacts",
                "release artifacts must be a bounded list",
                path,
            )
        )
        artifacts = []
    _, unique_artifact_ids = _stable_ids(artifacts, "artifact_id")
    artifact_paths: list[str] = []
    for artifact in artifacts:
        if not _closed_object(
            artifact,
            _RELEASE_ARTIFACT_PIN_KEYS,
            rule_id="formal-validation-release-artifact-shape",
            label="release artifact",
            failures=failures,
            path=path,
        ):
            continue
        artifact_path = artifact.get("path")
        artifact_digest = artifact.get("sha256")
        resolved = safe_repo_path(repo_root, artifact_path) if isinstance(artifact_path, str) else None
        if isinstance(artifact_path, str):
            artifact_paths.append(artifact_path)
        if (
            resolved is None
            or not resolved.is_file()
            or not isinstance(artifact_digest, str)
            or not _SHA256_RE.fullmatch(artifact_digest)
            or _sha256_file(resolved) != artifact_digest
        ):
            failures.append(
                _failure(
                    "formal-validation-release-digest",
                    f"release artifact {artifact.get('artifact_id')!r} path or SHA-256 pin is stale",
                    path,
                )
            )
    if not unique_artifact_ids or len(artifact_paths) != len(set(artifact_paths)):
        failures.append(
            _failure(
                "formal-validation-release-artifacts",
                "release artifact ids and paths must be unique",
                path,
            )
        )

    if release.protocol.get("revision") == "2.0.0":
        failures.extend(
            validate_retest_bundle(
                repo_root,
                release,
                release.protocol,
                release.corpus,
                release.snapshot,
                release.analysis,
            )
        )
    else:
        legacy_manifest = {
            "bundle_id": manifest.get("bundle_id"),
            "revision": manifest.get("revision"),
            "protocol_path": manifest.get("protocol_path"),
            "corpus_path": manifest.get("corpus_path"),
            "snapshot_path": manifest.get("snapshot_path"),
            "analysis_path": manifest.get("analysis_path"),
            "satisfiability_snapshot_path": None,
            "satisfiability_analysis_path": None,
        }
        failures.extend(
            validate_bundle(
                repo_root,
                legacy_manifest,
                release.protocol,
                release.corpus,
                release.snapshot,
                release.analysis,
                replay_cases=False,
            )
        )
        artifact_by_kind = {item.get("kind"): item for item in artifacts if isinstance(item, Mapping)}
        sat_snapshot_pin = artifact_by_kind.get("satisfiability-snapshot")
        sat_analysis_pin = artifact_by_kind.get("satisfiability-analysis")
        if sat_snapshot_pin is not None or sat_analysis_pin is not None:
            if sat_snapshot_pin is None or sat_analysis_pin is None:
                failures.append(
                    _failure(
                        "formal-validation-release-artifacts",
                        "historical satisfiability evidence must be selected atomically",
                        path,
                    )
                )
            else:
                legacy_manifest["revision"] = "2.0.0"
                legacy_manifest["satisfiability_snapshot_path"] = sat_snapshot_pin.get("path")
                legacy_manifest["satisfiability_analysis_path"] = sat_analysis_pin.get("path")
                snapshot = load_bounded_json_object(
                    repo_root,
                    str(sat_snapshot_pin.get("path")),
                    max_bytes=_MAX_FILE_BYTES,
                )
                analysis = load_bounded_json_object(
                    repo_root,
                    str(sat_analysis_pin.get("path")),
                    max_bytes=_MAX_FILE_BYTES,
                )
                failures.extend(validate_satisfiability_analysis(repo_root, legacy_manifest, snapshot, analysis))
    return failures


def validate_retest_bundle(
    repo_root: Path,
    release: EvidenceRelease,
    protocol: dict[str, object],
    corpus: dict[str, object],
    snapshot: dict[str, object],
    analysis: dict[str, object],
) -> list[PolicyFailure]:
    """Validate the integrated issue-828 evidence release."""

    failures: list[PolicyFailure] = []
    protocol_path = str(release.manifest.get("protocol_path"))
    corpus_path = str(release.manifest.get("corpus_path"))
    snapshot_path = str(release.manifest.get("snapshot_path"))
    analysis_path = str(release.manifest.get("analysis_path"))
    if release.manifest.get("revision") != "3.0.0":
        failures.append(
            _failure(
                "formal-validation-retest-release",
                "the integrated issue-828 retest must be release 3.0.0",
                release.manifest_path,
            )
        )
    if protocol.get("revision") != "2.0.0" or corpus.get("revision") != "2.0.0":
        failures.append(
            _failure(
                "formal-validation-retest-revision",
                "the integrated retest must bind protocol and corpus revision 2.0.0",
                release.manifest_path,
            )
        )

    _validate_protocol(repo_root, protocol, failures, protocol_path)
    cases_by_id = _validate_corpus(repo_root, protocol, corpus, failures, corpus_path)
    try:
        historical_corpus = load_bounded_json_object(
            repo_root,
            "docs/research/formal-semantic-validation/corpus/manifest-v1.json",
            max_bytes=_MAX_FILE_BYTES,
        )
    except (OSError, ValueError) as exc:
        failures.append(
            _failure(
                "formal-validation-historical-retention",
                f"could not load the immutable v1 corpus ({type(exc).__name__})",
                corpus_path,
            )
        )
        historical_corpus = {}
    historical_cases = {
        item.get("case_id"): item for item in historical_corpus.get("cases", []) if isinstance(item, Mapping)
    }
    retained_cases_match = all(
        cases_by_id.get(str(case_id))
        == {
            **case,
            "limitation": _RETAINED_CASE_TEXT_REPLACEMENTS.get(
                str(case.get("limitation")),
                case.get("limitation"),
            ),
        }
        for case_id, case in historical_cases.items()
    )
    if not historical_cases or not retained_cases_match:
        failures.append(
            _failure(
                "formal-validation-historical-retention",
                "the v2 corpus must retain every v1 case semantically unchanged, "
                "allowing only the governed identity wording",
                corpus_path,
            )
        )

    _validate_retest_snapshot(
        repo_root,
        release,
        protocol,
        corpus,
        snapshot,
        cases_by_id,
        failures,
        snapshot_path,
    )
    _validate_baseline_drift(
        repo_root,
        snapshot,
        historical_cases,
        failures,
        snapshot_path,
    )
    _validate_analysis(repo_root, protocol, corpus, snapshot, analysis, failures, analysis_path)
    return failures


def _validate_baseline_drift(
    repo_root: Path,
    snapshot: Mapping[str, object],
    historical_cases: Mapping[object, Mapping[str, object]],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    """Join retained retest observations to one immutable baseline release."""

    baseline = snapshot.get("baseline")
    if not _closed_object(
        baseline,
        _BASELINE_KEYS,
        rule_id="formal-validation-baseline-selection",
        label="retest baseline",
        failures=failures,
        path=path,
    ):
        return
    baseline_path = baseline.get("release_path")
    baseline_digest = baseline.get("release_sha256")
    if (
        not isinstance(baseline_path, str)
        or not isinstance(baseline_digest, str)
        or not _SHA256_RE.fullmatch(baseline_digest)
        or not _nonempty_string(baseline.get("release_revision"))
        or not _nonempty_string(baseline.get("execution_id"))
    ):
        failures.append(
            _failure(
                "formal-validation-baseline-selection",
                "retest baseline must pin a release path, digest, revision, and execution",
                path,
            )
        )
        return

    try:
        indexed_records = dict(
            load_index_records(
                repo_root,
                index_path=MANIFEST_PATH,
                schema_version=MANIFEST_SCHEMA_VERSION,
                directory_key="bundles_directory",
                max_bytes=_MAX_FILE_BYTES,
            )
        )
    except (OSError, ValueError) as exc:
        failures.append(
            _failure(
                "formal-validation-baseline-selection",
                f"could not load the indexed baseline release ({type(exc).__name__})",
                path,
            )
        )
        return
    baseline_manifest = indexed_records.get(baseline_path)
    resolved_baseline_path = safe_repo_path(repo_root, baseline_path)
    if (
        not isinstance(baseline_manifest, Mapping)
        or resolved_baseline_path is None
        or not resolved_baseline_path.is_file()
        or _sha256_file(resolved_baseline_path) != baseline_digest
        or baseline_manifest.get("revision") != baseline.get("release_revision")
        or baseline_manifest.get("protocol_path") != "docs/research/formal-semantic-validation/protocol-v1.json"
        or baseline_manifest.get("corpus_path") != "docs/research/formal-semantic-validation/corpus/manifest-v1.json"
    ):
        failures.append(
            _failure(
                "formal-validation-baseline-selection",
                "retest baseline must select one indexed historical release with an exact digest and revision",
                path,
            )
        )
        return

    baseline_snapshot_path = baseline_manifest.get("snapshot_path")
    baseline_snapshot_digest = baseline_manifest.get("snapshot_sha256")
    resolved_snapshot_path = (
        safe_repo_path(repo_root, baseline_snapshot_path) if isinstance(baseline_snapshot_path, str) else None
    )
    if (
        resolved_snapshot_path is None
        or not resolved_snapshot_path.is_file()
        or not isinstance(baseline_snapshot_digest, str)
        or _sha256_file(resolved_snapshot_path) != baseline_snapshot_digest
    ):
        failures.append(
            _failure(
                "formal-validation-baseline-selection",
                "selected baseline release has a stale execution-snapshot pin",
                path,
            )
        )
        return
    try:
        baseline_snapshot = load_bounded_json_object(
            repo_root,
            str(baseline_snapshot_path),
            max_bytes=_MAX_FILE_BYTES,
        )
    except (OSError, ValueError) as exc:
        failures.append(
            _failure(
                "formal-validation-baseline-selection",
                f"could not load the selected baseline snapshot ({type(exc).__name__})",
                path,
            )
        )
        return
    if baseline_snapshot.get("execution_id") != baseline.get("execution_id"):
        failures.append(
            _failure(
                "formal-validation-baseline-selection",
                "selected baseline execution id does not match its pinned snapshot",
                path,
            )
        )

    baseline_observations = baseline_snapshot.get("observations")
    retest_observations = snapshot.get("observations")
    baseline_ids, baseline_unique = _stable_ids(baseline_observations, "case_id")
    retest_ids, retest_unique = _stable_ids(retest_observations, "case_id")
    retained_ids = {str(case_id) for case_id in historical_cases}
    if (
        not _is_sequence(baseline_observations)
        or not _is_sequence(retest_observations)
        or not baseline_unique
        or not retest_unique
        or not retained_ids.issubset(baseline_ids)
        or not retained_ids.issubset(retest_ids)
    ):
        failures.append(
            _failure(
                "formal-validation-baseline-drift",
                "every retained case must join uniquely to baseline and retest observations",
                path,
            )
        )
        return
    baseline_by_id = {str(item.get("case_id")): item for item in baseline_observations if isinstance(item, Mapping)}
    retest_by_id = {str(item.get("case_id")): item for item in retest_observations if isinstance(item, Mapping)}

    deviations = snapshot.get("deviations")
    deviation_ids, deviations_unique = _stable_ids(deviations, "case_id")
    if not _is_sequence(deviations) or not deviations_unique:
        failures.append(
            _failure(
                "formal-validation-baseline-drift",
                "baseline deviations must be a unique bounded list",
                path,
            )
        )
        deviations = []
    deviations_by_id = {str(item.get("case_id")): item for item in deviations if isinstance(item, Mapping)}

    expected_deviation_ids: set[str] = set()
    comparison_keys = ("actual_outcome", "diagnostic_kind", "result_digest")
    for case_id in sorted(retained_ids):
        baseline_observation = baseline_by_id[case_id]
        retest_observation = retest_by_id[case_id]
        changed_fields = [
            key for key in comparison_keys if baseline_observation.get(key) != retest_observation.get(key)
        ]
        if not changed_fields:
            continue
        expected_deviation_ids.add(case_id)
        deviation = deviations_by_id.get(case_id)
        if not _closed_object(
            deviation,
            _DEVIATION_KEYS,
            rule_id="formal-validation-baseline-drift",
            label=f"baseline deviation {case_id!r}",
            failures=failures,
            path=path,
        ):
            continue
        expected_baseline = {key: baseline_observation.get(key) for key in comparison_keys}
        expected_retest = {key: retest_observation.get(key) for key in comparison_keys}
        if (
            deviation.get("changed_fields") != changed_fields
            or deviation.get("baseline") != expected_baseline
            or deviation.get("retest") != expected_retest
            or deviation.get("disposition") != "accepted"
            or not _nonempty_string(deviation.get("category"))
            or not _nonempty_string(deviation.get("rationale"))
        ):
            failures.append(
                _failure(
                    "formal-validation-baseline-drift",
                    f"retained case {case_id!r} needs an exact accepted drift disposition",
                    path,
                )
            )
    if deviation_ids != expected_deviation_ids:
        failures.append(
            _failure(
                "formal-validation-baseline-drift",
                "deviations must cover exactly the retained cases whose governed observations changed",
                path,
            )
        )


def _validate_retest_snapshot(
    repo_root: Path,
    release: EvidenceRelease,
    protocol: dict[str, object],
    corpus: dict[str, object],
    snapshot: dict[str, object],
    cases_by_id: dict[str, Mapping[str, object]],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    if not _closed_object(
        snapshot,
        _SNAPSHOT_V2_KEYS,
        rule_id="formal-validation-snapshot-shape",
        label="retest snapshot",
        failures=failures,
        path=path,
    ):
        return
    _validate_retest_header(protocol, corpus, snapshot, failures, path)
    command_ids, commands_by_id = _validate_retest_commands(protocol, snapshot, failures, path)

    release_artifacts = [item for item in release.manifest.get("artifacts", []) if isinstance(item, Mapping)]
    release_artifacts_by_path = {
        item.get("path"): item for item in release_artifacts if isinstance(item.get("path"), str)
    }
    expected_release_paths: set[str] = set()
    observations = snapshot.get("observations")
    observation_ids, unique_observation_ids = _stable_ids(observations, "case_id")
    if not _is_sequence(observations) or not unique_observation_ids:
        failures.append(
            _failure(
                "formal-validation-observation-coverage",
                "retest observations must have unique case ids",
                path,
            )
        )
        observations = []
    for observation in observations:
        expected_release_paths.update(
            _validate_retest_observation(
                repo_root,
                snapshot,
                cases_by_id,
                (release_artifacts_by_path, commands_by_id),
                observation,
                failures,
                path,
            )
        )
    if observation_ids != set(cases_by_id) or len(observation_ids) != len(cases_by_id):
        failures.append(
            _failure(
                "formal-validation-observation-coverage",
                "retest snapshot must contain exactly one observation per v2 corpus case",
                path,
            )
        )
    if (
        command_ids.issuperset(
            {
                case_id
                for case_id, case in cases_by_id.items()
                if case.get("replay_mode") in PRODUCTION_EVIDENCE_REPLAY_MODES
            }
        )
        is False
    ):
        failures.append(
            _failure(
                "formal-validation-production-command",
                "every production evidence case needs one fixed command",
                path,
            )
        )
    selected_release_paths = {
        str(item.get("path"))
        for item in release_artifacts
        if item.get("kind") in {"corpus-input", "production-evidence"}
    }
    if selected_release_paths != expected_release_paths:
        failures.append(
            _failure(
                "formal-validation-production-evidence-join",
                "the atomic release must select exactly every production input and evidence artifact",
                release.manifest_path,
            )
        )

    _validate_retest_participant_observations(protocol, snapshot, failures, path)


def _validate_retest_header(
    protocol: Mapping[str, object],
    corpus: Mapping[str, object],
    snapshot: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    if (
        snapshot.get("protocol_revision") != protocol.get("revision")
        or snapshot.get("corpus_revision") != corpus.get("revision")
        or snapshot.get("execution_status") != "complete"
    ):
        failures.append(
            _failure(
                "formal-validation-snapshot-revision",
                "retest snapshot must bind the selected revisions and a complete execution",
                path,
            )
        )
    revision = snapshot.get("raes_revision")
    if not isinstance(revision, str) or not _COMMIT_RE.fullmatch(revision):
        failures.append(
            _failure(
                "formal-validation-revision-pin",
                "retest snapshot must pin a full RAES commit",
                path,
            )
        )
    versions = snapshot.get("versions")
    if (
        not isinstance(versions, Mapping)
        or set(versions) != _VERSION_KEYS
        or not all(_nonempty_string(value) for value in versions.values())
    ):
        failures.append(
            _failure(
                "formal-validation-version-disclosure",
                "retest snapshot must record the bounded output-affecting versions",
                path,
            )
        )


def _validate_retest_commands(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> tuple[set[object], dict[object, Mapping[str, object]]]:
    commands = snapshot.get("commands")
    command_ids, unique_command_ids = _stable_ids(commands, "command_id")
    commands_by_id = (
        {item.get("command_id"): item for item in commands if isinstance(item, Mapping)}
        if _is_sequence(commands)
        else {}
    )
    if not _is_sequence(commands) or not unique_command_ids:
        failures.append(
            _failure(
                "formal-validation-commands",
                "retest command ids must be a unique bounded list",
                path,
            )
        )
        commands = []
    for command in commands:
        _validate_retest_command(command, failures, path)
    _validate_retest_participant_command(protocol, commands_by_id, failures, path)
    return command_ids, commands_by_id


def _validate_retest_command(command: object, failures: list[PolicyFailure], path: str) -> None:
    if not _closed_object(
        command,
        _COMMAND_KEYS,
        rule_id="formal-validation-command-shape",
        label="retest command",
        failures=failures,
        path=path,
    ):
        return
    if not _string_list(command.get("argv")) or command.get("network") != "disabled":
        failures.append(
            _failure(
                "formal-validation-commands",
                f"command {command.get('command_id')!r} must use fixed argv with network disabled",
                path,
            )
        )


def _validate_retest_participant_command(
    protocol: Mapping[str, object],
    commands_by_id: Mapping[object, Mapping[str, object]],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    participant_command = commands_by_id.get("participant-fixtures")
    expected_argv = [
        "implementations/python/.venv/bin/pytest",
        "-q",
        *_participant_test_refs(protocol),
    ]
    if not isinstance(participant_command, Mapping) or participant_command.get("argv") != expected_argv:
        failures.append(
            _failure(
                "formal-validation-participant-command",
                "retest snapshot must retain the complete participant fixture command",
                path,
            )
        )


def _validate_retest_observation(
    repo_root: Path,
    snapshot: Mapping[str, object],
    cases_by_id: Mapping[str, Mapping[str, object]],
    replay_context: tuple[
        Mapping[object, Mapping[str, object]],
        Mapping[object, Mapping[str, object]],
    ],
    observation: object,
    failures: list[PolicyFailure],
    path: str,
) -> set[str]:
    expected_paths: set[str] = set()
    if not _closed_object(
        observation,
        _OBSERVATION_V2_KEYS,
        rule_id="formal-validation-observation-shape",
        label="retest observation",
        failures=failures,
        path=path,
    ):
        return expected_paths
    case_id = observation.get("case_id")
    case = cases_by_id.get(str(case_id))
    if case is None:
        failures.append(
            _failure(
                "formal-validation-observation-case",
                f"observation references unknown case {case_id!r}",
                path,
            )
        )
    else:
        _validate_retest_observation_metadata(snapshot, case, observation, failures, path)
        if case.get("replay_mode") in PRODUCTION_EVIDENCE_REPLAY_MODES:
            release_artifacts_by_path, commands_by_id = replay_context
            _validate_production_evidence_observation(
                repo_root,
                release_artifacts_by_path,
                case,
                observation,
                commands_by_id.get(case_id),
                failures,
                path,
            )
            expected_paths.update(
                value
                for value in (case.get("fixture_path"), observation.get("evidence_artifact_path"))
                if isinstance(value, str)
            )
        else:
            _validate_retained_retest_observation(repo_root, case, observation, failures, path)
    return expected_paths


def _validate_retest_observation_metadata(
    snapshot: Mapping[str, object],
    case: Mapping[str, object],
    observation: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    case_id = observation.get("case_id")
    if observation.get("execution_id") != snapshot.get("execution_id") or observation.get(
        "configuration_id"
    ) != snapshot.get("configuration_id"):
        failures.append(
            _failure(
                "formal-validation-observation-join",
                f"observation {case_id!r} must bind the retest execution and configuration",
                path,
            )
        )
    expected_replayable = case.get("replay_mode") != "unsupported"
    if observation.get("replayable") is not expected_replayable:
        failures.append(
            _failure(
                "formal-validation-observation-replayable",
                f"observation {case_id!r} misstates replayability",
                path,
            )
        )
    if not _string_list(observation.get("evidence_refs")) or not _string_list(observation.get("limitations")):
        failures.append(
            _failure(
                "formal-validation-observation-evidence",
                f"observation {case_id!r} needs evidence refs and explicit limitations",
                path,
            )
        )


def _validate_retained_retest_observation(
    repo_root: Path,
    case: Mapping[str, object],
    observation: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    case_id = observation.get("case_id")
    evidence_fields = (
        "evidence_profile",
        "analysis_profile",
        "configuration_digest",
        "evidence_digest",
        "evidence_artifact_path",
        "evidence_artifact_sha256",
        "source_digest",
    )
    if any(observation.get(key) is not None for key in evidence_fields):
        failures.append(
            _failure(
                "formal-validation-production-evidence-join",
                f"retained case {case_id!r} must not synthesize a production envelope",
                path,
            )
        )
    if case.get("replay_mode") == "unsupported":
        _validate_unsupported_retest_observation(observation, failures, path)
        return
    try:
        replayed = replay_case(repo_root, case)
    except (OSError, ValueError) as exc:
        failures.append(
            _failure(
                "formal-validation-replay-error",
                f"retained case {case_id!r} could not replay ({type(exc).__name__})",
                path,
            )
        )
    else:
        if not _replay_observation_matches(case_id, observation, replayed):
            failures.append(
                _failure(
                    "formal-validation-replay-drift",
                    f"retained case {case_id!r} drifted without a matching observation",
                    path,
                )
            )


def _validate_unsupported_retest_observation(
    observation: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    if (
        observation.get("actual_outcome") != "unsupported"
        or observation.get("diagnostic_kind") is not None
        or observation.get("result_digest") is not None
    ):
        failures.append(
            _failure(
                "formal-validation-unsupported-observation",
                f"historical unsupported case {observation.get('case_id')!r} must remain unsupported",
                path,
            )
        )


def _validate_retest_participant_observations(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    obligations = {
        item.get("obligation_id"): item
        for item in protocol.get("participant_obligations", [])
        if isinstance(item, Mapping)
    }
    observations = snapshot.get("participant_observations")
    observation_ids, unique = _stable_ids(observations, "obligation_id")
    if not _is_sequence(observations) or not unique or observation_ids != set(obligations):
        failures.append(
            _failure(
                "formal-validation-participant-observation-coverage",
                "retest snapshot must retain every participant obligation exactly once",
                path,
            )
        )
        return
    for observation in observations:
        if not _closed_object(
            observation,
            _PARTICIPANT_OBSERVATION_KEYS,
            rule_id="formal-validation-participant-observation-shape",
            label="participant observation",
            failures=failures,
            path=path,
        ):
            continue
        obligation = obligations.get(observation.get("obligation_id"))
        expected_refs = (
            [
                obligation.get("positive_test_ref"),
                obligation.get("negative_test_ref"),
            ]
            if isinstance(obligation, Mapping)
            else []
        )
        if (
            observation.get("execution_id") != snapshot.get("execution_id")
            or observation.get("evidence_refs") != expected_refs
            or observation.get("positive_outcome") != "passed"
            or observation.get("negative_outcome") != "passed"
            or not _string_list(observation.get("limitations"))
        ):
            failures.append(
                _failure(
                    "formal-validation-participant-observation-join",
                    f"participant observation {observation.get('obligation_id')!r} is stale",
                    path,
                )
            )


@dataclasses.dataclass(frozen=True)
class _ProductionEvidenceReplay:
    evidence_digest_matches: bool
    direct_digest: str
    outcome: str
    profile: str
    analysis_profile: str
    configuration_digest: str
    source_digest: str


def _validate_production_evidence_observation(
    repo_root: Path,
    release_artifacts_by_path: Mapping[object, Mapping[str, object]],
    case: Mapping[str, object],
    observation: Mapping[str, object],
    command: object,
    failures: list[PolicyFailure],
    path: str,
) -> None:
    case_id = case.get("case_id")
    replay_mode = case.get("replay_mode")
    fixture_value = case.get("fixture_path")
    evidence_value = observation.get("evidence_artifact_path")
    fixture = safe_repo_path(repo_root, fixture_value) if isinstance(fixture_value, str) else None
    evidence_path = safe_repo_path(repo_root, evidence_value) if isinstance(evidence_value, str) else None
    fixture_pin = release_artifacts_by_path.get(fixture_value)
    evidence_pin = release_artifacts_by_path.get(evidence_value)
    if (
        fixture is None
        or not fixture.is_file()
        or evidence_path is None
        or not evidence_path.is_file()
        or fixture_pin is None
        or fixture_pin.get("kind") != "corpus-input"
        or evidence_pin is None
        or evidence_pin.get("kind") != "production-evidence"
    ):
        failures.append(
            _failure(
                "formal-validation-production-evidence-join",
                f"case {case_id!r} lacks an atomically selected input or evidence artifact",
                path,
            )
        )
        return
    if observation.get("evidence_artifact_sha256") != _sha256_file(evidence_path) or evidence_pin.get(
        "sha256"
    ) != observation.get("evidence_artifact_sha256"):
        failures.append(
            _failure(
                "formal-validation-production-evidence-join",
                f"case {case_id!r} evidence artifact SHA-256 is stale",
                path,
            )
        )
    expected_argv = _production_evidence_argv(str(replay_mode), fixture_value)
    _validate_production_evidence_command(command, expected_argv, case_id, failures, path)
    try:
        replay = _replay_production_evidence(
            repo_root,
            case,
            observation,
            fixture,
            evidence_value,
            expected_argv,
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as exc:
        failures.append(
            _failure(
                "formal-validation-production-replay",
                f"case {case_id!r} production replay failed ({type(exc).__name__})",
                path,
            )
        )
        return
    if not _production_evidence_joins_match(case, observation, replay):
        failures.append(
            _failure(
                "formal-validation-production-evidence-join",
                f"case {case_id!r} source, configuration, outcome, CLI, replay, or evidence joins drifted",
                path,
            )
        )


def _replay_production_evidence(
    repo_root: Path,
    case: Mapping[str, object],
    observation: Mapping[str, object],
    fixture: Path,
    evidence_value: object,
    expected_argv: list[object],
) -> _ProductionEvidenceReplay:
    replay_mode = case.get("replay_mode")
    if replay_mode == "exploit-path":
        load_bounded_json_object(repo_root, str(case.get("fixture_path")), max_bytes=2 * 1024 * 1024)
    stored_payload = load_bounded_json_object(
        repo_root,
        str(evidence_value),
        max_bytes=_MAX_FILE_BYTES,
    )
    if replay_mode == "satisfiability":
        from raes_contracts.satisfiability import ScenarioSatisfiabilityEvidenceModel
        from raes_processor.satisfiability import analyze_scenario_file, replay_satisfiability_evidence

        stored = ScenarioSatisfiabilityEvidenceModel.model_validate(stored_payload)
        direct = analyze_scenario_file(fixture, profile=_CURRENT_SATISFIABILITY_PROFILE)
        configuration_digest = direct.solver_configuration_digest
    else:
        from raes_contracts.exploit_path import ExploitPathAnalysisEvidenceModel
        from raes_processor.exploit_path import analyze_exploit_path_file, replay_exploit_path_evidence

        stored = ExploitPathAnalysisEvidenceModel.model_validate(stored_payload)
        direct = analyze_exploit_path_file(fixture, profile="raes-exploit-path-analysis-v1")
        configuration_digest = direct.search_configuration_digest
    from raes_contracts.canonical import canonical_json_digest
    from raes_contracts.satisfiability import canonical_contract_digest

    stored_artifact_matches = canonical_json_digest(stored_payload) == observation.get("evidence_digest")
    direct_digest = canonical_contract_digest(direct)
    stored_digest = canonical_contract_digest(stored)
    cli_payload = _run_production_evidence_cli(repo_root, expected_argv)
    cli = type(stored).model_validate(cli_payload)
    cli_digest = canonical_contract_digest(cli)
    migration_pair = _MIGRATED_PRODUCTION_EVIDENCE_DIGESTS.get(str(case.get("case_id")))
    evidence_digest_matches = stored_artifact_matches and stored_digest == direct_digest == cli_digest
    if stored_artifact_matches and migration_pair == (observation.get("evidence_digest"), direct_digest):
        evidence_digest_matches = cli_digest == direct_digest
    elif evidence_digest_matches:
        if replay_mode == "satisfiability":
            replay_satisfiability_evidence(fixture, stored)
        else:
            replay_exploit_path_evidence(fixture, stored)
    return _ProductionEvidenceReplay(
        evidence_digest_matches=evidence_digest_matches,
        direct_digest=direct_digest,
        outcome=direct.outcome.value,
        profile=direct.profile,
        analysis_profile=direct.analysis_profile,
        configuration_digest=configuration_digest,
        source_digest=direct.source.byte_digest,
    )


def _production_evidence_joins_match(
    case: Mapping[str, object],
    observation: Mapping[str, object],
    replay: _ProductionEvidenceReplay,
) -> bool:
    evidence_digest = observation.get("evidence_digest")
    joins = (
        observation.get("actual_outcome") == replay.outcome == case.get("expected_outcome"),
        observation.get("diagnostic_kind") == replay.profile,
        observation.get("result_digest") == evidence_digest,
        observation.get("evidence_profile") == replay.profile,
        observation.get("analysis_profile") == replay.analysis_profile,
        observation.get("configuration_digest") == replay.configuration_digest,
        observation.get("source_digest") == replay.source_digest,
    )
    digest_join = evidence_digest == replay.direct_digest or _MIGRATED_PRODUCTION_EVIDENCE_DIGESTS.get(
        str(case.get("case_id"))
    ) == (evidence_digest, replay.direct_digest)
    return replay.evidence_digest_matches and digest_join and all(joins)


def _production_evidence_argv(replay_mode: str, fixture_value: object) -> list[object]:
    return [
        "implementations/python/.venv/bin/raes",
        "processor",
        "satisfiability" if replay_mode == "satisfiability" else "exploit-path",
        fixture_value,
        "--profile",
        (_CURRENT_SATISFIABILITY_PROFILE if replay_mode == "satisfiability" else "raes-exploit-path-analysis-v1"),
    ]


def _validate_production_evidence_command(
    command: object,
    expected_argv: list[object],
    case_id: object,
    failures: list[PolicyFailure],
    path: str,
) -> None:
    if not isinstance(command, Mapping) or command.get("argv") != expected_argv or command.get("network") != "disabled":
        failures.append(
            _failure(
                "formal-validation-production-command",
                f"case {case_id!r} must use its production CLI with fixed offline argv",
                path,
            )
        )


def _run_production_evidence_cli(repo_root: Path, argv: list[object]) -> dict[str, object]:
    if not all(isinstance(value, str) for value in argv):
        raise ValueError("production evidence argv must contain only strings")
    executable = safe_repo_path(repo_root, str(argv[0]))
    if executable is None or not executable.is_file():
        raise ValueError("production evidence executable is missing")
    completed = subprocess.run(
        [str(executable), *(str(value) for value in argv[1:])],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env={},
    )
    if len(completed.stdout.encode("utf-8")) > _MAX_FILE_BYTES or len(completed.stderr.encode("utf-8")) > 16 * 1024:
        raise ValueError("production evidence command exceeded its output bound")
    if completed.returncode != 0 or completed.stderr:
        raise ValueError(f"production evidence command exited with status {completed.returncode}")
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("production evidence command did not emit an object")
    return payload


def load_bundle(repo_root: Path = REPO_ROOT) -> tuple[_JsonObject, _JsonObject, _JsonObject, _JsonObject, _JsonObject]:
    manifest = _assembled_manifest(repo_root)
    paths: list[str] = []
    for key in ("protocol_path", "corpus_path", "snapshot_path", "analysis_path"):
        value = manifest.get(key)
        if not _nonempty_string(value) or safe_repo_path(repo_root, str(value)) is None:
            raise ValueError(f"manifest {key} must be a safe repository path")
        paths.append(str(value))
    protocol, corpus, snapshot, analysis = (
        load_bounded_json_object(repo_root, path, max_bytes=_MAX_FILE_BYTES) for path in paths
    )
    return manifest, protocol, corpus, snapshot, analysis


def load_satisfiability_analysis(
    repo_root: Path = REPO_ROOT,
) -> tuple[_JsonObject, _JsonObject, _JsonObject]:
    """Load the revisioned issue-826 supplement selected by the bundle."""

    manifest = _assembled_manifest(repo_root)
    values = [
        manifest.get("satisfiability_snapshot_path"),
        manifest.get("satisfiability_analysis_path"),
    ]
    for key, value in zip(
        ("satisfiability_snapshot_path", "satisfiability_analysis_path"),
        values,
        strict=True,
    ):
        path = safe_repo_path(repo_root, str(value)) if _nonempty_string(value) else None
        if path is None:
            raise ValueError(f"manifest {key} must be a safe repository path")
    snapshot, analysis = (
        load_bounded_json_object(repo_root, str(value), max_bytes=_MAX_FILE_BYTES) for value in values
    )
    return manifest, snapshot, analysis


def _assembled_manifest(repo_root: Path) -> dict[str, object]:
    releases = load_release_bundles(repo_root)
    historical = [
        item
        for item in releases
        if item.protocol.get("revision") == "1.0.0"
        and any(
            isinstance(artifact, Mapping) and artifact.get("kind") == "satisfiability-analysis"
            for artifact in item.manifest.get("artifacts", [])
        )
    ]
    if not historical:
        raise ValueError(f"{MANIFEST_PATH!r} must select an atomic historical satisfiability release")
    release = max(historical, key=lambda item: revision_key(item.manifest.get("revision")))
    artifact_by_kind = {
        artifact.get("kind"): artifact
        for artifact in release.manifest.get("artifacts", [])
        if isinstance(artifact, Mapping)
    }
    supplement_snapshot = artifact_by_kind["satisfiability-snapshot"]
    supplement_analysis = artifact_by_kind["satisfiability-analysis"]
    return {
        "bundle_id": _HISTORICAL_BUNDLE_ID,
        "revision": release.manifest["revision"],
        "protocol_path": release.manifest["protocol_path"],
        "corpus_path": release.manifest["corpus_path"],
        "snapshot_path": release.manifest["snapshot_path"],
        "analysis_path": release.manifest["analysis_path"],
        "satisfiability_snapshot_path": supplement_snapshot["path"],
        "satisfiability_analysis_path": supplement_analysis["path"],
    }


def validate_satisfiability_analysis(
    repo_root: Path,
    manifest: _JsonObject,
    snapshot: _JsonObject,
    analysis: _JsonObject,
) -> list[PolicyFailure]:
    """Recompute the finite-profile control matrix and replay every envelope."""

    failures: list[PolicyFailure] = []
    path = str(manifest.get("satisfiability_analysis_path"))
    snapshot_path = str(manifest.get("satisfiability_snapshot_path"))
    if manifest.get("revision") != "2.0.0":
        failures.append(
            _failure(
                "formal-satisfiability-manifest-revision",
                "the satisfiability supplement requires bundle revision 2.0.0",
                MANIFEST_PATH,
            )
        )
    if not _closed_object(
        analysis,
        _SATISFIABILITY_ANALYSIS_KEYS,
        rule_id="formal-satisfiability-analysis-shape",
        label="satisfiability analysis",
        failures=failures,
        path=path,
    ):
        return failures
    snapshot_shape_valid = _closed_object(
        snapshot,
        _SATISFIABILITY_SNAPSHOT_KEYS,
        rule_id="formal-satisfiability-snapshot-shape",
        label="satisfiability execution snapshot",
        failures=failures,
        path=snapshot_path,
    )
    if (
        analysis.get("profile") != _HISTORICAL_SATISFIABILITY_ANALYSIS_PROFILE
        or analysis.get("revision") != "1.0.0"
        or analysis.get("issue_number") != 826
        or analysis.get("requirement_uid") != "ASR-530"
        or analysis.get("analysis_profile") != _HISTORICAL_SATISFIABILITY_PROFILE
        or analysis.get("claim_class_id") != "constraint-satisfiability"
    ):
        failures.append(
            _failure(
                "formal-satisfiability-scope",
                "the supplement must remain bound to issue 826, ASR-530, and the v1 finite-domain profile",
                path,
            )
        )
    if not snapshot_shape_valid:
        return failures
    if (
        snapshot.get("profile") != _HISTORICAL_SATISFIABILITY_EXECUTION_PROFILE
        or snapshot.get("revision") != "1.0.0"
        or snapshot.get("execution_id") != analysis.get("execution_id")
        or snapshot.get("revision") != analysis.get("snapshot_revision")
        or snapshot.get("analysis_profile") != analysis.get("analysis_profile")
        or not _nonempty_string(snapshot.get("captured_at"))
        or not _nonempty_string(snapshot.get("solver_configuration_digest"))
        or snapshot.get("deviations") != []
    ):
        failures.append(
            _failure(
                "formal-satisfiability-snapshot-join",
                "the execution snapshot must bind the analysis, profile, configuration, and no-deviation run",
                snapshot_path,
            )
        )
    if (
        analysis.get("evidence_status") != "demonstrated"
        or not _nonempty_string(analysis.get("scope"))
        or not _string_list(analysis.get("limitations"))
    ):
        failures.append(
            _failure(
                "formal-satisfiability-disclosure",
                "the bounded demonstrated result requires a scope and non-empty limitations",
                path,
            )
        )

    cases = analysis.get("cases")
    if not _is_sequence(cases) or len(cases) != len(_SATISFIABILITY_CONTROL_OUTCOMES):
        failures.append(
            _failure(
                "formal-satisfiability-control-coverage",
                "the supplement requires exactly one positive, negative, and unsupported control",
                path,
            )
        )
        return failures
    controls = [item.get("control") for item in cases if isinstance(item, Mapping)]
    case_ids, unique_case_ids = _stable_ids(cases, "case_id")
    if (
        set(controls) != set(_SATISFIABILITY_CONTROL_OUTCOMES)
        or len(controls) != len(set(controls))
        or len(case_ids) != len(cases)
        or not unique_case_ids
    ):
        failures.append(
            _failure(
                "formal-satisfiability-control-coverage",
                "controls and case ids must be complete, unique, and stable",
                path,
            )
        )

    cases_by_id = {
        item.get("case_id"): item
        for item in cases
        if isinstance(item, Mapping) and _nonempty_string(item.get("case_id"))
    }
    commands = snapshot.get("commands")
    command_ids, unique_command_ids = _stable_ids(commands, "command_id")
    if not _is_sequence(commands) or command_ids != set(cases_by_id) or not unique_command_ids:
        failures.append(
            _failure(
                "formal-satisfiability-snapshot-commands",
                "the snapshot requires one fixed-argv command per satisfiability case",
                snapshot_path,
            )
        )
        commands = []
    for command in commands:
        if not _closed_object(
            command,
            _COMMAND_KEYS,
            rule_id="formal-satisfiability-command-shape",
            label="satisfiability command",
            failures=failures,
            path=snapshot_path,
        ):
            continue
        case = cases_by_id.get(command.get("command_id"))
        expected_argv = [
            _HISTORICAL_CLI,
            "processor",
            "satisfiability",
            case.get("fixture_path") if isinstance(case, Mapping) else None,
            "--profile",
            analysis.get("analysis_profile"),
        ]
        if command.get("argv") != expected_argv or command.get("network") != "disabled":
            failures.append(
                _failure(
                    "formal-satisfiability-snapshot-commands",
                    f"command {command.get('command_id')!r} drifted from its fixed offline invocation",
                    snapshot_path,
                )
            )

    observations = snapshot.get("observations")
    observation_ids, unique_observation_ids = _stable_ids(observations, "case_id")
    if not _is_sequence(observations) or observation_ids != set(cases_by_id) or not unique_observation_ids:
        failures.append(
            _failure(
                "formal-satisfiability-snapshot-coverage",
                "the snapshot requires one observation per satisfiability case",
                snapshot_path,
            )
        )
        observations = []
    observations_by_case: dict[object, Mapping[str, object]] = {}
    for observation in observations:
        if not _closed_object(
            observation,
            _SATISFIABILITY_OBSERVATION_KEYS,
            rule_id="formal-satisfiability-observation-shape",
            label="satisfiability observation",
            failures=failures,
            path=snapshot_path,
        ):
            continue
        observations_by_case[observation.get("case_id")] = observation
        if (
            observation.get("evidence_profile") != "scenario-satisfiability-evidence/v1"
            or observation.get("replayable") is not True
            or not _nonempty_string(observation.get("limitation"))
        ):
            failures.append(
                _failure(
                    "formal-satisfiability-snapshot-disclosure",
                    f"observation {observation.get('case_id')!r} lacks replay or limitation disclosure",
                    snapshot_path,
                )
            )

    from raes_processor.satisfiability import (
        analyze_scenario_file,
        replay_satisfiability_evidence,
    )

    for item in cases:
        if not _closed_object(
            item,
            _SATISFIABILITY_CASE_KEYS,
            rule_id="formal-satisfiability-case-shape",
            label="satisfiability case",
            failures=failures,
            path=path,
        ):
            continue
        case_id = item.get("case_id")
        control = item.get("control")
        expected_for_control = _SATISFIABILITY_CONTROL_OUTCOMES.get(str(control))
        if expected_for_control is None or item.get("expected_outcome") != expected_for_control:
            failures.append(
                _failure(
                    "formal-satisfiability-replay-drift",
                    f"case {case_id!r} does not preserve its control outcome",
                    path,
                )
            )
        fixture_value = item.get("fixture_path")
        fixture = safe_repo_path(repo_root, str(fixture_value)) if _nonempty_string(fixture_value) else None
        if fixture is None or not fixture.is_file():
            failures.append(
                _failure(
                    "formal-satisfiability-case-path",
                    f"case {case_id!r} has a missing or unsafe fixture",
                    path,
                )
            )
            continue
        if not _nonempty_string(item.get("limitation")):
            failures.append(
                _failure(
                    "formal-satisfiability-case-limit",
                    f"case {case_id!r} must record a limitation",
                    path,
                )
            )
        try:
            evidence = analyze_scenario_file(fixture, profile=_CURRENT_SATISFIABILITY_PROFILE)
            replay_satisfiability_evidence(fixture, evidence)
        except (OSError, ValueError, RuntimeError) as exc:
            failures.append(
                _failure(
                    "formal-satisfiability-replay-error",
                    f"case {case_id!r} could not complete production replay ({type(exc).__name__})",
                    path,
                )
            )
            continue
        normalized_digest_matches = evidence.normalized_model_digest == item.get("expected_normalized_model_digest")
        normalized_digest_matches = normalized_digest_matches or _RENAMED_SATISFIABILITY_MODEL_DIGESTS.get(
            str(case_id)
        ) == (
            item.get("expected_normalized_model_digest"),
            evidence.normalized_model_digest,
        )
        if evidence.outcome.value != item.get("expected_outcome") or not normalized_digest_matches:
            failures.append(
                _failure(
                    "formal-satisfiability-replay-drift",
                    f"case {case_id!r} drifted from its frozen outcome or normalized model",
                    path,
                )
            )
        observation = observations_by_case.get(case_id)
        observation_normalized_digest_matches = observation is not None and (
            observation.get("normalized_model_digest") == evidence.normalized_model_digest
            or _RENAMED_SATISFIABILITY_MODEL_DIGESTS.get(str(case_id))
            == (
                observation.get("normalized_model_digest"),
                evidence.normalized_model_digest,
            )
        )
        solver_digest_matches = (
            snapshot.get("solver_configuration_digest") == evidence.solver_configuration_digest
            or (
                snapshot.get("solver_configuration_digest"),
                evidence.solver_configuration_digest,
            )
            == _RENAMED_SOLVER_CONFIGURATION_DIGEST
        )
        if observation is None or (
            observation.get("actual_outcome") != evidence.outcome.value
            or observation.get("source_byte_digest") != evidence.source.byte_digest
            or not observation_normalized_digest_matches
            or not solver_digest_matches
        ):
            failures.append(
                _failure(
                    "formal-satisfiability-snapshot-drift",
                    f"case {case_id!r} drifted from its execution snapshot",
                    snapshot_path,
                )
            )
        if control == "positive" and evidence.witness is None:
            failures.append(
                _failure(
                    "formal-satisfiability-evidence-shape",
                    "positive control lacks a witness",
                    path,
                )
            )
        elif control == "negative" and evidence.unsat_core is None:
            failures.append(
                _failure(
                    "formal-satisfiability-evidence-shape",
                    "negative control lacks a core",
                    path,
                )
            )
        elif control == "unsupported" and (evidence.unsupported is None or not evidence.diagnostics):
            failures.append(
                _failure(
                    "formal-satisfiability-evidence-shape",
                    "unsupported control lacks its fail-closed disclosure",
                    path,
                )
            )
    return failures


def validate_bundle(
    repo_root: Path,
    manifest: _JsonObject,
    protocol: _JsonObject,
    corpus: _JsonObject,
    snapshot: _JsonObject,
    analysis: _JsonObject,
    *,
    replay_cases: bool = True,
) -> list[PolicyFailure]:
    failures: list[PolicyFailure] = []
    if not _closed_object(
        manifest,
        _MANIFEST_KEYS,
        rule_id="formal-validation-manifest-shape",
        label="manifest",
        failures=failures,
        path=MANIFEST_PATH,
    ):
        return failures
    protocol_path = str(manifest.get("protocol_path"))
    corpus_path = str(manifest.get("corpus_path"))
    snapshot_path = str(manifest.get("snapshot_path"))
    analysis_path = str(manifest.get("analysis_path"))
    _validate_protocol(repo_root, protocol, failures, protocol_path)
    cases_by_id = _validate_corpus(repo_root, protocol, corpus, failures, corpus_path)
    _validate_snapshot(
        repo_root,
        protocol,
        corpus,
        snapshot,
        cases_by_id,
        failures,
        snapshot_path,
        replay_cases=replay_cases,
    )
    _validate_analysis(repo_root, protocol, corpus, snapshot, analysis, failures, analysis_path)
    return failures


def evaluate(
    repo_root: Path = REPO_ROOT,
    *,
    participant_test_runner: ParticipantTestRunner = _replay_participant_tests,
) -> list[PolicyFailure]:
    try:
        releases = load_release_bundles(repo_root)
    except (OSError, ValueError) as exc:
        return [_failure("formal-validation-bundle-load", str(exc), MANIFEST_PATH)]
    failures: list[PolicyFailure] = []
    for release in releases:
        failures.extend(validate_release_bundle(repo_root, release))
    if failures:
        return failures
    protocol = max(releases, key=lambda item: revision_key(item.manifest.get("revision"))).protocol
    test_refs = _participant_test_refs(protocol)
    replayed, detail = participant_test_runner(repo_root, test_refs)
    if not replayed:
        return [
            _failure(
                "formal-validation-participant-replay",
                detail,
                str(
                    max(
                        releases,
                        key=lambda item: revision_key(item.manifest.get("revision")),
                    ).manifest.get("snapshot_path")
                ),
            )
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    failures = evaluate(args.repo_root.resolve())
    if failures:
        for failure in failures:
            print(failure.render(), file=sys.stderr)
        return 1
    print("Formal semantic-validation evidence bundle passed integrity and replay checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
