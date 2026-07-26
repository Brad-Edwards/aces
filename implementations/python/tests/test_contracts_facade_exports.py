"""Public-surface checks for the contracts package facade."""

import raes_contracts.contracts as contracts_facade
from raes_contracts.contracts._exports import PUBLIC_EXPORTS


def test_contracts_facade_matches_export_manifest() -> None:
    assert contracts_facade.__all__ == PUBLIC_EXPORTS
    assert len(PUBLIC_EXPORTS) == len(set(PUBLIC_EXPORTS))
    assert [name for name in PUBLIC_EXPORTS if not hasattr(contracts_facade, name)] == []
