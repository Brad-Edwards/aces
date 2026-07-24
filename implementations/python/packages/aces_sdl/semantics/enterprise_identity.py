"""Pure analysis for authored forest, facade, trust, and federation intent."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ..relationships import RelationshipType
from ._domain_topology_types import resolve_section_ref


@dataclass(frozen=True)
class EnterpriseIdentityIssue:
    code: str
    message: str


def _type_value(value: object) -> str:
    return value.value if isinstance(value, RelationshipType) else str(value)


def _issue(code: str, message: str) -> EnterpriseIdentityIssue:
    return EnterpriseIdentityIssue(code=code, message=message)


def _forest_issues(
    identity_domains: Mapping[str, object],
    identity_forests: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[EnterpriseIdentityIssue]:
    issues: list[EnterpriseIdentityIssue] = []
    memberships: defaultdict[str, list[str]] = defaultdict(list)
    for forest_name, forest in identity_forests.items():
        root_ref = getattr(forest, "root_domain_ref", "")
        domain_refs = tuple(getattr(forest, "domain_refs", ()))
        resolved_members: set[str] = set()
        for domain_ref in domain_refs:
            if is_unresolved(domain_ref):
                continue
            domain_name = resolve_section_ref(domain_ref, "identity_domains", identity_domains)
            if domain_name is None:
                issues.append(
                    _issue(
                        "enterprise-identity.forest.domain-unbound",
                        f"Identity forest '{forest_name}' domain_ref '{domain_ref}' does not resolve "
                        "to an identity domain",
                    )
                )
                continue
            resolved_members.add(domain_name)
            memberships[domain_name].append(forest_name)
        if not is_unresolved(root_ref):
            root_name = resolve_section_ref(root_ref, "identity_domains", identity_domains)
            if root_name is None:
                issues.append(
                    _issue(
                        "enterprise-identity.forest.root-unbound",
                        f"Identity forest '{forest_name}' root_domain_ref '{root_ref}' does not resolve "
                        "to an identity domain",
                    )
                )
            elif root_name not in resolved_members:
                issues.append(
                    _issue(
                        "enterprise-identity.forest.root-not-member",
                        f"Identity forest '{forest_name}' root_domain_ref '{root_ref}' must appear in domain_refs",
                    )
                )
    for domain_name, forests in memberships.items():
        if len(forests) > 1:
            issues.append(
                _issue(
                    "enterprise-identity.forest.domain-multiple",
                    f"Identity domain '{domain_name}' belongs to multiple forests: {', '.join(sorted(forests))}",
                )
            )
    if identity_forests:
        for domain_name in identity_domains:
            if domain_name not in memberships:
                issues.append(
                    _issue(
                        "enterprise-identity.forest.domain-missing",
                        f"Identity domain '{domain_name}' must belong to exactly one identity forest",
                    )
                )
    return issues


def _service_owner(service_ref: object, nodes: Mapping[str, object]) -> str | None:
    if not isinstance(service_ref, str):
        return None
    for node_name, node in nodes.items():
        for service in getattr(node, "services", ()):
            service_name = getattr(service, "name", "")
            if service_name and service_ref == f"nodes.{node_name}.services.{service_name}":
                return node_name
    return None


def _facade_issues(
    identity_facades: Mapping[str, object],
    nodes: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[EnterpriseIdentityIssue]:
    issues: list[EnterpriseIdentityIssue] = []
    for facade_name, facade in identity_facades.items():
        service_ref = getattr(facade, "service_ref", "")
        if not is_unresolved(service_ref) and _service_owner(service_ref, nodes) is None:
            issues.append(
                _issue(
                    "enterprise-identity.facade.service-unbound",
                    f"Identity facade '{facade_name}' service_ref '{service_ref}' does not resolve "
                    "to a named VM service",
                )
            )
    return issues


_DETAIL_FIELDS = {
    RelationshipType.FOREST_TRUSTS.value: "forest_trust",
    RelationshipType.DIRECTORY_FEDERATES_TO.value: "identity_federation",
}


def _relationship_detail_issues(
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[EnterpriseIdentityIssue]:
    issues: list[EnterpriseIdentityIssue] = []
    detail_fields = tuple(_DETAIL_FIELDS.values())
    for name, relationship in relationships.items():
        type_value = getattr(relationship, "type", "")
        if is_unresolved(type_value):
            continue
        type_name = _type_value(type_value)
        expected = _DETAIL_FIELDS.get(type_name)
        populated = [field_name for field_name in detail_fields if getattr(relationship, field_name, None) is not None]
        if expected is not None and expected not in populated:
            issues.append(
                _issue(
                    "enterprise-identity.relationship.detail-required",
                    f"Relationship '{name}' type '{type_name}' requires {expected} detail",
                )
            )
        for field_name in populated:
            if field_name != expected:
                issues.append(
                    _issue(
                        "enterprise-identity.relationship.detail-mismatch",
                        f"Relationship '{name}' carries {field_name} detail with type '{type_name}'",
                    )
                )
    return issues


def _typed_edge_issues(
    identity_domains: Mapping[str, object],
    identity_forests: Mapping[str, object],
    identity_facades: Mapping[str, object],
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[EnterpriseIdentityIssue]:
    issues: list[EnterpriseIdentityIssue] = []
    seen_trust_pairs: set[frozenset[str]] = set()
    federated_facades: set[str] = set()
    for name, relationship in relationships.items():
        type_value = getattr(relationship, "type", "")
        source = getattr(relationship, "source", "")
        target = getattr(relationship, "target", "")
        if any(is_unresolved(value) for value in (type_value, source, target)):
            continue
        type_name = _type_value(type_value)
        if type_name == RelationshipType.FOREST_TRUSTS.value:
            source_name = resolve_section_ref(source, "identity_forests", identity_forests)
            target_name = resolve_section_ref(target, "identity_forests", identity_forests)
            if source_name is None or target_name is None:
                issues.append(
                    _issue(
                        "enterprise-identity.forest-trust.endpoint-invalid",
                        f"Relationship '{name}' forest trust endpoints must resolve to identity forests",
                    )
                )
            elif source_name == target_name:
                issues.append(
                    _issue(
                        "enterprise-identity.forest-trust.self",
                        f"Relationship '{name}' cannot trust a forest with itself",
                    )
                )
            else:
                pair = frozenset((source_name, target_name))
                if pair in seen_trust_pairs:
                    issues.append(
                        _issue(
                            "enterprise-identity.forest-trust.duplicate",
                            f"Relationship '{name}' duplicates a forest trust for the same forest pair",
                        )
                    )
                seen_trust_pairs.add(pair)
        elif type_name == RelationshipType.DIRECTORY_FEDERATES_TO.value:
            authority_resolves = (
                resolve_section_ref(source, "identity_domains", identity_domains) is not None
                or resolve_section_ref(source, "identity_forests", identity_forests) is not None
            )
            facade_resolves = resolve_section_ref(target, "identity_facades", identity_facades)
            if not authority_resolves or facade_resolves is None:
                issues.append(
                    _issue(
                        "enterprise-identity.federation.endpoint-invalid",
                        f"Relationship '{name}' must connect one identity domain or forest to an identity facade",
                    )
                )
            elif facade_resolves in federated_facades:
                issues.append(
                    _issue(
                        "enterprise-identity.federation.facade-multiple",
                        f"Identity facade '{facade_resolves}' has multiple authored human authorities",
                    )
                )
            else:
                federated_facades.add(facade_resolves)
    return issues


def analyze_enterprise_identity(
    *,
    identity_domains: Mapping[str, object],
    identity_forests: Mapping[str, object],
    identity_facades: Mapping[str, object],
    nodes: Mapping[str, object],
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[EnterpriseIdentityIssue, ...]:
    """Validate enterprise identity declarations without runtime/provider inference."""

    issues = _forest_issues(identity_domains, identity_forests, is_unresolved)
    issues.extend(_facade_issues(identity_facades, nodes, is_unresolved))
    issues.extend(_relationship_detail_issues(relationships, is_unresolved))
    issues.extend(
        _typed_edge_issues(
            identity_domains,
            identity_forests,
            identity_facades,
            relationships,
            is_unresolved,
        )
    )
    return tuple(issues)


__all__ = ["EnterpriseIdentityIssue", "analyze_enterprise_identity"]
