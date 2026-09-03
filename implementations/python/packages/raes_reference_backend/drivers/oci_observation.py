"""Owned OCI compute-substrate readback projection."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.realization_envelope import ObservationStrength, RealizationConcern
from raes_contracts.realization_observation import RealizationObservation

from raes_reference_backend.driver import ContainerHandle
from raes_reference_backend.envelopes import load_reference_realization_envelope

_DOMAIN = "runtime"
_CODE_SUBSTRATE_UNOBSERVED = "reference-backend.driver.compute-substrate-unobserved"


def ownership_fields_match(
    fields: list[str],
    *,
    address: str,
    expected_name: str,
    expected_native_id: str | None,
    workspace: str,
) -> bool:
    """Return whether bounded inspect fields prove current run ownership."""

    native_id, observed_workspace, owned_address, native_name = fields
    return bool(
        native_id
        and (expected_native_id is None or native_id == expected_native_id)
        and observed_workspace == workspace
        and owned_address == address
        and native_name.removeprefix("/") == expected_name
    )


def substrate_observations(
    handles: Sequence[ContainerHandle],
    *,
    runtime: str,
    ownership_readback: Callable[[str], bool],
) -> tuple[tuple[RealizationObservation, ...], tuple[Diagnostic, ...]]:
    """Project bounded observations only for freshly read, owned containers."""

    envelope = load_reference_realization_envelope("oci-container")
    observations: list[RealizationObservation] = []
    diagnostics: list[Diagnostic] = []
    for sequence, handle in enumerate(handles):
        if not handle.realized or not ownership_readback(handle.address):
            diagnostics.append(
                Diagnostic(
                    code=_CODE_SUBSTRATE_UNOBSERVED,
                    domain=_DOMAIN,
                    address=handle.address,
                    message=f"Container runtime did not provide owned daemon readback for '{handle.address}'.",
                    severity=Severity.ERROR,
                )
            )
            continue
        observations.append(
            RealizationObservation(
                address=handle.address,
                field_path="compute-substrate",
                concern=RealizationConcern.COMPUTE_SUBSTRATE,
                source=ObservationStrength.DAEMON_OBSERVED,
                value="operating-system-container",
                envelope_digest=envelope.digest,
                configuration_digest=envelope.configuration.configuration_digest,
                observer_version=f"reference-oci-{runtime}/v1",
                sequence=sequence,
                binding_verified=True,
            )
        )
    return tuple(observations), tuple(diagnostics)


__all__ = ["ownership_fields_match", "substrate_observations"]
