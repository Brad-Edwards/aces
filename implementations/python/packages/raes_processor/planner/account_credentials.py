"""Processor-owned validation for direct account credential plan payloads."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import ValidationError
from raes.accounts import Account, account_credential_binding_issues


def account_credential_spec_is_valid(spec: Mapping[str, object]) -> bool:
    """Return whether a direct-plan spec satisfies the canonical SDL account contract."""

    try:
        account = Account.model_validate(dict(spec))
    except ValidationError:
        return False
    return not account_credential_binding_issues(account)


__all__ = ["account_credential_spec_is_valid"]
