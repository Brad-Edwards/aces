"""Closed registry data for semantic projection predicate profiles."""

from __future__ import annotations

PROFILE_ADAPTERS = {
    "declared": "declared-owner-adapter",
    "admitted": "admitted-owner-adapter",
    "observed": "observed-owner-adapter",
    "verified": "verified-owner-adapter",
}
PROFILE_PRODUCERS = {
    "declared": "sdl-authoring-input-v1",
    "admitted": "validation-basis-disclosure-v1",
    "observed": "proposition-truth-result-v1",
    "verified": "artifact-transformation-report-v1",
}
PROFILE_AXES = {
    "declared": ("applicable", "not-applicable", "forbidden"),
    "admitted": ("not-applicable", "not-applicable", "forbidden"),
    "observed": ("not-applicable", "applicable", "forbidden"),
    "verified": ("not-applicable", "not-applicable", "applicable"),
}

_BINDING_POSTURES = {
    (False, False): "strict",
    (True, False): "approximate",
    (False, True): "lossy",
    (True, True): "approximate-lossy",
}


def binding_posture(allow_approximate_bindings: bool, allow_lossy_bindings: bool) -> str:
    return _BINDING_POSTURES[(allow_approximate_bindings, allow_lossy_bindings)]


__all__ = ["PROFILE_ADAPTERS", "PROFILE_AXES", "PROFILE_PRODUCERS", "binding_posture"]
