"""Reference HTTP/JSON control-plane API tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import raes_runtime.control_plane_store as control_plane_store_module
from raes import parse_sdl
from raes_backend_stubs.stubs import create_stub_target
from raes_contracts.contracts import (
    ParticipantContextViewModel,
    ParticipantHistoryViewModel,
    ParticipantStatusViewModel,
)
from raes_contracts.plan_projection import provisioning_plan_model
from raes_contracts.runtime_state import (
    ExplicitnessClass,
    ExplicitnessProvenance,
    RealizationProvenanceEntry,
    RuntimeSnapshot,
)
from raes_processor.compiler import compile_runtime_model
from raes_processor.models import OperationReceipt, OperationState, OperationStatus, RuntimeDomain
from raes_processor.planner import plan
from raes_runtime.control_plane import RuntimeControlPlane
from raes_runtime.control_plane_api import create_control_plane_app
from raes_runtime.control_plane_security import (
    ControlPlaneIdentity,
    ControlPlaneRole,
    ControlPlaneSecurityConfig,
)
from raes_runtime.control_plane_store import ControlPlaneOperationRecord, LocalControlPlaneStore
from starlette.testclient import TestClient


def _scenario(yaml_str: str):
    return parse_sdl(textwrap.dedent(yaml_str))


def _provisioning_payload(plan_value: object) -> dict[str, object]:
    return provisioning_plan_model(plan_value).model_dump(mode="json", exclude_none=True)


def _admit_workflow_prerequisites(control_plane: RuntimeControlPlane, execution_plan: object) -> None:
    provisioning = control_plane.submit_provisioning(execution_plan.provisioning)
    evaluation = control_plane.submit_evaluation(execution_plan.evaluation)
    assert provisioning.accepted, provisioning.diagnostics
    assert evaluation.accepted, evaluation.diagnostics


def _participant_operation_record(operation_id: str, participant_address: str) -> ControlPlaneOperationRecord:
    submitted_at = "2026-06-05T10:00:00Z"
    return ControlPlaneOperationRecord(
        receipt=OperationReceipt(
            operation_id=operation_id,
            domain=RuntimeDomain.PARTICIPANT,
            submitted_at=submitted_at,
            accepted=True,
        ),
        status=OperationStatus(
            operation_id=operation_id,
            domain=RuntimeDomain.PARTICIPANT,
            state=OperationState.RUNNING,
            submitted_at=submitted_at,
            updated_at=submitted_at,
            changed_addresses=[participant_address],
        ),
    )


def _test_security(target_name: str, *, max_request_bytes: int = 1_000_000) -> ControlPlaneSecurityConfig:
    return ControlPlaneSecurityConfig(
        max_request_bytes=max_request_bytes,
        trust_proxy_identity_headers=True,
        trusted_identities={
            "backend-service": ControlPlaneIdentity(
                identity="backend-service",
                roles=frozenset({ControlPlaneRole.BACKEND}),
                target_name=target_name,
            ),
        },
        bearer_tokens={
            "test-operator-token": ControlPlaneIdentity(
                identity="operator",
                roles=frozenset({ControlPlaneRole.OPERATOR, ControlPlaneRole.AUDITOR}),
                target_name=target_name,
            ),
            "test-auditor-token": ControlPlaneIdentity(
                identity="auditor",
                roles=frozenset({ControlPlaneRole.AUDITOR}),
                target_name=target_name,
            ),
        },
    )


def test_control_plane_strict_defaults_ship_without_builtin_principals():
    security = ControlPlaneSecurityConfig.strict_defaults()

    assert security.require_verified_identity is True
    assert security.trust_proxy_identity_headers is False
    assert security.trusted_identities == {}
    assert security.bearer_tokens == {}


def test_control_plane_api_default_security_does_not_trust_builtin_headers_or_tokens():
    target = create_stub_target()
    control_plane = RuntimeControlPlane(target)
    app = create_control_plane_app(control_plane)

    with TestClient(app) as client:
        header_response = client.get(
            "/snapshot",
            headers={
                "x-raes-client-verified": "true",
                "x-raes-client-identity": "backend-service",
            },
        )
        token_response = client.get(
            "/snapshot",
            headers={"authorization": "Bearer operator-token"},
        )

    assert header_response.status_code == 401
    assert token_response.status_code == 401


def test_control_plane_api_openapi_documents_explicit_error_responses():
    target = create_stub_target()
    control_plane = RuntimeControlPlane(target)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )

    operation_responses = app.openapi()["paths"]

    assert "409" in operation_responses["/operations/provisioning"]["post"]["responses"]
    assert "409" in operation_responses["/operations/orchestration"]["post"]["responses"]
    assert "409" in operation_responses["/operations/evaluation"]["post"]["responses"]
    assert "404" in operation_responses["/operations/{operation_id}"]["get"]["responses"]
    assert "409" in operation_responses["/workflows/{workflow_address}/cancel"]["post"]["responses"]
    assert "409" in operation_responses["/workflows/reconcile-timeouts"]["post"]["responses"]
    assert "409" in operation_responses["/participants/{participant_address}/episodes/initialize"]["post"]["responses"]
    assert "409" in operation_responses["/participants/{participant_address}/episodes/reset"]["post"]["responses"]
    assert "409" in operation_responses["/participants/{participant_address}/episodes/restart"]["post"]["responses"]
    terminate_responses = operation_responses["/participants/{participant_address}/episodes/terminate"]["post"][
        "responses"
    ]
    assert "400" in terminate_responses
    assert "409" in terminate_responses
    assert "404" in operation_responses["/participants/{participant_address}/status"]["get"]["responses"]
    history_path = "/participants/{participant_address}/episodes/{episode_id}/history"
    assert "404" in operation_responses[history_path]["get"]["responses"]
    assert "404" in operation_responses["/participants/{participant_address}/context"]["get"]["responses"]
    assert "/apparatus/operational-summary" in operation_responses


def test_control_plane_api_accepts_orchestration_plan_and_exposes_snapshot():
    scenario = _scenario("""
name: workflow
nodes:
  vm:
    type: compute
    resources: {ram: 1 gib, cpu: 1}
    conditions: {health: ops}
    roles: {ops: operator}
conditions:
  health: {command: /bin/true, interval: 15}
propositions:
  health:
    description: The governed VM has declared runtime state.
    subjects: [nodes.vm]
    basis: declared_state
    predicate: {kind: presence, property: runtime, semantic_ref: urn:raes:declared-property:runtime, operator: exists}
assertions:
  health: {proposition: health, role: postcondition, polarity: positive}
entities:
  blue: {role: blue}
objectives:
  validate:
    entity: blue
    success: {assertions: [health]}
workflows:
  response:
    start: run
    steps:
      run:
        type: objective
        objective: validate
        on_success: finish
      finish: {type: end}
""")
    target = create_stub_target()
    execution_plan = plan(compile_runtime_model(scenario), target.manifest)
    control_plane = RuntimeControlPlane(target)
    _admit_workflow_prerequisites(control_plane, execution_plan)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )
    headers = {
        "x-raes-client-verified": "true",
        "x-raes-client-identity": "backend-service",
    }

    with TestClient(app) as client:
        response = client.post(
            "/operations/orchestration",
            json={
                "operations": [
                    {
                        "action": op.action.value,
                        "address": op.address,
                        "resource_type": op.resource_type,
                        "payload": op.payload,
                        "ordering_dependencies": list(op.ordering_dependencies),
                        "refresh_dependencies": list(op.refresh_dependencies),
                    }
                    for op in execution_plan.orchestration.operations
                ],
                "startup_order": execution_plan.orchestration.startup_order,
                "diagnostics": [],
            },
            headers=headers,
        )
        assert response.status_code == 200
        receipt = response.json()
        status_response = client.get(
            f"/operations/{receipt['operation_id']}",
            headers=headers,
        )
        assert status_response.status_code == 200
        snapshot_response = client.get("/snapshot", headers=headers)
        assert snapshot_response.status_code == 200
        snapshot = snapshot_response.json()
        assert snapshot["orchestration_results"]
        assert snapshot["orchestration_results"]["orchestration.workflow.response"]["workflow_status"] == "running"


def test_control_plane_api_exposes_operational_apparatus_summary_to_auditors():
    scenario = _scenario("""
name: workflow
nodes:
  vm:
    type: compute
    resources: {ram: 1 gib, cpu: 1}
    conditions: {health: ops}
    roles: {ops: operator}
conditions:
  health: {command: /bin/true, interval: 15}
propositions:
  health:
    description: The governed VM has declared runtime state.
    subjects: [nodes.vm]
    basis: declared_state
    predicate: {kind: presence, property: runtime, semantic_ref: urn:raes:declared-property:runtime, operator: exists}
assertions:
  health: {proposition: health, role: postcondition, polarity: positive}
entities:
  blue: {role: blue}
objectives:
  validate:
    entity: blue
    success: {assertions: [health]}
workflows:
  response:
    start: run
    steps:
      run:
        type: objective
        objective: validate
        on_success: finish
      finish: {type: end}
""")
    target = create_stub_target()
    execution_plan = plan(compile_runtime_model(scenario), target.manifest)
    control_plane = RuntimeControlPlane(target)
    _admit_workflow_prerequisites(control_plane, execution_plan)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )
    backend_headers = {
        "x-raes-client-verified": "true",
        "x-raes-client-identity": "backend-service",
    }
    auditor_headers = {"authorization": "Bearer test-auditor-token"}

    with TestClient(app) as client:
        receipt = client.post(
            "/operations/orchestration",
            json={
                "operations": [
                    {
                        "action": op.action.value,
                        "address": op.address,
                        "resource_type": op.resource_type,
                        "payload": op.payload,
                        "ordering_dependencies": list(op.ordering_dependencies),
                        "refresh_dependencies": list(op.refresh_dependencies),
                    }
                    for op in execution_plan.orchestration.operations
                ],
                "startup_order": execution_plan.orchestration.startup_order,
                "diagnostics": [],
            },
            headers=backend_headers,
        ).json()
        response = client.get("/apparatus/operational-summary", headers=auditor_headers)

    assert response.status_code == 200
    summary = response.json()
    assert summary["target"] == target.name
    assert summary["resources"]["total"] >= 1
    assert summary["resources"]["by_domain"]["orchestration"] >= 1
    assert summary["operations"]["by_state"]["succeeded"] == 3
    orchestration_record = next(
        record for record in summary["operations"]["recent"] if record["operation_id"] == receipt["operation_id"]
    )
    assert orchestration_record["diagnostic_count"] == 0
    assert orchestration_record["diagnostic_codes"] == []
    assert orchestration_record["changed_addresses"]
    assert summary["runtime_surfaces"]["orchestration_results"] >= 1
    assert summary["runtime_surfaces"]["orchestration_history"] >= 1
    assert summary["audit"]["allowed"] >= 2
    assert summary["audit"]["denied"] == 0
    assert summary["audit"]["recent"][-1]["identity"] == "auditor"
    assert "details" not in summary["audit"]["recent"][-1]


def test_control_plane_api_operational_apparatus_summary_requires_read_role():
    target = create_stub_target()
    control_plane = RuntimeControlPlane(target)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )

    with TestClient(app) as client:
        response = client.get("/apparatus/operational-summary")

    assert response.status_code == 401
    assert control_plane.audit_log()
    assert control_plane.audit_log()[-1].allowed is False


def test_control_plane_api_rejects_unauthenticated_mutations():
    target = create_stub_target()
    control_plane = RuntimeControlPlane(target)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )

    with TestClient(app) as client:
        response = client.post(
            "/operations/provisioning",
            json={"operations": [], "diagnostics": [], "realization_authority": []},
        )

    assert response.status_code == 401


def test_control_plane_api_supports_idempotent_retries():
    target = create_stub_target()
    control_plane = RuntimeControlPlane(target)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )
    headers = {
        "x-raes-client-verified": "true",
        "x-raes-client-identity": "backend-service",
        "idempotency-key": "same-request",
    }

    with TestClient(app) as client:
        first = client.post(
            "/operations/provisioning",
            json={"operations": [], "diagnostics": [], "realization_authority": []},
            headers=headers,
        )
        second = client.post(
            "/operations/provisioning",
            json={"operations": [], "diagnostics": [], "realization_authority": []},
            headers=headers,
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["operation_id"] == second.json()["operation_id"]


def test_control_plane_api_persists_operations_and_snapshot(tmp_path: Path):
    scenario = _scenario("""
name: workflow
nodes:
  vm:
    type: compute
    resources: {ram: 1 gib, cpu: 1}
""")
    target = create_stub_target()
    execution_plan = plan(compile_runtime_model(scenario), target.manifest)
    store = LocalControlPlaneStore(tmp_path / "cp-store")
    control_plane = RuntimeControlPlane(target, store=store)
    control_plane.register_planner_produced_provisioning_plan(execution_plan.provisioning)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )
    headers = {
        "x-raes-client-verified": "true",
        "x-raes-client-identity": "backend-service",
    }

    with TestClient(app) as client:
        receipt = client.post(
            "/operations/provisioning",
            json=_provisioning_payload(execution_plan.provisioning),
            headers=headers,
        ).json()

    restarted = RuntimeControlPlane(target, store=store)
    assert restarted.get_operation(receipt["operation_id"]) is not None
    assert restarted.get_snapshot().snapshot.entries


def test_backend_principal_cannot_rewrite_registered_realization_authority() -> None:
    scenario = _scenario("""
name: authority-integrity
realization:
  default: closed
nodes:
  vm:
    type: compute
    resources: {ram: 1 gib, cpu: 1}
""")
    target = create_stub_target()
    execution_plan = plan(compile_runtime_model(scenario), target.manifest)
    control_plane = RuntimeControlPlane(target)
    control_plane.register_planner_produced_provisioning_plan(execution_plan.provisioning)
    app = create_control_plane_app(control_plane, security=_test_security(target.name))
    payload = _provisioning_payload(execution_plan.provisioning)
    closed_entry = next(
        entry for entry in payload["realization_authority"] if entry["requirement_kind"] == "runtime-environment"
    )
    closed_entry["mode"] = "open"
    closed_entry["source"] = "authored-scope"

    with TestClient(app) as client:
        response = client.post(
            "/operations/provisioning",
            json=payload,
            headers={
                "x-raes-client-verified": "true",
                "x-raes-client-identity": "backend-service",
            },
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "provisioning plan is not planner-authorized"}
    assert control_plane.snapshot.entries == {}


def test_authenticated_snapshot_preserves_realization_governing_scope_from_store(tmp_path: Path):
    target = create_stub_target()
    store = LocalControlPlaneStore(tmp_path / "cp-store")
    store.save_snapshot(
        RuntimeSnapshot(
            realization_provenance=(
                RealizationProvenanceEntry(
                    address="node.web",
                    field_path="nodes.web.os",
                    domain="runtime-realization",
                    requirement_kind="os-family",
                    explicitness=ExplicitnessClass.OPEN,
                    provenance=ExplicitnessProvenance.BACKEND_REALIZED,
                    governing_scope="#/",
                ),
            )
        )
    )
    restarted = RuntimeControlPlane(target, store=store)
    app = create_control_plane_app(
        restarted,
        security=_test_security(target.name),
    )

    with TestClient(app) as client:
        response = client.get(
            "/snapshot",
            headers={"authorization": "Bearer test-auditor-token"},
        )

    assert response.status_code == 200
    assert response.json()["realization_provenance"] == [
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


def test_control_plane_api_records_audit_events_for_denials():
    target = create_stub_target()
    control_plane = RuntimeControlPlane(target)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )

    with TestClient(app) as client:
        response = client.get("/snapshot")

    assert response.status_code == 401
    assert control_plane.audit_log()
    assert control_plane.audit_log()[-1].allowed is False


def test_control_plane_api_enforces_request_size_limit():
    target = create_stub_target()
    control_plane = RuntimeControlPlane(target)
    security = _test_security(target.name, max_request_bytes=32)
    app = create_control_plane_app(control_plane, security=security)
    headers = {
        "x-raes-client-verified": "true",
        "x-raes-client-identity": "backend-service",
    }

    with TestClient(app) as client:
        response = client.post(
            "/operations/provisioning",
            json={"operations": [], "diagnostics": [], "padding": "x" * 100},
            headers=headers,
        )

    assert response.status_code == 413


def test_control_plane_api_rejects_invalid_content_length_header():
    target = create_stub_target()
    control_plane = RuntimeControlPlane(target)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )
    headers = {
        "x-raes-client-verified": "true",
        "x-raes-client-identity": "backend-service",
        "content-type": "application/json",
        "content-length": "not-a-number",
    }

    with TestClient(app) as client:
        response = client.post(
            "/operations/provisioning",
            content=b'{"operations":[],"diagnostics":[]}',
            headers=headers,
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid content-length"}
    assert control_plane.audit_log()[-1].reason == "invalid content-length"


def test_local_control_plane_store_saves_snapshot_with_atomic_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    store = LocalControlPlaneStore(tmp_path / "cp-store")
    replace_calls: list[tuple[Path, Path]] = []
    real_replace = control_plane_store_module.os.replace

    def tracked_replace(source: str, destination: str) -> None:
        replace_calls.append((Path(source), Path(destination)))
        real_replace(source, destination)

    monkeypatch.setattr(control_plane_store_module.os, "replace", tracked_replace)

    store.save_snapshot(RuntimeSnapshot())

    assert replace_calls
    assert replace_calls[0][1] == tmp_path / "cp-store" / "snapshot.json"
    assert not replace_calls[0][0].exists()
    assert not list((tmp_path / "cp-store").glob("*.tmp"))


def test_local_control_plane_store_cleans_temp_file_after_atomic_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    store = LocalControlPlaneStore(tmp_path / "cp-store")

    def fail_replace(source: str, destination: str) -> None:
        del source, destination
        raise OSError("replace failed")

    monkeypatch.setattr(control_plane_store_module.os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        store.save_snapshot(RuntimeSnapshot())

    assert not (tmp_path / "cp-store" / "snapshot.json").exists()
    assert not list((tmp_path / "cp-store").glob("*.tmp"))


def test_control_plane_api_cancels_workflow_runs():
    scenario = _scenario("""
name: workflow
nodes:
  vm:
    type: compute
    resources: {ram: 1 gib, cpu: 1}
    conditions: {health: ops}
    roles: {ops: operator}
conditions:
  health: {command: /bin/true, interval: 15}
propositions:
  health:
    description: The governed VM has declared runtime state.
    subjects: [nodes.vm]
    basis: declared_state
    predicate: {kind: presence, property: runtime, semantic_ref: urn:raes:declared-property:runtime, operator: exists}
assertions:
  health: {proposition: health, role: postcondition, polarity: positive}
entities:
  blue: {role: blue}
objectives:
  validate:
    entity: blue
    success: {assertions: [health]}
workflows:
  response:
    start: run
    steps:
      run:
        type: objective
        objective: validate
        on_success: finish
      finish: {type: end}
""")
    target = create_stub_target()
    execution_plan = plan(compile_runtime_model(scenario), target.manifest)
    control_plane = RuntimeControlPlane(target)
    _admit_workflow_prerequisites(control_plane, execution_plan)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )
    headers = {
        "x-raes-client-verified": "true",
        "x-raes-client-identity": "backend-service",
    }

    with TestClient(app) as client:
        client.post(
            "/operations/orchestration",
            json={
                "operations": [
                    {
                        "action": op.action.value,
                        "address": op.address,
                        "resource_type": op.resource_type,
                        "payload": op.payload,
                        "ordering_dependencies": list(op.ordering_dependencies),
                        "refresh_dependencies": list(op.refresh_dependencies),
                    }
                    for op in execution_plan.orchestration.operations
                ],
                "startup_order": execution_plan.orchestration.startup_order,
                "diagnostics": [],
            },
            headers=headers,
        )
        cancel = client.post(
            "/workflows/orchestration.workflow.response/cancel",
            json={"reason": "operator requested stop"},
            headers=headers,
        )
        snapshot = client.get("/snapshot", headers=headers).json()

    assert cancel.status_code == 200
    result = snapshot["orchestration_results"]["orchestration.workflow.response"]
    assert result["workflow_status"] == "cancelled"
    assert result["terminal_reason"] == "operator requested stop"


def test_control_plane_api_reconciles_workflow_timeouts():
    scenario = _scenario("""
name: workflow
nodes:
  vm:
    type: compute
    resources: {ram: 1 gib, cpu: 1}
    conditions: {health: ops}
    roles: {ops: operator}
conditions:
  health: {command: /bin/true, interval: 15}
propositions:
  health:
    description: The governed VM has declared runtime state.
    subjects: [nodes.vm]
    basis: declared_state
    predicate: {kind: presence, property: runtime, semantic_ref: urn:raes:declared-property:runtime, operator: exists}
assertions:
  health: {proposition: health, role: postcondition, polarity: positive}
entities:
  blue: {role: blue}
objectives:
  validate:
    entity: blue
    success: {assertions: [health]}
workflows:
  response:
    start: run
    timeout: 1
    steps:
      run:
        type: objective
        objective: validate
        on_success: finish
      finish: {type: end}
""")
    target = create_stub_target()
    execution_plan = plan(compile_runtime_model(scenario), target.manifest)
    control_plane = RuntimeControlPlane(target)
    _admit_workflow_prerequisites(control_plane, execution_plan)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )
    headers = {
        "x-raes-client-verified": "true",
        "x-raes-client-identity": "backend-service",
    }

    with TestClient(app) as client:
        client.post(
            "/operations/orchestration",
            json={
                "operations": [
                    {
                        "action": op.action.value,
                        "address": op.address,
                        "resource_type": op.resource_type,
                        "payload": op.payload,
                        "ordering_dependencies": list(op.ordering_dependencies),
                        "refresh_dependencies": list(op.refresh_dependencies),
                    }
                    for op in execution_plan.orchestration.operations
                ],
                "startup_order": execution_plan.orchestration.startup_order,
                "diagnostics": [],
            },
            headers=headers,
        )
        workflow_address = "orchestration.workflow.response"
        seeded = dict(control_plane._snapshot.orchestration_results[workflow_address])
        seeded["started_at"] = "2000-01-01T00:00:00Z"
        seeded["updated_at"] = "2000-01-01T00:00:01Z"
        control_plane._snapshot = control_plane._snapshot.with_entries(
            dict(control_plane._snapshot.entries),
            orchestration_results={
                **control_plane._snapshot.orchestration_results,
                workflow_address: seeded,
            },
        )
        reconcile = client.post(
            "/workflows/reconcile-timeouts",
            headers=headers,
        )
        assert reconcile.status_code == 200
        snapshot = client.get("/snapshot", headers=headers).json()

    result = snapshot["orchestration_results"]["orchestration.workflow.response"]
    assert result["workflow_status"] == "timed_out"
    assert result["terminal_reason"] == "workflow timed out"


def test_control_plane_api_cancellation_triggers_compensation_history():
    scenario = _scenario("""
name: workflow
nodes:
  vm:
    type: compute
    resources: {ram: 1 gib, cpu: 1}
    conditions: {health: ops}
    roles: {ops: operator}
conditions:
  health: {command: /bin/true, interval: 15}
propositions:
  health:
    description: The governed VM has declared runtime state.
    subjects: [nodes.vm]
    basis: declared_state
    predicate: {kind: presence, property: runtime, semantic_ref: urn:raes:declared-property:runtime, operator: exists}
assertions:
  health: {proposition: health, role: postcondition, polarity: positive}
entities:
  blue: {role: blue}
objectives:
  validate:
    entity: blue
    success: {assertions: [health]}
workflows:
  rollback:
    start: finish
    steps:
      finish: {type: end}
  response:
    start: run
    compensation:
      mode: automatic
      on: [cancelled]
    steps:
      run:
        type: objective
        objective: validate
        compensate_with: rollback
        on_success: finish
        on_failure: finish
      finish: {type: end}
""")
    target = create_stub_target()
    execution_plan = plan(compile_runtime_model(scenario), target.manifest)
    control_plane = RuntimeControlPlane(target)
    _admit_workflow_prerequisites(control_plane, execution_plan)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )
    headers = {
        "x-raes-client-verified": "true",
        "x-raes-client-identity": "backend-service",
    }

    with TestClient(app) as client:
        client.post(
            "/operations/orchestration",
            json={
                "operations": [
                    {
                        "action": op.action.value,
                        "address": op.address,
                        "resource_type": op.resource_type,
                        "payload": op.payload,
                        "ordering_dependencies": list(op.ordering_dependencies),
                        "refresh_dependencies": list(op.refresh_dependencies),
                    }
                    for op in execution_plan.orchestration.operations
                ],
                "startup_order": execution_plan.orchestration.startup_order,
                "diagnostics": [],
            },
            headers=headers,
        )
        workflow_address = "orchestration.workflow.response"
        seeded = dict(control_plane._snapshot.orchestration_results[workflow_address])
        seeded["steps"] = {
            **seeded["steps"],
            "run": {"lifecycle": "completed", "outcome": "succeeded", "attempts": 1},
        }
        control_plane._snapshot = control_plane._snapshot.with_entries(
            dict(control_plane._snapshot.entries),
            orchestration_results={
                **control_plane._snapshot.orchestration_results,
                workflow_address: seeded,
            },
            orchestration_history={
                **control_plane._snapshot.orchestration_history,
                workflow_address: [
                    *control_plane._snapshot.orchestration_history[workflow_address],
                    {
                        "event_type": "step_completed",
                        "timestamp": seeded["updated_at"],
                        "step_name": "run",
                        "branch_name": None,
                        "join_step": None,
                        "outcome": "succeeded",
                        "details": {},
                    },
                ],
            },
        )
        cancel = client.post(
            "/workflows/orchestration.workflow.response/cancel",
            json={"reason": "operator requested stop"},
            headers=headers,
        )
        snapshot = client.get("/snapshot", headers=headers).json()

    assert cancel.status_code == 200
    result = snapshot["orchestration_results"]["orchestration.workflow.response"]
    history = snapshot["orchestration_history"]["orchestration.workflow.response"]
    assert result["workflow_status"] == "cancelled"
    assert result["compensation_status"] == "succeeded"
    assert any(event["event_type"] == "compensation_started" for event in history)
    assert any(
        event["event_type"] == "compensation_workflow_completed"
        and event["details"].get("workflow_address") == "orchestration.workflow.rollback"
        for event in history
    )


def test_control_plane_api_timeout_triggers_compensation_history():
    scenario = _scenario("""
name: workflow
nodes:
  vm:
    type: compute
    resources: {ram: 1 gib, cpu: 1}
    conditions: {health: ops}
    roles: {ops: operator}
conditions:
  health: {command: /bin/true, interval: 15}
propositions:
  health:
    description: The governed VM has declared runtime state.
    subjects: [nodes.vm]
    basis: declared_state
    predicate: {kind: presence, property: runtime, semantic_ref: urn:raes:declared-property:runtime, operator: exists}
assertions:
  health: {proposition: health, role: postcondition, polarity: positive}
entities:
  blue: {role: blue}
objectives:
  validate:
    entity: blue
    success: {assertions: [health]}
workflows:
  rollback:
    start: finish
    steps:
      finish: {type: end}
  response:
    start: run
    timeout: 1
    compensation:
      mode: automatic
      on: [timed_out]
    steps:
      run:
        type: objective
        objective: validate
        compensate_with: rollback
        on_success: finish
        on_failure: finish
      finish: {type: end}
""")
    target = create_stub_target()
    execution_plan = plan(compile_runtime_model(scenario), target.manifest)
    control_plane = RuntimeControlPlane(target)
    _admit_workflow_prerequisites(control_plane, execution_plan)
    app = create_control_plane_app(
        control_plane,
        security=_test_security(target.name),
    )
    headers = {
        "x-raes-client-verified": "true",
        "x-raes-client-identity": "backend-service",
    }

    with TestClient(app) as client:
        client.post(
            "/operations/orchestration",
            json={
                "operations": [
                    {
                        "action": op.action.value,
                        "address": op.address,
                        "resource_type": op.resource_type,
                        "payload": op.payload,
                        "ordering_dependencies": list(op.ordering_dependencies),
                        "refresh_dependencies": list(op.refresh_dependencies),
                    }
                    for op in execution_plan.orchestration.operations
                ],
                "startup_order": execution_plan.orchestration.startup_order,
                "diagnostics": [],
            },
            headers=headers,
        )
        workflow_address = "orchestration.workflow.response"
        seeded = dict(control_plane._snapshot.orchestration_results[workflow_address])
        seeded["started_at"] = "2000-01-01T00:00:00Z"
        seeded["updated_at"] = "2000-01-01T00:00:01Z"
        seeded["steps"] = {
            **seeded["steps"],
            "run": {"lifecycle": "completed", "outcome": "succeeded", "attempts": 1},
        }
        control_plane._snapshot = control_plane._snapshot.with_entries(
            dict(control_plane._snapshot.entries),
            orchestration_results={
                **control_plane._snapshot.orchestration_results,
                workflow_address: seeded,
            },
            orchestration_history={
                **control_plane._snapshot.orchestration_history,
                workflow_address: [
                    *control_plane._snapshot.orchestration_history[workflow_address],
                    {
                        "event_type": "step_completed",
                        "timestamp": "2000-01-01T00:00:01Z",
                        "step_name": "run",
                        "branch_name": None,
                        "join_step": None,
                        "outcome": "succeeded",
                        "details": {},
                    },
                ],
            },
        )
        client.post("/workflows/reconcile-timeouts", headers=headers)
        snapshot = client.get("/snapshot", headers=headers).json()

    result = snapshot["orchestration_results"]["orchestration.workflow.response"]
    history = snapshot["orchestration_history"]["orchestration.workflow.response"]
    assert result["workflow_status"] == "timed_out"
    assert result["compensation_status"] == "succeeded"
    assert any(event["event_type"] == "compensation_completed" for event in history)


class TestParticipantEpisodeHttpRoutes:
    """RUN-311 — HTTP surface for participant episode lifecycle control.

    Each POST route must drive the same state-machine transitions as the
    in-process control plane and the resulting ``/snapshot`` response
    must expose the mutated ``participant_episode_results`` /
    ``participant_episode_history`` fields in the RuntimeSnapshot envelope.
    """

    def _build_client(self):
        target = create_stub_target()
        control_plane = RuntimeControlPlane(target)
        app = create_control_plane_app(
            control_plane,
            security=_test_security(target.name),
        )
        return TestClient(app)

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "x-raes-client-verified": "true",
            "x-raes-client-identity": "backend-service",
        }

    def test_initialize_route_creates_first_episode(self):
        client = self._build_client()

        response = client.post(
            "/participants/participant.alice/episodes/initialize",
            headers=self._headers,
            json={},
        )
        snapshot = client.get("/snapshot", headers=self._headers).json()

        assert response.status_code == 200
        body = response.json()
        assert body["accepted"] is True
        assert body["domain"] == "participant"
        state = snapshot["participant_episode_results"]["participant.alice"]
        assert state["status"] == "running"
        assert state["sequence_number"] == 0
        history = snapshot["participant_episode_history"]["participant.alice"]
        assert [event["event_type"] for event in history] == [
            "episode_initialized",
            "episode_running",
        ]

    def test_reset_route_allocates_new_episode(self):
        client = self._build_client()
        client.post(
            "/participants/participant.alice/episodes/initialize",
            headers=self._headers,
            json={},
        )

        response = client.post(
            "/participants/participant.alice/episodes/reset",
            headers=self._headers,
            json={"reason": "operator reset"},
        )
        snapshot = client.get("/snapshot", headers=self._headers).json()

        assert response.status_code == 200
        state = snapshot["participant_episode_results"]["participant.alice"]
        assert state["sequence_number"] == 1
        assert state["last_control_action"] == "reset"
        assert state["previous_episode_id"] == "participant.alice-episode-1"

    def test_terminate_route_drives_state_to_terminated(self):
        client = self._build_client()
        client.post(
            "/participants/participant.alice/episodes/initialize",
            headers=self._headers,
            json={},
        )

        response = client.post(
            "/participants/participant.alice/episodes/terminate",
            headers=self._headers,
            json={"terminal_reason": "completed"},
        )
        snapshot = client.get("/snapshot", headers=self._headers).json()

        assert response.status_code == 200
        state = snapshot["participant_episode_results"]["participant.alice"]
        assert state["status"] == "terminated"
        assert state["terminal_reason"] == "completed"
        history = snapshot["participant_episode_history"]["participant.alice"]
        assert history[-1]["event_type"] == "episode_completed"

    def test_terminate_route_rejects_invalid_terminal_reason(self):
        client = self._build_client()
        client.post(
            "/participants/participant.alice/episodes/initialize",
            headers=self._headers,
            json={},
        )

        response = client.post(
            "/participants/participant.alice/episodes/terminate",
            headers=self._headers,
            json={"terminal_reason": "exploded"},
        )

        assert response.status_code == 400
        assert "invalid terminal_reason" in response.json()["detail"]

    def test_restart_route_resumes_after_termination(self):
        client = self._build_client()
        client.post(
            "/participants/participant.alice/episodes/initialize",
            headers=self._headers,
            json={},
        )
        client.post(
            "/participants/participant.alice/episodes/terminate",
            headers=self._headers,
            json={"terminal_reason": "completed"},
        )

        response = client.post(
            "/participants/participant.alice/episodes/restart",
            headers=self._headers,
            json={},
        )
        snapshot = client.get("/snapshot", headers=self._headers).json()

        assert response.status_code == 200
        state = snapshot["participant_episode_results"]["participant.alice"]
        assert state["sequence_number"] == 1
        assert state["status"] == "running"
        assert state["last_control_action"] == "restart"

    def test_routes_require_authenticated_identity(self):
        client = self._build_client()

        response = client.post(
            "/participants/participant.alice/episodes/initialize",
            json={},
        )
        assert response.status_code == 401

    def test_retrieval_routes_require_authenticated_identity(self):
        client = self._build_client()

        status = client.get("/participants/participant.alice/status")
        history = client.get(
            "/participants/participant.alice/episodes/participant.alice-episode-1/history",
        )
        context = client.get(
            "/participants/participant.alice/context",
            params={"view_ref": "views.context.network-posture.v1"},
        )

        assert status.status_code == 401
        assert history.status_code == 401
        assert context.status_code == 401

    def test_routes_reject_unknown_body_fields(self):
        """Closed-world request bodies — unknown fields must be rejected."""
        client = self._build_client()

        response = client.post(
            "/participants/participant.alice/episodes/initialize",
            headers=self._headers,
            json={"episode_id": "alice-1", "unknown": "value"},
        )
        assert response.status_code == 422

    def test_status_route_returns_api_408_status_view(self):
        client = self._build_client()
        client.post(
            "/participants/participant.alice/episodes/initialize",
            headers=self._headers,
            json={},
        )

        response = client.get(
            "/participants/participant.alice/status",
            headers=self._headers,
        )

        assert response.status_code == 200
        view = ParticipantStatusViewModel.model_validate(response.json())
        assert view.participant_address == "participant.alice"
        assert view.episode_id == "participant.alice-episode-1"
        assert view.episode_state is not None
        assert view.episode_state.status == "running"

    def test_status_route_scopes_open_operations_to_participant(self):
        target = create_stub_target()
        control_plane = RuntimeControlPlane(target)
        control_plane.initialize_participant_episode("participant.alice")
        control_plane.initialize_participant_episode("participant.bob")
        control_plane._operations = {
            "op-alice": _participant_operation_record("op-alice", "participant.alice"),
            "op-bob": _participant_operation_record("op-bob", "participant.bob"),
        }
        client = TestClient(
            create_control_plane_app(
                control_plane,
                security=_test_security(target.name),
            )
        )

        response = client.get(
            "/participants/participant.alice/status",
            headers=self._headers,
        )

        assert response.status_code == 200
        view = ParticipantStatusViewModel.model_validate(response.json())
        assert view.open_operation_refs == ["op-alice"]

    def test_history_route_returns_api_408_history_view(self):
        client = self._build_client()
        client.post(
            "/participants/participant.alice/episodes/initialize",
            headers=self._headers,
            json={},
        )

        response = client.get(
            "/participants/participant.alice/episodes/participant.alice-episode-1/history",
            headers=self._headers,
        )

        assert response.status_code == 200
        view = ParticipantHistoryViewModel.model_validate(response.json())
        assert view.participant_address == "participant.alice"
        assert view.episode_id == "participant.alice-episode-1"
        assert [event.event_type for event in view.episode_history] == [
            "episode_initialized",
            "episode_running",
        ]
        assert view.completeness == "complete"

    def test_context_route_returns_api_408_sem214_view(self):
        client = self._build_client()
        client.post(
            "/participants/participant.alice/episodes/initialize",
            headers=self._headers,
            json={},
        )

        response = client.get(
            "/participants/participant.alice/context",
            params={
                "view_ref": "views.context.network-posture.v1",
                "episode_id": "participant.alice-episode-1",
                "payload_ref": "evidence.context.alice.network-posture",
                "meaning_ref": "attacker.override",
                "audience_scope": "audience_neutral",
                "observation_point": "future-state",
                "comparability_class": "backend_specific_non_comparable",
                "backend_disclosure_ref": "attacker.disclosure",
            },
            headers=self._headers,
        )

        assert response.status_code == 200
        view = ParticipantContextViewModel.model_validate(response.json())
        assert view.participant_address == "participant.alice"
        assert view.view_ref == "views.context.network-posture.v1"
        assert view.derived_from_refs == ["runtime.snapshot.current"]
        assert view.meaning_ref == "views.context.network-posture.v1"
        assert view.participant_scope == "participant_local"
        assert view.audience_scope == "participant_visible"
        assert view.observation_point == "participant.alice-episode-1"
        assert view.source_layers[0].source_layer == "source_snapshot"
        assert view.source_layers[0].evidence_refs == ["runtime.snapshot.current"]
        assert view.transformation.transformation_rule_ref == "views.context.network-posture.v1"
        assert view.comparability.comparability_class == "portable_equivalent"
        assert view.comparability.backend_disclosure_refs == []
        assert view.payload_ref == "evidence.context.alice.network-posture"

    def test_retrieval_routes_return_404_for_unknown_participants(self):
        client = self._build_client()

        status = client.get("/participants/participant.unknown/status", headers=self._headers)
        history = client.get(
            "/participants/participant.unknown/episodes/episode-1/history",
            headers=self._headers,
        )
        context = client.get(
            "/participants/participant.unknown/context",
            params={"view_ref": "views.context.network-posture.v1"},
            headers=self._headers,
        )

        assert status.status_code == 404
        assert history.status_code == 404
        assert context.status_code == 404
