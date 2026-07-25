"""Validation for the libvirt scenario-evidence artifact.

Re-validates the embedded published-contract payloads, enforces the redaction gate
(no raw libvirt XML, domain UUIDs, QEMU command lines, host paths, connection URIs,
credentials, or private keys), and checks the participant/evaluator boundary
invariant. Split from ``libvirt_evidence_run`` to keep each module under the
ADR-015 source-size cap.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from raes_contracts.contracts import (
    BackendManifestV2Model,
    EvaluationHistoryEventModel,
    EvaluationResultStateModel,
    ExperimentRealizedFormDisclosureModel,
)
from pydantic import BaseModel

from raes_operations._evidence_run_artifact import EVIDENCE_RUN_SCHEMA
from raes_operations._evidence_run_realization import _validate_realization_sources

# Redaction gate: substrings/patterns that must never appear in the artifact.
_FORBIDDEN_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key material"),
    (re.compile(r"</?domain[\s>]"), "raw libvirt domain XML"),
    (re.compile(r"</?devices>"), "raw libvirt device XML"),
    (re.compile(r"qemu-system-\w+"), "QEMU command line"),
    (re.compile(r"qemu-kvm"), "QEMU command line"),
    (re.compile(r"(?i)\bpassword\b\s*[:=]"), "embedded credential"),
    (re.compile(r"(?i)\bsecret\b\s*[:=]"), "embedded credential"),
    (re.compile(r"/home/[A-Za-z0-9._-]+/"), "host home path"),
    (re.compile(r"/var/lib/libvirt"), "libvirt host state path"),
    (re.compile(r"/root/"), "host root path"),
    (re.compile(r"qemu\+ssh://|qemu://[^/]"), "libvirt connection URI with host"),
    (
        re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),
        "domain UUID as portable semantics",
    ),
)

_REQUIRED_SECTIONS = (
    "scenario",
    "compiled_artifact",
    "backend",
    "realization_facts",
    "realized_topology",
    "participant_action_proof",
    "terminal_observation",
    "defensive_evidence",
    "negative_boundary_checks",
    "evaluator_outcome",
    "realized_form_disclosures",
    "limitations",
    "non_claims",
    "redaction_provenance",
    "invariant_ledger_refs",
)


def validate_libvirt_evidence_run_artifact(payload: Mapping[str, Any]) -> list[str]:
    """Validate a scenario-evidence artifact: schema, required surfaces, embedded contracts, redaction, boundary.

    Returns a list of human-readable violation strings; an empty list means the
    artifact is valid.
    """
    problems: list[str] = []
    if payload.get("schema") != EVIDENCE_RUN_SCHEMA:
        problems.append(f"schema must be {EVIDENCE_RUN_SCHEMA!r}")
    for section in _REQUIRED_SECTIONS:
        if section not in payload:
            problems.append(f"missing required section: {section}")

    problems.extend(_validate_embedded_contracts(payload))
    problems.extend(_validate_redaction(payload))
    problems.extend(_validate_boundary(payload))
    problems.extend(_validate_realization_sources(payload))
    return problems


def _try_validate(model_cls: type[BaseModel], value: object, label: str) -> list[str]:
    """Validate ``value`` against ``model_cls``; return a one-item problem list on failure."""
    try:
        model_cls.model_validate(value)
    except Exception as exc:
        return [f"{label}: {exc}"]
    return []


def _validate_backend_manifest(payload: Mapping[str, Any]) -> list[str]:
    backend = payload.get("backend", {})
    if not isinstance(backend, Mapping):
        return []
    return _try_validate(
        BackendManifestV2Model,
        backend.get("manifest", {}),
        "backend.manifest is not a valid BackendManifestV2Model",
    )


def _validate_evaluator_outcome(payload: Mapping[str, Any]) -> list[str]:
    outcome = payload.get("evaluator_outcome", {})
    if not isinstance(outcome, Mapping):
        return []
    problems = _try_validate(
        EvaluationResultStateModel,
        outcome.get("result", {}),
        "evaluator_outcome.result is not a valid EvaluationResultStateModel",
    )
    for index, event in enumerate(outcome.get("history", []) or []):
        problems.extend(
            _try_validate(EvaluationHistoryEventModel, event, f"evaluator_outcome.history[{index}] invalid")
        )
    return problems


def _validate_disclosures(payload: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    for index, disclosure in enumerate(payload.get("realized_form_disclosures", []) or []):
        problems.extend(
            _try_validate(
                ExperimentRealizedFormDisclosureModel, disclosure, f"realized_form_disclosures[{index}] invalid"
            )
        )
    return problems


def _validate_embedded_contracts(payload: Mapping[str, Any]) -> list[str]:
    return [
        *_validate_backend_manifest(payload),
        *_validate_evaluator_outcome(payload),
        *_validate_disclosures(payload),
    ]


def redaction_violations(payload: Mapping[str, Any]) -> list[str]:
    """Return redaction-gate violations for any JSON-serializable artifact payload.

    Shared by the libvirt scenario-evidence validator and the issue #600 corpus
    validator so both enforce one redaction gate rather than a forked copy (no raw
    libvirt XML, domain UUIDs, QEMU command lines, host paths, connection URIs,
    credentials, or private keys).
    """
    blob = json.dumps(payload, sort_keys=True, default=str)
    return [
        f"redaction violation: {label} present in artifact"
        for pattern, label in _FORBIDDEN_REDACTION_PATTERNS
        if pattern.search(blob)
    ]


def _validate_redaction(payload: Mapping[str, Any]) -> list[str]:
    return redaction_violations(payload)


def _validate_boundary(payload: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    proof = payload.get("participant_action_proof", {})
    exposed: set[str] = set()
    if isinstance(proof, Mapping):
        exposed.update(proof.get("participant_visible_refs", []) or [])
        exposed.update(proof.get("participant_disclosed_refs", []) or [])
    boundary = payload.get("negative_boundary_checks", {})
    if isinstance(boundary, Mapping):
        for check in boundary.get("checks", []) or []:
            if isinstance(check, Mapping) and check.get("ref") in exposed:
                problems.append(f"boundary violation: internal ref {check.get('ref')!r} is exposed to the participant")
    return problems
