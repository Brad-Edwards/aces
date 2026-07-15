"""Participant-local interactive-access semantic analysis (DSL-117)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ._domain_topology_types import resolve_section_ref


@dataclass(frozen=True)
class ParticipantInteractiveAccessIssue:
    """One fail-closed authored interactive-access invariant violation."""

    code: str
    message: str


def _concrete_channel(value: object, *, is_unresolved: Callable[[object], bool]) -> str | None:
    if is_unresolved(value):
        return None
    channel = getattr(value, "value", value)
    return channel if isinstance(channel, str) else None


def analyze_participant_interactive_access(
    *,
    agents_by_name: Mapping[str, object],
    nodes: Mapping[str, object],
    accounts: Mapping[str, object],
    is_vm_node: Callable[[str], bool],
    is_unresolved: Callable[[object], bool],
) -> tuple[ParticipantInteractiveAccessIssue, ...]:
    """Evaluate resolution, authority, and uniqueness for every participant."""

    issues: list[ParticipantInteractiveAccessIssue] = []
    for participant_name, agent in agents_by_name.items():
        seen_endpoints: dict[tuple[str, str], str] = {}
        starting_refs = tuple(getattr(agent, "starting_accounts", ()))
        unresolved_starting_ref = any(is_unresolved(ref) for ref in starting_refs)
        starting_accounts = {
            resolved
            for ref in starting_refs
            if not is_unresolved(ref) and (resolved := resolve_section_ref(ref, "accounts", accounts)) is not None
        }
        for access_id, access in getattr(agent, "interactive_access", {}).items():
            label = f"Agent '{participant_name}' interactive_access '{access_id}'"
            target_ref = getattr(access, "target_ref", "")
            target_name = None
            if not is_unresolved(target_ref):
                target_name = resolve_section_ref(target_ref, "nodes", nodes)
                if target_name is None:
                    issues.append(
                        ParticipantInteractiveAccessIssue(
                            code="participant.interactive-access-target-unbound",
                            message=f"{label} target_ref '{target_ref}' does not reference a declared VM node",
                        )
                    )
                elif not is_vm_node(target_name):
                    issues.append(
                        ParticipantInteractiveAccessIssue(
                            code="participant.interactive-access-target-not-vm",
                            message=f"{label} target_ref '{target_ref}' must reference a VM node",
                        )
                    )

            account_ref = getattr(access, "account_ref", None)
            if account_ref is not None and not is_unresolved(account_ref):
                account_name = resolve_section_ref(account_ref, "accounts", accounts)
                if account_name is None:
                    issues.append(
                        ParticipantInteractiveAccessIssue(
                            code="participant.interactive-access-account-unbound",
                            message=f"{label} account_ref '{account_ref}' does not reference a declared account",
                        )
                    )
                else:
                    account_node_ref = getattr(accounts[account_name], "node", "")
                    account_node = (
                        None
                        if is_unresolved(account_node_ref)
                        else resolve_section_ref(account_node_ref, "nodes", nodes)
                    )
                    if target_name is not None and account_node is not None and account_node != target_name:
                        issues.append(
                            ParticipantInteractiveAccessIssue(
                                code="participant.interactive-access-account-node-mismatch",
                                message=(
                                    f"{label} account_ref '{account_ref}' belongs to node '{account_node}', "
                                    f"not target '{target_name}'"
                                ),
                            )
                        )
                    if account_name not in starting_accounts and not unresolved_starting_ref:
                        issues.append(
                            ParticipantInteractiveAccessIssue(
                                code="participant.interactive-access-account-not-starting",
                                message=f"{label} account_ref '{account_ref}' is not in starting_accounts",
                            )
                        )

            channel = _concrete_channel(getattr(access, "channel", None), is_unresolved=is_unresolved)
            if target_name is None or not is_vm_node(target_name) or channel is None:
                continue
            endpoint_key = (target_name, channel)
            first_access_id = seen_endpoints.get(endpoint_key)
            if first_access_id is not None:
                issues.append(
                    ParticipantInteractiveAccessIssue(
                        code="participant.interactive-access-duplicate-endpoint",
                        message=(
                            f"{label} duplicates interactive_access target/channel "
                            f"'{target_name}'/'{channel}' declared by '{first_access_id}'"
                        ),
                    )
                )
            else:
                seen_endpoints[endpoint_key] = access_id
    return tuple(issues)


__all__ = ["ParticipantInteractiveAccessIssue", "analyze_participant_interactive_access"]
