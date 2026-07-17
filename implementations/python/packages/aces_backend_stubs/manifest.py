"""Pure stub backend manifest declaration (issue #609).

This module holds the stub backend's :class:`BackendManifest` factory and its
supporting constants, separated from ``stubs.py`` so callers that only need the
capability *declaration* -- authoring/inspection surfaces such as the
``aces processor plan`` CLI and the MCP dry-run planning tools -- can import the
manifest without dragging the live stub runtime components (and their
``aces_runtime`` dependency) into the process. It imports only the
capability/contract declaration layers; nothing here touches ``aces_runtime``.

``stubs.py`` re-exports :func:`create_stub_manifest` and the ``REFERENCE_*``
constants so its historical public surface is unchanged.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

from aces_backend_protocols.capabilities import (
    PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS,
    PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_ROLE_SCOPE,
    BackendCapabilitySet,
    BackendManifest,
    EvaluatorCapabilities,
    ObservationCapabilities,
    OrchestratorCapabilities,
    ParticipantRuntimeCapabilities,
    ProvisionerCapabilities,
    WorkflowFeature,
    WorkflowStatePredicateFeature,
)
from aces_contracts.apparatus import ConceptBinding, RealizationSupportDeclaration
from aces_contracts.manifest_authority import BACKEND_SUPPORTED_CONTRACT_IDS
from aces_contracts.vocabulary import RealizationSupportMode

REFERENCE_BACKEND_SUPPORTED_CONTRACT_VERSIONS = frozenset(BACKEND_SUPPORTED_CONTRACT_IDS) - {"realization-envelope-v1"}
REFERENCE_PARTICIPANT_ROLES = frozenset(
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_ROLE_SCOPE]
)
REFERENCE_PARTICIPANT_BEHAVIOR_FEATURES = frozenset(
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE]
)
REFERENCE_PARTICIPANT_INTERACTION_FEATURES = frozenset(
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE]
)


def _current_backend_version() -> str:
    try:
        return distribution_version("aces-sdl")
    except PackageNotFoundError:
        return "0.0.0+unknown"


def create_stub_manifest(
    *,
    with_participant_runtime: bool = True,
    with_observation: bool = True,
    **config,
) -> BackendManifest:
    """Return the fully capable stub manifest.

    ``with_participant_runtime=False`` omits the participant runtime
    capability block so legacy tests that construct targets with only
    provisioner/orchestrator/evaluator components still satisfy
    ``registry.target-shape-mismatch`` validation. Production callers
    should leave this at its default.
    """

    del config
    supported_contract_versions = set(REFERENCE_BACKEND_SUPPORTED_CONTRACT_VERSIONS)
    if not with_participant_runtime:
        supported_contract_versions.discard("participant-episode-state-envelope-v1")
        supported_contract_versions.discard("participant-episode-history-event-stream-v1")
        supported_contract_versions.discard("participant-behavior-history-event-stream-v1")
        supported_contract_versions.discard("participant-lifecycle-event-v1")
        supported_contract_versions.discard("participant-observation-envelope-v1")
        supported_contract_versions.discard("participant-shared-state-record-v1")
        supported_contract_versions.discard("participant-joint-action-record-v1")
        supported_contract_versions.discard("participant-time-management-context-v1")
        supported_contract_versions.discard("participant-outcome-report-v1")
    if not with_observation:
        supported_contract_versions.discard("experiment-capture-spec-v1")
        supported_contract_versions.discard("experiment-evidence-record-v1")
        supported_contract_versions.discard("experiment-derived-measure-v1")
        supported_contract_versions.discard("experiment-run-v1")
    concept_bindings = (
        ConceptBinding(scope="capabilities.provisioner.supported_node_types", family="assets"),
        ConceptBinding(scope="capabilities.provisioner.supported_os_families", family="assets"),
        ConceptBinding(scope="capabilities.provisioner.supported_content_types", family="tools-and-artifacts"),
        ConceptBinding(scope="capabilities.provisioner.supported_account_features", family="identities"),
        ConceptBinding(scope="capabilities.provisioner.supported_domain_profiles", family="identities"),
        ConceptBinding(scope="capabilities.orchestrator.supported_sections", family="actions-and-events"),
        ConceptBinding(scope="capabilities.evaluator.supported_sections", family="observables"),
    )
    if with_participant_runtime:
        concept_bindings += (
            ConceptBinding(
                scope="capabilities.participant_runtime.supported_participant_roles",
                family="identities",
            ),
            ConceptBinding(
                scope="capabilities.participant_runtime.supported_behavior_features",
                family="actions-and-events",
            ),
            ConceptBinding(
                scope="capabilities.participant_runtime.supported_interaction_features",
                family="relationships",
            ),
        )
    if with_observation:
        concept_bindings += (
            ConceptBinding(
                scope="capabilities.observation.supported_capture_kinds",
                family="provenance-and-evidence",
            ),
            ConceptBinding(
                scope="capabilities.observation.supported_channel_kinds",
                family="apparatus-declarations",
            ),
            ConceptBinding(
                scope="capabilities.observation.supported_sealing_modes",
                family="provenance-and-evidence",
            ),
        )
    return BackendManifest(
        name="stub",
        version=_current_backend_version(),
        supported_contract_versions=frozenset(supported_contract_versions),
        compatible_processors=frozenset({"aces-reference-processor"}),
        concept_bindings=concept_bindings,
        realization_support=(
            RealizationSupportDeclaration(
                domain="runtime-realization",
                support_mode=RealizationSupportMode.CONSTRAINED,
                supported_constraint_kinds=frozenset(
                    {
                        "node-type",
                        "os-family",
                        "content-type",
                        "account-feature",
                        "workflow-feature",
                        "workflow-state-predicate",
                    }
                ),
                supported_exact_requirement_kinds=frozenset({"declared-capability-match"}),
                disclosure_kinds=frozenset(
                    {
                        "backend-manifest-v2",
                        "runtime-snapshot-v1",
                        "operation-status-v1",
                    }
                ),
            ),
        ),
        capabilities=BackendCapabilitySet(
            provisioner=ProvisionerCapabilities(
                name="stub-provisioner",
                supported_node_types=frozenset({"vm", "switch"}),
                supported_os_families=frozenset({"linux", "windows", "macos", "freebsd", "other"}),
                supported_content_types=frozenset({"file", "dataset", "directory"}),
                supported_account_features=frozenset(
                    {"groups", "mail", "spn", "shell", "home", "disabled", "auth_method"}
                ),
                supported_domain_profiles=frozenset({"active_directory"}),
                max_total_nodes=None,
                supports_acls=True,
                supports_accounts=True,
                supports_generated_artifacts=True,
                supports_persistent_volumes=True,
            ),
            orchestrator=OrchestratorCapabilities(
                name="stub-orchestrator",
                supported_sections=frozenset({"injects", "events", "scripts", "stories", "workflows"}),
                supports_workflows=True,
                supports_assertion_refs=True,
                supports_inject_bindings=True,
                supported_workflow_features=frozenset(
                    {
                        WorkflowFeature.DECISION,
                        WorkflowFeature.SWITCH,
                        WorkflowFeature.CALL,
                        WorkflowFeature.PARALLEL_BARRIER,
                        WorkflowFeature.RETRY,
                        WorkflowFeature.FAILURE_TRANSITIONS,
                        WorkflowFeature.CANCELLATION,
                        WorkflowFeature.TIMEOUTS,
                        WorkflowFeature.COMPENSATION,
                    }
                ),
                supported_workflow_state_predicates=frozenset(
                    {
                        WorkflowStatePredicateFeature.OUTCOME_MATCHING,
                        WorkflowStatePredicateFeature.ATTEMPT_COUNTS,
                    }
                ),
            ),
            evaluator=EvaluatorCapabilities(
                name="stub-evaluator",
                supported_sections=frozenset({"conditions", "propositions", "assertions", "objectives"}),
                supports_scoring=True,
                supports_objectives=True,
                supported_predicate_families=frozenset({"presence", "boolean", "string", "number"}),
                supported_quantifiers=frozenset({"all", "any", "at_least"}),
                supported_truth_outcomes=frozenset({"true", "false", "unknown", "unsupported"}),
                supported_evidence_channels=frozenset({"log", "api_response", "file_artifact"}),
                supported_time_domains=frozenset({"scenario_time"}),
                preserves_binding_provenance=True,
            ),
            participant_runtime=(
                ParticipantRuntimeCapabilities(
                    name="stub-participant-runtime",
                    supported_participant_roles=REFERENCE_PARTICIPANT_ROLES,
                    supported_behavior_features=REFERENCE_PARTICIPANT_BEHAVIOR_FEATURES,
                    supported_interaction_features=REFERENCE_PARTICIPANT_INTERACTION_FEATURES,
                )
                if with_participant_runtime
                else None
            ),
            observation=(
                ObservationCapabilities(
                    name="stub-observation",
                    supported_capture_kinds=frozenset({"artifact", "log", "observation", "telemetry", "trace"}),
                    supported_channel_kinds=frozenset(
                        {
                            "backend-log",
                            "evaluation-history",
                            "file-artifact",
                            "participant-observation",
                            "runtime-snapshot",
                            "workflow-history",
                        }
                    ),
                    supported_evidence_contracts=frozenset(
                        {
                            "experiment-capture-spec-v1",
                            "experiment-evidence-record-v1",
                            "experiment-derived-measure-v1",
                            "experiment-run-v1",
                        }
                    ),
                    supported_media_types=frozenset({"application/json", "text/plain"}),
                    supported_sealing_modes=frozenset({"digest", "immutable-store"}),
                    supports_redaction=True,
                    supports_loss_disclosure=True,
                    supports_chain_of_custody=False,
                )
                if with_observation
                else None
            ),
        ),
    )
