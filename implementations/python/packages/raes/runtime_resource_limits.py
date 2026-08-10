"""Portable process-resource limit policy owned by runtime operational policy."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import Field, ValidationInfo, field_validator, model_validator
from raes_contracts.apparatus import ProcessResourceLimitCapability
from raes_contracts.canonical import canonical_json_digest
from raes_contracts.vocabulary import ProcessResourceLimitKind, ProcessResourceLimitScope

from ._base import SDLModel, WholeFieldVariableReference, contains_variable_token, parse_int_or_var
from .runtime_capabilities import (
    RuntimeProcessIdentity,
    RuntimeProcessRole,
)

RuntimeProcessLimitResource = ProcessResourceLimitKind
RuntimeProcessLimitScope = ProcessResourceLimitScope
RuntimeProcessLimitValue = Annotated[int, Field(ge=0)] | Literal["unlimited"] | WholeFieldVariableReference

__all__ = [
    "RuntimeProcessLimitResource",
    "RuntimeProcessLimitScope",
    "RuntimeProcessLimitValue",
    "RuntimeProcessResourceLimit",
    "process_resource_limit_identity_digest",
    "process_resource_limit_identity_payload",
    "process_resource_limit_capability_admits",
    "process_resource_limit_domain_admits",
    "process_resource_limit_subject_matches",
    "process_resource_limit_subject_projection",
    "project_process_resource_limit",
]


def _parse_limit_value(value: object, *, field_name: str) -> RuntimeProcessLimitValue:
    if value == "unlimited":
        return "unlimited"
    return parse_int_or_var(value, minimum=0, field_name=field_name)


def _subject_has_structural_selector(subject: RuntimeProcessIdentity) -> bool:
    return bool(
        subject.name
        or subject.pid is not None
        or subject.parent_pid is not None
        or subject.user
        or subject.group
        or subject.command
        or subject.working_directory
        or subject.role != RuntimeProcessRole.OTHER
    )


def _subject_has_stable_projected_selector(subject: RuntimeProcessIdentity) -> bool:
    return bool(
        subject.name
        or subject.pid is not None
        or subject.parent_pid is not None
        or subject.user
        or subject.group
        or subject.working_directory
        or subject.role != RuntimeProcessRole.OTHER
    )


def _subject_has_variable(subject: RuntimeProcessIdentity) -> bool:
    values: tuple[object, ...] = (
        subject.name,
        subject.pid,
        subject.parent_pid,
        subject.user,
        subject.group,
        *subject.command,
        subject.command_redacted,
        subject.working_directory,
        subject.role,
    )
    return any(isinstance(value, str) and contains_variable_token(value) for value in values)


class RuntimeProcessResourceLimit(SDLModel):
    """One portable soft/hard process limit for a selected process or subtree."""

    resource: RuntimeProcessLimitResource
    soft: RuntimeProcessLimitValue
    hard: RuntimeProcessLimitValue
    subject: RuntimeProcessIdentity
    scope: RuntimeProcessLimitScope = RuntimeProcessLimitScope.PROCESS
    description: str = ""

    @field_validator("soft", "hard", mode="before")
    @classmethod
    def parse_limit_value(cls, value: object, info: ValidationInfo) -> RuntimeProcessLimitValue:
        return _parse_limit_value(value, field_name=info.field_name)

    @model_validator(mode="after")
    def validate_limit(self) -> RuntimeProcessResourceLimit:
        if _subject_has_variable(self.subject):
            raise ValueError("runtime process resource limit variables are permitted only in soft and hard values")
        if self.subject.command_redacted is True and self.subject.command:
            raise ValueError("runtime process resource limit redacted command must be omitted from the selector")
        if self.subject.command_redacted is True and not _subject_has_stable_projected_selector(self.subject):
            raise ValueError("runtime process resource limit redacted command requires a stable projected selector")
        if not _subject_has_structural_selector(self.subject):
            raise ValueError("runtime process resource limit subject requires a structural selector")
        if contains_variable_token(self.description):
            raise ValueError("runtime process resource limit variables are permitted only in soft and hard values")
        if isinstance(self.soft, int) and isinstance(self.hard, int) and self.soft > self.hard:
            raise ValueError("runtime process resource limit soft value must not exceed hard value")
        if self.soft == "unlimited" and self.hard != "unlimited":
            raise ValueError("runtime process resource limit unlimited soft value requires unlimited hard value")
        return self


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def process_resource_limit_subject_projection(
    subject: RuntimeProcessIdentity | Mapping[str, object],
) -> dict[str, object]:
    """Return the lossless, portable selector used at every process-limit seam."""

    model = subject if isinstance(subject, RuntimeProcessIdentity) else RuntimeProcessIdentity.model_validate(subject)
    return {
        "name": model.name,
        "pid": model.pid,
        "parent_pid": model.parent_pid,
        "command": list(model.command),
        "command_redacted": model.command_redacted,
        "role": _enum_value(model.role),
        "user": model.user,
        "group": model.group,
        "working_directory": model.working_directory,
    }


def _selector_field_is_active(field_name: str, value: object) -> bool:
    if field_name in {"pid", "parent_pid"}:
        return value is not None
    if field_name == "role":
        return value != RuntimeProcessRole.OTHER.value
    if field_name == "command_redacted":
        return value is True
    return bool(value)


def process_resource_limit_subject_matches(
    selector: RuntimeProcessIdentity | Mapping[str, object],
    candidate: RuntimeProcessIdentity | Mapping[str, object],
) -> bool:
    """Return whether an inventory process satisfies every active selector field."""

    expected = process_resource_limit_subject_projection(selector)
    observed = process_resource_limit_subject_projection(candidate)
    return all(
        observed[field_name] == value
        for field_name, value in expected.items()
        if _selector_field_is_active(field_name, value)
    )


def process_resource_limit_identity_payload(
    value: RuntimeProcessResourceLimit | Mapping[str, object],
) -> dict[str, object]:
    """Return the stable semantic identity, excluding soft/hard values."""

    model = (
        value if isinstance(value, RuntimeProcessResourceLimit) else RuntimeProcessResourceLimit.model_validate(value)
    )
    return {
        "resource": _enum_value(model.resource),
        "subject": process_resource_limit_subject_projection(model.subject),
        "scope": _enum_value(model.scope),
    }


def process_resource_limit_identity_digest(
    value: RuntimeProcessResourceLimit | Mapping[str, object],
) -> str:
    """Return a value-free key stable across collection ordering and substitutions."""

    return canonical_json_digest(process_resource_limit_identity_payload(value))


def project_process_resource_limit(
    value: RuntimeProcessResourceLimit | Mapping[str, object],
) -> dict[str, object]:
    """Project one authored/observed limit into the canonical portable record."""

    model = (
        value if isinstance(value, RuntimeProcessResourceLimit) else RuntimeProcessResourceLimit.model_validate(value)
    )
    return {
        **process_resource_limit_identity_payload(model),
        "soft": model.soft,
        "hard": model.hard,
    }


def process_resource_limit_capability_admits(
    capability: ProcessResourceLimitCapability,
    value: RuntimeProcessResourceLimit | Mapping[str, object],
    *,
    soft_values: tuple[object, ...] | None = None,
    hard_values: tuple[object, ...] | None = None,
) -> bool:
    """Check a concrete or finite-domain demand against one apparatus claim."""

    model = (
        value if isinstance(value, RuntimeProcessResourceLimit) else RuntimeProcessResourceLimit.model_validate(value)
    )
    soft_domain = soft_values if soft_values is not None else (model.soft,)
    hard_domain = hard_values if hard_values is not None else (model.hard,)
    return process_resource_limit_domain_admits(
        capability,
        resource=model.resource,
        scope=model.scope.value,
        soft_values=soft_domain,
        hard_values=hard_domain,
    )


def process_resource_limit_domain_admits(
    capability: ProcessResourceLimitCapability,
    *,
    resource: object,
    scope: object,
    soft_values: tuple[object, ...],
    hard_values: tuple[object, ...],
) -> bool:
    """Check one semantic limit identity and its leaf domains."""

    resource_value = getattr(resource, "value", resource)
    scope_value = getattr(scope, "value", scope)
    if capability.resource.value != resource_value:
        return False
    if scope_value not in {candidate.value for candidate in capability.scopes}:
        return False
    return all(capability.admits(candidate) for candidate in (*soft_values, *hard_values))


def reject_duplicate_process_resource_limits(values: list[RuntimeProcessResourceLimit]) -> None:
    seen: set[str] = set()
    for value in values:
        identity = process_resource_limit_identity_digest(value)
        if identity in seen:
            raise ValueError("Duplicate runtime process resource limit for the same resource, subject, and scope")
        seen.add(identity)
