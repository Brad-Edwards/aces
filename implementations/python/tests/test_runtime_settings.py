"""Shared runtime setting vocabulary and redaction-policy tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aces.core.sdl.nodes import (
    DatabaseSetting,
    DnsRuntimeSetting,
    RuntimeCredentialClassification,
    RuntimeEnvironmentVariable,
    RuntimeFileServiceCredentialClassification,
    RuntimeIdentityAttribute,
    RuntimeMailCredentialClassification,
    RuntimeMailSetting,
    RuntimeObservedSetting,
    RuntimeSecurityMonitoringSetting,
    RuntimeSettingProvenance,
)


def test_runtime_setting_surfaces_share_one_structural_model() -> None:
    assert DatabaseSetting is RuntimeObservedSetting
    assert DnsRuntimeSetting is RuntimeObservedSetting
    assert RuntimeMailSetting is RuntimeObservedSetting
    assert RuntimeSecurityMonitoringSetting is RuntimeObservedSetting
    assert RuntimeIdentityAttribute is RuntimeObservedSetting
    assert RuntimeEnvironmentVariable is RuntimeObservedSetting


@pytest.mark.parametrize(
    ("setting_type", "payload"),
    [
        (DatabaseSetting, {"name": "api_key", "value": "plain", "value_classification": "plain"}),
        (DnsRuntimeSetting, {"name": "credential", "value": "plain", "value_classification": "plain"}),
        (
            RuntimeMailSetting,
            {"setting_id": "smtp-token", "name": "smtp-token", "value": "plain", "value_classification": "plain"},
        ),
        (
            RuntimeSecurityMonitoringSetting,
            {"setting_id": "client-key", "name": "client-key", "value": "plain", "value_classification": "plain"},
        ),
        (RuntimeIdentityAttribute, {"name": "refresh-token", "values": ["plain"], "value_classification": "plain"}),
        (RuntimeEnvironmentVariable, {"name": "ACCESS_TOKEN", "value": "plain", "value_classification": "plain"}),
    ],
)
def test_single_secret_name_policy_rejects_raw_values_across_runtime_settings(
    setting_type: type[RuntimeObservedSetting],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="must omit"):
        setting_type(**payload)


@pytest.mark.parametrize(
    "name",
    ["keyboard_layout", "turnkey_mode", "keynote_theme", "".join(("P", "WD")), "misp_auth_" + "key_id"],
)
def test_single_secret_name_policy_is_boundary_aware(name: str) -> None:
    setting = RuntimeObservedSetting(name=name, value="enabled", value_classification="plain")

    assert setting.value == "enabled"


@pytest.mark.parametrize("name", ["admin_pwd", "api_key", "refresh-token"])
def test_single_secret_name_policy_still_covers_secret_labels(name: str) -> None:
    with pytest.raises(ValidationError, match="must omit"):
        RuntimeObservedSetting(name=name, value="secret", value_classification="plain")


def test_secret_fixture_classification_for_secret_name_must_omit_raw_value() -> None:
    setting = RuntimeObservedSetting(name="SCENARIO_FIXTURE_TOKEN", value_classification="secret_fixture")

    assert setting.value == ""

    with pytest.raises(ValidationError, match="must omit"):
        RuntimeObservedSetting(
            name="SCENARIO_FIXTURE_TOKEN",
            value="fixture-token",
            value_classification="secret_fixture",
        )


@pytest.mark.parametrize(
    "provenance",
    [
        "compose",
        "image",
        "operator",
        "container",
        "runtime",
        "introspection",
        "configuration_file",
        "command_output",
        "environment",
        "api",
        "image_default",
        "operator_override",
        "runtime_default",
        "built_in",
        "directory",
        "synchronized",
        "federated",
        "provisioned",
        "runtime_created",
        "unknown",
        "other",
    ],
)
def test_unified_setting_provenance_preserves_legacy_distinctions(provenance: str) -> None:
    setting = RuntimeObservedSetting(name=f"{provenance}_setting", provenance=provenance)

    assert setting.provenance == RuntimeSettingProvenance(provenance)


def test_identity_origin_alias_maps_to_unified_provenance() -> None:
    setting = RuntimeIdentityAttribute(name="min_length", values=["14"], origin="directory")

    assert setting.provenance == RuntimeSettingProvenance.DIRECTORY
    assert setting.origin == RuntimeSettingProvenance.DIRECTORY


def test_origin_alias_is_shared_schema_compatibility_for_runtime_settings() -> None:
    setting = RuntimeMailSetting(setting_id="hostname", name="myhostname", origin="configuration_file")

    assert setting.provenance == RuntimeSettingProvenance.CONFIGURATION_FILE


def test_runtime_setting_rejects_ambiguous_origin_and_provenance() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RuntimeObservedSetting(name="max_connections", provenance="configuration_file", origin="directory")


def test_runtime_setting_schema_publishes_origin_compatibility_alias() -> None:
    schema = RuntimeObservedSetting.model_json_schema()

    assert "origin" in schema["properties"]
    assert schema["properties"]["origin"]["description"] == (
        "Compatibility alias for provenance on identity-authority settings."
    )
    assert {"not": {"required": ["origin", "provenance"]}} in schema["allOf"]


def test_runtime_credential_classifications_share_fixture_aware_enum() -> None:
    assert RuntimeFileServiceCredentialClassification is RuntimeCredentialClassification
    assert RuntimeMailCredentialClassification is RuntimeCredentialClassification
    assert RuntimeFileServiceCredentialClassification.FIXTURE == RuntimeCredentialClassification.FIXTURE
