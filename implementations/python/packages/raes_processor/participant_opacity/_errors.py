"""Stable errors shared by participant-opacity assurance lanes."""


class ParticipantOpacityEvidenceError(ValueError):
    """Stored evidence does not replay against its governed finite input."""


class ParticipantOpacityOperationalError(RuntimeError):
    """An opacity analyzer failed outside its typed outcome domain."""


__all__ = (
    "ParticipantOpacityEvidenceError",
    "ParticipantOpacityOperationalError",
)
