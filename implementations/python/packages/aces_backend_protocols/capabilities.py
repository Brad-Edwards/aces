"""Domain-specific runtime capability declarations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from aces_contracts.controlled_vocabularies import validate_controlled_vocabulary_scope_values
from aces_contracts.manifest_authority import validate_backend_supported_contract_versions
from aces_contracts.vocabulary import ParticipantFeatureSupportLevel, WorkflowFeature, WorkflowStatePredicateFeature

from .provisioner_capabilities import ProvisionerCapabilities

if TYPE_CHECKING:
    from .backend_manifest import BackendManifest

PARTICIPANT_RUNTIME_ROLE_SCOPE = "capabilities.participant_runtime.supported_participant_roles"
PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE = "capabilities.participant_runtime.supported_behavior_features"
PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE = "capabilities.participant_runtime.supported_interaction_features"
OBSERVATION_CAPABILITY_CAPTURE_KIND_SCOPE = "capabilities.observation.supported_capture_kinds"
OBSERVATION_CAPABILITY_CHANNEL_KIND_SCOPE = "capabilities.observation.supported_channel_kinds"
OBSERVATION_CAPABILITY_SEALING_MODE_SCOPE = "capabilities.observation.supported_sealing_modes"
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
_PARTICIPANT_INTERACTION_CONTRACTS = frozenset(
    {
        "participant-behavior-history-event-stream-v1",
        "participant-shared-state-record-v1",
        "participant-joint-action-record-v1",
        "participant-time-management-context-v1",
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
        "contention": _PARTICIPANT_INTERACTION_CONTRACTS,
        "coordination": _PARTICIPANT_INTERACTION_CONTRACTS,
        "interference": _PARTICIPANT_INTERACTION_CONTRACTS,
        "shared_state_change": _PARTICIPANT_INTERACTION_CONTRACTS,
    },
}
"""Minimum published contract surfaces needed to make API-405 claims checkable.

The table is intentionally conservative. It gives the conformance runner a
falsifiable floor for standard terms, so a manifest cannot claim ACES participant support
while omitting the contracts that carry the corresponding runtime evidence.
"""

OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS = frozenset(
    {
        "experiment-capture-spec-v1",
        "experiment-evidence-record-v1",
        "experiment-derived-measure-v1",
        "experiment-run-v1",
    }
)


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


def _validate_participant_feature_support_term(feature: str) -> None:
    errors: list[str] = []
    for scope in (PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE, PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE):
        try:
            validate_controlled_vocabulary_scope_values(scope, (feature,))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        return
    raise ValueError(
        "ParticipantFeatureSupport.feature must be a governed participant behavior or interaction feature "
        f"term, or match the governed extension pattern; got {feature!r}; "
        f"validation details: {'; '.join(errors)}"
    )


@dataclass(frozen=True)
class ParticipantFeatureSupport:
    """API-407 per-feature participant runtime support declaration."""

    feature: str
    support_level: ParticipantFeatureSupportLevel | str
    constraint_refs: tuple[str, ...] = ()
    disclosure_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.feature.strip():
            raise ValueError("ParticipantFeatureSupport.feature must be non-empty")
        _validate_participant_feature_support_term(self.feature)

        try:
            support_level = (
                self.support_level
                if isinstance(self.support_level, ParticipantFeatureSupportLevel)
                else ParticipantFeatureSupportLevel(str(self.support_level))
            )
        except ValueError as exc:
            raise ValueError("ParticipantFeatureSupport.support_level must be a valid support level") from exc

        constraint_refs = tuple(self.constraint_refs)
        disclosure_refs = tuple(self.disclosure_refs)
        _validate_unique_non_empty_strings("ParticipantFeatureSupport.constraint_refs", constraint_refs)
        _validate_unique_non_empty_strings("ParticipantFeatureSupport.disclosure_refs", disclosure_refs)
        if support_level != ParticipantFeatureSupportLevel.EXACT and not disclosure_refs:
            raise ValueError(
                "ParticipantFeatureSupport disclosure_refs must be non-empty when support_level is below exact"
            )

        object.__setattr__(self, "support_level", support_level)
        object.__setattr__(self, "constraint_refs", constraint_refs)
        object.__setattr__(self, "disclosure_refs", disclosure_refs)


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
    feature_support: tuple[ParticipantFeatureSupport, ...] = ()
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
        feature_support = tuple(
            entry if isinstance(entry, ParticipantFeatureSupport) else ParticipantFeatureSupport(**entry)
            for entry in self.feature_support
        )
        feature_names = tuple(entry.feature for entry in feature_support)
        _validate_unique_non_empty_strings("ParticipantRuntimeCapabilities.feature_support", feature_names)
        supported_features = self.supported_behavior_features | self.supported_interaction_features
        for entry in feature_support:
            if (
                entry.support_level == ParticipantFeatureSupportLevel.UNSUPPORTED
                and entry.feature in supported_features
            ):
                raise ValueError(
                    "ParticipantRuntimeCapabilities.feature_support cannot declare a supported feature unsupported"
                )
        object.__setattr__(self, "feature_support", feature_support)


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
class BackendCapabilitySet:
    """Backend-specific nested capability blocks."""

    provisioner: ProvisionerCapabilities
    orchestrator: OrchestratorCapabilities | None = None
    evaluator: EvaluatorCapabilities | None = None
    participant_runtime: ParticipantRuntimeCapabilities | None = None
    observation: ObservationCapabilities | None = None


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


def observation_capability_contract_gaps(manifest: BackendManifest) -> tuple[str, ...]:
    """Return missing contract surfaces for declared EXP-715 observation claims."""

    observation = manifest.observation
    if observation is None:
        return ()

    required_contracts = set(observation.supported_evidence_contracts) | set(OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS)
    missing = sorted(required_contracts - manifest.supported_contract_versions)
    gaps: list[str] = []
    if missing:
        gaps.append(f"capabilities.observation missing required contracts: {', '.join(missing)}")
    return tuple(gaps)


def __getattr__(name: str) -> object:
    """Preserve the historical manifest imports without a circular import."""

    if name in {"BackendCompatibility", "BackendManifest"}:
        from . import backend_manifest

        return getattr(backend_manifest, name)
    raise AttributeError(name)
