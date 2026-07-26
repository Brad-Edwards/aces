"""Published JSON Schema bundle assembly for external RAES contracts."""

from __future__ import annotations

from copy import deepcopy
from functools import cache
from typing import Any

from raes.canonical import InstantiatedScenarioSnapshot
from raes.scenario import InstantiatedScenario, Scenario

from .associated_artifacts import AssociatedArtifactManifestModel
from .catalogs import (
    ConceptFamilyCatalogModel,
    ReferenceModelCatalogModel,
    UcoAlignmentCatalogModel,
)
from .execution_state import (
    EvaluationHistoryEventModel,
    EvaluationResultStateModel,
    InstantiationRequestModel,
    PropositionTruthResultModel,
    WorkflowCancellationRequestModel,
    WorkflowExecutionStateModel,
    WorkflowHistoryEventModel,
)
from .experiment_apparatus import ExperimentApparatusContextModel, ExperimentTaskModel
from .experiment_bindings import (
    ExperimentBindingDescriptorSetModel,
    ParticipantConfigurationResultModel,
)
from .experiment_capture import ExperimentCaptureSpecModel
from .experiment_evidence import ExperimentDerivedMeasureModel, ExperimentEvidenceRecordModel
from .experiment_run import ExperimentRunModel
from .experiment_spec import ExperimentSpecModel, ExperimentStudyModel
from .manifests import ProcessorManifestV2Model
from .participant_context import ParticipantContextViewModel
from .participant_control import ParticipantControlOccurrenceModel
from .participant_decision_surface import ParticipantDecisionSurfaceModel
from .participant_envelopes import (
    ParticipantJointActionRecordModel,
    ParticipantLifecycleEventModel,
    ParticipantObservationEnvelopeModel,
    ParticipantSharedStateRecordModel,
    ParticipantTimeManagementContextModel,
)
from .participant_manifests import (
    BackendManifestV2Model,
    ParticipantImplementationManifestModel,
    ParticipantImplementationProvenanceModel,
)
from .participant_runtime import (
    ParticipantBehaviorHistoryEventModel,
    ParticipantEpisodeHistoryEventModel,
    ParticipantEpisodeStateModel,
)
from .participant_views import (
    ParticipantHistoryViewModel,
    ParticipantOutcomeReportModel,
    ParticipantStatusViewModel,
)
from .random_stream import RandomStreamProfileModel, RandomStreamVectorModel
from .realization_plans import (
    EvaluationPlanModel,
    OperationReceiptModel,
    OperationStatusModel,
    OrchestrationPlanModel,
    ProvisioningPlanModel,
    RuntimeSnapshotEnvelopeModel,
)
from .reusable_assets import (
    ReusableAssetTrustPolicyModel,
    _backend_profile_schema_for_bundle,
    _event_stream_schema,
)
from .runtime_facts import RuntimeFactBindingPlaneModel
from .schema_constraints import (
    _aces_semantic_invariant_profile_schema_for_bundle,
    _attach_compiled_address_map_constraints,
    _attach_instantiation_invariants,
    _attach_json_schema_metadata,
    _attach_plan_identity_constraints,
    _attach_sdl_identifier_constraints,
    _validate_aces_semantic_invariant_annotations,
)
from .schema_invariants import (
    _add_aces_invariant,
    _attach_aces_semantic_profile,
    _attach_experiment_datetime_invariants,
    _attach_initial_service_state_invariants,
    _attach_stateful_resource_invariants,
)
from .semantic_profiles import SemanticProfileModel
from .time_model import RealizedTimeModelProvenanceModel, TimeModelDeclarationModel, TimeRuntimeStateModel
from .trial_cleanup import SchedulerIsolationProofModel, TrialCleanupPlanModel, TrialCleanupReceiptModel
from .validation_disclosure import ValidationBasisDisclosureDocumentModel
from .vocabulary_sources import (
    AtlasTacticsSourceModel,
    AttackEnterpriseTacticsSourceModel,
    ControlledVocabularyCatalogModel,
    NistCsfDefensiveCategorySourceModel,
)


def _raw_schema_bundle() -> dict[str, dict[str, Any]]:
    from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel

    from ..behavioral_relations import BehavioralRelationCatalogModel
    from ..exploit_path import ExploitPathAnalysisEvidenceModel
    from ..provenance import SDLLineageLedgerModel
    from ..satisfiability import ScenarioSatisfiabilityEvidenceModel
    from ..scientific_completeness import (
        ScientificCompletenessAssessmentModel,
        ScientificCompletenessTaxonomyModel,
    )
    from ..validation_profiles import ValidationProfileCatalogModel

    return {
        "aces-semantic-invariants-v1": _aces_semantic_invariant_profile_schema_for_bundle(),
        "sdl-authoring-input-v1": Scenario.model_json_schema(),
        "instantiated-scenario-v1": InstantiatedScenario.model_json_schema(),
        "instantiated-scenario-snapshot-v1": InstantiatedScenarioSnapshot.model_json_schema(),
        "scenario-instantiation-request-v1": InstantiationRequestModel.model_json_schema(),
        "exploit-path-analysis-evidence-v1": ExploitPathAnalysisEvidenceModel.model_json_schema(),
        "scenario-satisfiability-evidence-v1": ScenarioSatisfiabilityEvidenceModel.model_json_schema(),
        "backend-manifest-v2": BackendManifestV2Model.model_json_schema(),
        "realization-envelope-v1": BackendRealizationEnvelopeModel.model_json_schema(),
        "processor-manifest-v2": ProcessorManifestV2Model.model_json_schema(),
        "participant-implementation-manifest-v1": ParticipantImplementationManifestModel.model_json_schema(),
        "participant-implementation-provenance-v1": ParticipantImplementationProvenanceModel.model_json_schema(),
        "concept-families-v1": ConceptFamilyCatalogModel.model_json_schema(),
        "behavioral-relations-v1": BehavioralRelationCatalogModel.model_json_schema(),
        "reference-models-v1": ReferenceModelCatalogModel.model_json_schema(),
        "uco-alignment-v1": UcoAlignmentCatalogModel.model_json_schema(),
        "controlled-vocabularies-v1": ControlledVocabularyCatalogModel.model_json_schema(),
        "attack-enterprise-tactics-source-v1": AttackEnterpriseTacticsSourceModel.model_json_schema(),
        "atlas-tactics-source-v1": AtlasTacticsSourceModel.model_json_schema(),
        "nist-csf-defensive-categories-source-v1": NistCsfDefensiveCategorySourceModel.model_json_schema(),
        "semantic-profile-v1": SemanticProfileModel.model_json_schema(),
        "backend-profile-v1": _backend_profile_schema_for_bundle(),
        "random-stream-profile-v1": RandomStreamProfileModel.model_json_schema(),
        "random-stream-vector-v1": RandomStreamVectorModel.model_json_schema(),
        "experiment-apparatus-context-v1": ExperimentApparatusContextModel.model_json_schema(),
        "experiment-authoring-input-v1": ExperimentSpecModel.model_json_schema(),
        "experiment-binding-descriptors-v1": ExperimentBindingDescriptorSetModel.model_json_schema(),
        "experiment-capture-spec-v1": ExperimentCaptureSpecModel.model_json_schema(),
        "experiment-derived-measure-v1": ExperimentDerivedMeasureModel.model_json_schema(),
        "experiment-evidence-record-v1": ExperimentEvidenceRecordModel.model_json_schema(),
        "experiment-run-v1": ExperimentRunModel.model_json_schema(),
        "experiment-study-v1": ExperimentStudyModel.model_json_schema(),
        "experiment-task-v1": ExperimentTaskModel.model_json_schema(),
        "trial-cleanup-plan-v1": TrialCleanupPlanModel.model_json_schema(),
        "trial-cleanup-receipt-v1": TrialCleanupReceiptModel.model_json_schema(),
        "scheduler-isolation-proof-v1": SchedulerIsolationProofModel.model_json_schema(),
        "time-model-v1": TimeModelDeclarationModel.model_json_schema(),
        "time-runtime-state-v1": TimeRuntimeStateModel.model_json_schema(),
        "realized-time-model-v1": RealizedTimeModelProvenanceModel.model_json_schema(),
        "provisioning-plan-v1": ProvisioningPlanModel.model_json_schema(),
        "orchestration-plan-v1": OrchestrationPlanModel.model_json_schema(),
        "evaluation-plan-v1": EvaluationPlanModel.model_json_schema(),
        "runtime-snapshot-v1": RuntimeSnapshotEnvelopeModel.model_json_schema(),
        "workflow-result-envelope-v1": WorkflowExecutionStateModel.model_json_schema(),
        "workflow-history-event-stream-v1": _event_stream_schema(
            "WorkflowHistoryEventStream",
            WorkflowHistoryEventModel.model_json_schema(),
        ),
        "workflow-cancellation-request-v1": WorkflowCancellationRequestModel.model_json_schema(),
        "evaluation-result-envelope-v1": EvaluationResultStateModel.model_json_schema(),
        "proposition-truth-result-v1": PropositionTruthResultModel.model_json_schema(),
        "sdl-lineage-ledger-v1": SDLLineageLedgerModel.model_json_schema(),
        "scientific-completeness-taxonomy-v1": ScientificCompletenessTaxonomyModel.model_json_schema(),
        "scientific-completeness-assessment-v1": ScientificCompletenessAssessmentModel.model_json_schema(),
        "validation-profile-catalog-v1": ValidationProfileCatalogModel.model_json_schema(),
        "validation-basis-disclosure-v1": ValidationBasisDisclosureDocumentModel.model_json_schema(),
        "evaluation-history-event-stream-v1": _event_stream_schema(
            "EvaluationHistoryEventStream",
            EvaluationHistoryEventModel.model_json_schema(),
        ),
        "participant-episode-state-envelope-v1": ParticipantEpisodeStateModel.model_json_schema(),
        "participant-episode-history-event-stream-v1": _event_stream_schema(
            "ParticipantEpisodeHistoryEventStream",
            ParticipantEpisodeHistoryEventModel.model_json_schema(),
        ),
        "participant-behavior-history-event-stream-v1": _event_stream_schema(
            "ParticipantBehaviorHistoryEventStream",
            ParticipantBehaviorHistoryEventModel.model_json_schema(),
        ),
        "participant-lifecycle-event-v1": ParticipantLifecycleEventModel.model_json_schema(),
        "participant-observation-envelope-v1": ParticipantObservationEnvelopeModel.model_json_schema(),
        "participant-shared-state-record-v1": ParticipantSharedStateRecordModel.model_json_schema(),
        "participant-joint-action-record-v1": ParticipantJointActionRecordModel.model_json_schema(),
        "participant-time-management-context-v1": ParticipantTimeManagementContextModel.model_json_schema(),
        "participant-control-occurrence-v1": ParticipantControlOccurrenceModel.model_json_schema(),
        "participant-outcome-report-v1": ParticipantOutcomeReportModel.model_json_schema(),
        "participant-status-view-v1": ParticipantStatusViewModel.model_json_schema(),
        "participant-history-view-v1": ParticipantHistoryViewModel.model_json_schema(),
        "participant-context-view-v1": ParticipantContextViewModel.model_json_schema(),
        "runtime-fact-binding-plane-v1": RuntimeFactBindingPlaneModel.model_json_schema(),
        "participant-decision-surface-v1": ParticipantDecisionSurfaceModel.model_json_schema(),
        "participant-configuration-result-v1": ParticipantConfigurationResultModel.model_json_schema(),
        "operation-receipt-v1": OperationReceiptModel.model_json_schema(),
        "operation-status-v1": OperationStatusModel.model_json_schema(),
        "associated-artifact-manifest-v1": AssociatedArtifactManifestModel.model_json_schema(),
        "reusable-asset-trust-policy-v1": ReusableAssetTrustPolicyModel.model_json_schema(),
    }


@cache
def _schema_bundle_template() -> dict[str, dict[str, Any]]:
    """Build the immutable-in-practice template used by :func:`schema_bundle`."""

    bundle = _raw_schema_bundle()
    _add_aces_invariant(
        bundle["behavioral-relations-v1"],
        "behavioral-relations-reference-resolution",
        "Relation map keys, bibliography references, claim-surface relation references, and worked-example keys "
        "must resolve exactly inside one taxonomy revision.",
        validator="raes_contracts.behavioral_relations.BehavioralRelationCatalogModel",
        inputs=[{"contract_id": "behavioral-relations-v1", "instance_path": "#"}],
    )
    _add_aces_invariant(
        bundle["experiment-study-v1"],
        "study-behavioral-claim-catalog-resolution",
        "Every study behavioral claim must resolve against the canonical taxonomy revision, include a required "
        "observation projection, and keep bounded evidence out of universal quantifiers.",
        validator="raes_contracts.behavioral_relations.validate_behavioral_claim_binding",
        inputs=[
            {"contract_id": "experiment-study-v1", "instance_path": "#/behavioral_claims"},
            {"contract_id": "behavioral-relations-v1", "instance_path": "#"},
        ],
    )
    _add_aces_invariant(
        bundle["scientific-completeness-taxonomy-v1"],
        "scientific-completeness-taxonomy-rectangular",
        "Concern and profile ids must be unique, and every profile disposition "
        "map must exactly cover the taxonomy concern set.",
        validator="raes_contracts.scientific_completeness.ScientificCompletenessTaxonomyModel",
        inputs=[{"contract_id": "scientific-completeness-taxonomy-v1", "instance_path": "#"}],
    )
    _add_aces_invariant(
        bundle["scientific-completeness-taxonomy-v1"],
        "scientific-completeness-behavioral-claim-resolution",
        "Each profile must carry resolved behavioral claim bindings and disjoint, catalog-resolved nonclaimed "
        "relation ids.",
        validator="raes_contracts.scientific_completeness.CompletenessProfileModel.validate_behavioral_claims",
        inputs=[
            {"contract_id": "scientific-completeness-taxonomy-v1", "instance_path": "#/profiles"},
            {"contract_id": "behavioral-relations-v1", "instance_path": "#"},
        ],
    )
    _add_aces_invariant(
        bundle["scientific-completeness-assessment-v1"],
        "scientific-completeness-assessment-status-evidence",
        "Concern ids must be unique and each delivery status must carry its "
        "required executable evidence, external binding, issue refs, or "
        "exclusion rationale.",
        validator="raes_contracts.scientific_completeness.ScientificCompletenessAssessmentModel",
        inputs=[{"contract_id": "scientific-completeness-assessment-v1", "instance_path": "#"}],
    )
    _add_aces_invariant(
        bundle["runtime-fact-binding-plane-v1"],
        "runtime-fact-binding-references-resolve",
        "Every fact version resolves to a declaration, every binding event resolves to its compiled sink and "
        "optional immutable fact version with matching scope, sensitivity, provenance, redaction, and sink policy, "
        "and every projection exactly matches the immutable version it discloses.",
        validator="raes_contracts.contracts.runtime_facts.RuntimeFactBindingPlaneModel._validate_references",
        inputs=[{"contract_id": "runtime-fact-binding-plane-v1", "instance_path": "#"}],
    )
    _add_aces_invariant(
        bundle["scientific-completeness-assessment-v1"],
        "scientific-completeness-taxonomy-assessment-join",
        "Assessment family, taxonomy revision, and concern ids must exactly "
        "match the joined taxonomy before completeness is computed.",
        validator="raes_contracts.scientific_completeness.evaluate_profile_completeness",
        inputs=[
            {"contract_id": "scientific-completeness-taxonomy-v1", "instance_path": "#"},
            {"contract_id": "scientific-completeness-assessment-v1", "instance_path": "#"},
        ],
    )
    _add_aces_invariant(
        bundle["validation-profile-catalog-v1"],
        "validation-profile-catalog-reference-integrity",
        "Strength ranks and term ids must be unique, profile identities must "
        "be unique, required and optional gates must be disjoint, and every "
        "profile reference must resolve within the catalog.",
        validator=("raes_contracts.validation_profiles.ValidationProfileCatalogModel"),
        inputs=[
            {
                "contract_id": "validation-profile-catalog-v1",
                "instance_path": "#",
            }
        ],
    )
    for contract_id, json_schema in bundle.items():
        _attach_sdl_identifier_constraints(contract_id, json_schema)
        _attach_instantiation_invariants(contract_id, json_schema)
        _attach_experiment_datetime_invariants(contract_id, json_schema)
        _attach_stateful_resource_invariants(contract_id, json_schema)
        _attach_initial_service_state_invariants(contract_id, json_schema)
        _attach_json_schema_metadata(contract_id, json_schema)
        _attach_compiled_address_map_constraints(contract_id, json_schema)
        _attach_plan_identity_constraints(contract_id, json_schema)
        _attach_aces_semantic_profile(contract_id, json_schema)
    known_contract_ids = frozenset(bundle)
    for contract_id, json_schema in bundle.items():
        _validate_aces_semantic_invariant_annotations(
            contract_id=contract_id,
            json_schema=json_schema,
            known_contract_ids=known_contract_ids,
        )
    return bundle


def schema_bundle() -> dict[str, dict[str, Any]]:
    """Return an isolated copy of the repo-published external contract schemas.

    Generating the complete bundle is expensive because it traverses every
    Pydantic contract model and attaches the governed RAES annotations.  The
    generated template is process-stable, so build it once while preserving the
    public function's historical fresh-dictionary semantics for callers.
    """

    return deepcopy(_schema_bundle_template())
