"""Tests for the ``aces conformance backend`` Typer subcommand."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from raes_cli.main import app
from raes_conformance.conformance import fixtures_root
from typer.testing import CliRunner


def _contract_valid_dir(root: Path, contract_name: str) -> Path:
    """Resolve a contract's ``valid`` fixture directory under ``root``.

    Mirrors the runner's ``_fixture_contract_root`` glob so a seeded-violation
    test stays robust to where in the corpus a contract family lives instead of
    hard-coding its tree position.
    """

    matches = sorted(path for path in root.glob(f"**/{contract_name}") if path.is_dir())
    assert matches, f"no fixture directory for contract {contract_name!r} under {root}"
    return matches[0] / "valid"


def _seed_canonical_corpus(tmp_path: Path) -> Path:
    """Copy the published ``contracts/fixtures`` corpus into ``tmp_path``.

    Seeded-violation tests mutate the *copy* so the canonical corpus is never
    corrupted in place. The source root is resolved through the same
    ``corpus_family_root(FIXTURES)`` seam the runner uses, not a
    ``Path(__file__).parents[N]`` heuristic.
    """

    destination = tmp_path / "fixtures"
    shutil.copytree(fixtures_root(), destination)
    return destination


@pytest.mark.integration
def test_backend_conformance_cli_passes_for_provisioning_only_profile():
    runner = CliRunner()
    result = runner.invoke(app, ["conformance", "backend", "--profile", "provisioning-only"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["profile"] == "provisioning-only"
    assert payload["passed"] is True
    claim = payload["claim"]
    assert claim["taxonomy_id"] == "aces-behavioral-relations"
    assert claim["taxonomy_revision"] == "rev3"
    assert claim["relation_id"] == "bounded-probe-success"
    assert claim["quantifier_scope"] == "finite-cases"
    assert claim["evidence_scope"] == "finite"
    assert claim["observation_projection_ref"] == "backend-conformance-case-report"
    assert claim["evidence_refs"]
    assert any("equivalence" in nonclaim for nonclaim in claim["explicit_non_claims"])
    contract_names = {case["contract_name"] for case in payload["cases"]}
    assert contract_names == {
        "backend-manifest-v2",
        "operation-receipt-v1",
        "operation-status-v1",
        "runtime-snapshot-v1",
    }


@pytest.mark.integration
def test_backend_conformance_cli_passes_for_full_remote_control_plane_profile():
    runner = CliRunner()
    result = runner.invoke(app, ["conformance", "backend", "--profile", "full-remote-control-plane"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["passed"] is True
    contract_names = {case["contract_name"] for case in payload["cases"]}
    assert "participant-episode-state-envelope-v1" in contract_names
    assert "participant-episode-history-event-stream-v1" in contract_names
    assert "participant-behavior-history-event-stream-v1" in contract_names
    # CT-5 scope item 1: the realistic stub backend manifest passes end-to-end
    # against the canonical corpus under a profile that requires runtime contracts.
    stub_cases = [
        case for case in payload["cases"] if case["contract_name"] == "backend-manifest-v2" and case["name"] == "stub"
    ]
    assert stub_cases, "expected the stub backend-manifest-v2 fixture to be exercised"
    assert all(case["passed"] for case in stub_cases)


def test_backend_conformance_cli_exits_non_zero_when_fixtures_missing(tmp_path: Path):
    """Pointing the CLI at an empty fixtures root must surface the failure
    via exit code and the JSON report's ``conformance.fixture-missing``
    diagnostics — so CI gates wired up to ``aces conformance backend`` can
    catch the regression directly."""

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "conformance",
            "backend",
            "--profile",
            "provisioning-only",
            "--fixtures-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["passed"] is False
    assert payload["diagnostics"], "missing fixture root must populate top-level diagnostics"
    codes = {diag["code"] for diag in payload["diagnostics"]}
    assert codes == {"conformance.fixture-missing"}
    for diag in payload["diagnostics"]:
        assert diag["domain"] == "conformance"
        assert diag["severity"] == "error"
        assert "Missing valid fixture directory" in diag["message"]


def test_backend_conformance_cli_emits_structured_profile_load_diagnostics(tmp_path: Path):
    """Codex review (issue #66, finding 2 of cycle 2): the CLI must serialize
    diagnostic ``code``/``domain``/``address``/``severity`` so CI gates can
    distinguish ``conformance.profile-load-failed`` from
    ``conformance.fixture-missing`` without parsing prose."""

    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "conformance",
            "backend",
            "--profile",
            "provisioning-only",
            "--profiles-root",
            str(backend_dir),
        ],
    )

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    codes = {diag["code"] for diag in payload["diagnostics"]}
    assert codes == {"conformance.profile-load-failed"}


@pytest.mark.integration
def test_backend_conformance_cli_respects_profiles_root_override(tmp_path: Path):
    """The CLI must thread ``--profiles-root`` through to the runner so the
    published profile JSON is provably the authority end-to-end."""

    synthetic = {
        "schema_version": "backend-profile/v1",
        "profile": "provisioning-only",
        "required_contracts": ["backend-manifest-v2"],
    }
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / "provisioning-only.json").write_text(json.dumps(synthetic) + "\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "conformance",
            "backend",
            "--profile",
            "provisioning-only",
            "--profiles-root",
            str(backend_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    contract_names = {case["contract_name"] for case in payload["cases"]}
    assert contract_names == {"backend-manifest-v2"}


@pytest.mark.integration
def test_backend_conformance_cli_accepts_unknown_profile_id_from_corpus(tmp_path: Path):
    """ASR-502 + codex review (issue #66, finding 1 of cycle 3): the CLI must
    accept any profile id discoverable from the JSON corpus, not only the
    Python-enum members. Adding a new ``contracts/profiles/backend/<id>.json``
    must work without a coordinated enum edit."""

    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / "future-control-plane.json").write_text(
        json.dumps(
            {
                "schema_version": "backend-profile/v1",
                "profile": "future-control-plane",
                "required_contracts": ["backend-manifest-v2"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "conformance",
            "backend",
            "--profile",
            "future-control-plane",
            "--profiles-root",
            str(backend_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["profile"] == "future-control-plane"
    assert payload["passed"] is True


@pytest.mark.integration
def test_backend_conformance_cli_catches_seeded_manifest_violation(tmp_path: Path):
    """CT-5 scope item 2 (manifest surface): a real contract violation is caught.

    Copy the canonical fixture corpus to tmp, drop the required ``identity``
    field from the ``backend-manifest-v2`` ``stub`` fixture, then run the CLI
    against the mutated corpus. The runner must exit non-zero and report a
    ``conformance.schema-invalid`` diagnostic that names the offending contract
    — proving "backends can be checked against contracts" has a demonstrated
    catch, not just a missing-fixture failure. Assertions stay on stable
    diagnostic ``code``/``contract_name``/``address`` rather than exact Pydantic
    prose."""

    corpus = _seed_canonical_corpus(tmp_path)
    target = _contract_valid_dir(corpus, "backend-manifest-v2") / "stub.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert "identity" in payload, "fixture precondition: stub manifest declares identity"
    del payload["identity"]
    target.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "conformance",
            "backend",
            "--profile",
            "provisioning-only",
            "--fixtures-root",
            str(corpus),
        ],
    )

    assert result.exit_code == 1, result.output
    report = json.loads(result.output)
    assert report["passed"] is False
    stub_cases = [
        case for case in report["cases"] if case["contract_name"] == "backend-manifest-v2" and case["name"] == "stub"
    ]
    assert stub_cases, "expected a backend-manifest-v2 'stub' case in the report"
    stub_case = stub_cases[0]
    assert stub_case["passed"] is False
    schema_diags = [diag for diag in stub_case["diagnostics"] if diag["code"] == "conformance.schema-invalid"]
    assert schema_diags, f"expected a schema-invalid diagnostic, got {stub_case['diagnostics']}"
    assert any(diag["address"] == "backend-manifest-v2" for diag in schema_diags)
    assert all(diag["domain"] == "conformance" for diag in schema_diags)


@pytest.mark.integration
def test_backend_conformance_cli_catches_seeded_deep_runtime_violation(tmp_path: Path):
    """CT-5 scope items 2 + 3 (deep runtime surface): the catch reaches the
    runtime contracts a full profile requires, not just the manifest.

    Copy the canonical corpus to tmp, drop the required ``participant_address``
    field from a ``participant-episode-state-envelope-v1`` valid fixture (a
    contract required only by the deep ``full-remote-control-plane`` profile),
    and run the CLI against the mutated corpus. The runner must exit non-zero
    and surface a ``conformance.schema-invalid`` diagnostic naming the deep
    contract."""

    corpus = _seed_canonical_corpus(tmp_path)
    target = _contract_valid_dir(corpus, "participant-episode-state-envelope-v1") / "initialized.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert "participant_address" in payload, "fixture precondition: episode state declares participant_address"
    del payload["participant_address"]
    target.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "conformance",
            "backend",
            "--profile",
            "full-remote-control-plane",
            "--fixtures-root",
            str(corpus),
        ],
    )

    assert result.exit_code == 1, result.output
    report = json.loads(result.output)
    assert report["passed"] is False
    episode_cases = [
        case
        for case in report["cases"]
        if case["contract_name"] == "participant-episode-state-envelope-v1" and case["name"] == "initialized"
    ]
    assert episode_cases, "expected a participant-episode-state-envelope-v1 'initialized' case in the report"
    episode_case = episode_cases[0]
    assert episode_case["passed"] is False
    schema_diags = [diag for diag in episode_case["diagnostics"] if diag["code"] == "conformance.schema-invalid"]
    assert schema_diags, f"expected a schema-invalid diagnostic, got {episode_case['diagnostics']}"
    assert any(diag["address"] == "participant-episode-state-envelope-v1" for diag in schema_diags)
