"""HTTP/JSON control-plane DTO conversion helpers."""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from typing import Any

from aces_contracts.contracts import (
    EvaluationPlanModel,
    OperationStatusModel,
    OrchestrationPlanModel,
    ProvisioningPlanModel,
    RuntimeSnapshotEnvelopeModel,
)
from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.participant_episode import ParticipantEpisodeTerminalReason
from aces_contracts.planning import (
    ChangeAction,
    EvaluationOp,
    EvaluationPlan,
    OrchestrationOp,
    OrchestrationPlan,
    ProvisioningPlan,
    ProvisionOp,
)
from aces_contracts.runtime_state import OperationStatus, RuntimeSnapshotEnvelope
from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field


class _ParticipantInitializeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    episode_id: str | None = None


class _ParticipantResetBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    episode_id: str | None = None
    reason: str = Field(default="reset by operator")


class _ParticipantRestartBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    episode_id: str | None = None
    reason: str = Field(default="restarted by operator")


class _ParticipantTerminateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    terminal_reason: str = Field(default=ParticipantEpisodeTerminalReason.INTERRUPTED.value)
    detail: str = Field(default="terminated by operator")


def _diagnostic_from_mapping(payload: dict[str, Any]) -> Diagnostic:
    return Diagnostic(
        code=str(payload.get("code", "runtime.control-plane")),
        domain=str(payload.get("domain", "runtime")),
        address=str(payload.get("address", "runtime.control-plane")),
        message=str(payload.get("message", "")),
        severity=Severity(str(payload.get("severity", "error"))),
    )


def _provisioning_plan(model: ProvisioningPlanModel) -> ProvisioningPlan:
    return ProvisioningPlan(
        operations=[
            ProvisionOp(
                action=ChangeAction(str(op.action)),
                address=op.address,
                resource_type=op.resource_type,
                payload=dict(op.payload),
                ordering_dependencies=tuple(op.ordering_dependencies),
                refresh_dependencies=tuple(op.refresh_dependencies),
            )
            for op in model.operations
        ],
        diagnostics=[_diagnostic_from_mapping(payload) for payload in model.diagnostics],
        realization_envelope=model.realization_envelope,
    )


def _orchestration_plan(model: OrchestrationPlanModel) -> OrchestrationPlan:
    return OrchestrationPlan(
        operations=[
            OrchestrationOp(
                action=ChangeAction(str(op.action)),
                address=op.address,
                resource_type=op.resource_type,
                payload=dict(op.payload),
                ordering_dependencies=tuple(op.ordering_dependencies),
                refresh_dependencies=tuple(op.refresh_dependencies),
            )
            for op in model.operations
        ],
        startup_order=list(model.startup_order),
        diagnostics=[_diagnostic_from_mapping(payload) for payload in model.diagnostics],
    )


def _evaluation_plan(model: EvaluationPlanModel) -> EvaluationPlan:
    return EvaluationPlan(
        operations=[
            EvaluationOp(
                action=ChangeAction(str(op.action)),
                address=op.address,
                resource_type=op.resource_type,
                payload=dict(op.payload),
                ordering_dependencies=tuple(op.ordering_dependencies),
                refresh_dependencies=tuple(op.refresh_dependencies),
            )
            for op in model.operations
        ],
        startup_order=list(model.startup_order),
        diagnostics=[_diagnostic_from_mapping(payload) for payload in model.diagnostics],
    )


def _operation_status_model(status: OperationStatus) -> OperationStatusModel:
    return OperationStatusModel.model_validate(
        {
            "schema_version": status.schema_version,
            "operation_id": status.operation_id,
            "domain": status.domain.value,
            "state": status.state.value,
            "submitted_at": status.submitted_at,
            "updated_at": status.updated_at,
            "diagnostics": [asdict(diag) for diag in status.diagnostics],
            "changed_addresses": list(status.changed_addresses),
        }
    )


def _snapshot_model(envelope: RuntimeSnapshotEnvelope) -> RuntimeSnapshotEnvelopeModel:
    snapshot = envelope.snapshot
    return RuntimeSnapshotEnvelopeModel.model_validate(
        {
            "schema_version": envelope.schema_version,
            "entries": {
                address: {
                    "address": entry.address,
                    "domain": entry.domain.value,
                    "resource_type": entry.resource_type,
                    "payload": dict(entry.payload),
                    "ordering_dependencies": list(entry.ordering_dependencies),
                    "refresh_dependencies": list(entry.refresh_dependencies),
                    "status": entry.status,
                }
                for address, entry in snapshot.entries.items()
            },
            "orchestration_results": dict(snapshot.orchestration_results),
            "orchestration_history": dict(snapshot.orchestration_history),
            "evaluation_results": dict(snapshot.evaluation_results),
            "evaluation_history": dict(snapshot.evaluation_history),
            "participant_episode_results": dict(snapshot.participant_episode_results),
            "participant_episode_history": dict(snapshot.participant_episode_history),
            "participant_behavior_history": dict(snapshot.participant_behavior_history),
            "shared_state_records": dict(snapshot.shared_state_records),
            "shared_state_history": dict(snapshot.shared_state_history),
            "joint_action_records": dict(snapshot.joint_action_records),
            "time_management_contexts": dict(snapshot.time_management_contexts),
            "realization_envelope": (
                snapshot.realization_envelope.model_dump(mode="json")
                if snapshot.realization_envelope is not None
                else None
            ),
            "metadata": dict(snapshot.metadata),
        }
    )


def _request_fingerprint(request: Request, body: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(request.url.path.encode("utf-8"))
    digest.update(b"\n")
    digest.update(body)
    return digest.hexdigest()
