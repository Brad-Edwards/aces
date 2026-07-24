"""Authority sets for processor, backend, and participant implementation declarations."""

from __future__ import annotations

from collections.abc import Iterable

PROCESSOR_SUPPORTED_SDL_VERSION_IDS = ("sdl-authoring-input-v1",)

# These are the published processor-facing and live-control-plane contracts a
# processor may honestly claim to support. Concept-authority catalogs, semantic
# profiles, backend manifests, and authoring-side request artifacts are
# separate authority surfaces and do not belong in this declaration field.
PROCESSOR_SUPPORTED_CONTRACT_IDS = (
    "processor-manifest-v2",
    "provisioning-plan-v1",
    "orchestration-plan-v1",
    "evaluation-plan-v1",
    "workflow-cancellation-request-v1",
    "operation-receipt-v1",
    "operation-status-v1",
    "runtime-snapshot-v1",
    "workflow-result-envelope-v1",
    "workflow-history-event-stream-v1",
    "evaluation-result-envelope-v1",
    "proposition-truth-result-v1",
    "evaluation-history-event-stream-v1",
    "participant-episode-state-envelope-v1",
    "participant-episode-history-event-stream-v1",
    "participant-behavior-history-event-stream-v1",
)

# These are the published backend-facing and live-control-plane contracts a
# backend may honestly claim to support. Concept-authority catalogs, semantic
# profiles, processor manifests, and authoring-side request artifacts are
# separate authority surfaces and do not belong in this declaration field.
BACKEND_SUPPORTED_CONTRACT_IDS = (
    "backend-manifest-v2",
    "realization-envelope-v1",
    "provisioning-plan-v1",
    "orchestration-plan-v1",
    "evaluation-plan-v1",
    "operation-receipt-v1",
    "operation-status-v1",
    "runtime-snapshot-v1",
    "workflow-result-envelope-v1",
    "workflow-history-event-stream-v1",
    "evaluation-result-envelope-v1",
    "proposition-truth-result-v1",
    "evaluation-history-event-stream-v1",
    "participant-episode-state-envelope-v1",
    "participant-episode-history-event-stream-v1",
    "participant-behavior-history-event-stream-v1",
    "participant-lifecycle-event-v1",
    "participant-observation-envelope-v1",
    "participant-shared-state-record-v1",
    "participant-joint-action-record-v1",
    "participant-time-management-context-v1",
    "participant-outcome-report-v1",
    "experiment-capture-spec-v1",
    "experiment-evidence-record-v1",
    "experiment-derived-measure-v1",
    "experiment-run-v1",
    "live-activity-profile-v1",
    "live-activity-occurrence-v1",
)

PARTICIPANT_IMPLEMENTATION_SUPPORTED_CONTRACT_IDS = (
    "participant-implementation-manifest-v1",
    "participant-implementation-provenance-v1",
    "participant-episode-state-envelope-v1",
    "participant-episode-history-event-stream-v1",
    "participant-behavior-history-event-stream-v1",
)


def validate_processor_supported_sdl_versions(values: Iterable[str]) -> None:
    _validate_allowed_values(
        "supported_sdl_versions",
        values,
        PROCESSOR_SUPPORTED_SDL_VERSION_IDS,
        "published SDL authoring contract ids",
    )


def validate_processor_supported_contract_versions(values: Iterable[str]) -> None:
    _validate_allowed_values(
        "supported_contract_versions",
        values,
        PROCESSOR_SUPPORTED_CONTRACT_IDS,
        "published processor/runtime contract ids",
    )


def validate_backend_supported_contract_versions(values: Iterable[str]) -> None:
    _validate_allowed_values(
        "supported_contract_versions",
        values,
        BACKEND_SUPPORTED_CONTRACT_IDS,
        "published backend/runtime contract ids",
    )


def validate_participant_implementation_supported_contract_versions(values: Iterable[str]) -> None:
    _validate_allowed_values(
        "supported_contract_versions",
        values,
        PARTICIPANT_IMPLEMENTATION_SUPPORTED_CONTRACT_IDS,
        "published participant implementation contract ids",
    )


def validate_participant_supported_contract_versions(values: Iterable[str]) -> None:
    _validate_allowed_values(
        "supported_participant_contracts",
        values,
        PARTICIPANT_IMPLEMENTATION_SUPPORTED_CONTRACT_IDS,
        "published participant implementation contract ids",
    )


def _validate_allowed_values(
    field_name: str,
    values: Iterable[str],
    allowed_values: tuple[str, ...],
    allowed_label: str,
) -> None:
    materialized = list(values)
    if len(materialized) != len(set(materialized)):
        raise ValueError(f"{field_name} must not contain duplicates")

    allowed = frozenset(allowed_values)
    unknown = sorted(set(materialized) - allowed)
    if unknown:
        declared = ", ".join(unknown)
        raise ValueError(f"{field_name} include values outside the {allowed_label}: {declared}")
