"""Portable contracts for run-local typed fact binding."""

from __future__ import annotations

from enum import Enum
from typing import Literal, TypeVar

from pydantic import Field, StrictBool, StrictFloat, StrictInt, StrictStr, field_validator, model_validator

from ..versions import RUNTIME_FACT_BINDING_PLANE_V1_SCHEMA_VERSION
from .base import ContractModel, NonEmptyString, Rfc3339DateTimeString


class RuntimeFactValueType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    REFERENCE = "reference"


class RuntimeFactSourceKind(str, Enum):
    OBSERVATION = "observation"
    DERIVED = "derived"
    TOOL_RESULT = "tool_result"
    SECRET_REFERENCE = "secret_reference"  # noqa: S105


class RuntimeFactScopeKind(str, Enum):
    RUN = "run"
    PARTICIPANT = "participant"
    EPISODE = "episode"
    WORKFLOW = "workflow"


class RuntimeFactSensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    SECRET = "secret"  # noqa: S105


class RuntimeFactAudience(str, Enum):
    PARTICIPANT = "participant"
    WORKFLOW = "workflow"
    PROTECTED_SINK = "protected_sink"


class RuntimeFactAbsenceDisposition(str, Enum):
    BLOCK = "block"
    FAIL = "fail"
    INAPPLICABLE = "inapplicable"


class RuntimeFactBindingDisposition(str, Enum):
    BOUND = "bound"
    ABSENT = "absent"
    STALE = "stale"
    AMBIGUOUS = "ambiguous"
    UNAUTHORIZED = "unauthorized"
    UNSUPPORTED = "unsupported"
    WRONG_TYPE = "wrong_type"
    WRONG_SCOPE = "wrong_scope"
    SECRET_UNAVAILABLE = "secret_unavailable"  # noqa: S105
    DISPATCH_FAILED = "dispatch_failed"


RuntimeFactScalar = StrictBool | StrictInt | StrictFloat | StrictStr
_ModelT = TypeVar("_ModelT")


def _unique(values: list[str], field_name: str) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} entries must be unique")
    return values


class RuntimeFactVisibilityModel(ContractModel):
    participant_addresses: list[NonEmptyString] = Field(default_factory=list)
    workflow_addresses: list[NonEmptyString] = Field(default_factory=list)
    operator_visible: bool = True

    @field_validator("participant_addresses", "workflow_addresses")
    @classmethod
    def _validate_unique_refs(cls, value: list[str], info: object) -> list[str]:
        return _unique(value, getattr(info, "field_name", "visibility"))


class RuntimeFactScopeModel(ContractModel):
    kind: RuntimeFactScopeKind
    run_id: NonEmptyString
    participant_address: NonEmptyString | None = None
    episode_id: NonEmptyString | None = None
    workflow_address: NonEmptyString | None = None

    @model_validator(mode="after")
    def _validate_scope_shape(self) -> RuntimeFactScopeModel:
        if self.kind == RuntimeFactScopeKind.RUN:
            if any((self.participant_address, self.episode_id, self.workflow_address)):
                raise ValueError("run-scoped facts cannot carry participant, episode, or workflow scope")
        elif self.kind == RuntimeFactScopeKind.PARTICIPANT:
            if self.participant_address is None or self.episode_id is not None or self.workflow_address is not None:
                raise ValueError("participant-scoped facts require only participant_address")
        elif self.kind == RuntimeFactScopeKind.EPISODE:
            if self.participant_address is None or self.episode_id is None or self.workflow_address is not None:
                raise ValueError("episode-scoped facts require participant_address and episode_id")
        elif self.kind == RuntimeFactScopeKind.WORKFLOW:
            if self.workflow_address is None or self.participant_address is not None or self.episode_id is not None:
                raise ValueError("workflow-scoped facts require only workflow_address")
        return self


class RuntimeFactDeclarationModel(ContractModel):
    fact_id: NonEmptyString
    value_type: RuntimeFactValueType
    source_kind: RuntimeFactSourceKind
    sensitivity: RuntimeFactSensitivity
    visibility: RuntimeFactVisibilityModel
    authority_refs: list[NonEmptyString] = Field(min_length=1)

    @field_validator("authority_refs")
    @classmethod
    def _validate_authority_refs(cls, value: list[str]) -> list[str]:
        return _unique(value, "authority_refs")

    @model_validator(mode="after")
    def _validate_secret_source_posture(self) -> RuntimeFactDeclarationModel:
        secret_source = self.source_kind == RuntimeFactSourceKind.SECRET_REFERENCE
        secret_sensitivity = self.sensitivity == RuntimeFactSensitivity.SECRET
        if secret_source != secret_sensitivity:
            raise ValueError("secret_reference source kind and secret sensitivity must be declared together")
        return self


class RuntimeFactVersionModel(ContractModel):
    fact_id: NonEmptyString
    version_id: NonEmptyString
    sequence: int = Field(ge=1)
    value_type: RuntimeFactValueType
    source_kind: RuntimeFactSourceKind
    sensitivity: RuntimeFactSensitivity
    scope: RuntimeFactScopeModel
    observed_at: Rfc3339DateTimeString
    expires_at: Rfc3339DateTimeString | None = None
    value: RuntimeFactScalar | None = None
    secret_ref: NonEmptyString | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_refs: list[NonEmptyString] = Field(min_length=1)
    provenance_refs: list[NonEmptyString] = Field(min_length=1)

    @field_validator("evidence_refs", "provenance_refs")
    @classmethod
    def _validate_unique_refs(cls, value: list[str], info: object) -> list[str]:
        return _unique(value, getattr(info, "field_name", "refs"))

    @model_validator(mode="after")
    def _validate_value_posture(self) -> RuntimeFactVersionModel:
        if self.sensitivity == RuntimeFactSensitivity.SECRET:
            if self.secret_ref is None or self.value is not None:
                raise ValueError("secret facts require secret_ref and cannot carry a portable value")
        elif self.value is None or self.secret_ref is not None:
            raise ValueError("non-secret facts require value and cannot carry secret_ref")
        if self.value is not None and not _value_matches_type(self.value, self.value_type):
            raise ValueError("fact value does not match value_type")
        return self


def _value_matches_type(value: RuntimeFactScalar, value_type: RuntimeFactValueType) -> bool:
    if value_type in {RuntimeFactValueType.STRING, RuntimeFactValueType.REFERENCE}:
        return isinstance(value, str)
    if value_type == RuntimeFactValueType.BOOLEAN:
        return isinstance(value, bool)
    if value_type == RuntimeFactValueType.INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    if value_type == RuntimeFactValueType.NUMBER:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


class RuntimeFactSinkModel(ContractModel):
    sink_id: NonEmptyString
    action_contract_address: NonEmptyString
    target_field: NonEmptyString
    value_type: RuntimeFactValueType
    allowed_source_kinds: list[RuntimeFactSourceKind] = Field(min_length=1)
    allowed_scope_kinds: list[RuntimeFactScopeKind] = Field(min_length=1)
    allowed_sensitivities: list[RuntimeFactSensitivity] = Field(min_length=1)
    max_age_seconds: int | None = Field(default=None, ge=0)
    authority_refs: list[NonEmptyString] = Field(min_length=1)
    audience: RuntimeFactAudience
    absence_disposition: RuntimeFactAbsenceDisposition

    @field_validator("action_contract_address")
    @classmethod
    def _validate_action_contract_address(cls, value: str) -> str:
        if not value.startswith("participant.action-contract."):
            raise ValueError("action_contract_address must be a compiled participant action-contract address")
        return value

    @field_validator("target_field")
    @classmethod
    def _validate_target_field(cls, value: str) -> str:
        if not value.startswith("input.") or len(value) == len("input."):
            raise ValueError("target_field must identify a run-local action input beneath 'input.'")
        return value

    @field_validator("allowed_source_kinds", "allowed_scope_kinds", "allowed_sensitivities", "authority_refs")
    @classmethod
    def _validate_unique_values(cls, value: list[object], info: object) -> list[object]:
        if len(value) != len(set(value)):
            raise ValueError(f"{getattr(info, 'field_name', 'values')} entries must be unique")
        return value


class RuntimeFactBindingSelectionModel(ContractModel):
    sink: RuntimeFactSinkModel
    candidate_fact_ids: list[NonEmptyString] = Field(default_factory=list)

    @field_validator("candidate_fact_ids")
    @classmethod
    def _validate_candidate_fact_ids(cls, value: list[str]) -> list[str]:
        return _unique(value, "candidate_fact_ids")


class RuntimeFactBindingRequestModel(ContractModel):
    run_id: NonEmptyString
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    workflow_address: NonEmptyString | None = None
    action_instance_id: NonEmptyString
    action_contract_address: NonEmptyString


class RuntimeFactBindingEventModel(ContractModel):
    event_id: NonEmptyString
    run_id: NonEmptyString
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    workflow_address: NonEmptyString | None = None
    action_instance_id: NonEmptyString
    action_contract_address: NonEmptyString
    sink_id: NonEmptyString
    target_field: NonEmptyString
    fact_id: NonEmptyString | None = None
    fact_version_id: NonEmptyString | None = None
    disposition: RuntimeFactBindingDisposition
    sensitivity: RuntimeFactSensitivity | None = None
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    provenance_refs: list[NonEmptyString] = Field(default_factory=list)
    authorization_refs: list[NonEmptyString] = Field(default_factory=list)
    redacted: bool = False
    reason_code: NonEmptyString | None = None


class RuntimeFactProjectionModel(ContractModel):
    fact_id: NonEmptyString
    fact_version_id: NonEmptyString
    value_type: RuntimeFactValueType
    source_kind: RuntimeFactSourceKind
    sensitivity: RuntimeFactSensitivity
    scope: RuntimeFactScopeModel
    observed_at: Rfc3339DateTimeString
    value: RuntimeFactScalar | None = None
    redacted: bool = False
    secret_reference_present: bool = False
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    provenance_refs: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_projection_posture(self) -> RuntimeFactProjectionModel:
        if self.sensitivity == RuntimeFactSensitivity.SECRET:
            if self.value is not None or not self.redacted or not self.secret_reference_present:
                raise ValueError("secret fact projections must be redacted and value-free")
        elif self.value is None or self.redacted or self.secret_reference_present:
            raise ValueError("non-secret fact projections require an unredacted value")
        return self


class RuntimeFactBindingPlaneModel(ContractModel):
    schema_version: Literal[RUNTIME_FACT_BINDING_PLANE_V1_SCHEMA_VERSION] = RUNTIME_FACT_BINDING_PLANE_V1_SCHEMA_VERSION
    declarations: list[RuntimeFactDeclarationModel] = Field(default_factory=list)
    sinks: list[RuntimeFactSinkModel] = Field(default_factory=list)
    versions: list[RuntimeFactVersionModel] = Field(default_factory=list)
    events: list[RuntimeFactBindingEventModel] = Field(default_factory=list)
    projections: list[RuntimeFactProjectionModel] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_references(self) -> RuntimeFactBindingPlaneModel:
        declarations = _unique_index(self.declarations, "fact_id", "declaration")
        sinks = _unique_index(self.sinks, "sink_id", "sink")
        versions = _unique_index(self.versions, "version_id", "fact version")
        _unique_index(self.events, "event_id", "binding event")

        sequences: dict[str, list[int]] = {}
        for version in self.versions:
            declaration = declarations.get(version.fact_id)
            if declaration is None:
                raise ValueError(f"fact version fact_id {version.fact_id!r} must resolve to a declaration")
            if (
                version.value_type != declaration.value_type
                or version.source_kind != declaration.source_kind
                or version.sensitivity != declaration.sensitivity
            ):
                raise ValueError("fact version type, source, and sensitivity must match its declaration")
            sequences.setdefault(version.fact_id, []).append(version.sequence)
        for fact_id, fact_sequences in sequences.items():
            expected = list(range(1, len(fact_sequences) + 1))
            if sorted(fact_sequences) != expected:
                raise ValueError(f"fact version sequence for {fact_id!r} must be contiguous from 1")

        for event in self.events:
            sink = sinks.get(event.sink_id)
            if sink is None:
                raise ValueError(f"binding event sink_id {event.sink_id!r} must resolve to a sink")
            if event.target_field != sink.target_field or event.action_contract_address != sink.action_contract_address:
                raise ValueError("binding event target and action contract must match its sink")
            if event.disposition == RuntimeFactBindingDisposition.BOUND:
                if event.fact_id is None or event.fact_version_id is None:
                    raise ValueError("bound events require fact_id and fact_version_id")
            if event.fact_version_id is not None:
                version = versions.get(event.fact_version_id)
                if version is None:
                    raise ValueError(
                        f"binding event fact_version_id {event.fact_version_id!r} must resolve to a fact version"
                    )
                if event.fact_id != version.fact_id:
                    raise ValueError("binding event fact_id must match its fact version")
                declaration = declarations[version.fact_id]
                _validate_event_version_metadata(event, sink, version, declaration)

        for projection in self.projections:
            version = versions.get(projection.fact_version_id)
            if version is None:
                raise ValueError(
                    f"projection fact_version_id {projection.fact_version_id!r} must resolve to a fact version"
                )
            if projection.fact_id != version.fact_id:
                raise ValueError("projection fact_id must match its fact version")
            _validate_projection_version_metadata(projection, version)
        return self


def _validate_event_version_metadata(
    event: RuntimeFactBindingEventModel,
    sink: RuntimeFactSinkModel,
    version: RuntimeFactVersionModel,
    declaration: RuntimeFactDeclarationModel,
) -> None:
    expected_redaction = version.sensitivity == RuntimeFactSensitivity.SECRET
    metadata_matches = (
        event.sensitivity == version.sensitivity
        and event.evidence_refs == version.evidence_refs
        and event.provenance_refs == version.provenance_refs
        and event.redacted == expected_redaction
    )
    if not metadata_matches:
        raise ValueError("binding event metadata must match its immutable fact version")
    if event.disposition != RuntimeFactBindingDisposition.BOUND:
        return
    sink_policy_matches = (
        version.value_type == sink.value_type
        and version.source_kind in sink.allowed_source_kinds
        and version.scope.kind in sink.allowed_scope_kinds
        and version.sensitivity in sink.allowed_sensitivities
        and event.run_id == version.scope.run_id
        and version.scope.participant_address in {None, event.participant_address}
        and version.scope.episode_id in {None, event.episode_id}
        and version.scope.workflow_address in {None, event.workflow_address}
        and (set(declaration.authority_refs) | set(sink.authority_refs)).issubset(event.authorization_refs)
    )
    if not sink_policy_matches:
        raise ValueError("bound event fact version must satisfy its compiled sink policy")
    if sink.audience == RuntimeFactAudience.PARTICIPANT:
        visible = event.participant_address in declaration.visibility.participant_addresses
    elif sink.audience == RuntimeFactAudience.WORKFLOW:
        visible = bool(event.workflow_address and event.workflow_address in declaration.visibility.workflow_addresses)
    else:
        visible = event.participant_address in declaration.visibility.participant_addresses
    if not visible or (
        version.sensitivity == RuntimeFactSensitivity.SECRET and sink.audience != RuntimeFactAudience.PROTECTED_SINK
    ):
        raise ValueError("bound event fact version must satisfy sink visibility and audience policy")


def _validate_projection_version_metadata(
    projection: RuntimeFactProjectionModel,
    version: RuntimeFactVersionModel,
) -> None:
    secret = version.sensitivity == RuntimeFactSensitivity.SECRET
    metadata_matches = (
        projection.value_type == version.value_type
        and projection.source_kind == version.source_kind
        and projection.sensitivity == version.sensitivity
        and projection.scope == version.scope
        and projection.observed_at == version.observed_at
        and projection.confidence == version.confidence
        and projection.evidence_refs == version.evidence_refs
        and projection.provenance_refs == version.provenance_refs
        and projection.value == (None if secret else version.value)
        and projection.redacted == secret
        and projection.secret_reference_present == secret
    )
    if not metadata_matches:
        raise ValueError("projection metadata must match its immutable fact version")


def _unique_index(items: list[_ModelT], field_name: str, kind: str) -> dict[str, _ModelT]:
    indexed: dict[str, _ModelT] = {}
    for item in items:
        key = getattr(item, field_name)
        if key in indexed:
            raise ValueError(f"{kind} {field_name} {key!r} must be unique")
        indexed[key] = item
    return indexed


__all__ = (
    "RuntimeFactAbsenceDisposition",
    "RuntimeFactAudience",
    "RuntimeFactBindingDisposition",
    "RuntimeFactBindingEventModel",
    "RuntimeFactBindingPlaneModel",
    "RuntimeFactProjectionModel",
    "RuntimeFactBindingRequestModel",
    "RuntimeFactBindingSelectionModel",
    "RuntimeFactDeclarationModel",
    "RuntimeFactScopeKind",
    "RuntimeFactScopeModel",
    "RuntimeFactSensitivity",
    "RuntimeFactSinkModel",
    "RuntimeFactSourceKind",
    "RuntimeFactValueType",
    "RuntimeFactVersionModel",
    "RuntimeFactVisibilityModel",
)
