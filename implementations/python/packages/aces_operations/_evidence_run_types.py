"""Structural types and the input bundle for the libvirt scenario-evidence artifact.

These ``Protocol`` types describe the duck-typed runtime-layer shapes the artifact
builder and producer read — the compiled model, its node/network/boundary
deployments, the participant behaviors and action contracts, the terminal snapshot,
and the execution plan. They are structural (no ``isinstance`` use), so they give a
more specific type than ``Any`` *without* importing the concrete ``aces_processor``
model classes, which ADR-036 walls off from ``aces_operations``. ``BackendManifest``
is imported from the allowed pure-capabilities module.

Kept in a separate module so ``_evidence_run_artifact`` stays under the ADR-015
source-size cap.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from aces_backend_protocols.capabilities import BackendManifest

__all__ = [
    "ActionContract",
    "BackendManifest",
    "CompiledModel",
    "EvidenceArtifactInputs",
    "EvidenceCheck",
    "EvidenceSourceMode",
    "ExecutionPlan",
    "LibvirtEvidenceRunConfig",
    "NodeDeployment",
    "ObservationBoundary",
    "ParticipantBehavior",
    "RealizedNetwork",
    "TerminalSnapshot",
]

EvidenceSourceMode = Literal["deterministic", "native-live", "guest-certified"]


@dataclass(frozen=True)
class EvidenceCheck:
    """One named check over the scenario-evidence production run.

    Every check is gating: it contributes to ``LibvirtEvidenceRunReport.passed``.
    There is deliberately no non-gating escape hatch — in particular, a native-live
    run that fails to realize the libvirt substrate must report ``passed=False`` so
    the mode can never claim success without actually realizing.
    """

    name: str
    passed: bool
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class LibvirtEvidenceRunConfig:
    """Runtime controls for the libvirt scenario-evidence producer."""

    evidence_source_mode: EvidenceSourceMode = "deterministic"
    connection_uri: str = "qemu:///system"


class ActionContract(Protocol):
    """Compiled action contract surface read by the proof builder."""

    spec: Mapping[str, Any]


class ParticipantBehavior(Protocol):
    """Compiled participant behavior surface read by the lifecycle/proof builders."""

    observation_boundary_addresses: Sequence[str]
    action_contract_addresses: Sequence[str]


class ObservationBoundary(Protocol):
    """Compiled observation boundary surface read by the boundary/admission builders."""

    spec: Mapping[str, Any] | None
    view_transitions: Sequence[Any]


class NodeDeployment(Protocol):
    """Compiled node-deployment surface read by the topology builder."""

    address: str
    name: str
    node_type: str | None
    os_family: str | None
    spec: Mapping[str, Any]


class RealizedNetwork(Protocol):
    """Compiled network surface read by the topology builder."""

    address: str
    name: str
    spec: Mapping[str, Any]


class CompiledModel(Protocol):
    """The compiled runtime model exposed via ``ExecutionPlan.model``."""

    scenario_name: str
    participant_behaviors: Mapping[str, ParticipantBehavior]
    action_contracts: Mapping[str, ActionContract]
    observation_boundaries: Mapping[str, ObservationBoundary]
    objectives: Mapping[str, Any]
    evaluations: Mapping[str, Any]
    networks: Mapping[str, RealizedNetwork]
    node_deployments: Mapping[str, NodeDeployment]


class TerminalSnapshot(Protocol):
    """Terminal control-plane snapshot surface read by the observation builders."""

    participant_episode_results: Mapping[str, Any]
    participant_behavior_history: Mapping[str, Any]


class ExecutionPlan(Protocol):
    """The runtime execution plan returned by ``RuntimeManager.plan``."""

    model: CompiledModel
    manifest: BackendManifest
    provisioning: object
    diagnostics: Sequence[Any]


@dataclass(frozen=True)
class EvidenceArtifactInputs:
    """Bundled inputs for ``assemble_artifact`` (keeps the builder to one parameter)."""

    scenario_path: Path
    run_id: str
    recorded_at: str
    mode: str
    model: CompiledModel
    manifest: BackendManifest
    proof: Mapping[str, Any]
    native_snapshot: Mapping[str, Any] | None
    native_cleanup_verified: bool | None
    unrealized_capabilities: tuple[str, ...] = ()
    guest_observed: Mapping[str, Any] | None = None
