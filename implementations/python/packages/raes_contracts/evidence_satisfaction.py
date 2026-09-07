"""Content-backed post-run evidence satisfaction validation."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import BinaryIO

from jsonschema import Draft202012Validator

from .contracts import (
    ExperimentArtifactRefModel,
    ExperimentCaptureRequirementModel,
    ExperimentCaptureSpecModel,
    ExperimentEvidenceRecordModel,
    ExperimentEvidenceReferenceModel,
    ExperimentRunModel,
    ExperimentTaskModel,
    schema_bundle,
    validate_experiment_run_structure_against_task,
)
from .contracts.base import _parse_rfc3339_datetime
from .evidence_output_validation import validate_evidence_output_contract
from .json_ingress import JSONValue, parse_bounded_json, parse_bounded_json_object

_CHUNK_SIZE = 64 * 1024
_MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class _ValidatedEvidenceBinding:
    """A requirement-to-record-to-artifact relation created only after proof."""

    requirement_id: str
    record: ExperimentEvidenceRecordModel
    artifact: ExperimentArtifactRefModel


def _read_payload(reader: BinaryIO, *, size: int, algorithm: str) -> tuple[bytes, str]:
    if size > _MAX_ARTIFACT_BYTES:
        raise ValueError("evidence artifact exceeds the bounded validation limit")
    try:
        digest = hashlib.new(algorithm)
    except ValueError as exc:
        raise ValueError("evidence artifact checksum algorithm is unsupported") from exc
    chunks: list[bytes] = []
    total = 0
    while total <= size:
        chunk = reader.read(min(_CHUNK_SIZE, size + 1 - total))
        if not isinstance(chunk, bytes):
            raise ValueError("evidence artifact reader must return bytes")
        if not chunk:
            break
        chunks.append(chunk)
        digest.update(chunk)
        total += len(chunk)
    if total != size:
        raise ValueError("evidence artifact bytes do not match the declared size")
    return b"".join(chunks), digest.hexdigest()


def _json_pointer_resolves(document: object, pointer: str) -> bool:
    if pointer == "":
        return True
    current = document
    for encoded in pointer.removeprefix("/").split("/"):
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return False
    return True


def _artifact_for_record(
    run: ExperimentRunModel,
    record: ExperimentEvidenceRecordModel,
) -> ExperimentArtifactRefModel:
    raw_content = record.raw_content
    candidates = []
    if raw_content.artifact_ref is not None:
        candidates = [
            artifact
            for artifact in run.evidence_artifacts
            if artifact.artifact_id == raw_content.artifact_ref.artifact_id
        ]
    elif raw_content.content_uri is not None and raw_content.content_checksum is not None:
        candidates = [
            artifact
            for artifact in run.evidence_artifacts
            if artifact.uri == raw_content.content_uri
            and artifact.checksum.algorithm == raw_content.content_checksum.algorithm
            and artifact.checksum.value.casefold() == raw_content.content_checksum.value.casefold()
        ]
    if len(candidates) != 1:
        raise ValueError("evidence record must resolve to exactly one emitted run artifact")
    if raw_content.artifact_ref is not None and raw_content.artifact_ref != candidates[0]:
        raise ValueError("evidence record artifact_ref does not match the emitted run artifact")
    return candidates[0]


def _validate_record_binding(
    *,
    task: ExperimentTaskModel,
    run: ExperimentRunModel,
    capture_spec: ExperimentCaptureSpecModel,
    requirement: ExperimentCaptureRequirementModel,
    record: ExperimentEvidenceRecordModel,
) -> None:
    if (
        record.capture_spec_ref.ref_id != capture_spec.capture_spec_id
        or record.capture_spec_ref.ref_version != capture_spec.spec_version
    ):
        raise ValueError("evidence record capture_spec_ref does not match the supplied capture spec")
    if record.capture_requirement_ref != requirement.requirement_id:
        raise ValueError("evidence record capture_requirement_ref does not match the capture requirement")
    if record.output_contract != requirement.output_contract:
        raise ValueError("evidence record output_contract does not match the admitted capture requirement")
    if record.run_ref.ref_id != run.run_id or (
        record.run_ref.ref_version is not None and record.run_ref.ref_version != run.run_version
    ):
        raise ValueError("evidence record run_ref does not match the experiment run")
    if record.task_ref is not None and (
        record.task_ref.ref_id != task.task_id or record.task_ref.ref_version != task.task_version
    ):
        raise ValueError("evidence record task_ref does not match the experiment task")
    if record.evidence_kind != requirement.capture_kind:
        raise ValueError("evidence record kind does not match the capture requirement")
    if record.capture_window_ref not in requirement.window_refs:
        raise ValueError("evidence record capture window does not match the capture requirement")
    matching_windows = [
        window for window in capture_spec.capture_windows if window.window_id == record.capture_window_ref
    ]
    if len(matching_windows) != 1:
        raise ValueError("evidence record capture window must resolve exactly in the supplied capture spec")
    window = matching_windows[0]
    captured_at = _parse_rfc3339_datetime("captured_at", record.captured_at)
    starts_at = _parse_rfc3339_datetime("starts_at", window.starts_at) if window.starts_at is not None else None
    ends_at = _parse_rfc3339_datetime("ends_at", window.ends_at) if window.ends_at is not None else None
    if window.window_kind in {"run", "task"}:
        run_starts_at = _parse_rfc3339_datetime("started_at", run.started_at)
        run_ends_at = _parse_rfc3339_datetime("ended_at", run.ended_at)
        starts_at = max(value for value in (starts_at, run_starts_at) if value is not None)
        ends_at = min(value for value in (ends_at, run_ends_at) if value is not None)
    elif window.window_kind == "interval" and (starts_at is None or ends_at is None):
        raise ValueError("interval capture window timing cannot be proved without both bounds")
    elif starts_at is None and ends_at is None:
        raise ValueError("capture window timing cannot be proved from the supplied evidence")
    if starts_at is not None and captured_at < starts_at:
        raise ValueError("evidence was captured before the admitted capture window")
    if ends_at is not None and captured_at > ends_at:
        raise ValueError("evidence was captured after the admitted capture window")
    if record.sensitivity != requirement.sensitivity:
        raise ValueError("evidence record sensitivity does not match the capture requirement")
    if record.redaction_state == "withheld":
        raise ValueError("withheld evidence cannot satisfy a required capture")
    requires_redaction = requirement.redaction_policy is not None or requirement.sensitivity == "redacted"
    expected_redaction_state = "redacted" if requires_redaction else "none"
    if record.redaction_state != expected_redaction_state:
        if requires_redaction:
            raise ValueError("required evidence redaction policy was not applied")
        raise ValueError("redacted evidence is not permitted by the capture requirement")
    if record.redaction_policy != requirement.redaction_policy:
        raise ValueError("evidence record redaction policy does not match the capture requirement")
    if record.redaction_policy is not None:
        raise ValueError("the governed redaction policy has no content verifier")
    if record.raw_content.loss_disclosure is not None and record.redaction_state == "none":
        raise ValueError("lossy evidence cannot satisfy a required complete capture")
    required_source = requirement.channel_ref
    if not any(
        source.ref_kind == required_source.ref_kind
        and source.ref_id == required_source.ref_id
        and (required_source.ref_version is None or source.ref_version == required_source.ref_version)
        for source in record.source_refs
    ):
        raise ValueError("evidence record source does not match the admitted measurement channel")


def _parse_contract_document(payload: bytes, *, media_type: str, output_contract: str) -> JSONValue:
    schema = schema_bundle().get(output_contract)
    if schema is None:
        raise ValueError("evidence output_contract is not present in the authoritative contract registry")
    root = schema.get("type")
    if root not in {"object", "array"}:
        raise ValueError("evidence output_contract does not declare a supported JSON root")
    try:
        if media_type == "application/json":
            document = parse_bounded_json(payload, max_bytes=_MAX_ARTIFACT_BYTES, root=root)
        elif media_type == "application/jsonl":
            if root != "array":
                raise ValueError("JSON Lines evidence requires an array-root output_contract")
            lines = payload.splitlines()
            if not lines or any(not line.strip() for line in lines):
                raise ValueError("JSON Lines evidence must contain non-empty object records")
            document = [parse_bounded_json_object(line, max_bytes=_MAX_ARTIFACT_BYTES) for line in lines]
        else:
            raise ValueError("evidence media type cannot be validated against the declared JSON output_contract")
    except ValueError as exc:
        raise ValueError("emitted evidence does not satisfy the declared output_contract") from exc
    if next(Draft202012Validator(schema).iter_errors(document), None) is not None:
        raise ValueError("emitted evidence does not satisfy the declared output_contract")
    validate_evidence_output_contract(output_contract, document)
    return document


def _validate_artifact_content(
    requirement: ExperimentCaptureRequirementModel,
    record: ExperimentEvidenceRecordModel,
    artifact: ExperimentArtifactRefModel,
    reader: BinaryIO | None,
) -> None:
    if reader is None:
        raise ValueError("required emitted evidence has no concrete byte reader")
    if requirement.required_artifact_roles and artifact.role not in requirement.required_artifact_roles:
        raise ValueError("emitted evidence artifact role does not match the capture requirement")
    if artifact.media_type not in requirement.expected_media_types:
        raise ValueError("emitted evidence media type does not match the capture requirement")
    if artifact.sensitivity != requirement.sensitivity or artifact.sensitivity != record.sensitivity:
        raise ValueError("emitted evidence artifact sensitivity does not match the validated capture record")
    payload, checksum = _read_payload(
        reader,
        size=artifact.size_bytes,
        algorithm=artifact.checksum.algorithm,
    )
    if checksum.casefold() != artifact.checksum.value.casefold():
        raise ValueError("emitted evidence checksum does not match the captured bytes")
    for integrity in requirement.integrity_requirements:
        if integrity in {"checksum", "sha256-digest"}:
            if integrity == "sha256-digest" and artifact.checksum.algorithm != "sha256":
                raise ValueError("emitted evidence does not satisfy the required sha256 integrity mode")
        else:
            raise ValueError(f"emitted evidence cannot prove integrity requirement {integrity!r}")
    document = _parse_contract_document(
        payload,
        media_type=artifact.media_type,
        output_contract=requirement.output_contract,
    )
    missing = sorted(
        selector for selector in requirement.field_selectors if not _json_pointer_resolves(document, selector)
    )
    if missing:
        raise ValueError("emitted evidence is missing required field selector(s): " + ", ".join(missing))


def _binding_satisfies_reference(
    binding: _ValidatedEvidenceBinding,
    reference: ExperimentEvidenceReferenceModel,
) -> bool:
    if reference.ref_version is not None and reference.ref_version != binding.record.record_version:
        return False
    if reference.ref_digest is not None:
        artifact_digest = f"{binding.artifact.checksum.algorithm}:{binding.artifact.checksum.value}"
        if artifact_digest.casefold() != reference.ref_digest.casefold():
            return False
    return reference.ref_path is None or binding.artifact.uri == reference.ref_path


def _validate_task_evidence_bindings(
    task: ExperimentTaskModel,
    run: ExperimentRunModel,
    bindings: Mapping[str, _ValidatedEvidenceBinding],
) -> None:
    missing_observations = sorted(
        reference.ref_id
        for reference in task.evaluation_protocol.observation_requirements
        if (binding := bindings.get(reference.ref_id)) is None or not _binding_satisfies_reference(binding, reference)
    )
    if missing_observations:
        raise ValueError(
            "validated evidence bindings do not satisfy task observation requirements: "
            + ", ".join(missing_observations)
        )

    missing_metric_evidence: list[str] = []
    for result_id, result in run.result_summaries.items():
        result_artifact_ids = {reference.ref_id for reference in result.evidence_refs}
        metric = task.evaluation_protocol.metric_definitions[result.metric_id]
        for reference in metric.evidence_requirements:
            binding = bindings.get(reference.ref_id)
            if (
                binding is None
                or binding.artifact.artifact_id not in result_artifact_ids
                or not _binding_satisfies_reference(binding, reference)
            ):
                missing_metric_evidence.append(f"{result_id}:{reference.ref_id}")
    if missing_metric_evidence:
        raise ValueError(
            "run result evidence_refs do not resolve to validated metric evidence bindings: "
            + ", ".join(sorted(missing_metric_evidence))
        )


def validate_experiment_run_evidence(
    task: ExperimentTaskModel,
    run: ExperimentRunModel,
    *,
    capture_specs: Mapping[str, ExperimentCaptureSpecModel],
    evidence_records: Mapping[str, ExperimentEvidenceRecordModel],
    artifact_readers: Mapping[str, BinaryIO],
) -> tuple[ExperimentEvidenceReferenceModel, ...]:
    """Prove task/run evidence claims against exact records and emitted bytes.

    The caller acquires immutable byte streams.  This validator never fetches
    artifact URIs, searches host paths, or treats adapter-authored reference
    identifiers and summaries as evidence.
    """

    validate_experiment_run_structure_against_task(task, run)
    referenced_specs = {(reference.ref_id, reference.ref_version) for reference in run.traceability.capture_spec_refs}
    supplied_specs = {(spec.capture_spec_id, spec.spec_version) for spec in capture_specs.values()}
    if referenced_specs != supplied_specs:
        raise ValueError("run capture_spec_refs must resolve exactly to supplied capture specs")
    referenced_records = {
        (reference.ref_id, reference.ref_version) for reference in run.traceability.evidence_record_refs
    }
    supplied_records = {(record.evidence_record_id, record.record_version) for record in evidence_records.values()}
    if referenced_records != supplied_records:
        raise ValueError("run evidence_record_refs must resolve exactly to supplied evidence records")

    records_by_requirement: dict[tuple[str, str], list[ExperimentEvidenceRecordModel]] = {}
    requirements: dict[str, tuple[ExperimentCaptureSpecModel, ExperimentCaptureRequirementModel]] = {}
    for capture_spec in capture_specs.values():
        for requirement_id, requirement in capture_spec.capture_requirements.items():
            if requirement_id in requirements:
                raise ValueError("capture requirement ids must be unambiguous across supplied capture specs")
            requirements[requirement_id] = (capture_spec, requirement)
    for record in evidence_records.values():
        key = (record.capture_spec_ref.ref_id, record.capture_requirement_ref)
        records_by_requirement.setdefault(key, []).append(record)
    valid_requirement_keys = {
        (capture_spec.capture_spec_id, requirement_id) for requirement_id, (capture_spec, _) in requirements.items()
    }
    if not set(records_by_requirement).issubset(valid_requirement_keys):
        raise ValueError("evidence records must resolve to admitted capture requirements")

    task_requirement_ids = {reference.ref_id for reference in task.evaluation_protocol.observation_requirements} | {
        reference.ref_id
        for metric in task.evaluation_protocol.metric_definitions.values()
        for reference in metric.evidence_requirements
    }
    unresolved = sorted(task_requirement_ids - set(requirements))
    if unresolved:
        raise ValueError("task evidence requirements do not resolve to capture requirements: " + ", ".join(unresolved))

    validated_bindings: dict[str, _ValidatedEvidenceBinding] = {}
    for requirement_id in sorted(requirements):
        capture_spec, requirement = requirements[requirement_id]
        records = records_by_requirement.get((capture_spec.capture_spec_id, requirement_id), [])
        if len(records) != 1:
            raise ValueError(f"capture requirement {requirement_id!r} must resolve to exactly one evidence record")
        record = records[0]
        _validate_record_binding(
            task=task,
            run=run,
            capture_spec=capture_spec,
            requirement=requirement,
            record=record,
        )
        artifact = _artifact_for_record(run, record)
        _validate_artifact_content(requirement, record, artifact, artifact_readers.get(artifact.artifact_id))
        validated_bindings[requirement_id] = _ValidatedEvidenceBinding(
            requirement_id=requirement_id,
            record=record,
            artifact=artifact,
        )
    _validate_task_evidence_bindings(task, run, validated_bindings)
    return tuple(
        ExperimentEvidenceReferenceModel(
            ref_kind="evidence",
            ref_id=binding.requirement_id,
            ref_version=binding.record.record_version,
            ref_digest=f"{binding.artifact.checksum.algorithm}:{binding.artifact.checksum.value}",
            ref_path=binding.artifact.uri,
        )
        for binding in validated_bindings.values()
    )


__all__ = ["validate_experiment_run_evidence"]
