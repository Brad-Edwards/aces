"""Validation for the libvirt scenario-evidence artifact.

Re-validates the embedded published-contract payloads, enforces the redaction gate
(no raw libvirt XML, domain UUIDs, QEMU command lines, host paths, connection URIs,
credentials, or private keys), and checks the participant/evaluator boundary
invariant. Split from ``libvirt_evidence_run`` to keep each module under the
ADR-015 source-size cap.
"""

from __future__ import annotations

import hashlib
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
from pydantic import BaseModel

from aces_operations._evidence_run_artifact import EVIDENCE_RUN_SCHEMA

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


def _validate_realization_sources(payload: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    if "native-realized" in json.dumps(payload, sort_keys=True, default=str):
        problems.append("realization source violation: native-realized is not an admitted observation basis")

    facts = payload.get("realization_facts", {})
    if not isinstance(facts, Mapping):
        return [*problems, "realization_facts must be a mapping"]
    expected_sources = {
        "authored": "authored",
        "planned": "planned",
        "driver_reported": "driver-reported",
        "daemon_observed": "daemon-observed",
        "guest_observed": "guest-observed",
    }
    for key, source in expected_sources.items():
        section = facts.get(key)
        if not isinstance(section, Mapping) or section.get("source") != source:
            problems.append(f"realization source violation: {key}.source must be {source!r}")

    topology = payload.get("realized_topology", {})
    if isinstance(topology, Mapping):
        if topology.get("basis") not in {"planned", "mixed-source"}:
            problems.append("realized_topology.basis must be planned or mixed-source")
        for collection in ("nodes", "networks"):
            for item in topology.get(collection, ()) or ():
                if isinstance(item, Mapping) and item.get("source") != "planned":
                    problems.append(f"realization source violation: realized_topology.{collection} is planned")
        native_surface = topology.get("native_surface")
        if isinstance(native_surface, Mapping) and native_surface.get("source") != "daemon-observed":
            problems.append("realization source violation: native_surface must be daemon-observed")

    backend = payload.get("backend", {})
    provenance = backend.get("realization_provenance", {}) if isinstance(backend, Mapping) else {}
    substrate_realized = isinstance(provenance, Mapping) and provenance.get("substrate_realized") is True
    cleanup = facts.get("cleanup")
    if not isinstance(cleanup, Mapping) or cleanup.get("source") != "driver-reported":
        problems.append("realization cleanup must be driver-reported")
    if substrate_realized:
        if provenance.get("basis") != "daemon-observed-substrate":
            problems.append("realization provenance basis must be daemon-observed-substrate")
        cleanup_verified = provenance.get("cleanup_verified")
        expected_cleanup_status = "verified" if cleanup_verified is True else "failed"
        if (
            not isinstance(cleanup_verified, bool)
            or not isinstance(cleanup, Mapping)
            or cleanup.get("status") != expected_cleanup_status
        ):
            problems.append("daemon-observed substrate requires a consistent cleanup outcome")
        daemon = facts.get("daemon_observed", {})
        domains = daemon.get("domains", ()) if isinstance(daemon, Mapping) else ()
        if not isinstance(domains, list | tuple) or not domains:
            problems.append("daemon-observed substrate requires at least one observed domain")
        for collection in ("domains", "networks"):
            for item in daemon.get(collection, ()) if isinstance(daemon, Mapping) else ():
                if isinstance(item, Mapping) and item.get("observation_source") != "daemon-observed":
                    problems.append(f"realization source violation: daemon_observed.{collection} item source")
                if isinstance(item, Mapping):
                    problems.extend(_validate_daemon_observation_item(collection, item))
        daemon_items = [
            item
            for collection in ("domains", "networks")
            for item in (daemon.get(collection, ()) if isinstance(daemon, Mapping) else ())
            if isinstance(item, Mapping)
        ]
        observed_addresses = {item.get("address") for item in daemon_items}
        driver_reported = facts.get("driver_reported", {})
        reported_addresses = (
            driver_reported.get("realized_addresses", ()) if isinstance(driver_reported, Mapping) else ()
        )
        if (
            not isinstance(reported_addresses, list | tuple)
            or not all(isinstance(item, str) for item in reported_addresses)
            or set(reported_addresses) != observed_addresses
        ):
            problems.append("driver-reported addresses do not match daemon observations")
        native_surface = topology.get("native_surface") if isinstance(topology, Mapping) else None
        if not isinstance(native_surface, Mapping):
            problems.append("daemon-observed substrate requires a native surface")
        else:
            for collection in ("domains", "networks"):
                observed_names = sorted(
                    str(item.get("name"))
                    for item in (daemon.get(collection, ()) if isinstance(daemon, Mapping) else ())
                    if isinstance(item, Mapping)
                )
                surface_names = native_surface.get(collection, ())
                if (
                    not isinstance(surface_names, list | tuple)
                    or sorted(str(item) for item in surface_names) != observed_names
                ):
                    problems.append(f"native surface {collection} do not match daemon observations")
        problems.extend(_validate_realization_binding(backend, facts))
    elif isinstance(provenance, Mapping) and provenance.get("basis") != "planned-not-realized":
        problems.append("unrealized substrate basis must be planned-not-realized")
    else:
        daemon = facts.get("daemon_observed", {})
        daemon_domains = daemon.get("domains", ()) if isinstance(daemon, Mapping) else ()
        daemon_networks = daemon.get("networks", ()) if isinstance(daemon, Mapping) else ()
        if daemon_domains or daemon_networks or facts.get("binding") is not None:
            problems.append("unrealized substrate cannot publish daemon observations or realization binding")
        if isinstance(provenance, Mapping) and provenance.get("cleanup_verified") is not None:
            problems.append("unrealized substrate cleanup must be not-applicable")
        if isinstance(cleanup, Mapping) and cleanup.get("status") != "not-required":
            problems.append("unrealized substrate cleanup status must be not-required")

    defensive = payload.get("defensive_evidence", {})
    if isinstance(defensive, Mapping) and "soc_readback" in defensive:
        problems.append("guest observation violation: daemon substrate cannot supply SOC readback")
    return problems


def _validate_realization_binding(backend: Mapping[str, Any], facts: Mapping[str, Any]) -> list[str]:
    binding = facts.get("binding")
    manifest = backend.get("manifest", {})
    envelope = manifest.get("realization_envelope", {}) if isinstance(manifest, Mapping) else {}
    if not isinstance(binding, Mapping) or not isinstance(envelope, Mapping):
        return ["daemon-observed substrate requires a realization binding"]
    problems: list[str] = []
    if binding.get("realization_envelope_digest") != envelope.get("digest"):
        problems.append("realization binding envelope digest does not match backend manifest")
    if binding.get("configuration_digest") != envelope.get("configuration_digest"):
        problems.append("realization binding configuration digest does not match backend manifest")
    driver_digest = binding.get("driver_configuration_digest")
    if not isinstance(driver_digest, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", driver_digest):
        problems.append("realization binding requires a canonical driver configuration digest")
    if binding.get("driver") != "techvault-appliance":
        problems.append("realization binding driver does not match the TechVault appliance")
    for field_name in ("connection_uri_digest", "name_prefix_digest"):
        value = binding.get(field_name)
        if not isinstance(value, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", value):
            problems.append(f"realization binding requires canonical {field_name}")
    boot_artifacts = binding.get("boot_artifact_digests")
    if not isinstance(boot_artifacts, Mapping) or set(boot_artifacts) != {"kernel", "initramfs"}:
        problems.append("realization binding requires kernel and initramfs artifact digests")
    elif any(
        not isinstance(value, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", value)
        for value in boot_artifacts.values()
    ):
        problems.append("realization binding boot artifact digests must be canonical sha256 values")
    material = {
        "driver": binding.get("driver"),
        "configuration_digest": binding.get("configuration_digest"),
        "boot_artifact_digests": binding.get("boot_artifact_digests"),
        "connection_uri_digest": binding.get("connection_uri_digest"),
        "name_prefix_digest": binding.get("name_prefix_digest"),
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    expected_driver_digest = "sha256:" + hashlib.sha256(encoded).hexdigest()
    if driver_digest != expected_driver_digest:
        problems.append("realization binding driver configuration digest does not match its material")
    return problems


def _validate_daemon_observation_item(collection: str, item: Mapping[str, Any]) -> list[str]:
    required = {
        "domains": {
            "address",
            "name",
            "architecture",
            "image_policy",
            "memory_mib",
            "vcpus",
            "network_attachments",
            "observation_source",
        },
        "networks": {
            "address",
            "name",
            "cidr",
            "gateway",
            "internal",
            "forward_mode",
            "observation_source",
        },
    }[collection]
    if set(item) != required:
        noun = "domain" if collection == "domains" else "network"
        return [f"incomplete daemon {noun} observation"]
    if not all(isinstance(item.get(key), str) and item.get(key) for key in ("address", "name")):
        return [f"incomplete daemon {collection[:-1]} observation"]
    if collection == "domains":
        if (
            not isinstance(item.get("architecture"), str)
            or not item.get("architecture")
            or not isinstance(item.get("image_policy"), str)
            or not item.get("image_policy")
            or not isinstance(item.get("memory_mib"), int)
            or item["memory_mib"] <= 0
            or not isinstance(item.get("vcpus"), int)
            or item["vcpus"] <= 0
            or not isinstance(item.get("network_attachments"), list | tuple)
        ):
            return ["incomplete daemon domain observation"]
    elif (
        not isinstance(item.get("cidr"), str)
        or not item.get("cidr")
        or not isinstance(item.get("gateway"), str)
        or not item.get("gateway")
        or not isinstance(item.get("internal"), bool)
        or item.get("forward_mode") not in {"none", "nat"}
    ):
        return ["incomplete daemon network observation"]
    return []


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
