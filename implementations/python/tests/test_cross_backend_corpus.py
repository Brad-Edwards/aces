"""Coverage for the cross-backend evidence corpus producer (issue #600).

Exercises the cross-backend invariant ledger builder against the authored reference
scenario: the n=2 pairing (libvirt reference backend + APTL) over one authored
scenario digest, the four ledger sections, the redaction/validation gates, the
optional APTL evidence-export translation (allowlisted portable fields only), and
build determinism (two fresh builds are byte-identical). The canonical published
corpus lives in Brad-Edwards/research, not in this repo; RAES ships the producer.
"""

from __future__ import annotations

import json
from pathlib import Path

from paths import EXAMPLES_DIR
from raes_operations.cross_backend_corpus import (
    CORPUS_SCHEMA,
    CrossBackendCorpusConfig,
    build_cross_backend_corpus,
    validate_cross_backend_corpus_artifact,
)
from raes_operations.run_artifacts import serialize_run_artifact

_REFERENCE_SCENARIO = EXAMPLES_DIR / "enterprise-participant-evidence-loop.sdl.yaml"


def _build(tmp_path: Path, config: CrossBackendCorpusConfig | None = None):
    return build_cross_backend_corpus(scenario_path=_REFERENCE_SCENARIO, project_dir=tmp_path, config=config)


def test_build_corpus_passes_and_validates(tmp_path: Path) -> None:
    report = _build(tmp_path)
    assert report.passed, report.render()
    assert report.artifact is not None
    artifact = report.artifact
    assert artifact["schema"] == CORPUS_SCHEMA
    assert validate_cross_backend_corpus_artifact(artifact) == []
    backend_ids = [run["backend_id"] for run in artifact["backend_runs"]]
    assert backend_ids == ["libvirt-reference", "aptl-docker"]
    assert len(set(backend_ids)) == 2


def test_ledger_has_four_sections_and_shared_scenario_digest(tmp_path: Path) -> None:
    artifact = _build(tmp_path).artifact
    assert artifact is not None
    ledger = artifact["invariant_ledger"]
    for section in (
        "preserved_invariants",
        "realization_differences",
        "unsupported_or_degraded_surfaces",
        "evidence_limitations",
    ):
        assert section in ledger
    digest_row = next(row for row in ledger["preserved_invariants"] if row["invariant"] == "authored_scenario_digest")
    assert digest_row["status"] == "preserved"
    per_backend = digest_row["per_backend"]
    assert per_backend["libvirt-reference"]["basis"] == "verified-in-artifact"
    assert per_backend["aptl-docker"]["basis"] == "external-summarized"
    assert per_backend["libvirt-reference"]["value"] == per_backend["aptl-docker"]["value"]


def test_compiled_addresses_shared_across_backends(tmp_path: Path) -> None:
    artifact = _build(tmp_path).artifact
    assert artifact is not None
    libvirt_run, aptl_run = artifact["backend_runs"]
    assert libvirt_run["compiled_address_sets"] == aptl_run["compiled_address_sets"]
    actions = libvirt_run["compiled_address_sets"]["action_contracts"]
    assert any("probe-customer-portal-login" in address for address in actions)


def test_realization_differences_record_substrate_and_provenance(tmp_path: Path) -> None:
    artifact = _build(tmp_path).artifact
    assert artifact is not None
    diffs = {row["dimension"]: row for row in artifact["invariant_ledger"]["realization_differences"]}
    assert diffs["substrate"]["libvirt-reference"] != diffs["substrate"]["aptl-docker"]
    assert diffs["evidence_provenance"]["libvirt-reference"] == "generated-in-repo"
    assert diffs["evidence_provenance"]["aptl-docker"] == "external-summarized"


def test_validator_requires_two_distinct_backends(tmp_path: Path) -> None:
    artifact = _build(tmp_path).artifact
    assert artifact is not None
    one_run = {**artifact, "backend_runs": artifact["backend_runs"][:1]}
    assert any("exactly two" in problem for problem in validate_cross_backend_corpus_artifact(one_run))
    duplicated = json.loads(json.dumps(artifact))
    duplicated["backend_runs"][1]["backend_id"] = duplicated["backend_runs"][0]["backend_id"]
    assert any("distinct backend_ids" in problem for problem in validate_cross_backend_corpus_artifact(duplicated))


def test_validator_requires_matching_scenario_digest(tmp_path: Path) -> None:
    artifact = _build(tmp_path).artifact
    assert artifact is not None
    tampered = json.loads(json.dumps(artifact))
    tampered["backend_runs"][1]["scenario"]["content_sha256"] = "sha256:deadbeef"
    problems = validate_cross_backend_corpus_artifact(tampered)
    assert any("does not match the authored scenario digest" in problem for problem in problems)


def test_validator_redaction_gate_flags_forbidden_content(tmp_path: Path) -> None:
    artifact = _build(tmp_path).artifact
    assert artifact is not None
    leaked = json.loads(json.dumps(artifact))
    leaked["backend_runs"][0]["limitations"].append("-----BEGIN RSA PRIVATE KEY-----")
    problems = validate_cross_backend_corpus_artifact(leaked)
    assert any("redaction violation" in problem for problem in problems)


def test_aptl_export_translation_drops_private_fields(tmp_path: Path) -> None:
    authored_digest = _build(tmp_path).artifact["authored_scenario"]["content_sha256"]
    export = {
        "scenario": {"content_sha256": authored_digest},
        "evidence_source_mode": "docker-live",
        "limitations": ["APTL export limitation"],
        # Private fields that must NOT leak into the corpus:
        "container_id": "a1b2c3d4e5f6",
        "raw_domain_xml": "<domain type='kvm'><devices></devices></domain>",
        "wazuh_rule_body": "password: hunter2",
    }
    export_path = tmp_path / "aptl-export.json"
    export_path.write_text(json.dumps(export), encoding="utf-8")

    report = _build(tmp_path, CrossBackendCorpusConfig(aptl_evidence_path=export_path))
    assert report.passed, report.render()
    artifact = report.artifact
    assert artifact is not None
    aptl_run = artifact["backend_runs"][1]
    assert aptl_run["evidence_provenance"] == "external-artifact-summarized"
    assert "APTL export limitation" in aptl_run["limitations"]
    # Directly assert the non-allowlisted private values never reach the artifact,
    # independent of the redaction gate: container_id matches no redaction pattern, so
    # a future widening of the allowlist would leak it silently without this check.
    serialized = json.dumps(artifact)
    for private_value in ("a1b2c3d4e5f6", "<domain type='kvm'>", "hunter2"):
        assert private_value not in serialized
    # The private fields never reach the corpus, so the redaction gate also stays clean.
    assert validate_cross_backend_corpus_artifact(artifact) == []


def test_aptl_export_digest_mismatch_fails(tmp_path: Path) -> None:
    export = {"scenario": {"content_sha256": "sha256:not-the-authored-scenario"}}
    export_path = tmp_path / "aptl-export-mismatch.json"
    export_path.write_text(json.dumps(export), encoding="utf-8")
    report = _build(tmp_path, CrossBackendCorpusConfig(aptl_evidence_path=export_path))
    assert not report.passed
    failed = {check.name for check in report.checks if not check.passed}
    assert "aptl_evidence_descriptor" in failed
    # A bad export must not leave a writable artifact (no silent summary overwrite).
    assert report.artifact is None


def test_aptl_export_address_divergence_fails(tmp_path: Path) -> None:
    authored_digest = _build(tmp_path).artifact["authored_scenario"]["content_sha256"]
    # Same authored scenario digest, but the exported compiled addresses diverge.
    export = {
        "scenario": {"content_sha256": authored_digest},
        "compiled_address_sets": {"action_contracts": ["participant.action-contract.something-else"]},
    }
    export_path = tmp_path / "aptl-export-addrs.json"
    export_path.write_text(json.dumps(export), encoding="utf-8")
    report = _build(tmp_path, CrossBackendCorpusConfig(aptl_evidence_path=export_path))
    assert not report.passed
    assert report.artifact is None
    diagnostics = " ".join(
        diag for check in report.checks if check.name == "aptl_evidence_descriptor" for diag in check.diagnostics
    )
    assert "compiled_address_sets[action_contracts]" in diagnostics


def test_aptl_export_unreadable_fails_without_writing(tmp_path: Path) -> None:
    export_path = tmp_path / "aptl-export-bad.json"
    export_path.write_text("{not valid json", encoding="utf-8")
    report = _build(tmp_path, CrossBackendCorpusConfig(aptl_evidence_path=export_path))
    assert not report.passed
    # Read/parse failure falls back to a summary internally, but the artifact must
    # NOT be materialized -- the operator supplied a real export that could not be read.
    assert report.artifact is None


def test_build_is_byte_stable(tmp_path: Path) -> None:
    # The corpus is regenerable and deterministic: two fresh builds are byte-identical
    # (only portable, timestamp-free fields cross from the libvirt run). The canonical
    # published corpus lives in Brad-Edwards/research, not committed in this repo.
    first = _build(tmp_path).artifact
    second = _build(tmp_path / "second").artifact
    assert first is not None and second is not None
    assert serialize_run_artifact(first) == serialize_run_artifact(second)
