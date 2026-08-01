"""Records and reference-context container for participant behavior semantics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ParticipantBehaviorReference:
    """Normalized reference from an agent to a behavior contract artifact."""

    participant_name: str
    reference_kind: str
    raw: str
    canonical_name: str


@dataclass(frozen=True)
class ParticipantBehaviorIssue:
    """Machine-readable participant behavior consistency issue."""

    code: str
    participant_name: str
    ref: str
    action_name: str = ""
    boundary_name: str = ""
    transition_id: str = ""
    spec_name: str = ""
    message: str = ""


@dataclass(frozen=True)
class ParticipantBehaviorAnalysis:
    """Result of analyzing participant behavior references."""

    references: tuple[ParticipantBehaviorReference, ...] = ()
    issues: tuple[ParticipantBehaviorIssue, ...] = ()

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)


@dataclass(frozen=True)
class _BehaviorSpecificationReferenceContext:
    participant_names: set[str]
    participant_roles_by_agent: Mapping[str, str]
    action_names: set[str]
    observation_boundary_names: set[str]
    outcome_rule_names: set[str]
    agents_by_name: Mapping[str, object]
    action_contracts: Mapping[str, object]
    observation_boundaries: Mapping[str, object]
    clocks: Mapping[str, object]
    time_progression_policies: Mapping[str, object]
    temporal_constraints: Mapping[str, object]
    objectives: Mapping[str, object]

    @property
    def participant_roles(self) -> set[str]:
        return set(self.participant_roles_by_agent.values())
