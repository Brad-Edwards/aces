"""Cross-surface runtime observed-value and credential-posture invariants."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from aces_sdl.image_provenance import ImageBuildArg, ImageEnvironmentDefault
from aces_sdl.runtime_app_authorization import RuntimeAppAuthorizationPrincipal
from aces_sdl.runtime_application import RuntimeApplicationExposedField
from aces_sdl.runtime_configuration import RuntimeEnvironmentValueClassification, RuntimeEnvironmentVariable
from aces_sdl.runtime_database import DatabaseSetting
from aces_sdl.runtime_datastore import RuntimeDatastoreSetting
from aces_sdl.runtime_directory_identity import RuntimeIdentityAttribute
from aces_sdl.runtime_dns import DnsRuntimeSetting
from aces_sdl.runtime_forwarding_agent import RuntimeForwardingSetting, RuntimeForwardingShipTarget
from aces_sdl.runtime_mail_service import RuntimeMailSetting
from aces_sdl.runtime_platform_application import RuntimePlatformApplicationConnector, RuntimePlatformApplicationSetting
from aces_sdl.runtime_security_monitoring import RuntimeSecurityMonitoringSetting
from pydantic import ValidationError

SecretValueFactory = Callable[[], object]


@pytest.mark.parametrize(
    ("_surface", "factory"),
    [
        ("database setting", lambda: DatabaseSetting(name="admin_password", value="hunter2")),
        ("DNS setting", lambda: DnsRuntimeSetting(name="tsig_secret", value="base64-secret")),
        (
            "mail setting",
            lambda: RuntimeMailSetting(setting_id="relay-pw", name="relay_password", value="hunter2"),
        ),
        (
            "security-monitoring setting",
            lambda: RuntimeSecurityMonitoringSetting(setting_id="api", name="api_token", value="hunter2"),
        ),
        ("identity attribute", lambda: RuntimeIdentityAttribute(name="unicodePwd", values=["hunter2"])),
        (
            "datastore setting",
            lambda: RuntimeDatastoreSetting(setting_id="admin-pw", name="admin_password", value="hunter2"),
        ),
        (
            "platform setting",
            lambda: RuntimePlatformApplicationSetting(setting_id="api", name="api_key", value="hunter2"),
        ),
        (
            "forwarding setting",
            lambda: RuntimeForwardingSetting(setting_id="enroll", name="enrollment_key", value="hunter2"),
        ),
        (
            "application exposed field",
            lambda: RuntimeApplicationExposedField(name="operator_api_key", sensitivity="plain", value="hunter2"),
        ),
        (
            "runtime environment variable",
            lambda: RuntimeEnvironmentVariable(
                name="TECHVAULT_ADMIN_PASSWORD",
                value="hunter2",
                value_classification="plain",
            ),
        ),
        (
            "image build argument",
            lambda: ImageBuildArg(name="PIP_INDEX_TOKEN", value="hunter2", value_classification="plain"),
        ),
        (
            "image default environment",
            lambda: ImageEnvironmentDefault(name="API_TOKEN", value="hunter2", value_classification="plain"),
        ),
    ],
)
def test_secret_bearing_observed_values_reject_unclassified_raw_values(
    _surface: str,
    factory: SecretValueFactory,
) -> None:
    """Secret-looking names must not carry raw values as plain/unknown data."""

    with pytest.raises(ValidationError, match="secret-bearing name"):
        factory()


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


def test_secret_bearing_environment_name_requires_redaction_or_fixture_class() -> None:
    with pytest.raises(ValidationError, match="value_classification must be"):
        RuntimeEnvironmentVariable(name="OPERATOR_API_KEY", value_classification="plain")


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
