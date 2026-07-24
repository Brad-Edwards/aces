"""Backend manifest for the reference emulation backend (RUN-314).

The manifest declares the same evidence-backed contract ids, concept
bindings, realization-support declaration, and capability terms the
non-normative stub declares -- the reference backend emits/validates the
identical portable surface, so its claims are backed by the same shared
models and conformance evidence. The identity (``reference-emulation``)
and capability component names differ; nothing here imports or subclasses
the stub.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

from aces_backend_protocols.capabilities import (
    CLEANUP_CAPABILITY_REQUIRED_CONTRACTS,
    PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS,
    PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_ROLE_SCOPE,
    TIME_CAPABILITY_REQUIRED_CONTRACTS,
    BackendCapabilitySet,
    BackendManifest,
    CleanupCapabilities,
    EvaluatorCapabilities,
    ObservationCapabilities,
    OrchestratorCapabilities,
    ParticipantRuntimeCapabilities,
    ProvisionerCapabilities,
    TimeCapabilities,
    WorkflowFeature,
    WorkflowStatePredicateFeature,
)
from aces_contracts.apparatus import ConceptBinding, RealizationSupportDeclaration
from aces_contracts.manifest_authority import BACKEND_SUPPORTED_CONTRACT_IDS
from aces_contracts.vocabulary import RealizationSupportMode

REFERENCE_BACKEND_NAME = "reference-emulation"
REFERENCE_BACKEND_SUPPORTED_CONTRACT_VERSIONS = frozenset(
    contract_id for contract_id in BACKEND_SUPPORTED_CONTRACT_IDS if contract_id != "realization-envelope-v1"
)
_TIME_DEDICATED_CONTRACT_VERSIONS = frozenset({"time-model-v1", "time-runtime-state-v1", "realized-time-model-v1"})

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


def _concept_bindings(*, with_time: bool) -> tuple[ConceptBinding, ...]:
    bindings = (
        ConceptBinding(scope="capabilities.provisioner.supported_node_types", family="assets"),
        ConceptBinding(scope="capabilities.provisioner.supported_os_families", family="assets"),
        ConceptBinding(scope="capabilities.provisioner.supported_content_types", family="tools-and-artifacts"),
        ConceptBinding(scope="capabilities.provisioner.supported_account_features", family="identities"),
        ConceptBinding(scope="capabilities.provisioner.supported_domain_profiles", family="identities"),
        ConceptBinding(scope="capabilities.orchestrator.supported_sections", family="actions-and-events"),
        ConceptBinding(scope="capabilities.evaluator.supported_sections", family="observables"),
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
    if with_time:
        bindings += (
            ConceptBinding(scope="capabilities.time.supported_domain_kinds", family="time-and-apparatus"),
            ConceptBinding(scope="capabilities.time.supported_authority_kinds", family="time-and-apparatus"),
            ConceptBinding(scope="capabilities.time.supported_advancement_modes", family="time-and-apparatus"),
            ConceptBinding(scope="capabilities.time.supported_synchronization_modes", family="time-and-apparatus"),
            ConceptBinding(scope="capabilities.time.supported_constraint_kinds", family="time-and-apparatus"),
        )
    return bindings


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


def _time_capabilities(*, enabled: bool) -> TimeCapabilities | None:
    if not enabled:
        return None
    return TimeCapabilities(
        name="reference-emulation-time-runtime",
        supported_contract_versions=TIME_CAPABILITY_REQUIRED_CONTRACTS,
        supported_domain_kinds=frozenset({"wall_clock", "monotonic", "simulated", "logical", "external"}),
        supported_authority_kinds=frozenset({"runtime", "backend", "system", "external"}),
        supported_advancement_modes=frozenset({"real_time", "dilated", "stepped", "event_driven", "externally_paced"}),
        supported_synchronization_modes=frozenset({"none", "authority", "barrier", "conservative"}),
        supported_mapping_kinds=frozenset({"identity", "affine_rational"}),
        supported_constraint_kinds=frozenset({"precedence", "duration", "window", "deadline", "cadence"}),
        supported_reset_behaviors=frozenset({"unsupported", "new_segment_zero", "new_segment_preserve_value"}),
        supported_replay_behaviors=frozenset({"unsupported", "restart_from_anchor", "restore_recorded_advances"}),
        supports_pause=True,
        supports_jump=True,
        supports_exact_rational_mappings=True,
        supports_append_only_history=True,
        supports_run_provenance=True,
    )


def _capabilities(*, with_time: bool) -> BackendCapabilitySet:
    return BackendCapabilitySet(
        provisioner=ProvisionerCapabilities(
            name="reference-emulation-provisioner",
            supported_node_types=frozenset({"vm", "switch"}),
            supported_os_families=frozenset({"linux", "windows", "macos", "freebsd", "other"}),
            supported_content_types=frozenset({"file", "dataset", "directory"}),
            supported_account_features=frozenset({"groups", "mail", "shell", "home", "disabled", "auth_method"}),
            supported_domain_profiles=frozenset(),
            max_total_nodes=None,
            supports_acls=False,
            supports_accounts=True,
        ),
        orchestrator=OrchestratorCapabilities(
            name="reference-emulation-orchestrator",
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
            name="reference-emulation-evaluator",
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
        participant_runtime=ParticipantRuntimeCapabilities(
            name="reference-emulation-participant-runtime",
            supported_participant_roles=_PARTICIPANT_ROLES,
            supported_behavior_features=_PARTICIPANT_BEHAVIOR_FEATURES,
            supported_interaction_features=_PARTICIPANT_INTERACTION_FEATURES,
        ),
        observation=ObservationCapabilities(
            name="reference-emulation-observation",
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
        ),
        cleanup=CleanupCapabilities(
            name="reference-emulation-cleanup",
            supported_contract_versions=CLEANUP_CAPABILITY_REQUIRED_CONTRACTS,
            supported_action_kinds=frozenset({"destroy", "reset", "restore", "compensate", "verify"}),
            supported_verification_methods=frozenset({"probe", "receipt"}),
            supports_reusable_state=True,
            supports_residual_state_disclosure=True,
        ),
        time=_time_capabilities(enabled=with_time),
    )


def create_reference_backend_manifest(*, with_time: bool = False, **config) -> BackendManifest:
    """Return the fully capable reference emulation backend manifest.

    Extra ``config`` kwargs (e.g. ``driver``, ``workspace``) flow through
    the registry descriptor to both factories; the manifest factory accepts
    and ignores them.
    """

    del config
    return BackendManifest(
        name=REFERENCE_BACKEND_NAME,
        version=_current_backend_version(),
        supported_contract_versions=(
            REFERENCE_BACKEND_SUPPORTED_CONTRACT_VERSIONS
            if with_time
            else REFERENCE_BACKEND_SUPPORTED_CONTRACT_VERSIONS - _TIME_DEDICATED_CONTRACT_VERSIONS
        ),
        compatible_processors=frozenset({"aces-reference-processor"}),
        concept_bindings=_concept_bindings(with_time=with_time),
        realization_support=_realization_support(),
        capabilities=_capabilities(with_time=with_time),
    )
