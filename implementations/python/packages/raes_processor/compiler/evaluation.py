"""Evaluation-domain compilation: propositions, assertions, condition bindings."""

from raes.nodes import NodeType
from raes.scenario import InstantiatedScenario

from ..models import (
    AssertionRuntime,
    ConditionBinding,
    Diagnostic,
    PropositionRuntime,
    RuntimeTemplate,
)
from .addresses import _assertion_address, _condition_binding_address, _node_address, _proposition_address
from .alias_index import _runtime_addressable_ref_index, _runtime_addresses_for_refs
from .ref_resolution import _evaluation_contracts
from .support import _dedupe, _dump

_OBSERVED_PROPOSITION_TIME_DOMAIN = "scenario_time"


def _evidence_capability_projection(
    scenario: InstantiatedScenario,
    evidence_requirement_refs: list[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Project channel kinds without treating opaque channel refs as kinds."""

    channels: set[str] = set()
    unresolved: list[str] = []
    for ref in evidence_requirement_refs:
        requirement = scenario.evidence_requirements[ref]
        channel = requirement.channel
        if channel is None:
            unresolved.append(ref)
            continue
        channels.add(str(getattr(channel, "value", channel)))
    return tuple(sorted(channels)), tuple(unresolved)


def _compile_propositions(
    scenario: InstantiatedScenario,
) -> dict[str, PropositionRuntime]:
    address_index = _runtime_addressable_ref_index(scenario)
    propositions: dict[str, PropositionRuntime] = {}
    for name, proposition in scenario.propositions.items():
        channels, unresolved_channels = _evidence_capability_projection(
            scenario,
            proposition.evidence_requirements,
        )
        address = _proposition_address(name)
        propositions[address] = PropositionRuntime(
            address=address,
            name=name,
            spec=_dump(proposition),
            subject_addresses=_runtime_addresses_for_refs(
                list(proposition.subjects),
                addressable_ref_index=address_index,
            ),
            predicate_kind=proposition.predicate.kind,
            quantifier=proposition.quantifier.value,
            evaluation_basis=proposition.basis.value,
            evidence_requirement_refs=tuple(proposition.evidence_requirements),
            evidence_channels=channels,
            unresolved_evidence_channel_refs=unresolved_channels,
            required_time_domain=(
                _OBSERVED_PROPOSITION_TIME_DOMAIN if proposition.basis.value == "observed_state" else ""
            ),
        )
    return propositions


def _compile_assertions(
    scenario: InstantiatedScenario,
) -> dict[str, AssertionRuntime]:
    return {
        _assertion_address(name): AssertionRuntime(
            address=_assertion_address(name),
            name=name,
            spec=_dump(assertion),
            proposition_address=_proposition_address(assertion.proposition),
            role=assertion.role.value,
            polarity=assertion.polarity.value,
            ordering_dependencies=(_proposition_address(assertion.proposition),),
            refresh_dependencies=(_proposition_address(assertion.proposition),),
        )
        for name, assertion in scenario.assertions.items()
    }


def _compile_condition_bindings(
    scenario: InstantiatedScenario,
    condition_templates: dict[str, RuntimeTemplate],
    propositions: dict[str, PropositionRuntime],
    diagnostics: list[Diagnostic],
) -> dict[str, ConditionBinding]:
    condition_bindings: dict[str, ConditionBinding] = {}
    for node_name, node in scenario.nodes.items():
        if node.type != NodeType.COMPUTE:
            continue
        node_addr = _node_address(node_name)
        for condition_name, role_name in node.conditions.items():
            template = condition_templates.get(condition_name)
            if template is None:
                diagnostics.append(
                    Diagnostic(
                        code="evaluation.condition-template-ref-unbound",
                        domain="evaluation",
                        address=node_addr,
                        message=(
                            f"Condition binding '{condition_name}' on node '{node_name}' "
                            "does not resolve to a declared condition template."
                        ),
                    )
                )
                continue
            address = _condition_binding_address(node_name, condition_name)
            proposition_address = (
                _proposition_address(template.spec["proposition"]) if template.spec.get("proposition") else ""
            )
            proposition_dependencies = (proposition_address,) if proposition_address in propositions else ()
            result_contract, execution_contract = _evaluation_contracts("condition-binding")
            condition_bindings[address] = ConditionBinding(
                address=address,
                name=condition_name,
                node_name=node_name,
                node_address=node_addr,
                condition_name=condition_name,
                template_address=template.address,
                role_name=role_name,
                proposition_address=proposition_address,
                ordering_dependencies=proposition_dependencies,
                refresh_dependencies=_dedupe([node_addr, *proposition_dependencies]),
                spec={"binding": {"node": node_name, "role": role_name}, "template": template.spec},
                result_contract=result_contract,
                execution_contract=execution_contract,
            )
    return condition_bindings
