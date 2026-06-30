"""Coverage for the libvirt paper-proof evaluator-evidence artifact (issue #615).

Exercises the producer in both evidence-source modes against the paper scenario
(``paper-agent-loop.sdl.yaml``) and asserts every required evidence surface,
embedded-contract validity, the redaction gate, and the participant/evaluator
boundary. The native-live path is exercised with an injected fake libvirt
connection (no daemon), mirroring ``test_libvirt_backend_techvault_native``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aces_backend_libvirt.techvault_native import ProbeResult, TechVaultNativeLibvirtDriver
from aces_contracts.contracts import (
    BackendManifestV2Model,
    EvaluationHistoryEventModel,
    EvaluationResultStateModel,
    ExperimentRealizedFormDisclosureModel,
)
from aces_operations.libvirt_paper_evidence import (
    EVIDENCE_RUN_SCHEMA,
    LibvirtPaperEvidenceConfig,
    run_libvirt_paper_evidence,
    validate_libvirt_paper_evidence_artifact,
)
from aces_operations.run_artifacts import (
    atomic_write_json_artifact,
    is_valid_run_id_label,
    run_artifact_path,
)
from paths import EXAMPLES_DIR

_PAPER_SCENARIO = EXAMPLES_DIR / "paper-agent-loop.sdl.yaml"
_TECHVAULT_SCENARIO = EXAMPLES_DIR / "techvault-operational.sdl.yaml"

_REQUIRED_SECTIONS = (
    "scenario",
    "compiled_artifact",
    "backend",
    "realized_topology",
    "participant_action_proof",
    "terminal_observation",
    "defensive_evidence",
    "negative_boundary_checks",
    "evaluator_outcome",
    "realized_form_disclosures",
    "limitations",
    "non_claims",
    "redaction_provenance",
    "invariant_ledger_refs",
)


# --- fake native libvirt substrate (no daemon) ---------------------------------


class _NativeObject:
    def __init__(self, name: str = "") -> None:
        self._name = name

    def name(self) -> str:
        return self._name

    def create(self) -> None:  # pragma: no cover - structural stub
        pass

    def destroy(self) -> None:  # pragma: no cover - structural stub
        pass

    def undefine(self) -> None:  # pragma: no cover - structural stub
        pass


def _name_from_xml(xml: str) -> str:
    return xml[xml.index("<name>") + len("<name>") : xml.index("</name>")]


class _FakeConnection:
    def __init__(self) -> None:
        self.networks: dict[str, _NativeObject] = {}
        self.domains: dict[str, _NativeObject] = {}

    def networkDefineXML(self, xml: str):  # noqa: N802 - mirrors libvirt API
        obj = _NativeObject(_name_from_xml(xml))
        self.networks[obj.name()] = obj
        return obj

    def defineXML(self, xml: str):  # noqa: N802 - mirrors libvirt API
        obj = _NativeObject(_name_from_xml(xml))
        self.domains[obj.name()] = obj
        return obj

    def networkLookupByName(self, name: str):  # noqa: N802 - mirrors libvirt API
        return self.networks[name]

    def lookupByName(self, name: str):  # noqa: N802 - mirrors libvirt API
        return self.domains[name]

    def listAllDomains(self):  # noqa: N802 - mirrors libvirt API
        return list(self.domains.values())

    def listAllNetworks(self):  # noqa: N802 - mirrors libvirt API
        return list(self.networks.values())


class _InitramfsBuilder:
    def build(self, *, domain, target: Path):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"initramfs")
        return target


class _Probe:
    def ping(self, ip: str):
        return ProbeResult(True)

    def tcp(self, ip: str, port: int):
        return ProbeResult(True)


def _native_driver_factory(tmp_path: Path):
    kernel = tmp_path / "vmlinuz"
    kernel.write_bytes(b"kernel")

    def factory() -> TechVaultNativeLibvirtDriver:
        return TechVaultNativeLibvirtDriver(
            state_dir=tmp_path / "state",
            connection=_FakeConnection(),
            kernel_path=kernel,
            name_prefix="paper-test",
            initramfs_builder=_InitramfsBuilder(),
        )

    return factory


# --- deterministic mode --------------------------------------------------------


def test_deterministic_artifact_carries_all_evidence_surfaces(tmp_path):
    report = run_libvirt_paper_evidence(scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-det-1")

    assert report.passed, report.render()
    artifact = report.artifact
    assert artifact is not None
    assert artifact["schema"] == EVIDENCE_RUN_SCHEMA
    assert artifact["evidence_source_mode"] == "deterministic"
    for section in _REQUIRED_SECTIONS:
        assert section in artifact, f"missing evidence surface: {section}"
    assert validate_libvirt_paper_evidence_artifact(artifact) == []


def test_scenario_identity_is_portable_and_hashed(tmp_path):
    report = run_libvirt_paper_evidence(scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-det-2")
    scenario = report.artifact["scenario"]
    assert scenario["name"] == "paper-enterprise-participant-evidence-loop"
    assert scenario["content_sha256"].startswith("sha256:")
    # Portable ref, never the absolute host path.
    assert scenario["relative_path"] == "examples/scenarios/paper-agent-loop.sdl.yaml"
    assert not scenario["relative_path"].startswith("/")


def test_embedded_published_contracts_revalidate(tmp_path):
    artifact = run_libvirt_paper_evidence(
        scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-det-3"
    ).artifact

    # The backend manifest is carried as the canonical BackendManifestV2 payload —
    # the same contract the rest of the stack uses — not a hand-rolled summary.
    manifest = artifact["backend"]["manifest"]
    BackendManifestV2Model.model_validate(manifest)
    assert manifest["identity"]["name"] == "libvirt-qemu"
    assert manifest["capabilities"]["participant_runtime"] is not None
    capability_profile = artifact["backend"]["capability_profile"]
    assert capability_profile["participant_runtime_contract_gaps"] == []
    assert capability_profile["observation_contract_gaps"] == []
    EvaluationResultStateModel.model_validate(artifact["evaluator_outcome"]["result"])
    for event in artifact["evaluator_outcome"]["history"]:
        EvaluationHistoryEventModel.model_validate(event)
    assert artifact["realized_form_disclosures"], "expected realized-form disclosures"
    for disclosure in artifact["realized_form_disclosures"]:
        ExperimentRealizedFormDisclosureModel.model_validate(disclosure)


def test_participant_action_proof_is_from_libvirt_runtime(tmp_path):
    artifact = run_libvirt_paper_evidence(
        scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-det-4"
    ).artifact
    proof = artifact["participant_action_proof"]
    assert proof["lifecycle_clean"] is True
    assert proof["diagnostics"] == []
    assert proof["runtime"] == "libvirt-deterministic-participant-runtime"
    assert proof["admitted_action_addresses"], "expected at least one admitted action"
    # The participant surface exposes nothing of the internal/evaluator state.
    assert proof["participant_visible_refs"] == []
    assert proof["participant_disclosed_refs"] == []


def test_negative_boundary_withholds_internal_and_evaluator_surfaces(tmp_path):
    artifact = run_libvirt_paper_evidence(
        scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-det-5"
    ).artifact
    boundary = artifact["negative_boundary_checks"]
    refs = {check["ref"] for check in boundary["checks"]}
    assert "nodes.customer-db.services.postgres" in refs
    assert "nodes.wazuh-manager" in refs
    assert "content.evaluator-notes" in refs
    assert boundary["all_internal_surfaces_withheld"] is True
    assert all(not check["exposed_to_participant"] for check in boundary["checks"])


def test_defensive_evidence_is_evaluator_only_with_disclosure(tmp_path):
    artifact = run_libvirt_paper_evidence(
        scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-det-6"
    ).artifact
    defensive = artifact["defensive_evidence"]
    assert defensive["visibility"] == "evaluator-only"
    assert "loss_disclosure" in defensive
    assert "not upstream Wazuh" in defensive["loss_disclosure"]
    # Deterministic mode does not boot a live SOC stack.
    assert defensive["evidence_source"] == "structural-evaluator-channel"
    assert "soc_readback" not in defensive
    # captured_at is the shared run timestamp, not a freshly synthesized one.
    assert defensive["captured_at"] == artifact["recorded_at"]


def test_non_claims_are_carried_verbatim(tmp_path):
    artifact = run_libvirt_paper_evidence(
        scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-det-7"
    ).artifact
    joined = " ".join(artifact["non_claims"])
    assert "No Wazuh detection-quality claim" in joined
    assert "No byte-equivalence" in joined
    assert "aces#600" in joined


# --- redaction gate ------------------------------------------------------------


def test_artifact_contains_no_forbidden_secrets(tmp_path):
    artifact = run_libvirt_paper_evidence(
        scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-redact-1"
    ).artifact
    blob = json.dumps(artifact)
    assert "/home/" not in blob
    assert "<domain" not in blob
    assert "qemu-system" not in blob
    assert "BEGIN PRIVATE KEY" not in blob
    assert "/var/lib/libvirt" not in blob


def test_validator_flags_injected_host_path_leak(tmp_path):
    artifact = run_libvirt_paper_evidence(
        scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-redact-2"
    ).artifact
    artifact["realized_topology"]["leak"] = "/home/operator/.ssh/id_rsa"
    problems = validate_libvirt_paper_evidence_artifact(artifact)
    assert any("redaction violation" in p for p in problems)


def test_validator_flags_injected_domain_uuid(tmp_path):
    artifact = run_libvirt_paper_evidence(
        scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-redact-3"
    ).artifact
    artifact["realized_topology"]["leak_uuid"] = "550e8400-e29b-41d4-a716-446655440000"
    problems = validate_libvirt_paper_evidence_artifact(artifact)
    assert any("domain UUID" in p for p in problems)


def test_validator_flags_participant_boundary_exposure(tmp_path):
    artifact = run_libvirt_paper_evidence(
        scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-redact-4"
    ).artifact
    # Simulate a regression that leaks a withheld internal ref onto the participant view.
    artifact["participant_action_proof"]["participant_visible_refs"] = ["nodes.wazuh-manager"]
    problems = validate_libvirt_paper_evidence_artifact(artifact)
    assert any("boundary violation" in p for p in problems)


# --- native-live mode ----------------------------------------------------------


def test_native_live_paper_scenario_fails_realization_and_discloses_unrealized_content_plane(tmp_path):
    report = run_libvirt_paper_evidence(
        scenario_path=_PAPER_SCENARIO,
        project_dir=tmp_path,
        run_id="paper-live-1",
        config=LibvirtPaperEvidenceConfig(evidence_source_mode="native-live"),
        driver_factory=_native_driver_factory(tmp_path),
        probe=_Probe(),
    )
    # The libvirt backend cannot realize the paper scenario's content plane, so the
    # gating native-realization check fails: native-live must never claim success
    # without realizing. The artifact is still written and validates, recording the
    # attempt and the disclosed unrealized capabilities.
    assert not report.passed, report.render()
    artifact = report.artifact
    assert artifact is not None
    assert validate_libvirt_paper_evidence_artifact(artifact) == []
    provenance = artifact["backend"]["realization_provenance"]
    assert provenance["substrate_realized"] is False
    assert artifact["realized_topology"]["unrealized_capabilities"], "expected disclosed unrealized capabilities"


def test_native_live_realizes_substrate_for_provisionable_scenario(tmp_path):
    report = run_libvirt_paper_evidence(
        scenario_path=_TECHVAULT_SCENARIO,
        project_dir=tmp_path,
        run_id="tv-live-1",
        config=LibvirtPaperEvidenceConfig(evidence_source_mode="native-live"),
        driver_factory=_native_driver_factory(tmp_path),
        probe=_Probe(),
    )
    # This is the only native-live success path: real domain/network snapshot data
    # flows through artifact assembly, so it must clear the full check set and the
    # redaction/contract validator (the path most able to leak host-private data).
    assert report.passed, report.render()
    artifact = report.artifact
    assert validate_libvirt_paper_evidence_artifact(artifact) == []
    assert artifact["backend"]["realization_provenance"]["substrate_realized"] is True
    native_surface = artifact["realized_topology"]["native_surface"]
    assert len(native_surface["domains"]) == 30
    assert len(native_surface["networks"]) == 4
    # Native SOC readback is the translated native readback, explicitly disclosed.
    defensive = artifact["defensive_evidence"]
    assert defensive["evidence_source"] == "native-translated-readback"
    assert "soc_readback" in defensive
    assert defensive["captured_at"] == artifact["recorded_at"]


def test_native_live_without_realized_substrate_fails(tmp_path):
    report = run_libvirt_paper_evidence(
        scenario_path=_PAPER_SCENARIO,
        project_dir=tmp_path,
        run_id="paper-live-2",
        config=LibvirtPaperEvidenceConfig(evidence_source_mode="native-live"),
    )
    # The default driver factory has no daemon to connect to, so nothing is realized.
    # The gating realization check fails: native-live cannot pass without realizing.
    # The artifact still builds and records substrate_realized=False.
    assert not report.passed, report.render()
    assert report.artifact["backend"]["realization_provenance"]["substrate_realized"] is False


# --- artifact write + run-id ---------------------------------------------------


def test_artifact_written_to_stable_path(tmp_path):
    report = run_libvirt_paper_evidence(scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="paper-write-1")
    expected = tmp_path / "runs" / "paper-write-1" / "paper-evidence" / "libvirt-paper-evidence-run.json"
    assert report.artifact_path == str(expected)
    assert expected.is_file()
    written = json.loads(expected.read_text())
    assert written["schema"] == EVIDENCE_RUN_SCHEMA


def test_unsafe_run_id_is_rejected_without_write(tmp_path):
    report = run_libvirt_paper_evidence(scenario_path=_PAPER_SCENARIO, project_dir=tmp_path, run_id="../escape")
    assert not report.passed
    assert report.artifact_path is None
    assert not (tmp_path / "runs").exists()


# --- run_artifacts shared helper ----------------------------------------------


def test_run_id_label_validation():
    assert is_valid_run_id_label("paper-evidence_2026.06.29")
    assert not is_valid_run_id_label("../escape")
    assert not is_valid_run_id_label(".hidden")
    assert not is_valid_run_id_label("with/slash")
    assert not is_valid_run_id_label("")


def test_run_artifact_path_rejects_unsafe_label(tmp_path):
    with pytest.raises(ValueError, match="safe filesystem label"):
        run_artifact_path(tmp_path, "../escape", "paper-evidence", "run.json")


def test_atomic_write_json_artifact_round_trips(tmp_path):
    target = tmp_path / "runs" / "r1" / "sub" / "artifact.json"
    atomic_write_json_artifact(target, {"b": 2, "a": 1})
    text = target.read_text()
    # Canonical serialization: sorted keys, indent 2, trailing newline, no temp files left.
    assert text == '{\n  "a": 1,\n  "b": 2\n}\n'
    assert list(target.parent.glob("*.tmp")) == []
