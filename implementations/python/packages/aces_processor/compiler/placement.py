"""Content and account placement compilation."""

from aces_sdl.nodes import NodeType
from aces_sdl.scenario import InstantiatedScenario
from aces_sdl.semantics.domain_topology import (
    DomainTopologyAnalysis,
)

from ..models import (
    AccountPlacement,
    ContentPlacement,
    Diagnostic,
)
from .addresses import _account_address, _compiled_domain_binding, _content_address
from .ref_resolution import _resolve_node_ref
from .support import _dump


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
) -> dict[str, AccountPlacement]:
    account_placements: dict[str, AccountPlacement] = {}
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
        account_placements[address] = AccountPlacement(
            address=address,
            name=name,
            account_name=name,
            node_name=account.node,
            target_address=target_address,
            domain_topology=(
                _compiled_domain_binding(scenario, node_domain_binding) if node_domain_binding is not None else None
            ),
            ordering_dependencies=(target_address,),
            refresh_dependencies=(target_address,),
            spec=_dump(account),
        )
    return account_placements
