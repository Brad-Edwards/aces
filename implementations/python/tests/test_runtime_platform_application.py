"""Runtime platform-application (RuntimePlatformApplication) SDL surface tests."""

from __future__ import annotations

import pytest
from aces_sdl.runtime_platform_application import (
    RelationshipServiceIntegration,
    RelationshipServiceIntegrationDirection,
    RelationshipServiceIntegrationKind,
    RuntimePlatformApplication,
    RuntimePlatformApplicationConnector,
    RuntimePlatformApplicationConnectorKind,
    RuntimePlatformApplicationContentObject,
    RuntimePlatformApplicationContentObjectKind,
    RuntimePlatformApplicationExecutionPolicy,
    RuntimePlatformApplicationKind,
    RuntimePlatformApplicationMarking,
    RuntimePlatformApplicationMarkingScheme,
    RuntimePlatformApplicationOrganization,
    RuntimePlatformApplicationSetting,
    RuntimePlatformApplicationSettingClassification,
    RuntimePlatformApplicationSettingProvenance,
    RuntimePlatformApplicationTenant,
    RuntimePlatformApplicationUpstreamBinding,
    RuntimePlatformApplicationUpstreamBindingRole,
)
from pydantic import ValidationError

# --------------------------------------------------------------------------- #
# Per-platform_kind valid fixtures (each carries its required profile)
# --------------------------------------------------------------------------- #


def _threat_intel(**overrides) -> dict:
    application = {
        "platform_application_id": "misp",
        "service": "misp-web",
        "platform_kind": "threat_intel",
        "product": "MISP",
        "version": "2.4",
        "organizations": [{"organization_id": "org-aptl", "name": "APTL"}],
        "content_objects": [
            {"content_object_id": "tax-tlp", "kind": "taxonomy", "name": "tlp", "attributes": {"namespace": "tlp"}},
            {
                "content_object_id": "gc-mitre",
                "kind": "galaxy_cluster",
                "name": "mitre-attack",
                "references": ["tax-tlp"],
            },
            {"content_object_id": "wl-cidr", "kind": "warninglist", "attributes": {"match_type": "cidr"}},
            {
                "content_object_id": "feed-ct",
                "kind": "feed",
                "attributes": {"provider": "circl", "source_format": "misp"},
            },
            {"content_object_id": "sg-trusted", "kind": "sharing_group", "name": "trusted"},
        ],
        "markings": [{"marking_id": "tlp-red", "scheme": "tlp", "level": "red"}],
        "authorization_ref": "misp-rbac",
    }
    application.update(overrides)
    return application


def _soar(**overrides) -> dict:
    application = {
        "platform_application_id": "shuffle",
        "platform_kind": "soar",
        "product": "Shuffle",
        "content_objects": [
            {"content_object_id": "wf-enrich", "kind": "workflow", "name": "enrich-ioc"},
            {"content_object_id": "app-virustotal", "kind": "app", "name": "virustotal"},
        ],
    }
    application.update(overrides)
    return application


def _analyzer_engine(**overrides) -> dict:
    application = {
        "platform_application_id": "cortex",
        "platform_kind": "analyzer_engine",
        "product": "Cortex",
        "content_objects": [
            {"content_object_id": "an-virustotal", "kind": "analyzer", "name": "VirusTotal_GetReport"},
            {"content_object_id": "re-block", "kind": "responder", "name": "Block_IP"},
        ],
        "execution_policy": {"policy_id": "default", "runner": "docker", "max_concurrent_jobs": 5},
    }
    application.update(overrides)
    return application


def _case_management(**overrides) -> dict:
    application = {
        "platform_application_id": "thehive",
        "platform_kind": "case_management",
        "product": "TheHive",
        "content_objects": [
            {"content_object_id": "ct-incident", "kind": "case_template", "name": "incident"},
            {"content_object_id": "cf-severity", "kind": "custom_field", "name": "business-severity"},
        ],
    }
    application.update(overrides)
    return application


def _analytics_dashboard(**overrides) -> dict:
    application = {
        "platform_application_id": "wazuh-dashboard",
        "platform_kind": "analytics_dashboard",
        "product": "wazuh-dashboard",
        "tenants": [{"tenant_id": "global", "name": "global_tenant"}],
        "content_objects": [
            {"content_object_id": "ip-alerts", "kind": "index_pattern", "name": "wazuh-alerts-*"},
            {
                "content_object_id": "viz-top-agents",
                "kind": "visualization",
                "name": "top-agents",
                "references": ["ip-alerts"],
            },
        ],
        "upstream_bindings": [
            {
                "binding_id": "indexer-backend",
                "role": "index_backend",
                "target_node_ref": "wazuh-indexer",
                "target_service_ref": "indexer-https",
            }
        ],
    }
    application.update(overrides)
    return application


_ALL_FIXTURES = {
    "threat_intel": _threat_intel,
    "soar": _soar,
    "analyzer_engine": _analyzer_engine,
    "case_management": _case_management,
    "analytics_dashboard": _analytics_dashboard,
}


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #


def test_full_threat_intel_inventory_is_valid() -> None:
    application = RuntimePlatformApplication(**_threat_intel())
    assert application.platform_application_id == "misp"
    assert application.platform_kind == RuntimePlatformApplicationKind.THREAT_INTEL
    assert application.content_objects[0].kind == RuntimePlatformApplicationContentObjectKind.TAXONOMY
    assert application.content_objects[1].references == ["tax-tlp"]
    assert application.markings[0].scheme == RuntimePlatformApplicationMarkingScheme.TLP
    assert application.authorization_ref == "misp-rbac"


@pytest.mark.parametrize("kind", list(_ALL_FIXTURES))
def test_every_platform_kind_fixture_is_valid(kind: str) -> None:
    application = RuntimePlatformApplication(**_ALL_FIXTURES[kind]())
    assert application.platform_kind == RuntimePlatformApplicationKind(kind)


def test_analytics_dashboard_binding_and_references() -> None:
    application = RuntimePlatformApplication(**_analytics_dashboard())
    binding = application.upstream_bindings[0]
    assert binding.role == RuntimePlatformApplicationUpstreamBindingRole.INDEX_BACKEND
    assert application.tenants[0].tenant_id == "global"


# --------------------------------------------------------------------------- #
# Stable-id rejection (empty / variable placeholder)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad_id", ["", "   ", "${app}"])
def test_platform_application_id_rejects_empty_or_variable(bad_id: str) -> None:
    with pytest.raises(ValidationError, match="platform_application_id"):
        RuntimePlatformApplication(**_soar(platform_application_id=bad_id))


@pytest.mark.parametrize("bad_id", ["", "${org}"])
def test_organization_id_rejects_empty_or_variable(bad_id: str) -> None:
    with pytest.raises(ValidationError, match="organization_id"):
        RuntimePlatformApplicationOrganization(organization_id=bad_id)


@pytest.mark.parametrize("bad_id", ["", "${tenant}"])
def test_tenant_id_rejects_empty_or_variable(bad_id: str) -> None:
    with pytest.raises(ValidationError, match="tenant_id"):
        RuntimePlatformApplicationTenant(tenant_id=bad_id)


@pytest.mark.parametrize("bad_id", ["", "${obj}"])
def test_content_object_id_rejects_empty_or_variable(bad_id: str) -> None:
    with pytest.raises(ValidationError, match="content_object_id"):
        RuntimePlatformApplicationContentObject(content_object_id=bad_id)


@pytest.mark.parametrize("bad_id", ["", "${marking}"])
def test_marking_id_rejects_empty_or_variable(bad_id: str) -> None:
    with pytest.raises(ValidationError, match="marking_id"):
        RuntimePlatformApplicationMarking(marking_id=bad_id)


@pytest.mark.parametrize("bad_id", ["", "${binding}"])
def test_binding_id_rejects_empty_or_variable(bad_id: str) -> None:
    with pytest.raises(ValidationError, match="binding_id"):
        RuntimePlatformApplicationUpstreamBinding(binding_id=bad_id)


@pytest.mark.parametrize("bad_id", ["", "${connector}"])
def test_connector_id_rejects_empty_or_variable(bad_id: str) -> None:
    with pytest.raises(ValidationError, match="connector_id"):
        RuntimePlatformApplicationConnector(connector_id=bad_id)


@pytest.mark.parametrize("bad_id", ["", "${setting}"])
def test_setting_id_rejects_empty_or_variable(bad_id: str) -> None:
    with pytest.raises(ValidationError, match="setting_id"):
        RuntimePlatformApplicationSetting(setting_id=bad_id)


# --------------------------------------------------------------------------- #
# Enum normalization + sentinels
# --------------------------------------------------------------------------- #


def test_enum_normalization_is_case_and_separator_insensitive() -> None:
    application = RuntimePlatformApplication(**_soar(platform_kind="SOAR"))
    assert application.platform_kind == RuntimePlatformApplicationKind.SOAR

    obj = RuntimePlatformApplicationContentObject(content_object_id="o", kind="GALAXY-CLUSTER")
    assert obj.kind == RuntimePlatformApplicationContentObjectKind.GALAXY_CLUSTER

    binding = RuntimePlatformApplicationUpstreamBinding(binding_id="b", role="INDEX-BACKEND")
    assert binding.role == RuntimePlatformApplicationUpstreamBindingRole.INDEX_BACKEND

    connector = RuntimePlatformApplicationConnector(connector_id="c", kind="ANALYZER-ENGINE")
    assert connector.kind == RuntimePlatformApplicationConnectorKind.ANALYZER_ENGINE

    setting = RuntimePlatformApplicationSetting(setting_id="s", provenance="CONFIG-FILE")
    assert setting.provenance == RuntimePlatformApplicationSettingProvenance.CONFIG_FILE


def test_variable_placeholder_enums_pass_through() -> None:
    obj = RuntimePlatformApplicationContentObject(content_object_id="o", kind="${kind}")
    assert obj.kind == "${kind}"


def test_unknown_enum_member_is_rejected() -> None:
    with pytest.raises(ValidationError, match="platform_kind must be one of"):
        RuntimePlatformApplication(platform_application_id="p", platform_kind="bogus")


def test_open_taxonomies_carry_unknown_and_other() -> None:
    for enum_cls in (
        RuntimePlatformApplicationKind,
        RuntimePlatformApplicationContentObjectKind,
        RuntimePlatformApplicationUpstreamBindingRole,
        RuntimePlatformApplicationConnectorKind,
        RuntimePlatformApplicationSettingProvenance,
    ):
        members = {m.value for m in enum_cls}
        assert {"unknown", "other"} <= members, enum_cls.__name__


def test_closed_vocabularies_carry_no_sentinels() -> None:
    scheme = {m.value for m in RuntimePlatformApplicationMarkingScheme}
    assert scheme == {"tlp", "pap", "distribution"}
    classification = {m.value for m in RuntimePlatformApplicationSettingClassification}
    assert classification == {"plain", "redacted", "operator_secret"}


# --------------------------------------------------------------------------- #
# Duplicate-id rejection + list coercion
# --------------------------------------------------------------------------- #


def test_rejects_duplicate_local_stable_ids_across_child_kinds() -> None:
    with pytest.raises(ValidationError, match="Duplicate runtime platform application stable id 'shared-id'"):
        RuntimePlatformApplication(
            platform_application_id="p",
            organizations=[{"organization_id": "shared-id"}],
            tenants=[{"tenant_id": "shared-id"}],
        )


def test_rejects_duplicate_content_object_references() -> None:
    with pytest.raises(ValidationError, match="Duplicate runtime platform application references entry on 'o'"):
        RuntimePlatformApplicationContentObject(content_object_id="o", references=["a", "a"])


def test_scalar_ref_lists_coerce_to_single_element_lists() -> None:
    obj = RuntimePlatformApplicationContentObject(
        content_object_id="o", references="ip-1", marking_refs="tlp-red", evidence_refs="/evidence.json"
    )
    assert obj.references == ["ip-1"]
    assert obj.marking_refs == ["tlp-red"]
    assert obj.evidence_refs == ["/evidence.json"]


def test_extra_fields_are_forbidden() -> None:
    with pytest.raises(ValidationError):
        RuntimePlatformApplicationOrganization(organization_id="o", bogus="x")


# --------------------------------------------------------------------------- #
# Content objects never carry raw bodies
# --------------------------------------------------------------------------- #


def test_content_object_has_no_raw_body_field() -> None:
    fields = set(RuntimePlatformApplicationContentObject.model_fields)
    assert not (fields & {"body", "raw", "raw_body", "content", "document", "payload"})
    assert {"attributes", "references", "marking_refs", "evidence_refs"} <= fields


# --------------------------------------------------------------------------- #
# Secret redaction (connectors + settings)
# --------------------------------------------------------------------------- #


def test_secret_named_connector_may_use_plain_scenario_classification() -> None:
    connector = RuntimePlatformApplicationConnector(
        connector_id="c",
        name="cortex-api-key",
        credential_classification="plain",
    )

    assert connector.credential_classification == RuntimePlatformApplicationSettingClassification.PLAIN


def test_secret_named_connector_with_redacted_classification_is_valid() -> None:
    connector = RuntimePlatformApplicationConnector(
        connector_id="c", name="cortex-api-key", credential_classification="operator_secret"
    )
    assert connector.credential_classification == RuntimePlatformApplicationSettingClassification.OPERATOR_SECRET


def test_secret_named_setting_may_carry_scenario_value() -> None:
    setting = RuntimePlatformApplicationSetting(setting_id="s", name="admin_password", value="hunter2")

    assert setting.value == "hunter2"


def test_secret_named_setting_redacted_is_valid() -> None:
    setting = RuntimePlatformApplicationSetting(setting_id="s", name="admin_password", classification="redacted")
    assert setting.classification == RuntimePlatformApplicationSettingClassification.REDACTED


def test_redacted_setting_must_not_carry_raw_value() -> None:
    with pytest.raises(ValidationError, match="must omit its raw value"):
        RuntimePlatformApplicationSetting(setting_id="s", name="log_level", value="debug", classification="redacted")


def test_plain_non_secret_setting_keeps_value() -> None:
    setting = RuntimePlatformApplicationSetting(setting_id="s", name="log_level", value="debug")
    assert setting.value == "debug"


# --------------------------------------------------------------------------- #
# require_profile_for_platform_kind guard — exemptions
# --------------------------------------------------------------------------- #


def test_unknown_platform_kind_is_permissive() -> None:
    application = RuntimePlatformApplication(platform_application_id="p", platform_kind="unknown")
    assert application.platform_kind == RuntimePlatformApplicationKind.UNKNOWN


def test_other_platform_kind_is_permissive() -> None:
    application = RuntimePlatformApplication(platform_application_id="p", platform_kind="other")
    assert application.platform_kind == RuntimePlatformApplicationKind.OTHER


def test_default_platform_kind_is_unknown_and_permissive() -> None:
    application = RuntimePlatformApplication(platform_application_id="p")
    assert application.platform_kind == RuntimePlatformApplicationKind.UNKNOWN


def test_variable_placeholder_platform_kind_is_exempt() -> None:
    application = RuntimePlatformApplication(platform_application_id="p", platform_kind="${kind}")
    assert application.platform_kind == "${kind}"


# --------------------------------------------------------------------------- #
# require_profile_for_platform_kind guard — threat_intel
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "missing_id",
    ["tax-tlp", "gc-mitre", "wl-cidr", "feed-ct", "sg-trusted"],
)
def test_threat_intel_requires_each_corpus_kind(missing_id: str) -> None:
    fixture = _threat_intel()
    fixture["content_objects"] = [o for o in fixture["content_objects"] if o["content_object_id"] != missing_id]
    with pytest.raises(ValidationError, match="platform_kind 'threat_intel' requires"):
        RuntimePlatformApplication(**fixture)


def test_threat_intel_with_no_content_is_rejected() -> None:
    with pytest.raises(ValidationError, match="platform_kind 'threat_intel' requires"):
        RuntimePlatformApplication(platform_application_id="misp", platform_kind="threat_intel")


# --------------------------------------------------------------------------- #
# require_profile_for_platform_kind guard — soar
# --------------------------------------------------------------------------- #


def test_soar_requires_workflow_content_object() -> None:
    with pytest.raises(ValidationError, match="platform_kind 'soar' requires .*'workflow'"):
        RuntimePlatformApplication(
            platform_application_id="shuffle",
            platform_kind="soar",
            content_objects=[{"content_object_id": "app-x", "kind": "app"}],
        )


def test_soar_with_workflow_is_valid() -> None:
    application = RuntimePlatformApplication(**_soar())
    assert application.platform_kind == RuntimePlatformApplicationKind.SOAR


# --------------------------------------------------------------------------- #
# require_profile_for_platform_kind guard — analyzer_engine
# --------------------------------------------------------------------------- #


def test_analyzer_engine_requires_analyzer_or_responder() -> None:
    with pytest.raises(ValidationError, match="requires >=1 analyzer or responder content_object"):
        RuntimePlatformApplication(
            platform_application_id="cortex",
            platform_kind="analyzer_engine",
            content_objects=[{"content_object_id": "app-x", "kind": "app"}],
            execution_policy={"policy_id": "default"},
        )


def test_analyzer_engine_requires_execution_policy() -> None:
    with pytest.raises(ValidationError, match="requires an execution_policy"):
        RuntimePlatformApplication(
            platform_application_id="cortex",
            platform_kind="analyzer_engine",
            content_objects=[{"content_object_id": "an-x", "kind": "analyzer"}],
        )


def test_analyzer_engine_with_responder_only_is_valid() -> None:
    application = RuntimePlatformApplication(
        platform_application_id="cortex",
        platform_kind="analyzer_engine",
        content_objects=[{"content_object_id": "re-x", "kind": "responder"}],
        execution_policy={"policy_id": "default"},
    )
    assert application.execution_policy is not None


# --------------------------------------------------------------------------- #
# require_profile_for_platform_kind guard — case_management
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("missing_kind", ["case_template", "custom_field"])
def test_case_management_requires_template_and_custom_field(missing_kind: str) -> None:
    fixture = _case_management()
    fixture["content_objects"] = [o for o in fixture["content_objects"] if o["kind"] != missing_kind]
    with pytest.raises(ValidationError, match="platform_kind 'case_management' requires"):
        RuntimePlatformApplication(**fixture)


# --------------------------------------------------------------------------- #
# require_profile_for_platform_kind guard — analytics_dashboard
# --------------------------------------------------------------------------- #


def test_analytics_dashboard_requires_saved_object() -> None:
    with pytest.raises(ValidationError, match="requires >=1 saved-object content_object"):
        RuntimePlatformApplication(
            platform_application_id="dash",
            platform_kind="analytics_dashboard",
            content_objects=[{"content_object_id": "wf-x", "kind": "workflow"}],
            upstream_bindings=[{"binding_id": "b", "role": "index_backend"}],
        )


def test_analytics_dashboard_saved_object_requires_references() -> None:
    fixture = _analytics_dashboard()
    fixture["content_objects"] = [{"content_object_id": "ip-alerts", "kind": "index_pattern"}]
    with pytest.raises(ValidationError, match="saved-object content_object that carries references"):
        RuntimePlatformApplication(**fixture)


def test_analytics_dashboard_requires_backing_upstream_binding() -> None:
    fixture = _analytics_dashboard()
    fixture["upstream_bindings"] = [{"binding_id": "b", "role": "sync_peer"}]
    with pytest.raises(ValidationError, match="requires >=1 upstream_binding with role"):
        RuntimePlatformApplication(**fixture)


def test_analytics_dashboard_with_data_source_binding_is_valid() -> None:
    fixture = _analytics_dashboard()
    fixture["upstream_bindings"] = [{"binding_id": "b", "role": "data_source", "target_node_ref": "n"}]
    application = RuntimePlatformApplication(**fixture)
    assert application.upstream_bindings[0].role == RuntimePlatformApplicationUpstreamBindingRole.DATA_SOURCE


def test_execution_policy_parses_nested_fields() -> None:
    policy = RuntimePlatformApplicationExecutionPolicy(policy_id="p", runner="docker", max_concurrent_jobs="8")
    assert policy.max_concurrent_jobs == 8


# --------------------------------------------------------------------------- #
# RelationshipServiceIntegration
# --------------------------------------------------------------------------- #


def test_service_integration_full_edge_is_valid() -> None:
    integration = RelationshipServiceIntegration(
        consumer_ref="thehive",
        engine_ref="cortex",
        integration_kind="analyzer",
        auth_principal_ref="cortex-api-user",
        enabled=True,
        direction="outbound",
        description="TheHive calls Cortex analyzers",
    )
    assert integration.consumer_ref == "thehive"
    assert integration.engine_ref == "cortex"
    assert integration.integration_kind == RelationshipServiceIntegrationKind.ANALYZER
    assert integration.auth_principal_ref == "cortex-api-user"
    assert integration.enabled is True
    assert integration.direction == RelationshipServiceIntegrationDirection.OUTBOUND


def test_service_integration_defaults() -> None:
    integration = RelationshipServiceIntegration()
    assert integration.integration_kind == RelationshipServiceIntegrationKind.UNKNOWN
    assert integration.direction == RelationshipServiceIntegrationDirection.BIDIRECTIONAL
    assert integration.enabled is None


def test_service_integration_open_kind_normalizes() -> None:
    integration = RelationshipServiceIntegration(integration_kind="WEBHOOK")
    assert integration.integration_kind == RelationshipServiceIntegrationKind.WEBHOOK
    integration = RelationshipServiceIntegration(integration_kind="ENRICHMENT")
    assert integration.integration_kind == RelationshipServiceIntegrationKind.ENRICHMENT


def test_service_integration_open_kind_carries_unknown_and_other() -> None:
    members = {m.value for m in RelationshipServiceIntegrationKind}
    assert {"unknown", "other"} <= members


def test_service_integration_open_kind_accepts_unknown_member() -> None:
    integration = RelationshipServiceIntegration(integration_kind="unknown")
    assert integration.integration_kind == RelationshipServiceIntegrationKind.UNKNOWN


def test_service_integration_closed_direction_normalizes() -> None:
    integration = RelationshipServiceIntegration(direction="INBOUND")
    assert integration.direction == RelationshipServiceIntegrationDirection.INBOUND
    integration = RelationshipServiceIntegration(direction="bidirectional")
    assert integration.direction == RelationshipServiceIntegrationDirection.BIDIRECTIONAL


def test_service_integration_closed_direction_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError, match="direction must be one of"):
        RelationshipServiceIntegration(direction="sideways")


def test_service_integration_closed_direction_carries_no_sentinels() -> None:
    members = {m.value for m in RelationshipServiceIntegrationDirection}
    assert members == {"inbound", "outbound", "bidirectional"}


def test_service_integration_variable_placeholder_enums_pass_through() -> None:
    integration = RelationshipServiceIntegration(integration_kind="${kind}", direction="${dir}")
    assert integration.integration_kind == "${kind}"
    assert integration.direction == "${dir}"


def test_service_integration_enabled_parses_string_bool() -> None:
    integration = RelationshipServiceIntegration(enabled="false")
    assert integration.enabled is False
    integration = RelationshipServiceIntegration(enabled="${flag}")
    assert integration.enabled == "${flag}"
