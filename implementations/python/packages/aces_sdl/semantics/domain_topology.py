"""Pure authored identity-domain topology analysis.

The analyzer owns the name-level invariants for controller roles, member joins,
and domain-bound accounts.  It deliberately describes authored realization
intent and does not inspect observed runtime identity inventory.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum

from ..identity_domains import IdentityDomainProfile
from ..nodes import NodeType
from ..relationships import RelationshipType


class DomainNodeRole(str, Enum):
    """A node's authored role within an identity domain."""

    CONTROLLER = "controller"
    MEMBER = "member"


@dataclass(frozen=True)
class DomainTopologyIssue:
    """Machine-readable authored-topology consistency issue."""

    code: str
    message: str


@dataclass(frozen=True)
class DomainNodeBinding:
    """Normalized name-level binding for one domain-participating node."""

    node_name: str
    domain_name: str
    role: DomainNodeRole
    controller_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class DomainAccountBinding:
    """Normalized name-level binding for one domain-scoped account."""

    account_name: str
    node_name: str
    domain_name: str


@dataclass(frozen=True)
class DomainTopologyAnalysis:
    """Normalized topology facts and fail-closed authoring issues."""

    node_bindings: Mapping[str, DomainNodeBinding] = field(default_factory=dict)
    account_bindings: Mapping[str, DomainAccountBinding] = field(default_factory=dict)
    controllers_by_domain: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    issues: tuple[DomainTopologyIssue, ...] = ()

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)


def _resolve_section_ref(ref: object, section: str, declarations: Mapping[str, object]) -> str | None:
    if not isinstance(ref, str):
        return None
    if ref in declarations:
        return ref
    prefix = f"{section}."
    qualified = ref[len(prefix) :] if ref.startswith(prefix) else ""
    return qualified if qualified in declarations else None


def _relationship_type(value: object) -> str:
    return value.value if isinstance(value, RelationshipType) else str(value)


def _domain_profile(value: object) -> str:
    return value.value if isinstance(value, IdentityDomainProfile) else str(value)


def _issue(code: str, message: str) -> DomainTopologyIssue:
    return DomainTopologyIssue(code=code, message=message)


_RELATIONSHIP_DETAIL_MISMATCH = "domain.relationship.detail-mismatch"


@dataclass(frozen=True)
class _TopologyRelationship:
    name: str
    type_value: str
    label: str
    node_name: str
    domain_name: str


@dataclass
class _TopologyFacts:
    issues: list[DomainTopologyIssue] = field(default_factory=list)
    controller_edges: defaultdict[str, list[tuple[str, str]]] = field(default_factory=lambda: defaultdict(list))
    join_edges: defaultdict[str, list[tuple[str, str, tuple[str, ...]]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    controller_pairs: set[tuple[str, str]] = field(default_factory=set)
    join_pairs: set[tuple[str, str]] = field(default_factory=set)


def _controller_detail_issues(
    label: str,
    controller_detail: object,
    join_detail: object,
) -> list[DomainTopologyIssue]:
    issues: list[DomainTopologyIssue] = []
    if controller_detail is None:
        issues.append(
            _issue(
                "domain.relationship.controller-detail-required",
                f"{label} type 'domain_controller_for' requires domain_controller detail",
            )
        )
    if join_detail is not None:
        issues.append(
            _issue(
                _RELATIONSHIP_DETAIL_MISMATCH,
                f"{label} type 'domain_controller_for' must not carry domain_join detail",
            )
        )
    return issues


def _join_detail_issues(
    label: str,
    controller_detail: object,
    join_detail: object,
) -> list[DomainTopologyIssue]:
    issues: list[DomainTopologyIssue] = []
    if join_detail is None:
        issues.append(
            _issue(
                "domain.relationship.join-detail-required",
                f"{label} type 'joins_domain' requires domain_join detail",
            )
        )
    if controller_detail is not None:
        issues.append(
            _issue(
                _RELATIONSHIP_DETAIL_MISMATCH,
                f"{label} type 'joins_domain' must not carry domain_controller detail",
            )
        )
    return issues


def _untyped_detail_issues(
    label: str,
    type_value: str,
    controller_detail: object,
    join_detail: object,
) -> list[DomainTopologyIssue]:
    issues: list[DomainTopologyIssue] = []
    if controller_detail is not None or join_detail is not None:
        issues.append(
            _issue(
                _RELATIONSHIP_DETAIL_MISMATCH,
                f"{label} carries domain topology detail but has type '{type_value}'",
            )
        )
    return issues


def _relationship_detail_issues(
    relationship_name: str,
    relationship: object,
    is_unresolved: Callable[[object], bool],
) -> list[DomainTopologyIssue]:
    relationship_type = getattr(relationship, "type", "")
    issues: list[DomainTopologyIssue] = []
    if not is_unresolved(relationship_type):
        type_value = _relationship_type(relationship_type)
        controller_detail = getattr(relationship, "domain_controller", None)
        join_detail = getattr(relationship, "domain_join", None)
        label = f"Relationship '{relationship_name}'"
        if type_value == RelationshipType.DOMAIN_CONTROLLER_FOR.value:
            issues = _controller_detail_issues(label, controller_detail, join_detail)
        elif type_value == RelationshipType.JOINS_DOMAIN.value:
            issues = _join_detail_issues(label, controller_detail, join_detail)
        else:
            issues = _untyped_detail_issues(label, type_value, controller_detail, join_detail)
    return issues


def _typed_relationship_issues(
    relationships: Mapping[str, object],
    *,
    is_unresolved: Callable[[object], bool],
) -> list[DomainTopologyIssue]:
    issues: list[DomainTopologyIssue] = []
    for relationship_name, relationship in relationships.items():
        issues.extend(_relationship_detail_issues(relationship_name, relationship, is_unresolved))
    return issues


def _topology_relationship(
    relationship_name: str,
    relationship: object,
    identity_domains: Mapping[str, object],
    nodes: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[_TopologyRelationship | None, list[DomainTopologyIssue]]:
    relationship_type = getattr(relationship, "type", "")
    source_ref = getattr(relationship, "source", "")
    target_ref = getattr(relationship, "target", "")
    if any(is_unresolved(value) for value in (relationship_type, source_ref, target_ref)):
        return None, []

    type_value = _relationship_type(relationship_type)
    topology_types = {
        RelationshipType.DOMAIN_CONTROLLER_FOR.value,
        RelationshipType.JOINS_DOMAIN.value,
    }
    if type_value not in topology_types:
        return None, []

    issues: list[DomainTopologyIssue] = []
    label = f"Relationship '{relationship_name}'"
    node_name = _resolve_section_ref(source_ref, "nodes", nodes)
    domain_name = _resolve_section_ref(target_ref, "identity_domains", identity_domains)
    if node_name is None:
        issues.append(
            _issue(
                "domain.relationship.source-unbound",
                f"{label} domain topology source '{source_ref}' does not resolve to a node",
            )
        )
    elif getattr(nodes[node_name], "type", None) != NodeType.VM:
        role = "controller" if type_value == RelationshipType.DOMAIN_CONTROLLER_FOR.value else "join"
        issues.append(
            _issue(
                "domain.relationship.source-not-vm",
                f"{label} {role} source '{source_ref}' must be a VM node",
            )
        )
    if domain_name is None:
        issues.append(
            _issue(
                "domain.relationship.target-unbound",
                f"{label} target '{target_ref}' does not resolve to an identity domain",
            )
        )

    topology_relationship = None
    if node_name is not None and domain_name is not None:
        topology_relationship = _TopologyRelationship(
            name=relationship_name,
            type_value=type_value,
            label=label,
            node_name=node_name,
            domain_name=domain_name,
        )
    return topology_relationship, issues


def _record_controller_relationship(
    facts: _TopologyFacts,
    topology: _TopologyRelationship,
    relationship: object,
) -> None:
    if getattr(relationship, "domain_controller", None) is None:
        return
    pair = (topology.node_name, topology.domain_name)
    if pair in facts.controller_pairs:
        facts.issues.append(
            _issue(
                "domain.controller.duplicate",
                f"Relationship '{topology.name}' repeats duplicate controller fact for node "
                f"'{topology.node_name}' and identity domain '{topology.domain_name}'",
            )
        )
    else:
        facts.controller_pairs.add(pair)
        facts.controller_edges[topology.domain_name].append((topology.name, topology.node_name))


def _resolved_join_controllers(
    topology: _TopologyRelationship,
    join_detail: object,
    nodes: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[tuple[str, ...], list[DomainTopologyIssue]]:
    controller_names: list[str] = []
    issues: list[DomainTopologyIssue] = []
    for controller_ref in getattr(join_detail, "controller_refs", ()):
        if is_unresolved(controller_ref):
            continue
        controller_name = _resolve_section_ref(controller_ref, "nodes", nodes)
        if controller_name is None:
            issues.append(
                _issue(
                    "domain.join.controller-unbound",
                    f"{topology.label} controller_ref '{controller_ref}' does not resolve to a node",
                )
            )
            continue
        controller_names.append(controller_name)
    return tuple(controller_names), issues


def _record_join_relationship(
    facts: _TopologyFacts,
    topology: _TopologyRelationship,
    relationship: object,
    nodes: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> None:
    join_detail = getattr(relationship, "domain_join", None)
    if join_detail is None:
        return
    pair = (topology.node_name, topology.domain_name)
    if pair in facts.join_pairs:
        facts.issues.append(
            _issue(
                "domain.join.duplicate",
                f"Relationship '{topology.name}' repeats duplicate join fact for node "
                f"'{topology.node_name}' and identity domain '{topology.domain_name}'",
            )
        )
        return

    facts.join_pairs.add(pair)
    controller_names, issues = _resolved_join_controllers(topology, join_detail, nodes, is_unresolved)
    facts.issues.extend(issues)
    facts.join_edges[topology.domain_name].append((topology.name, topology.node_name, controller_names))


def _collect_topology_facts(
    identity_domains: Mapping[str, object],
    nodes: Mapping[str, object],
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> _TopologyFacts:
    facts = _TopologyFacts(issues=_typed_relationship_issues(relationships, is_unresolved=is_unresolved))
    for relationship_name, relationship in relationships.items():
        topology, issues = _topology_relationship(
            relationship_name,
            relationship,
            identity_domains,
            nodes,
            is_unresolved,
        )
        facts.issues.extend(issues)
        if topology is None:
            continue
        if topology.type_value == RelationshipType.DOMAIN_CONTROLLER_FOR.value:
            _record_controller_relationship(facts, topology, relationship)
        else:
            _record_join_relationship(facts, topology, relationship, nodes, is_unresolved)
    return facts


def _controllers_by_domain(
    identity_domains: Mapping[str, object],
    controller_edges: Mapping[str, list[tuple[str, str]]],
) -> dict[str, tuple[str, ...]]:
    return {
        domain_name: tuple(node_name for _relationship_name, node_name in controller_edges.get(domain_name, ()))
        for domain_name in identity_domains
    }


def _missing_controller_issues(
    controllers_by_domain: Mapping[str, tuple[str, ...]],
) -> list[DomainTopologyIssue]:
    issues: list[DomainTopologyIssue] = []
    for domain_name, controllers in controllers_by_domain.items():
        if not controllers:
            issues.append(
                _issue(
                    "domain.controller.missing",
                    f"Identity domain '{domain_name}' has no controller relationship",
                )
            )
    return issues


def _join_controller_issues(
    join_edges: Mapping[str, list[tuple[str, str, tuple[str, ...]]]],
    controllers_by_domain: Mapping[str, tuple[str, ...]],
) -> list[DomainTopologyIssue]:
    issues: list[DomainTopologyIssue] = []
    for domain_name, joins in join_edges.items():
        valid_controllers = set(controllers_by_domain.get(domain_name, ()))
        for relationship_name, _node_name, controller_names in joins:
            for controller_name in controller_names:
                if controller_name not in valid_controllers:
                    issues.append(
                        _issue(
                            "domain.join.controller-wrong-domain",
                            f"Relationship '{relationship_name}' controller_ref '{controller_name}' does not "
                            f"control the same domain '{domain_name}'",
                        )
                    )
    return issues


def _build_memberships(
    controllers_by_domain: Mapping[str, tuple[str, ...]],
    join_edges: Mapping[str, list[tuple[str, str, tuple[str, ...]]]],
) -> dict[str, list[DomainNodeBinding]]:
    memberships: dict[str, list[DomainNodeBinding]] = defaultdict(list)
    for domain_name, controllers in controllers_by_domain.items():
        for node_name in controllers:
            memberships[node_name].append(
                DomainNodeBinding(
                    node_name=node_name,
                    domain_name=domain_name,
                    role=DomainNodeRole.CONTROLLER,
                    controller_names=controllers,
                )
            )
    for domain_name, joins in join_edges.items():
        for _relationship_name, node_name, controller_names in joins:
            memberships[node_name].append(
                DomainNodeBinding(
                    node_name=node_name,
                    domain_name=domain_name,
                    role=DomainNodeRole.MEMBER,
                    controller_names=controller_names,
                )
            )
    return memberships


def _redundant_join_issues(
    node_name: str,
    bindings: list[DomainNodeBinding],
) -> list[DomainTopologyIssue]:
    issues: list[DomainTopologyIssue] = []
    for domain_name in {binding.domain_name for binding in bindings}:
        roles = {binding.role for binding in bindings if binding.domain_name == domain_name}
        if DomainNodeRole.CONTROLLER in roles and DomainNodeRole.MEMBER in roles:
            issues.append(
                _issue(
                    "domain.node.redundant-join",
                    f"Node '{node_name}' is a controller for domain '{domain_name}' and must not declare "
                    "a redundant join",
                )
            )
    return issues


def _multiple_active_directory_issues(
    node_name: str,
    bindings: list[DomainNodeBinding],
    identity_domains: Mapping[str, object],
) -> list[DomainTopologyIssue]:
    issues: list[DomainTopologyIssue] = []
    active_directory_domains = {
        binding.domain_name
        for binding in bindings
        if _domain_profile(getattr(identity_domains[binding.domain_name], "profile", ""))
        == IdentityDomainProfile.ACTIVE_DIRECTORY.value
    }
    if len(active_directory_domains) > 1:
        issues.append(
            _issue(
                "domain.node.multiple-active-directory-domains",
                f"Node '{node_name}' belongs to multiple active_directory domains: "
                f"{', '.join(sorted(active_directory_domains))}",
            )
        )
    return issues


def _membership_issues(
    memberships: Mapping[str, list[DomainNodeBinding]],
    identity_domains: Mapping[str, object],
) -> list[DomainTopologyIssue]:
    issues: list[DomainTopologyIssue] = []
    for node_name, bindings in memberships.items():
        issues.extend(_redundant_join_issues(node_name, bindings))
        issues.extend(_multiple_active_directory_issues(node_name, bindings, identity_domains))
    return issues


def _account_domain(
    account_name: str,
    account: object,
    identity_domains: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[str | None, list[DomainTopologyIssue]]:
    issues: list[DomainTopologyIssue] = []
    domain_name = None
    domain_ref = getattr(account, "domain_ref", "")
    if getattr(account, "spn", "") and not domain_ref:
        issues.append(
            _issue(
                "domain.account.spn-without-domain",
                f"Account '{account_name}' declares an SPN and requires explicit domain_ref",
            )
        )
    if domain_ref and not is_unresolved(domain_ref):
        domain_name = _resolve_section_ref(domain_ref, "identity_domains", identity_domains)
        if domain_name is None:
            issues.append(
                _issue(
                    "domain.account.domain-unbound",
                    f"Account '{account_name}' domain_ref '{domain_ref}' does not resolve to an identity domain",
                )
            )
    return domain_name, issues


def _account_node(
    account: object,
    nodes: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> str | None:
    node_ref = getattr(account, "node", "")
    if is_unresolved(node_ref):
        return None
    return _resolve_section_ref(node_ref, "nodes", nodes)


def _account_binding(
    account_name: str,
    account: object,
    identity_domains: Mapping[str, object],
    nodes: Mapping[str, object],
    memberships: Mapping[str, list[DomainNodeBinding]],
    is_unresolved: Callable[[object], bool],
) -> tuple[DomainAccountBinding | None, list[DomainTopologyIssue]]:
    domain_name, issues = _account_domain(account_name, account, identity_domains, is_unresolved)
    binding = None
    if domain_name is not None:
        node_name = _account_node(account, nodes, is_unresolved)
        if node_name is not None:
            if any(member.domain_name == domain_name for member in memberships.get(node_name, ())):
                binding = DomainAccountBinding(
                    account_name=account_name,
                    node_name=node_name,
                    domain_name=domain_name,
                )
            else:
                issues.append(
                    _issue(
                        "domain.account.node-outside-domain",
                        f"Account '{account_name}' is placed on node '{node_name}', which does not belong to "
                        f"domain '{domain_name}'",
                    )
                )
    return binding, issues


def _account_bindings(
    accounts: Mapping[str, object],
    identity_domains: Mapping[str, object],
    nodes: Mapping[str, object],
    memberships: Mapping[str, list[DomainNodeBinding]],
    is_unresolved: Callable[[object], bool],
) -> tuple[dict[str, DomainAccountBinding], list[DomainTopologyIssue]]:
    bindings: dict[str, DomainAccountBinding] = {}
    issues: list[DomainTopologyIssue] = []
    for account_name, account in accounts.items():
        binding, account_issues = _account_binding(
            account_name,
            account,
            identity_domains,
            nodes,
            memberships,
            is_unresolved,
        )
        issues.extend(account_issues)
        if binding is not None:
            bindings[account_name] = binding
    return bindings, issues


def _authority_account(
    domain_name: str,
    domain: object,
    accounts: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[str | None, list[DomainTopologyIssue]]:
    issues: list[DomainTopologyIssue] = []
    authority_name = None
    authority_ref = getattr(domain, "authority_account_ref", "")
    if not is_unresolved(authority_ref):
        authority_name = _resolve_section_ref(authority_ref, "accounts", accounts)
        if authority_name is None:
            issues.append(
                _issue(
                    "domain.authority.account-unbound",
                    f"Identity domain '{domain_name}' authority account '{authority_ref}' is not declared",
                )
            )
    return authority_name, issues


def _authority_binding(
    domain_name: str,
    authority_name: str,
    accounts: Mapping[str, object],
    nodes: Mapping[str, object],
    controllers_by_domain: Mapping[str, tuple[str, ...]],
    account_bindings: Mapping[str, DomainAccountBinding],
) -> tuple[DomainAccountBinding | None, list[DomainTopologyIssue]]:
    issues: list[DomainTopologyIssue] = []
    binding = None
    authority_node_ref = getattr(accounts[authority_name], "node", "")
    authority_node = _resolve_section_ref(authority_node_ref, "nodes", nodes)
    if authority_node not in set(controllers_by_domain.get(domain_name, ())):
        issues.append(
            _issue(
                "domain.authority.not-on-controller",
                f"Identity domain '{domain_name}' authority account '{authority_name}' must be placed on "
                "one of its controller nodes",
            )
        )
    else:
        existing_binding = account_bindings.get(authority_name)
        if existing_binding is not None and existing_binding.domain_name != domain_name:
            issues.append(
                _issue(
                    "domain.authority.domain-conflict",
                    f"Identity domain '{domain_name}' authority account '{authority_name}' is already bound to "
                    f"domain '{existing_binding.domain_name}'",
                )
            )
        else:
            binding = DomainAccountBinding(
                account_name=authority_name,
                node_name=authority_node,
                domain_name=domain_name,
            )
    return binding, issues


def _apply_authority_bindings(
    identity_domains: Mapping[str, object],
    accounts: Mapping[str, object],
    nodes: Mapping[str, object],
    controllers_by_domain: Mapping[str, tuple[str, ...]],
    account_bindings: dict[str, DomainAccountBinding],
    is_unresolved: Callable[[object], bool],
) -> list[DomainTopologyIssue]:
    issues: list[DomainTopologyIssue] = []
    for domain_name, domain in identity_domains.items():
        authority_name, authority_issues = _authority_account(domain_name, domain, accounts, is_unresolved)
        issues.extend(authority_issues)
        if authority_name is None:
            continue
        binding, binding_issues = _authority_binding(
            domain_name,
            authority_name,
            accounts,
            nodes,
            controllers_by_domain,
            account_bindings,
        )
        issues.extend(binding_issues)
        if binding is not None:
            account_bindings[authority_name] = binding
    return issues


def analyze_domain_topology(
    *,
    identity_domains: Mapping[str, object],
    nodes: Mapping[str, object],
    accounts: Mapping[str, object],
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> DomainTopologyAnalysis:
    """Validate and normalize authored controller, join, and account facts."""

    facts = _collect_topology_facts(identity_domains, nodes, relationships, is_unresolved)
    controllers_by_domain = _controllers_by_domain(identity_domains, facts.controller_edges)
    facts.issues.extend(_missing_controller_issues(controllers_by_domain))
    facts.issues.extend(_join_controller_issues(facts.join_edges, controllers_by_domain))

    memberships = _build_memberships(controllers_by_domain, facts.join_edges)
    facts.issues.extend(_membership_issues(memberships, identity_domains))
    node_bindings = {node_name: bindings[0] for node_name, bindings in memberships.items() if bindings}

    account_bindings, account_issues = _account_bindings(
        accounts,
        identity_domains,
        nodes,
        memberships,
        is_unresolved,
    )
    facts.issues.extend(account_issues)
    facts.issues.extend(
        _apply_authority_bindings(
            identity_domains,
            accounts,
            nodes,
            controllers_by_domain,
            account_bindings,
            is_unresolved,
        )
    )

    return DomainTopologyAnalysis(
        node_bindings=node_bindings,
        account_bindings=account_bindings,
        controllers_by_domain=controllers_by_domain,
        issues=tuple(facts.issues),
    )


__all__ = [
    "DomainAccountBinding",
    "DomainNodeBinding",
    "DomainNodeRole",
    "DomainTopologyAnalysis",
    "DomainTopologyIssue",
    "analyze_domain_topology",
]
