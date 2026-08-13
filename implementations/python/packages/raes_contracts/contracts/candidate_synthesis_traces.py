"""Closed construct-contribution trace types for SDL candidate synthesis."""

from __future__ import annotations

from collections.abc import Mapping, Set
from enum import Enum
from typing import Annotated

from pydantic import Field, field_validator

from .base import ContractModel, NonEmptyString

CanonicalSDLRef = Annotated[
    str,
    Field(pattern=r"^nodes\.[a-z][a-z0-9-]*$", max_length=128),
]


class SynthesisContributionKind(str, Enum):
    IMPORTED_ASSERTION = "imported-assertion"
    TRANSFORMATION_ASSUMPTION = "transformation-assumption"
    INFERRED_STRUCTURE = "inferred-structure"
    TRANSFORMATION_DEFAULT = "transformation-default"
    AUTHOR_DECISION = "author-decision"
    GOVERNED_POLICY_DECISION = "governed-policy-decision"


class CandidateSynthesisContributionModel(ContractModel):
    kind: SynthesisContributionKind
    ref_id: NonEmptyString


class CandidateSynthesisConstructTraceModel(ContractModel):
    target_ref: CanonicalSDLRef
    contributions: tuple[CandidateSynthesisContributionModel, ...] = Field(min_length=1, max_length=128)

    @field_validator("contributions")
    @classmethod
    def _validate_contributions(
        cls,
        value: tuple[CandidateSynthesisContributionModel, ...],
    ) -> tuple[CandidateSynthesisContributionModel, ...]:
        order = {
            SynthesisContributionKind.IMPORTED_ASSERTION: 0,
            SynthesisContributionKind.TRANSFORMATION_ASSUMPTION: 1,
            SynthesisContributionKind.INFERRED_STRUCTURE: 2,
            SynthesisContributionKind.TRANSFORMATION_DEFAULT: 3,
            SynthesisContributionKind.AUTHOR_DECISION: 4,
            SynthesisContributionKind.GOVERNED_POLICY_DECISION: 5,
        }
        keys = tuple((order[item.kind], item.ref_id) for item in value)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("construct contributions must use stable kind/ref ordering")
        return value


ContributionKey = tuple[SynthesisContributionKind, str]


def validate_resolved_contributions(
    contributions: Set[ContributionKey],
    owners: Mapping[SynthesisContributionKind, Set[str]],
    required: Set[ContributionKey],
) -> None:
    if any(ref_id not in owners[kind] for kind, ref_id in contributions):
        raise ValueError("construct contribution reference does not resolve against its owning collection")
    if required.difference(contributions):
        raise ValueError("construct trace omits required assertion, assumption, or decision provenance")
    if not any(kind == SynthesisContributionKind.INFERRED_STRUCTURE for kind, _ in contributions):
        raise ValueError("construct trace requires at least one resolved transformation rule")


__all__ = [
    "CandidateSynthesisConstructTraceModel",
    "CandidateSynthesisContributionModel",
    "SynthesisContributionKind",
    "validate_resolved_contributions",
]
