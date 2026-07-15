"""Participant action contracts, observation boundaries, outcome-interpretation rules."""

from aces_sdl.participant_outcome_semantics import (
    OutcomeInterpretationSourceLayer,
    OutcomeInterpretationTargetLayer,
)
from aces_sdl.scenario import InstantiatedScenario

from ..models import (
    ParticipantActionContractRuntime,
    ParticipantObservationBoundaryRuntime,
    ParticipantOutcomeInterpretationRuleRuntime,
)
from .addresses import (
    _action_contract_address,
    _evaluation_address,
    _objective_address,
    _observation_boundary_address,
    _outcome_interpretation_rule_address,
    _workflow_address,
)
from .support import _dedupe, _dump
from .view_relations import (
    _compile_view_relation_timeline,
    _initial_view_relation,
    _ordered_view_transitions,
    _view_relation_refs,
)


def _compile_action_contracts(scenario: InstantiatedScenario) -> dict[str, ParticipantActionContractRuntime]:
    action_contracts: dict[str, ParticipantActionContractRuntime] = {}
    for name, contract in scenario.action_contracts.items():
        contract_spec = _dump(contract)
        interactions = contract_spec.get("interactions", [])
        temporal_contracts = contract_spec.get("temporal_contracts", [])
        interaction_classes = _dedupe(
            [
                str(interaction.get("interaction_class", ""))
                for interaction in interactions
                if isinstance(interaction, dict) and interaction.get("interaction_class")
            ]
        )
        shared_state_refs = _dedupe(
            [
                str(ref)
                for interaction in interactions
                if isinstance(interaction, dict)
                for ref in interaction.get("shared_state_refs", [])
            ]
        )
        precondition_classes = _dedupe(
            [
                str(precondition.get("precondition_class", ""))
                for precondition in contract_spec.get("preconditions", [])
                if isinstance(precondition, dict) and precondition.get("precondition_class")
            ]
        )
        effect_classes = _dedupe(
            [
                str(effect.get("effect_class", ""))
                for effect in contract_spec.get("effects", [])
                if isinstance(effect, dict) and effect.get("effect_class")
            ]
        )
        failure_classes = _dedupe(str(failure_class) for failure_class in contract_spec.get("failure_classes", []))
        backend_failure_mappings = tuple(
            {
                "backend_error_code": str(mapping.get("backend_error_code", "")),
                "failure_class": str(mapping.get("failure_class", "")),
                "diagnostic": str(mapping.get("diagnostic", "")),
            }
            for mapping in contract_spec.get("backend_failure_mappings", [])
            if isinstance(mapping, dict)
        )
        temporal_contract_ids = _dedupe(
            [
                str(temporal_contract.get("temporal_id", ""))
                for temporal_contract in temporal_contracts
                if isinstance(temporal_contract, dict) and temporal_contract.get("temporal_id")
            ]
        )
        temporal_kinds = _dedupe(
            [
                str(temporal_contract.get("temporal_kind", ""))
                for temporal_contract in temporal_contracts
                if isinstance(temporal_contract, dict) and temporal_contract.get("temporal_kind")
            ]
        )
        time_domains = _dedupe(
            [
                str(temporal_contract.get("time_domain", ""))
                for temporal_contract in temporal_contracts
                if isinstance(temporal_contract, dict) and temporal_contract.get("time_domain")
            ]
        )
        clock_authorities = _dedupe(
            [
                str(temporal_contract.get("clock_authority", ""))
                for temporal_contract in temporal_contracts
                if isinstance(temporal_contract, dict) and temporal_contract.get("clock_authority")
            ]
        )
        backend_timing_disclosures = tuple(
            {
                "disclosure_id": str(disclosure.get("disclosure_id", "")),
                "disclosure_kind": str(disclosure.get("disclosure_kind", "")),
                "support_mode": str(disclosure.get("support_mode", "")),
                "description": str(disclosure.get("description", "")),
                "affected_temporal_ids": [
                    str(temporal_id) for temporal_id in disclosure.get("affected_temporal_ids", [])
                ],
                "limitations": [str(limitation) for limitation in disclosure.get("limitations", [])],
            }
            for disclosure in contract_spec.get("backend_timing_disclosures", [])
            if isinstance(disclosure, dict)
        )
        action_contracts[_action_contract_address(name)] = ParticipantActionContractRuntime(
            address=_action_contract_address(name),
            name=name,
            action_name=name,
            semantic_version=str(contract_spec.get("semantic_version", "")),
            lifecycle_state=str(contract_spec.get("lifecycle_state", "")),
            behavioral_granularity=str(contract_spec.get("behavioral_granularity", "")),
            precondition_classes=precondition_classes,
            effect_classes=effect_classes,
            failure_classes=failure_classes,
            backend_failure_mappings=backend_failure_mappings,
            interaction_classes=interaction_classes,
            shared_state_refs=shared_state_refs,
            temporal_contract_ids=temporal_contract_ids,
            temporal_kinds=temporal_kinds,
            time_domains=time_domains,
            clock_authorities=clock_authorities,
            backend_timing_disclosures=backend_timing_disclosures,
            spec=contract_spec,
        )
    return action_contracts


def _compile_observation_boundaries(scenario: InstantiatedScenario) -> dict[str, ParticipantObservationBoundaryRuntime]:
    observation_boundaries: dict[str, ParticipantObservationBoundaryRuntime] = {}
    for name, boundary in scenario.observation_boundaries.items():
        boundary_spec = _dump(boundary)
        view_rules = boundary_spec.get("view_rules", [])
        view_transitions = boundary_spec.get("view_transitions", [])
        initial_view_relation = _initial_view_relation(view_rules=view_rules)
        disclosed_refs = _view_relation_refs(initial_view_relation, {"disclosed"})
        evidence_only_refs = _view_relation_refs(initial_view_relation, {"evidence_only"})
        discovered_refs = _view_relation_refs(initial_view_relation, {"discovered"})
        inferred_refs = _view_relation_refs(initial_view_relation, {"inferred"})
        concealed_refs = _view_relation_refs(initial_view_relation, {"concealed"})
        deceptive_refs = _view_relation_refs(initial_view_relation, {"deceptive"})
        view_relation_timeline = _compile_view_relation_timeline(
            view_rules=view_rules,
            view_transitions=view_transitions,
        )
        ordered_view_transitions = _ordered_view_transitions(view_transitions)
        observation_boundaries[_observation_boundary_address(name)] = ParticipantObservationBoundaryRuntime(
            address=_observation_boundary_address(name),
            name=name,
            boundary_name=name,
            projection_basis=str(boundary_spec.get("projection_basis", "")),
            hidden_refs=tuple(str(ref) for ref in boundary_spec.get("hidden_refs", [])),
            observable_refs=tuple(str(ref) for ref in boundary_spec.get("observable_refs", [])),
            evidence_refs=tuple(str(ref) for ref in boundary_spec.get("evidence_refs", [])),
            disclosed_refs=disclosed_refs,
            evidence_only_refs=evidence_only_refs,
            discovered_refs=discovered_refs,
            inferred_refs=inferred_refs,
            concealed_refs=concealed_refs,
            deceptive_refs=deceptive_refs,
            view_transitions=ordered_view_transitions,
            view_relation_timeline=view_relation_timeline,
            realized_view_disclosure=str(boundary_spec.get("realized_view_disclosure") or ""),
            spec=boundary_spec,
        )
    return observation_boundaries


def _outcome_source_ref_address(source_layer: str, ref: str) -> str:
    if source_layer == OutcomeInterpretationSourceLayer.PARTICIPANT_ACTION_OUTCOME.value:
        return _action_contract_address(ref)
    if source_layer == OutcomeInterpretationSourceLayer.OBJECTIVE_RESULT.value:
        return _objective_address(ref)
    if source_layer == OutcomeInterpretationSourceLayer.WORKFLOW_RESULT.value:
        return _workflow_address(ref)
    if source_layer == OutcomeInterpretationSourceLayer.EVALUATION_RESULT.value:
        return _evaluation_address(ref)
    return ref


def _outcome_target_ref_address(target_layer: str, ref: str) -> str:
    if target_layer == OutcomeInterpretationTargetLayer.OBJECTIVE_RESULT.value:
        return _objective_address(ref)
    if target_layer == OutcomeInterpretationTargetLayer.WORKFLOW_RESULT.value:
        return _workflow_address(ref)
    if target_layer == OutcomeInterpretationTargetLayer.EVALUATION_RESULT.value:
        return _evaluation_address(ref)
    return ref


def _compile_outcome_interpretation_rules(
    scenario: InstantiatedScenario,
) -> dict[str, ParticipantOutcomeInterpretationRuleRuntime]:
    rules: dict[str, ParticipantOutcomeInterpretationRuleRuntime] = {}
    for name, rule in scenario.outcome_interpretation_rules.items():
        rule_spec = _dump(rule)
        sources = tuple(source for source in rule_spec.get("source_bindings", ()) if isinstance(source, dict))
        targets = tuple(target for target in rule_spec.get("target_bindings", ()) if isinstance(target, dict))
        source_layers = tuple(str(source.get("source_layer", "")) for source in sources)
        target_layers = tuple(str(target.get("target_layer", "")) for target in targets)
        source_refs = tuple(
            _outcome_source_ref_address(str(source.get("source_layer", "")), str(source.get("ref", "")))
            for source in sources
        )
        target_refs = tuple(
            _outcome_target_ref_address(str(target.get("target_layer", "")), str(target.get("ref", "")))
            for target in targets
        )
        address = _outcome_interpretation_rule_address(name)
        rules[address] = ParticipantOutcomeInterpretationRuleRuntime(
            address=address,
            name=name,
            rule_name=name,
            semantic_version=str(rule_spec.get("semantic_version", "")),
            participant_scope=str(rule_spec.get("participant_scope", "")),
            observation_point_basis=str(rule_spec.get("observation_point_basis", "")),
            interpretation_basis=str(rule_spec.get("interpretation_basis", "")),
            source_layers=source_layers,
            source_refs=source_refs,
            target_layers=target_layers,
            target_refs=target_refs,
            evidence_refs=tuple(str(ref) for ref in rule_spec.get("evidence_refs", ())),
            limitations=tuple(str(item) for item in rule_spec.get("limitations", ())),
            spec=rule_spec,
        )
    return rules
