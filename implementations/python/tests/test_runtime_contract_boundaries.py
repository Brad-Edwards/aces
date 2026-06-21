"""Runtime/backend contract ownership regression tests."""

from __future__ import annotations

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.evaluation import EvaluationResultContract
from aces_contracts.participant_episode import ParticipantEpisodeInitializeRequest
from aces_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from aces_contracts.workflow import WorkflowResultContract
from aces_processor import models


def test_processor_models_reexports_shared_runtime_contracts() -> None:
    assert models.Diagnostic is Diagnostic
    assert models.ApplyResult is ApplyResult
    assert models.RuntimeSnapshot is RuntimeSnapshot
    assert models.WorkflowResultContract is WorkflowResultContract
    assert models.EvaluationResultContract is EvaluationResultContract
    assert models.ParticipantEpisodeInitializeRequest is ParticipantEpisodeInitializeRequest
