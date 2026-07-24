"""RFC 8785 and domain-separated SHA-256 live-activity identities."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

import rfc8785
from aces_sdl.live_activity import ActivityProfile

from .contracts.historical_state import HistoricalBaselineDigestModel
from .contracts.live_activity import (
    LIVE_ACTIVITY_OCCURRENCE_PROFILE,
    LIVE_ACTIVITY_PROFILE_DIGEST_PROFILE,
    ActivityOccurrenceContextModel,
    ActivityOccurrenceIdentityModel,
    ActivityProfileDigestModel,
    CompiledActivityProfileModel,
)

LIVE_ACTIVITY_PROFILE_DIGEST_DOMAIN = b"aces-live-activity|profile-digest|v1\x00"
LIVE_ACTIVITY_OCCURRENCE_DOMAIN = b"aces-live-activity|occurrence-identity|v1\x00"


def canonical_activity_profile_bytes(
    profile_id: str,
    profile: ActivityProfile,
    baseline_digest: HistoricalBaselineDigestModel,
) -> bytes:
    payload = {
        "profile": LIVE_ACTIVITY_PROFILE_DIGEST_PROFILE,
        "activity_profile_id": profile_id,
        "historical_baseline_digest": baseline_digest.model_dump(mode="json"),
        "activity_profile": profile.model_dump(mode="json", by_alias=True),
    }
    try:
        return rfc8785.dumps(payload)
    except rfc8785.CanonicalizationError as exc:
        raise ValueError(f"live activity profile canonicalization failed: {exc}") from exc


def derive_activity_profile_digest(
    profile_id: str,
    profile: ActivityProfile,
    baseline_digest: HistoricalBaselineDigestModel,
) -> ActivityProfileDigestModel:
    canonical = canonical_activity_profile_bytes(profile_id, profile, baseline_digest)
    digest = hashlib.sha256(LIVE_ACTIVITY_PROFILE_DIGEST_DOMAIN + canonical).hexdigest()
    return ActivityProfileDigestModel(
        profile=LIVE_ACTIVITY_PROFILE_DIGEST_PROFILE,
        activity_profile_id=profile_id,
        activity_profile_version=profile.version,
        historical_baseline_digest=baseline_digest.value,
        algorithm="sha256",
        value=f"sha256:{digest}",
    )


def canonical_activity_occurrence_bytes(context: ActivityOccurrenceContextModel) -> bytes:
    try:
        return rfc8785.dumps(context.model_dump(mode="json", by_alias=True))
    except rfc8785.CanonicalizationError as exc:
        raise ValueError(f"live activity occurrence canonicalization failed: {exc}") from exc


def _digest_occurrence(canonical: bytes) -> bytes:
    return hashlib.sha256(LIVE_ACTIVITY_OCCURRENCE_DOMAIN + canonical).digest()


def derive_activity_occurrence_identities(
    contexts: Iterable[ActivityOccurrenceContextModel],
) -> tuple[ActivityOccurrenceIdentityModel, ...]:
    pending: list[tuple[ActivityOccurrenceContextModel, bytes, bytes]] = []
    canonical_owners: dict[bytes, ActivityOccurrenceContextModel] = {}
    digest_owners: dict[bytes, bytes] = {}
    for context in contexts:
        if context.occurrence_profile != LIVE_ACTIVITY_OCCURRENCE_PROFILE:
            raise ValueError(f"unsupported activity occurrence profile {context.occurrence_profile!r}")
        canonical = canonical_activity_occurrence_bytes(context)
        if canonical in canonical_owners:
            raise ValueError("duplicate live activity occurrence coordinate")
        canonical_owners[canonical] = context
        digest = _digest_occurrence(canonical)
        prior = digest_owners.get(digest)
        if prior is not None and prior != canonical:
            raise ValueError("live activity occurrence digest collision")
        digest_owners[digest] = canonical
        pending.append((context, canonical, digest))
    return tuple(
        ActivityOccurrenceIdentityModel(
            profile=LIVE_ACTIVITY_OCCURRENCE_PROFILE,
            context=context,
            algorithm="sha256",
            value=f"lao1:{digest.hex()}",
        )
        for context, _canonical, digest in pending
    )


def activity_occurrence_context(
    compiled: CompiledActivityProfileModel,
    *,
    action_id: str,
    logical_time_seconds: int,
    occurrence_ordinal: int,
) -> ActivityOccurrenceContextModel:
    try:
        action = compiled.actions[action_id]
    except KeyError:
        raise ValueError(f"unknown compiled activity action {action_id!r}") from None
    expected_time = action.schedule_anchor_seconds + occurrence_ordinal * action.schedule_interval_seconds
    if occurrence_ordinal >= action.max_occurrences:
        raise ValueError("activity occurrence ordinal exceeds the finite schedule bound")
    if logical_time_seconds != expected_time:
        raise ValueError("activity occurrence logical time does not match its stable schedule ordinal")
    return ActivityOccurrenceContextModel(
        occurrence_profile=LIVE_ACTIVITY_OCCURRENCE_PROFILE,
        deployment_tenant_id=compiled.deployment_tenant_id,
        range_instance_id=compiled.range_instance_id,
        reset_generation_id=compiled.reset_generation_id,
        activity_profile_id=compiled.activity_profile_id,
        activity_digest=compiled.activity_digest.value,
        historical_baseline_digest=compiled.baseline_digest.value,
        logical_time_seconds=logical_time_seconds,
        occurrence_ordinal=occurrence_ordinal,
        action_id=action.action_id,
        template_id=action.template_id,
        execution_context_id=action.execution_context_id,
        target_service_id=action.target_service_id,
        entropy_identity=compiled.entropy_identity,
        random_stream_profile=action.random_stream_profile,
        schedule_profile=action.schedule_profile,
        transform_profile=action.transform_profile,
        address_profile=action.address_profile,
    )


def validate_activity_occurrence_context(
    compiled: CompiledActivityProfileModel,
    context: ActivityOccurrenceContextModel,
) -> None:
    expected = activity_occurrence_context(
        compiled,
        action_id=context.action_id.rsplit(".", 1)[-1],
        logical_time_seconds=context.logical_time_seconds,
        occurrence_ordinal=context.occurrence_ordinal,
    )
    if context.reset_generation_id != compiled.reset_generation_id:
        raise ValueError("stale reset generation in live activity occurrence")
    for field_name in type(context).model_fields:
        if getattr(context, field_name) != getattr(expected, field_name):
            raise ValueError(f"live activity occurrence {field_name} does not match the compiled profile")


__all__ = [
    "LIVE_ACTIVITY_OCCURRENCE_DOMAIN",
    "LIVE_ACTIVITY_PROFILE_DIGEST_DOMAIN",
    "activity_occurrence_context",
    "canonical_activity_occurrence_bytes",
    "canonical_activity_profile_bytes",
    "derive_activity_occurrence_identities",
    "derive_activity_profile_digest",
    "validate_activity_occurrence_context",
]
