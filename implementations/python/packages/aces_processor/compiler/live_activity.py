"""Compile admitted live-activity policy without creating plan resources."""

from __future__ import annotations

from aces_contracts.contracts.historical_state import HistoricalBaselineDigestModel
from aces_contracts.contracts.live_activity import (
    ActivityGovernedEntropyIdentityModel,
    ActivityPublicSeedIdentityModel,
    ActivityRationalQuantityModel,
    CompiledActivityActionModel,
    CompiledActivityBudgetEnvelopeModel,
    CompiledActivityProfileModel,
)
from aces_contracts.live_activity_addressing import derive_activity_profile_digest
from aces_sdl.scenario import InstantiatedScenario
from aces_sdl.semantics.domain_topology import resolve_section_ref

from aces_processor.semantics.planner import reverse_delete_order, topological_dependency_order

from .addresses import _resolve_node_service_ref


def _canonical_activity_ref(profile_id: str, collection: str, local_id: str) -> str:
    return f"activity_profiles.{profile_id}.{collection}.{local_id}"


def _entropy_identity(profile: object) -> ActivityPublicSeedIdentityModel | ActivityGovernedEntropyIdentityModel:
    entropy = profile.randomness.root_entropy
    if entropy.kind == "public-seed":
        return ActivityPublicSeedIdentityModel(
            kind="public-seed",
            encoding=entropy.encoding,
            value=entropy.value,
        )
    return ActivityGovernedEntropyIdentityModel(
        kind="governed-reference",
        reference_id=entropy.reference_id,
        reference_version=entropy.reference_version,
    )


def _action_graph_address(profile_id: str, action_id: str) -> str:
    return f"live-activity.{profile_id}.actions.{action_id}"


def _rational(value: object) -> ActivityRationalQuantityModel:
    return ActivityRationalQuantityModel(
        numerator=value.numerator,
        denominator=value.denominator,
    )


def _compile_budget(budget: object) -> CompiledActivityBudgetEnvelopeModel:
    return CompiledActivityBudgetEnvelopeModel(
        dimension=budget.dimension.value,
        unit=budget.unit.value,
        window_seconds=int(budget.window_seconds),
        action_demands={action_id: _rational(demand) for action_id, demand in sorted(budget.action_demands.items())},
        range_capacity=_rational(budget.range_capacity),
        fleet_capacity=_rational(budget.fleet_capacity),
        participant_reservation=_rational(budget.participant_reservation),
    )


def _dependency_graph(profile_id: str, profile: object) -> dict[str, tuple[str, ...]]:
    graph: dict[str, list[str]] = {_action_graph_address(profile_id, action_id): [] for action_id in profile.actions}
    for edge in profile.dependencies:
        if edge.kind.value == "ordering":
            graph[_action_graph_address(profile_id, edge.action_ref)].append(
                _action_graph_address(profile_id, edge.depends_on_ref)
            )
    return {action_id: tuple(dependencies) for action_id, dependencies in graph.items()}


def _compile_action(
    scenario: InstantiatedScenario,
    profile_id: str,
    profile: object,
    action_id: str,
) -> CompiledActivityActionModel:
    action = profile.actions[action_id]
    template_id = resolve_section_ref(
        action.template_ref,
        "activity_templates",
        scenario.activity_templates,
    )
    if template_id is None:
        raise ValueError("admitted live activity template must resolve")
    context = profile.execution_contexts[action.execution_context_ref]
    service = _resolve_node_service_ref(scenario, context.target_service_ref)
    if service is None:
        raise ValueError("admitted live activity target service must resolve")
    schedule = profile.schedules[action.schedule_ref]
    template = scenario.activity_templates[template_id]
    ordering_dependencies = sorted(
        edge.depends_on_ref
        for edge in profile.dependencies
        if edge.action_ref == action_id and edge.kind.value == "ordering"
    )
    refresh_dependencies = sorted(
        edge.depends_on_ref
        for edge in profile.dependencies
        if edge.action_ref == action_id and edge.kind.value == "refresh"
    )
    return CompiledActivityActionModel(
        action_id=_canonical_activity_ref(profile_id, "actions", action_id),
        template_id=f"activity_templates.{template_id}",
        execution_context_id=_canonical_activity_ref(
            profile_id,
            "execution_contexts",
            action.execution_context_ref,
        ),
        target_service_id=f"nodes.{service[0]}.services.{service[1]}",
        operation_profile=template.capability.identity,
        schedule_profile=schedule.profile,
        schedule_anchor_seconds=int(schedule.anchor_seconds),
        schedule_interval_seconds=int(schedule.interval_seconds),
        max_occurrences=schedule.finite_occurrence_count(),
        max_retry_attempts=int(action.retry.max_attempts),
        random_stream_profile=profile.randomness.random_stream_profile,
        transform_profile=profile.randomness.transform_profile,
        address_profile=profile.randomness.address_profile,
        readback_profile=profile.readback.profile,
        lifecycle_profile=profile.lifecycle.profile,
        ordering_dependencies=ordering_dependencies,
        refresh_dependencies=refresh_dependencies,
    )


def compile_activity_profiles(
    scenario: InstantiatedScenario,
    baseline_digests: dict[str, HistoricalBaselineDigestModel],
) -> dict[str, CompiledActivityProfileModel]:
    """Compile profile identities and bounds only; never enumerate occurrences."""

    compiled: dict[str, CompiledActivityProfileModel] = {}
    for profile_id in sorted(scenario.activity_profiles):
        profile = scenario.activity_profiles[profile_id]
        baseline_id = resolve_section_ref(
            profile.historical_baseline_ref,
            "historical_baselines",
            scenario.historical_baselines,
        )
        if baseline_id is None:
            raise ValueError("admitted live activity historical baseline must resolve")
        baseline = scenario.historical_baselines[baseline_id]
        tenant_id = resolve_section_ref(
            baseline.deployment_tenant_ref,
            "deployment_tenants",
            scenario.deployment_tenants,
        )
        if tenant_id is None:
            raise ValueError("admitted live activity deployment tenant must resolve")
        baseline_digest = baseline_digests[baseline_id]
        activity_digest = derive_activity_profile_digest(profile_id, profile, baseline_digest)
        graph = _dependency_graph(profile_id, profile)
        order = [address.rsplit(".", 1)[-1] for address in topological_dependency_order(graph)]
        compiled[profile_id] = CompiledActivityProfileModel(
            contract_profile=profile.contract_profile,
            activity_profile_id=profile_id,
            activity_profile_version=profile.version,
            activity_digest=activity_digest,
            baseline_digest=baseline_digest,
            deployment_tenant_id=tenant_id,
            range_instance_id=baseline.range_instance_id,
            reset_generation_id=baseline.reset_generation_id,
            entropy_identity=_entropy_identity(profile),
            actions={
                action_id: _compile_action(scenario, profile_id, profile, action_id)
                for action_id in sorted(profile.actions)
            },
            budget_envelopes=[
                _compile_budget(budget) for budget in sorted(profile.budgets, key=lambda item: item.dimension.value)
            ],
            dependency_order=order,
            reverse_teardown_order=[address.rsplit(".", 1)[-1] for address in reverse_delete_order(graph)],
            required_operation_profiles=sorted(
                {
                    scenario.activity_templates[
                        resolve_section_ref(
                            action.template_ref,
                            "activity_templates",
                            scenario.activity_templates,
                        )
                    ].capability.identity
                    for action in profile.actions.values()
                }
            ),
            required_schedule_profiles=sorted({schedule.profile for schedule in profile.schedules.values()}),
            required_readback_profiles=[profile.readback.profile],
            required_lifecycle_profiles=[profile.lifecycle.profile],
            required_resource_dimensions=sorted({budget.dimension.value for budget in profile.budgets}),
            required_dependency_kinds=sorted({edge.kind.value for edge in profile.dependencies}),
        )
    return compiled


__all__ = ["compile_activity_profiles"]
