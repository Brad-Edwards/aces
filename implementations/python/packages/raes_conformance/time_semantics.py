"""ASR-528 semantic conformance checks for shared-time claims."""

from __future__ import annotations

from raes_backend_protocols.backend_manifest import BackendManifest
from raes_backend_protocols.capability_admission import time_model_capability_gaps
from raes_contracts.contracts.time_model import (
    RealizedTimeModelProvenanceModel,
    TimeModelDeclarationModel,
    TimeRuntimeStateModel,
    validate_realized_time_model,
    validate_time_runtime_state,
)
from raes_contracts.diagnostics import Diagnostic

from raes_conformance.conformance.diagnostics import sanitized_failure_message


def _time_diagnostic(code: str, address: str, message: str) -> Diagnostic:
    return Diagnostic(code=code, domain="time-conformance", address=address, message=message)


def time_model_conformance_diagnostics(
    manifest: BackendManifest,
    declaration: TimeModelDeclarationModel,
    *,
    runtime_state: TimeRuntimeStateModel | None,
    provenance: RealizedTimeModelProvenanceModel | None,
    run_id: str | None = None,
) -> tuple[Diagnostic, ...]:
    """Verify capability, runtime readback, and run disclosure as one claim."""

    diagnostics = [
        _time_diagnostic("conformance.time-capability-gap", "capabilities.time", gap)
        for gap in time_model_capability_gaps(manifest, declaration)
    ]
    if runtime_state is None:
        diagnostics.append(
            _time_diagnostic(
                "conformance.time-runtime-state-missing",
                "runtime.snapshot.time-model-state",
                "time conformance requires typed runtime clock readback",
            )
        )
    else:
        try:
            validate_time_runtime_state(declaration, runtime_state)
        except ValueError as exc:
            diagnostics.append(
                _time_diagnostic(
                    "conformance.time-runtime-state-invalid",
                    "runtime.snapshot.time-model-state",
                    sanitized_failure_message(exc),
                )
            )
    if provenance is None:
        diagnostics.append(
            _time_diagnostic(
                "conformance.realized-time-provenance-missing",
                "experiment.run.realized-time-model",
                "time conformance requires run-scoped realized-time provenance",
            )
        )
    else:
        try:
            validate_realized_time_model(declaration, provenance, run_id=run_id)
        except ValueError as exc:
            diagnostics.append(
                _time_diagnostic(
                    "conformance.realized-time-provenance-invalid",
                    "experiment.run.realized-time-model",
                    sanitized_failure_message(exc),
                )
            )
    return tuple(diagnostics)


__all__ = ["time_model_conformance_diagnostics"]
