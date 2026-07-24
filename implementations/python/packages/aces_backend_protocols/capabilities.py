"""Domain-specific runtime capability declarations."""

from dataclasses import dataclass, field

from aces_contracts.controlled_vocabularies import validate_controlled_vocabulary_scope_values
from aces_contracts.manifest_authority import validate_backend_supported_contract_versions
from aces_contracts.vocabulary import WorkflowFeature, WorkflowStatePredicateFeature

from . import participant_capabilities as _participant_capabilities
from . import time_capabilities as _time_capabilities

PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE = _participant_capabilities.PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE
PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS = (
    _participant_capabilities.PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS
)
PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE = _participant_capabilities.PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE
PARTICIPANT_RUNTIME_ROLE_SCOPE = _participant_capabilities.PARTICIPANT_RUNTIME_ROLE_SCOPE
ParticipantFeatureSupport = _participant_capabilities.ParticipantFeatureSupport
ParticipantRuntimeCapabilities = _participant_capabilities.ParticipantRuntimeCapabilities
TIME_CAPABILITY_REQUIRED_CONTRACTS = _time_capabilities.TIME_CAPABILITY_REQUIRED_CONTRACTS
TimeCapabilities = _time_capabilities.TimeCapabilities

OBSERVATION_CAPABILITY_CAPTURE_KIND_SCOPE = "capabilities.observation.supported_capture_kinds"
OBSERVATION_CAPABILITY_CHANNEL_KIND_SCOPE = "capabilities.observation.supported_channel_kinds"
OBSERVATION_CAPABILITY_SEALING_MODE_SCOPE = "capabilities.observation.supported_sealing_modes"
PROVISIONER_DOMAIN_PROFILE_SCOPE = "capabilities.provisioner.supported_domain_profiles"

OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS = frozenset(
    {
        "experiment-capture-spec-v1",
        "experiment-evidence-record-v1",
        "experiment-derived-measure-v1",
        "experiment-run-v1",
    }
)

CLEANUP_CAPABILITY_REQUIRED_CONTRACTS = frozenset({"trial-cleanup-plan-v1", "trial-cleanup-receipt-v1"})
_CLEANUP_ACTION_KINDS = frozenset({"destroy", "reset", "restore", "compensate", "verify", "custom"})


@dataclass(frozen=True)
class ProvisionerCapabilities:
    name: str
    supported_node_types: frozenset[str] = frozenset()
    supported_os_families: frozenset[str] = frozenset()
    supported_content_types: frozenset[str] = frozenset()
    supported_account_features: frozenset[str] = frozenset()
    supported_domain_profiles: frozenset[str] = frozenset()
    max_total_nodes: int | None = None
    supports_acls: bool = False
    supports_accounts: bool = False
    supports_generated_artifacts: bool = False
    supports_persistent_volumes: bool = False
    constraints: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ProvisionerCapabilities.name must be non-empty")
        if not self.supported_node_types:
            raise ValueError("ProvisionerCapabilities.supported_node_types must not be empty")
        if any(not node_type.strip() for node_type in self.supported_node_types):
            raise ValueError("ProvisionerCapabilities.supported_node_types must not contain empty strings")
        if not self.supported_os_families:
            raise ValueError("ProvisionerCapabilities.supported_os_families must not be empty")
        if any(not os_family.strip() for os_family in self.supported_os_families):
            raise ValueError("ProvisionerCapabilities.supported_os_families must not contain empty strings")
        if any(not content_type.strip() for content_type in self.supported_content_types):
            raise ValueError("ProvisionerCapabilities.supported_content_types must not contain empty strings")
        if any(not feature.strip() for feature in self.supported_account_features):
            raise ValueError("ProvisionerCapabilities.supported_account_features must not contain empty strings")
        if any(not profile.strip() for profile in self.supported_domain_profiles):
            raise ValueError("ProvisionerCapabilities.supported_domain_profiles must not contain empty strings")
        validate_controlled_vocabulary_scope_values(
            "capabilities.provisioner.supported_node_types",
            self.supported_node_types,
        )
        validate_controlled_vocabulary_scope_values(
            "capabilities.provisioner.supported_os_families",
            self.supported_os_families,
        )
        validate_controlled_vocabulary_scope_values(
            "capabilities.provisioner.supported_content_types",
            self.supported_content_types,
        )
        validate_controlled_vocabulary_scope_values(
            "capabilities.provisioner.supported_account_features",
            self.supported_account_features,
        )
        validate_controlled_vocabulary_scope_values(
            PROVISIONER_DOMAIN_PROFILE_SCOPE,
            self.supported_domain_profiles,
        )
        if self.max_total_nodes is not None and self.max_total_nodes < 1:
            raise ValueError("ProvisionerCapabilities.max_total_nodes must be positive when provided")
        if self.supports_accounts and not self.supported_account_features:
            raise ValueError("ProvisionerCapabilities that support accounts must declare supported_account_features")
        if not self.supports_accounts and self.supported_account_features:
            raise ValueError("supported_account_features require supports_accounts=True")


@dataclass(frozen=True)
class OrchestratorCapabilities:
    """Orchestration support declaration."""

    name: str
    supported_sections: frozenset[str] = frozenset()
    supports_workflows: bool = False
    supports_assertion_refs: bool = True
    supports_inject_bindings: bool = True
    supported_workflow_features: frozenset[WorkflowFeature] = frozenset()
    supported_workflow_state_predicates: frozenset[WorkflowStatePredicateFeature] = frozenset()
    constraints: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("OrchestratorCapabilities.name must be non-empty")
        if not self.supported_sections:
            raise ValueError("OrchestratorCapabilities.supported_sections must not be empty")
        if any(not section.strip() for section in self.supported_sections):
            raise ValueError("OrchestratorCapabilities.supported_sections must not contain empty strings")
        validate_controlled_vocabulary_scope_values(
            "capabilities.orchestrator.supported_sections",
            self.supported_sections,
        )
        if self.supports_workflows:
            if "workflows" not in self.supported_sections:
                raise ValueError(
                    "OrchestratorCapabilities that support workflows must include 'workflows' in supported_sections"
                )
            if not self.supported_workflow_features:
                raise ValueError(
                    "OrchestratorCapabilities that support workflows must declare supported_workflow_features"
                )
        else:
            if "workflows" in self.supported_sections:
                raise ValueError("'workflows' in supported_sections requires supports_workflows=True")
            if self.supported_workflow_features:
                raise ValueError("supported_workflow_features require supports_workflows=True")
            if self.supported_workflow_state_predicates:
                raise ValueError("supported_workflow_state_predicates require supports_workflows=True")


@dataclass(frozen=True)
class EvaluatorCapabilities:
    """Evaluation support declaration."""

    name: str
    supported_sections: frozenset[str] = frozenset()
    supports_scoring: bool = True
    supports_objectives: bool = True
    supported_predicate_families: frozenset[str] = frozenset()
    supported_quantifiers: frozenset[str] = frozenset()
    supported_truth_outcomes: frozenset[str] = frozenset()
    supported_evidence_channels: frozenset[str] = frozenset()
    supported_time_domains: frozenset[str] = frozenset()
    preserves_binding_provenance: bool = False
    constraints: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("EvaluatorCapabilities.name must be non-empty")
        if not self.supported_sections:
            raise ValueError("EvaluatorCapabilities.supported_sections must not be empty")
        if any(not section.strip() for section in self.supported_sections):
            raise ValueError("EvaluatorCapabilities.supported_sections must not contain empty strings")
        validate_controlled_vocabulary_scope_values(
            "capabilities.evaluator.supported_sections",
            self.supported_sections,
        )
        if not self.supports_scoring and not self.supports_objectives:
            raise ValueError("EvaluatorCapabilities must support scoring, objectives, or both")
        self._validate_proposition_support()

    def _validate_proposition_support(self) -> None:
        proposition_sections = {"propositions", "assertions"}
        if not proposition_sections.intersection(self.supported_sections):
            return
        if not proposition_sections.issubset(self.supported_sections):
            raise ValueError("Evaluator proposition support requires both propositions and assertions sections")
        if not self.supported_predicate_families or not self.supported_quantifiers:
            raise ValueError("Evaluator proposition support requires predicate families and quantifiers")
        portable_outcomes = {"true", "false", "unknown", "unsupported"}
        if set(self.supported_truth_outcomes) != portable_outcomes:
            raise ValueError("Evaluator proposition support requires all portable truth outcomes")
        if not self.supported_evidence_channels or not self.supported_time_domains:
            raise ValueError("Evaluator proposition support requires evidence channels and time domains")
        if not self.preserves_binding_provenance:
            raise ValueError("Evaluator proposition support requires binding provenance")


def _validate_unique_non_empty_strings(field_name: str, values: tuple[str, ...]) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{field_name} must not contain empty strings")
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must not contain duplicate values")


@dataclass(frozen=True)
class ObservationCapabilities:
    """Backend observation and evidence-collection support declaration (EXP-715)."""

    name: str
    supported_capture_kinds: frozenset[str] = frozenset()
    supported_channel_kinds: frozenset[str] = frozenset()
    supported_evidence_contracts: frozenset[str] = frozenset()
    supported_media_types: frozenset[str] = frozenset()
    supported_sealing_modes: frozenset[str] = frozenset()
    supports_redaction: bool = False
    supports_loss_disclosure: bool = False
    supports_chain_of_custody: bool = False
    constraints: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ObservationCapabilities.name must be non-empty")
        _validate_unique_non_empty_strings(
            "ObservationCapabilities.supported_capture_kinds", self.supported_capture_kinds
        )
        _validate_unique_non_empty_strings(
            "ObservationCapabilities.supported_channel_kinds", self.supported_channel_kinds
        )
        _validate_unique_non_empty_strings(
            "ObservationCapabilities.supported_evidence_contracts",
            self.supported_evidence_contracts,
        )
        _validate_unique_non_empty_strings("ObservationCapabilities.supported_media_types", self.supported_media_types)
        _validate_unique_non_empty_strings(
            "ObservationCapabilities.supported_sealing_modes", self.supported_sealing_modes
        )
        if not self.supported_capture_kinds:
            raise ValueError("ObservationCapabilities.supported_capture_kinds must not be empty")
        if not self.supported_channel_kinds:
            raise ValueError("ObservationCapabilities.supported_channel_kinds must not be empty")
        if not self.supported_evidence_contracts:
            raise ValueError("ObservationCapabilities.supported_evidence_contracts must not be empty")
        if not self.supported_media_types:
            raise ValueError("ObservationCapabilities.supported_media_types must not be empty")
        if not self.supported_sealing_modes:
            raise ValueError("ObservationCapabilities.supported_sealing_modes must not be empty")
        validate_controlled_vocabulary_scope_values(
            OBSERVATION_CAPABILITY_CAPTURE_KIND_SCOPE,
            self.supported_capture_kinds,
        )
        validate_controlled_vocabulary_scope_values(
            OBSERVATION_CAPABILITY_CHANNEL_KIND_SCOPE,
            self.supported_channel_kinds,
        )
        validate_controlled_vocabulary_scope_values(
            OBSERVATION_CAPABILITY_SEALING_MODE_SCOPE,
            self.supported_sealing_modes,
        )
        validate_backend_supported_contract_versions(self.supported_evidence_contracts)
        for contract_id in self.supported_evidence_contracts:
            if not contract_id.startswith("experiment-"):
                raise ValueError("ObservationCapabilities.supported_evidence_contracts must be experiment contracts")


@dataclass(frozen=True)
class CleanupCapabilities:
    """Backend support for portable cleanup intent, receipts, and verification."""

    name: str
    supported_contract_versions: frozenset[str] = frozenset()
    supported_action_kinds: frozenset[str] = frozenset()
    supported_verification_methods: frozenset[str] = frozenset()
    supports_reusable_state: bool = False
    supports_residual_state_disclosure: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("CleanupCapabilities.name must be non-empty")
        _validate_unique_non_empty_strings(
            "CleanupCapabilities.supported_contract_versions", self.supported_contract_versions
        )
        _validate_unique_non_empty_strings("CleanupCapabilities.supported_action_kinds", self.supported_action_kinds)
        _validate_unique_non_empty_strings(
            "CleanupCapabilities.supported_verification_methods", self.supported_verification_methods
        )
        if self.supported_contract_versions != CLEANUP_CAPABILITY_REQUIRED_CONTRACTS:
            raise ValueError(
                "CleanupCapabilities.supported_contract_versions must contain trial-cleanup-plan-v1 "
                "and trial-cleanup-receipt-v1"
            )
        validate_backend_supported_contract_versions(self.supported_contract_versions)
        unknown_actions = sorted(self.supported_action_kinds - _CLEANUP_ACTION_KINDS)
        if unknown_actions:
            raise ValueError(
                f"CleanupCapabilities.supported_action_kinds contains unknown values: {', '.join(unknown_actions)}"
            )
        if not self.supported_action_kinds:
            raise ValueError("CleanupCapabilities.supported_action_kinds must not be empty")
        if not self.supported_verification_methods:
            raise ValueError("CleanupCapabilities.supported_verification_methods must not be empty")
        if self.supports_reusable_state and not self.supports_residual_state_disclosure:
            raise ValueError("CleanupCapabilities reusable-state support requires residual-state disclosure")


@dataclass(frozen=True)
class BackendCapabilitySet:
    """Backend-specific nested capability blocks."""

    provisioner: ProvisionerCapabilities
    orchestrator: OrchestratorCapabilities | None = None
    evaluator: EvaluatorCapabilities | None = None
    participant_runtime: ParticipantRuntimeCapabilities | None = None
    observation: ObservationCapabilities | None = None
    cleanup: CleanupCapabilities | None = None
    time: TimeCapabilities | None = None


def __getattr__(name: str) -> object:
    """Preserve the historical manifest imports without a circular import."""

    if name in {"BackendCompatibility", "BackendManifest"}:
        from . import backend_manifest

        return getattr(backend_manifest, name)
    if name in {
        "observation_capability_contract_gaps",
        "participant_autonomous_execution_capability_gaps",
        "participant_runtime_capability_contract_gaps",
        "require_cleanup_plan_capability",
        "require_time_model_capability",
        "time_capability_contract_gaps",
        "time_model_capability_gaps",
    }:
        from . import capability_admission

        return getattr(capability_admission, name)
    raise AttributeError(name)
