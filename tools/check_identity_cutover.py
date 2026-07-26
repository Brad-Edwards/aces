#!/usr/bin/env python3
"""Reject retired project naming outside exact historical records."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.policy.common import (  # noqa: E402
    PolicyFailure,
    failures_to_json,
    load_bounded_json_object,
    safe_repo_path,
)

MANIFEST_PATH = "tools/policy/historical_identity_records.json"
MANIFEST_SCHEMA = "historical-identity-records/v1"
MAX_MANIFEST_BYTES = 1_000_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTITY_PATTERN = re.compile(
    rb"(?:(?<![A-Za-z0-9])|(?<=\\[nrt])|(?<=\\x0[9aAdD])|(?<=\\u000[9aAdD]))"
    rb"(?:A"
    rb"CES|A"
    rb"ces|a"
    rb"ces)(?:[-_.][A-Za-z0-9]+)*"
)
RECORD_CLASSES = {
    "accepted-adr",
    "dated-design-record",
    "historical-index",
    "provenance-record",
    "release-history",
    "research-record",
}

RULE_LIVE = "identity-cutover-live-token"
RULE_MANIFEST = "identity-cutover-manifest"
RULE_MANIFEST_PATH = "identity-cutover-manifest-path"
RULE_HISTORICAL_CONTENT = "identity-cutover-historical-content"
RULE_HISTORICAL_COUNT = "identity-cutover-historical-count"
RULE_TRACKED_TREE = "identity-cutover-tracked-tree"


@dataclass(frozen=True)
class HistoricalRecord:
    path: str
    record_class: str
    rationale: str
    occurrences: int
    content_sha256: str


def _manifest_failure(message: str) -> PolicyFailure:
    return PolicyFailure(RULE_MANIFEST, message, MANIFEST_PATH)


def _load_historical_records(
    repo_root: Path,
) -> tuple[dict[str, HistoricalRecord], list[PolicyFailure]]:
    try:
        payload = load_bounded_json_object(
            repo_root,
            MANIFEST_PATH,
            max_bytes=MAX_MANIFEST_BYTES,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return {}, [_manifest_failure(str(exc))]

    failures: list[PolicyFailure] = []
    if payload.get("schema_version") != MANIFEST_SCHEMA:
        failures.append(_manifest_failure(f"schema_version must be {MANIFEST_SCHEMA!r}"))
    if payload.get("hash_algorithm") != "sha256":
        failures.append(_manifest_failure("hash_algorithm must be 'sha256'"))
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        failures.append(_manifest_failure("records must be a list"))
        return {}, failures

    records: dict[str, HistoricalRecord] = {}
    expected_keys = {
        "path",
        "record_class",
        "rationale",
        "occurrences",
        "content_sha256",
    }
    for index, raw_record in enumerate(raw_records):
        if not isinstance(raw_record, dict):
            failures.append(_manifest_failure(f"records[{index}] must be an object"))
            continue
        if set(raw_record) != expected_keys:
            failures.append(_manifest_failure(f"records[{index}] must contain exactly {sorted(expected_keys)!r}"))
            continue
        path = raw_record.get("path")
        record_class = raw_record.get("record_class")
        rationale = raw_record.get("rationale")
        occurrences = raw_record.get("occurrences")
        content_sha256 = raw_record.get("content_sha256")
        if not isinstance(path, str) or not path:
            failures.append(_manifest_failure(f"records[{index}].path must be a non-empty string"))
            continue
        if path in records:
            failures.append(_manifest_failure(f"duplicate historical record path {path!r}"))
            continue
        if safe_repo_path(repo_root, path) is None:
            failures.append(PolicyFailure(RULE_MANIFEST_PATH, "historical path is unsafe", path))
            continue
        if record_class not in RECORD_CLASSES:
            failures.append(
                _manifest_failure(f"records[{index}].record_class must be one of {sorted(RECORD_CLASSES)!r}")
            )
            continue
        if not isinstance(rationale, str) or not rationale.strip():
            failures.append(_manifest_failure(f"records[{index}].rationale must be non-empty"))
            continue
        if isinstance(occurrences, bool) or not isinstance(occurrences, int) or occurrences < 1:
            failures.append(_manifest_failure(f"records[{index}].occurrences must be a positive integer"))
            continue
        if not isinstance(content_sha256, str) or not SHA256_RE.fullmatch(content_sha256):
            failures.append(_manifest_failure(f"records[{index}].content_sha256 must be a lowercase sha256 digest"))
            continue
        records[path] = HistoricalRecord(
            path=path,
            record_class=record_class,
            rationale=rationale,
            occurrences=occurrences,
            content_sha256=content_sha256,
        )
    return records, failures


def _tracked_paths(repo_root: Path) -> tuple[list[str], list[PolicyFailure]]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
        paths = [raw_path.decode("utf-8") for raw_path in result.stdout.split(b"\0") if raw_path]
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        return [], [PolicyFailure(RULE_TRACKED_TREE, f"cannot enumerate tracked files: {exc}")]
    return paths, []


def _match_lines(content: bytes, matches: list[re.Match[bytes]]) -> list[int]:
    return [content.count(b"\n", 0, match.start()) + 1 for match in matches]


def evaluate_identity_cutover(repo_root: Path = REPO_ROOT) -> list[PolicyFailure]:
    records, failures = _load_historical_records(repo_root)
    tracked_paths, tracked_failures = _tracked_paths(repo_root)
    failures.extend(tracked_failures)
    if failures:
        return failures

    tracked = set(tracked_paths)
    for record_path in sorted(records.keys() - tracked):
        failures.append(
            PolicyFailure(
                RULE_MANIFEST_PATH,
                "historical record is not a tracked file",
                record_path,
            )
        )

    for relative_path in tracked_paths:
        path = safe_repo_path(repo_root, relative_path)
        if path is None or not path.is_file():
            failures.append(
                PolicyFailure(
                    RULE_TRACKED_TREE,
                    "tracked path is missing, unsafe, or not a regular file",
                    relative_path,
                )
            )
            continue
        try:
            content = path.read_bytes()
        except OSError as exc:
            failures.append(
                PolicyFailure(
                    RULE_TRACKED_TREE,
                    f"tracked file cannot be read: {exc}",
                    relative_path,
                )
            )
            continue

        matches = list(IDENTITY_PATTERN.finditer(content))
        record = records.get(relative_path)
        if record is not None:
            digest = hashlib.sha256(content).hexdigest()
            if digest != record.content_sha256:
                failures.append(
                    PolicyFailure(
                        RULE_HISTORICAL_CONTENT,
                        "historical record content no longer matches its classified digest",
                        relative_path,
                    )
                )
            if len(matches) != record.occurrences:
                failures.append(
                    PolicyFailure(
                        RULE_HISTORICAL_COUNT,
                        f"historical record declares {record.occurrences} occurrences but contains {len(matches)}",
                        relative_path,
                    )
                )
            continue

        if matches:
            lines = _match_lines(content, matches)
            displayed = ", ".join(str(line) for line in lines[:8])
            suffix = "" if len(lines) <= 8 else f", plus {len(lines) - 8} more"
            failures.append(
                PolicyFailure(
                    RULE_LIVE,
                    f"contains {len(matches)} retired identity occurrence(s) at line(s) {displayed}{suffix}",
                    relative_path,
                )
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON.")
    args = parser.parse_args()

    failures = evaluate_identity_cutover(REPO_ROOT)
    if args.json:
        print(failures_to_json(failures))
    else:
        for failure in failures:
            print(failure.render(), file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
