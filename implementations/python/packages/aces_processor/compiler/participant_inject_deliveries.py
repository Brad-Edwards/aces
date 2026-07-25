"""Participant-directed inject delivery compilation (DSL-142)."""

from raes.scenario import InstantiatedScenario

from ..models import ParticipantInjectDeliveryRuntime
from .addresses import (
    _behavior_specification_address,
    _observation_boundary_address,
    _participant_behavior_address,
    _participant_inject_delivery_address,
    _section_ref_name,
)
from .alias_index import _runtime_addressable_ref_index, _runtime_addresses_for_refs
from .support import _address, _dedupe, _dump


def _compile_participant_inject_deliveries(
    scenario: InstantiatedScenario,
) -> dict[str, ParticipantInjectDeliveryRuntime]:
    """Compile admitted delivery declarations as participant metadata."""

    deliveries: dict[str, ParticipantInjectDeliveryRuntime] = {}
    addressable_ref_index = _runtime_addressable_ref_index(scenario)
    for spec_name, behavior_spec in scenario.behavior_specifications.items():
        owner_address = _behavior_specification_address(spec_name)
        for binding_id, binding in sorted(behavior_spec.participant_inject_deliveries.items()):
            address = _participant_inject_delivery_address(spec_name, binding_id)
            participant_name = _section_ref_name(binding.participant_ref, "agents", scenario.agents)
            inject_name = _section_ref_name(binding.inject_ref, "injects", scenario.injects)
            event_name = _section_ref_name(binding.occurrence.event_ref, "events", scenario.events)
            script_name = _section_ref_name(binding.occurrence.script_ref, "scripts", scenario.scripts)
            story_name = _section_ref_name(binding.occurrence.story_ref, "stories", scenario.stories)
            boundary_name = _section_ref_name(
                binding.observation_boundary_ref,
                "observation_boundaries",
                scenario.observation_boundaries,
            )
            source_item_address = _runtime_addresses_for_refs(
                [binding.source_item_ref],
                addressable_ref_index=addressable_ref_index,
            )[0]
            result_item_address = _runtime_addresses_for_refs(
                [binding.result_item_ref],
                addressable_ref_index=addressable_ref_index,
            )[0]
            temporal_addresses = tuple(
                _address(
                    "time",
                    "constraint",
                    _section_ref_name(ref, "temporal_constraints", scenario.temporal_constraints),
                )
                for ref in binding.temporal_constraint_refs
            )
            evidence_addresses = tuple(
                _address(
                    "sdl",
                    "evidence-requirements",
                    _section_ref_name(ref, "evidence_requirements", scenario.evidence_requirements),
                )
                for ref in binding.evidence_requirement_refs
            )
            control_transition_address = ""
            controller_address = ""
            control_authority_scope_addresses: tuple[str, ...] = ()
            control_evidence_addresses: tuple[str, ...] = ()
            if binding.control_transition_ref is not None:
                control_transition_address = _address(
                    "participant",
                    "behavior-specification",
                    spec_name,
                    "control-transition",
                    binding.control_transition_ref,
                )
                controller_name = (
                    participant_name
                    if binding.controller_ref == "self"
                    else _section_ref_name(binding.controller_ref, "agents", scenario.agents)
                )
                controller_address = _participant_behavior_address(controller_name)
                control_authority_scope_addresses = _runtime_addresses_for_refs(
                    binding.control_authority_scope_refs,
                    addressable_ref_index=addressable_ref_index,
                )
                control_evidence_addresses = _runtime_addresses_for_refs(
                    binding.control_evidence_refs,
                    addressable_ref_index=addressable_ref_index,
                )
            inject_address = _address("orchestration", "inject", inject_name)
            event_address = _address("orchestration", "event", event_name)
            script_address = _address("orchestration", "script", script_name)
            story_address = _address("orchestration", "story", story_name)
            participant_address = _participant_behavior_address(participant_name)
            observation_boundary_address = _observation_boundary_address(boundary_name)
            dependencies = _dedupe(
                [
                    owner_address,
                    participant_address,
                    inject_address,
                    event_address,
                    script_address,
                    story_address,
                    source_item_address,
                    result_item_address,
                    observation_boundary_address,
                    *temporal_addresses,
                    *evidence_addresses,
                    *([control_transition_address] if control_transition_address else []),
                    *([controller_address] if controller_address else []),
                    *control_authority_scope_addresses,
                    *control_evidence_addresses,
                ]
            )
            policy = binding.delivery_policy
            deliveries[address] = ParticipantInjectDeliveryRuntime(
                address=address,
                name=binding_id,
                binding_id=binding_id,
                behavior_specification_address=owner_address,
                participant_address=participant_address,
                inject_address=inject_address,
                event_address=event_address,
                script_address=script_address,
                story_address=story_address,
                source_item_ref=binding.source_item_ref,
                source_item_address=source_item_address,
                result_item_ref=binding.result_item_ref,
                result_item_address=result_item_address,
                observation_boundary_address=observation_boundary_address,
                delivery_kind=binding.delivery_kind.value,
                policy_ref=policy.policy_ref,
                policy_revision=policy.policy_revision,
                exposure_policy_ref=policy.exposure_policy_ref,
                audience_scope_ref=policy.audience_scope_ref,
                visibility_basis_ref=policy.visibility_basis_ref,
                disclosure_basis_ref=policy.disclosure_basis_ref,
                order_basis=binding.order_basis.value,
                temporal_constraint_addresses=temporal_addresses,
                evidence_requirement_addresses=evidence_addresses,
                failure_disposition=binding.failure_disposition.value,
                control_transition_address=control_transition_address,
                controller_address=controller_address,
                control_authority_scope_refs=tuple(binding.control_authority_scope_refs),
                control_authority_scope_addresses=control_authority_scope_addresses,
                control_effective_order=binding.control_effective_order,
                control_valid_from_order=binding.control_valid_from_order,
                control_valid_until_order=binding.control_valid_until_order,
                control_evidence_refs=tuple(binding.control_evidence_refs),
                control_evidence_addresses=control_evidence_addresses,
                ordering_dependencies=(inject_address, event_address, script_address, story_address),
                refresh_dependencies=dependencies,
                spec=_dump(binding),
            )
    return deliveries
