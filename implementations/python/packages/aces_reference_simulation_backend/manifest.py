"""Backend manifest for the reference simulation backend (RUN-315)."""

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
    OrchestratorCapabilities,
    ParticipantRuntimeCapabilities,
    ProvisionerCapabilities,
    WorkflowFeature,
    WorkflowStatePredicateFeature,
)
from aces_contracts.apparatus import ConceptBinding, RealizationSupportDeclaration
from aces_contracts.manifest_authority import BACKEND_SUPPORTED_CONTRACT_IDS
from aces_contracts.vocabulary import RealizationSupportMode

REFERENCE_SIMULATION_BACKEND_NAME = "reference-simulation"

_PARTICIPANT_ROLES = frozenset(PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_ROLE_SCOPE])
_PARTICIPANT_BEHAVIOR_FEATURES = frozenset(
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE]
)
_PARTICIPANT_INTERACTION_FEATURES = frozenset(
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE]
)


def _current_backend_version() -> str:
    try:
        return distribution_version("aces-sdl")
    except PackageNotFoundError:
        return "0.0.0+unknown"


def _concept_bindings() -> tuple[ConceptBinding, ...]:
    return (
        ConceptBinding(scope="capabilities.provisioner.supported_node_types", family="assets"),
        ConceptBinding(scope="capabilities.provisioner.supported_os_families", family="assets"),
        ConceptBinding(scope="capabilities.provisioner.supported_content_types", family="tools-and-artifacts"),
        ConceptBinding(scope="capabilities.provisioner.supported_account_features", family="identities"),
        ConceptBinding(scope="capabilities.orchestrator.supported_sections", family="actions-and-events"),
        ConceptBinding(scope="capabilities.evaluator.supported_sections", family="observables"),
        ConceptBinding(scope="capabilities.participant_runtime.supported_participant_roles", family="identities"),
        ConceptBinding(
            scope="capabilities.participant_runtime.supported_behavior_features",
            family="actions-and-events",
        ),
        ConceptBinding(
            scope="capabilities.participant_runtime.supported_interaction_features",
            family="relationships",
        ),
    )


def _realization_support() -> tuple[RealizationSupportDeclaration, ...]:
    return (
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
    )


def _capabilities() -> BackendCapabilitySet:
    return BackendCapabilitySet(
        provisioner=ProvisionerCapabilities(
            name="reference-simulation-provisioner",
            supported_node_types=frozenset({"vm", "switch"}),
            supported_os_families=frozenset({"linux", "windows", "macos", "freebsd", "other"}),
            supported_content_types=frozenset({"file", "dataset", "directory"}),
            supported_account_features=frozenset({"groups", "mail", "spn", "shell", "home", "disabled", "auth_method"}),
            max_total_nodes=None,
            supports_acls=True,
            supports_accounts=True,
            constraints={
                "realization": "in-process discrete simulation",
                "state_boundary": "portable ACES snapshot entries",
            },
        ),
        orchestrator=OrchestratorCapabilities(
            name="reference-simulation-orchestrator",
            supported_sections=frozenset({"injects", "events", "scripts", "stories", "workflows"}),
            supports_workflows=True,
            supports_condition_refs=True,
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
            constraints={"clock": "simulation_tick"},
        ),
        evaluator=EvaluatorCapabilities(
            name="reference-simulation-evaluator",
            supported_sections=frozenset({"conditions", "metrics", "evaluations", "tlos", "goals", "objectives"}),
            supports_scoring=True,
            supports_objectives=True,
            constraints={"clock": "simulation_tick"},
        ),
        participant_runtime=ParticipantRuntimeCapabilities(
            name="reference-simulation-participant-runtime",
            supported_participant_roles=_PARTICIPANT_ROLES,
            supported_behavior_features=_PARTICIPANT_BEHAVIOR_FEATURES,
            supported_interaction_features=_PARTICIPANT_INTERACTION_FEATURES,
            constraints={"clock": "simulation_tick"},
        ),
    )


def create_reference_simulation_backend_manifest(**config) -> BackendManifest:
    """Return the fully capable reference simulation backend manifest."""

    del config
    return BackendManifest(
        name=REFERENCE_SIMULATION_BACKEND_NAME,
        version=_current_backend_version(),
        supported_contract_versions=frozenset(BACKEND_SUPPORTED_CONTRACT_IDS),
        compatible_processors=frozenset({"aces-reference-processor"}),
        concept_bindings=_concept_bindings(),
        realization_support=_realization_support(),
        constraints={
            "simulation_engine": "in-process-discrete",
            "clock": "simulation_tick",
            "state_boundary": "portable-aces-contracts",
        },
        capabilities=_capabilities(),
    )
