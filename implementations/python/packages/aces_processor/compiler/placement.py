"""Content and account placement compilation."""

from aces_sdl.nodes import NodeType
from aces_sdl.scenario import InstantiatedScenario
from aces_sdl.semantics.domain_topology import (
    DomainNodeRole,
    DomainTopologyAnalysis,
)

from ..models import (
    AccountPlacement,
    ContentPlacement,
    Diagnostic,
    DomainControllerPlacement,
)
from .addresses import (
    _account_address,
    _compiled_domain_binding,
    _content_address,
    _domain_controller_address,
    _node_address,
)
from .ref_resolution import _resolve_node_ref
from .support import _dedupe, _dump


def _compile_content_placements(
    scenario: InstantiatedScenario,
    diagnostics: list[Diagnostic],
) -> dict[str, ContentPlacement]:
    content_placements: dict[str, ContentPlacement] = {}
    for name, content in scenario.content.items():
        address = _content_address(name)
        target_address, target_diagnostics = _resolve_node_ref(
            scenario,
            ref_name=content.target,
            owner_address=address,
            domain="provisioning",
            code_prefix="provisioning.content-target-ref",
            node_label="content target",
            required_type=NodeType.VM,
        )
        diagnostics.extend(target_diagnostics)
        if target_address is None:
            continue
        content_placements[address] = ContentPlacement(
            address=address,
            name=name,
            content_name=name,
            target_node=content.target,
            target_address=target_address,
            ordering_dependencies=(target_address,),
            refresh_dependencies=(target_address,),
            spec=_dump(content),
        )
    return content_placements


def _compile_account_placements(
    scenario: InstantiatedScenario,
    diagnostics: list[Diagnostic],
    domain_analysis: DomainTopologyAnalysis,
    domain_controller_placements: dict[str, DomainControllerPlacement],
) -> dict[str, AccountPlacement]:
    account_placements: dict[str, AccountPlacement] = {}
    controller_placements_by_domain: dict[str, list[str]] = {}
    for placement in domain_controller_placements.values():
        controller_placements_by_domain.setdefault(placement.domain_topology.domain_id, []).append(placement.address)
    for name, account in scenario.accounts.items():
        address = _account_address(name)
        target_address, target_diagnostics = _resolve_node_ref(
            scenario,
            ref_name=account.node,
            owner_address=address,
            domain="provisioning",
            code_prefix="provisioning.account-node-ref",
            node_label="account node",
            required_type=NodeType.VM,
        )
        diagnostics.extend(target_diagnostics)
        if target_address is None:
            continue
        account_domain_binding = domain_analysis.account_bindings.get(name)
        node_domain_binding = (
            domain_analysis.node_bindings.get(account_domain_binding.node_name)
            if account_domain_binding is not None
            else None
        )
        domain_topology = (
            _compiled_domain_binding(scenario, node_domain_binding) if node_domain_binding is not None else None
        )
        dependencies = _dedupe(
            [
                target_address,
                *(
                    controller_placements_by_domain.get(domain_topology.domain_id, ())
                    if domain_topology is not None
                    else ()
                ),
            ]
        )
        account_placements[address] = AccountPlacement(
            address=address,
            name=name,
            account_name=name,
            node_name=account.node,
            target_address=target_address,
            domain_topology=domain_topology,
            ordering_dependencies=dependencies,
            refresh_dependencies=dependencies,
            spec=_dump(account),
        )
    return account_placements


def _compile_domain_controller_placements(
    scenario: InstantiatedScenario,
    domain_analysis: DomainTopologyAnalysis,
) -> dict[str, DomainControllerPlacement]:
    placements: dict[str, DomainControllerPlacement] = {}
    for controller_node_name, binding in domain_analysis.node_bindings.items():
        if binding.role is not DomainNodeRole.CONTROLLER:
            continue
        address = _domain_controller_address(controller_node_name, binding.domain_name)
        target_address = _node_address(controller_node_name)
        placements[address] = DomainControllerPlacement(
            address=address,
            name=f"{controller_node_name}.{binding.domain_name}",
            target_address=target_address,
            domain_topology=_compiled_domain_binding(scenario, binding),
            ordering_dependencies=(target_address,),
            refresh_dependencies=(target_address,),
            spec={},
        )
    return placements
