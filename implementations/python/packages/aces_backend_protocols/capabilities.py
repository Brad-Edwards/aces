"""Domain-specific runtime capability declarations."""

from __future__ import annotations

from dataclasses import dataclass, field

from aces_contracts.apparatus import (
    ApparatusIdentity,
    ConceptBinding,
    RealizationSupportDeclaration,
)
from aces_contracts.controlled_vocabularies import validate_controlled_vocabulary_scope_values
from aces_contracts.manifest_authority import validate_backend_supported_contract_versions
from aces_contracts.vocabulary import WorkflowFeature, WorkflowStatePredicateFeature

PARTICIPANT_RUNTIME_ROLE_SCOPE = "capabilities.participant_runtime.supported_participant_roles"
PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE = "capabilities.participant_runtime.supported_behavior_features"
PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE = "capabilities.participant_runtime.supported_interaction_features"

_PARTICIPANT_EPISODE_CONTRACTS = frozenset(
    {
        "participant-episode-state-envelope-v1",
        "participant-episode-history-event-stream-v1",
        "runtime-snapshot-v1",
    }
)
_PARTICIPANT_BEHAVIOR_CONTRACTS = frozenset(
    {
        "participant-behavior-history-event-stream-v1",
        "runtime-snapshot-v1",
    }
)

PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS = {
    PARTICIPANT_RUNTIME_ROLE_SCOPE: {
        "blue": _PARTICIPANT_EPISODE_CONTRACTS,
        "green": _PARTICIPANT_EPISODE_CONTRACTS,
        "red": _PARTICIPANT_EPISODE_CONTRACTS,
        "white": _PARTICIPANT_EPISODE_CONTRACTS,
    },
    PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE: {
        "action_contracts": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "attribution_support": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "behavior_history": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "effects": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "failure_classes": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "observation_boundaries": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "outcome_interpretation": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "preconditions": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "state_transitions": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "temporal_contracts": _PARTICIPANT_BEHAVIOR_CONTRACTS,
    },
    PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE: {
        "contention": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "coordination": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "interference": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "shared_state_change": _PARTICIPANT_BEHAVIOR_CONTRACTS,
    },
}
"""Minimum published contract surfaces needed to make API-405 claims checkable.

The table is intentionally conservative: it does not prove that every backend
implements every action kind. It gives the conformance runner a falsifiable
floor for standard terms, so a manifest cannot claim ACES participant support
while omitting the contracts that carry the corresponding runtime evidence.
"""


@dataclass(frozen=True)
class ProvisionerCapabilities:
    """Provisioning support declaration."""

    name: str
    supported_node_types: frozenset[str] = frozenset()
    supported_os_families: frozenset[str] = frozenset()
    supported_content_types: frozenset[str] = frozenset()
    supported_account_features: frozenset[str] = frozenset()
    max_total_nodes: int | None = None
    supports_acls: bool = False
    supports_accounts: bool = False
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
    supports_condition_refs: bool = True
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


@dataclass(frozen=True)
class ParticipantRuntimeCapabilities:
    """Participant-episode lifecycle support declaration.

    Declaring this capability means the backend exposes the full
    participant episode control surface defined in RUN-311:
    ``initialize``, ``reset``, ``restart``, and ``terminate`` on the
    ``ParticipantRuntime`` protocol, plus the ``status``/``results``/
    ``history`` observation methods. A backend that advertises this
    capability MUST populate ``RuntimeSnapshot.participant_episode_results``
    and ``participant_episode_history`` so downstream consumers see the
    state machine transitions.

    API-405 support dimensions live here because they are backend apparatus
    claims: which participant roles, behavior features, and interaction
    features this participant runtime can actually realize.
    """

    name: str
    supported_participant_roles: frozenset[str] = frozenset()
    supported_behavior_features: frozenset[str] = frozenset()
    supported_interaction_features: frozenset[str] = frozenset()
    constraints: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ParticipantRuntimeCapabilities.name must be non-empty")
        if not self.supported_participant_roles:
            raise ValueError("ParticipantRuntimeCapabilities.supported_participant_roles must not be empty")
        if not self.supported_behavior_features:
            raise ValueError("ParticipantRuntimeCapabilities.supported_behavior_features must not be empty")
        if not self.supported_interaction_features:
            raise ValueError("ParticipantRuntimeCapabilities.supported_interaction_features must not be empty")
        if any(not role.strip() for role in self.supported_participant_roles):
            raise ValueError(
                "ParticipantRuntimeCapabilities.supported_participant_roles must not contain empty strings"
            )
        if any(not feature.strip() for feature in self.supported_behavior_features):
            raise ValueError(
                "ParticipantRuntimeCapabilities.supported_behavior_features must not contain empty strings"
            )
        if any(not feature.strip() for feature in self.supported_interaction_features):
            raise ValueError(
                "ParticipantRuntimeCapabilities.supported_interaction_features must not contain empty strings"
            )
        validate_controlled_vocabulary_scope_values(
            PARTICIPANT_RUNTIME_ROLE_SCOPE,
            self.supported_participant_roles,
        )
        validate_controlled_vocabulary_scope_values(
            PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE,
            self.supported_behavior_features,
        )
        validate_controlled_vocabulary_scope_values(
            PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE,
            self.supported_interaction_features,
        )


@dataclass(frozen=True)
class BackendCapabilitySet:
    """Backend-specific nested capability blocks."""

    provisioner: ProvisionerCapabilities
    orchestrator: OrchestratorCapabilities | None = None
    evaluator: EvaluatorCapabilities | None = None
    participant_runtime: ParticipantRuntimeCapabilities | None = None


@dataclass(frozen=True)
class BackendCompatibility:
    """Backend compatibility claims against processor surfaces."""

    processors: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.processors:
            raise ValueError("BackendCompatibility.processors must not be empty")
        if any(not processor.strip() for processor in self.processors):
            raise ValueError("BackendCompatibility.processors must not contain empty strings")


@dataclass(frozen=True, init=False)
class BackendManifest:
    """Complete runtime target capability declaration."""

    identity: ApparatusIdentity
    supported_contract_versions: frozenset[str]
    compatibility: BackendCompatibility
    realization_support: tuple[RealizationSupportDeclaration, ...]
    concept_bindings: tuple[ConceptBinding, ...]
    constraints: dict[str, str]
    capabilities: BackendCapabilitySet

    def __init__(
        self,
        *,
        identity: ApparatusIdentity | None = None,
        supported_contract_versions: frozenset[str] = frozenset(),
        compatibility: BackendCompatibility | None = None,
        realization_support: tuple[RealizationSupportDeclaration, ...] = (),
        concept_bindings: tuple[ConceptBinding, ...] = (),
        constraints: dict[str, str] | None = None,
        capabilities: BackendCapabilitySet | None = None,
        name: str | None = None,
        version: str = "0.0.0+unknown",
        compatible_processors: frozenset[str] = frozenset(),
        provisioner: ProvisionerCapabilities | None = None,
        orchestrator: OrchestratorCapabilities | None = None,
        evaluator: EvaluatorCapabilities | None = None,
        participant_runtime: ParticipantRuntimeCapabilities | None = None,
    ) -> None:
        if identity is None:
            if name is None:
                raise ValueError("BackendManifest requires either identity or name.")
            identity = ApparatusIdentity(name=name, version=version)
        if compatibility is None:
            compatibility = BackendCompatibility(processors=frozenset(compatible_processors))
        if capabilities is None:
            if provisioner is None:
                raise ValueError("BackendManifest requires either capabilities or provisioner.")
            capabilities = BackendCapabilitySet(
                provisioner=provisioner,
                orchestrator=orchestrator,
                evaluator=evaluator,
                participant_runtime=participant_runtime,
            )
        supported_contract_versions = frozenset(supported_contract_versions)
        if not supported_contract_versions:
            raise ValueError("BackendManifest.supported_contract_versions must not be empty")
        if any(not version.strip() for version in supported_contract_versions):
            raise ValueError("BackendManifest.supported_contract_versions must not contain empty strings")
        validate_backend_supported_contract_versions(supported_contract_versions)
        realization_support = tuple(realization_support)
        if not realization_support:
            raise ValueError("BackendManifest.realization_support must not be empty")
        concept_bindings = tuple(concept_bindings)
        if not concept_bindings:
            raise ValueError("BackendManifest.concept_bindings must not be empty")
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "supported_contract_versions", supported_contract_versions)
        object.__setattr__(self, "compatibility", compatibility)
        object.__setattr__(self, "realization_support", realization_support)
        object.__setattr__(self, "concept_bindings", concept_bindings)
        object.__setattr__(self, "constraints", {} if constraints is None else dict(constraints))
        object.__setattr__(self, "capabilities", capabilities)

    @property
    def name(self) -> str:
        return self.identity.name

    @property
    def version(self) -> str:
        return self.identity.version

    @property
    def compatible_processors(self) -> frozenset[str]:
        return self.compatibility.processors

    @property
    def provisioner(self) -> ProvisionerCapabilities:
        return self.capabilities.provisioner

    @property
    def orchestrator(self) -> OrchestratorCapabilities | None:
        return self.capabilities.orchestrator

    @property
    def evaluator(self) -> EvaluatorCapabilities | None:
        return self.capabilities.evaluator

    @property
    def participant_runtime(self) -> ParticipantRuntimeCapabilities | None:
        return self.capabilities.participant_runtime

    @property
    def has_orchestrator(self) -> bool:
        return self.orchestrator is not None

    @property
    def has_evaluator(self) -> bool:
        return self.evaluator is not None

    @property
    def has_participant_runtime(self) -> bool:
        return self.participant_runtime is not None

    @property
    def evaluator_supported_sections(self) -> frozenset[str]:
        if self.evaluator is None:
            return frozenset()
        return self.evaluator.supported_sections

    @property
    def supports_scoring(self) -> bool:
        return self.evaluator.supports_scoring if self.evaluator is not None else False

    @property
    def supports_objectives(self) -> bool:
        return self.evaluator.supports_objectives if self.evaluator is not None else False


def participant_runtime_capability_contract_gaps(manifest: BackendManifest) -> tuple[str, ...]:
    """Return missing contract surfaces for declared standard API-405 claims.

    Governed extension terms remain valid vocabulary values, but ACES cannot
    know their backend-specific evidence obligations. Standard terms are tied to
    the published contract families that make the claim falsifiable in
    conformance and downstream review.
    """

    participant_runtime = manifest.participant_runtime
    if participant_runtime is None:
        return ()

    declared_terms = {
        PARTICIPANT_RUNTIME_ROLE_SCOPE: participant_runtime.supported_participant_roles,
        PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE: participant_runtime.supported_behavior_features,
        PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE: participant_runtime.supported_interaction_features,
    }
    gaps: list[str] = []
    for scope, terms in declared_terms.items():
        required_by_term = PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[scope]
        for term in sorted(terms):
            required_contracts = required_by_term.get(term)
            if required_contracts is None:
                continue
            missing = sorted(required_contracts - manifest.supported_contract_versions)
            if missing:
                gaps.append(f"{scope}.{term} missing required contracts: {', '.join(missing)}")
    return tuple(gaps)
