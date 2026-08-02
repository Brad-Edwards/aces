"""SDL orchestration and workflow models.

This package is a thin facade over cohesive subdomains:

* :mod:`._durations` - OCR-compatible :func:`parse_duration`.
* :mod:`._events` - authored narrative timing models (:class:`Inject`,
  :class:`Event`, :class:`Script`, :class:`Story`).
* :mod:`._steps` - workflow step types, predicates, policies, and
  :class:`WorkflowStep`.
* :mod:`._workflow` - the :class:`Workflow` control graph.
"""

from ._durations import parse_duration
from ._events import Event, Inject, Script, Story
from ._steps import (
    WorkflowCompensationFailurePolicy,
    WorkflowCompensationMode,
    WorkflowCompensationPolicy,
    WorkflowCompensationTrigger,
    WorkflowPredicate,
    WorkflowStep,
    WorkflowStepExecutionMode,
    WorkflowStepOutcome,
    WorkflowStepStateRef,
    WorkflowStepType,
    WorkflowSwitchCase,
    WorkflowTimeoutPolicy,
)
from ._workflow import Workflow
