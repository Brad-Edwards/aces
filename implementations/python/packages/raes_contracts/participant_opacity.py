"""Portable contracts for bounded participant-predicate opacity analysis."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .canonical import canonical_json_digest
from .contracts.base import (
    BehavioralClaimBindingModel,
    ContractModel,
    PrefixedDigestString,
)
from .diagnostics import DiagnosticModel
from .satisfiability import SourceArtifactIdentityModel
from .versions import (
    PARTICIPANT_OPACITY_ANALYSIS_EVIDENCE_SCHEMA_VERSION,
    PARTICIPANT_OPACITY_ANALYSIS_INPUT_SCHEMA_VERSION,
)

SafeRef = Annotated[
    str,
    Field(pattern=r"^[a-z][a-z0-9._:/-]*$", max_length=256),
]
SafeKey = Annotated[
    str,
    Field(pattern=r"^[a-z][a-z0-9._:/|-]*$", max_length=256),
]
Revision = Annotated[
    str,
    Field(pattern=r"^[a-z0-9][a-z0-9._/-]*$", max_length=128),
]
MAX_OPACITY_POINTS = 100_000
MAX_OPACITY_DIAGNOSTICS = 64
NORMALIZED_INPUT_PROVENANCE_NONCLAIM = (
    "No source or materializer authenticity is established by this normalized-input evidence."
)


class ParticipantOpacityOutcome(str, Enum):
    """Closed bounded-analysis outcomes."""

    NO_COUNTEREXAMPLE = "no-counterexample-within-declared-finite-bounds"
    COUNTEREXAMPLE = "counterexample-found"
    VACUOUS = "vacuous-secret-domain"
    UNSUPPORTED = "unsupported"


class ParticipantOpacityDeclaredCountsModel(ContractModel):
    """Exact realized cardinalities of every finite quantified coordinate."""

    points: int = Field(ge=1, le=MAX_OPACITY_POINTS)
    runs: int = Field(ge=1, le=MAX_OPACITY_POINTS)
    cuts: int = Field(ge=1, le=MAX_OPACITY_POINTS)
    strategies: int = Field(ge=1, le=MAX_OPACITY_POINTS)
    scheduler_environment_pairs: int = Field(ge=1, le=MAX_OPACITY_POINTS)
    order_variants: int = Field(ge=1, le=MAX_OPACITY_POINTS)


class OpacityPossiblePointModel(ContractModel):
    """One safe abstract point in a complete declared finite carrier."""

    ordinal: int = Field(ge=0, le=MAX_OPACITY_POINTS - 1)
    point_ref: SafeRef
    run_ref: SafeRef
    cut_ref: SafeRef
    strategy_ref: SafeRef
    scheduler_ref: SafeRef
    environment_ref: SafeRef
    order_ref: SafeRef
    reachable: bool
    secret_holds: bool
    initial_information_key: SafeKey
    observation_key: SafeKey
    memory_key: SafeKey
    release_state_key: SafeKey
    coalition_fusion_key: SafeKey | None = None


class ParticipantOpacityAnalysisInputModel(ContractModel):
    """Normalized finite carrier supplied by a trusted materializer."""

    schema_version: Literal[PARTICIPANT_OPACITY_ANALYSIS_INPUT_SCHEMA_VERSION] = (
        PARTICIPANT_OPACITY_ANALYSIS_INPUT_SCHEMA_VERSION
    )
    analysis_profile: Literal["raes-participant-opacity-bounded-test/v1"]
    source: SourceArtifactIdentityModel
    profile_id: SafeRef
    profile_revision: Revision
    profile_digest: PrefixedDigestString
    normalized_model_ref: SafeRef
    materializer_id: SafeRef
    materializer_version: Revision
    materializer_digest: PrefixedDigestString
    complete_enumeration: bool
    declared_counts: ParticipantOpacityDeclaredCountsModel
    claim: BehavioralClaimBindingModel
    points: tuple[OpacityPossiblePointModel, ...] = Field(
        min_length=1,
        max_length=MAX_OPACITY_POINTS,
    )

    @model_validator(mode="after")
    def _validate_finite_carrier(
        self,
    ) -> ParticipantOpacityAnalysisInputModel:
        ordinals = [point.ordinal for point in self.points]
        point_refs = [point.point_ref for point in self.points]
        if len(ordinals) != len(set(ordinals)) or set(ordinals) != set(range(len(self.points))):
            raise ValueError("point ordinals must uniquely and contiguously cover the point count")
        if len(point_refs) != len(set(point_refs)):
            raise ValueError("possible point refs must be unique")
        realized = {
            "points": len(self.points),
            "runs": len({point.run_ref for point in self.points}),
            "cuts": len({point.cut_ref for point in self.points}),
            "strategies": len({point.strategy_ref for point in self.points}),
            "scheduler_environment_pairs": len({(point.scheduler_ref, point.environment_ref) for point in self.points}),
            "order_variants": len({point.order_ref for point in self.points}),
        }
        declared = self.declared_counts.model_dump(mode="python")
        if realized != declared:
            raise ValueError("declared finite counts must exactly match the realized carrier count")
        return self

    def canonicalized(self) -> ParticipantOpacityAnalysisInputModel:
        """Return a canonical point ordering without changing carrier meaning."""

        ordered = tuple(sorted(self.points, key=lambda point: point.ordinal))
        if ordered == self.points:
            return self
        return self.model_copy(update={"points": ordered})

    @property
    def canonical_digest(self) -> str:
        """Digest the canonicalized finite carrier and all joined identities."""

        return canonical_json_digest(self.canonicalized().model_dump(mode="json"))


class ParticipantOpacityCheckerConfigurationModel(ContractModel):
    """Complete output-affecting identity of the bounded checker."""

    profile: Literal["raes-participant-opacity-checker/v1"]
    tool_id: Literal["raes-processor-participant-opacity"]
    tool_version: Literal["1.0.0"]
    algorithm: Literal["exhaustive-information-cell-scan/v1"]
    information_cell_key: Literal["initial-observation-memory-release-coalition-strategy-order/v1"]
    counterexample_selection: Literal["lowest-canonical-ordinal/v1"]
    max_points: Literal[4096]

    @property
    def canonical_digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))


class ParticipantOpacityCounterexampleModel(ContractModel):
    """Sanitized reference to one canonical secret-only information cell."""

    safe_ref: Annotated[
        str,
        Field(pattern=r"^participant-opacity-counterexample:[0-9]{6}$"),
    ]
    counterexample_digest: PrefixedDigestString
    actual_point_ordinal: int = Field(ge=0, le=MAX_OPACITY_POINTS - 1)
    examined_cell_size: int = Field(ge=1, le=MAX_OPACITY_POINTS)


class UnsupportedParticipantOpacityAnalysisModel(ContractModel):
    """Stable fail-closed reason set for a valid but non-positive analysis."""

    profile: Literal["raes-participant-opacity-unsupported/v1"]
    reason_codes: tuple[str, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def _validate_reasons(
        self,
    ) -> UnsupportedParticipantOpacityAnalysisModel:
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("unsupported reason codes must be unique and sorted")
        return self


class ParticipantOpacityAnalysisEvidenceModel(ContractModel):
    """Digest-bound bounded result with no raw possible-point contents."""

    schema_version: Literal[PARTICIPANT_OPACITY_ANALYSIS_EVIDENCE_SCHEMA_VERSION] = (
        PARTICIPANT_OPACITY_ANALYSIS_EVIDENCE_SCHEMA_VERSION
    )
    analysis_profile: Literal["raes-participant-opacity-bounded-test/v1"]
    provenance_scope: Literal["normalized-input-only"]
    taxonomy_id: Literal["raes-behavioral-relations"]
    taxonomy_revision: Revision
    relation_id: Literal["participant-predicate-opacity"]
    profile_id: SafeRef
    profile_revision: Revision
    profile_digest: PrefixedDigestString
    normalized_model_ref: SafeRef
    normalized_model_digest: PrefixedDigestString
    checker_configuration: ParticipantOpacityCheckerConfigurationModel
    checker_configuration_digest: PrefixedDigestString
    claim: BehavioralClaimBindingModel
    outcome: ParticipantOpacityOutcome
    checked_points: int = Field(ge=0, le=MAX_OPACITY_POINTS)
    checked_secret_points: int = Field(ge=0, le=MAX_OPACITY_POINTS)
    diagnostics: tuple[DiagnosticModel, ...] = Field(max_length=MAX_OPACITY_DIAGNOSTICS)
    counterexample: ParticipantOpacityCounterexampleModel | None = None
    unsupported: UnsupportedParticipantOpacityAnalysisModel | None = None

    @model_validator(mode="after")
    def _validate_evidence_join(
        self,
    ) -> ParticipantOpacityAnalysisEvidenceModel:
        if self.checked_secret_points > self.checked_points:
            raise ValueError("checked secret points cannot exceed checked points")
        if self.checker_configuration_digest != self.checker_configuration.canonical_digest:
            raise ValueError("checker_configuration_digest must bind the checker configuration")
        expected_counterexample = self.outcome is ParticipantOpacityOutcome.COUNTEREXAMPLE
        expected_unsupported = self.outcome in {
            ParticipantOpacityOutcome.VACUOUS,
            ParticipantOpacityOutcome.UNSUPPORTED,
        }
        if (self.counterexample is not None) != expected_counterexample:
            raise ValueError("counterexample payload must exactly match the counterexample outcome")
        if self.counterexample is not None:
            expected_digest = participant_opacity_counterexample_digest(
                safe_ref=self.counterexample.safe_ref,
                actual_point_ordinal=self.counterexample.actual_point_ordinal,
                examined_cell_size=self.counterexample.examined_cell_size,
                normalized_model_digest=self.normalized_model_digest,
            )
            if self.counterexample.counterexample_digest != expected_digest:
                raise ValueError("counterexample_digest must bind the sanitized counterexample identity")
        if (self.unsupported is not None) != expected_unsupported:
            raise ValueError("unsupported payload must exactly match a non-positive unsupported outcome")
        if self.unsupported is not None:
            diagnostic_codes = tuple(sorted({diagnostic.code for diagnostic in self.diagnostics}))
            if self.unsupported.reason_codes != diagnostic_codes:
                raise ValueError("unsupported reason codes must match evidence diagnostics")
        decided = self.outcome in {
            ParticipantOpacityOutcome.NO_COUNTEREXAMPLE,
            ParticipantOpacityOutcome.COUNTEREXAMPLE,
        }
        if decided and (self.checked_points == 0 or self.checked_secret_points == 0):
            raise ValueError("decided outcomes require nonzero checked and secret point counts")
        if decided and self.diagnostics:
            raise ValueError("decided outcomes cannot carry error diagnostics")
        if self.outcome is ParticipantOpacityOutcome.VACUOUS and self.checked_secret_points != 0:
            raise ValueError("a vacuous secret domain requires zero checked secret points")
        if self.claim.taxonomy_id != self.taxonomy_id:
            raise ValueError("evidence claim taxonomy id must match the evidence")
        if self.claim.taxonomy_revision != self.taxonomy_revision:
            raise ValueError("evidence claim taxonomy revision must match the evidence")
        if self.claim.relation_id != self.relation_id:
            raise ValueError("evidence claim relation must match the evidence")
        if self.claim.relation_parameter_profile_ref != self.profile_id:
            raise ValueError("evidence claim profile id must match the evidence")
        if self.claim.relation_parameter_profile_revision != self.profile_revision:
            raise ValueError("evidence claim profile revision must match the evidence")
        if (
            self.claim.assurance_axis,
            self.claim.assurance_status,
            self.claim.evidence_scope,
            self.claim.quantifier_scope,
        ) != ("bounded-test", "tested", "finite", "finite-cases"):
            raise ValueError("opacity evidence claim must remain bounded-test/tested/finite/finite-cases")
        if NORMALIZED_INPUT_PROVENANCE_NONCLAIM not in self.claim.explicit_non_claims:
            raise ValueError("normalized-input evidence must disclaim source and materializer authenticity")
        return self


def participant_opacity_counterexample_digest(
    *,
    safe_ref: str,
    actual_point_ordinal: int,
    examined_cell_size: int,
    normalized_model_digest: str,
) -> str:
    """Digest only the sanitized counterexample identity and model join."""

    return canonical_json_digest(
        {
            "safe_ref": safe_ref,
            "actual_point_ordinal": actual_point_ordinal,
            "examined_cell_size": examined_cell_size,
            "normalized_model_digest": normalized_model_digest,
        }
    )


__all__ = [
    "MAX_OPACITY_POINTS",
    "NORMALIZED_INPUT_PROVENANCE_NONCLAIM",
    "OpacityPossiblePointModel",
    "ParticipantOpacityAnalysisEvidenceModel",
    "ParticipantOpacityAnalysisInputModel",
    "ParticipantOpacityCheckerConfigurationModel",
    "ParticipantOpacityCounterexampleModel",
    "ParticipantOpacityDeclaredCountsModel",
    "ParticipantOpacityOutcome",
    "UnsupportedParticipantOpacityAnalysisModel",
    "participant_opacity_counterexample_digest",
]
