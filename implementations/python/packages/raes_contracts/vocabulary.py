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


ConceptFamilyId = Annotated[
    str,
    Field(min_length=1, pattern=r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"),
]
"""Pattern-constrained concept family identifier matching the authoritative catalog key format."""
