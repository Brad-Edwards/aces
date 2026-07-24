"""Provider-neutral deterministic live-activity authoring declarations."""

from __future__ import annotations

import math
from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from ._base import SDLModel, WholeFieldVariableReference, is_variable_ref, parse_enum_or_var, parse_int_or_var
from ._identifiers import PortableIdentifier
from .orchestration import parse_duration

LIVE_ACTIVITY_CONTRACT_PROFILE = "aces-live-activity/v1"
ACTIVITY_SCHEDULE_PROFILE = "finite-logical-schedule/v1"
ACTIVITY_LIFECYCLE_PROFILE = "range-lifecycle/v1"
ACTIVITY_READBACK_PROFILE = "evidence-readback/v1"
ACTIVITY_TELEMETRY_PROFILE = "evidence-provenance/v1"
ACTIVITY_RANDOM_ADDRESS_PROFILE = "activity-random-address/v1"
ACTIVITY_TRANSFORM_PROFILE = "bounded-integer/v1"


class ActivityProtocol(str, Enum):
    HTTP_API = "http_api"
    SMTP = "smtp"
    IMAP = "imap"
    LDAP = "ldap"
    DATABASE = "database"
    FILE_SERVICE = "file_service"


class ActivityOperation(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SEND = "send"
    RECEIVE = "receive"
    QUERY = "query"
    LIST = "list"
    AUTHENTICATE = "authenticate"


class ActivityReadbackClass(str, Enum):
    NONE = "none"
    STATUS = "status"
    OBJECT_STATE = "object_state"
    COLLECTION_STATE = "collection_state"


class ActivityParameterKind(str, Enum):
    HISTORICAL_OBJECT_REF = "historical_object_ref"
    CONTENT_REF = "content_ref"
    ENTITY_REF = "entity_ref"
    ACCOUNT_REF = "account_ref"


class ActivityCapabilityRequirement(SDLModel):
    profile: Literal["protocol-operation/v1"] = "protocol-operation/v1"
    protocol: ActivityProtocol
    operation: ActivityOperation

    @property
    def identity(self) -> str:
        return f"{self.profile}:{self.protocol.value}:{self.operation.value}"


class ActivityTemplateParameter(SDLModel):
    kind: ActivityParameterKind
    required: bool = True


class ActivityTemplate(SDLModel):
    version: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=1024)
    capability: ActivityCapabilityRequirement
    parameters: dict[PortableIdentifier, ActivityTemplateParameter] = Field(
        default_factory=dict,
        max_length=64,
    )
    readback_class: ActivityReadbackClass


class BackgroundActivityActor(SDLModel):
    entity_ref: str = Field(min_length=1, max_length=2048)
    account_ref: str = Field(min_length=1, max_length=2048)
    deployment_tenant_ref: str = Field(min_length=1, max_length=2048)
    operating_scope_refs: list[str] = Field(min_length=1, max_length=256)

    @field_validator("operating_scope_refs")
    @classmethod
    def _unique_scope_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("activity actor operating_scope_refs must be non-empty")
        if len(values) != len(set(values)):
            raise ValueError("activity actor operating_scope_refs must be unique")
        return values


class ActivityExecutionContext(SDLModel):
    deployment_tenant_ref: str = Field(min_length=1, max_length=2048)
    account_ref: str = Field(min_length=1, max_length=2048)
    target_service_ref: str = Field(min_length=1, max_length=2048)
    protocol: ActivityProtocol | WholeFieldVariableReference

    @field_validator("protocol", mode="before")
    @classmethod
    def _protocol_or_variable(cls, value: object) -> ActivityProtocol | str:
        return parse_enum_or_var(value, ActivityProtocol, field_name="protocol")


class ActivityParameterBinding(SDLModel):
    parameter_ref: PortableIdentifier
    value_ref: str = Field(min_length=1, max_length=2048)


class ActivityRetryPolicy(SDLModel):
    max_attempts: int | WholeFieldVariableReference = Field(default=1)
    interval_seconds: int | str = Field(default=1)

    @field_validator("max_attempts", mode="before")
    @classmethod
    def _bounded_attempts(cls, value: object) -> int | str:
        return parse_int_or_var(value, minimum=1, maximum=64, field_name="max_attempts")

    @field_validator("interval_seconds", mode="before")
    @classmethod
    def _positive_interval(cls, value: object) -> int | str:
        parsed = parse_duration(value)  # type: ignore[arg-type]
        if not is_variable_ref(parsed) and parsed < 1:
            raise ValueError("retry interval_seconds must be positive")
        return parsed


class LogicalActivitySchedule(SDLModel):
    profile: Literal["finite-logical-schedule/v1"] = ACTIVITY_SCHEDULE_PROFILE
    time_domain: Literal["logical"] = "logical"
    anchor_seconds: int | WholeFieldVariableReference = Field(default=0)
    interval_seconds: int | str
    horizon_seconds: int | str | None = None
    max_occurrences: int | WholeFieldVariableReference

    @field_validator("anchor_seconds", mode="before")
    @classmethod
    def _anchor(cls, value: object) -> int | str:
        return parse_int_or_var(value, minimum=0, field_name="anchor_seconds")

    @field_validator("interval_seconds", "horizon_seconds", mode="before")
    @classmethod
    def _duration(cls, value: object) -> int | str | None:
        if value is None:
            return None
        parsed = parse_duration(value)  # type: ignore[arg-type]
        if not is_variable_ref(parsed) and parsed < 1:
            raise ValueError("activity schedule durations must be positive")
        return parsed

    @field_validator("max_occurrences", mode="before")
    @classmethod
    def _occurrence_bound(cls, value: object) -> int | str:
        return parse_int_or_var(value, minimum=1, maximum=1_000_000, field_name="max_occurrences")

    def finite_occurrence_count(self) -> int:
        if any(
            is_variable_ref(value)
            for value in (self.anchor_seconds, self.interval_seconds, self.horizon_seconds, self.max_occurrences)
        ):
            raise ValueError("activity schedule occurrence count requires a concrete schedule")
        bound = int(self.max_occurrences)
        if self.horizon_seconds is None:
            return bound
        horizon_bound = math.ceil(int(self.horizon_seconds) / int(self.interval_seconds))
        return min(bound, horizon_bound)


class ActivityAction(SDLModel):
    template_ref: str = Field(min_length=1, max_length=2048)
    actor_ref: PortableIdentifier
    execution_context_ref: PortableIdentifier
    schedule_ref: PortableIdentifier
    parameter_bindings: list[ActivityParameterBinding] = Field(default_factory=list, max_length=64)
    retry: ActivityRetryPolicy = Field(default_factory=ActivityRetryPolicy)

    @field_validator("parameter_bindings")
    @classmethod
    def _unique_parameter_bindings(cls, values: list[ActivityParameterBinding]) -> list[ActivityParameterBinding]:
        names = [value.parameter_ref for value in values]
        if len(names) != len(set(names)):
            raise ValueError("activity action parameter bindings must be unique")
        return values


class ActivityDependencyKind(str, Enum):
    ORDERING = "ordering"
    REFRESH = "refresh"


class ActivityDependency(SDLModel):
    action_ref: PortableIdentifier
    depends_on_ref: PortableIdentifier
    kind: ActivityDependencyKind


class ExactRational(SDLModel):
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=1)

    @model_validator(mode="after")
    def _canonical_fraction(self) -> ExactRational:
        if math.gcd(self.numerator, self.denominator) != 1:
            raise ValueError("exact rational quantities must be in lowest terms")
        return self


class ActivityResourceDimension(str, Enum):
    OPERATIONS = "operations"
    BYTES = "bytes"
    CONNECTIONS = "connections"
    CPU_MILLISECONDS = "cpu_milliseconds"


class ActivityResourceUnit(str, Enum):
    OPERATION = "operation"
    BYTE = "byte"
    CONNECTION = "connection"
    CPU_MILLISECOND = "cpu_millisecond"


class ActivityBudgetEnvelope(SDLModel):
    dimension: ActivityResourceDimension
    unit: ActivityResourceUnit
    window_seconds: int | str
    action_demands: dict[PortableIdentifier, ExactRational] = Field(min_length=1, max_length=4096)
    range_capacity: ExactRational
    fleet_capacity: ExactRational
    participant_reservation: ExactRational

    @field_validator("window_seconds", mode="before")
    @classmethod
    def _window(cls, value: object) -> int | str:
        parsed = parse_duration(value)  # type: ignore[arg-type]
        if not is_variable_ref(parsed) and parsed < 1:
            raise ValueError("activity budget window_seconds must be positive")
        return parsed


class ActivityLifecyclePolicy(SDLModel):
    profile: Literal["range-lifecycle/v1"] = ACTIVITY_LIFECYCLE_PROFILE
    on_start: Literal["admit_new"]
    on_resume: Literal["admit_new"]
    on_pause: Literal["suspend_new"]
    in_flight_on_pause: Literal["finish", "cancel"]
    on_drain: Literal["drain"]
    on_reset_generation_advance: Literal["discard_stale"]
    on_teardown: Literal["discard_pending"]
    drain_timeout_seconds: int | str

    @field_validator("drain_timeout_seconds", mode="before")
    @classmethod
    def _drain_timeout(cls, value: object) -> int | str:
        parsed = parse_duration(value)  # type: ignore[arg-type]
        if not is_variable_ref(parsed) and parsed < 1:
            raise ValueError("activity lifecycle drain_timeout_seconds must be positive")
        return parsed


class ActivityReadbackPolicy(SDLModel):
    profile: Literal["evidence-readback/v1"] = ACTIVITY_READBACK_PROFILE
    action_refs: list[PortableIdentifier] = Field(min_length=1, max_length=4096)
    observability_refs: list[str] = Field(min_length=1, max_length=256)
    evidence_requirement_refs: list[str] = Field(min_length=1, max_length=256)
    participant_proof: Literal[False] = False

    @field_validator("action_refs", "observability_refs", "evidence_requirement_refs")
    @classmethod
    def _unique_references(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("activity readback references must be unique")
        return values


class ActivityTelemetryPolicy(SDLModel):
    profile: Literal["evidence-provenance/v1"] = ACTIVITY_TELEMETRY_PROFILE
    observability_refs: list[str] = Field(min_length=1, max_length=256)
    evidence_requirement_refs: list[str] = Field(min_length=1, max_length=256)
    participant_proof: Literal[False] = False
    emits_participant_receipts: Literal[False] = False
    establishes_objective_truth: Literal[False] = False

    @field_validator("observability_refs", "evidence_requirement_refs")
    @classmethod
    def _unique_references(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("activity telemetry references must be unique")
        return values


class ActivityPublicSeed(SDLModel):
    kind: Literal["public-seed"]
    encoding: Literal["hex-fixed-width"]
    value: str = Field(pattern=r"^[0-9a-f]{64}$")


class ActivityGovernedEntropyRef(SDLModel):
    kind: Literal["governed-reference"]
    reference_id: str = Field(min_length=1, max_length=256)
    reference_version: str = Field(min_length=1, max_length=128)


ActivityRootEntropy = Annotated[
    ActivityPublicSeed | ActivityGovernedEntropyRef,
    Field(discriminator="kind"),
]


class ActivityRandomnessBinding(SDLModel):
    random_stream_profile: Literal["blake3-xof-v1"] = "blake3-xof-v1"
    address_profile: Literal["activity-random-address/v1"] = ACTIVITY_RANDOM_ADDRESS_PROFILE
    transform_profile: Literal["bounded-integer/v1"] = ACTIVITY_TRANSFORM_PROFILE
    root_entropy: ActivityRootEntropy


class ActivityProfile(SDLModel):
    version: str = Field(min_length=1, max_length=128)
    contract_profile: Literal["aces-live-activity/v1"] = LIVE_ACTIVITY_CONTRACT_PROFILE
    historical_baseline_ref: str = Field(min_length=1, max_length=2048)
    randomness: ActivityRandomnessBinding
    actors: dict[PortableIdentifier, BackgroundActivityActor] = Field(min_length=1, max_length=256)
    execution_contexts: dict[PortableIdentifier, ActivityExecutionContext] = Field(min_length=1, max_length=256)
    schedules: dict[PortableIdentifier, LogicalActivitySchedule] = Field(min_length=1, max_length=256)
    actions: dict[PortableIdentifier, ActivityAction] = Field(min_length=1, max_length=4096)
    dependencies: list[ActivityDependency] = Field(default_factory=list, max_length=16384)
    budgets: list[ActivityBudgetEnvelope] = Field(min_length=1, max_length=256)
    lifecycle: ActivityLifecyclePolicy
    readback: ActivityReadbackPolicy
    telemetry: ActivityTelemetryPolicy


__all__ = [
    "ACTIVITY_LIFECYCLE_PROFILE",
    "ACTIVITY_RANDOM_ADDRESS_PROFILE",
    "ACTIVITY_READBACK_PROFILE",
    "ACTIVITY_SCHEDULE_PROFILE",
    "ACTIVITY_TELEMETRY_PROFILE",
    "ACTIVITY_TRANSFORM_PROFILE",
    "LIVE_ACTIVITY_CONTRACT_PROFILE",
    "ActivityAction",
    "ActivityBudgetEnvelope",
    "ActivityCapabilityRequirement",
    "ActivityDependency",
    "ActivityDependencyKind",
    "ActivityExecutionContext",
    "ActivityLifecyclePolicy",
    "ActivityOperation",
    "ActivityParameterBinding",
    "ActivityParameterKind",
    "ActivityProfile",
    "ActivityProtocol",
    "ActivityRandomnessBinding",
    "ActivityReadbackClass",
    "ActivityReadbackPolicy",
    "ActivityResourceDimension",
    "ActivityResourceUnit",
    "ActivityRetryPolicy",
    "ActivityRootEntropy",
    "ActivityTelemetryPolicy",
    "ActivityTemplate",
    "ActivityTemplateParameter",
    "BackgroundActivityActor",
    "ExactRational",
    "LogicalActivitySchedule",
]
