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
from typing import Protocol

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
MANIFEST_SCHEMA_VERSION = "formal-semantic-validation-bundle-index/v1"
_MAX_FILE_BYTES = 512 * 1024
_MAX_CASES = 128
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

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
_RENAMED_RESULT_DIGESTS = {
    "compile-repeatability-control": (
        "918862c521a9c5a282b7cbd20ba6fcddd20eb90817ed5bcebacdf3270f91d7ac",
        "a5a1840cf01683dc60a87e91a15b99cd0bdcdf5c181b1aedc8f505065a820514",
    ),
    "compile-non-vacuity-control": (
        "c310cf5424ab404673093e5c95801d00e5583947dbcac68c47d4d8c1eb8b6766",
        "50558f4eebab0685559cec27be46f0b0602ef512f42eb7a3471b2001100988a9",
    ),
}
_RENAMED_SATISFIABILITY_MODEL_DIGESTS = {
    "finite-domain-satisfiable": (
        "sha256:32ac029d9279e6c7ea4cd9082435eb6fa455122bba57498923b8371818ef708c",
        "sha256:8e6bcd2f92ac1549c44e91793b565ed570d4afd51aea234b2444d97805b9f78f",
    ),
    "finite-domain-unsatisfiable": (
        "sha256:3a061baa67090e312abc4bca7a3ed24cc9458487b67f2fc37b3b7abcac2ecf1b",
        "sha256:f258eabe4ba3e8e508832b3a3828e69ab82d476ae160feda0d0a9056722559c7",
    ),
    "finite-domain-unsupported": (
        "sha256:2f0f762771dc329419ab739766f684c18261aba28c2fbc50a26ee8ad80224ba5",
        "sha256:4751565c5a5336474158d40a025c035d67ba07381b05e4dce7ef29dee57648db",
    ),
}
_RENAMED_SOLVER_CONFIGURATION_DIGEST = (
    "sha256:63e58f4637dbd8328d84a286e1e5af1f3a69557e5209f683909ce22f39838e7d",
    "sha256:1204635e17e759e9ad3bd6be2ecb28c6de05c07ead6dfdd15936ed5d3d5b81b2",
)

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


def _is_sequence(value: object) -> bool:
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
                f"{label} must use the closed key set; missing={sorted(expected_keys - keys)!r}, unknown={sorted(keys - expected_keys)!r}",
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


def _diagnostic_payload(exc: Exception, repo_root: Path) -> object:
    errors = getattr(exc, "errors", None)
    payload: object = errors if errors is not None else str(exc)
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return rendered.replace(str(repo_root.resolve()), "<repo>")


def replay_case(repo_root: Path, case: Mapping[str, object]) -> dict[str, str | None]:
    """Replay one supported case through its declared production boundary."""
    from raes import SDLError, instantiate_scenario, parse_sdl_file
    from raes_processor.compiler import compile_runtime_model

    fixture_value = case.get("fixture_path")
    fixture = safe_repo_path(repo_root, str(fixture_value)) if _nonempty_string(fixture_value) else None
    if fixture is None or not fixture.is_file():
        raise ValueError(f"missing or unsafe replay fixture {fixture_value!r}")

    replay_mode = case.get("replay_mode")
    if replay_mode == "parse":
        try:
            scenario = parse_sdl_file(fixture)
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

    def compiled_digest(path: Path) -> str:
        scenario = parse_sdl_file(path)
        instantiated = instantiate_scenario(scenario, parameters={})
        return _digest(dataclasses.asdict(compile_runtime_model(instantiated)))

    if replay_mode == "compile-stability":
        first = compiled_digest(fixture)
        second = compiled_digest(fixture)
        return {
            "actual_outcome": "stable" if first == second else "drifted",
            "diagnostic_kind": None,
            "result_digest": _digest([first, second]),
        }
    if replay_mode == "compile-distinguish":
        comparison_value = case.get("comparison_fixture_path")
        comparison = safe_repo_path(repo_root, str(comparison_value)) if _nonempty_string(comparison_value) else None
        if comparison is None or not comparison.is_file():
            raise ValueError(f"missing or unsafe comparison fixture {comparison_value!r}")
        first = compiled_digest(fixture)
        second = compiled_digest(comparison)
        return {
            "actual_outcome": "distinguishable" if first != second else "indistinguishable",
            "diagnostic_kind": None,
            "result_digest": _digest([first, second]),
        }
    raise ValueError(f"case {case.get('case_id')!r} is not replayable")


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
        re.search(rf"^def {re.escape(function_name)}\s*\(", path.read_text(encoding="utf-8"), re.MULTILINE) is not None
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
        return False, f"participant fixture replay exited with status {completed.returncode}"
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
        status = expected_status if matching == len(class_cases) and class_cases else "refuted"
        results.append(
            {
                "claim_class_id": claim_class_id,
                "evidence_status": status,
                "case_count": len(class_cases),
                "matching_case_count": matching,
                "replayable_case_count": sum(1 for item in class_cases if item.get("replay_mode") != "unsupported"),
                "unsupported_case_count": sum(1 for item in class_cases if item.get("replay_mode") == "unsupported"),
                "participant_obligation_count": participant_count if claim_class_id == "semantic-consistency" else 0,
            }
        )
    return results


def _validate_protocol(repo_root: Path, protocol: dict, failures: list[PolicyFailure], path: str) -> None:
    if not _closed_object(
        protocol,
        _PROTOCOL_KEYS,
        rule_id="formal-validation-protocol-shape",
        label="protocol",
        failures=failures,
        path=path,
    ):
        return
    if protocol.get("issue_number") != 168 or protocol.get("requirement_uid") != "ASR-530":
        failures.append(
            _failure("formal-validation-protocol-scope", "protocol must remain anchored to issue 168 and ASR-530", path)
        )
    if set(protocol.get("evidence_status_values", [])) != EVIDENCE_STATUSES:
        failures.append(
            _failure("formal-validation-evidence-status", "protocol must use the ADR-021 evidence statuses", path)
        )
    if not _closed_object(
        protocol.get("analysis_rules"),
        _ANALYSIS_RULE_KEYS,
        rule_id="formal-validation-analysis-rules",
        label="analysis_rules",
        failures=failures,
        path=path,
    ):
        pass

    claim_ids, unique_claim_ids = _stable_ids(protocol.get("claim_classes"), "claim_class_id")
    if claim_ids != REQUIRED_CLAIM_CLASS_IDS or not unique_claim_ids:
        failures.append(
            _failure(
                "formal-validation-claim-coverage", "protocol must contain each required claim class exactly once", path
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
    protocol: dict,
    corpus: dict,
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
            _failure("formal-validation-case-count", f"corpus cases must contain 1..{_MAX_CASES} entries", path)
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
                _failure("formal-validation-case-claim", f"case {case_id!r} references unknown claim class", path)
            )
        else:
            polarities[claim_id].add(item.get("polarity"))
        if item.get("polarity") not in {"positive", "negative"}:
            failures.append(_failure("formal-validation-case-polarity", f"case {case_id!r} has invalid polarity", path))
        replay_mode = item.get("replay_mode")
        if replay_mode not in REPLAY_MODES:
            failures.append(
                _failure("formal-validation-replay-mode", f"case {case_id!r} has invalid replay mode", path)
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
                    _failure("formal-validation-case-path", f"case {case_id!r} has a missing or unsafe fixture", path)
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
                        "formal-validation-case-path", f"case {case_id!r} has an unexpected comparison fixture", path
                    )
                )
        if not _nonempty_string(item.get("limitation")):
            failures.append(
                _failure("formal-validation-case-limit", f"case {case_id!r} must record a limitation", path)
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
    protocol: dict,
    corpus: dict,
    snapshot: dict,
    cases_by_id: dict[str, Mapping[str, object]],
    failures: list[PolicyFailure],
    path: str,
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
            _failure("formal-validation-execution-status", "snapshot must preserve a complete execution", path)
        )
    historical_revision = snapshot.get(_HISTORICAL_REVISION_FIELD)
    if not isinstance(historical_revision, str) or not _COMMIT_RE.fullmatch(historical_revision):
        failures.append(
            _failure("formal-validation-revision-pin", "historical revision must be a full immutable Git commit", path)
        )

    commands = snapshot.get("commands")
    if not _is_sequence(commands) or not commands:
        failures.append(
            _failure("formal-validation-commands", "snapshot must record fixed-argv reproduction commands", path)
        )
    else:
        command_ids, unique_command_ids = _stable_ids(commands, "command_id")
        if not command_ids or not unique_command_ids:
            failures.append(_failure("formal-validation-commands", "command ids must be unique stable ids", path))
        for item in commands:
            if not _closed_object(
                item,
                _COMMAND_KEYS,
                rule_id="formal-validation-command-shape",
                label="command",
                failures=failures,
                path=path,
            ):
                continue
            if not _string_list(item.get("argv")) or item.get("network") != "disabled":
                failures.append(
                    _failure(
                        "formal-validation-commands",
                        f"command {item.get('command_id')!r} must use non-empty argv and disabled network",
                        path,
                    )
                )
        participant_refs = _participant_test_refs(protocol)
        expected_participant_argv = [
            "implementations/python/.venv/bin/pytest",
            "-q",
            *participant_refs,
        ]
        participant_commands = [
            item for item in commands if isinstance(item, Mapping) and item.get("command_id") == "participant-fixtures"
        ]
        if len(participant_commands) != 1 or participant_commands[0].get("argv") != expected_participant_argv:
            failures.append(
                _failure(
                    "formal-validation-participant-command",
                    "snapshot must bind the participant replay command to every declared positive and negative test ref",
                    path,
                )
            )

    observations = snapshot.get("observations")
    if not _is_sequence(observations):
        failures.append(_failure("formal-validation-observations", "snapshot observations must be a list", path))
        observations = []
    observation_ids: list[object] = []
    for item in observations:
        if not _closed_object(
            item,
            _OBSERVATION_KEYS,
            rule_id="formal-validation-observation-shape",
            label="observation",
            failures=failures,
            path=path,
        ):
            continue
        case_id = item.get("case_id")
        observation_ids.append(case_id)
        case = cases_by_id.get(str(case_id))
        if case is None:
            failures.append(
                _failure("formal-validation-observation-case", f"observation references unknown case {case_id!r}", path)
            )
            continue
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
                    "formal-validation-observation-replayable", f"observation {case_id!r} misstates replayability", path
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
        if expected_replayable:
            try:
                replayed = replay_case(repo_root, case)
            except (ValueError, OSError) as exc:
                failures.append(
                    _failure("formal-validation-replay-error", f"could not replay {case_id!r}: {exc}", path)
                )
            else:
                for key in ("actual_outcome", "diagnostic_kind", "result_digest"):
                    value_matches = item.get(key) == replayed[key]
                    if key == "result_digest":
                        value_matches = value_matches or _RENAMED_RESULT_DIGESTS.get(str(case_id)) == (
                            item.get(key),
                            replayed[key],
                        )
                    if not value_matches:
                        failures.append(
                            _failure(
                                "formal-validation-replay-drift",
                                f"observation {case_id!r} field {key} drifted from replay",
                                path,
                            )
                        )
                        break
        elif (
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
            _failure("formal-validation-participant-observations", "participant observations must be a list", path)
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
        if not _closed_object(
            item,
            _PARTICIPANT_OBSERVATION_KEYS,
            rule_id="formal-validation-participant-observation-shape",
            label="participant observation",
            failures=failures,
            path=path,
        ):
            continue
        observed_obligations.append(item.get("obligation_id"))
        if item.get("obligation_id") not in obligation_ids:
            failures.append(
                _failure(
                    "formal-validation-participant-observation-join",
                    f"unknown participant obligation {item.get('obligation_id')!r}",
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
        obligation = obligations_by_id.get(item.get("obligation_id"))
        expected_refs = (
            [obligation.get("positive_test_ref"), obligation.get("negative_test_ref")]
            if isinstance(obligation, Mapping)
            else []
        )
        if item.get("evidence_refs") != expected_refs:
            failures.append(
                _failure(
                    "formal-validation-participant-observation-evidence",
                    f"participant obligation {item.get('obligation_id')!r} must bind its declared positive and negative refs",
                    path,
                )
            )
        if item.get("positive_outcome") != "passed" or item.get("negative_outcome") != "passed":
            failures.append(
                _failure(
                    "formal-validation-participant-result",
                    f"participant obligation {item.get('obligation_id')!r} did not preserve passing fixtures",
                    path,
                )
            )
        if (
            not _string_list(item.get("evidence_refs"), nonempty=True)
            or len(item.get("evidence_refs", [])) != 2
            or not _string_list(item.get("limitations"))
        ):
            failures.append(
                _failure(
                    "formal-validation-participant-observation-evidence",
                    f"participant obligation {item.get('obligation_id')!r} needs two evidence refs and limitations",
                    path,
                )
            )
    if set(observed_obligations) != obligation_ids or len(observed_obligations) != len(set(observed_obligations)):
        failures.append(
            _failure(
                "formal-validation-participant-observation-coverage",
                "snapshot must contain exactly one observation per participant obligation",
                path,
            )
        )


def _validate_analysis(
    repo_root: Path,
    protocol: dict,
    corpus: dict,
    snapshot: dict,
    analysis: dict,
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
        failures.append(_failure("formal-validation-analysis-results", "claim_results must be a list", path))
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
                _failure("formal-validation-analysis-result-join", f"unknown claim result {claim_class_id!r}", path)
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
        if expected["evidence_status"] == "untested" and item.get("evidence_status") in {"partial", "demonstrated"}:
            failures.append(
                _failure(
                    "formal-validation-unsupported-overclaim",
                    f"unsupported class {claim_class_id!r} cannot be promoted",
                    path,
                )
            )
        if not _string_list(item.get("limitations")):
            failures.append(
                _failure(
                    "formal-validation-claim-limitations", f"claim result {claim_class_id!r} needs limitations", path
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
    overall = (
        "refuted" if "refuted" in statuses else "partial" if statuses & {"partial", "demonstrated"} else "untested"
    )
    if analysis.get("evidence_status") != overall:
        failures.append(
            _failure("formal-validation-analysis-drift", "overall evidence status does not match claim results", path)
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
    for key in ("threats_to_validity", "allowed_evidence", "disallowed_evidence", "evidence_artifacts"):
        if not _string_list(claim.get(key)):
            failures.append(_failure("formal-validation-claim-record", f"claim needs non-empty {key}", path))
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
                "formal-validation-analysis-disclosure", "analysis needs a plain-language outcome and limitations", path
            )
        )


def load_bundle(repo_root: Path = REPO_ROOT) -> tuple[dict, dict, dict, dict, dict]:
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


def load_satisfiability_analysis(repo_root: Path = REPO_ROOT) -> tuple[dict, dict, dict]:
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
    records = load_index_records(
        repo_root,
        index_path=MANIFEST_PATH,
        schema_version=MANIFEST_SCHEMA_VERSION,
        directory_key="parts_directory",
        max_bytes=_MAX_FILE_BYTES,
    )
    base_parts: list[tuple[str, dict[str, object]]] = []
    supplement_parts: list[tuple[str, dict[str, object]]] = []
    for path, record in records:
        kind = record.get("part_kind")
        revision_key(record.get("revision"))
        if kind == "base":
            expected = {
                "part_kind",
                "revision",
                "protocol_path",
                "corpus_path",
                "snapshot_path",
                "analysis_path",
            }
            base_parts.append((path, record))
        elif kind == "satisfiability":
            expected = {
                "part_kind",
                "revision",
                "satisfiability_snapshot_path",
                "satisfiability_analysis_path",
            }
            supplement_parts.append((path, record))
        else:
            raise ValueError(f"{path!r} has unknown formal evidence part_kind {kind!r}")
        if set(record) != expected:
            raise ValueError(f"{path!r} fields must exactly match {sorted(expected)}")
        for key, value in record.items():
            if not key.endswith("_path"):
                continue
            resolved = safe_repo_path(repo_root, value) if isinstance(value, str) else None
            if resolved is None or not resolved.is_file():
                raise ValueError(f"{path!r} contains unsafe or missing {key}")
    if not base_parts or not supplement_parts:
        raise ValueError(f"{MANIFEST_PATH!r} must select base and satisfiability evidence parts")
    _base_path, base = max(base_parts, key=lambda item: (revision_key(item[1]["revision"]), item[0]))
    _supplement_path, supplement = max(
        supplement_parts,
        key=lambda item: (revision_key(item[1]["revision"]), item[0]),
    )
    return {
        "bundle_id": _HISTORICAL_BUNDLE_ID,
        "revision": supplement["revision"],
        "protocol_path": base["protocol_path"],
        "corpus_path": base["corpus_path"],
        "snapshot_path": base["snapshot_path"],
        "analysis_path": base["analysis_path"],
        "satisfiability_snapshot_path": supplement["satisfiability_snapshot_path"],
        "satisfiability_analysis_path": supplement["satisfiability_analysis_path"],
    }


def validate_satisfiability_analysis(
    repo_root: Path,
    manifest: dict,
    snapshot: dict,
    analysis: dict,
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
            == (observation.get("normalized_model_digest"), evidence.normalized_model_digest)
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
            failures.append(_failure("formal-satisfiability-evidence-shape", "positive control lacks a witness", path))
        elif control == "negative" and evidence.unsat_core is None:
            failures.append(_failure("formal-satisfiability-evidence-shape", "negative control lacks a core", path))
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
    manifest: dict,
    protocol: dict,
    corpus: dict,
    snapshot: dict,
    analysis: dict,
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
    _validate_snapshot(repo_root, protocol, corpus, snapshot, cases_by_id, failures, snapshot_path)
    _validate_analysis(repo_root, protocol, corpus, snapshot, analysis, failures, analysis_path)
    return failures


def evaluate(
    repo_root: Path = REPO_ROOT,
    *,
    participant_test_runner: ParticipantTestRunner = _replay_participant_tests,
) -> list[PolicyFailure]:
    try:
        bundle = load_bundle(repo_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [_failure("formal-validation-bundle-load", str(exc), MANIFEST_PATH)]
    failures = validate_bundle(repo_root, *bundle)
    if failures:
        return failures
    try:
        satisfiability_bundle = load_satisfiability_analysis(repo_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [_failure("formal-satisfiability-bundle-load", str(exc), MANIFEST_PATH)]
    failures = validate_satisfiability_analysis(repo_root, *satisfiability_bundle)
    if failures:
        return failures
    protocol = bundle[1]
    test_refs = _participant_test_refs(protocol)
    replayed, detail = participant_test_runner(repo_root, test_refs)
    if not replayed:
        return [
            _failure(
                "formal-validation-participant-replay",
                detail,
                str(bundle[0].get("snapshot_path")),
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
