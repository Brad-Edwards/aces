"""Semantic validation helpers for runtime mail-service inventories."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

_NODES_PREFIX = "nodes."


class _MailComponentLike(Protocol):
    component_id: str


class _MailListenerLike(Protocol):
    listener_id: str
    service: str
    component_ref: str


class _MailDomainLike(Protocol):
    domain_id: str


class _MailStoreLike(Protocol):
    store_id: str


class _MailMailboxLike(Protocol):
    mailbox_id: str
    domain_ref: str
    store_ref: str
    account_ref: str
    local_user_ref: str


class _MailAliasLike(Protocol):
    alias_id: str
    domain_ref: str
    target_refs: Sequence[str]


class _MailRoutingRuleLike(Protocol):
    rule_id: str
    source_ref: str
    target_ref: str


class _MailQueueLike(Protocol):
    queue_id: str


class _MailSettingLike(Protocol):
    setting_id: str
    component_ref: str
    source_path: str


class _RuntimeMailServiceLike(Protocol):
    service_id: str
    service: str
    components: Sequence[_MailComponentLike]
    listeners: Sequence[_MailListenerLike]
    domains: Sequence[_MailDomainLike]
    mailbox_stores: Sequence[_MailStoreLike]
    mailboxes: Sequence[_MailMailboxLike]
    aliases: Sequence[_MailAliasLike]
    routing_rules: Sequence[_MailRoutingRuleLike]
    queues: Sequence[_MailQueueLike]
    settings: Sequence[_MailSettingLike]


class _RuntimeLike(Protocol):
    mail_services: Sequence[_RuntimeMailServiceLike]


class _NodeLike(Protocol):
    runtime: _RuntimeLike | None


class _MailAccessLike(Protocol):
    listener_ref: str
    mailbox_ref: str
    domain_ref: str


class _RelationshipLike(Protocol):
    target: str
    mail_access: _MailAccessLike | None


class _ScenarioLike(Protocol):
    nodes: Mapping[str, _NodeLike]
    accounts: Mapping[str, object]
    relationships: Mapping[str, _RelationshipLike]


class _MailSemanticValidator(Protocol):
    _s: _ScenarioLike

    def _node_service_names(self, node: _NodeLike) -> set[str]: ...

    def _node_observed_paths(self, node: _NodeLike) -> set[str]: ...

    def _node_local_user_names(self, node: _NodeLike) -> set[str]: ...

    def _verify_owned_service_ref(
        self,
        node_name: str,
        ref: str,
        service_names: set[str],
        *,
        owner_label: str,
    ) -> None: ...

    def _is_unresolved_var(self, value: object) -> bool: ...

    def _split_runtime_ref(self, ref: object, *, surface: str) -> tuple[str, str] | None: ...

    def _err(self, msg: str) -> None: ...


@dataclass(frozen=True)
class _MailServiceLocalIds:
    components: set[str]
    domains: set[str]
    stores: set[str]
    mailboxes: set[str]
    aliases: set[str]
    routing_refs: set[str]


@dataclass(frozen=True)
class _MailRefTail:
    service_id: str
    collection_name: str
    child_id: str


_ChildIdReader = Callable[[_RuntimeMailServiceLike], Iterable[str]]
_MAIL_CHILD_ID_READERS: Mapping[str, _ChildIdReader] = {
    "components": lambda service: (component.component_id for component in service.components),
    "listeners": lambda service: (listener.listener_id for listener in service.listeners),
    "domains": lambda service: (domain.domain_id for domain in service.domains),
    "mailbox_stores": lambda service: (store.store_id for store in service.mailbox_stores),
    "mailboxes": lambda service: (mailbox.mailbox_id for mailbox in service.mailboxes),
    "aliases": lambda service: (alias.alias_id for alias in service.aliases),
    "routing_rules": lambda service: (rule.rule_id for rule in service.routing_rules),
    "queues": lambda service: (queue.queue_id for queue in service.queues),
    "settings": lambda service: (setting.setting_id for setting in service.settings),
}


def collect_qualified_mail_refs(scenario: _ScenarioLike) -> set[str]:
    """Return targetable refs for runtime mail services and stable children."""
    refs: set[str] = set()
    for node_name, node in scenario.nodes.items():
        for service in _mail_services_for_node(node):
            base = f"{_NODES_PREFIX}{node_name}.runtime.mail_services.{service.service_id}"
            refs.add(base)
            refs.update(
                f"{base}.{collection_name}.{child_id}"
                for collection_name, child_id in _iter_mail_child_refs(service)
                if child_id
            )
    return refs


def verify_runtime_mail_services(validator: _MailSemanticValidator) -> None:
    """Validate runtime mail-service inventories against the scenario graph."""
    for node_name, node in validator._s.nodes.items():
        mail_services = _mail_services_for_node(node)
        if not mail_services:
            continue
        service_names = validator._node_service_names(node)
        observed_paths = validator._node_observed_paths(node)
        local_user_names = validator._node_local_user_names(node)
        for service in mail_services:
            label = f"Node '{node_name}' runtime mail service '{service.service_id}'"
            validator._verify_owned_service_ref(
                node_name,
                service.service,
                service_names,
                owner_label=label,
            )
            _verify_mail_service_children(
                validator,
                node_name=node_name,
                label=label,
                service=service,
                service_names=service_names,
                observed_paths=observed_paths,
                local_user_names=local_user_names,
            )


def _verify_mail_service_children(
    validator: _MailSemanticValidator,
    *,
    node_name: str,
    label: str,
    service: _RuntimeMailServiceLike,
    service_names: set[str],
    observed_paths: set[str],
    local_user_names: set[str],
) -> None:
    local_ids = _collect_mail_service_local_ids(service)
    _verify_mail_listeners(validator, node_name, label, service, service_names, local_ids)
    _verify_mailboxes(validator, label, service, local_user_names, local_ids)
    _verify_mail_aliases(validator, label, service, local_ids)
    _verify_mail_routing_rules(validator, label, service, local_ids)
    _verify_mail_settings(validator, label, service, observed_paths, local_ids)


def _mail_services_for_node(node: _NodeLike) -> Sequence[_RuntimeMailServiceLike]:
    runtime = node.runtime
    return () if runtime is None else runtime.mail_services


def _iter_mail_child_refs(service: _RuntimeMailServiceLike) -> Iterable[tuple[str, str]]:
    for collection_name, read_child_ids in _MAIL_CHILD_ID_READERS.items():
        yield from ((collection_name, child_id) for child_id in read_child_ids(service))


def _collect_mail_service_local_ids(service: _RuntimeMailServiceLike) -> _MailServiceLocalIds:
    mailbox_ids = {mailbox.mailbox_id for mailbox in service.mailboxes}
    alias_ids = {alias.alias_id for alias in service.aliases}
    domain_ids = {domain.domain_id for domain in service.domains}
    return _MailServiceLocalIds(
        components={component.component_id for component in service.components},
        domains=domain_ids,
        stores={store.store_id for store in service.mailbox_stores},
        mailboxes=mailbox_ids,
        aliases=alias_ids,
        routing_refs=mailbox_ids | alias_ids | domain_ids,
    )


def _verify_mail_listeners(
    validator: _MailSemanticValidator,
    node_name: str,
    label: str,
    service: _RuntimeMailServiceLike,
    service_names: set[str],
    local_ids: _MailServiceLocalIds,
) -> None:
    for listener in service.listeners:
        listener_label = f"{label} listener '{listener.listener_id}'"
        validator._verify_owned_service_ref(
            node_name,
            listener.service,
            service_names,
            owner_label=listener_label,
        )
        _verify_mail_ref(
            validator,
            listener.component_ref,
            local_ids.components,
            label=listener_label,
            field_name="component_ref",
        )


def _verify_mailboxes(
    validator: _MailSemanticValidator,
    label: str,
    service: _RuntimeMailServiceLike,
    local_user_names: set[str],
    local_ids: _MailServiceLocalIds,
) -> None:
    for mailbox in service.mailboxes:
        mailbox_label = f"{label} mailbox '{mailbox.mailbox_id}'"
        _verify_mail_ref(validator, mailbox.domain_ref, local_ids.domains, label=mailbox_label, field_name="domain_ref")
        _verify_mail_ref(validator, mailbox.store_ref, local_ids.stores, label=mailbox_label, field_name="store_ref")
        _verify_mail_account_ref(validator, mailbox.account_ref, mailbox_label)
        _verify_mail_local_user_ref(validator, mailbox.local_user_ref, local_user_names, mailbox_label)


def _verify_mail_aliases(
    validator: _MailSemanticValidator,
    label: str,
    service: _RuntimeMailServiceLike,
    local_ids: _MailServiceLocalIds,
) -> None:
    for alias in service.aliases:
        alias_label = f"{label} alias '{alias.alias_id}'"
        _verify_mail_ref(validator, alias.domain_ref, local_ids.domains, label=alias_label, field_name="domain_ref")
        for target_ref in alias.target_refs:
            _verify_mail_ref(
                validator,
                target_ref,
                local_ids.mailboxes | local_ids.aliases,
                label=alias_label,
                field_name="target_ref",
            )


def _verify_mail_routing_rules(
    validator: _MailSemanticValidator,
    label: str,
    service: _RuntimeMailServiceLike,
    local_ids: _MailServiceLocalIds,
) -> None:
    for rule in service.routing_rules:
        rule_label = f"{label} routing rule '{rule.rule_id}'"
        _verify_mail_ref(validator, rule.source_ref, local_ids.routing_refs, label=rule_label, field_name="source_ref")
        _verify_mail_ref(validator, rule.target_ref, local_ids.routing_refs, label=rule_label, field_name="target_ref")


def _verify_mail_settings(
    validator: _MailSemanticValidator,
    label: str,
    service: _RuntimeMailServiceLike,
    observed_paths: set[str],
    local_ids: _MailServiceLocalIds,
) -> None:
    for setting in service.settings:
        setting_label = f"{label} setting '{setting.setting_id}'"
        _verify_mail_ref(
            validator,
            setting.component_ref,
            local_ids.components,
            label=setting_label,
            field_name="component_ref",
        )
        if _source_path_misses_observed_inventory(validator, setting.source_path, observed_paths):
            validator._err(f"{setting_label} source_path '{setting.source_path}' does not resolve to an observed file")


def _source_path_misses_observed_inventory(
    validator: _MailSemanticValidator,
    source_path: str,
    observed_paths: set[str],
) -> bool:
    return bool(
        source_path
        and observed_paths
        and not validator._is_unresolved_var(source_path)
        and source_path not in observed_paths
    )


def _verify_mail_ref(
    validator: _MailSemanticValidator,
    ref: str,
    local_refs: set[str],
    *,
    label: str,
    field_name: str,
) -> None:
    if not ref or validator._is_unresolved_var(ref):
        return
    if ref not in local_refs:
        validator._err(f"{label} {field_name} '{ref}' does not resolve inside mail service")


def _verify_mail_account_ref(validator: _MailSemanticValidator, ref: str, label: str) -> None:
    if not ref or validator._is_unresolved_var(ref):
        return
    if ref not in validator._s.accounts:
        validator._err(f"{label} account_ref '{ref}' does not resolve to a top-level account")


def _verify_mail_local_user_ref(
    validator: _MailSemanticValidator,
    ref: str,
    local_user_names: set[str],
    label: str,
) -> None:
    if not ref or validator._is_unresolved_var(ref):
        return
    if local_user_names and ref not in local_user_names:
        validator._err(f"{label} local_user_ref '{ref}' does not resolve to a runtime.local_identity user")


def resolve_mail_service_ref(
    validator: _MailSemanticValidator,
    ref: object,
) -> _RuntimeMailServiceLike | None:
    """Resolve a qualified runtime mail-service or child ref to the service."""
    resolved: _RuntimeMailServiceLike | None = None
    split = validator._split_runtime_ref(ref, surface="mail_services")
    if split is not None:
        node_name, tail = split
        parsed_tail = _parse_mail_ref_tail(tail)
        if parsed_tail is not None:
            resolved = _resolve_mail_service_tail(
                _mail_services_for_node_name(validator._s, node_name),
                parsed_tail,
            )
    return resolved


def _mail_services_for_node_name(
    scenario: _ScenarioLike,
    node_name: str,
) -> Sequence[_RuntimeMailServiceLike]:
    node = scenario.nodes.get(node_name)
    return () if node is None else _mail_services_for_node(node)


def _parse_mail_ref_tail(tail: str) -> _MailRefTail | None:
    tail_parts = tail.split(".")
    parsed_tail: _MailRefTail | None = None
    if len(tail_parts) == 1:
        parsed_tail = _MailRefTail(tail_parts[0], "", "")
    elif len(tail_parts) == 3:
        parsed_tail = _MailRefTail(*tail_parts)
    return parsed_tail


def _resolve_mail_service_tail(
    mail_services: Sequence[_RuntimeMailServiceLike],
    parsed_tail: _MailRefTail,
) -> _RuntimeMailServiceLike | None:
    resolved: _RuntimeMailServiceLike | None = None
    for service in mail_services:
        if service.service_id != parsed_tail.service_id:
            continue
        resolved = _matched_service_for_tail(service, parsed_tail)
        break
    return resolved


def _matched_service_for_tail(
    service: _RuntimeMailServiceLike,
    parsed_tail: _MailRefTail,
) -> _RuntimeMailServiceLike | None:
    matches_service = not parsed_tail.collection_name
    matches_child = bool(
        parsed_tail.collection_name
        and _mail_child_ref_exists(service, parsed_tail.collection_name, parsed_tail.child_id)
    )
    return service if matches_service or matches_child else None


def _mail_child_ref_exists(
    service: _RuntimeMailServiceLike,
    collection_name: str,
    child_id: str,
) -> bool:
    read_child_ids = _MAIL_CHILD_ID_READERS.get(collection_name)
    return read_child_ids is not None and child_id in read_child_ids(service)


def verify_relationship_mail_access(validator: _MailSemanticValidator) -> None:
    """Validate typed ``mail_access`` blocks on top-level relationship edges."""
    for name, relationship in validator._s.relationships.items():
        access = relationship.mail_access
        if access is None:
            continue
        label = f"Relationship '{name}'"
        mail_service = _check_mail_access_target(validator, relationship.target, label)
        if mail_service is None:
            continue
        _verify_mail_ref(
            validator,
            access.listener_ref,
            {listener.listener_id for listener in mail_service.listeners},
            label=f"{label} mail_access",
            field_name="listener_ref",
        )
        _verify_mail_ref(
            validator,
            access.mailbox_ref,
            {mailbox.mailbox_id for mailbox in mail_service.mailboxes},
            label=f"{label} mail_access",
            field_name="mailbox_ref",
        )
        _verify_mail_ref(
            validator,
            access.domain_ref,
            {domain.domain_id for domain in mail_service.domains},
            label=f"{label} mail_access",
            field_name="domain_ref",
        )


def _check_mail_access_target(
    validator: _MailSemanticValidator,
    target: str,
    label: str,
) -> _RuntimeMailServiceLike | None:
    mail_service = resolve_mail_service_ref(validator, target)
    if mail_service is not None or validator._is_unresolved_var(target):
        return mail_service
    validator._err(f"{label} has mail_access but target '{target}' does not resolve to a mail service")
    return None
