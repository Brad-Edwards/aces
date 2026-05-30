"""Runtime forwarding-agent (SCN-010 §5.5) SDL surface tests.

Covers the OPEN ``agent_kind`` discriminator spine, the typed source / transform
/ ship-target / buffer-policy / reload-channel / setting children, secret-bearing
setting + enrollment-identity redaction, duplicate-id rejection, and — the core
correctness feature — the ``require_profile_for_agent_kind`` guard (positive for
``log_forwarder`` and ``content_sync`` plus each REQUIRE / REJECT negative).
"""

from __future__ import annotations

import pytest
from aces_sdl.runtime_forwarding_agent import (
    RuntimeForwardingAgent,
    RuntimeForwardingAgentImplementation,
    RuntimeForwardingAgentKind,
    RuntimeForwardingBufferCrypto,
    RuntimeForwardingBufferPolicy,
    RuntimeForwardingEnrollmentClassification,
    RuntimeForwardingParseFormat,
    RuntimeForwardingProtocol,
    RuntimeForwardingReloadChannel,
    RuntimeForwardingReloadChannelKind,
    RuntimeForwardingSetting,
    RuntimeForwardingShipTarget,
    RuntimeForwardingSource,
    RuntimeForwardingSourceKind,
    RuntimeForwardingTransform,
    RuntimeForwardingTransformKind,
)
from pydantic import ValidationError

from aces.core.sdl._errors import SDLValidationError
from aces.core.sdl.scenario import Scenario
from aces.core.sdl.validator import SemanticValidator

# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #


def _log_forwarder(**overrides) -> dict:
    agent = {
        "forwarding_agent_id": "wazuh-sidecar-suricata",
        "implementation": "wazuh_agent",
        "agent_kind": "log_forwarder",
        "version": "4.7.0",
        "name": "suricata-eve-shipper",
        "sources": [
            {
                "source_id": "eve",
                "kind": "tailed_path",
                "location": "/logs/eve.json",
                "parse_format": "json",
            }
        ],
        "transforms": [{"transform_id": "passthrough", "kind": "passthrough"}],
        "ship_targets": [
            {
                "target_id": "manager",
                "target_node_ref": "wazuh.manager",
                "ingestion_port": 1514,
                "enrollment_port": 1515,
                "protocol": "syslog",
                "enrollment_identity_classification": "redacted",
            }
        ],
        "buffer_policy": {
            "buffer_policy_id": "client-buffer",
            "queue_capacity": 5000,
            "eps": 500,
            "crypto": "aes",
            "reconnect_seconds": 60,
        },
        "settings": [
            {
                "setting_id": "node-name",
                "name": "node_name",
                "value": "suricata-sidecar",
                "provenance": "configuration_file",
            }
        ],
    }
    agent.update(overrides)
    return agent


def _content_sync(**overrides) -> dict:
    agent = {
        "forwarding_agent_id": "misp-suricata-sync",
        "implementation": "misp_suricata_sync",
        "agent_kind": "content_sync",
        "version": "1.0",
        "name": "misp-iocs-to-rules",
        "sources": [
            {
                "source_id": "misp-feed",
                "kind": "api_pull",
                "location": "https://misp/attributes/restSearch",
                "parse_format": "misp_json",
                "selector": "aptl:enforce",
            }
        ],
        "transforms": [
            {"transform_id": "ioc-rule", "kind": "ioc_to_rule", "sid_namespace": "99000000"},
        ],
        "ship_targets": [
            {
                "target_id": "rules-file",
                "target_service_ref": "suricata",
                "protocol": "tcp",
            }
        ],
        "reload_channels": [
            {
                "reload_channel_id": "suricata-reload",
                "target_ref": "suricata.control_channels.rule-reload",
                "kind": "unix_socket",
            }
        ],
    }
    agent.update(overrides)
    return agent


# --------------------------------------------------------------------------- #
# Construction / typed-child coercion                                         #
# --------------------------------------------------------------------------- #


def test_log_forwarder_typed_children() -> None:
    agent = RuntimeForwardingAgent(**_log_forwarder())

    assert agent.forwarding_agent_id == "wazuh-sidecar-suricata"
    assert agent.implementation is RuntimeForwardingAgentImplementation.WAZUH_AGENT
    assert agent.agent_kind is RuntimeForwardingAgentKind.LOG_FORWARDER
    assert isinstance(agent.sources[0], RuntimeForwardingSource)
    assert agent.sources[0].kind is RuntimeForwardingSourceKind.TAILED_PATH
    assert agent.sources[0].parse_format is RuntimeForwardingParseFormat.JSON
    assert isinstance(agent.transforms[0], RuntimeForwardingTransform)
    assert agent.transforms[0].kind is RuntimeForwardingTransformKind.PASSTHROUGH
    target = agent.ship_targets[0]
    assert isinstance(target, RuntimeForwardingShipTarget)
    assert target.ingestion_port == 1514
    assert target.enrollment_port == 1515
    assert target.protocol is RuntimeForwardingProtocol.SYSLOG
    assert target.enrollment_identity_classification is RuntimeForwardingEnrollmentClassification.REDACTED
    assert isinstance(agent.buffer_policy, RuntimeForwardingBufferPolicy)
    assert agent.buffer_policy.crypto is RuntimeForwardingBufferCrypto.AES
    assert agent.buffer_policy.queue_capacity == 5000


def test_content_sync_typed_children() -> None:
    agent = RuntimeForwardingAgent(**_content_sync())

    assert agent.agent_kind is RuntimeForwardingAgentKind.CONTENT_SYNC
    assert agent.sources[0].kind is RuntimeForwardingSourceKind.API_PULL
    assert agent.sources[0].selector == "aptl:enforce"
    assert agent.transforms[0].kind is RuntimeForwardingTransformKind.IOC_TO_RULE
    assert agent.transforms[0].sid_namespace == "99000000"
    assert isinstance(agent.reload_channels[0], RuntimeForwardingReloadChannel)
    assert agent.reload_channels[0].kind is RuntimeForwardingReloadChannelKind.UNIX_SOCKET
    assert agent.buffer_policy is None


def test_kebab_case_enum_inputs_normalize() -> None:
    agent = RuntimeForwardingAgent(
        **_log_forwarder(
            implementation="Wazuh-Agent",
            sources=[{"source_id": "s1", "kind": "tailed-path", "parse_format": "eve-json"}],
        )
    )
    assert agent.implementation is RuntimeForwardingAgentImplementation.WAZUH_AGENT
    assert agent.sources[0].kind is RuntimeForwardingSourceKind.TAILED_PATH
    assert agent.sources[0].parse_format is RuntimeForwardingParseFormat.EVE_JSON


def test_open_tail_kinds_impose_no_profile() -> None:
    # unknown / other are permissive — a near-empty instance validates.
    for kind in ("unknown", "other"):
        agent = RuntimeForwardingAgent(forwarding_agent_id=f"agent-{kind}", agent_kind=kind)
        assert agent.agent_kind.value == kind


def test_variable_ref_agent_kind_is_exempt_from_guard() -> None:
    agent = RuntimeForwardingAgent(forwarding_agent_id="agent-var", agent_kind="${AGENT_KIND}")
    assert agent.agent_kind == "${AGENT_KIND}"


def test_invalid_enum_value_rejected() -> None:
    with pytest.raises(ValidationError, match="agent_kind must be one of"):
        RuntimeForwardingAgent(forwarding_agent_id="bad", agent_kind="totally_invalid")


def test_id_fields_reject_variable_placeholders() -> None:
    with pytest.raises(ValidationError, match="forwarding_agent_id must be a stable identifier"):
        RuntimeForwardingAgent(forwarding_agent_id="${ID}")


# --------------------------------------------------------------------------- #
# Duplicate-id and secret-redaction guards                                    #
# --------------------------------------------------------------------------- #


def test_rejects_duplicate_stable_ids_across_children() -> None:
    with pytest.raises(ValidationError, match="Duplicate runtime forwarding agent stable id 'dup'"):
        RuntimeForwardingAgent(
            **_log_forwarder(
                sources=[{"source_id": "dup", "kind": "tailed_path"}],
                transforms=[{"transform_id": "dup", "kind": "passthrough"}],
            )
        )


def test_buffer_policy_id_participates_in_uniqueness() -> None:
    with pytest.raises(ValidationError, match="Duplicate runtime forwarding agent stable id 'shared'"):
        RuntimeForwardingAgent(
            **_log_forwarder(
                sources=[{"source_id": "shared", "kind": "tailed_path"}],
                buffer_policy={
                    "buffer_policy_id": "shared",
                    "queue_capacity": 1,
                },
                ship_targets=[{"target_id": "t1", "ingestion_port": 1514}],
            )
        )


def test_secret_named_setting_must_omit_raw_value() -> None:
    with pytest.raises(ValidationError, match="secret-bearing name and must omit its raw value"):
        RuntimeForwardingSetting(setting_id="enroll", name="enrollment_key", value="hunter2")


def test_secret_named_setting_redacted_is_accepted() -> None:
    setting = RuntimeForwardingSetting(setting_id="enroll", name="authd.pass", classification="redacted")
    assert setting.classification.value == "redacted"


def test_classified_setting_must_omit_value_even_with_plain_name() -> None:
    with pytest.raises(ValidationError, match="must omit its raw value"):
        RuntimeForwardingSetting(setting_id="s", name="something", value="x", classification="operator_secret")


def test_ship_target_port_range_enforced() -> None:
    with pytest.raises(ValidationError, match="ingestion_port must be <= 65535"):
        RuntimeForwardingShipTarget(target_id="t", ingestion_port=70000)


# --------------------------------------------------------------------------- #
# require_profile_for_agent_kind — log_forwarder                              #
# --------------------------------------------------------------------------- #


def test_log_forwarder_positive_profile() -> None:
    # The full fixture already satisfies the profile.
    RuntimeForwardingAgent(**_log_forwarder())


def test_log_forwarder_requires_buffer_policy() -> None:
    with pytest.raises(ValidationError, match="requires a buffer_policy"):
        RuntimeForwardingAgent(**_log_forwarder(buffer_policy=None))


def test_log_forwarder_requires_ingestion_endpoint() -> None:
    with pytest.raises(ValidationError, match="requires >=1 ship_target carrying an ingestion endpoint"):
        RuntimeForwardingAgent(
            **_log_forwarder(
                ship_targets=[
                    {"target_id": "manager", "enrollment_port": 1515, "protocol": "syslog"},
                ]
            )
        )


def test_log_forwarder_rejects_ioc_to_rule_transform() -> None:
    with pytest.raises(ValidationError, match="must not carry a transform of kind 'ioc_to_rule'"):
        RuntimeForwardingAgent(
            **_log_forwarder(
                transforms=[{"transform_id": "bad", "kind": "ioc_to_rule"}],
            )
        )


# --------------------------------------------------------------------------- #
# require_profile_for_agent_kind — content_sync                               #
# --------------------------------------------------------------------------- #


def test_content_sync_positive_profile() -> None:
    RuntimeForwardingAgent(**_content_sync())


def test_content_sync_requires_api_pull_source() -> None:
    with pytest.raises(ValidationError, match="requires >=1 source of kind 'api_pull'"):
        RuntimeForwardingAgent(
            **_content_sync(
                sources=[{"source_id": "s", "kind": "tailed_path"}],
            )
        )


def test_content_sync_requires_ioc_to_rule_transform() -> None:
    with pytest.raises(ValidationError, match="requires >=1 transform of kind 'ioc_to_rule'"):
        RuntimeForwardingAgent(
            **_content_sync(
                transforms=[{"transform_id": "t", "kind": "parse"}],
            )
        )


def test_content_sync_requires_reload_channel() -> None:
    with pytest.raises(ValidationError, match="requires >=1 reload_channel"):
        RuntimeForwardingAgent(**_content_sync(reload_channels=[]))


def test_content_sync_rejects_buffer_policy() -> None:
    with pytest.raises(ValidationError, match="must not carry a buffer_policy"):
        RuntimeForwardingAgent(
            **_content_sync(
                buffer_policy={"buffer_policy_id": "b", "queue_capacity": 1},
            )
        )


def test_content_sync_rejects_enrollment_port_endpoint() -> None:
    with pytest.raises(ValidationError, match="must not carry a ship_target enrollment endpoint"):
        RuntimeForwardingAgent(
            **_content_sync(
                ship_targets=[{"target_id": "rules", "enrollment_port": 1515}],
            )
        )


def test_content_sync_rejects_enrollment_identity_classification() -> None:
    with pytest.raises(ValidationError, match="must not carry a ship_target enrollment endpoint"):
        RuntimeForwardingAgent(
            **_content_sync(
                ship_targets=[
                    {"target_id": "rules", "enrollment_identity_classification": "operator_secret"},
                ]
            )
        )


def test_content_sync_allows_ship_target_without_enrollment() -> None:
    # A ship_target with no enrollment endpoint and the default 'none' class is fine.
    agent = RuntimeForwardingAgent(
        **_content_sync(
            ship_targets=[{"target_id": "rules", "ingestion_port": 0}],
        )
    )
    assert agent.ship_targets[0].enrollment_identity_classification is RuntimeForwardingEnrollmentClassification.NONE


# --------------------------------------------------------------------------- #
# Scenario-level ship_target ref resolution (validator.py)                     #
# --------------------------------------------------------------------------- #


def _validate(scenario: Scenario) -> list[str]:
    validator = SemanticValidator(scenario)
    try:
        validator.validate()
        return []
    except SDLValidationError as exc:
        return exc.errors


def _manager_node() -> dict:
    return {
        "type": "vm",
        "resources": {"ram": "2 gib", "cpu": 2},
        "services": [{"port": 1514, "protocol": "tcp", "name": "wazuh-agent-events"}],
    }


def _sensor_node(agent: dict) -> dict:
    return {
        "type": "vm",
        "resources": {"ram": "1 gib", "cpu": 1},
        "services": [{"port": 80, "protocol": "tcp", "name": "suricata"}],
        "runtime": {"forwarding_agents": [agent]},
    }


def test_surface_is_node_scoped_not_top_level() -> None:
    assert "forwarding_agents" not in Scenario.model_fields


def test_log_forwarder_target_node_ref_resolves_to_defined_node() -> None:
    # The _log_forwarder fixture ships to target_node_ref "wazuh.manager".
    scenario = Scenario(
        name="forwarding",
        nodes={"wazuh.manager": _manager_node(), "sensor": _sensor_node(_log_forwarder())},
    )
    assert _validate(scenario) == []


def test_ship_target_node_ref_must_resolve_to_defined_node() -> None:
    agent = _log_forwarder(
        ship_targets=[{"target_id": "manager", "target_node_ref": "ghost-node", "ingestion_port": 1514}],
    )
    scenario = Scenario(name="forwarding", nodes={"sensor": _sensor_node(agent)})
    errors = _validate(scenario)
    assert any("target_node_ref 'ghost-node'" in error for error in errors)


def test_ship_target_service_ref_must_resolve_on_target_node() -> None:
    agent = _log_forwarder(
        ship_targets=[
            {
                "target_id": "manager",
                "target_node_ref": "manager",
                "target_service_ref": "missing-svc",
                "ingestion_port": 1514,
            }
        ],
    )
    scenario = Scenario(
        name="forwarding",
        nodes={"manager": _manager_node(), "sensor": _sensor_node(agent)},
    )
    errors = _validate(scenario)
    assert any("target_service_ref 'missing-svc'" in error and "manager" in error for error in errors)


def test_content_sync_target_service_ref_resolves_on_owning_node() -> None:
    # No target_node_ref -> the service ref must resolve on the forwarder's own node.
    scenario = Scenario(name="forwarding", nodes={"sensor": _sensor_node(_content_sync())})
    assert _validate(scenario) == []
