"""Validation for the paper demonstration corpus artifact (issue #600).

Enforces the corpus contract without forking the libvirt paper validator: it reuses
the shared ``redaction_violations`` gate and asserts the n=2 backend-pairing
invariants that make the corpus a demonstration corpus rather than a single run --
exactly two distinct backend runs keyed to one authored scenario digest, and a
four-section invariant ledger present. It does not re-implement contract validation
that the libvirt producer already performed on its own artifact.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aces_operations._paper_evidence_validation import redaction_violations

CORPUS_SCHEMA = "aces.paper-demonstration-corpus/v1"

_REQUIRED_SECTIONS: tuple[str, ...] = (
    "authored_scenario",
    "backend_runs",
    "invariant_ledger",
    "non_claims",
    "redaction_provenance",
    "links",
)

_REQUIRED_LEDGER_SECTIONS: tuple[str, ...] = (
    "preserved_invariants",
    "realization_differences",
    "unsupported_or_degraded_surfaces",
    "evidence_limitations",
)


def _authored_digest(payload: Mapping[str, Any]) -> str:
    scenario = payload.get("authored_scenario")
    return str(scenario.get("content_sha256", "")) if isinstance(scenario, Mapping) else ""


def _run_digest(run: Mapping[str, Any]) -> str:
    scenario = run.get("scenario")
    return str(scenario.get("content_sha256", "")) if isinstance(scenario, Mapping) else ""


def _check_run_digests(runs: list[Any], authored_digest: str) -> list[str]:
    problems: list[str] = []
    for index, run in enumerate(runs):
        if not isinstance(run, Mapping):
            problems.append(f"backend_runs[{index}] must be an object")
            continue
        run_digest = _run_digest(run)
        if authored_digest and run_digest != authored_digest:
            problems.append(
                f"backend_runs[{index}] ({run.get('backend_id')}) scenario digest {run_digest!r} "
                f"does not match the authored scenario digest {authored_digest!r}"
            )
    return problems


def _validate_backend_runs(payload: Mapping[str, Any]) -> list[str]:
    runs = payload.get("backend_runs")
    if not isinstance(runs, list):
        return ["backend_runs must be a list"]
    if len(runs) != 2:
        return [f"backend_runs must contain exactly two backend realizations (n=2), found {len(runs)}"]

    problems: list[str] = []
    backend_ids = [str(run.get("backend_id")) for run in runs if isinstance(run, Mapping)]
    if len(set(backend_ids)) != 2:
        problems.append(f"the two backend runs must have distinct backend_ids, found {backend_ids}")
    authored_digest = _authored_digest(payload)
    if not authored_digest:
        problems.append("authored_scenario.content_sha256 is missing")
    problems.extend(_check_run_digests(runs, authored_digest))
    return problems


def _validate_ledger(payload: Mapping[str, Any]) -> list[str]:
    ledger = payload.get("invariant_ledger")
    if not isinstance(ledger, Mapping):
        return ["invariant_ledger must be an object"]
    return [
        f"invariant_ledger missing section: {section}" for section in _REQUIRED_LEDGER_SECTIONS if section not in ledger
    ]


def validate_paper_demonstration_corpus_artifact(payload: Mapping[str, Any]) -> list[str]:
    """Validate a corpus artifact: schema, required sections, n=2 pairing, ledger, redaction.

    Returns a list of human-readable violation strings; an empty list means valid.
    """
    problems: list[str] = []
    if payload.get("schema") != CORPUS_SCHEMA:
        problems.append(f"schema must be {CORPUS_SCHEMA!r}")
    problems.extend(f"missing required section: {section}" for section in _REQUIRED_SECTIONS if section not in payload)
    problems.extend(_validate_backend_runs(payload))
    problems.extend(_validate_ledger(payload))
    problems.extend(redaction_violations(payload))
    return problems
