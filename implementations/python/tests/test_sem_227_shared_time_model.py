"""SEM-227/228/229, DSL-126/127/128, and RUN-317/318 shared time model."""

from __future__ import annotations

import textwrap
from fractions import Fraction
from pathlib import Path

import pytest
from aces_processor.compiler import compile_runtime_model
from aces_runtime.time_coordinator import ClockLifecycleState, TimeCoordinator
from hypothesis import given
from hypothesis import strategies as st
from raes._errors import SDLParseError, SDLValidationError
from raes.parser import parse_sdl, parse_sdl_file


def _scenario_yaml() -> str:
    return textwrap.dedent(
        """
        name: shared-time
        nodes:
          workstation:
            type: VM
            resources: {ram: 1 GiB, cpu: 1}
        time_domains:
          scenario:
            kind: simulated
            tick_period_seconds: {numerator: 1, denominator: 1000}
            epoch: scenario_start
            visibility: participant_visible
            description: exact scenario milliseconds
          evidence:
            kind: wall_clock
            tick_period_seconds: {numerator: 1, denominator: 1000000000}
            epoch: unix
            visibility: evidence_only
            description: evidence capture timestamps
        clocks:
          scenario-clock:
            time_domain_ref: scenario
            authority_kind: runtime
            authority_ref: runtime.time-coordinator
            monotonicity: non_decreasing
            supports_pause: true
            supports_reset: true
            description: authoritative scenario clock
          evidence-clock:
            time_domain_ref: evidence
            authority_kind: system
            authority_ref: apparatus.system-clock
            monotonicity: may_jump
            supports_jump: true
            description: non-semantic evidence timestamp clock
        time_domain_mappings:
          scenario-to-evidence:
            source_domain_ref: scenario
            target_domain_ref: evidence
            mapping_kind: affine_rational
            scale: {numerator: 1000000, denominator: 1}
            offset_ticks: 100
            description: admitted example anchor
        time_progression_policies:
          scenario-policy:
            clock_ref: scenario-clock
            advancement_mode: stepped
            synchronization_mode: barrier
            step_ticks: 10
            reset_behavior: new_segment_zero
            replay_behavior: restore_recorded_advances
            description: deterministic stepped scenario progression
          evidence-policy:
            clock_ref: evidence-clock
            advancement_mode: real_time
            synchronization_mode: authority
            reset_behavior: unsupported
            replay_behavior: unsupported
            description: evidence timestamps follow the system authority
        temporal_constraints:
          workstation-window:
            constraint_kind: window
            clock_ref: scenario-clock
            subject_refs: [nodes.workstation]
            start: {tick: 10}
            end: {tick: 100}
            description: workstation activity is eligible within this window
        """
    )


def test_shared_time_model_parses_and_compiles_exact_authorities() -> None:
    scenario = parse_sdl(_scenario_yaml())
    model = compile_runtime_model(scenario)

    assert model.time_model.domains[0].address == "time.domain.scenario"
    assert model.time_model.domains[0].tick_period_denominator == 1000
    assert model.time_model.clocks[0].time_domain_address == "time.domain.scenario"
    assert model.time_model.progression_policies[0].step_ticks == 10
    assert model.time_model.constraints[0].subject_addresses == ("sdl.nodes.workstation",)


def test_time_coordinator_preserves_segments_and_append_only_history() -> None:
    model = compile_runtime_model(parse_sdl(_scenario_yaml()))
    coordinator = TimeCoordinator(model.time_model)
    snapshot = coordinator.initialize()

    clock = "time.clock.scenario-clock"
    snapshot = coordinator.advance(snapshot, clock, ticks=10)
    snapshot = coordinator.pause(snapshot, clock)
    assert snapshot.time_model_state is not None
    assert snapshot.time_model_state.clocks[clock].state == ClockLifecycleState.PAUSED.value
    with pytest.raises(ValueError, match="paused clock"):
        coordinator.advance(snapshot, clock, ticks=10)
    snapshot = coordinator.resume(snapshot, clock)
    snapshot = coordinator.reset(snapshot, clock)

    reading = coordinator.reading(snapshot, clock)
    assert (reading.segment, reading.tick, reading.microstep) == (1, 0, 0)
    history = snapshot.time_model_state.clocks[clock].history
    assert [event.sequence for event in history] == list(range(5))
    assert [event.kind for event in history] == [
        "initialize",
        "advance",
        "pause",
        "resume",
        "reset",
    ]


def test_time_domains_are_incomparable_without_an_explicit_mapping() -> None:
    model = compile_runtime_model(parse_sdl(_scenario_yaml()))
    coordinator = TimeCoordinator(model.time_model)

    assert coordinator.convert_tick("time.mapping.scenario-to-evidence", 2) == Fraction(2000100, 1)
    with pytest.raises(KeyError, match="unknown compiled time-domain mapping"):
        coordinator.convert_tick("time.mapping.evidence-to-scenario", 2)


def test_time_model_rejects_dangling_clock_and_subject_refs() -> None:
    dangling_clock = _scenario_yaml().replace("time_domain_ref: scenario", "time_domain_ref: missing", 1)
    with pytest.raises(SDLValidationError, match="does not reference a declared time domain"):
        parse_sdl(dangling_clock)

    dangling_subject = _scenario_yaml().replace(
        "subject_refs: [nodes.workstation]",
        "subject_refs: [nodes.missing]",
    )
    with pytest.raises(SDLValidationError, match="does not reference any defined element"):
        parse_sdl(dangling_subject)


def test_time_model_rejects_implicit_or_ambiguous_progression() -> None:
    unreduced = _scenario_yaml().replace(
        "tick_period_seconds: {numerator: 1, denominator: 1000}",
        "tick_period_seconds: {numerator: 2, denominator: 2000}",
        1,
    )
    with pytest.raises(SDLParseError, match="exact ratios must be reduced"):
        parse_sdl(unreduced)

    wrong_step = _scenario_yaml().replace("step_ticks: 10", "step_ticks: 9")
    model = compile_runtime_model(parse_sdl(wrong_step))
    coordinator = TimeCoordinator(model.time_model)
    snapshot = coordinator.initialize()
    with pytest.raises(ValueError, match="declared step_ticks"):
        coordinator.advance(snapshot, "time.clock.scenario-clock", ticks=10)


def test_shared_time_model_references_follow_module_namespacing(tmp_path: Path) -> None:
    module = tmp_path / "time-module.yaml"
    module.write_text(
        """
name: time-module
module:
  id: aces/time-module
  version: 1.0.0
  exports:
    nodes: [workstation]
    time_domains: [scenario]
    clocks: [scenario-clock]
    time_progression_policies: [scenario-policy]
    temporal_constraints: [workstation-window]
nodes:
  workstation:
    type: VM
    resources: {ram: 1 GiB, cpu: 1}
time_domains:
  scenario:
    kind: simulated
    tick_period_seconds: {numerator: 1, denominator: 1}
    epoch: scenario_start
    description: module scenario time
clocks:
  scenario-clock:
    time_domain_ref: scenario
    authority_kind: runtime
    authority_ref: runtime.time-coordinator
    monotonicity: non_decreasing
    supports_reset: true
    description: module scenario clock
time_progression_policies:
  scenario-policy:
    clock_ref: scenario-clock
    advancement_mode: event_driven
    synchronization_mode: barrier
    reset_behavior: new_segment_zero
    replay_behavior: restart_from_anchor
    description: module progression
temporal_constraints:
  workstation-window:
    constraint_kind: window
    clock_ref: scenario-clock
    subject_refs: [nodes.workstation]
    start: {tick: 0}
    end: {tick: 10}
    description: module activity window
""",
        encoding="utf-8",
    )
    root = tmp_path / "root.yaml"
    root.write_text(
        """
name: root
imports:
  - path: time-module.yaml
    namespace: shared
""",
        encoding="utf-8",
    )

    scenario = parse_sdl_file(root)

    assert scenario.clocks["shared.scenario-clock"].time_domain_ref == "shared.scenario"
    assert scenario.time_progression_policies["shared.scenario-policy"].clock_ref == "shared.scenario-clock"
    constraint = scenario.temporal_constraints["shared.workstation-window"]
    assert constraint.clock_ref == "shared.scenario-clock"
    assert constraint.subject_refs == ["nodes.shared.workstation"]


@given(st.lists(st.sampled_from(("advance", "reset")), min_size=1, max_size=30))
def test_clock_transition_history_is_append_only_across_generated_lifecycles(
    operations: list[str],
) -> None:
    model = compile_runtime_model(parse_sdl(_scenario_yaml()))
    coordinator = TimeCoordinator(model.time_model)
    snapshot = coordinator.initialize()
    clock = "time.clock.scenario-clock"

    expected_segment = 0
    expected_tick = 0
    for operation in operations:
        if operation == "advance":
            snapshot = coordinator.advance(snapshot, clock, ticks=10)
            expected_tick += 10
        else:
            snapshot = coordinator.reset(snapshot, clock)
            expected_segment += 1
            expected_tick = 0

    reading = coordinator.reading(snapshot, clock)
    assert snapshot.time_model_state is not None
    history = snapshot.time_model_state.clocks[clock].history
    assert (reading.segment, reading.tick) == (expected_segment, expected_tick)
    assert [event.sequence for event in history] == list(range(len(operations) + 1))
    assert len(history) == len(operations) + 1
