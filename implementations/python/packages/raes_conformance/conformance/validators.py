"""Contract validator registries and structural payload validation."""

from __future__ import annotations

from raes_contracts.behavioral_relation_profiles import BehavioralRelationProfileModel
from raes_contracts.behavioral_relations import BehavioralRelationCatalogModel
from raes_contracts.contracts import (
    AssociatedArtifactManifestModel,
    BackendManifestV2Model,
    EvaluationHistoryEventModel,
    EvaluationPlanModel,
    EvaluationResultStateModel,
    ExperimentApparatusContextModel,
    ExperimentBindingDescriptorSetModel,
    ExperimentCaptureSpecModel,
    ExperimentDerivedMeasureModel,
    ExperimentEvidenceRecordModel,
    ExperimentRunModel,
    ExperimentSpecModel,
    ExperimentStudyModel,
    ExternalConceptBindingDocumentModel,
    OperationReceiptModel,
    OperationStatusModel,
    OrchestrationPlanModel,
    ParticipantBehaviorHistoryEventModel,
    ParticipantConfigurationResultModel,
    ParticipantControlOccurrenceModel,
    ParticipantCrossingOccurrenceModel,
    ParticipantEpisodeHistoryEventModel,
    ParticipantEpisodeStateModel,
    ParticipantImplementationManifestModel,
    ParticipantImplementationProvenanceModel,
    ParticipantLifecycleEventModel,
    ParticipantObservationEnvelopeModel,
    ParticipantSharedStateRecordModel,
    ProvisioningPlanModel,
    RuntimeFactBindingPlaneModel,
    RuntimeSnapshotEnvelopeModel,
    ValidationBasisDisclosureDocumentModel,
    WorkflowExecutionStateModel,
    WorkflowHistoryEventModel,
)
from raes_contracts.contracts.participant_execution import (
    ParticipantExecutionBindingModel,
    ParticipantExecutionControlRequestModel,
    ParticipantExecutionServiceStateModel,
)
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.participant_opacity import (
    ParticipantOpacityAnalysisEvidenceModel,
    ParticipantOpacityAnalysisInputModel,
    ParticipantOpacityModelCheckEvidenceModel,
    ParticipantOpacityModelCheckInputModel,
)
from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel
from raes_contracts.scientific_completeness import (
    ScientificCompletenessAssessmentModel,
    ScientificCompletenessTaxonomyModel,
)
from raes_contracts.validation_profiles import ValidationProfileCatalogModel

from raes_conformance.conformance.diagnostics import _diagnostic, sanitized_failure_message

_SCHEMA_INVALID_DIAGNOSTIC_CODE = "conformance.schema-invalid"
_MODEL_VALIDATORS = {
    "backend-manifest-v2": BackendManifestV2Model.model_validate,
    "participant-implementation-manifest-v1": ParticipantImplementationManifestModel.model_validate,
    "participant-implementation-provenance-v1": ParticipantImplementationProvenanceModel.model_validate,
    "provisioning-plan-v1": ProvisioningPlanModel.model_validate,
    "orchestration-plan-v1": OrchestrationPlanModel.model_validate,
    "evaluation-plan-v1": EvaluationPlanModel.model_validate,
    "operation-receipt-v1": OperationReceiptModel.model_validate,
    "operation-status-v1": OperationStatusModel.model_validate,
    "runtime-snapshot-v1": RuntimeSnapshotEnvelopeModel.model_validate,
    "runtime-fact-binding-plane-v1": RuntimeFactBindingPlaneModel.model_validate,
    "workflow-result-envelope-v1": WorkflowExecutionStateModel.model_validate,
    "evaluation-result-envelope-v1": EvaluationResultStateModel.model_validate,
    "participant-episode-state-envelope-v1": ParticipantEpisodeStateModel.model_validate,
    "participant-execution-binding-v1": ParticipantExecutionBindingModel.model_validate,
    "participant-execution-control-v1": ParticipantExecutionControlRequestModel.model_validate,
    "participant-execution-service-state-v1": ParticipantExecutionServiceStateModel.model_validate,
    "participant-lifecycle-event-v1": ParticipantLifecycleEventModel.model_validate,
    "participant-observation-envelope-v1": ParticipantObservationEnvelopeModel.model_validate,
    "participant-shared-state-record-v1": ParticipantSharedStateRecordModel.model_validate,
    "participant-control-occurrence-v1": ParticipantControlOccurrenceModel.model_validate,
    "participant-crossing-occurrence-v1": ParticipantCrossingOccurrenceModel.model_validate,
    "experiment-capture-spec-v1": ExperimentCaptureSpecModel.model_validate,
    "experiment-evidence-record-v1": ExperimentEvidenceRecordModel.model_validate,
    "experiment-derived-measure-v1": ExperimentDerivedMeasureModel.model_validate,
    "experiment-run-v1": ExperimentRunModel.model_validate,
    "experiment-binding-descriptors-v1": ExperimentBindingDescriptorSetModel.model_validate,
    "participant-configuration-result-v1": ParticipantConfigurationResultModel.model_validate,
}


_STRUCTURAL_ONLY_VALIDATORS = {
    "associated-artifact-manifest-v1": AssociatedArtifactManifestModel.model_validate,
    "behavioral-relation-profile-v1": BehavioralRelationProfileModel.model_validate,
    "behavioral-relations-v1": BehavioralRelationCatalogModel.model_validate,
    "external-concept-bindings-v1": ExternalConceptBindingDocumentModel.model_validate,
    "experiment-apparatus-context-v1": ExperimentApparatusContextModel.model_validate,
    "experiment-authoring-input-v1": ExperimentSpecModel.model_validate,
    "experiment-study-v1": ExperimentStudyModel.model_validate,
    "realization-envelope-v1": BackendRealizationEnvelopeModel.model_validate,
    "scientific-completeness-assessment-v1": ScientificCompletenessAssessmentModel.model_validate,
    "scientific-completeness-taxonomy-v1": ScientificCompletenessTaxonomyModel.model_validate,
    "validation-profile-catalog-v1": ValidationProfileCatalogModel.model_validate,
    "validation-basis-disclosure-v1": ValidationBasisDisclosureDocumentModel.model_validate,
    "participant-opacity-analysis-input-v1": ParticipantOpacityAnalysisInputModel.model_validate,
    "participant-opacity-analysis-evidence-v1": ParticipantOpacityAnalysisEvidenceModel.model_validate,
    "participant-opacity-model-check-input-v1": ParticipantOpacityModelCheckInputModel.model_validate,
    "participant-opacity-model-check-evidence-v1": ParticipantOpacityModelCheckEvidenceModel.model_validate,
}


_SEMANTIC_CONTEXT_REQUIRED_CONTRACTS = frozenset(
    {
        "associated-artifact-manifest-v1",
        "external-concept-bindings-v1",
    }
)


_EVENT_STREAM_VALIDATORS: dict[str, tuple[type, str]] = {
    "workflow-history-event-stream-v1": (WorkflowHistoryEventModel, "workflow"),
    "evaluation-history-event-stream-v1": (EvaluationHistoryEventModel, "evaluation"),
    "participant-episode-history-event-stream-v1": (
        ParticipantEpisodeHistoryEventModel,
        "participant episode",
    ),
    "participant-behavior-history-event-stream-v1": (
        ParticipantBehaviorHistoryEventModel,
        "participant behavior",
    ),
}


def _validate_event_stream(
    *,
    contract_name: str,
    payload: object,
    model_cls: type,
    event_label: str,
) -> list[Diagnostic]:
    """Validate a published history event stream against one Pydantic model.

    Shared by the workflow, evaluation, and participant-episode history
    event streams so adding a new stream type only requires extending
    ``_EVENT_STREAM_VALIDATORS``.
    """

    if not isinstance(payload, list):
        return [
            _diagnostic(
                _SCHEMA_INVALID_DIAGNOSTIC_CODE,
                contract_name,
                f"{event_label} history payload must be a list",
            )
        ]
    diagnostics: list[Diagnostic] = []
    for index, event in enumerate(payload):
        try:
            model_cls.model_validate(event)
        except Exception as exc:
            diagnostics.append(
                _diagnostic(
                    _SCHEMA_INVALID_DIAGNOSTIC_CODE,
                    f"{contract_name}[{index}]",
                    f"{event_label} history event is invalid: {sanitized_failure_message(exc)}",
                )
            )
    return diagnostics


def _validate_payload(contract_name: str, payload: object) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    validator = _MODEL_VALIDATORS.get(contract_name) or _STRUCTURAL_ONLY_VALIDATORS.get(contract_name)
    if validator is not None:
        try:
            validator(payload)
        except Exception as exc:
            diagnostics.append(
                _diagnostic(
                    _SCHEMA_INVALID_DIAGNOSTIC_CODE,
                    contract_name,
                    f"{contract_name} failed contract validation: {sanitized_failure_message(exc)}",
                )
            )
            return diagnostics
    elif contract_name in _EVENT_STREAM_VALIDATORS:
        diagnostics.extend(
            _validate_event_stream(
                contract_name=contract_name,
                payload=payload,
                model_cls=_EVENT_STREAM_VALIDATORS[contract_name][0],
                event_label=_EVENT_STREAM_VALIDATORS[contract_name][1],
            )
        )
    else:
        diagnostics.append(
            _diagnostic(
                "conformance.contract-unknown",
                contract_name,
                f"No conformance validator is registered for {contract_name}.",
            )
        )
    return diagnostics


def validate_contract_payload(contract_name: str, payload: object) -> tuple[Diagnostic, ...]:
    """Validate one payload through the registered structural contract boundary."""

    return tuple(_validate_payload(contract_name, payload))


def supported_contract_ids() -> tuple[str, ...]:
    """Return the contract ids owned by the conformance validator registry."""

    return tuple(sorted((*_MODEL_VALIDATORS, *_STRUCTURAL_ONLY_VALIDATORS, *_EVENT_STREAM_VALIDATORS)))


def contract_payload_root(contract_name: str) -> str | None:
    """Return the required JSON root shape for a registered contract."""

    if contract_name in _EVENT_STREAM_VALIDATORS:
        return "array"
    if contract_name in _MODEL_VALIDATORS or contract_name in _STRUCTURAL_ONLY_VALIDATORS:
        return "object"
    return None


def contract_validation_strength(contract_name: str) -> str | None:
    """Return the strongest context-free validation claim for a contract."""

    if contract_name in _SEMANTIC_CONTEXT_REQUIRED_CONTRACTS:
        return "structural-context-required"
    if contract_name in _STRUCTURAL_ONLY_VALIDATORS:
        return "structural"
    if contract_name in _MODEL_VALIDATORS or contract_name in _EVENT_STREAM_VALIDATORS:
        return "semantic"
    return None
