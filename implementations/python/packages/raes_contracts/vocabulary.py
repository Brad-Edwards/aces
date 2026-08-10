"""Public vocabulary used by external RAES contracts."""

from enum import Enum
from typing import Annotated

from pydantic import Field


class ProcessorFeature(str, Enum):
    """Processing features that a processor may support."""

    COMPILATION = "compilation"
    PLANNING = "planning"
    ORCHESTRATION_COORDINATION = "orchestration-coordination"
    EVALUATION_COORDINATION = "evaluation-coordination"
    WORKFLOW_SEMANTICS = "workflow-semantics"
    OBJECTIVE_WINDOW_CONSISTENCY = "objective-window-consistency"
    DEPENDENCY_ORDERING = "dependency-ordering"
    RUNTIME_CONTROL_PLANE = "runtime-control-plane"


class GeneratedArtifactKind(str, Enum):
    """Portable kinds of material a provisioner may generate."""

    CERTIFICATE_BUNDLE = "certificate_bundle"
    RENDERED_CONFIG = "rendered_config"
    SSH_KEY_BUNDLE = "ssh_key_bundle"


class WorkflowFeature(str, Enum):
    """Portable workflow control features that an orchestrator may support."""

    DECISION = "decision"
    SWITCH = "switch"
    RETRY = "retry"
    CALL = "call"
    PARALLEL_BARRIER = "parallel-barrier"
    FAILURE_TRANSITIONS = "failure-transitions"
    CANCELLATION = "cancellation"
    TIMEOUTS = "timeouts"
    COMPENSATION = "compensation"
    OBJECTIVE_STEPS = "objective-steps"
    SCAFFOLDED_STEPS = "scaffolded-steps"


class WorkflowStatePredicateFeature(str, Enum):
    """Portable workflow state-predicate features that an orchestrator may support."""

    OUTCOME_MATCHING = "outcome-matching"
    ATTEMPT_COUNTS = "attempt-counts"


class RealizationSupportMode(str, Enum):
    """How an apparatus can supply realizations for underspecified inputs."""

    EXACT_ONLY = "exact-only"
    CONSTRAINED = "constrained"
    OPEN_REALIZATION = "open-realization"


class ProcessResourceLimitKind(str, Enum):
    """Portable process-resource terms governed by the runtime contract."""

    OPEN_FILE_DESCRIPTORS = "open_file_descriptors"
    LOCKED_MEMORY_BYTES = "locked_memory_bytes"


class ProcessResourceLimitScope(str, Enum):
    """Process inheritance scope for a portable resource limit."""

    PROCESS = "process"
    SUBTREE = "subtree"


class ObservationStrength(str, Enum):
    """Strongest evidence a backend configuration emits for one concern."""

    NONE = "none"
    DRIVER_REPORTED = "driver-reported"
    DAEMON_OBSERVED = "daemon-observed"
    GUEST_OBSERVED = "guest-observed"


def observation_strength_satisfies(
    actual: ObservationStrength,
    required: ObservationStrength,
) -> bool:
    """Return whether an observation is at least as strong as required."""

    rank = {
        ObservationStrength.NONE: 0,
        ObservationStrength.DRIVER_REPORTED: 1,
        ObservationStrength.DAEMON_OBSERVED: 2,
        ObservationStrength.GUEST_OBSERVED: 3,
    }
    return rank[actual] >= rank[required]


class RealizationVerificationScope(str, Enum):
    """Closed scope at which an inventory realization was corroborated."""

    PRESENCE = "presence"
    CONFIGURATION = "configuration"


def verification_scope_satisfies(
    actual: RealizationVerificationScope,
    required: RealizationVerificationScope,
) -> bool:
    """Return whether an observation covers the required inventory scope."""

    rank = {
        RealizationVerificationScope.PRESENCE: 0,
        RealizationVerificationScope.CONFIGURATION: 1,
    }
    return rank[actual] >= rank[required]


class Closure(str, Enum):
    """Whether unspecified realizable dimensions under a scope are admitted."""

    OPEN_WORLD = "open-world"
    CLOSED_WORLD = "closed-world"


class ParticipantFeatureSupportLevel(str, Enum):
    """ADR-054 guarantee-strength scale for per-feature participant runtime support."""

    UNSUPPORTED = "unsupported"
    DISCLOSED_WEAK = "disclosed_weak"
    BOUNDED = "bounded"
    EXACT = "exact"


class ConceptProvenanceCategory(str, Enum):
    """How a concept family relates to its authority source."""

    ADOPTED = "adopted"
    ADAPTED = "adapted"
    NATIVE = "native"


class ExternalKnowledgeBindingEffect(str, Enum):
    """Portable SEM-217 effects a binding may claim about native RAES meaning."""

    ANNOTATES = "annotates"
    CONSTRAINS = "constrains"
    REFINES = "refines"
    ALIGNS = "aligns"


ConceptFamilyId = Annotated[
    str,
    Field(min_length=1, pattern=r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"),
]
"""Pattern-constrained concept family identifier matching the authoritative catalog key format."""
