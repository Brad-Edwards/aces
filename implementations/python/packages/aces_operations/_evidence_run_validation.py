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

_SHA256_RE = re.compile(r"sha256:[a-f0-9]{64}")
_DAEMON_REQUIRED_FIELDS = {
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
}


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
    problems.extend(_validate_fact_sources(facts))
    topology = payload.get("realized_topology", {})
    problems.extend(_validate_topology_sources(topology))
    backend = payload.get("backend", {})
    provenance = backend.get("realization_provenance", {}) if isinstance(backend, Mapping) else {}
    substrate_realized = isinstance(provenance, Mapping) and provenance.get("substrate_realized") is True
    cleanup = facts.get("cleanup")
    problems.extend(_validate_cleanup_source(cleanup))
    if substrate_realized:
        problems.extend(_validate_realized_substrate(backend, facts, topology, provenance, cleanup))
    elif isinstance(provenance, Mapping) and provenance.get("basis") != "planned-not-realized":
        problems.append("unrealized substrate basis must be planned-not-realized")
    else:
        problems.extend(_validate_unrealized_substrate(facts, provenance, cleanup))
    problems.extend(_validate_guest_observation_boundary(payload))
    problems.extend(_validate_guest_observations(facts))
    return problems


def _validate_guest_observations(facts: Mapping[str, Any]) -> list[str]:
    """Validate the guest-observed fact section when a guest report is present.

    A daemon-only run carries ``{"source": "guest-observed", "status": "not-observed"}``
    and is skipped here. A guest-certified run must bind every observed domain to the
    control-plane operation, a fresh challenge, a canonical native correlation, and a
    daemon-observed domain (rejecting unjoined or cross-operation evidence).
    """

    guest = facts.get("guest_observed")
    if not isinstance(guest, Mapping) or guest.get("status") == "not-observed":
        return []
    problems = _validate_guest_metadata(guest)
    domains = guest.get("domains")
    if not isinstance(domains, list | tuple) or not domains:
        return [*problems, "guest observation requires at least one observed domain"]
    daemon_addresses = _daemon_domain_addresses(facts)
    for item in domains:
        problems.extend(_validate_guest_domain(item, daemon_addresses))
    return problems


_GUEST_METADATA_FIELDS = (
    ("observation timestamp", "observed_at"),
    ("probe policy", "probe_policy"),
    ("fresh challenge", "challenge"),
)


def _validate_guest_metadata(guest: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    if not _is_canonical_sha256(guest.get("operation_ref")):
        problems.append("guest observation requires a canonical operation reference")
    if not isinstance(guest.get("certifying"), bool):
        problems.append("guest observation requires an explicit certifying flag")
    problems.extend(
        f"guest observation requires a {label}"
        for label, field_name in _GUEST_METADATA_FIELDS
        if not _nonempty_string(guest.get(field_name))
    )
    return problems


def _daemon_domain_addresses(facts: Mapping[str, Any]) -> set[object]:
    daemon = facts.get("daemon_observed", {})
    domains = daemon.get("domains", ()) if isinstance(daemon, Mapping) else ()
    return {item.get("address") for item in domains if isinstance(item, Mapping)}


_GUEST_DOMAIN_FIELDS = ("architecture", "vcpus", "memory_mib", "network", "content", "accounts", "services")


def _validate_guest_domain(item: object, daemon_addresses: set[object]) -> list[str]:
    if not isinstance(item, Mapping):
        return ["guest observation domain must be a mapping"]
    problems: list[str] = []
    if not _is_canonical_sha256(item.get("correlation")):
        problems.append("guest observation requires a canonical native correlation")
    if item.get("address") not in daemon_addresses:
        problems.append("guest observation is not joined to a daemon-observed domain")
    problems.extend(
        f"guest observation domain missing {field_name}"
        for field_name in _GUEST_DOMAIN_FIELDS
        if field_name not in item
    )
    return problems


def _validate_fact_sources(facts: Mapping[str, Any]) -> list[str]:
    expected_sources = {
        "authored": "authored",
        "planned": "planned",
        "driver_reported": "driver-reported",
        "daemon_observed": "daemon-observed",
        "guest_observed": "guest-observed",
    }
    return [
        f"realization source violation: {key}.source must be {source!r}"
        for key, source in expected_sources.items()
        if not isinstance(facts.get(key), Mapping) or facts[key].get("source") != source
    ]


def _validate_topology_sources(topology: object) -> list[str]:
    if not isinstance(topology, Mapping):
        return []
    problems: list[str] = []
    if topology.get("basis") not in {"planned", "mixed-source"}:
        problems.append("realized_topology.basis must be planned or mixed-source")
    for collection in ("nodes", "networks"):
        for item in topology.get(collection, ()) or ():
            if isinstance(item, Mapping) and item.get("source") != "planned":
                problems.append(f"realization source violation: realized_topology.{collection} is planned")
    native_surface = topology.get("native_surface")
    if isinstance(native_surface, Mapping) and native_surface.get("source") != "daemon-observed":
        problems.append("realization source violation: native_surface must be daemon-observed")
    return problems


def _validate_cleanup_source(cleanup: object) -> list[str]:
    if isinstance(cleanup, Mapping) and cleanup.get("source") == "driver-reported":
        return []
    return ["realization cleanup must be driver-reported"]


def _validate_realized_substrate(
    backend: object,
    facts: Mapping[str, Any],
    topology: object,
    provenance: Mapping[str, Any],
    cleanup: object,
) -> list[str]:
    daemon = facts.get("daemon_observed", {})
    daemon_items = _daemon_items(daemon)
    problems = _validate_realized_provenance(provenance, cleanup)
    problems.extend(_validate_daemon_observations(daemon))
    problems.extend(_validate_reported_addresses(facts, daemon_items))
    problems.extend(_validate_native_surface(topology, daemon))
    if isinstance(backend, Mapping):
        problems.extend(_validate_realization_binding(backend, facts))
    else:
        problems.append("daemon-observed substrate requires a realization binding")
    return problems


def _validate_realized_provenance(provenance: Mapping[str, Any], cleanup: object) -> list[str]:
    problems: list[str] = []
    if provenance.get("basis") != "daemon-observed-substrate":
        problems.append("realization provenance basis must be daemon-observed-substrate")
    cleanup_verified = provenance.get("cleanup_verified")
    expected_cleanup_status = "verified" if cleanup_verified is True else "failed"
    cleanup_consistent = (
        isinstance(cleanup_verified, bool)
        and isinstance(cleanup, Mapping)
        and cleanup.get("status") == expected_cleanup_status
    )
    if not cleanup_consistent:
        problems.append("daemon-observed substrate requires a consistent cleanup outcome")
    return problems


def _validate_daemon_observations(daemon: object) -> list[str]:
    problems: list[str] = []
    domains = daemon.get("domains", ()) if isinstance(daemon, Mapping) else ()
    if not isinstance(domains, list | tuple) or not domains:
        problems.append("daemon-observed substrate requires at least one observed domain")
    for collection in ("domains", "networks"):
        values = daemon.get(collection, ()) if isinstance(daemon, Mapping) else ()
        for item in values:
            if isinstance(item, Mapping):
                if item.get("observation_source") != "daemon-observed":
                    problems.append(f"realization source violation: daemon_observed.{collection} item source")
                problems.extend(_validate_daemon_observation_item(collection, item))
    return problems


def _daemon_items(daemon: object) -> list[Mapping[str, Any]]:
    if not isinstance(daemon, Mapping):
        return []
    return [
        item
        for collection in ("domains", "networks")
        for item in daemon.get(collection, ())
        if isinstance(item, Mapping)
    ]


def _validate_reported_addresses(
    facts: Mapping[str, Any],
    daemon_items: list[Mapping[str, Any]],
) -> list[str]:
    observed_addresses = {item.get("address") for item in daemon_items}
    driver_reported = facts.get("driver_reported", {})
    reported_addresses = driver_reported.get("realized_addresses", ()) if isinstance(driver_reported, Mapping) else ()
    valid = (
        isinstance(reported_addresses, list | tuple)
        and all(isinstance(item, str) for item in reported_addresses)
        and set(reported_addresses) == observed_addresses
    )
    return [] if valid else ["driver-reported addresses do not match daemon observations"]


def _validate_native_surface(topology: object, daemon: object) -> list[str]:
    native_surface = topology.get("native_surface") if isinstance(topology, Mapping) else None
    if not isinstance(native_surface, Mapping):
        return ["daemon-observed substrate requires a native surface"]
    problems: list[str] = []
    for collection in ("domains", "networks"):
        observed_names = sorted(
            str(item.get("name"))
            for item in (daemon.get(collection, ()) if isinstance(daemon, Mapping) else ())
            if isinstance(item, Mapping)
        )
        surface_names = native_surface.get(collection, ())
        if not isinstance(surface_names, list | tuple) or sorted(str(item) for item in surface_names) != observed_names:
            problems.append(f"native surface {collection} do not match daemon observations")
    return problems


def _validate_unrealized_substrate(
    facts: Mapping[str, Any],
    provenance: Mapping[str, Any],
    cleanup: object,
) -> list[str]:
    problems: list[str] = []
    daemon = facts.get("daemon_observed", {})
    daemon_domains = daemon.get("domains", ()) if isinstance(daemon, Mapping) else ()
    daemon_networks = daemon.get("networks", ()) if isinstance(daemon, Mapping) else ()
    if daemon_domains or daemon_networks or facts.get("binding") is not None:
        problems.append("unrealized substrate cannot publish daemon observations or realization binding")
    guest = facts.get("guest_observed")
    if isinstance(guest, Mapping) and guest.get("status") != "not-observed":
        problems.append("unrealized substrate cannot publish guest observations")
    if provenance.get("cleanup_verified") is not None:
        problems.append("unrealized substrate cleanup must be not-applicable")
    if isinstance(cleanup, Mapping) and cleanup.get("status") != "not-required":
        problems.append("unrealized substrate cleanup status must be not-required")
    return problems


def _validate_guest_observation_boundary(payload: Mapping[str, Any]) -> list[str]:
    defensive = payload.get("defensive_evidence", {})
    if isinstance(defensive, Mapping) and "soc_readback" in defensive:
        return ["guest observation violation: daemon substrate cannot supply SOC readback"]
    return []


def _validate_realization_binding(backend: Mapping[str, Any], facts: Mapping[str, Any]) -> list[str]:
    binding = facts.get("binding")
    manifest = backend.get("manifest", {})
    envelope = manifest.get("realization_envelope", {}) if isinstance(manifest, Mapping) else {}
    if not isinstance(binding, Mapping) or not isinstance(envelope, Mapping):
        return ["daemon-observed substrate requires a realization binding"]
    problems = _validate_binding_identity(binding, envelope)
    problems.extend(_validate_boot_artifact_binding(binding))
    expected_driver_digest = _driver_configuration_digest(binding)
    if binding.get("driver_configuration_digest") != expected_driver_digest:
        problems.append("realization binding driver configuration digest does not match its material")
    return problems


def _validate_binding_identity(binding: Mapping[str, Any], envelope: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    if binding.get("realization_envelope_digest") != envelope.get("digest"):
        problems.append("realization binding envelope digest does not match backend manifest")
    if binding.get("configuration_digest") != envelope.get("configuration_digest"):
        problems.append("realization binding configuration digest does not match backend manifest")
    driver_digest = binding.get("driver_configuration_digest")
    if not _is_canonical_sha256(driver_digest):
        problems.append("realization binding requires a canonical driver configuration digest")
    if binding.get("driver") not in {"techvault-appliance", "guest-certified-appliance"}:
        problems.append("realization binding driver does not match a governed appliance mode")
    for field_name in ("connection_uri_digest", "name_prefix_digest"):
        if not _is_canonical_sha256(binding.get(field_name)):
            problems.append(f"realization binding requires canonical {field_name}")
    return problems


def _validate_boot_artifact_binding(binding: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    boot_artifacts = binding.get("boot_artifact_digests")
    if not isinstance(boot_artifacts, Mapping) or set(boot_artifacts) != {"kernel", "initramfs"}:
        problems.append("realization binding requires kernel and initramfs artifact digests")
    elif not all(_is_canonical_sha256(value) for value in boot_artifacts.values()):
        problems.append("realization binding boot artifact digests must be canonical sha256 values")
    return problems


def _driver_configuration_digest(binding: Mapping[str, Any]) -> str:
    material = {
        "driver": binding.get("driver"),
        "configuration_digest": binding.get("configuration_digest"),
        "boot_artifact_digests": binding.get("boot_artifact_digests"),
        "connection_uri_digest": binding.get("connection_uri_digest"),
        "name_prefix_digest": binding.get("name_prefix_digest"),
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _is_canonical_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _validate_daemon_observation_item(collection: str, item: Mapping[str, Any]) -> list[str]:
    noun = "domain" if collection == "domains" else "network"
    problems: list[str] = []
    if set(item) != _DAEMON_REQUIRED_FIELDS[collection] or not _valid_observation_identity(item):
        problems.append(f"incomplete daemon {noun} observation")
    elif collection == "domains" and not _valid_domain_observation(item):
        problems.append("incomplete daemon domain observation")
    elif collection == "networks" and not _valid_network_observation(item):
        problems.append("incomplete daemon network observation")
    return problems


def _valid_observation_identity(item: Mapping[str, Any]) -> bool:
    return all(_nonempty_string(item.get(key)) for key in ("address", "name"))


def _valid_domain_observation(item: Mapping[str, Any]) -> bool:
    checks = (
        _nonempty_string(item.get("architecture")),
        _nonempty_string(item.get("image_policy")),
        isinstance(item.get("memory_mib"), int) and item["memory_mib"] > 0,
        isinstance(item.get("vcpus"), int) and item["vcpus"] > 0,
        isinstance(item.get("network_attachments"), list | tuple),
    )
    return all(checks)


def _valid_network_observation(item: Mapping[str, Any]) -> bool:
    checks = (
        _nonempty_string(item.get("cidr")),
        _nonempty_string(item.get("gateway")),
        isinstance(item.get("internal"), bool),
        item.get("forward_mode") in {"none", "nat"},
    )
    return all(checks)


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


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
