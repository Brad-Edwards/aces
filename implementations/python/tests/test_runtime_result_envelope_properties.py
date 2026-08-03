"""Property-based coverage for the portable runtime result/evaluator envelopes (FM2).

Delivers the ``property_based_or_differential_tests`` artifact kind for the
``runtime-contracts`` formal-spec subsystem (``specs/formal/runtime-contracts``,
FM2) recorded in ``specs/formal/assurance-fulfillment.yaml`` (issue #521). Where
``test_workflow_semantics_properties.py`` covers the workflow *rules*, this file
covers the portable *typed envelopes* the runtime-contracts domain owns:

* the typed workflow execution envelope and step execution state
  (``raes_contracts.workflow``), and
* the typed evaluator result envelope (``raes_contracts.evaluation``).

For each envelope the properties are the same shape: any legally constructed
value survives a ``to_payload`` -> ``from_payload`` round-trip unchanged
(structure-preservation), while targeted illegal states are rejected at
construction, and the evaluator contract validator flags exactly the
capability mismatches its rules describe. The round-trip and rejection
guarantees hold across the generated space, not for a single fixture.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from raes_contracts.evaluation import (
    EvaluationExecutionState,
    EvaluationResultContract,
    EvaluationResultStatus,
    validate_evaluation_result,
)
from raes_contracts.workflow import (
    WorkflowCompensationStatus,
    WorkflowExecutionState,
    WorkflowStatus,
    WorkflowStepExecutionState,
    WorkflowStepLifecycle,
    WorkflowStepOutcome,
)

_TIMESTAMP = "2020-01-01T00:00:00Z"
_TERMINAL_STATUSES = (
    WorkflowStatus.SUCCEEDED,
    WorkflowStatus.FAILED,
    WorkflowStatus.CANCELLED,
    WorkflowStatus.TIMED_OUT,
)
_NON_TERMINAL_STATUSES = (WorkflowStatus.PENDING, WorkflowStatus.RUNNING)

# --------------------------------------------------------------------------- #
# Typed workflow step execution state                                         #
# --------------------------------------------------------------------------- #


@st.composite
def _legal_workflow_step_state(draw):
    lifecycle = draw(st.sampled_from(list(WorkflowStepLifecycle)))
    if lifecycle == WorkflowStepLifecycle.PENDING:
        return WorkflowStepExecutionState(lifecycle=lifecycle, outcome=None, attempts=0)
    if lifecycle == WorkflowStepLifecycle.RUNNING:
        return WorkflowStepExecutionState(
            lifecycle=lifecycle,
            outcome=None,
            attempts=draw(st.integers(min_value=0, max_value=5)),
        )
    outcome = draw(st.sampled_from([None, *list(WorkflowStepOutcome)]))
    return WorkflowStepExecutionState(
        lifecycle=lifecycle,
        outcome=outcome,
        attempts=draw(st.integers(min_value=0, max_value=5)),
    )


class TestWorkflowStepEnvelope:
    @given(_legal_workflow_step_state())
    @settings(deadline=None)
    def test_payload_round_trip_is_identity(self, state):
        assert WorkflowStepExecutionState.from_payload(state.to_payload()) == state

    def test_pending_step_with_attempts_is_rejected(self):
        with pytest.raises(ValueError, match="pending workflow steps must report 0 attempts"):
            WorkflowStepExecutionState(lifecycle=WorkflowStepLifecycle.PENDING, attempts=1)

    def test_non_completed_step_with_outcome_is_rejected(self):
        with pytest.raises(ValueError, match="non-completed workflow steps may not report an outcome"):
            WorkflowStepExecutionState(
                lifecycle=WorkflowStepLifecycle.RUNNING,
                outcome=WorkflowStepOutcome.SUCCEEDED,
                attempts=1,
            )

    def test_negative_attempts_are_rejected(self):
        with pytest.raises(ValueError, match="attempts must be >= 0"):
            WorkflowStepExecutionState(lifecycle=WorkflowStepLifecycle.RUNNING, attempts=-1)


# --------------------------------------------------------------------------- #
# Typed workflow execution envelope                                           #
# --------------------------------------------------------------------------- #


@st.composite
def _legal_workflow_execution_state(draw):
    status = draw(st.sampled_from(list(WorkflowStatus)))
    steps = {
        f"step-{index}": draw(_legal_workflow_step_state())
        for index in range(draw(st.integers(min_value=0, max_value=3)))
    }
    if status in _NON_TERMINAL_STATUSES:
        return WorkflowExecutionState(
            workflow_status=status,
            run_id="run-1",
            started_at=_TIMESTAMP,
            updated_at=_TIMESTAMP,
            terminal_reason=None,
            compensation_status=WorkflowCompensationStatus.NOT_REQUIRED,
            steps=steps,
        )
    compensation_status = draw(st.sampled_from(list(WorkflowCompensationStatus)))
    started_at: str | None = None
    updated_at: str | None = None
    failures: list[dict[str, str]] = []
    if compensation_status != WorkflowCompensationStatus.NOT_REQUIRED:
        started_at = _TIMESTAMP
        updated_at = draw(st.sampled_from([None, _TIMESTAMP]))
        failures = draw(st.sampled_from([[], [{"step": "step-0", "reason": "boom"}]]))
    return WorkflowExecutionState(
        workflow_status=status,
        run_id="run-1",
        started_at=_TIMESTAMP,
        updated_at=_TIMESTAMP,
        terminal_reason="terminal",
        compensation_status=compensation_status,
        compensation_started_at=started_at,
        compensation_updated_at=updated_at,
        compensation_failures=failures,
        steps=steps,
    )


class TestWorkflowExecutionEnvelope:
    @given(_legal_workflow_execution_state())
    @settings(deadline=None)
    def test_payload_round_trip_is_identity(self, state):
        assert WorkflowExecutionState.from_payload(state.to_payload()) == state

    def test_terminal_status_requires_terminal_reason(self):
        with pytest.raises(ValueError, match="terminal workflow statuses must include terminal_reason"):
            WorkflowExecutionState(
                workflow_status=WorkflowStatus.SUCCEEDED,
                run_id="run-1",
                started_at=_TIMESTAMP,
                updated_at=_TIMESTAMP,
                terminal_reason=None,
            )

    def test_non_terminal_status_forbids_terminal_reason(self):
        with pytest.raises(ValueError, match="non-terminal workflow statuses may not include terminal_reason"):
            WorkflowExecutionState(
                workflow_status=WorkflowStatus.RUNNING,
                run_id="run-1",
                started_at=_TIMESTAMP,
                updated_at=_TIMESTAMP,
                terminal_reason="early",
            )

    def test_non_terminal_status_forbids_compensation_activity(self):
        with pytest.raises(ValueError, match="non-terminal workflow statuses may not report compensation activity"):
            WorkflowExecutionState(
                workflow_status=WorkflowStatus.RUNNING,
                run_id="run-1",
                started_at=_TIMESTAMP,
                updated_at=_TIMESTAMP,
                compensation_status=WorkflowCompensationStatus.RUNNING,
                compensation_started_at=_TIMESTAMP,
            )

    def test_not_required_compensation_forbids_timestamps(self):
        with pytest.raises(ValueError, match="compensation_status=not_required may not report compensation timestamps"):
            WorkflowExecutionState(
                workflow_status=WorkflowStatus.SUCCEEDED,
                run_id="run-1",
                started_at=_TIMESTAMP,
                updated_at=_TIMESTAMP,
                terminal_reason="terminal",
                compensation_status=WorkflowCompensationStatus.NOT_REQUIRED,
                compensation_started_at=_TIMESTAMP,
            )


# --------------------------------------------------------------------------- #
# Typed evaluator result envelope                                             #
# --------------------------------------------------------------------------- #

_NON_RESULT_EVALUATION_STATUSES = (
    EvaluationResultStatus.PENDING,
    EvaluationResultStatus.RUNNING,
    EvaluationResultStatus.FAILED,
)


@st.composite
def _legal_evaluation_state(draw):
    status = draw(st.sampled_from(list(EvaluationResultStatus)))
    passed: bool | None = None
    score: int | None = None
    max_score: int | None = None
    if status == EvaluationResultStatus.READY:
        report = draw(st.sampled_from(("passed", "score", "both")))
        if report in ("passed", "both"):
            passed = draw(st.booleans())
        if report in ("score", "both"):
            max_score = draw(st.integers(min_value=0, max_value=100))
            score = draw(st.integers(min_value=0, max_value=max_score))
    return EvaluationExecutionState(
        resource_type="goal",
        run_id="run-1",
        status=status,
        observed_at=_TIMESTAMP,
        updated_at=_TIMESTAMP,
        passed=passed,
        score=score,
        max_score=max_score,
    )


class TestEvaluationResultEnvelope:
    @given(_legal_evaluation_state())
    @settings(deadline=None)
    def test_payload_round_trip_is_identity(self, state):
        assert EvaluationExecutionState.from_payload(state.to_payload()) == state

    @given(_legal_evaluation_state())
    @settings(deadline=None)
    def test_capability_matched_contract_reports_no_violations(self, state):
        # A contract whose declared capabilities match what the state reports
        # must accept the state with zero violations across the generated space.
        contract = EvaluationResultContract(
            state_schema_version=state.state_schema_version,
            resource_type=state.resource_type,
            supports_passed=state.passed is not None,
            supports_score=state.score is not None,
            fixed_max_score=state.max_score if state.score is not None else None,
        )
        assert validate_evaluation_result(contract, state) == []

    def test_reporting_passed_without_capability_is_flagged(self):
        state = EvaluationExecutionState(
            resource_type="goal",
            run_id="run-1",
            status=EvaluationResultStatus.READY,
            observed_at=_TIMESTAMP,
            updated_at=_TIMESTAMP,
            passed=True,
        )
        contract = EvaluationResultContract(resource_type="goal", supports_passed=False)
        assert any("may not report 'passed'" in violation for violation in validate_evaluation_result(contract, state))

    def test_reporting_score_without_capability_is_flagged(self):
        state = EvaluationExecutionState(
            resource_type="goal",
            run_id="run-1",
            status=EvaluationResultStatus.READY,
            observed_at=_TIMESTAMP,
            updated_at=_TIMESTAMP,
            score=3,
            max_score=5,
        )
        contract = EvaluationResultContract(resource_type="goal", supports_score=False)
        assert any(
            "may not report score fields" in violation for violation in validate_evaluation_result(contract, state)
        )

    def test_resource_type_mismatch_is_flagged(self):
        state = EvaluationExecutionState(
            resource_type="goal",
            run_id="run-1",
            status=EvaluationResultStatus.PENDING,
            observed_at=_TIMESTAMP,
            updated_at=_TIMESTAMP,
        )
        contract = EvaluationResultContract(resource_type="metric")
        assert any(
            "does not match compiled contract" in violation for violation in validate_evaluation_result(contract, state)
        )
