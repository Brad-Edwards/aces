"""First-class participant behavior specification models (ACT-606)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from typing_extensions import TypeAliasType

from ._base import SDLModel
from ._identifiers import PortableIdentifier


class ParticipantBehaviorSpecificationLifecycle(str, Enum):
    """Governance lifecycle for participant behavior specifications."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


_BEHAVIOR_SPEC_EXTENSION_KEY_RE = re.compile(r"^x-[a-z0-9]+(?:-[a-z0-9]+)*:[a-z0-9]+(?:-[a-z0-9]+)*$")
_BEHAVIOR_SPEC_EXTENSION_POLICIES = frozenset({"closed", "governed-extension"})
BehaviorSpecificationExtensionScalar = str | int | float | bool | None
BehaviorSpecificationExtensionValue = TypeAliasType(
    "BehaviorSpecificationExtensionValue",
    BehaviorSpecificationExtensionScalar
    | list["BehaviorSpecificationExtensionValue"]
    | dict[str, "BehaviorSpecificationExtensionValue"],
)
ToolAffordanceReference = Annotated[str, Field(min_length=1, pattern=r"\S")]


class ParticipantToolAffordance(SDLModel):
    """Authored participant-local binding from tool identity to governed behavior."""

    tool_ref: str | None = Field(default=None, min_length=1)
    action_contract_refs: list[ToolAffordanceReference] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    observation_boundary_refs: list[ToolAffordanceReference] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )

    @field_validator("action_contract_refs", "observation_boundary_refs")
    @classmethod
    def _require_unique_non_empty_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("tool affordance refs must be non-empty")
        if len(set(values)) != len(values):
            raise ValueError("tool affordance refs must be unique within each field")
        return values


def tool_affordance_reference(spec_name: str, affordance_id: str) -> str:
    """Return the stable authored reference for one nested affordance binding."""

    return f"behavior_specifications.{spec_name}.tool_affordances.{affordance_id}"


class ParticipantBehaviorSpecification(SDLModel):
    """First-class authored aggregate over participant behavior surfaces."""

    semantic_version: str
    lifecycle_state: ParticipantBehaviorSpecificationLifecycle = ParticipantBehaviorSpecificationLifecycle.ACTIVE
    participant_refs: list[str] = Field(default_factory=list)
    participant_role_refs: list[str] = Field(default_factory=list)
    action_contract_refs: list[str] = Field(default_factory=list)
    observation_boundary_refs: list[str] = Field(default_factory=list)
    outcome_interpretation_rule_refs: list[str] = Field(default_factory=list)
    authority_scope_refs: list[str] = Field(default_factory=list)
    behavior_mode: str | None = None
    ai_offensive_behavior_refs: list[str] = Field(default_factory=list)
    offensive_behavior_refs: list[str] = Field(default_factory=list)
    realization_profile_ref: str | None = None
    backend_feature_support_refs: list[str] = Field(default_factory=list)
    evidence_contract_refs: list[str] = Field(default_factory=list)
    tool_affordances: dict[PortableIdentifier, ParticipantToolAffordance] = Field(
        default_factory=dict,
        json_schema_extra={"additionalProperties": False},
    )
    extension_policy: str = "governed-extension"
    extensions: dict[str, BehaviorSpecificationExtensionValue] = Field(default_factory=dict)

    @field_validator("semantic_version", "extension_policy")
    @classmethod
    def _require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("behavior specification fields must be non-empty")
        return value

    @field_validator("behavior_mode", "realization_profile_ref")
    @classmethod
    def _require_optional_non_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("behavior specification optional fields must be non-empty when provided")
        return value

    @field_validator(
        "participant_refs",
        "participant_role_refs",
        "action_contract_refs",
        "observation_boundary_refs",
        "outcome_interpretation_rule_refs",
        "authority_scope_refs",
        "ai_offensive_behavior_refs",
        "offensive_behavior_refs",
        "backend_feature_support_refs",
        "evidence_contract_refs",
    )
    @classmethod
    def _require_unique_non_empty_refs(cls, values: list[str]) -> list[str]:
        for value in values:
            if not value.strip():
                raise ValueError("behavior specification refs must be non-empty")
        if len(set(values)) != len(values):
            raise ValueError("behavior specification refs must be unique within each field")
        return values

    @field_validator("extensions")
    @classmethod
    def _validate_extension_keys(
        cls, values: dict[str, BehaviorSpecificationExtensionValue]
    ) -> dict[str, BehaviorSpecificationExtensionValue]:
        invalid = sorted(key for key in values if not _BEHAVIOR_SPEC_EXTENSION_KEY_RE.fullmatch(key))
        if invalid:
            joined = ", ".join(invalid)
            raise ValueError(
                "behavior specification extension keys must match x-<owner>:<term> governed extension syntax: " + joined
            )
        return values

    @model_validator(mode="after")
    def _validate_aggregate_shape(self) -> ParticipantBehaviorSpecification:
        if self.extension_policy not in _BEHAVIOR_SPEC_EXTENSION_POLICIES:
            allowed = ", ".join(sorted(_BEHAVIOR_SPEC_EXTENSION_POLICIES))
            raise ValueError(f"behavior specification extension_policy must be one of: {allowed}")
        if self.extension_policy == "closed" and self.extensions:
            raise ValueError("behavior specification extensions require extension_policy governed-extension")
        if not self.participant_refs and not self.participant_role_refs:
            raise ValueError("behavior specifications require participant_refs or participant_role_refs")
        if not any(
            (
                self.action_contract_refs,
                self.observation_boundary_refs,
                self.outcome_interpretation_rule_refs,
                self.authority_scope_refs,
                self.behavior_mode,
                self.ai_offensive_behavior_refs,
                self.offensive_behavior_refs,
                self.realization_profile_ref,
                self.backend_feature_support_refs,
                self.evidence_contract_refs,
                self.tool_affordances,
            )
        ):
            raise ValueError("behavior specifications must aggregate at least one behavior surface reference")
        return self
