"""Shared runtime setting, provenance, credential, and redaction models."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import AliasChoices, Field, GetJsonSchemaHandler, field_validator, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from ._base import SDLModel, is_variable_ref
from .runtime_values import absolute_path_or_var, coerce_string_list, parse_runtime_enum_or_var, require_symbol


class RuntimeSensitivityClassification(str, Enum):
    """Sensitivity/redaction class for observed runtime facts."""

    PLAIN = "plain"
    REDACTED = "redacted"
    SECRET_FIXTURE = "_".join(("secret", "fixture"))
    OPERATOR_SECRET = "_".join(("operator", "secret"))
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeSettingProvenance(str, Enum):
    """Unified provenance taxonomy for observed runtime settings."""

    COMPOSE = "compose"
    IMAGE = "image"
    OPERATOR = "operator"
    CONTAINER = "container"
    RUNTIME = "runtime"
    INTROSPECTION = "introspection"
    CONFIGURATION_FILE = "configuration_file"
    COMMAND_OUTPUT = "command_output"
    ENVIRONMENT = "environment"
    API = "api"
    IMAGE_DEFAULT = "image_default"
    OPERATOR_OVERRIDE = "operator_override"
    RUNTIME_DEFAULT = "runtime_default"
    BUILT_IN = "built_in"
    DIRECTORY = "directory"
    SYNCHRONIZED = "synchronized"
    FEDERATED = "federated"
    PROVISIONED = "provisioned"
    RUNTIME_CREATED = "runtime_created"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeCredentialClassification(str, Enum):
    """Semantic classification of a runtime credential, never its raw value."""

    NO_CREDENTIAL = "no_credential"
    WEAK = "weak"
    DEFAULT_OR_TRIVIAL = "default_or_trivial"
    FIXTURE = "fixture"
    STRONG = "strong"
    REDACTED = "redacted"
    UNKNOWN = "unknown"
    OTHER = "other"


_RAW_OMIT_SENSITIVITIES = frozenset(
    {RuntimeSensitivityClassification.REDACTED, RuntimeSensitivityClassification.OPERATOR_SECRET}
)
_SECRET_NAME_ALLOWED_CLASSIFICATIONS = frozenset(
    {
        RuntimeSensitivityClassification.REDACTED,
        RuntimeSensitivityClassification.OPERATOR_SECRET,
        RuntimeSensitivityClassification.SECRET_FIXTURE,
    }
)

_SECRET_NAME_SUBSTRINGS: tuple[str, ...] = (
    "password",
    "passwd",
    "passphrase",
    "secret",
    "credential",
    "credentials",
    "conninfo",
    "pg_hba",
    "private_key",
    "privatekey",
    "keytab",
    "krbprincipalkey",
    "supplementalcredentials",
    "unicodepwd",
    "dbcspwd",
    "ntpwdhash",
    "lmpwdhash",
    "userpassword",
    "cleartextpassword",
    "client_secret",
    "clientsecret",
    "access_token",
    "refresh_token",
    "api_key",
    "shared_key",
    "enrollment_key",
    "client_key",
    "access_key",
    "auth_key",
    "sasl_passwd",
    "sasl_password",
    "authd.pass",
)
_SECRET_NAME_PARTS = frozenset(
    {
        "password",
        "passwd",
        "passphrase",
        "secret",
        "credential",
        "credentials",
        "token",
        "tsig",
        "hmac",
        "keytab",
        "keyfile",
    }
)
_SECRET_KEY_QUALIFIERS = frozenset(
    {
        "access",
        "api",
        "auth",
        "client",
        "enrollment",
        "private",
        "rndc",
        "shared",
        "signing",
        "update",
    }
)


def name_indicates_secret(name: str) -> bool:
    """Return whether a concrete runtime setting name denotes secret-bearing data."""

    lowered = name.lower().replace("-", "_")
    parts_list = [part for part in re.split(r"[^a-z0-9]+", lowered) if part]
    parts = frozenset(parts_list)
    return not _is_key_identifier(parts_list) and (
        _has_secret_substring(lowered) or _has_secret_part(parts) or _has_secret_key(parts)
    )


def _is_key_identifier(parts: list[str]) -> bool:
    return len(parts) >= 2 and parts[-2:] == ["key", "id"]


def _has_secret_substring(name: str) -> bool:
    return any(token in name for token in _SECRET_NAME_SUBSTRINGS)


def _has_secret_part(parts: frozenset[str]) -> bool:
    return bool(parts & _SECRET_NAME_PARTS) or ("pwd" in parts and len(parts) > 1)


def _has_secret_key(parts: frozenset[str]) -> bool:
    if "key" not in parts:
        return False
    if "id" in parts:
        return False
    return len(parts) == 1 or bool(parts & _SECRET_KEY_QUALIFIERS)


def setting_name_is_concrete_secret(name: object) -> bool:
    """Return whether ``name`` is a concrete, non-variable secret-bearing label."""

    return isinstance(name, str) and not is_variable_ref(name) and name_indicates_secret(name)


class RuntimeObservedSetting(SDLModel):
    """Observed runtime setting with unified provenance, sensitivity, and redaction."""

    setting_id: str = ""
    component_ref: str = ""
    name: str
    value: str = ""
    values: list[str] = Field(default_factory=list)
    value_classification: RuntimeSensitivityClassification | str = RuntimeSensitivityClassification.UNKNOWN
    provenance: RuntimeSettingProvenance | str = Field(
        default=RuntimeSettingProvenance.UNKNOWN,
        validation_alias=AliasChoices("provenance", "origin"),
    )
    source: str = ""
    source_path: str = ""
    description: str = ""

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        provenance_schema = json_schema.get("properties", {}).get("provenance")
        if provenance_schema:
            origin_schema = dict(provenance_schema)
            origin_schema["title"] = "Origin"
            origin_schema["description"] = "Compatibility alias for provenance on identity-authority settings."
            json_schema.setdefault("properties", {}).setdefault("origin", origin_schema)
        return json_schema

    @property
    def origin(self) -> RuntimeSettingProvenance | str:
        """Backward-compatible identity-setting alias for ``provenance``."""

        return self.provenance

    @field_validator("setting_id")
    @classmethod
    def validate_setting_id(cls, value: str) -> str:
        return require_symbol(value, field_name="setting_id") if value else value

    @field_validator("component_ref")
    @classmethod
    def validate_component_ref(cls, value: str) -> str:
        return require_symbol(value, field_name="component_ref") if value else value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("runtime setting name must be a non-empty string")
        if "=" in value:
            raise ValueError("environment variable name/runtime setting name must not contain '='")
        return value

    @field_validator("values", mode="before")
    @classmethod
    def coerce_values(cls, value: Any) -> list[str]:
        return coerce_string_list(value)

    @field_validator("values")
    @classmethod
    def validate_values(cls, values: list[str]) -> list[str]:
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("runtime setting values must be non-empty strings")
        if len(values) != len(set(values)):
            raise ValueError("Duplicate runtime setting value")
        return values

    @field_validator("value_classification", mode="before")
    @classmethod
    def normalize_value_classification(
        cls,
        value: RuntimeSensitivityClassification | str,
    ) -> RuntimeSensitivityClassification | str:
        return parse_runtime_enum_or_var(value, RuntimeSensitivityClassification, field_name="value_classification")

    @field_validator("provenance", mode="before")
    @classmethod
    def normalize_provenance(cls, value: RuntimeSettingProvenance | str) -> RuntimeSettingProvenance | str:
        return parse_runtime_enum_or_var(value, RuntimeSettingProvenance, field_name="provenance")

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str) -> str:
        return absolute_path_or_var(value, field_name="source_path") if value else value

    @model_validator(mode="after")
    def validate_value_shape_and_redaction(self) -> RuntimeObservedSetting:
        if self.value and self.values:
            raise ValueError("runtime setting must use either value or values, not both")
        if setting_name_is_concrete_secret(self.name):
            self._enforce_secret_name_redaction()
        elif self._has_raw_value() and self.value_classification in _RAW_OMIT_SENSITIVITIES:
            raise ValueError(
                f"runtime setting '{self.name}' classified '{self.value_classification}' must omit its raw value"
            )
        return self

    def _has_raw_value(self) -> bool:
        return bool(self.value or self.values)

    def _enforce_secret_name_redaction(self) -> None:
        if self._has_raw_value():
            raise ValueError(f"runtime setting '{self.name}' carries a secret-bearing name and must omit its raw value")
        if is_variable_ref(self.value_classification):
            return
        if self.value_classification not in _SECRET_NAME_ALLOWED_CLASSIFICATIONS:
            raise ValueError(
                f"runtime setting '{self.name}' carries a secret-bearing name; "
                f"value_classification must be 'redacted' or 'operator_secret' "
                f"(or 'secret_fixture' for approved fixtures)"
            )


__all__ = [
    "RuntimeCredentialClassification",
    "RuntimeObservedSetting",
    "RuntimeSensitivityClassification",
    "RuntimeSettingProvenance",
    "name_indicates_secret",
    "setting_name_is_concrete_secret",
]
