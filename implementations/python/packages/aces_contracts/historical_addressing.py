"""Stateless RFC 8785 historical semantic-address derivation."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

import rfc8785
from aces_sdl.historical_state import HistoricalBaseline

from .contracts.historical_state import (
    HISTORICAL_BASELINE_DIGEST_PROFILE,
    HISTORICAL_SEMANTIC_ADDRESS_PROFILE,
    HistoricalBaselineDigestModel,
    HistoricalSemanticAddressContextModel,
    HistoricalSemanticAddressModel,
)

HISTORICAL_ADDRESS_DOMAIN = b"aces-authored-historical-state|semantic-address|v1\x00"
HISTORICAL_BASELINE_DIGEST_DOMAIN = b"aces-authored-historical-state|baseline-digest|v1\x00"


def canonical_historical_address_bytes(context: HistoricalSemanticAddressContextModel) -> bytes:
    """Return canonical JCS bytes for one complete typed semantic coordinate."""

    try:
        return rfc8785.dumps(context.model_dump(mode="json", by_alias=True))
    except rfc8785.CanonicalizationError as exc:
        raise ValueError(f"historical semantic address canonicalization failed: {exc}") from exc


def _digest_address(canonical_bytes: bytes) -> bytes:
    return hashlib.sha256(HISTORICAL_ADDRESS_DOMAIN + canonical_bytes).digest()


def canonical_historical_baseline_bytes(baseline_id: str, baseline: HistoricalBaseline) -> bytes:
    """Return canonical bytes for one complete typed historical baseline."""

    payload = {
        "profile": HISTORICAL_BASELINE_DIGEST_PROFILE,
        "baseline_id": baseline_id,
        "baseline": baseline.model_dump(mode="json", by_alias=True),
    }
    try:
        return rfc8785.dumps(payload)
    except rfc8785.CanonicalizationError as exc:
        raise ValueError(f"historical baseline canonicalization failed: {exc}") from exc


def derive_historical_baseline_digest(
    baseline_id: str,
    baseline: HistoricalBaseline,
) -> HistoricalBaselineDigestModel:
    """Derive the portable identity of an admitted historical baseline."""

    canonical_bytes = canonical_historical_baseline_bytes(baseline_id, baseline)
    digest = hashlib.sha256(HISTORICAL_BASELINE_DIGEST_DOMAIN + canonical_bytes).hexdigest()
    return HistoricalBaselineDigestModel(
        profile=HISTORICAL_BASELINE_DIGEST_PROFILE,
        baseline_id=baseline_id,
        baseline_version=baseline.version,
        algorithm="sha256",
        value=f"sha256:{digest}",
    )


def derive_historical_semantic_addresses(
    contexts: Iterable[HistoricalSemanticAddressContextModel],
) -> tuple[HistoricalSemanticAddressModel, ...]:
    """Derive a complete batch, failing before output on duplicates or collisions."""

    pending: list[tuple[HistoricalSemanticAddressContextModel, bytes, bytes]] = []
    coordinates: set[tuple[str, ...]] = set()
    canonical_owners: dict[bytes, HistoricalSemanticAddressContextModel] = {}
    digest_owners: dict[bytes, bytes] = {}
    for context in contexts:
        if context.address_profile != HISTORICAL_SEMANTIC_ADDRESS_PROFILE:
            raise ValueError(f"unsupported historical semantic address profile {context.address_profile!r}")
        coordinate = (
            context.address_profile,
            context.range_instance_id,
            context.deployment_tenant_id,
            context.reset_generation_id,
            context.baseline_id,
            context.baseline_version,
            context.object_id,
        )
        if coordinate in coordinates:
            raise ValueError("duplicate historical semantic address coordinate")
        coordinates.add(coordinate)
        canonical_bytes = canonical_historical_address_bytes(context)
        if canonical_bytes in canonical_owners:
            raise ValueError("distinct historical semantic coordinates produced duplicate canonical bytes")
        canonical_owners[canonical_bytes] = context
        digest = _digest_address(canonical_bytes)
        previous_bytes = digest_owners.get(digest)
        if previous_bytes is not None and previous_bytes != canonical_bytes:
            raise ValueError("historical semantic address digest collision")
        digest_owners[digest] = canonical_bytes
        pending.append((context, canonical_bytes, digest))
    return tuple(
        HistoricalSemanticAddressModel(
            profile=HISTORICAL_SEMANTIC_ADDRESS_PROFILE,
            context=context,
            algorithm="sha256",
            value=f"hsa1:{digest.hex()}",
        )
        for context, _canonical_bytes, digest in pending
    )


def derive_historical_semantic_address(
    context: HistoricalSemanticAddressContextModel,
) -> HistoricalSemanticAddressModel:
    """Derive one semantic address through the same batch collision discipline."""

    return derive_historical_semantic_addresses((context,))[0]


__all__ = [
    "HISTORICAL_ADDRESS_DOMAIN",
    "HISTORICAL_BASELINE_DIGEST_DOMAIN",
    "canonical_historical_baseline_bytes",
    "canonical_historical_address_bytes",
    "derive_historical_baseline_digest",
    "derive_historical_semantic_address",
    "derive_historical_semantic_addresses",
]
