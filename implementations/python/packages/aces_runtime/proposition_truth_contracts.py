"""Runtime admission for portable proposition truth-result envelopes."""

from __future__ import annotations

from aces_contracts.contracts import PropositionTruthResultModel
from aces_contracts.diagnostics import Diagnostic
from aces_contracts.runtime_state import RuntimeSnapshot
from pydantic import ValidationError

from .diagnostics import _failure_diagnostic

_INVALID_CODE = "runtime.proposition-truth-contract-invalid"
_RESULTS_ADDRESS = "runtime.apply.proposition-truth-results"


def _invalid(address: str, message: str) -> Diagnostic:
    return _failure_diagnostic(_INVALID_CODE, address, message)


def _validation_message(exc: ValidationError) -> str:
    error = exc.errors()[0]
    location = ".".join(str(part) for part in error.get("loc", ()))
    prefix = f"{location}: " if location else ""
    return prefix + str(error.get("msg", "invalid proposition truth result"))


def _semantic_entry_diagnostics(
    snapshot: RuntimeSnapshot,
    result: PropositionTruthResultModel,
    address: str,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    proposition_entry = snapshot.entries.get(result.proposition_address)
    if proposition_entry is None or proposition_entry.resource_type != "proposition":
        diagnostics.append(_invalid(address, "proposition_address must reference an admitted proposition entry."))
    elif not isinstance(proposition_entry.payload, dict):
        diagnostics.append(_invalid(address, "admitted proposition entry payload must be a mapping."))
    elif proposition_entry.payload.get("evaluation_basis") != result.evaluation_basis.value:
        diagnostics.append(_invalid(address, "proposition entry evaluation_basis must match the truth result."))

    assertion_entry = snapshot.entries.get(result.assertion_address)
    if assertion_entry is None or assertion_entry.resource_type != "assertion":
        diagnostics.append(_invalid(address, "assertion_address must reference an admitted assertion entry."))
        return diagnostics
    if not isinstance(assertion_entry.payload, dict):
        diagnostics.append(_invalid(address, "admitted assertion entry payload must be a mapping."))
        return diagnostics
    if assertion_entry.payload.get("proposition_address") != result.proposition_address:
        diagnostics.append(_invalid(address, "assertion entry proposition_address must match the truth result."))
    if assertion_entry.payload.get("polarity") != result.assertion_polarity.value:
        diagnostics.append(_invalid(address, "assertion entry polarity must match the truth result."))
    return diagnostics


def proposition_truth_contract_diagnostics(snapshot: RuntimeSnapshot) -> list[Diagnostic]:
    """Return fail-closed diagnostics for all truth results in a snapshot."""

    if not isinstance(snapshot.proposition_truth_results, dict):
        return [_invalid(_RESULTS_ADDRESS, "RuntimeSnapshot.proposition_truth_results must be a dict.")]
    diagnostics: list[Diagnostic] = []
    for result_key, payload in snapshot.proposition_truth_results.items():
        address = result_key if isinstance(result_key, str) and result_key else _RESULTS_ADDRESS
        if not isinstance(result_key, str) or not result_key:
            diagnostics.append(_invalid(_RESULTS_ADDRESS, "Proposition truth result keys must be non-empty strings."))
            continue
        if not isinstance(payload, dict):
            diagnostics.append(_invalid(address, "Proposition truth results must be mappings."))
            continue
        try:
            result = PropositionTruthResultModel.model_validate(payload)
        except ValidationError as exc:
            diagnostics.append(_invalid(address, _validation_message(exc)))
            continue
        if result_key != result.assertion_address:
            diagnostics.append(_invalid(address, "Proposition truth result map key must equal assertion_address."))
            continue
        diagnostics.extend(_semantic_entry_diagnostics(snapshot, result, address))
    return diagnostics


__all__ = ["proposition_truth_contract_diagnostics"]
