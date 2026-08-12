"""Issue #1043: forwarding-agent ownership and evidence-plane posture."""

from __future__ import annotations

import textwrap

import pytest
from raes import SDLValidationError, parse_sdl
from raes.runtime_forwarding_agent import (
    RuntimeForwardingAgent,
    RuntimeForwardingAgentOwnershipRole,
)


def _evidence_requirement(source_ref: str) -> str:
    return f"""
    evidence_requirements:
      agent-output:
        source_refs: [{source_ref}]
        source_class: apparatus
        scope: experiment-run
        window: run
        channel: log
        artifact_role: measurement-log
        sensitivity: plain
        redaction: none
        integrity: checksum
        retention: run_lifetime
        loss_disclosure: required
    """


def _node_agent_scenario(*, role: str, bind_evidence: bool) -> str:
    evidence = _evidence_requirement("nodes.sensor.runtime.forwarding_agents.telemetry") if bind_evidence else ""
    return f"""
    name: forwarding-agent-posture
    nodes:
      sensor:
        type: compute
        resources: {{ram: 1 gib, cpu: 1}}
        runtime:
          forwarding_agents:
            - forwarding_agent_id: telemetry
              agent_kind: other
              ownership_role: {role}
    {evidence}
    """


def test_forwarding_agent_defaults_to_system_under_test() -> None:
    agent = RuntimeForwardingAgent(forwarding_agent_id="telemetry")

    assert agent.ownership_role is RuntimeForwardingAgentOwnershipRole.SYSTEM_UNDER_TEST


def test_measurement_apparatus_requires_and_accepts_inbound_evidence_binding() -> None:
    scenario = parse_sdl(_node_agent_scenario(role="measurement_apparatus", bind_evidence=True))

    agent = scenario.nodes["sensor"].runtime.forwarding_agents[0]
    assert agent.ownership_role is RuntimeForwardingAgentOwnershipRole.MEASUREMENT_APPARATUS


def test_measurement_apparatus_without_evidence_binding_fails_closed() -> None:
    source = _node_agent_scenario(role="measurement_apparatus", bind_evidence=False)
    with pytest.raises(SDLValidationError) as excinfo:
        parse_sdl(source)

    assert any(
        "measurement_apparatus" in error and "EvidenceRequirement.source_refs" in error
        for error in excinfo.value.errors
    )


def test_system_under_test_cannot_be_claimed_as_apparatus_evidence_source() -> None:
    source = _node_agent_scenario(role="system_under_test", bind_evidence=True)
    with pytest.raises(SDLValidationError) as excinfo:
        parse_sdl(source)

    assert any("system_under_test" in error and "source_class 'apparatus'" in error for error in excinfo.value.errors)


def test_scenario_level_measurement_apparatus_is_a_targetable_evidence_source() -> None:
    source = textwrap.dedent(
        """
        name: scenario-forwarding-apparatus
        forwarding_agents:
          - forwarding_agent_id: telemetry
            agent_kind: other
            ownership_role: measurement_apparatus
        """
    ) + textwrap.dedent(_evidence_requirement("forwarding_agents.telemetry"))

    scenario = parse_sdl(source)

    assert scenario.forwarding_agents[0].ownership_role is RuntimeForwardingAgentOwnershipRole.MEASUREMENT_APPARATUS
