"""Data contracts for backend-neutral realization conformance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.planning import ProvisioningPlan
from raes_contracts.realization_envelope import RealizationConcern
from raes_contracts.realization_observation import RealizationObservation


class ExecutionBasis(str, Enum):
    """Execution substrate used by one conformance case."""

    FIXTURE_ONLY = "fixture-only"
    HERMETIC_LIVE = "hermetic-live"
    NATIVE_LIVE = "native-live"


class ProbeOutcome(str, Enum):
    """Closed outcome vocabulary for realization probes."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ExpectedRealizationObservation:
    """Independent expected fact projected by the injected harness."""

    address: str
    field_path: str
    concern: RealizationConcern
    value: object


@dataclass(frozen=True)
class RealizationTransformation:
    """One material difference between planned and observed realization."""

    address: str
    concern: RealizationConcern
    kind: str
    disclosed: bool


@dataclass(frozen=True)
class RealizationProbeRequest:
    """Validated probe request supplied to an independent execution harness."""

    probe_digest: str
    probe_kind: str
    payload: dict[str, object]
    negative: bool
    provisioning_plan: ProvisioningPlan | None
    envelope_digest: str
    configuration_digest: str
    observer_version: str


@dataclass(frozen=True)
class RealizationProbeEvidence:
    """Evidence returned by a backend-specific but independently-owned harness."""

    accepted: bool
    accounted_operations: tuple[str, ...] = ()
    changed_addresses: tuple[str, ...] = ()
    expected_observations: tuple[ExpectedRealizationObservation, ...] = ()
    observations: tuple[RealizationObservation, ...] = ()
    transformations: tuple[RealizationTransformation, ...] = ()
    driver_invoked: bool = False
    native_mutated: bool = False
    portable_state_before: str = ""
    portable_state_after: str = ""
    native_state_before: str = ""
    native_state_after: str = ""
    baseline_sequence: int = 0
    cleanup_verified: bool = False
    residual_state: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()


class RealizationConformanceHarness(Protocol):
    """Narrow operations-owned execution, observation, ledger, and cleanup seam."""

    def execute(self, request: RealizationProbeRequest) -> RealizationProbeEvidence:
        """Execute one validated positive or negative probe."""
        ...


@dataclass(frozen=True)
class RealizationProbeCase:
    """One realization probe in the existing backend conformance report."""

    name: str
    contract_name: str
    valid: bool
    passed: bool
    diagnostics: tuple[Diagnostic, ...] = ()
    execution_basis: str = ExecutionBasis.FIXTURE_ONLY.value
    outcome: str = ProbeOutcome.PASSED.value
    probe_kind: str | None = None
    probe_digest: str | None = None
    probe_set_digest: str | None = None
    envelope_digest: str | None = None
    configuration_digest: str | None = None
    target_binding: str | None = None
    expected_operations: tuple[str, ...] = ()
    accounted_operations: tuple[str, ...] = ()
    expected_observation_strengths: tuple[str, ...] = ()
    actual_observation_strengths: tuple[str, ...] = ()
    portable_state_unchanged: bool | None = None
    native_state_unchanged: bool | None = None
    cleanup_verified: bool | None = None
    residual_state: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class RealizationConformanceRun:
    """Internal aggregate returned to ``run_target_conformance``."""

    cases: tuple[RealizationProbeCase, ...] = ()
    probe_set_digest: str | None = None
    target_binding: str | None = None
    native_conformance: bool = False
