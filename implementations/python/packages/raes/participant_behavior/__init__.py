"""Participant behavior contract models (SEM-208, SEM-209, SEM-210).

The legacy ``agents.*.actions`` list remains the authoring reference list.
These models provide the governed source of truth those names resolve to when
an SDL document declares explicit participant behavior semantics.

This package is a thin facade over cohesive subdomains:

* :mod:`._action_contracts` - action-argument domains, the interaction
  declaration, and the governed :class:`ParticipantActionContract`.
* :mod:`._view_boundaries` - view rules/transitions and the
  :class:`ParticipantObservationBoundary` projection.

The ``ParticipantEffectClass`` / ``ParticipantFailureClass`` /
``ParticipantPreconditionClass`` (and the imported action/temporal) names are
re-exported here to preserve the pre-split ``raes.participant_behavior`` import
surface; their object identity remains owned by
:mod:`raes.participant_action_semantics` and
:mod:`raes.participant_temporal_semantics`.
"""

from ..participant_action_semantics import (
    ParticipantActionEffect,
    ParticipantActionPrecondition,
    ParticipantBackendFailureMapping,
    ParticipantEffectClass,
    ParticipantFailureClass,
    ParticipantPreconditionClass,
)
from ..participant_temporal_semantics import (
    ParticipantBackendTimingDisclosure,
    ParticipantTemporalContract,
    validate_action_contract_temporal_payload,
)
from ._action_contracts import (
    ExternalMappingLoss,
    ParticipantActionArgumentAuthoredValue,
    ParticipantActionArgumentCardinality,
    ParticipantActionArgumentDefinition,
    ParticipantActionArgumentNormalization,
    ParticipantActionArgumentOmission,
    ParticipantActionArgumentScalar,
    ParticipantActionArgumentValueType,
    ParticipantActionContract,
    ParticipantActionGranularity,
    ParticipantActionLifecycle,
    ParticipantInteractionClass,
    ParticipantInteractionDeclaration,
)
from ._view_boundaries import (
    ParticipantInformationBoundaryClass,
    ParticipantObservationBoundary,
    ParticipantViewDisposition,
    ParticipantViewHistoryEventType,
    ParticipantViewRule,
    ParticipantViewTransition,
    ParticipantViewTransitionKind,
)
