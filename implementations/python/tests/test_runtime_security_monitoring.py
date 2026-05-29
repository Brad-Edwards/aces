"""Runtime security-monitoring manager SDL surface tests."""

from __future__ import annotations

import pytest
from aces_sdl._module_symbols import symbol_index
from pydantic import ValidationError

from aces.core.sdl import parse_sdl
from aces.core.sdl._errors import SDLValidationError
from aces.core.sdl.nodes import (
    Node,
    RuntimeConfiguration,
    RuntimeSecurityMonitoringAgentStatus,
    RuntimeSecurityMonitoringComponentKind,
    RuntimeSecurityMonitoringComponentStatus,
    RuntimeSecurityMonitoringContentFormat,
    RuntimeSecurityMonitoringContentKind,
    RuntimeSecurityMonitoringImplementation,
    RuntimeSecurityMonitoringListenerRole,
    RuntimeSecurityMonitoringManager,
    RuntimeSecurityMonitoringSetting,
)
from aces.core.sdl.scenario import ModuleDescriptor, Scenario
from aces.core.sdl.validator import SemanticValidator


def _validate(scenario: Scenario) -> list[str]:
    validator = SemanticValidator(scenario)
    try:
        validator.validate()
        return []
    except SDLValidationError as exc:
        return exc.errors


def _security_manager(**overrides) -> dict:
    manager = {
        "manager_id": "techvault-wazuh",
        "service": "wazuh-api",
        "implementation": "wazuh",
        "manager_kind": "siem",
        "version": "v4.12.0",
        "revision": "rc1",
        "configuration_file_refs": ["/var/ossec/etc/ossec.conf"],
        "log_file_refs": ["/var/ossec/logs/ossec.log"],
        "listeners": [
            {
                "listener_id": "agent-events",
                "service": "wazuh-agent-events",
                "role": "agent_event_ingestion",
                "auth_required": True,
                "tls_enabled": True,
            },
            {
                "listener_id": "agent-enrollment",
                "service": "wazuh-enrollment",
                "role": "agent_enrollment",
                "auth_required": True,
                "tls_enabled": True,
            },
            {
                "listener_id": "manager-api",
                "service": "wazuh-api",
                "role": "api",
                "auth_required": True,
                "tls_enabled": True,
            },
        ],
        "components": [
            {"component_id": "analysisd", "kind": "analysis_engine", "name": "wazuh-analysisd", "status": "running"},
            {"component_id": "remoted", "kind": "agent_ingestion", "name": "wazuh-remoted", "status": "running"},
            {"component_id": "authd", "kind": "agent_enrollment", "name": "wazuh-authd", "status": "running"},
            {"component_id": "modulesd", "kind": "module_supervisor", "name": "wazuh-modulesd", "status": "running"},
            {"component_id": "clusterd", "kind": "cluster", "name": "wazuh-clusterd", "status": "stopped"},
            {"component_id": "api", "kind": "api", "name": "wazuh-apid", "status": "running"},
        ],
        "agents": [
            {"agent_id": "001", "name": "aptl-dns-agent", "status": "available", "group_refs": ["default"]},
            {"agent_id": "002", "name": "aptl-webapp-agent", "status": "available", "group_refs": ["default"]},
            {"agent_id": "003", "name": "dc.techvault.local", "status": "available", "group_refs": ["default"]},
        ],
        "agent_groups": [
            {
                "group_id": "default",
                "name": "default",
                "member_refs": ["001", "002", "003"],
                "configuration_file_refs": ["/var/ossec/etc/shared/default/agent.conf"],
            }
        ],
        "content_sets": [
            {
                "content_id": "wazuh-ruleset",
                "kind": "rule_corpus",
                "format": "wazuh_rule_xml",
                "file_count": 173,
                "file_refs": ["/var/ossec/ruleset/rules"],
                "loaded": True,
            },
            {
                "content_id": "wazuh-decoders",
                "kind": "decoder_corpus",
                "format": "wazuh_decoder_xml",
                "file_count": 123,
                "file_refs": ["/var/ossec/ruleset/decoders"],
                "loaded": True,
            },
        ],
        "settings": [
            {
                "setting_id": "json-output",
                "name": "jsonout_output",
                "value": "yes",
                "provenance": "configuration_file",
                "source_path": "/var/ossec/etc/ossec.conf",
            },
            {
                "setting_id": "vulnerability-detection",
                "name": "vulnerability_detection.enabled",
                "value": "yes",
                "provenance": "configuration_file",
                "source_path": "/var/ossec/etc/ossec.conf",
            },
        ],
    }
    manager.update(overrides)
    return manager


def _manager_node(manager: dict | None = None) -> dict:
    return {
        "type": "vm",
        "resources": {"ram": "2 gib", "cpu": 2},
        "services": [
            {"port": 1514, "protocol": "tcp", "name": "wazuh-agent-events"},
            {"port": 1515, "protocol": "tcp", "name": "wazuh-enrollment"},
            {"port": 514, "protocol": "udp", "name": "wazuh-syslog"},
            {"port": 55000, "protocol": "tcp", "name": "wazuh-api"},
        ],
        "runtime": {
            "filesystem_inventory": [
                {"path": "/var/ossec/etc/ossec.conf", "entry_type": "file"},
                {"path": "/var/ossec/logs/ossec.log", "entry_type": "file"},
                {"path": "/var/ossec/etc/shared/default/agent.conf", "entry_type": "file"},
                {"path": "/var/ossec/ruleset/rules", "entry_type": "directory"},
                {"path": "/var/ossec/ruleset/decoders", "entry_type": "directory"},
            ],
            "security_monitoring_managers": [manager or _security_manager()],
        },
    }


def test_security_monitoring_surface_is_node_scoped_not_top_level() -> None:
    assert "security_monitoring_managers" not in Scenario.model_fields
    assert "security_monitoring_managers" in RuntimeConfiguration.model_fields


def test_vm_runtime_security_monitoring_manager_inventory() -> None:
    node = Node(type="vm", runtime={"security_monitoring_managers": [_security_manager()]})

    manager = node.runtime.security_monitoring_managers[0]
    assert manager.manager_id == "techvault-wazuh"
    assert manager.implementation == RuntimeSecurityMonitoringImplementation.WAZUH
    assert manager.listeners[0].role == RuntimeSecurityMonitoringListenerRole.AGENT_EVENT_INGESTION
    assert manager.listeners[0].auth_required is True
    assert manager.components[0].kind == RuntimeSecurityMonitoringComponentKind.ANALYSIS_ENGINE
    assert manager.components[0].status == RuntimeSecurityMonitoringComponentStatus.RUNNING
    assert manager.agents[0].status == RuntimeSecurityMonitoringAgentStatus.AVAILABLE
    assert manager.content_sets[0].kind == RuntimeSecurityMonitoringContentKind.RULE_CORPUS
    assert manager.content_sets[1].format == RuntimeSecurityMonitoringContentFormat.WAZUH_DECODER_XML


def test_parser_accepts_kebab_case_runtime_security_monitoring_managers() -> None:
    scenario = parse_sdl(
        """
        name: security-monitoring-parser
        nodes:
          siem:
            type: vm
            resources: {ram: 2 gib, cpu: 2}
            services:
              - {port: 55000, name: wazuh-api}
            runtime:
              security-monitoring-managers:
                - manager-id: techvault-wazuh
                  service: wazuh-api
                  implementation: WAZUH
                  manager-kind: siem
                  listeners:
                    - listener-id: manager-api
                      service: wazuh-api
                      role: api
                      auth-required: true
                  content-sets:
                    - content-id: wazuh-ruleset
                      kind: rule-corpus
                      format: wazuh-rule-xml
                      file-count: 173
        """
    )

    manager = scenario.nodes["siem"].runtime.security_monitoring_managers[0]
    assert manager.manager_id == "techvault-wazuh"
    assert manager.listeners[0].role == RuntimeSecurityMonitoringListenerRole.API
    assert manager.content_sets[0].format == RuntimeSecurityMonitoringContentFormat.WAZUH_RULE_XML


def test_security_monitoring_manager_rejects_duplicate_stable_ids() -> None:
    with pytest.raises(ValidationError, match="Duplicate runtime security-monitoring stable id 'manager-api'"):
        RuntimeSecurityMonitoringManager(
            **_security_manager(
                components=[
                    {"component_id": "manager-api", "kind": "api", "name": "wazuh-apid"},
                ]
            )
        )


@pytest.mark.parametrize("setting_name", ["api_token", "api_key", "shared_key"])
def test_security_monitoring_setting_rejects_secret_bearing_raw_value(setting_name: str) -> None:
    with pytest.raises(ValidationError, match="must omit its raw value"):
        RuntimeSecurityMonitoringSetting(
            setting_id="api-token",
            name=setting_name,
            value="plaintext-token",
            value_classification="plain",
        )


class TestRuntimeSecurityMonitoringSemanticValidation:
    def test_manager_with_same_node_service_refs_is_valid(self) -> None:
        assert _validate(Scenario(name="security-monitoring", nodes={"siem": _manager_node()})) == []

    def test_listener_service_ref_must_reference_same_node_service(self) -> None:
        manager = _security_manager(
            listeners=[
                {
                    "listener_id": "manager-api",
                    "service": "nodes.other.services.wazuh-api",
                    "role": "api",
                }
            ]
        )
        scenario = Scenario(
            name="security-monitoring",
            nodes={
                "siem": _manager_node(manager),
                "other": {
                    "type": "vm",
                    "resources": {"ram": "1 gib", "cpu": 1},
                    "services": [{"port": 55000, "name": "wazuh-api"}],
                },
            },
        )

        errors = _validate(scenario)
        assert any("listener 'manager-api'" in error and "same node" in error for error in errors)

    def test_file_refs_resolve_to_runtime_filesystem_inventory_when_present(self) -> None:
        manager = _security_manager(configuration_file_refs=["/var/ossec/etc/missing.conf"])
        errors = _validate(Scenario(name="security-monitoring", nodes={"siem": _manager_node(manager)}))
        assert any("configuration_file_refs ref '/var/ossec/etc/missing.conf'" in error for error in errors)

    def test_agent_group_member_refs_must_resolve_to_agents(self) -> None:
        manager = _security_manager(
            agent_groups=[{"group_id": "default", "name": "default", "member_refs": ["ghost-agent"]}]
        )
        errors = _validate(Scenario(name="security-monitoring", nodes={"siem": _manager_node(manager)}))
        assert any("member_ref 'ghost-agent'" in error for error in errors)

    def test_agent_group_refs_must_resolve_to_groups(self) -> None:
        manager = _security_manager(
            agents=[{"agent_id": "001", "name": "aptl-dns-agent", "group_refs": ["ghost-group"]}],
            agent_groups=[{"group_id": "default", "name": "default"}],
        )
        errors = _validate(Scenario(name="security-monitoring", nodes={"siem": _manager_node(manager)}))
        assert any("group_ref 'ghost-group'" in error for error in errors)

    def test_relationship_target_to_manager_and_child_records_is_valid(self) -> None:
        scenario = Scenario(
            name="security-monitoring",
            nodes={
                "siem": _manager_node(),
                "client": {"type": "vm", "resources": {"ram": "1 gib", "cpu": 1}},
            },
            relationships={
                "client-to-siem": {
                    "type": "connects_to",
                    "source": "nodes.client",
                    "target": "nodes.siem.runtime.security_monitoring_managers.techvault-wazuh",
                },
                "manager-loads-rules": {
                    "type": "depends_on",
                    "source": "nodes.siem.runtime.security_monitoring_managers.techvault-wazuh",
                    "target": (
                        "nodes.siem.runtime.security_monitoring_managers.techvault-wazuh.content_sets.wazuh-ruleset"
                    ),
                },
                "agent-inventory": {
                    "type": "depends_on",
                    "source": ("nodes.siem.runtime.security_monitoring_managers.techvault-wazuh.agent_groups.default"),
                    "target": "nodes.siem.runtime.security_monitoring_managers.techvault-wazuh.agents.001",
                },
            },
        )

        assert _validate(scenario) == []


def test_module_symbol_index_rewrites_runtime_security_monitoring_refs() -> None:
    scenario = Scenario(
        name="shared",
        module=ModuleDescriptor(id="acme/shared", version="1.0.0", exports={"nodes": ["siem"]}),
        nodes={"siem": _manager_node()},
    )

    named = symbol_index(
        scenario,
        namespace="shared",
        descriptor=scenario.module,
    )["named"]

    assert named["nodes.siem.runtime.security_monitoring_managers.techvault-wazuh"] == (
        "nodes.shared.siem.runtime.security_monitoring_managers.techvault-wazuh"
    )
    assert named["nodes.siem.runtime.security_monitoring_managers.techvault-wazuh.listeners.manager-api"] == (
        "nodes.shared.siem.runtime.security_monitoring_managers.techvault-wazuh.listeners.manager-api"
    )
    assert named["nodes.siem.runtime.security_monitoring_managers.techvault-wazuh.agents.001"] == (
        "nodes.shared.siem.runtime.security_monitoring_managers.techvault-wazuh.agents.001"
    )
    assert named["nodes.siem.runtime.security_monitoring_managers.techvault-wazuh.content_sets.wazuh-ruleset"] == (
        "nodes.shared.siem.runtime.security_monitoring_managers.techvault-wazuh.content_sets.wazuh-ruleset"
    )
