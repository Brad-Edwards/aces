"""Reference runtime admission for portable proposition truth results."""

from __future__ import annotations

from copy import deepcopy

from aces_contracts.planning import RuntimeDomain
from aces_contracts.runtime_state import RuntimeSnapshot, SnapshotEntry
from aces_runtime.proposition_truth_contracts import proposition_truth_contract_diagnostics
from test_truth_result_contracts import _observed_result


def _semantic_entries(payload: dict[str, object]) -> dict[str, SnapshotEntry]:
    proposition_address = str(payload["proposition_address"])
    assertion_address = str(payload["assertion_address"])
    polarity = str(payload["assertion_polarity"])
    return {
        proposition_address: SnapshotEntry(
            address=proposition_address,
            domain=RuntimeDomain.EVALUATION,
            resource_type="proposition",
            payload={"name": "service-available", "evaluation_basis": payload["evaluation_basis"]},
        ),
        assertion_address: SnapshotEntry(
            address=assertion_address,
            domain=RuntimeDomain.EVALUATION,
            resource_type="assertion",
            payload={"proposition_address": proposition_address, "polarity": polarity},
        ),
    }


def test_runtime_snapshot_accepts_typed_truth_result_separate_from_lifecycle_result() -> None:
    payload = _observed_result()
    snapshot = RuntimeSnapshot(
        entries=_semantic_entries(payload),
        proposition_truth_results={payload["assertion_address"]: payload},
        evaluation_results={
            "evaluation.objective.restore-service": {
                "state_schema_version": "evaluation-result-state/v1",
                "resource_type": "objective",
                "run_id": "run-42",
                "status": "ready",
                "observed_at": "2026-07-12T08:00:00Z",
                "updated_at": "2026-07-12T08:00:00Z",
                "passed": True,
            }
        },
    )

    assert proposition_truth_contract_diagnostics(snapshot) == []
    assert snapshot.proposition_truth_results != snapshot.evaluation_results


def test_runtime_rejects_truth_result_key_that_hides_assertion_identity() -> None:
    payload = _observed_result()
    snapshot = RuntimeSnapshot(proposition_truth_results={"opaque-result-key": payload})

    diagnostics = proposition_truth_contract_diagnostics(snapshot)
    assert [diagnostic.code for diagnostic in diagnostics] == ["runtime.proposition-truth-contract-invalid"]
    assert "must equal assertion_address" in diagnostics[0].message


def test_runtime_rejects_backend_true_without_required_evidence() -> None:
    payload = deepcopy(_observed_result())
    payload["evidence_refs"] = []
    snapshot = RuntimeSnapshot(proposition_truth_results={payload["assertion_address"]: payload})

    diagnostics = proposition_truth_contract_diagnostics(snapshot)
    assert len(diagnostics) == 1
    assert "evidence_refs" in diagnostics[0].message


def test_runtime_rejects_truth_result_for_unadmitted_semantic_entries() -> None:
    payload = _observed_result()
    snapshot = RuntimeSnapshot(proposition_truth_results={payload["assertion_address"]: payload})

    diagnostics = proposition_truth_contract_diagnostics(snapshot)
    assert {diagnostic.message for diagnostic in diagnostics} == {
        "proposition_address must reference an admitted proposition entry.",
        "assertion_address must reference an admitted assertion entry.",
    }


def test_runtime_rejects_assertion_entry_that_changes_meaning() -> None:
    payload = _observed_result()
    entries = _semantic_entries(payload)
    assertion_address = str(payload["assertion_address"])
    entries[assertion_address] = SnapshotEntry(
        address=assertion_address,
        domain=RuntimeDomain.EVALUATION,
        resource_type="assertion",
        payload={
            "proposition_address": "evaluation.proposition.other",
            "polarity": "negative",
        },
    )
    snapshot = RuntimeSnapshot(
        entries=entries,
        proposition_truth_results={assertion_address: payload},
    )

    diagnostics = proposition_truth_contract_diagnostics(snapshot)
    assert {diagnostic.message for diagnostic in diagnostics} == {
        "assertion entry proposition_address must match the truth result.",
        "assertion entry polarity must match the truth result.",
    }


def test_runtime_rejects_truth_result_that_changes_proposition_basis() -> None:
    payload = _observed_result()
    entries = _semantic_entries(payload)
    proposition_address = str(payload["proposition_address"])
    entries[proposition_address] = SnapshotEntry(
        address=proposition_address,
        domain=RuntimeDomain.EVALUATION,
        resource_type="proposition",
        payload={"name": "service-available", "evaluation_basis": "declared_state"},
    )
    snapshot = RuntimeSnapshot(
        entries=entries,
        proposition_truth_results={payload["assertion_address"]: payload},
    )

    diagnostics = proposition_truth_contract_diagnostics(snapshot)
    assert [diagnostic.message for diagnostic in diagnostics] == [
        "proposition entry evaluation_basis must match the truth result."
    ]
