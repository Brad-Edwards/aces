"""Concern-owned explicitness selection for realization compilation."""

from __future__ import annotations

import re
from collections.abc import Mapping

from raes.explicitness import ExplicitnessClass, ExplicitnessProvenance, ExplicitnessRecord

_PATH_TOKEN_RE = re.compile(r"[^.\[\]]+")
_RANK = {
    ExplicitnessClass.OPEN: 0,
    ExplicitnessClass.CONSTRAINED: 1,
    ExplicitnessClass.EXACT: 2,
}


def semantic_explicitness_record(
    explicitness: Mapping[str, ExplicitnessRecord],
    *,
    field_path: str,
    excluded_fields: frozenset[str],
) -> ExplicitnessRecord | None:
    """Classify only authored leaves owned by one realization concern."""

    candidates = {
        path: record
        for path, record in explicitness.items()
        if (path == field_path or path.startswith((f"{field_path}.", f"{field_path}[")))
        and not excluded_fields.intersection(_PATH_TOKEN_RE.findall(path[len(field_path) :]))
    }
    if not candidates:
        return None
    leaf_records = [
        record
        for path, record in candidates.items()
        if not any(other != path and other.startswith((f"{path}.", f"{path}[")) for other in candidates)
    ]
    weakest = min(leaf_records, key=lambda item: _RANK[item.classification])
    variables = tuple(sorted({name for item in leaf_records for name in item.variables}))
    provenance = (
        ExplicitnessProvenance.PROCESSOR_DERIVED
        if any(item.provenance is ExplicitnessProvenance.PROCESSOR_DERIVED for item in leaf_records)
        else ExplicitnessProvenance.AUTHOR_DECLARED
    )
    return ExplicitnessRecord(
        path=field_path,
        classification=weakest.classification,
        provenance=provenance,
        reason="derived from realization-owned authored leaves",
        variables=variables,
    )


__all__ = ["semantic_explicitness_record"]
