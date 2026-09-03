"""Diagnostic-producing reference resolvers and evaluation-contract helpers."""

from collections.abc import Callable
from typing import Any

from raes.nodes import NodeType
from raes.scenario import InstantiatedScenario, Scenario

from ..models import (
    Diagnostic,
    EvaluationExecutionContract,
    EvaluationResultContract,
)
from .addresses import _resource_address_for_node
from .support import _dedupe


def _evaluation_contracts(
    resource_type: str,
) -> tuple[EvaluationResultContract, EvaluationExecutionContract]:
    if resource_type in {
        "condition-binding",
        "objective",
    }:
        return (
            EvaluationResultContract(
                resource_type=resource_type,
                supports_passed=True,
            ),
            EvaluationExecutionContract(resource_type=resource_type),
        )
    return (
        EvaluationResultContract(resource_type=resource_type),
        EvaluationExecutionContract(resource_type=resource_type),
    )


def _resolve_resource_refs(
    resources: dict[str, Any],
    *,
    ref_names: list[str],
    owner_address: str,
    domain: str,
    code_prefix: str,
    resource_label: str,
) -> tuple[tuple[str, ...], list[Diagnostic]]:
    resolved: list[str] = []
    diagnostics: list[Diagnostic] = []
    for ref_name in dict.fromkeys(ref_names):
        matched_addresses = sorted(address for address, resource in resources.items() if resource.name == ref_name)
        if not matched_addresses:
            diagnostics.append(
                Diagnostic(
                    code=f"{code_prefix}-unbound",
                    domain=domain,
                    address=owner_address,
                    message=(f"Reference '{ref_name}' does not resolve to a defined {resource_label}."),
                )
            )
            continue
        if len(matched_addresses) > 1:
            diagnostics.append(
                Diagnostic(
                    code=f"{code_prefix}-ambiguous",
                    domain=domain,
                    address=owner_address,
                    message=(
                        f"Reference '{ref_name}' resolves to multiple {resource_label}s: "
                        f"{', '.join(matched_addresses)}."
                    ),
                )
            )
            continue
        resolved.append(matched_addresses[0])
    return _dedupe(resolved), diagnostics


def _resolve_named_refs(
    *,
    ref_names: list[str],
    available_names: set[str],
    address_builder: Callable[[str], str],
    owner_address: str,
    domain: str,
    code_prefix: str,
    resource_label: str,
) -> tuple[tuple[str, ...], list[Diagnostic]]:
    resolved: list[str] = []
    diagnostics: list[Diagnostic] = []
    for ref_name in dict.fromkeys(ref_names):
        if ref_name not in available_names:
            diagnostics.append(
                Diagnostic(
                    code=f"{code_prefix}-unbound",
                    domain=domain,
                    address=owner_address,
                    message=(f"Reference '{ref_name}' does not resolve to a defined {resource_label}."),
                )
            )
            continue
        resolved.append(address_builder(ref_name))
    return _dedupe(resolved), diagnostics


def _resolve_node_ref(
    scenario: Scenario,
    *,
    ref_name: str,
    owner_address: str,
    domain: str,
    code_prefix: str,
    node_label: str,
    required_type: NodeType | None = None,
) -> tuple[str | None, list[Diagnostic]]:
    node = scenario.nodes.get(ref_name)
    if node is None:
        code = f"{code_prefix}-unbound"
        message = f"Reference '{ref_name}' does not resolve to a defined {node_label}."
    elif required_type is not None and node.type != required_type:
        expected = "a compute node" if required_type == NodeType.COMPUTE else "a switch/network node"
        code = f"{code_prefix}-invalid-type"
        message = f"Reference '{ref_name}' must resolve to {expected} for {node_label}."
    else:
        return _resource_address_for_node(scenario, ref_name), []
    return None, [Diagnostic(code=code, domain=domain, address=owner_address, message=message)]


def _node_dependency_addresses(
    scenario: InstantiatedScenario,
    *,
    node_name: str,
    ref_names: list[str],
    code_prefix: str,
    node_label: str,
    diagnostics: list[Diagnostic],
    require_switch: bool = False,
) -> list[str]:
    addresses: list[str] = []
    for ref_name in ref_names:
        dep_address, dep_diagnostics = _resolve_node_ref(
            scenario,
            ref_name=ref_name,
            owner_address=_resource_address_for_node(scenario, node_name),
            domain="provisioning",
            code_prefix=code_prefix,
            node_label=node_label,
            required_type=NodeType.SWITCH if require_switch else None,
        )
        diagnostics.extend(dep_diagnostics)
        if dep_address is not None:
            addresses.append(dep_address)
    return addresses
