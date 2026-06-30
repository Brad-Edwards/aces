"""Validation for the libvirt paper-evidence artifact.

Re-validates the embedded published-contract payloads, enforces the redaction gate
(no raw libvirt XML, domain UUIDs, QEMU command lines, host paths, connection URIs,
credentials, or private keys), and checks the participant/evaluator boundary
invariant. Split from ``libvirt_paper_evidence`` to keep each module under the
ADR-015 source-size cap.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from aces_contracts.contracts import (
    BackendManifestV2Model,
    EvaluationHistoryEventModel,
    EvaluationResultStateModel,
    ExperimentRealizedFormDisclosureModel,
)

from aces_operations._paper_evidence_artifact import EVIDENCE_RUN_SCHEMA

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


def validate_libvirt_paper_evidence_artifact(payload: Mapping[str, Any]) -> list[str]:
    """Validate a paper-evidence artifact: schema, required surfaces, embedded contracts, redaction, boundary.

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
    return problems


def _validate_embedded_contracts(payload: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    backend = payload.get("backend", {})
    if isinstance(backend, Mapping):
        try:
            BackendManifestV2Model.model_validate(backend.get("manifest", {}))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"backend.manifest is not a valid BackendManifestV2Model: {exc}")
    outcome = payload.get("evaluator_outcome", {})
    if isinstance(outcome, Mapping):
        try:
            EvaluationResultStateModel.model_validate(outcome.get("result", {}))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"evaluator_outcome.result is not a valid EvaluationResultStateModel: {exc}")
        for index, event in enumerate(outcome.get("history", []) or []):
            try:
                EvaluationHistoryEventModel.model_validate(event)
            except Exception as exc:  # noqa: BLE001
                problems.append(f"evaluator_outcome.history[{index}] invalid: {exc}")

    for index, disclosure in enumerate(payload.get("realized_form_disclosures", []) or []):
        try:
            ExperimentRealizedFormDisclosureModel.model_validate(disclosure)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"realized_form_disclosures[{index}] invalid: {exc}")
    return problems


def _validate_redaction(payload: Mapping[str, Any]) -> list[str]:
    blob = json.dumps(payload, sort_keys=True, default=str)
    return [
        f"redaction violation: {label} present in artifact"
        for pattern, label in _FORBIDDEN_REDACTION_PATTERNS
        if pattern.search(blob)
    ]


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
