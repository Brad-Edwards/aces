"""Closed vocabularies for API-423 participant-crossing contracts."""

from enum import Enum


class ParticipantCrossingDirection(str, Enum):
    """Closed participant-boundary directions."""

    INGRESS = "ingress"
    EGRESS = "egress"


class ParticipantCrossingInteractionKind(str, Enum):
    """Closed incumbent carrier kinds that may cross a participant boundary."""

    ACTION_PROPOSAL = "action-proposal"
    CONSTRAINED_FORM_SUBMISSION = "constrained-form-submission"
    CANDIDATE_SELECTION = "candidate-selection"
    APPROVAL = "approval"
    DENIAL = "denial"
    EXTERNAL_DIRECTION = "external-direction"
    INTERVENTION = "intervention"
    HANDOFF = "handoff"
    OVERRIDE = "override"
    CANCELLATION = "cancellation"
    PARTICIPANT_INJECT_DELIVERY = "participant-inject-delivery"
    OBSERVATION = "observation"
    DECISION_SURFACE_PROJECTION = "decision-surface-projection"
    REDACTED_OUTPUT = "redacted-output"
    DISCLOSURE = "disclosure"
    DELIVERY_RECEIPT = "delivery-receipt"
    ACTION_RESULT = "action-result"
    STATUS_PROJECTION = "status-projection"
    HISTORY_PROJECTION = "history-projection"


class ParticipantCrossingSubjectKind(str, Enum):
    """Closed typed references to incumbent participant and evidence carriers."""

    PARTICIPANT_CONTROL_OCCURRENCE = "participant-control-occurrence"
    PARTICIPANT_ACTION_CONTRACT = "participant-action-contract"
    PARTICIPANT_ACTION_ADMISSION = "participant-action-admission"
    PARTICIPANT_ACTION_ATTEMPT = "participant-action-attempt"
    PARTICIPANT_ACTION_RESULT = "participant-action-result"
    PARTICIPANT_LIFECYCLE_EVENT = "participant-lifecycle-event"
    PARTICIPANT_OBSERVATION = "participant-observation"
    PARTICIPANT_DECISION_SURFACE = "participant-decision-surface"
    PARTICIPANT_EXPOSURE = "participant-exposure"
    PARTICIPANT_INJECT_DELIVERY = "participant-inject-delivery"
    PARTICIPANT_CONTEXT_VIEW = "participant-context-view"
    PARTICIPANT_HISTORY_VIEW = "participant-history-view"
    PARTICIPANT_STATUS_VIEW = "participant-status-view"
    EXPERIMENT_EVIDENCE = "experiment-evidence"


class ParticipantCrossingOperation(str, Enum):
    """Semantically independent participant information-flow operations."""

    ADMISSION = "admission"
    WITHHOLDING = "withholding"
    PROJECTION = "projection"
    MASKING = "masking"
    REDACTION = "redaction"
    TRANSFORMATION = "transformation"
    DECLASSIFICATION = "declassification"
    DISCLOSURE = "disclosure"
    DELIVERY = "delivery"
    CONCEALMENT = "concealment"
    REVOCATION = "revocation"
    AUDIT_RETENTION = "audit-retention"


class ParticipantCrossingGateDisposition(str, Enum):
    """One deny-first decision-gate result."""

    PERMIT = "permit"
    DENY = "deny"
    NOT_APPLICABLE = "not-applicable"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"


class ParticipantCrossingDecisionDisposition(str, Enum):
    """Overall policy disposition for one crossing request."""

    PERMIT = "permit"
    DENY = "deny"
    TRANSFORM = "transform"
    WITHHOLD = "withhold"
    UNSUPPORTED = "unsupported"


class ParticipantCrossingBackendPosture(str, Enum):
    """Bounded backend-support posture without a realization claim."""

    EXACT = "exact"
    BOUNDED = "bounded"
    DISCLOSED_WEAK = "disclosed-weak"
    UNSUPPORTED = "unsupported"


class ParticipantCrossingLossKind(str, Enum):
    """Disclosed loss or guarantee weakening for a crossing fact."""

    NONE = "none"
    FIDELITY_LOSS = "fidelity-loss"
    GUARANTEE_WEAKENING = "guarantee-weakening"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"


__all__ = [
    "ParticipantCrossingBackendPosture",
    "ParticipantCrossingDecisionDisposition",
    "ParticipantCrossingDirection",
    "ParticipantCrossingGateDisposition",
    "ParticipantCrossingInteractionKind",
    "ParticipantCrossingLossKind",
    "ParticipantCrossingOperation",
    "ParticipantCrossingSubjectKind",
]
