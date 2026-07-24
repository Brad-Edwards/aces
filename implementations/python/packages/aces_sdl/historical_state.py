"""Provider-neutral authored historical-state declarations."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from ._base import SDLModel
from ._identifiers import PortableIdentifier

HISTORICAL_ADDRESS_PROFILE = "aces-historical-semantic-address/v1"
HISTORICAL_TIME_PROFILE = "logical-order/v1"


class HistoricalActorAuthority(str, Enum):
    """Incumbent declaration family that supplies an actor's identity."""

    ENTITY = "entity"
    AGENT = "agent"
    ACCOUNT = "account"
    SERVICE = "service"


class HistoricalActorRole(str, Enum):
    """One baseline-local role without product-authorization meaning."""

    AUTHOR = "author"
    SENDER = "sender"
    RECIPIENT = "recipient"
    OWNER = "owner"
    OBSERVER = "observer"
    SERVICE = "service"


class HistoricalActorBinding(SDLModel):
    """Baseline-local role bound to one incumbent SDL declaration."""

    authority: HistoricalActorAuthority
    authority_ref: str = Field(min_length=1, max_length=2048)
    role: HistoricalActorRole


class HistoricalObjectKind(str, Enum):
    """Portable semantic object families admitted by the initial profile."""

    MESSAGE = "message"
    CASE = "case"
    ALERT = "alert"
    TICKET = "ticket"
    DASHBOARD = "dashboard"
    FILE = "file"
    RECORD = "record"


class HistoricalContentSensitivity(str, Enum):
    """Bounded participant-content sensitivity, excluding secret material."""

    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class HistoricalObject(SDLModel):
    """One baseline-local semantic object, independent of product identity."""

    kind: HistoricalObjectKind
    writer_actor_ref: str = Field(min_length=1, max_length=2048)
    title: str = Field(default="", max_length=256)
    summary: str = Field(default="", max_length=1024)
    content_ref: str = Field(default="", max_length=2048)
    sensitivity: HistoricalContentSensitivity = HistoricalContentSensitivity.INTERNAL


class HistoricalEventOperation(str, Enum):
    """Portable state transition performed by one historical event."""

    CREATE = "create"
    UPDATE = "update"
    LINK = "link"
    UNLINK = "unlink"
    DELETE = "delete"
    RESTORE = "restore"


class HistoricalEvent(SDLModel):
    """One finite event in a baseline-owned logical history."""

    order: int = Field(ge=0)
    operation: HistoricalEventOperation
    actor_ref: str = Field(min_length=1, max_length=2048)
    object_refs: list[str] = Field(min_length=1, max_length=256)
    predecessor_refs: list[str] = Field(default_factory=list, max_length=256)
    cause_refs: list[str] = Field(default_factory=list, max_length=256)
    relationship_refs: list[str] = Field(default_factory=list, max_length=256)
    display_instant: str = Field(
        default="",
        max_length=64,
        pattern=(
            r"^(?:|\d{4}-\d{2}-\d{2}[Tt](?:[01]\d|2[0-3]):[0-5]\d:"
            r"(?:[0-5]\d|60)(?:\.\d+)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d))$"
        ),
    )
    relative_offset_seconds: int | None = Field(default=None, ge=0)

    @field_validator("object_refs", "predecessor_refs", "cause_refs", "relationship_refs")
    @classmethod
    def _unique_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("historical event references must be non-empty")
        if len(values) != len(set(values)):
            raise ValueError("historical event references must be unique")
        return values

    @model_validator(mode="after")
    def _validate_relationship_shape(self) -> HistoricalEvent:
        is_link_operation = self.operation in {HistoricalEventOperation.LINK, HistoricalEventOperation.UNLINK}
        if is_link_operation and not self.relationship_refs:
            raise ValueError("link and unlink historical events require relationship_refs")
        if not is_link_operation and self.relationship_refs:
            raise ValueError("relationship_refs are valid only for link and unlink historical events")
        return self


class HistoricalObjectLinkKind(str, Enum):
    """Governed semantic relationship between two historical objects."""

    CONTAINS = "contains"
    REPLIES_TO = "replies_to"
    REFERENCES = "references"
    DUPLICATES = "duplicates"
    ASSOCIATED_WITH = "associated_with"


class RelationshipHistoricalObjectLink(SDLModel):
    """Closed typed detail for a historical-object Relationship edge."""

    kind: HistoricalObjectLinkKind


class HistoricalMaterializationInterface(str, Enum):
    """Versioned provider-neutral native materialization interface profiles."""

    NATIVE_MESSAGE_V1 = "native-message/v1"
    NATIVE_CASE_V1 = "native-case/v1"
    NATIVE_ALERT_V1 = "native-alert/v1"
    NATIVE_TICKET_V1 = "native-ticket/v1"
    NATIVE_DASHBOARD_V1 = "native-dashboard/v1"
    NATIVE_FILE_V1 = "native-file/v1"
    NATIVE_RECORD_V1 = "native-record/v1"


class HistoricalReadbackProjection(str, Enum):
    """Governed participant-visible projection used for native readback."""

    OBJECT_V1 = "participant-visible-object/v1"
    LINKS_V1 = "participant-visible-links/v1"
    OBJECT_AND_LINKS_V1 = "participant-visible-object-and-links/v1"


class HistoricalObservationPoint(str, Enum):
    """Authored boundary at which a readback assertion is required."""

    AFTER_MATERIALIZATION = "after_materialization"
    AFTER_HISTORY = "after_history"


class HistoricalReadbackRequirement(SDLModel):
    """Participant-equivalent readback over existing Assertion declarations."""

    object_ref: str = Field(min_length=1, max_length=2048)
    assertion_refs: list[str] = Field(min_length=1, max_length=256)
    observation_boundary_ref: str = Field(min_length=1, max_length=2048)
    projection_profile: HistoricalReadbackProjection
    observation_point: HistoricalObservationPoint

    @field_validator("assertion_refs")
    @classmethod
    def _unique_assertions(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("historical readback assertion_refs must be unique")
        return values


class HistoricalMaterializationBinding(SDLModel):
    """Objects bound to one logical service and one portable interface."""

    object_refs: list[str] = Field(min_length=1, max_length=256)
    target_service_ref: str = Field(min_length=1, max_length=2048)
    interface_profile: HistoricalMaterializationInterface
    deployment_tenant_ref: str = Field(min_length=1, max_length=2048)
    deployment_cell_ref: str = Field(min_length=1, max_length=2048)
    reset_owner_relationship_ref: str = Field(min_length=1, max_length=2048)
    ordering_dependencies: list[str] = Field(default_factory=list, max_length=256)
    readback_requirement_refs: list[str] = Field(min_length=1, max_length=256)

    @field_validator("object_refs", "ordering_dependencies", "readback_requirement_refs")
    @classmethod
    def _unique_binding_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("historical materialization references must be non-empty")
        if len(values) != len(set(values)):
            raise ValueError("historical materialization references must be unique")
        return values


class HistoricalBaseline(SDLModel):
    """One closed authored authority for deterministic historical state."""

    version: str = Field(min_length=1, max_length=128)
    address_profile: Literal["aces-historical-semantic-address/v1"] = HISTORICAL_ADDRESS_PROFILE
    history_time_profile: Literal["logical-order/v1"] = HISTORICAL_TIME_PROFILE
    range_instance_id: str = Field(min_length=1, max_length=2048)
    deployment_tenant_ref: str = Field(min_length=1, max_length=2048)
    deployment_cell_ref: str = Field(min_length=1, max_length=2048)
    reset_generation_id: str = Field(min_length=1, max_length=2048)
    reset_owner_relationship_ref: str = Field(min_length=1, max_length=2048)
    description: str = Field(default="", max_length=1024)
    actors: dict[PortableIdentifier, HistoricalActorBinding] = Field(min_length=1, max_length=256)
    objects: dict[PortableIdentifier, HistoricalObject] = Field(min_length=1, max_length=4096)
    events: dict[PortableIdentifier, HistoricalEvent] = Field(min_length=1, max_length=16384)
    relationship_refs: list[str] = Field(default_factory=list, max_length=4096)
    materialization_bindings: dict[PortableIdentifier, HistoricalMaterializationBinding] = Field(
        min_length=1,
        max_length=4096,
    )
    readback_requirements: dict[PortableIdentifier, HistoricalReadbackRequirement] = Field(
        min_length=1,
        max_length=4096,
    )

    @field_validator("relationship_refs")
    @classmethod
    def _unique_relationship_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("historical baseline relationship_refs must be non-empty")
        if len(values) != len(set(values)):
            raise ValueError("historical baseline relationship_refs must be unique")
        return values


__all__ = [
    "HISTORICAL_ADDRESS_PROFILE",
    "HISTORICAL_TIME_PROFILE",
    "HistoricalActorAuthority",
    "HistoricalActorBinding",
    "HistoricalActorRole",
    "HistoricalBaseline",
    "HistoricalContentSensitivity",
    "HistoricalEvent",
    "HistoricalEventOperation",
    "HistoricalMaterializationBinding",
    "HistoricalMaterializationInterface",
    "HistoricalObject",
    "HistoricalObjectKind",
    "HistoricalObjectLinkKind",
    "HistoricalObservationPoint",
    "HistoricalReadbackProjection",
    "HistoricalReadbackRequirement",
    "RelationshipHistoricalObjectLink",
]
