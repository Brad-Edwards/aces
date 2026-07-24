"""Authored historical-state and semantic-address contracts (#859 / DSL-436)."""

from __future__ import annotations

import hashlib
import textwrap
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from aces_backend_protocols.capabilities import BackendManifest, HistoricalStateCapabilities
from aces_backend_protocols.manifest import backend_manifest_from_v2_model, backend_manifest_payload
from aces_backend_stubs.stubs import create_stub_manifest
from aces_contracts.contracts import BackendManifestV2Model, schema_bundle
from aces_contracts.contracts.historical_state import HistoricalSemanticAddressContextModel
from aces_contracts.historical_addressing import (
    HISTORICAL_BASELINE_DIGEST_DOMAIN,
    canonical_historical_address_bytes,
    canonical_historical_baseline_bytes,
    derive_historical_baseline_digest,
    derive_historical_semantic_address,
    derive_historical_semantic_addresses,
)
from aces_processor.compiler import compile_runtime_model
from aces_processor.planner import plan
from aces_sdl import (
    SDLParseError,
    SDLValidationError,
    instantiate_scenario,
    parse_sdl,
    parse_sdl_file,
)
from jsonschema import Draft202012Validator

_INSTANTIATION_PROVENANCE = {
    "authored_digest": {
        "profile": "aces-sdl-semantic/v1",
        "algorithm": "sha256",
        "value": "sha256:" + "a" * 64,
    }
}


def _valid_payload() -> dict[str, object]:
    return {
        "name": "historical-lab",
        "nodes": {
            "archive": {
                "type": "vm",
                "os": "linux",
                "services": [{"name": "records", "port": 8443}],
            }
        },
        "entities": {
            "operations": {
                "name": "Operations",
                "role": "blue",
            }
        },
        "content": {
            "message-metadata": {
                "type": "dataset",
                "target": "archive",
                "items": [
                    {
                        "name": "message-001",
                        "display_name": "Quarterly review",
                        "description": "Bounded inert metadata for the historical message.",
                    }
                ],
            }
        },
        "persistent_volumes": {
            "tenant-records": {
                "lifecycle": "ephemeral",
                "access_mode": "read_write_once",
                "consumers": [
                    {
                        "node": "archive",
                        "mount_destination": "/var/lib/records",
                        "access_mode": "read_write",
                    }
                ],
            }
        },
        "deployment_tenants": {"range-a": {}},
        "deployment_cells": {
            "range-a-cell": {
                "tenant_ref": "range-a",
                "node_refs": ["archive"],
                "cross_tenant_isolation": "default_deny",
            }
        },
        "evidence_requirements": {
            "native-readback": {
                "source_class": "participant_observation",
                "scope": "participant-visible historical object readback",
                "boundary_kind": "historical_readback",
                "channel": "api_response",
                "sensitivity": "plain",
                "redaction": "redact_secrets",
                "integrity": "checksum",
                "retention": "run_lifetime",
                "loss_disclosure": "required",
            }
        },
        "propositions": {
            "message-visible": {
                "description": "The historical message is visible through the participant projection.",
                "subjects": ["historical_baselines.enterprise.objects.message-001"],
                "basis": "observed_state",
                "predicate": {
                    "kind": "presence",
                    "property": "historical.object",
                    "semantic_ref": "urn:aces:historical:object",
                },
                "evidence_requirements": ["native-readback"],
            },
            "case-visible": {
                "description": "The historical case is visible through the participant projection.",
                "subjects": ["historical_baselines.enterprise.objects.case-001"],
                "basis": "observed_state",
                "predicate": {
                    "kind": "presence",
                    "property": "historical.object",
                    "semantic_ref": "urn:aces:historical:object",
                },
                "evidence_requirements": ["native-readback"],
            },
        },
        "assertions": {
            "message-readback": {
                "proposition": "message-visible",
                "role": "postcondition",
            },
            "case-readback": {
                "proposition": "case-visible",
                "role": "postcondition",
            },
        },
        "observation_boundaries": {
            "participant-history": {
                "projection_basis": "Participant-visible native history projection revision 1.",
                "observable_refs": [
                    "historical_baselines.enterprise.objects.message-001",
                    "historical_baselines.enterprise.objects.case-001",
                ],
                "redaction_policy": "Operator-only and secret-bearing state remains hidden.",
                "latency_profile": "Readback occurs after materialization.",
            }
        },
        "relationships": {
            "records-reset-owner": {
                "type": "uses_shared_service",
                "source": "range-a",
                "target": "nodes.archive.services.records",
                "shared_service": {
                    "tenant_isolation": "none",
                    "workload_authentication": "workload_identity",
                    "mutable_state_refs": ["tenant-records"],
                    "mutable_state_owner": "consumer_tenant",
                    "reset_generation_owner": "consumer_tenant",
                },
            },
            "message-case": {
                "type": "historical_object_link",
                "source": "historical_baselines.enterprise.objects.message-001",
                "target": "historical_baselines.enterprise.objects.case-001",
                "historical_object_link": {"kind": "associated_with"},
            },
        },
        "historical_baselines": {
            "enterprise": {
                "version": "1.0.0",
                "address_profile": "aces-historical-semantic-address/v1",
                "history_time_profile": "logical-order/v1",
                "range_instance_id": "range-instance-001",
                "deployment_tenant_ref": "range-a",
                "deployment_cell_ref": "range-a-cell",
                "reset_generation_id": "generation-001",
                "reset_owner_relationship_ref": "records-reset-owner",
                "actors": {
                    "records-owner": {
                        "authority": "entity",
                        "authority_ref": "operations",
                        "role": "owner",
                    }
                },
                "objects": {
                    "message-001": {
                        "kind": "message",
                        "writer_actor_ref": "records-owner",
                        "title": "Quarterly review",
                        "content_ref": "message-metadata",
                    },
                    "case-001": {
                        "kind": "case",
                        "writer_actor_ref": "records-owner",
                        "title": "Review follow-up",
                    },
                },
                "events": {
                    "create-message": {
                        "order": 0,
                        "operation": "create",
                        "actor_ref": "records-owner",
                        "object_refs": ["message-001"],
                    },
                    "create-case": {
                        "order": 1,
                        "operation": "create",
                        "actor_ref": "records-owner",
                        "object_refs": ["case-001"],
                        "predecessor_refs": ["create-message"],
                        "cause_refs": ["create-message"],
                    },
                    "link-message-case": {
                        "order": 2,
                        "operation": "link",
                        "actor_ref": "records-owner",
                        "object_refs": ["message-001", "case-001"],
                        "predecessor_refs": ["create-case"],
                        "cause_refs": ["create-case"],
                        "relationship_refs": ["message-case"],
                    },
                },
                "relationship_refs": ["message-case"],
                "materialization_bindings": {
                    "message-native": {
                        "object_refs": ["message-001"],
                        "target_service_ref": "nodes.archive.services.records",
                        "interface_profile": "native-message/v1",
                        "deployment_tenant_ref": "range-a",
                        "deployment_cell_ref": "range-a-cell",
                        "reset_owner_relationship_ref": "records-reset-owner",
                        "readback_requirement_refs": ["message-readback"],
                    },
                    "case-native": {
                        "object_refs": ["case-001"],
                        "target_service_ref": "nodes.archive.services.records",
                        "interface_profile": "native-case/v1",
                        "deployment_tenant_ref": "range-a",
                        "deployment_cell_ref": "range-a-cell",
                        "reset_owner_relationship_ref": "records-reset-owner",
                        "ordering_dependencies": ["message-native"],
                        "readback_requirement_refs": ["case-readback"],
                    },
                },
                "readback_requirements": {
                    "message-readback": {
                        "object_ref": "message-001",
                        "assertion_refs": ["message-readback"],
                        "observation_boundary_ref": "participant-history",
                        "projection_profile": "participant-visible-object/v1",
                        "observation_point": "after_materialization",
                    },
                    "case-readback": {
                        "object_ref": "case-001",
                        "assertion_refs": ["case-readback"],
                        "observation_boundary_ref": "participant-history",
                        "projection_profile": "participant-visible-object-and-links/v1",
                        "observation_point": "after_history",
                    },
                },
            }
        },
    }


def _parse(payload: dict[str, object]):
    return parse_sdl(yaml.safe_dump(payload, sort_keys=False))


def _baseline(payload: dict[str, object]) -> dict[str, object]:
    return payload["historical_baselines"]["enterprise"]  # type: ignore[index,return-value]


def test_complete_historical_baseline_is_admitted() -> None:
    scenario = _parse(_valid_payload())
    baseline = scenario.historical_baselines["enterprise"]

    assert baseline.objects["message-001"].kind.value == "message"
    assert baseline.events["link-message-case"].order == 2
    assert scenario.relationships["message-case"].historical_object_link.kind.value == "associated_with"


@pytest.mark.parametrize("field", ["native_id", "provider_options", "raw_body", "script"])
def test_unrepresentable_product_and_corpus_fields_fail_closed(field: str) -> None:
    payload = _valid_payload()
    _baseline(payload)["objects"]["message-001"][field] = "forbidden"  # type: ignore[index]

    with pytest.raises(SDLParseError):
        _parse(payload)


@pytest.mark.parametrize(
    ("authority", "authority_ref"),
    [
        ("entity", "missing"),
        ("agent", "operations"),
        ("account", "operations"),
        ("service", "archive"),
    ],
)
def test_actor_bindings_require_matching_incumbent_authority(authority: str, authority_ref: str) -> None:
    payload = _valid_payload()
    actor = _baseline(payload)["actors"]["records-owner"]  # type: ignore[index]
    actor["authority"] = authority
    actor["authority_ref"] = authority_ref

    with pytest.raises(SDLValidationError, match="actor.*authority_ref"):
        _parse(payload)


def test_event_references_and_logical_order_fail_closed() -> None:
    payload = _valid_payload()
    event = _baseline(payload)["events"]["create-case"]  # type: ignore[index]
    event["cause_refs"] = ["missing"]
    with pytest.raises(SDLValidationError, match="cause_refs does not resolve"):
        _parse(payload)

    payload = _valid_payload()
    _baseline(payload)["events"]["create-case"]["order"] = 0  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="order coordinates must be unique"):
        _parse(payload)

    payload = _valid_payload()
    event = _baseline(payload)["events"]["create-case"]  # type: ignore[index]
    event["cause_refs"] = ["link-message-case"]
    with pytest.raises(SDLValidationError, match="cause_refs must precede"):
        _parse(payload)


@pytest.mark.parametrize("field", ["predecessor_refs", "cause_refs"])
def test_event_graph_cycles_are_rejected(field: str) -> None:
    payload = _valid_payload()
    _baseline(payload)["events"]["create-message"][field] = ["create-case"]  # type: ignore[index]

    with pytest.raises(SDLValidationError, match="graph contains a cycle"):
        _parse(payload)


def test_object_lifecycle_rejects_use_before_create_and_post_delete_use() -> None:
    payload = _valid_payload()
    _baseline(payload)["events"]["create-message"]["operation"] = "update"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="before creation"):
        _parse(payload)

    payload = _valid_payload()
    events = _baseline(payload)["events"]  # type: ignore[index]
    events["delete-message"] = {
        "order": 2,
        "operation": "delete",
        "actor_ref": "records-owner",
        "object_refs": ["message-001"],
    }
    events["link-message-case"]["order"] = 3
    with pytest.raises(SDLValidationError, match="after deletion"):
        _parse(payload)


def test_object_lifecycle_requires_one_create_and_one_writer() -> None:
    payload = _valid_payload()
    del _baseline(payload)["events"]["create-case"]  # type: ignore[index]
    _baseline(payload)["events"]["link-message-case"]["predecessor_refs"] = ["create-message"]  # type: ignore[index]
    _baseline(payload)["events"]["link-message-case"]["cause_refs"] = ["create-message"]  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="exactly one create event"):
        _parse(payload)

    payload = _valid_payload()
    actors = _baseline(payload)["actors"]  # type: ignore[index]
    actors["other-writer"] = {
        "authority": "entity",
        "authority_ref": "operations",
        "role": "author",
    }
    _baseline(payload)["events"]["create-case"]["actor_ref"] = "other-writer"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="single writer"):
        _parse(payload)


def test_historical_object_links_require_typed_local_endpoints_and_no_properties() -> None:
    payload = _valid_payload()
    payload["relationships"]["message-case"]["target"] = "archive"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="endpoints must be distinct objects"):
        _parse(payload)

    payload = _valid_payload()
    payload["relationships"]["message-case"]["type"] = "depends_on"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="historical_object_link detail"):
        _parse(payload)

    payload = _valid_payload()
    payload["relationships"]["message-case"]["properties"] = {"native_id": "42"}  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="free-form properties"):
        _parse(payload)


def test_tenant_cell_reset_owner_and_target_must_agree() -> None:
    payload = _valid_payload()
    binding = _baseline(payload)["materialization_bindings"]["message-native"]  # type: ignore[index]
    binding["deployment_tenant_ref"] = "missing"
    with pytest.raises(SDLValidationError, match="tenant, cell, and reset owner must agree"):
        _parse(payload)

    payload = _valid_payload()
    payload["nodes"]["archive"]["services"].append({"name": "other", "port": 9443})  # type: ignore[index]
    binding = _baseline(payload)["materialization_bindings"]["message-native"]  # type: ignore[index]
    binding["target_service_ref"] = "nodes.archive.services.other"
    with pytest.raises(SDLValidationError, match="reset-owner relationship"):
        _parse(payload)

    payload = _valid_payload()
    reset = payload["relationships"]["records-reset-owner"]["shared_service"]  # type: ignore[index]
    reset["reset_generation_owner"] = "none"
    with pytest.raises(
        SDLValidationError,
        match="Historical baseline 'enterprise' reset owner must be an agreeing ADR-087 shared-service binding",
    ):
        _parse(payload)


def test_materialization_interface_single_authority_and_dependencies_are_validated() -> None:
    payload = _valid_payload()
    _baseline(payload)["materialization_bindings"]["message-native"]["interface_profile"] = "native-case/v1"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="does not support object"):
        _parse(payload)

    payload = _valid_payload()
    _baseline(payload)["materialization_bindings"]["case-native"]["object_refs"].append("message-001")  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="exactly one materialization binding"):
        _parse(payload)

    payload = _valid_payload()
    _baseline(payload)["materialization_bindings"]["message-native"]["ordering_dependencies"] = ["case-native"]  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="dependency graph contains a cycle"):
        _parse(payload)


def test_backend_manifest_declares_exact_historical_materialization_support() -> None:
    base = create_stub_manifest()
    capability = HistoricalStateCapabilities(
        supported_interface_profiles=frozenset({"native-message/v1", "native-case/v1"}),
        supported_object_kinds=frozenset({"message", "case"}),
    )
    manifest = BackendManifest(
        identity=base.identity,
        supported_contract_versions=base.supported_contract_versions,
        compatibility=base.compatibility,
        realization_support=base.realization_support,
        concept_bindings=base.concept_bindings,
        constraints=base.constraints,
        capabilities=replace(base.capabilities, historical_state=capability),
    )

    payload = backend_manifest_payload(manifest)
    model = BackendManifestV2Model.model_validate(payload)
    roundtrip = backend_manifest_from_v2_model(model)

    assert model.capabilities.historical_state is not None
    assert model.capabilities.historical_state.supported_interface_profiles == [
        "native-case/v1",
        "native-message/v1",
    ]
    assert roundtrip.historical_state == capability

    with pytest.raises(ValueError, match="unknown profiles"):
        HistoricalStateCapabilities(
            supported_interface_profiles=frozenset({"vendor-message/v1"}),
            supported_object_kinds=frozenset({"message"}),
        )
    with pytest.raises(ValueError, match="same exact support pairs"):
        HistoricalStateCapabilities(
            supported_interface_profiles=frozenset({"native-message/v1"}),
            supported_object_kinds=frozenset({"case"}),
        )


def _historical_manifest(
    *,
    profiles: frozenset[str] | None,
    kinds: frozenset[str] | None,
    exact_support: bool = True,
) -> BackendManifest:
    base = create_stub_manifest()
    capability = (
        None
        if profiles is None or kinds is None
        else HistoricalStateCapabilities(
            supported_interface_profiles=profiles,
            supported_object_kinds=kinds,
        )
    )
    return BackendManifest(
        identity=base.identity,
        supported_contract_versions=base.supported_contract_versions,
        compatibility=base.compatibility,
        realization_support=tuple(
            replace(
                declaration,
                supported_exact_requirement_kinds=frozenset(),
            )
            if not exact_support
            else declaration
            for declaration in base.realization_support
        ),
        concept_bindings=base.concept_bindings,
        constraints=base.constraints,
        capabilities=replace(base.capabilities, historical_state=capability),
    )


def test_planner_rejects_absent_and_partial_historical_capability() -> None:
    model = compile_runtime_model(_parse(_valid_payload()))

    absent = plan(
        model,
        _historical_manifest(profiles=None, kinds=None),
    )
    assert "historical-state.capability-missing" in {diagnostic.code for diagnostic in absent.diagnostics}

    partial = plan(
        model,
        _historical_manifest(
            profiles=frozenset({"native-message/v1"}),
            kinds=frozenset({"message"}),
        ),
    )
    assert {
        "historical-state.interface-unsupported",
        "historical-state.object-kind-unsupported",
    } <= {diagnostic.code for diagnostic in partial.diagnostics}


def test_planner_requires_sem_218_exact_support_for_historical_bindings() -> None:
    model = compile_runtime_model(_parse(_valid_payload()))
    historical_requirements = tuple(
        requirement
        for requirement in model.realization_requirements
        if requirement.field_path.startswith("historical_baselines.")
    )
    assert len(historical_requirements) == 8
    assert {requirement.requirement_kind for requirement in historical_requirements} == {
        "historical-materialization-interface",
        "historical-materialization-object-kind:message",
        "historical-materialization-object-kind:case",
        "historical-materialization-ordering",
        "historical-materialization-readback",
    }

    result = plan(
        model,
        _historical_manifest(
            profiles=frozenset({"native-message/v1", "native-case/v1"}),
            kinds=frozenset({"message", "case"}),
            exact_support=False,
        ),
    )
    exact_diagnostics = [
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == "realization.unsupported-exact-requirement"
        and "historical_baselines." in diagnostic.message
    ]
    assert len(exact_diagnostics) == 8


def test_readback_requires_exact_observed_assertion_boundary_and_coverage() -> None:
    payload = _valid_payload()
    payload["propositions"]["message-visible"]["basis"] = "declared_state"  # type: ignore[index]
    payload["propositions"]["message-visible"]["evidence_requirements"] = []  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="observed-state invariant or postcondition"):
        _parse(payload)

    payload = _valid_payload()
    _baseline(payload)["readback_requirements"]["message-readback"]["observation_boundary_ref"] = "missing"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="observation boundary does not resolve"):
        _parse(payload)

    payload = _valid_payload()
    payload["observation_boundaries"]["participant-history"]["observable_refs"].remove(  # type: ignore[index]
        "historical_baselines.enterprise.objects.message-001"
    )
    with pytest.raises(SDLValidationError, match="participant-visible through its observation boundary"):
        _parse(payload)

    payload = _valid_payload()
    _baseline(payload)["materialization_bindings"]["message-native"]["readback_requirement_refs"] = [  # type: ignore[index]
        "case-readback"
    ]
    with pytest.raises(SDLValidationError, match="readback for every bound object"):
        _parse(payload)


@pytest.mark.parametrize(
    "secret_uri",
    [
        "https://user:pass@example.test/history",
        "ftp://user:pass@example.test/history",
        "s3://access:secret@archive/history",
    ],
)
def test_unsafe_metadata_inline_corpus_and_secret_uri_are_rejected(
    secret_uri: str,
) -> None:
    payload = _valid_payload()
    _baseline(payload)["objects"]["message-001"]["summary"] = "-----BEGIN PRIVATE KEY-----"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="unsafe corpus material"):
        _parse(payload)

    payload = _valid_payload()
    payload["content"]["message-metadata"]["text"] = "raw historical corpus"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="inline historical corpus bodies"):
        _parse(payload)

    payload = _valid_payload()
    _baseline(payload)["objects"]["message-001"]["summary"] = secret_uri  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="unsafe corpus material"):
        _parse(payload)


def test_historical_content_must_match_tenant_target_and_sensitivity() -> None:
    payload = _valid_payload()
    payload["nodes"]["other"] = {"type": "vm", "os": "linux"}
    payload["deployment_tenants"]["range-b"] = {}  # type: ignore[index]
    payload["deployment_cells"]["range-b-cell"] = {  # type: ignore[index]
        "tenant_ref": "range-b",
        "node_refs": ["other"],
        "cross_tenant_isolation": "default_deny",
    }
    payload["content"]["message-metadata"]["target"] = "other"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="content target must belong to the baseline deployment cell"):
        _parse(payload)

    payload = _valid_payload()
    payload["nodes"]["staging"] = {"type": "vm", "os": "linux"}
    payload["deployment_cells"]["range-a-cell"]["node_refs"].append("staging")  # type: ignore[index]
    payload["content"]["message-metadata"]["target"] = "staging"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="content target must agree with materialization binding"):
        _parse(payload)

    payload = _valid_payload()
    payload["content"]["message-metadata"]["sensitive"] = True  # type: ignore[index]
    _baseline(payload)["objects"]["message-001"]["sensitivity"] = "public"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="must not downgrade sensitive content"):
        _parse(payload)


def test_module_composition_namespaces_baseline_and_external_refs(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["module"] = {
        "id": "aces/history",
        "version": "1.0.0",
        "exports": {
            section: list(payload[section])  # type: ignore[arg-type]
            for section in (
                "nodes",
                "entities",
                "content",
                "persistent_volumes",
                "deployment_tenants",
                "deployment_cells",
                "evidence_requirements",
                "propositions",
                "assertions",
                "observation_boundaries",
                "relationships",
                "historical_baselines",
            )
        },
    }
    module = tmp_path / "history.yaml"
    module.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    root = tmp_path / "root.yaml"
    root.write_text(
        textwrap.dedent(
            """
            name: root
            imports:
              - path: history.yaml
                namespace: archive
                version: 1.0.0
            """
        ),
        encoding="utf-8",
    )

    scenario = parse_sdl_file(root)
    baseline = scenario.historical_baselines["archive.enterprise"]

    assert baseline.deployment_tenant_ref == "archive.range-a"
    assert baseline.actors["records-owner"].authority_ref == "archive.operations"
    assert baseline.objects["message-001"].content_ref == "archive.message-metadata"
    assert baseline.materialization_bindings["message-native"].target_service_ref == (
        "nodes.archive.archive.services.records"
    )
    assert scenario.relationships["archive.message-case"].source == (
        "historical_baselines.archive.enterprise.objects.message-001"
    )
    assert scenario.propositions["archive.message-visible"].subjects == [
        "historical_baselines.archive.enterprise.objects.message-001"
    ]


def test_module_composition_uses_actor_authority_section_for_same_name(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    payload["accounts"] = {
        "operations": {
            "username": "operations",
            "node": "archive",
        }
    }
    actor = _baseline(payload)["actors"]["records-owner"]  # type: ignore[index]
    actor["authority"] = "account"
    actor["authority_ref"] = "operations"
    exported_sections = (
        "nodes",
        "content",
        "persistent_volumes",
        "accounts",
        "deployment_tenants",
        "deployment_cells",
        "evidence_requirements",
        "propositions",
        "assertions",
        "observation_boundaries",
        "relationships",
        "historical_baselines",
    )
    payload["module"] = {
        "id": "aces/history-account-authority",
        "version": "1.0.0",
        "exports": {
            section: list(payload[section])  # type: ignore[arg-type]
            for section in exported_sections
        },
    }
    module = tmp_path / "history.yaml"
    module.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    root = tmp_path / "root.yaml"
    root.write_text(
        textwrap.dedent(
            """
            name: root
            imports:
              - path: history.yaml
                namespace: archive
                version: 1.0.0
            """
        ),
        encoding="utf-8",
    )

    scenario = parse_sdl_file(root)

    assert (
        scenario.historical_baselines["archive.enterprise"].actors["records-owner"].authority_ref
        == "archive.operations"
    )


def test_variables_instantiate_address_context_and_revalidate() -> None:
    payload = _valid_payload()
    payload["variables"] = {
        "baseline_version": {"type": "string", "default": "1.2.3"},
        "range_instance": {"type": "string", "default": "range-instance-002"},
        "reset_generation": {"type": "string", "default": "generation-009"},
    }
    baseline = _baseline(payload)
    baseline["version"] = "${baseline_version}"
    baseline["range_instance_id"] = "${range_instance}"
    baseline["reset_generation_id"] = "${reset_generation}"

    model = compile_runtime_model(_parse(payload))
    address = model.historical_object_addresses["historical_baselines.enterprise.objects.message-001"]

    assert address.context.baseline_version == "1.2.3"
    assert address.context.range_instance_id == "range-instance-002"
    assert address.context.reset_generation_id == "generation-009"


@pytest.mark.parametrize(
    ("path", "default", "explicit", "is_list"),
    [
        (
            ("historical_baselines", "enterprise", "relationship_refs"),
            "message-case",
            "relationships.message-case",
            True,
        ),
        (
            ("relationships", "message-case", "source"),
            "historical_baselines.enterprise.objects.message-001",
            "historical_baselines.enterprise.objects.message-001",
            False,
        ),
        (
            (
                "historical_baselines",
                "enterprise",
                "events",
                "create-message",
                "object_refs",
            ),
            "message-001",
            "objects.message-001",
            True,
        ),
        (
            (
                "historical_baselines",
                "enterprise",
                "events",
                "link-message-case",
                "relationship_refs",
            ),
            "message-case",
            "relationships.message-case",
            True,
        ),
        (
            ("historical_baselines", "enterprise", "deployment_tenant_ref"),
            "range-a",
            "deployment_tenants.range-a",
            False,
        ),
        (
            ("historical_baselines", "enterprise", "deployment_cell_ref"),
            "range-a-cell",
            "deployment_cells.range-a-cell",
            False,
        ),
        (
            (
                "historical_baselines",
                "enterprise",
                "reset_owner_relationship_ref",
            ),
            "records-reset-owner",
            "relationships.records-reset-owner",
            False,
        ),
        (
            (
                "historical_baselines",
                "enterprise",
                "materialization_bindings",
                "message-native",
                "deployment_tenant_ref",
            ),
            "range-a",
            "deployment_tenants.range-a",
            False,
        ),
        (
            (
                "historical_baselines",
                "enterprise",
                "materialization_bindings",
                "message-native",
                "object_refs",
            ),
            "message-001",
            "objects.message-001",
            True,
        ),
        (
            (
                "historical_baselines",
                "enterprise",
                "materialization_bindings",
                "message-native",
                "readback_requirement_refs",
            ),
            "message-readback",
            "readback_requirements.message-readback",
            True,
        ),
        (
            (
                "historical_baselines",
                "enterprise",
                "readback_requirements",
                "message-readback",
                "object_ref",
            ),
            "message-001",
            "objects.message-001",
            False,
        ),
        (
            (
                "historical_baselines",
                "enterprise",
                "readback_requirements",
                "message-readback",
                "assertion_refs",
            ),
            "message-readback",
            "assertions.message-readback",
            True,
        ),
    ],
)
def test_reference_variables_defer_aggregate_checks_until_instantiation(
    path: tuple[str, ...],
    default: str,
    explicit: str,
    is_list: bool,
) -> None:
    payload = _valid_payload()
    payload["variables"] = {
        "historical_ref": {
            "type": "string",
            "default": default,
        }
    }
    target: object = payload
    for segment in path[:-1]:
        target = target[segment]  # type: ignore[index]
    target[path[-1]] = ["${historical_ref}"] if is_list else "${historical_ref}"  # type: ignore[index]

    authored = _parse(payload)
    defaulted = instantiate_scenario(authored)
    supplied = instantiate_scenario(
        authored,
        parameters={"historical_ref": explicit},
    )

    assert defaulted.historical_baselines["enterprise"]
    assert supplied.historical_baselines["enterprise"]


def _address_context(**overrides: str) -> HistoricalSemanticAddressContextModel:
    values = {
        "address_profile": "aces-historical-semantic-address/v1",
        "range_instance_id": "range-a",
        "deployment_tenant_id": "tenant-a",
        "reset_generation_id": "generation-a",
        "baseline_id": "baseline-a",
        "baseline_version": "1.0.0",
        "object_id": "object-a",
    }
    values.update(overrides)
    return HistoricalSemanticAddressContextModel.model_validate(values)


def test_semantic_addresses_are_jcs_deterministic_and_domain_separated() -> None:
    context = _address_context()
    first = derive_historical_semantic_address(context)
    second = derive_historical_semantic_address(
        HistoricalSemanticAddressContextModel.model_validate(
            {
                "object_id": "object-a",
                "baseline_version": "1.0.0",
                "baseline_id": "baseline-a",
                "reset_generation_id": "generation-a",
                "deployment_tenant_id": "tenant-a",
                "range_instance_id": "range-a",
                "address_profile": "aces-historical-semantic-address/v1",
            }
        )
    )

    assert first == second
    assert first.value.startswith("hsa1:")
    assert canonical_historical_address_bytes(context).startswith(b"{")

    for field, changed in (
        ("range_instance_id", "range-b"),
        ("deployment_tenant_id", "tenant-b"),
        ("reset_generation_id", "generation-b"),
        ("baseline_id", "baseline-b"),
        ("baseline_version", "2.0.0"),
        ("object_id", "object-b"),
    ):
        assert derive_historical_semantic_address(_address_context(**{field: changed})).value != first.value


def test_semantic_address_batch_rejects_duplicate_coordinates_and_collisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _address_context()
    with pytest.raises(ValueError, match="duplicate historical semantic address coordinate"):
        derive_historical_semantic_addresses((context, context))

    monkeypatch.setattr(
        "aces_contracts.historical_addressing.canonical_historical_address_bytes",
        lambda _context: b"same",
    )
    with pytest.raises(ValueError, match="duplicate canonical bytes"):
        derive_historical_semantic_addresses((context, _address_context(object_id="object-b")))

    monkeypatch.undo()
    monkeypatch.setattr("aces_contracts.historical_addressing._digest_address", lambda _value: b"x" * 32)
    with pytest.raises(ValueError, match="digest collision"):
        derive_historical_semantic_addresses((context, _address_context(object_id="object-b")))


def test_historical_baseline_digest_is_complete_deterministic_and_domain_separated() -> None:
    scenario = _parse(_valid_payload())
    baseline = scenario.historical_baselines["enterprise"]

    first = derive_historical_baseline_digest("enterprise", baseline)
    second = derive_historical_baseline_digest("enterprise", baseline)
    canonical_bytes = canonical_historical_baseline_bytes("enterprise", baseline)

    assert first == second
    assert first.value == "sha256:" + hashlib.sha256(HISTORICAL_BASELINE_DIGEST_DOMAIN + canonical_bytes).hexdigest()

    changed_baselines = (
        baseline.model_copy(update={"description": "Changed historical intent"}),
        baseline.model_copy(
            update={
                "objects": {
                    **baseline.objects,
                    "message-001": baseline.objects["message-001"].model_copy(update={"title": "Changed message"}),
                }
            }
        ),
        baseline.model_copy(
            update={
                "events": {
                    **baseline.events,
                    "create-message": baseline.events["create-message"].model_copy(update={"order": 99}),
                }
            }
        ),
        baseline.model_copy(
            update={
                "materialization_bindings": {
                    **baseline.materialization_bindings,
                    "message-native": baseline.materialization_bindings["message-native"].model_copy(
                        update={"ordering_dependencies": ["case-native"]}
                    ),
                }
            }
        ),
    )
    assert all(
        derive_historical_baseline_digest("enterprise", changed).value != first.value for changed in changed_baselines
    )


def test_compiler_preserves_graph_and_addresses_without_plan_resources() -> None:
    scenario = _parse(_valid_payload())
    model = compile_runtime_model(scenario)

    assert model.realization_instance.historical_baselines == scenario.historical_baselines
    assert set(model.historical_object_addresses) == {
        "historical_baselines.enterprise.objects.message-001",
        "historical_baselines.enterprise.objects.case-001",
    }
    assert model.historical_baseline_digests["enterprise"] == derive_historical_baseline_digest(
        "enterprise",
        scenario.historical_baselines["enterprise"],
    )
    assert all(not hasattr(address, "resource_type") for address in model.historical_object_addresses.values())
    assert len(model.node_deployments) == 1
    assert not model.generated_artifacts
    assert len(model.persistent_volumes) == 1


def test_four_published_embedding_schemas_carry_closed_historical_shape() -> None:
    bundle = schema_bundle()
    payload = _valid_payload()
    assert Draft202012Validator(bundle["sdl-authoring-input-v1"]).is_valid(payload)

    instantiated_payload = {**payload, "instantiation_provenance": _INSTANTIATION_PROVENANCE}
    assert Draft202012Validator(bundle["instantiated-scenario-v1"]).is_valid(instantiated_payload)
    assert Draft202012Validator(bundle["instantiated-scenario-snapshot-v1"]).is_valid(
        {
            "profile": "aces-sdl-instantiated-snapshot/v1",
            "scenario": instantiated_payload,
        }
    )
    satisfiability = bundle["scenario-satisfiability-evidence-v1"]
    assert "HistoricalBaseline" in str(satisfiability)

    invalid = deepcopy(payload)
    _baseline(invalid)["objects"]["message-001"]["native_id"] = "42"  # type: ignore[index]
    assert not Draft202012Validator(bundle["sdl-authoring-input-v1"]).is_valid(invalid)


def test_absent_historical_section_preserves_existing_documents() -> None:
    scenario = parse_sdl("name: minimal\nnodes: {}\n")
    model = compile_runtime_model(scenario)

    assert scenario.historical_baselines == {}
    assert model.historical_baseline_digests == {}
    assert model.historical_object_addresses == {}
