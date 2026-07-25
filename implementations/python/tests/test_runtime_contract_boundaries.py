"""Runtime/backend contract ownership regression tests."""

from __future__ import annotations

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.evaluation import EvaluationResultContract
from raes_contracts.participant_episode import ParticipantEpisodeInitializeRequest
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from raes_contracts.workflow import WorkflowResultContract
from raes_processor import models


def test_processor_models_reexports_shared_runtime_contracts() -> None:
    assert models.Diagnostic is Diagnostic
    assert models.ApplyResult is ApplyResult
    assert models.RuntimeSnapshot is RuntimeSnapshot
    assert models.WorkflowResultContract is WorkflowResultContract
    assert models.EvaluationResultContract is EvaluationResultContract
    assert models.ParticipantEpisodeInitializeRequest is ParticipantEpisodeInitializeRequest
