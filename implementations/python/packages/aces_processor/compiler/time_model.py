"""Compile authored shared time declarations into canonical runtime metadata."""

from aces_contracts.addressing import render_compiled_address
from aces_sdl.scenario import InstantiatedScenario

from ..models.time_model import (
    CompiledClock,
    CompiledTemporalConstraint,
    CompiledTimeDomain,
    CompiledTimeDomainMapping,
    CompiledTimeModel,
    CompiledTimeProgressionPolicy,
)


def _address(kind: str, name: str) -> str:
    return render_compiled_address("time", kind, name)


def _subject_address(scenario: InstantiatedScenario, ref: str) -> str:
    for section_name in (
        "nodes",
        "infrastructure",
        "features",
        "conditions",
        "propositions",
        "assertions",
        "vulnerabilities",
        "entities",
        "injects",
        "events",
        "scripts",
        "stories",
        "content",
        "generated_artifacts",
        "persistent_volumes",
        "accounts",
        "identity_domains",
        "relationships",
        "agents",
        "action_contracts",
        "observation_boundaries",
        "outcome_interpretation_rules",
        "behavior_specifications",
        "evidence_requirements",
        "objectives",
        "workflows",
    ):
        declarations = getattr(scenario, section_name)
        if ref in declarations:
            return render_compiled_address("sdl", section_name.replace("_", "-"), ref)
        prefix = f"{section_name}."
        candidate = ref[len(prefix) :] if ref.startswith(prefix) else ""
        if candidate in declarations:
            return render_compiled_address("sdl", section_name.replace("_", "-"), candidate)
    for workflow_name, workflow in scenario.workflows.items():
        prefix = f"{workflow_name}."
        if ref.startswith(prefix) and ref[len(prefix) :] in workflow.steps:
            return render_compiled_address("sdl", "workflow-step", workflow_name, ref[len(prefix) :])
    raise ValueError(f"validated temporal subject ref did not resolve: {ref}")


def compile_time_model(scenario: InstantiatedScenario) -> CompiledTimeModel:
    """Compile a semantically admitted scenario time model."""

    domains = tuple(
        CompiledTimeDomain(
            address=_address("domain", name),
            kind=domain.kind.value,
            tick_period_numerator=domain.tick_period_seconds.numerator,
            tick_period_denominator=domain.tick_period_seconds.denominator,
            epoch=domain.epoch.value,
            visibility=domain.visibility.value,
            description=domain.description,
        )
        for name, domain in scenario.time_domains.items()
    )
    clocks = tuple(
        CompiledClock(
            address=_address("clock", name),
            time_domain_address=_address("domain", clock.time_domain_ref),
            authority_kind=clock.authority_kind.value,
            authority_ref=clock.authority_ref,
            monotonicity=clock.monotonicity.value,
            supports_pause=clock.supports_pause,
            supports_reset=clock.supports_reset,
            supports_jump=clock.supports_jump,
            description=clock.description,
        )
        for name, clock in scenario.clocks.items()
    )
    mappings = tuple(
        CompiledTimeDomainMapping(
            address=_address("mapping", name),
            source_domain_address=_address("domain", mapping.source_domain_ref),
            target_domain_address=_address("domain", mapping.target_domain_ref),
            mapping_kind=mapping.mapping_kind.value,
            scale_numerator=mapping.scale.numerator,
            scale_denominator=mapping.scale.denominator,
            offset_ticks=mapping.offset_ticks,
            description=mapping.description,
        )
        for name, mapping in scenario.time_domain_mappings.items()
    )
    policies = tuple(
        CompiledTimeProgressionPolicy(
            address=_address("policy", name),
            clock_address=_address("clock", policy.clock_ref),
            advancement_mode=policy.advancement_mode.value,
            pacing_numerator=policy.pacing_ratio.numerator,
            pacing_denominator=policy.pacing_ratio.denominator,
            synchronization_mode=policy.synchronization_mode.value,
            step_ticks=policy.step_ticks,
            drift_bound_ticks=policy.drift_bound_ticks,
            reset_behavior=policy.reset_behavior.value,
            replay_behavior=policy.replay_behavior.value,
            description=policy.description,
        )
        for name, policy in scenario.time_progression_policies.items()
    )
    constraints = tuple(
        CompiledTemporalConstraint(
            address=_address("constraint", name),
            kind=constraint.constraint_kind.value,
            clock_address=_address("clock", constraint.clock_ref),
            subject_addresses=tuple(_subject_address(scenario, ref) for ref in constraint.subject_refs),
            start_tick=constraint.start.tick if constraint.start else None,
            start_microstep=constraint.start.microstep if constraint.start else None,
            end_tick=constraint.end.tick if constraint.end else None,
            end_microstep=constraint.end.microstep if constraint.end else None,
            duration_ticks=constraint.duration_ticks,
            cadence_ticks=constraint.cadence_ticks,
            description=constraint.description,
        )
        for name, constraint in scenario.temporal_constraints.items()
    )
    return CompiledTimeModel(
        domains=domains,
        clocks=clocks,
        mappings=mappings,
        progression_policies=policies,
        constraints=constraints,
    )


__all__ = ["compile_time_model"]
