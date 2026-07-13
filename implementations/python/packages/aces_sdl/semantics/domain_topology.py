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


def _typed_relationship_issues(
    relationships: Mapping[str, object],
    *,
    is_unresolved: Callable[[object], bool],
) -> list[DomainTopologyIssue]:
    issues: list[DomainTopologyIssue] = []
    for relationship_name, relationship in relationships.items():
        relationship_type = getattr(relationship, "type", "")
        if is_unresolved(relationship_type):
            continue
        type_value = _relationship_type(relationship_type)
        controller_detail = getattr(relationship, "domain_controller", None)
        join_detail = getattr(relationship, "domain_join", None)
        label = f"Relationship '{relationship_name}'"
        if type_value == RelationshipType.DOMAIN_CONTROLLER_FOR.value:
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
                        "domain.relationship.detail-mismatch",
                        f"{label} type 'domain_controller_for' must not carry domain_join detail",
                    )
                )
        elif type_value == RelationshipType.JOINS_DOMAIN.value:
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
                        "domain.relationship.detail-mismatch",
                        f"{label} type 'joins_domain' must not carry domain_controller detail",
                    )
                )
        else:
            if controller_detail is not None or join_detail is not None:
                issues.append(
                    _issue(
                        "domain.relationship.detail-mismatch",
                        f"{label} carries domain topology detail but has type '{type_value}'",
                    )
                )
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

    issues = _typed_relationship_issues(relationships, is_unresolved=is_unresolved)
    controller_edges: dict[str, list[tuple[str, str]]] = defaultdict(list)
    join_edges: dict[str, list[tuple[str, str, tuple[str, ...]]]] = defaultdict(list)
    controller_pairs: set[tuple[str, str]] = set()
    join_pairs: set[tuple[str, str]] = set()

    for relationship_name, relationship in relationships.items():
        relationship_type = getattr(relationship, "type", "")
        source_ref = getattr(relationship, "source", "")
        target_ref = getattr(relationship, "target", "")
        if is_unresolved(relationship_type) or is_unresolved(source_ref) or is_unresolved(target_ref):
            continue
        type_value = _relationship_type(relationship_type)
        if type_value not in {
            RelationshipType.DOMAIN_CONTROLLER_FOR.value,
            RelationshipType.JOINS_DOMAIN.value,
        }:
            continue

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
        if node_name is None or domain_name is None:
            continue

        if type_value == RelationshipType.DOMAIN_CONTROLLER_FOR.value:
            if getattr(relationship, "domain_controller", None) is None:
                continue
            pair = (node_name, domain_name)
            if pair in controller_pairs:
                issues.append(
                    _issue(
                        "domain.controller.duplicate",
                        f"Relationship '{relationship_name}' repeats duplicate controller fact for node "
                        f"'{node_name}' and identity domain '{domain_name}'",
                    )
                )
            else:
                controller_pairs.add(pair)
                controller_edges[domain_name].append((relationship_name, node_name))
            continue

        join_detail = getattr(relationship, "domain_join", None)
        if join_detail is None:
            continue
        pair = (node_name, domain_name)
        if pair in join_pairs:
            issues.append(
                _issue(
                    "domain.join.duplicate",
                    f"Relationship '{relationship_name}' repeats duplicate join fact for node "
                    f"'{node_name}' and identity domain '{domain_name}'",
                )
            )
            continue
        join_pairs.add(pair)
        controller_names: list[str] = []
        for controller_ref in getattr(join_detail, "controller_refs", ()):
            if is_unresolved(controller_ref):
                continue
            controller_name = _resolve_section_ref(controller_ref, "nodes", nodes)
            if controller_name is None:
                issues.append(
                    _issue(
                        "domain.join.controller-unbound",
                        f"{label} controller_ref '{controller_ref}' does not resolve to a node",
                    )
                )
                continue
            controller_names.append(controller_name)
        join_edges[domain_name].append((relationship_name, node_name, tuple(controller_names)))

    controllers_by_domain = {
        domain_name: tuple(node_name for _relationship_name, node_name in controller_edges.get(domain_name, ()))
        for domain_name in identity_domains
    }
    for domain_name, controllers in controllers_by_domain.items():
        if not controllers:
            issues.append(
                _issue(
                    "domain.controller.missing",
                    f"Identity domain '{domain_name}' has no controller relationship",
                )
            )

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

    for node_name, bindings in memberships.items():
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

    node_bindings = {node_name: bindings[0] for node_name, bindings in memberships.items() if bindings}
    account_bindings: dict[str, DomainAccountBinding] = {}
    for account_name, account in accounts.items():
        domain_ref = getattr(account, "domain_ref", "")
        if getattr(account, "spn", "") and not domain_ref:
            issues.append(
                _issue(
                    "domain.account.spn-without-domain",
                    f"Account '{account_name}' declares an SPN and requires explicit domain_ref",
                )
            )
        if not domain_ref or is_unresolved(domain_ref):
            continue
        domain_name = _resolve_section_ref(domain_ref, "identity_domains", identity_domains)
        if domain_name is None:
            issues.append(
                _issue(
                    "domain.account.domain-unbound",
                    f"Account '{account_name}' domain_ref '{domain_ref}' does not resolve to an identity domain",
                )
            )
            continue
        node_ref = getattr(account, "node", "")
        if is_unresolved(node_ref):
            continue
        node_name = _resolve_section_ref(node_ref, "nodes", nodes)
        if node_name is None:
            continue
        if not any(binding.domain_name == domain_name for binding in memberships.get(node_name, ())):
            issues.append(
                _issue(
                    "domain.account.node-outside-domain",
                    f"Account '{account_name}' is placed on node '{node_name}', which does not belong to "
                    f"domain '{domain_name}'",
                )
            )
            continue
        account_bindings[account_name] = DomainAccountBinding(
            account_name=account_name,
            node_name=node_name,
            domain_name=domain_name,
        )

    for domain_name, domain in identity_domains.items():
        authority_ref = getattr(domain, "authority_account_ref", "")
        if is_unresolved(authority_ref):
            continue
        authority_name = _resolve_section_ref(authority_ref, "accounts", accounts)
        if authority_name is None:
            issues.append(
                _issue(
                    "domain.authority.account-unbound",
                    f"Identity domain '{domain_name}' authority account '{authority_ref}' is not declared",
                )
            )
            continue
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
            continue
        existing_binding = account_bindings.get(authority_name)
        if existing_binding is not None and existing_binding.domain_name != domain_name:
            issues.append(
                _issue(
                    "domain.authority.domain-conflict",
                    f"Identity domain '{domain_name}' authority account '{authority_name}' is already bound to "
                    f"domain '{existing_binding.domain_name}'",
                )
            )
            continue
        account_bindings[authority_name] = DomainAccountBinding(
            account_name=authority_name,
            node_name=authority_node,
            domain_name=domain_name,
        )

    return DomainTopologyAnalysis(
        node_bindings=node_bindings,
        account_bindings=account_bindings,
        controllers_by_domain=controllers_by_domain,
        issues=tuple(issues),
    )


__all__ = [
    "DomainAccountBinding",
    "DomainNodeBinding",
    "DomainNodeRole",
    "DomainTopologyAnalysis",
    "DomainTopologyIssue",
    "analyze_domain_topology",
]
