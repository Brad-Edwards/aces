from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from tools.check_identity_cutover import evaluate_identity_cutover

REPO_ROOT = Path(__file__).resolve().parents[3]
RETIRED_LOWER = "a" + "ces"
RETIRED_UPPER = "A" + "CES"
MANIFEST_PATH = Path("tools/policy/historical_identity_records.json")


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )


def _record(path: str, content: bytes, *, occurrences: int = 1) -> dict[str, object]:
    return {
        "path": path,
        "record_class": "dated-design-record",
        "rationale": "Preserves a dated design decision from before the identity cutover.",
        "occurrences": occurrences,
        "content_sha256": hashlib.sha256(content).hexdigest(),
    }


def _seed_repo(
    repo_root: Path,
    *,
    files: dict[str, str | bytes],
    records: list[dict[str, object]] | None = None,
) -> None:
    for relative_path, content in files.items():
        _write(repo_root / relative_path, content)
    manifest = {
        "schema_version": "historical-identity-records/v1",
        "hash_algorithm": "sha256",
        "records": records or [],
    }
    _write(
        repo_root / MANIFEST_PATH,
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    )
    _git(repo_root, "init", "-q")
    _git(repo_root, "add", "-A")


def test_current_repository_satisfies_identity_cutover() -> None:
    assert evaluate_identity_cutover(REPO_ROOT) == []


def test_live_retired_identity_fails_in_visible_hidden_and_binary_files(tmp_path: Path) -> None:
    _seed_repo(
        tmp_path,
        files={
            "README.md": f"live {RETIRED_UPPER} identity\n",
            ".github/workflow.yml": f"project: {RETIRED_LOWER}-sdl\n",
            "artifact.bin": b"\x00" + RETIRED_LOWER.encode() + b".runtime\xff",
            "escaped.py": f'value = "prefix\\\\n{RETIRED_LOWER}-artifact\\\\n"\n',
        },
    )

    failures = evaluate_identity_cutover(tmp_path)

    assert {failure.path for failure in failures if failure.rule_id == "identity-cutover-live-token"} == {
        ".github/workflow.yml",
        "README.md",
        "artifact.bin",
        "escaped.py",
    }


def test_exact_content_bound_historical_record_passes(tmp_path: Path) -> None:
    content = f"# Decision\n\nThe {RETIRED_UPPER} name was current on this date.\n".encode()
    path = "docs/decisions/issue-1-preflight.md"
    _seed_repo(
        tmp_path,
        files={path: content},
        records=[_record(path, content)],
    )

    assert evaluate_identity_cutover(tmp_path) == []


def test_changed_historical_record_fails_closed(tmp_path: Path) -> None:
    original = f"Historical {RETIRED_UPPER} record.\n".encode()
    path = "docs/decisions/issue-1-preflight.md"
    _seed_repo(
        tmp_path,
        files={path: original},
        records=[_record(path, original)],
    )
    _write(tmp_path / path, original + b"Changed after classification.\n")

    failures = evaluate_identity_cutover(tmp_path)

    assert any(
        failure.rule_id == "identity-cutover-historical-content" and failure.path == path for failure in failures
    )


def test_historical_occurrence_count_is_verified(tmp_path: Path) -> None:
    content = f"{RETIRED_UPPER} and {RETIRED_LOWER}.runtime\n".encode()
    path = "docs/research/snapshot.md"
    _seed_repo(
        tmp_path,
        files={path: content},
        records=[_record(path, content, occurrences=1)],
    )

    failures = evaluate_identity_cutover(tmp_path)

    assert any(failure.rule_id == "identity-cutover-historical-count" and failure.path == path for failure in failures)


def test_unsafe_or_untracked_historical_path_fails_closed(tmp_path: Path) -> None:
    _seed_repo(
        tmp_path,
        files={"README.md": "RAES\n"},
        records=[
            _record(
                "../outside.md",
                f"Historical {RETIRED_UPPER} record.\n".encode(),
            )
        ],
    )

    failures = evaluate_identity_cutover(tmp_path)

    assert any(failure.rule_id == "identity-cutover-manifest-path" for failure in failures)


def test_identity_cutover_check_is_registered_in_canonical_policy_graph() -> None:
    noxfile_source = (REPO_ROOT / "noxfile.py").read_text(encoding="utf-8")
    assert '"tools/check_identity_cutover.py"' in noxfile_source
