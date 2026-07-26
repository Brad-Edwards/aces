"""Compilation of autonomous participant execution policies."""

from raes.scenario import InstantiatedScenario

from ..models import (
    ParticipantAutonomousExecutionRuntime,
    ParticipantExecutionBindingRuntime,
)
from .addresses import (
    _action_contract_address,
    _behavior_specification_address,
    _objective_address,
    _observation_boundary_address,
    _section_ref_name,
)
from .alias_index import _runtime_addressable_ref_index, _runtime_addresses_for_refs
from .support import _address, _dump


def _compile_autonomous_execution(
    *,
    scenario: InstantiatedScenario,
    spec_name: str,
    participant_addresses: tuple[str, ...],
    behavior_spec: object,
) -> ParticipantAutonomousExecutionRuntime | None:
    policy = behavior_spec.autonomous_execution
    if policy is None:
        return None
    address = _address("participant", "autonomous-execution", spec_name)
    authority = policy.evaluation_authority
    profile = getattr(policy, "profile", "participant-autonomous-execution/v1")
    activity_candidates = getattr(policy, "action_candidates", None)
    ordered_candidates = sorted(activity_candidates.items()) if activity_candidates is not None else []
    action_refs = (
        [candidate.action_ref for _, candidate in ordered_candidates]
        if ordered_candidates
        else list(policy.action_order)
    )
    work_window_refs = list(getattr(policy, "work_window_refs", ()))
    pause_window_refs = list(getattr(policy, "pause_window_refs", ()))
    temporal_constraint_refs = (
        [*work_window_refs, *pause_window_refs]
        if profile == "participant-autonomous-execution/v2"
        else list(policy.temporal_constraint_refs)
    )
    addressable_ref_index = _runtime_addressable_ref_index(scenario)
    execution_bindings_by_key: dict[tuple[str, tuple[str, ...]], ParticipantExecutionBindingRuntime] = {}
    for action_ref in action_refs:
        action_name = _section_ref_name(
            action_ref,
            "action_contracts",
            scenario.action_contracts,
        )
        action = scenario.action_contracts[action_name]
        target_refs = [
            *(str(ref) for effect in action.effects for ref in effect.target_refs),
            *(str(ref) for precondition in action.preconditions for ref in precondition.support_refs),
        ]
        action_contract_address = _action_contract_address(action_name)
        target_addresses = _runtime_addresses_for_refs(
            list(dict.fromkeys(target_refs)),
            addressable_ref_index=addressable_ref_index,
        )
        execution_bindings_by_key.setdefault(
            (action_contract_address, target_addresses),
            ParticipantExecutionBindingRuntime(
                action_contract_address=action_contract_address,
                target_addresses=target_addresses,
                participant_implementation_ref=policy.participant_implementation_ref,
                max_action_attempts=policy.max_action_attempts,
                max_in_flight=policy.max_in_flight,
            ),
        )
    execution_bindings = tuple(execution_bindings_by_key.values())
    target_addresses = tuple(
        dict.fromkeys(target for binding in execution_bindings for target in binding.target_addresses)
    )
    return ParticipantAutonomousExecutionRuntime(
        address=address,
        name=spec_name,
        behavior_specification_address=_behavior_specification_address(spec_name),
        participant_addresses=participant_addresses,
        participant_implementation_ref=policy.participant_implementation_ref,
        clock_address=_address("time", "clock", _section_ref_name(policy.clock_ref, "clocks", scenario.clocks)),
        progression_policy_address=_address(
            "time",
            "policy",
            _section_ref_name(
                policy.progression_policy_ref,
                "time_progression_policies",
                scenario.time_progression_policies,
            ),
        ),
        temporal_constraint_addresses=tuple(
            _address(
                "time",
                "constraint",
                _section_ref_name(ref, "temporal_constraints", scenario.temporal_constraints),
            )
            for ref in temporal_constraint_refs
        ),
        action_contract_addresses=tuple(
            _action_contract_address(_section_ref_name(ref, "action_contracts", scenario.action_contracts))
            for ref in action_refs
        ),
        target_addresses=target_addresses,
        execution_bindings=execution_bindings,
        observation_boundary_address=_observation_boundary_address(
            _section_ref_name(
                policy.observation_boundary_ref,
                "observation_boundaries",
                scenario.observation_boundaries,
            )
        ),
        selection_strategy=policy.selection_strategy,
        max_action_attempts=policy.max_action_attempts,
        max_in_flight=policy.max_in_flight,
        failure_policy=policy.failure_policy.value,
        evaluation_authority_mode=authority.mode.value,
        objective_refs=tuple(
            _objective_address(_section_ref_name(ref, "objectives", scenario.objectives))
            for ref in authority.objective_refs
        ),
        proof_producer_refs=tuple(authority.proof_producer_refs),
        score_authority_refs=tuple(authority.score_authority_refs),
        receipt_authority_refs=tuple(authority.receipt_authority_refs),
        profile=profile,
        work_window_addresses=tuple(
            _address(
                "time",
                "constraint",
                _section_ref_name(ref, "temporal_constraints", scenario.temporal_constraints),
            )
            for ref in work_window_refs
        ),
        pause_window_addresses=tuple(
            _address(
                "time",
                "constraint",
                _section_ref_name(ref, "temporal_constraints", scenario.temporal_constraints),
            )
            for ref in pause_window_refs
        ),
        stochastic_control_ref=str(getattr(policy, "stochastic_control_ref", "")),
        timing_minimum_ticks=int(getattr(getattr(policy, "timing", None), "minimum_ticks", 0)),
        timing_maximum_ticks=int(getattr(getattr(policy, "timing", None), "maximum_ticks", 0)),
        outside_window_disposition=str(getattr(policy, "outside_window_disposition", "")),
        empty_eligible_disposition=str(getattr(policy, "empty_eligible_disposition", "")),
        action_candidate_ids=tuple(str(candidate_id) for candidate_id, _ in ordered_candidates),
        action_candidate_weights=tuple(candidate.weight for _, candidate in ordered_candidates),
        action_candidate_dependencies=tuple(
            tuple(str(ref) for ref in candidate.depends_on) for _, candidate in ordered_candidates
        ),
        action_candidate_retry_failure_classes=tuple(
            tuple(value.value for value in candidate.retryable_failure_classes) for _, candidate in ordered_candidates
        ),
        action_candidate_max_retries=tuple(candidate.max_retries for _, candidate in ordered_candidates),
        action_candidate_cooldown_ticks=tuple(candidate.cooldown_ticks for _, candidate in ordered_candidates),
        max_occurrences=int(getattr(policy, "max_occurrences", 0)),
        max_burst_size=int(getattr(policy, "max_burst_size", 1)),
        refresh_dependencies=(
            *participant_addresses,
            *tuple(
                _action_contract_address(_section_ref_name(ref, "action_contracts", scenario.action_contracts))
                for ref in action_refs
            ),
            *tuple(
                _objective_address(_section_ref_name(ref, "objectives", scenario.objectives))
                for ref in authority.objective_refs
            ),
            *target_addresses,
        ),
        spec=_dump(policy),
    )


__all__ = ["_compile_autonomous_execution"]
