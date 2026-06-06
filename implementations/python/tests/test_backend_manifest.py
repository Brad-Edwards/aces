"""Backend manifest declaration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aces_backend_protocols.capabilities import (
    PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS,
    PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_ROLE_SCOPE,
    BackendManifest,
    OrchestratorCapabilities,
    ParticipantRuntimeCapabilities,
    ProvisionerCapabilities,
    participant_runtime_capability_contract_gaps,
)
from aces_backend_protocols.manifest import backend_manifest_payload
from aces_backend_stubs.stubs import create_stub_manifest
from aces_contracts.contracts import BackendManifestV2Model
from aces_contracts.manifest_authority import BACKEND_SUPPORTED_CONTRACT_IDS
from aces_contracts.vocabulary import WorkflowFeature, WorkflowStatePredicateFeature
from pydantic import ValidationError

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"
V2_VALID_DIR = FIXTURES_ROOT / "backend-manifest" / "backend-manifest-v2" / "valid"
V2_INVALID_DIR = FIXTURES_ROOT / "backend-manifest" / "backend-manifest-v2" / "invalid"
EXPECTED_SUPPORTED_CONTRACT_VERSIONS_V2 = list(BACKEND_SUPPORTED_CONTRACT_IDS)


def test_backend_workflow_vocab_enum_values():
    assert {feature.value for feature in WorkflowFeature} == {
        "decision",
        "switch",
        "retry",
        "call",
        "parallel-barrier",
        "failure-transitions",
        "cancellation",
        "timeouts",
        "compensation",
    }
    assert {feature.value for feature in WorkflowStatePredicateFeature} == {
        "outcome-matching",
        "attempt-counts",
    }


def test_backend_manifest_rejects_hollow_defaults():
    with pytest.raises(ValueError):
        BackendManifest(
            name="stub",
            provisioner=ProvisionerCapabilities(
                name="stub-provisioner",
                supported_node_types=frozenset({"vm"}),
                supported_os_families=frozenset({"linux"}),
            ),
        )


def test_provisioner_capabilities_reject_hollow_declaration():
    with pytest.raises(ValueError):
        ProvisionerCapabilities(
            name="stub-provisioner",
            supported_node_types=frozenset(),
            supported_os_families=frozenset({"linux"}),
        )


def test_backend_manifest_v2_roundtrip_from_stub_manifest():
    payload = backend_manifest_payload(create_stub_manifest())
    model = BackendManifestV2Model.model_validate(payload)

    assert model.schema_version == "backend-manifest/v2"
    assert model.identity.name == "stub"
    assert model.identity.version
    assert model.compatibility.processors == ["aces-reference-processor"]
    assert model.compatibility.model_dump(mode="json") == {"processors": ["aces-reference-processor"]}
    assert model.supported_contract_versions == EXPECTED_SUPPORTED_CONTRACT_VERSIONS_V2
    assert model.capabilities.orchestrator is not None
    assert model.capabilities.orchestrator.supported_workflow_features == [
        WorkflowFeature.CALL,
        WorkflowFeature.CANCELLATION,
        WorkflowFeature.COMPENSATION,
        WorkflowFeature.DECISION,
        WorkflowFeature.FAILURE_TRANSITIONS,
        WorkflowFeature.PARALLEL_BARRIER,
        WorkflowFeature.RETRY,
        WorkflowFeature.SWITCH,
        WorkflowFeature.TIMEOUTS,
    ]
    assert model.realization_support[0].support_mode.value == "constrained"
    assert model.model_dump(mode="json") == payload


def test_backend_manifest_v2_declares_participant_capability_dimensions():
    """API-405: participant-runtime backends must declare the participant
    roles, behavior features, and interaction features they support."""

    payload = backend_manifest_payload(create_stub_manifest())
    participant_runtime = payload["capabilities"]["participant_runtime"]

    assert participant_runtime["supported_participant_roles"] == ["blue", "green", "red", "white"]
    assert participant_runtime["supported_behavior_features"] == [
        "action_contracts",
        "attribution_support",
        "behavior_history",
        "effects",
        "failure_classes",
        "observation_boundaries",
        "outcome_interpretation",
        "preconditions",
        "state_transitions",
        "temporal_contracts",
    ]
    assert participant_runtime["supported_interaction_features"] == [
        "contention",
        "coordination",
        "interference",
        "shared_state_change",
    ]

    model = BackendManifestV2Model.model_validate(payload)
    assert model.capabilities.participant_runtime is not None
    assert model.capabilities.participant_runtime.supported_participant_roles == [
        "blue",
        "green",
        "red",
        "white",
    ]


def test_backend_manifest_without_participant_runtime_declares_no_participant_runtime_surface():
    payload = backend_manifest_payload(create_stub_manifest(with_participant_runtime=False))

    assert payload["capabilities"]["participant_runtime"] is None
    model = BackendManifestV2Model.model_validate(payload)
    assert model.capabilities.participant_runtime is None


@pytest.mark.parametrize(
    "field_name",
    [
        "supported_participant_roles",
        "supported_behavior_features",
        "supported_interaction_features",
    ],
)
def test_backend_manifest_v2_rejects_participant_runtime_without_api_405_declarations(field_name: str):
    payload = json.loads((V2_VALID_DIR / "stub.json").read_text(encoding="utf-8"))
    payload["capabilities"]["participant_runtime"].pop(field_name, None)

    with pytest.raises(ValidationError, match=field_name):
        BackendManifestV2Model.model_validate(payload)


def test_backend_manifest_v2_rejects_duplicate_api_405_declarations():
    payload = json.loads((V2_VALID_DIR / "stub.json").read_text(encoding="utf-8"))
    payload["capabilities"]["participant_runtime"]["supported_participant_roles"].append("blue")

    with pytest.raises(ValidationError, match="duplicate"):
        BackendManifestV2Model.model_validate(payload)


def test_participant_runtime_capabilities_validate_api_405_vocabularies():
    capability = ParticipantRuntimeCapabilities(
        name="participant-runtime",
        supported_participant_roles=frozenset({"blue", "x-acme:observer"}),
        supported_behavior_features=frozenset({"action_contracts", "x-acme:custom-feature"}),
        supported_interaction_features=frozenset({"coordination", "x-acme:custom-interaction"}),
    )

    assert "x-acme:observer" in capability.supported_participant_roles
    assert "x-acme:custom-feature" in capability.supported_behavior_features
    assert "x-acme:custom-interaction" in capability.supported_interaction_features

    with pytest.raises(ValueError, match="participant-runtime-behavior-features"):
        ParticipantRuntimeCapabilities(
            name="participant-runtime",
            supported_participant_roles=frozenset({"blue"}),
            supported_behavior_features=frozenset({"custom_feature"}),
            supported_interaction_features=frozenset({"coordination"}),
        )


def test_participant_runtime_capability_evidence_covers_standard_vocabularies():
    catalog_path = FIXTURES_ROOT / "concept-authority" / "controlled-vocabularies-v1" / "valid" / "reference.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    terms_by_scope = {
        scope: set(definition["terms"])
        for definition in catalog["vocabularies"].values()
        for scope in definition.get("governed_scopes", ())
        if scope.startswith("capabilities.participant_runtime.")
    }

    assert (
        set(PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_ROLE_SCOPE])
        == terms_by_scope[PARTICIPANT_RUNTIME_ROLE_SCOPE]
    )
    assert (
        set(PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE])
        == terms_by_scope[PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE]
    )
    assert (
        set(PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE])
        == terms_by_scope[PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE]
    )


def test_participant_runtime_capability_claims_require_published_contract_evidence():
    manifest = create_stub_manifest()
    weak_manifest = BackendManifest(
        identity=manifest.identity,
        supported_contract_versions=manifest.supported_contract_versions
        - frozenset({"participant-behavior-history-event-stream-v1"}),
        compatibility=manifest.compatibility,
        realization_support=manifest.realization_support,
        concept_bindings=manifest.concept_bindings,
        constraints=manifest.constraints,
        capabilities=manifest.capabilities,
    )

    assert participant_runtime_capability_contract_gaps(manifest) == ()
    gaps = participant_runtime_capability_contract_gaps(weak_manifest)
    assert any("supported_behavior_features.action_contracts" in gap for gap in gaps)
    assert any("supported_interaction_features.coordination" in gap for gap in gaps)


def test_backend_manifest_v2_requires_manifest_sections():
    with pytest.raises(ValidationError):
        BackendManifestV2Model(
            identity={"name": "stub", "version": "0.0.1"},
            capabilities={
                "provisioner": {
                    "name": "stub-provisioner",
                }
            },
        )


def test_backend_manifest_runtime_rejects_unknown_supported_contract_versions():
    with pytest.raises(ValueError, match="supported_contract_versions"):
        BackendManifest(
            name="bad",
            version="0.0.1",
            supported_contract_versions=frozenset({"semantic-profile-v1"}),
            compatible_processors=frozenset({"aces-reference-processor"}),
            realization_support=create_stub_manifest().realization_support,
            concept_bindings=create_stub_manifest().concept_bindings,
            provisioner=ProvisionerCapabilities(
                name="stub-provisioner",
                supported_node_types=frozenset({"vm"}),
                supported_os_families=frozenset({"linux"}),
            ),
        )


def test_backend_manifest_v2_rejects_empty_compatibility():
    with pytest.raises(ValidationError) as excinfo:
        BackendManifestV2Model.model_validate(
            {
                "schema_version": "backend-manifest/v2",
                "identity": {"name": "stub", "version": "0.0.1"},
                "supported_contract_versions": ["backend-manifest-v2"],
                "compatibility": {},
                "realization_support": [
                    {
                        "domain": "runtime-realization",
                        "support_mode": "constrained",
                        "supported_constraint_kinds": ["node-type"],
                        "disclosure_kinds": ["runtime-snapshot-v1"],
                    }
                ],
                "concept_bindings": [
                    {"scope": "capabilities.provisioner.supported_node_types", "family": "assets"},
                    {"scope": "capabilities.provisioner.supported_os_families", "family": "assets"},
                ],
                "capabilities": {
                    "provisioner": {
                        "name": "stub-provisioner",
                        "supported_node_types": ["vm"],
                        "supported_os_families": ["linux"],
                    }
                },
            }
        )
    assert "compatibility.processors" in str(excinfo.value)


def test_backend_manifest_v2_rejects_non_processor_compatibility_surfaces():
    payload = json.loads((V2_VALID_DIR / "stub.json").read_text(encoding="utf-8"))
    payload["compatibility"] = {
        "processors": ["aces-reference-processor"],
        "backends": ["peer-backend"],
    }

    with pytest.raises(ValidationError):
        BackendManifestV2Model.model_validate(payload)

    payload["compatibility"] = {
        "processors": ["aces-reference-processor"],
        "participant_implementations": ["participant-impl"],
    }

    with pytest.raises(ValidationError):
        BackendManifestV2Model.model_validate(payload)


def test_backend_manifest_v2_rejects_hollow_realization_support():
    with pytest.raises(ValidationError) as excinfo:
        BackendManifestV2Model.model_validate(
            {
                "schema_version": "backend-manifest/v2",
                "identity": {"name": "stub", "version": "0.0.1"},
                "supported_contract_versions": ["backend-manifest-v2"],
                "compatibility": {"processors": ["aces-reference-processor"]},
                "realization_support": [
                    {
                        "domain": "runtime-realization",
                        "support_mode": "constrained",
                        "disclosure_kinds": ["runtime-snapshot-v1"],
                    }
                ],
                "concept_bindings": [
                    {"scope": "capabilities.provisioner.supported_node_types", "family": "assets"},
                    {"scope": "capabilities.provisioner.supported_os_families", "family": "assets"},
                ],
                "capabilities": {
                    "provisioner": {
                        "name": "stub-provisioner",
                        "supported_node_types": ["vm"],
                        "supported_os_families": ["linux"],
                    }
                },
            }
        )
    assert "supported_constraint_kinds" in str(excinfo.value)


def test_backend_manifest_v2_rejects_hollow_capability_blocks():
    with pytest.raises(ValidationError) as excinfo:
        BackendManifestV2Model.model_validate(
            {
                "schema_version": "backend-manifest/v2",
                "identity": {"name": "stub", "version": "0.0.1"},
                "supported_contract_versions": ["backend-manifest-v2"],
                "compatibility": {"processors": ["aces-reference-processor"]},
                "realization_support": [
                    {
                        "domain": "runtime-realization",
                        "support_mode": "constrained",
                        "supported_constraint_kinds": ["node-type"],
                        "disclosure_kinds": ["runtime-snapshot-v1"],
                    }
                ],
                "concept_bindings": [
                    {"scope": "capabilities.provisioner.supported_node_types", "family": "assets"},
                    {"scope": "capabilities.provisioner.supported_os_families", "family": "assets"},
                ],
                "capabilities": {
                    "provisioner": {
                        "name": "stub-provisioner",
                    }
                },
            }
        )
    assert "supported_node_types" in str(excinfo.value)


def test_reference_backend_v2_fixture_matches_emitted_manifest():
    payload = json.loads((V2_VALID_DIR / "stub.json").read_text(encoding="utf-8"))
    assert payload == backend_manifest_payload(create_stub_manifest())


def test_backend_manifest_valid_fixtures_pass_validation():
    for path in sorted(V2_VALID_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        model = BackendManifestV2Model.model_validate(payload)
        assert model.identity.name, f"Valid v2 fixture {path.name} should have a name"


def test_backend_manifest_invalid_fixtures_fail_validation():
    for path in sorted(V2_INVALID_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        with pytest.raises(ValidationError):
            BackendManifestV2Model.model_validate(payload)


def test_backend_manifest_v2_requires_concept_bindings():
    payload = json.loads((V2_VALID_DIR / "stub.json").read_text(encoding="utf-8"))
    del payload["concept_bindings"]
    with pytest.raises(ValidationError):
        BackendManifestV2Model.model_validate(payload)


def test_backend_manifest_v2_rejects_empty_concept_bindings():
    payload = json.loads((V2_VALID_DIR / "stub.json").read_text(encoding="utf-8"))
    payload["concept_bindings"] = []
    with pytest.raises(ValidationError):
        BackendManifestV2Model.model_validate(payload)


def test_backend_manifest_accepts_governed_extension_vocabulary_values():
    payload = json.loads((V2_VALID_DIR / "stub.json").read_text(encoding="utf-8"))
    payload["capabilities"]["provisioner"]["supported_node_types"].append("x-acme:bare-metal")
    payload["capabilities"]["orchestrator"]["supported_sections"].append("x-acme:custom-stage")

    model = BackendManifestV2Model.model_validate(payload)

    assert "x-acme:bare-metal" in model.capabilities.provisioner.supported_node_types
    assert "x-acme:custom-stage" in model.capabilities.orchestrator.supported_sections


def test_backend_manifest_rejects_unguarded_vocabulary_values():
    payload = json.loads((V2_VALID_DIR / "stub.json").read_text(encoding="utf-8"))
    payload["capabilities"]["provisioner"]["supported_node_types"].append("bare-metal")

    with pytest.raises(ValidationError, match="provisioner-node-types"):
        BackendManifestV2Model.model_validate(payload)


def test_runtime_capabilities_accept_governed_extension_vocabulary_values():
    provisioner = ProvisionerCapabilities(
        name="stub-provisioner",
        supported_node_types=frozenset({"vm", "x-acme:bare-metal"}),
        supported_os_families=frozenset({"linux"}),
    )
    orchestrator = OrchestratorCapabilities(
        name="stub-orchestrator",
        supported_sections=frozenset({"events", "scripts", "workflows", "x-acme:custom-stage"}),
        supports_workflows=True,
        supported_workflow_features=frozenset({WorkflowFeature.DECISION}),
    )

    assert "x-acme:bare-metal" in provisioner.supported_node_types
    assert "x-acme:custom-stage" in orchestrator.supported_sections


def test_runtime_capabilities_reject_unguarded_vocabulary_values():
    with pytest.raises(ValueError, match="provisioner-node-types"):
        ProvisionerCapabilities(
            name="stub-provisioner",
            supported_node_types=frozenset({"vm", "bare-metal"}),
            supported_os_families=frozenset({"linux"}),
        )


def test_backend_manifest_v2_rejects_duplicate_binding_scopes():
    payload = json.loads((V2_VALID_DIR / "stub.json").read_text(encoding="utf-8"))
    payload["concept_bindings"] = [
        {"scope": "capabilities.provisioner.supported_node_types", "family": "assets"},
        {"scope": "capabilities.provisioner.supported_node_types", "family": "identities"},
    ]
    with pytest.raises(ValidationError):
        BackendManifestV2Model.model_validate(payload)


def test_backend_manifest_v2_concept_bindings_roundtrip():
    payload = json.loads((V2_VALID_DIR / "stub.json").read_text(encoding="utf-8"))
    model = BackendManifestV2Model.model_validate(payload)
    assert len(model.concept_bindings) == 9
    assert model.concept_bindings[0].scope == "capabilities.provisioner.supported_node_types"
    assert model.concept_bindings[0].family == "assets"
