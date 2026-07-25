"""Initial service state stays ordinary content with exact service realization."""

from __future__ import annotations

import textwrap
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from aces_backend_protocols.backend_manifest import BackendManifest
from aces_contracts.planning import ChangeAction, ProvisioningPlan, ProvisionOp, RuntimeDomain
from aces_contracts.runtime_state import RuntimeSnapshot, SnapshotEntry
from aces_processor.compiler import compile_scenario_runtime_model
from aces_processor.models import resource_payload
from aces_processor.planner import plan
from aces_processor.semantics.realization import realization_disclosure
from aces_runtime.control_plane import RuntimeControlPlane
from aces_runtime.registry import RuntimeTarget
from aces_sdl import SDLValidationError, parse_sdl, parse_sdl_file

from aces.backends.stubs import create_stub_manifest, create_stub_target


def _scenario(*replacements: tuple[str, str]):
    source = """
name: initial-service-state
nodes:
  app:
    type: vm
    os: linux
    resources:
      ram: 1 gib
      cpu: 1
    services:
      - name: mail
        port: 143
  other:
    type: vm
    os: linux
    resources:
      ram: 1 gib
      cpu: 1
    services:
      - name: mail
        port: 143
deployment_tenants:
  range:
    description: one isolated range
deployment_cells:
  range-cell:
    tenant_ref: range
    node_refs: [app, other]
    cross_tenant_isolation: default_deny
content:
  messages:
    type: dataset
    target: app
    items:
      - name: welcome
    service_materialization:
      target_service_ref: nodes.app.services.mail
      interface_profile: service-content
      profile_version: "1"
      requirements:
        operation: ensure-owned-items
        conflict_policy: reject-unowned-collision
        readback: canonical-content-digest
      readback_assertion_refs: [messages-visible]
      evidence_requirement_refs: [service-readback]
      observation_boundary_refs: [participant-view]
propositions:
  messages-visible:
    description: The authored message set is visible through the service.
    subjects: [content.messages]
    basis: observed_state
    predicate:
      kind: boolean
      property: service-content-visible
      semantic_ref: urn:aces:observable:service-content-visible
      expected: true
    evidence_requirements: [service-readback]
assertions:
  messages-visible:
    proposition: messages-visible
    role: postcondition
observation_boundaries:
  participant-view:
    projection_basis: ordinary participant access to the named service
    observable_refs: [content.messages]
    redaction_policy: preserve authored participant-visible fields
    latency_profile: available before participant admission
evidence_requirements:
  service-readback:
    source_refs: [content.messages]
    scope: native service readback
    boundary_kind: participant_equivalent
    channel: api_response
    artifact_role: service_materialization_readback
    media_types: [application/json]
    sensitivity: plain
    redaction: redact_secrets
    integrity: checksum
    retention: run_lifetime
    loss_disclosure: required
"""
    for old, new in replacements:
        source = source.replace(old, new)
    return parse_sdl(textwrap.dedent(source))


def _manifest_with_profile() -> BackendManifest:
    manifest = create_stub_manifest()
    provisioner = replace(
        manifest.provisioner,
        supported_service_materialization_profiles=frozenset({"service-content-v1"}),
    )
    return BackendManifest(
        identity=manifest.identity,
        supported_contract_versions=manifest.supported_contract_versions,
        compatibility=manifest.compatibility,
        realization_support=manifest.realization_support,
        concept_bindings=manifest.concept_bindings,
        constraints=manifest.constraints,
        capabilities=replace(manifest.capabilities, provisioner=provisioner),
        realization_envelope=manifest.realization_envelope,
    )


def test_service_materialization_compiles_through_content_placement() -> None:
    model = compile_scenario_runtime_model(_scenario())

    placement = model.content_placements["provision.content.messages"]
    assert placement.target_address == "provision.node.app"
    assert placement.target_node == "app"
    binding = placement.service_materialization
    assert binding is not None
    assert binding.target_service_address == "provision.node.app.service.mail"
    assert binding.interface_profile == "service-content"
    assert binding.profile_version == "1"
    assert binding.operation == "ensure-owned-items"
    assert binding.conflict_policy == "reject-unowned-collision"
    assert binding.readback == "canonical-content-digest"
    assert binding.canonical_content_digest.startswith("sha256:")
    assert binding.readback_assertion_addresses == ("evaluation.assertion.messages-visible",)
    assert binding.evidence_requirement_refs == ("service-readback",)
    assert binding.observation_boundary_addresses == ("participant.observation-boundary.participant-view",)
    assert placement.ordering_dependencies == ("provision.node.app",)
    assert any(
        requirement.requirement_kind == "service-content-materialization" and requirement.address == placement.address
        for requirement in model.realization_requirements
    )


def test_backend_profile_support_is_separate_from_content_type_support() -> None:
    model = compile_scenario_runtime_model(_scenario())

    unsupported = plan(model, create_stub_manifest())
    assert "provisioner.unsupported-service-materialization-profile" in {
        diagnostic.code for diagnostic in unsupported.diagnostics
    }
    supported = plan(model, _manifest_with_profile())
    assert "provisioner.unsupported-service-materialization-profile" not in {
        diagnostic.code for diagnostic in supported.diagnostics
    }


def test_direct_plan_submission_repeats_profile_and_readback_admission() -> None:
    operation = ProvisionOp(
        action=ChangeAction.CREATE,
        address="provision.content.messages",
        resource_type="content-placement",
        payload={
            "target_address": "provision.node.app",
            "spec": {"type": "dataset"},
            "service_materialization": {
                "target_service_address": "provision.node.app.service.mail",
                "interface_profile": "service-content",
                "profile_version": "1",
                "content_type": "dataset",
                "operation": "ensure-owned-items",
                "conflict_policy": "reject-unowned-collision",
                "readback": "canonical-content-digest",
                "canonical_content_digest": "sha256:" + "a" * 64,
                "shared_service_relationship_ref": "",
                "consumer_tenant_ref": "",
                "mutable_state_owner": "",
                "reset_generation_owner": "",
                "readback_assertion_addresses": ["evaluation.assertion.messages-visible"],
                "evidence_requirement_refs": ["service-readback"],
                "observation_boundary_addresses": ["participant.observation-boundary.participant-view"],
            },
        },
    )
    base_target = create_stub_target()
    unsupported = RuntimeControlPlane(base_target).submit_provisioning(ProvisioningPlan(operations=[operation]))
    assert [diagnostic.code for diagnostic in unsupported.diagnostics] == [
        "provisioner.unsupported-service-materialization-profile"
    ]

    manifest = _manifest_with_profile()
    target = RuntimeTarget(
        name=base_target.name,
        manifest=manifest,
        provisioner=base_target.provisioner,
        orchestrator=base_target.orchestrator,
        evaluator=base_target.evaluator,
        participant_runtime=base_target.participant_runtime,
    )
    missing_readback = RuntimeControlPlane(target).submit_provisioning(ProvisioningPlan(operations=[operation]))
    assert [diagnostic.code for diagnostic in missing_readback.diagnostics] == [
        "provisioner.service-materialization-readback-unsupported"
    ]


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        (
            ("readback_assertion_refs: [messages-visible]", "readback_assertion_refs: [missing]"),
            "readback_assertion_ref 'missing'",
        ),
        (
            ("observation_boundary_refs: [participant-view]", "observation_boundary_refs: [missing]"),
            "observation_boundary_ref 'missing'",
        ),
    ],
)
def test_service_materialization_readback_refs_fail_closed(
    replacement: tuple[str, str],
    message: str,
) -> None:
    with pytest.raises(SDLValidationError, match=message):
        _scenario(replacement)


def test_service_materialization_requires_a_named_service_target() -> None:
    with pytest.raises(SDLValidationError, match="must resolve to a named VM service"):
        _scenario(
            (
                "target_service_ref: nodes.app.services.mail",
                "target_service_ref: nodes.app.services.missing",
            )
        )


def test_service_materialization_target_must_belong_to_content_node() -> None:
    with pytest.raises(SDLValidationError, match="must belong to content target node"):
        _scenario(
            (
                "target_service_ref: nodes.app.services.mail",
                "target_service_ref: nodes.other.services.mail",
            )
        )


def test_runtime_rejects_changed_service_materialization_binding() -> None:
    model = compile_scenario_runtime_model(_scenario())
    placement = model.content_placements["provision.content.messages"]
    payload = resource_payload(placement)
    changed_payload = dict(payload)
    changed_binding = dict(changed_payload["service_materialization"])
    changed_binding["canonical_content_digest"] = "sha256:" + "f" * 64
    changed_payload["service_materialization"] = changed_binding
    returned = RuntimeSnapshot(
        entries={
            placement.address: SnapshotEntry(
                address=placement.address,
                domain=RuntimeDomain.PROVISIONING,
                resource_type="content-placement",
                payload=changed_payload,
            )
        }
    )
    requirement = next(
        item for item in model.realization_requirements if item.requirement_kind == "service-content-materialization"
    )

    diagnostics, provenance = realization_disclosure(
        (requirement,),
        ProvisioningPlan(
            operations=[
                ProvisionOp(
                    action=ChangeAction.CREATE,
                    address=placement.address,
                    resource_type="content-placement",
                    payload=payload,
                )
            ]
        ),
        returned,
    )

    assert provenance == ()
    assert [diagnostic.code for diagnostic in diagnostics] == ["runtime.backend-contract-invalid"]


def test_module_composition_rewrites_service_materialization_refs(tmp_path: Path) -> None:
    payload = _scenario().model_dump(mode="json", exclude_none=True)
    payload["module"] = {
        "id": "aces/initial-service-state",
        "version": "1.0.0",
        "exports": {
            section: list(payload[section])
            for section in (
                "nodes",
                "content",
                "propositions",
                "assertions",
                "observation_boundaries",
                "evidence_requirements",
                "deployment_tenants",
                "deployment_cells",
            )
        },
    }
    imported = tmp_path / "initial-service-state.yaml"
    imported.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    root = tmp_path / "root.yaml"
    root.write_text(
        textwrap.dedent(
            """
            name: root
            imports:
              - path: initial-service-state.yaml
                namespace: shared
                version: 1.0.0
            """
        ),
        encoding="utf-8",
    )

    scenario = parse_sdl_file(root)
    binding = scenario.content["shared.messages"].service_materialization

    assert binding is not None
    assert binding.target_service_ref == "nodes.shared.app.services.mail"
    assert binding.readback_assertion_refs == ["shared.messages-visible"]
    assert binding.evidence_requirement_refs == ["shared.service-readback"]
    assert binding.observation_boundary_refs == ["shared.participant-view"]
