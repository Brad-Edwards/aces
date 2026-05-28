"""Semantic validation helpers for runtime mail-service inventories."""

from __future__ import annotations

from typing import Any

_NODES_PREFIX = "nodes."
_MAIL_SERVICE_COLLECTION_IDS: tuple[tuple[str, str], ...] = (
    ("components", "component_id"),
    ("listeners", "listener_id"),
    ("domains", "domain_id"),
    ("mailbox_stores", "store_id"),
    ("mailboxes", "mailbox_id"),
    ("aliases", "alias_id"),
    ("routing_rules", "rule_id"),
    ("queues", "queue_id"),
    ("settings", "setting_id"),
)


def collect_qualified_mail_refs(scenario: Any) -> set[str]:
    """Return targetable refs for runtime mail services and stable children."""
    refs: set[str] = set()
    for node_name, node in scenario.nodes.items():
        runtime = getattr(node, "runtime", None)
        if runtime is None:
            continue
        for service in runtime.mail_services:
            base = f"{_NODES_PREFIX}{node_name}.runtime.mail_services.{service.service_id}"
            refs.add(base)
            for collection_name, id_field in _MAIL_SERVICE_COLLECTION_IDS:
                for item in getattr(service, collection_name):
                    item_id = getattr(item, id_field, "")
                    if item_id:
                        refs.add(f"{base}.{collection_name}.{item_id}")
    return refs


def verify_runtime_mail_services(validator: Any) -> None:
    """Validate runtime mail-service inventories against the scenario graph."""
    for node_name, node in validator._s.nodes.items():
        runtime = getattr(node, "runtime", None)
        if runtime is None or not runtime.mail_services:
            continue
        service_names = validator._node_service_names(node)
        observed_paths = validator._node_observed_paths(node)
        local_user_names = validator._node_local_user_names(node)
        for service in runtime.mail_services:
            label = f"Node '{node_name}' runtime mail service '{service.service_id}'"
            validator._verify_owned_service_ref(
                node_name,
                getattr(service, "service", ""),
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
    validator: Any,
    *,
    node_name: str,
    label: str,
    service: Any,
    service_names: set[str],
    observed_paths: set[str],
    local_user_names: set[str],
) -> None:
    component_ids = {component.component_id for component in service.components}
    domain_ids = {domain.domain_id for domain in service.domains}
    store_ids = {store.store_id for store in service.mailbox_stores}
    mailbox_ids = {mailbox.mailbox_id for mailbox in service.mailboxes}
    alias_ids = {alias.alias_id for alias in service.aliases}
    routing_refs = mailbox_ids | alias_ids | domain_ids

    for listener in service.listeners:
        listener_label = f"{label} listener '{listener.listener_id}'"
        validator._verify_owned_service_ref(
            node_name,
            getattr(listener, "service", ""),
            service_names,
            owner_label=listener_label,
        )
        _verify_mail_ref(
            validator, listener.component_ref, component_ids, label=listener_label, field_name="component_ref"
        )

    for mailbox in service.mailboxes:
        mailbox_label = f"{label} mailbox '{mailbox.mailbox_id}'"
        _verify_mail_ref(validator, mailbox.domain_ref, domain_ids, label=mailbox_label, field_name="domain_ref")
        _verify_mail_ref(validator, mailbox.store_ref, store_ids, label=mailbox_label, field_name="store_ref")
        _verify_mail_account_ref(validator, mailbox.account_ref, mailbox_label)
        _verify_mail_local_user_ref(validator, mailbox.local_user_ref, local_user_names, mailbox_label)

    for alias in service.aliases:
        alias_label = f"{label} alias '{alias.alias_id}'"
        _verify_mail_ref(validator, alias.domain_ref, domain_ids, label=alias_label, field_name="domain_ref")
        for target_ref in alias.target_refs:
            _verify_mail_ref(validator, target_ref, mailbox_ids | alias_ids, label=alias_label, field_name="target_ref")

    for rule in service.routing_rules:
        rule_label = f"{label} routing rule '{rule.rule_id}'"
        _verify_mail_ref(validator, rule.source_ref, routing_refs, label=rule_label, field_name="source_ref")
        _verify_mail_ref(validator, rule.target_ref, routing_refs, label=rule_label, field_name="target_ref")

    for setting in service.settings:
        setting_label = f"{label} setting '{setting.setting_id}'"
        _verify_mail_ref(
            validator, setting.component_ref, component_ids, label=setting_label, field_name="component_ref"
        )
        if (
            setting.source_path
            and observed_paths
            and not validator._is_unresolved_var(setting.source_path)
            and setting.source_path not in observed_paths
        ):
            validator._err(f"{setting_label} source_path '{setting.source_path}' does not resolve to an observed file")


def _verify_mail_ref(
    validator: Any,
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


def _verify_mail_account_ref(validator: Any, ref: str, label: str) -> None:
    if not ref or validator._is_unresolved_var(ref):
        return
    if ref not in validator._s.accounts:
        validator._err(f"{label} account_ref '{ref}' does not resolve to a top-level account")


def _verify_mail_local_user_ref(validator: Any, ref: str, local_user_names: set[str], label: str) -> None:
    if not ref or validator._is_unresolved_var(ref):
        return
    if local_user_names and ref not in local_user_names:
        validator._err(f"{label} local_user_ref '{ref}' does not resolve to a runtime.local_identity user")


def resolve_mail_service_ref(validator: Any, ref: object) -> Any | None:
    """Resolve a qualified runtime mail-service or child ref to the service."""
    split = validator._split_runtime_ref(ref, surface="mail_services")
    if split is None:
        return None
    node_name, tail = split
    node = validator._s.nodes.get(node_name)
    runtime = getattr(node, "runtime", None) if node is not None else None
    if runtime is None:
        return None

    tail_parts = tail.split(".")
    if len(tail_parts) == 1:
        service_id = tail_parts[0]
        collection_name = child_id = ""
    elif len(tail_parts) == 3:
        service_id, collection_name, child_id = tail_parts
    else:
        return None

    for service in runtime.mail_services:
        if service.service_id != service_id:
            continue
        if not collection_name:
            return service
        if _mail_child_ref_exists(service, collection_name, child_id):
            return service
        return None
    return None


def _mail_child_ref_exists(service: Any, collection_name: str, child_id: str) -> bool:
    for known_collection, id_field in _MAIL_SERVICE_COLLECTION_IDS:
        if collection_name != known_collection:
            continue
        return any(getattr(item, id_field, "") == child_id for item in getattr(service, collection_name))
    return False


def verify_relationship_mail_access(validator: Any) -> None:
    """Validate typed ``mail_access`` blocks on top-level relationship edges."""
    for name, relationship in validator._s.relationships.items():
        access = getattr(relationship, "mail_access", None)
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


def _check_mail_access_target(validator: Any, target: str, label: str) -> Any | None:
    mail_service = resolve_mail_service_ref(validator, target)
    if mail_service is not None or validator._is_unresolved_var(target):
        return mail_service
    validator._err(f"{label} has mail_access but target '{target}' does not resolve to a mail service")
    return None
