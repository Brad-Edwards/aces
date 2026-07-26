"""SEM-218 scoped realization designation and cascade behavior."""

from __future__ import annotations

import json
import textwrap
from dataclasses import replace
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError
from raes._errors import SDLParseError
from raes.explicitness import ExplicitnessClass, ExplicitnessProvenance
from raes.instantiate import instantiate_scenario
from raes.parser import parse_sdl, parse_sdl_file
from raes.realization_designation import (
    AuthorRealizationPosture,
    RealizationDesignationRecord,
    RealizationScopeDesignation,
    resolve_json_pointer_surface,
)
from raes_backend_libvirt.manifest import create_libvirt_manifest
from raes_backend_protocols.capabilities import BackendManifest, ProvisionerCapabilities
from raes_contracts.apparatus import ConceptBinding, RealizationSupportDeclaration
from raes_contracts.planning import ChangeAction, ProvisioningPlan, ProvisionOp, RuntimeDomain
from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel, realization_envelope_digest
from raes_contracts.runtime_state import RuntimeSnapshot, RuntimeSnapshotEnvelope, SnapshotEntry
from raes_contracts.vocabulary import Closure, RealizationSupportMode
from raes_processor.compiler import compile_runtime_model
from raes_processor.planner import plan
from raes_processor.semantics.realization import realization_disclosure
from raes_runtime.control_plane_api_models import _snapshot_model


def _scenario(realization: str = "", *, web_os: str = ""):
    realization_block = textwrap.dedent(realization).strip()
    web_os_line = f"    {web_os}\n" if web_os else ""
    return parse_sdl(
        f"name: scoped-realization\n"
        f"{realization_block + chr(10) if realization_block else ''}"
        "nodes:\n"
        "  web:\n"
        "    type: vm\n"
        f"{web_os_line}"
        "    resources: {ram: 1 gib, cpu: 1}\n"
        "  worker:\n"
        "    type: vm\n"
        "    resources: {ram: 1 gib, cpu: 1}\n"
    )


def _manifest(mode: RealizationSupportMode) -> BackendManifest:
    return BackendManifest(
        name="designation-test",
        version="1.0.0",
        supported_contract_versions=frozenset({"backend-manifest-v2"}),
        compatible_processors=frozenset({"raes-reference-processor"}),
        realization_support=(
            RealizationSupportDeclaration(
                domain="runtime-realization",
                support_mode=mode,
                supported_constraint_kinds=frozenset({"os-family", "node-type"}),
                supported_exact_requirement_kinds=frozenset({"declared-capability-match"}),
                disclosure_kinds=frozenset({"runtime-snapshot-v1"}),
            ),
        ),
        concept_bindings=(ConceptBinding(scope="capabilities.provisioner.supported_node_types", family="assets"),),
        provisioner=ProvisionerCapabilities(
            name="designation-test",
            supported_node_types=frozenset({"vm"}),
            supported_os_families=frozenset({"linux"}),
        ),
    )


def _requirement(model, field_path: str):
    return next(requirement for requirement in model.realization_requirements if requirement.field_path == field_path)


def _open_manifest_with_envelope(*, path: str, value: str) -> BackendManifest:
    manifest = create_libvirt_manifest()
    assert manifest.realization_envelope is not None
    payload = manifest.realization_envelope.model_dump(mode="json")
    payload["expression"]["domains"] = {"fixed": {"kind": "exact", "value": value}}
    payload["expression"]["bindings"] = [{"path": path, "scope": "field", "posture": "exact", "domain": "fixed"}]
    payload["digest"] = realization_envelope_digest(payload)
    envelope = BackendRealizationEnvelopeModel.model_validate(payload)
    support = replace(
        manifest.realization_support[0],
        support_mode=RealizationSupportMode.OPEN_REALIZATION,
    )
    return replace(manifest, realization_support=(support,), realization_envelope=envelope)


def test_root_open_is_typed_and_carried_to_compilation():
    scenario = _scenario("realization:\n  default: open")

    instantiated = instantiate_scenario(scenario)
    model = compile_runtime_model(instantiated)

    assert scenario.realization is not None
    assert scenario.realization.default is AuthorRealizationPosture.OPEN
    assert instantiated.instantiation_provenance.realization_designations[0].posture is AuthorRealizationPosture.OPEN
    requirement = _requirement(model, "nodes.web.os")
    assert requirement.explicitness is ExplicitnessClass.OPEN
    assert requirement.governing_scope == "#/"


def test_most_specific_scopes_override_in_both_directions_and_ignore_order():
    open_then_closed = """realization:
      default: open
      scopes:
        - field_pointer: /nodes
          posture: closed
        - field_pointer: /nodes/worker
          posture: open
    """
    reversed_scopes = """realization:
      default: open
      scopes:
        - field_pointer: /nodes/worker
          posture: open
        - field_pointer: /nodes
          posture: closed
    """

    first = compile_runtime_model(_scenario(open_then_closed))
    second = compile_runtime_model(_scenario(reversed_scopes))

    assert {
        requirement.field_path
        for requirement in first.realization_requirements
        if requirement.explicitness is ExplicitnessClass.OPEN
    } == {"nodes.worker.os"}
    assert first.realization_requirements == second.realization_requirements

    closed_then_open = """realization:
      default: closed
      scopes:
        - field_pointer: /nodes
          posture: open
        - field_pointer: /nodes/web
          posture: closed
    """
    model = compile_runtime_model(_scenario(closed_then_open))
    assert {
        requirement.field_path
        for requirement in model.realization_requirements
        if requirement.explicitness is ExplicitnessClass.OPEN
    } == {"nodes.worker.os"}


def test_explicit_leaf_wins_over_inherited_open_posture():
    model = compile_runtime_model(_scenario("realization:\n  default: open", web_os="os: linux"))

    requirement = _requirement(model, "nodes.web.os")
    assert requirement.explicitness is ExplicitnessClass.EXACT
    assert requirement.provenance is ExplicitnessProvenance.AUTHOR_DECLARED
    assert requirement.governing_scope == "#/nodes/web/os"


def test_omission_and_explicit_root_delegation_remain_distinct():
    omitted = instantiate_scenario(_scenario())
    delegated = instantiate_scenario(_scenario("realization:\n  default: unspecified"))

    assert omitted.instantiation_provenance.realization_designations == ()
    assert (
        delegated.instantiation_provenance.realization_designations[0].posture is AuthorRealizationPosture.UNSPECIFIED
    )

    omitted_model = compile_runtime_model(omitted)
    delegated_model = compile_runtime_model(delegated)
    assert not any(requirement.field_path == "nodes.web.os" for requirement in omitted_model.realization_requirements)
    requirement = _requirement(delegated_model, "nodes.web.os")
    assert requirement.delegated is True
    assert requirement.explicitness is None


@pytest.mark.parametrize(
    "realization",
    [
        "realization:\n  default: open\n  scopes:\n    - {field_pointer: /nodes/web~2os, posture: closed}",
        "realization:\n  default: open\n  scopes:\n    - {field_pointer: nodes/web, posture: closed}",
        (
            "realization:\n  default: open\n  scopes:\n"
            "    - {field_pointer: /nodes/web, posture: closed}\n"
            "    - {field_pointer: /nodes/web, posture: open}"
        ),
    ],
)
def test_invalid_or_conflicting_canonical_scopes_are_rejected(realization: str):
    with pytest.raises(SDLParseError):
        _scenario(realization)


@pytest.mark.parametrize("field_pointer", ["nodes/web", "/nodes/web~2os"])
def test_realization_designation_models_reject_non_rfc6901_pointers(field_pointer: str):
    with pytest.raises(ValidationError):
        RealizationScopeDesignation(
            field_pointer=field_pointer,
            posture=AuthorRealizationPosture.OPEN,
        )
    with pytest.raises(ValidationError):
        RealizationDesignationRecord(
            field_pointer=field_pointer,
            posture=AuthorRealizationPosture.OPEN,
        )


def test_rfc6901_scope_resolution_preserves_escaped_key_identity():
    found, value = resolve_json_pointer_surface(
        {"nodes": {"slash/key": {"os": "linux"}}},
        "/nodes/slash~1key/os",
    )

    assert found and value == "linux"
    assert not resolve_json_pointer_surface(
        {"nodes": {"slash/key": {"os": "linux"}}},
        "/nodes/slash/key/os",
    )[0]


def test_imported_scope_is_qualified_and_does_not_leak_to_host_or_sibling(tmp_path: Path):
    (tmp_path / "open-module.yaml").write_text(
        textwrap.dedent(
            """
            name: open-module
            version: 1.0.0
            module:
              id: acme/open-module
              version: 1.0.0
              exports: {nodes: [vm]}
            realization:
              default: closed
              scopes:
                - {field_pointer: /nodes/vm, posture: open}
            nodes:
              vm: {type: vm, resources: {ram: 1 gib, cpu: 1}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "closed-module.yaml").write_text(
        textwrap.dedent(
            """
            name: closed-module
            version: 1.0.0
            module:
              id: acme/closed-module
              version: 1.0.0
              exports: {nodes: [vm]}
            nodes:
              vm: {type: vm, resources: {ram: 1 gib, cpu: 1}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    root = tmp_path / "root.yaml"
    root.write_text(
        textwrap.dedent(
            """
            name: root
            imports:
              - {source: local:open-module.yaml, namespace: openmod}
              - {source: local:closed-module.yaml, namespace: closedmod}
            nodes:
              host: {type: vm, resources: {ram: 1 gib, cpu: 1}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    instantiated = instantiate_scenario(parse_sdl_file(root))
    model = compile_runtime_model(instantiated)
    records = instantiated.instantiation_provenance.realization_designations

    assert any(record.namespace == ("openmod",) and record.field_pointer == "/nodes/openmod.vm" for record in records)
    assert {
        requirement.field_path
        for requirement in model.realization_requirements
        if requirement.explicitness is ExplicitnessClass.OPEN
    } == {"nodes.openmod.vm.os"}


def test_open_demand_is_rejected_without_open_realization_support():
    model = compile_runtime_model(_scenario("realization:\n  default: open"))

    rejected = plan(model, _manifest(RealizationSupportMode.CONSTRAINED))
    accepted = plan(model, _manifest(RealizationSupportMode.OPEN_REALIZATION))

    diagnostics = [
        diagnostic
        for diagnostic in rejected.diagnostics
        if diagnostic.code == "realization.unsupported-open-requirement"
    ]
    assert diagnostics
    assert "nodes.web.os" in diagnostics[0].message
    assert "linux" not in diagnostics[0].message
    assert accepted.is_valid
    assert not any(diagnostic.code.startswith("realization.") for diagnostic in accepted.diagnostics)


def test_root_delegation_uses_injected_selected_apparatus_default():
    model = compile_runtime_model(_scenario("realization:\n  default: unspecified"))

    legacy_closed = plan(model, _manifest(RealizationSupportMode.CONSTRAINED))
    delegated_open = plan(
        model,
        _manifest(RealizationSupportMode.CONSTRAINED),
        apparatus_realization_default=lambda _requirement, _manifest: Closure.OPEN_WORLD,
    )

    assert not any(diagnostic.code.startswith("realization.") for diagnostic in legacy_closed.diagnostics)
    assert any(
        diagnostic.code == "realization.unsupported-open-requirement" for diagnostic in delegated_open.diagnostics
    )


def test_delegated_open_posture_is_materialized_through_runtime_disclosure():
    model = compile_runtime_model(_scenario("realization:\n  default: unspecified"))
    execution = plan(
        model,
        _manifest(RealizationSupportMode.OPEN_REALIZATION),
        apparatus_realization_default=lambda _requirement, _manifest: Closure.OPEN_WORLD,
    )
    requirement = _requirement(execution.model, "nodes.web.os")
    entries = {
        operation.address: SnapshotEntry(
            address=operation.address,
            domain=RuntimeDomain.PROVISIONING,
            resource_type=operation.resource_type,
            payload=dict(operation.payload),
        )
        for operation in execution.provisioning.operations
        if operation.action is not ChangeAction.DELETE
    }

    diagnostics, provenance = realization_disclosure(
        execution.model.realization_requirements,
        execution.provisioning,
        RuntimeSnapshot(entries=entries),
    )

    assert execution.is_valid
    assert requirement.explicitness is ExplicitnessClass.OPEN
    assert requirement.delegated is False
    assert diagnostics == []
    assert any(
        entry.field_path == "nodes.web.os"
        and entry.provenance is ExplicitnessProvenance.BACKEND_REALIZED
        and entry.governing_scope == "#/"
        for entry in provenance
    )


def test_open_request_uses_envelope_subsumption_only_for_open_concern_paths():
    model = compile_runtime_model(_scenario("realization:\n  default: open"))

    restricted = plan(
        model,
        _open_manifest_with_envelope(path="nodes.web.os", value="linux"),
    )
    unrelated = plan(
        model,
        _open_manifest_with_envelope(path="name", value="scoped-realization"),
    )

    assert any(
        diagnostic.code == "realization-envelope.subsumption.requested-unconstrained"
        and diagnostic.address == "nodes.web.os"
        for diagnostic in restricted.diagnostics
    )
    assert unrelated.is_valid


def test_backend_realized_open_slot_discloses_governing_scope_through_api():
    model = compile_runtime_model(_scenario("realization:\n  default: open"))
    requirement = _requirement(model, "nodes.web.os")
    plan_payload = ProvisioningPlan(
        operations=[
            ProvisionOp(
                action=ChangeAction.CREATE,
                address=requirement.address,
                resource_type="node",
                payload={"node_type": "vm"},
            )
        ]
    )
    snapshot = RuntimeSnapshot(
        entries={
            requirement.address: SnapshotEntry(
                address=requirement.address,
                domain=RuntimeDomain.PROVISIONING,
                resource_type="node",
                payload={"node_type": "vm", "os_family": "linux"},
            )
        }
    )

    diagnostics, provenance = realization_disclosure((requirement,), plan_payload, snapshot)
    delivered = _snapshot_model(RuntimeSnapshotEnvelope(snapshot=RuntimeSnapshot(realization_provenance=provenance)))

    assert diagnostics == []
    assert provenance[0].provenance is ExplicitnessProvenance.BACKEND_REALIZED
    assert provenance[0].governing_scope == "#/"
    assert delivered.realization_provenance[0].governing_scope == "#/"


@pytest.mark.parametrize("action", [None, ChangeAction.DELETE])
def test_open_disclosure_requires_an_active_plan_operation(action: ChangeAction | None):
    model = compile_runtime_model(_scenario("realization:\n  default: open"))
    requirement = _requirement(model, "nodes.web.os")
    operations = (
        []
        if action is None
        else [
            ProvisionOp(
                action=action,
                address=requirement.address,
                resource_type="node",
                payload={},
            )
        ]
    )
    snapshot = RuntimeSnapshot(
        entries={
            requirement.address: SnapshotEntry(
                address=requirement.address,
                domain=RuntimeDomain.PROVISIONING,
                resource_type="node",
                payload={"os_family": "linux"},
            )
        }
    )

    diagnostics, provenance = realization_disclosure(
        (requirement,),
        ProvisioningPlan(operations=operations),
        snapshot,
    )

    assert diagnostics == []
    assert provenance == ()


def test_published_schemas_match_designation_and_governing_scope_models():
    repository = Path(__file__).resolve().parents[3]
    scenario = _scenario("realization:\n  default: open")
    instantiated = instantiate_scenario(scenario)
    provenance = [
        {
            "address": "node.web",
            "field_path": "nodes.web.os",
            "domain": "runtime-realization",
            "requirement_kind": "os-family",
            "explicitness": "open",
            "provenance": "backend-realized",
            "governing_scope": "#/",
        }
    ]
    cases = (
        (
            "contracts/schemas/sdl/sdl-authoring-input-v1.json",
            scenario.model_dump(mode="json", by_alias=True),
        ),
        (
            "contracts/schemas/sdl/instantiated-scenario-v1.json",
            instantiated.model_dump(mode="json", by_alias=True),
        ),
        (
            "contracts/schemas/snapshots/runtime-snapshot-v1.json",
            {"schema_version": "runtime-snapshot/v1", "realization_provenance": provenance},
        ),
    )

    for relative_path, payload in cases:
        schema = json.loads((repository / relative_path).read_text(encoding="utf-8"))
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(payload))
        assert errors == []


@pytest.mark.parametrize("field_pointer", ["nodes/web", "/nodes/web~2os"])
def test_published_phase_schemas_reject_non_rfc6901_designation_pointers(field_pointer: str):
    repository = Path(__file__).resolve().parents[3]
    scenario = _scenario(
        """realization:
          default: closed
          scopes:
            - {field_pointer: /nodes/web, posture: open}
        """
    )
    authoring_payload = scenario.model_dump(mode="json", by_alias=True)
    authoring_payload["realization"]["scopes"][0]["field_pointer"] = field_pointer

    instantiated_payload = instantiate_scenario(scenario).model_dump(mode="json", by_alias=True)
    instantiated_payload["instantiation_provenance"]["realization_designations"][1]["field_pointer"] = field_pointer

    cases = (
        ("contracts/schemas/sdl/sdl-authoring-input-v1.json", authoring_payload),
        ("contracts/schemas/sdl/instantiated-scenario-v1.json", instantiated_payload),
        ("contracts/schemas/sdl/instantiated-scenario-snapshot-v1.json", instantiated_payload),
    )
    for relative_path, payload in cases:
        schema = json.loads((repository / relative_path).read_text(encoding="utf-8"))
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(payload))
        assert errors
