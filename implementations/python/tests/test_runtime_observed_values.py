"""Cross-surface runtime observed-value and credential-posture invariants."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError
from raes.image_provenance import ImageBuildArg, ImageEnvironmentDefault
from raes.runtime_app_authorization import RuntimeAppAuthorizationPrincipal
from raes.runtime_application import RuntimeApplicationExposedField
from raes.runtime_configuration import RuntimeEnvironmentValueClassification, RuntimeEnvironmentVariable
from raes.runtime_database import DatabaseSetting
from raes.runtime_datastore import RuntimeDatastoreSetting
from raes.runtime_directory_identity import RuntimeIdentityAttribute
from raes.runtime_dns import DnsRuntimeSetting
from raes.runtime_forwarding_agent import RuntimeForwardingSetting, RuntimeForwardingShipTarget
from raes.runtime_mail_service import RuntimeMailSetting
from raes.runtime_platform_application import RuntimePlatformApplicationConnector, RuntimePlatformApplicationSetting
from raes.runtime_security_monitoring import RuntimeSecurityMonitoringSetting

SecretValueFactory = Callable[[], object]
SecretValueReader = Callable[[object], Any]


@pytest.mark.parametrize(
    ("_surface", "factory", "read_value", "expected"),
    [
        (
            "database setting",
            lambda: DatabaseSetting(name="admin_password", value="hunter2"),
            lambda obj: obj.value,
            "hunter2",
        ),
        (
            "DNS setting",
            lambda: DnsRuntimeSetting(name="tsig_secret", value="base64-secret"),
            lambda obj: obj.value,
            "base64-secret",
        ),
        (
            "mail setting",
            lambda: RuntimeMailSetting(setting_id="relay-pw", name="relay_password", value="hunter2"),
            lambda obj: obj.value,
            "hunter2",
        ),
        (
            "security-monitoring setting",
            lambda: RuntimeSecurityMonitoringSetting(setting_id="api", name="api_token", value="hunter2"),
            lambda obj: obj.value,
            "hunter2",
        ),
        (
            "identity attribute",
            lambda: RuntimeIdentityAttribute(name="unicodePwd", values=["hunter2"]),
            lambda obj: obj.values,
            ["hunter2"],
        ),
        (
            "datastore setting",
            lambda: RuntimeDatastoreSetting(setting_id="admin-pw", name="admin_password", value="hunter2"),
            lambda obj: obj.value,
            "hunter2",
        ),
        (
            "platform setting",
            lambda: RuntimePlatformApplicationSetting(setting_id="api", name="api_key", value="hunter2"),
            lambda obj: obj.value,
            "hunter2",
        ),
        (
            "forwarding setting",
            lambda: RuntimeForwardingSetting(setting_id="enroll", name="enrollment_key", value="hunter2"),
            lambda obj: obj.value,
            "hunter2",
        ),
        (
            "application exposed field",
            lambda: RuntimeApplicationExposedField(name="operator_api_key", sensitivity="plain", value="hunter2"),
            lambda obj: obj.value,
            "hunter2",
        ),
        (
            "runtime environment variable",
            lambda: RuntimeEnvironmentVariable(
                name="TECHVAULT_ADMIN_PASSWORD",
                value="hunter2",
                value_classification="plain",
            ),
            lambda obj: obj.value,
            "hunter2",
        ),
        (
            "image build argument",
            lambda: ImageBuildArg(name="PIP_INDEX_TOKEN", value="hunter2", value_classification="plain"),
            lambda obj: obj.value,
            "hunter2",
        ),
        (
            "image default environment",
            lambda: ImageEnvironmentDefault(name="API_TOKEN", value="hunter2", value_classification="plain"),
            lambda obj: obj.value,
            "hunter2",
        ),
    ],
)
def test_secret_named_observed_values_remain_representable_as_scenario_content(
    _surface: str,
    factory: SecretValueFactory,
    read_value: SecretValueReader,
    expected: object,
) -> None:
    """Secret-looking names do not by themselves redact SDL scenario content."""

    assert read_value(factory()) == expected


def test_runtime_environment_operator_secret_omits_raw_value() -> None:
    env = RuntimeEnvironmentVariable(name="OPERATOR_API_KEY", value_classification="operator_secret")

    assert env.value == ""
    assert env.value_classification is RuntimeEnvironmentValueClassification.OPERATOR_SECRET

    with pytest.raises(ValidationError, match="must omit"):
        RuntimeEnvironmentVariable(
            name="OPERATOR_API_KEY",
            value="hunter2",
            value_classification="operator_secret",
        )


def test_secret_named_environment_values_do_not_require_redaction_or_fixture_class() -> None:
    env = RuntimeEnvironmentVariable(
        name="OPERATOR_API_KEY",
        value="scenario-api-key",
        value_classification="plain",
    )

    assert env.value == "scenario-api-key"


def test_explicit_secret_fixture_values_are_allowed() -> None:
    env = RuntimeEnvironmentVariable(
        name="SCENARIO_FIXTURE_TOKEN",
        value="fixture-token",
        value_classification="secret_fixture",
    )
    exposed = RuntimeApplicationExposedField(
        name="build_token",
        sensitivity="secret_fixture",
        value="fixture-token",
    )
    build_arg = ImageBuildArg(
        name="BUILD_TOKEN",
        value="fixture-token",
        value_classification="secret_fixture",
    )
    image_env = ImageEnvironmentDefault(
        name="IMAGE_TOKEN",
        value="fixture-token",
        value_classification="secret_fixture",
    )

    assert env.value == "fixture-token"
    assert exposed.value == "fixture-token"
    assert build_arg.value == "fixture-token"
    assert image_env.value == "fixture-token"


def test_non_secret_key_metadata_values_are_representable() -> None:
    gpg = RuntimeEnvironmentVariable(name="GPG_KEY", value="0xDEADBEEF", value_classification="plain")
    length = RuntimeApplicationExposedField(name="secret_key_length", sensitivity="plain", value="25")
    key_path = RuntimeEnvironmentVariable(
        name="LABADMIN_SSH_KEY_FILE",
        value="/keys/labadmin-ssh-key.pub",
        value_classification="plain",
    )
    working_directory = RuntimeEnvironmentVariable(name="PWD", value="/srv/app", value_classification="plain")
    image_gpg = ImageEnvironmentDefault(name="GPG_KEY", value="0xDEADBEEF", value_classification="plain")

    assert gpg.value == "0xDEADBEEF"
    assert length.value == "25"
    assert key_path.value == "/keys/labadmin-ssh-key.pub"
    assert working_directory.value == "/srv/app"
    assert image_gpg.value == "0xDEADBEEF"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SECRET_KEY", "techvault-secret-key-2024"),
        ("JWT_SECRET", "techvault-jwt-weak"),
        ("DB_PASSWORD", "techvault_db_pass"),
    ],
)
def test_route_visible_secret_fixture_values_are_preserved(name: str, value: str) -> None:
    field = RuntimeApplicationExposedField(name=name, sensitivity="secret_fixture", value=value)

    assert field.value == value


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SERVICE_KEY", "service-key"),
        ("backup_key", "backup-key"),
        ("CONFIG-KEY", "config-key"),
        ("PUBLIC_API_KEY", "api-key"),
        ("SSH_KEY", "ssh-key"),
        ("enrollment_key", "enrollment-key"),
        ("rndc.key", "rndc-key"),
        ("update_key", "update-key"),
    ],
)
def test_credential_shaped_environment_names_remain_realizable(name: str, value: str) -> None:
    env = RuntimeEnvironmentVariable(name=name, value=value, value_classification="plain")

    assert env.value == value


def test_credential_posture_surfaces_do_not_gain_raw_secret_fields() -> None:
    """Posture-only credentials stay separate from observed key/value settings."""

    posture_models = (
        RuntimeAppAuthorizationPrincipal,
        RuntimeForwardingShipTarget,
        RuntimePlatformApplicationConnector,
    )
    forbidden = {"value", "raw_value", "credential_value", "password", "secret", "api_key", "hash"}

    for model in posture_models:
        assert not (set(model.model_fields) & forbidden), model.__name__
