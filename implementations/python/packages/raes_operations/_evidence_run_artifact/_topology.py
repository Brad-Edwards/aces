"""Scenario, compiled-artifact, realization-facts, and topology section builders."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from raes_backend_libvirt.techvault_native import expected_surface

from raes_operations._evidence_run_types import (
    CompiledModel,
    NodeDeployment,
    RealizedNetwork,
)
from raes_operations.run_artifacts import portable_artifact_ref


def _scenario_section(scenario_path: Path, model: CompiledModel) -> dict[str, Any]:
    from raes.parser import parse_sdl_file

    content = scenario_path.read_bytes()
    version: str | None = None
    try:
        version = getattr(parse_sdl_file(scenario_path), "version", None)
    except Exception:
        version = None
    return {
        "name": model.scenario_name,
        "version": version,
        "relative_path": portable_artifact_ref(scenario_path),
        "content_sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
    }


def _compiled_artifact_section(model: CompiledModel) -> dict[str, Any]:
    addresses = {
        "participant_behaviors": sorted(model.participant_behaviors),
        "action_contracts": sorted(model.action_contracts),
        "observation_boundaries": sorted(model.observation_boundaries),
        "objectives": sorted(model.objectives),
        "networks": sorted(model.networks),
        "node_deployments": sorted(model.node_deployments),
    }
    fingerprint = hashlib.sha256(json.dumps(addresses, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "processor": "raes-reference-processor",
        "compiled_address_sets": addresses,
        "compiled_model_fingerprint": "sha256:" + fingerprint,
    }


def _node_services(node: NodeDeployment) -> list[dict[str, Any]]:
    spec = getattr(node, "spec", {}) or {}
    node_spec = spec.get("node", {}) if isinstance(spec, Mapping) else {}
    services = node_spec.get("services", []) if isinstance(node_spec, Mapping) else []
    return [
        {"name": svc.get("name"), "port": svc.get("port"), "protocol": svc.get("protocol")}
        for svc in services
        if isinstance(svc, Mapping)
    ]


def _node_network_links(node: NodeDeployment) -> list[str]:
    spec = getattr(node, "spec", {}) or {}
    infra = spec.get("infrastructure", {}) if isinstance(spec, Mapping) else {}
    links = infra.get("links", []) if isinstance(infra, Mapping) else []
    return [str(link) for link in links]


def _network_properties(network: RealizedNetwork) -> dict[str, Any]:
    spec = getattr(network, "spec", {}) or {}
    infra = spec.get("infrastructure", {}) if isinstance(spec, Mapping) else {}
    props = infra.get("properties") if isinstance(infra, Mapping) else None
    if not isinstance(props, Mapping):
        return {}
    return {"cidr": props.get("cidr"), "gateway": props.get("gateway"), "internal": props.get("internal")}


def _realization_facts_section(
    model: CompiledModel,
    native_snapshot: Mapping[str, Any] | None,
    cleanup_verified: bool | None,
    guest_observed: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    observed = native_snapshot if isinstance(native_snapshot, Mapping) else {}
    daemon_domains = observed.get("domains", ())
    daemon_networks = observed.get("networks", ())
    realized_addresses = observed.get("realized_addresses", ())
    return {
        "authored": {
            "source": "authored",
            "scenario_name": model.scenario_name,
        },
        "planned": {
            "source": "planned",
            "node_addresses": sorted(model.node_deployments),
            "network_addresses": sorted(model.networks),
        },
        "driver_reported": {
            "source": "driver-reported",
            "realized_addresses": list(realized_addresses) if isinstance(realized_addresses, list | tuple) else [],
        },
        "daemon_observed": {
            "source": "daemon-observed",
            "domains": list(daemon_domains) if isinstance(daemon_domains, list | tuple) else [],
            "networks": list(daemon_networks) if isinstance(daemon_networks, list | tuple) else [],
        },
        "guest_observed": _guest_observed_section(guest_observed),
        "cleanup": {
            "source": "driver-reported",
            "status": _cleanup_status(cleanup_verified),
        },
        "binding": observed.get("binding"),
    }


def _guest_observed_section(guest_observed: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return the guest-observed fact section: the bound report, or a not-observed stub.

    A daemon-only run discloses ``not-observed`` honestly; a guest-certified run
    embeds the operation-joined, challenge-bound, per-domain guest report.
    """

    if not isinstance(guest_observed, Mapping):
        return {"source": "guest-observed", "status": "not-observed"}
    return {**guest_observed, "source": "guest-observed"}


def _cleanup_status(cleanup_verified: bool | None) -> str:
    if cleanup_verified is None:
        return "not-required"
    return "verified" if cleanup_verified else "failed"


def _topology_section(
    model: CompiledModel,
    native_snapshot: Mapping[str, Any] | None,
    unrealized_capabilities: tuple[str, ...] = (),
) -> dict[str, Any]:
    substrate_realized = native_snapshot is not None
    nodes = [
        {
            "source": "planned",
            "address": node.address,
            "name": node.name,
            "node_type": getattr(node, "node_type", None),
            "os_family": getattr(node, "os_family", None),
            "services": _node_services(node),
            "networks": _node_network_links(node),
        }
        for node in model.node_deployments.values()
    ]
    networks = [
        {"source": "planned", "address": net.address, "name": net.name, **_network_properties(net)}
        for net in model.networks.values()
    ]
    section: dict[str, Any] = {
        "basis": "mixed-source" if substrate_realized else "planned",
        "disclosure": (
            "Compiled topology remains planned; the native surface contains only independently daemon-observed "
            "substrate fields."
            if substrate_realized
            else "Compiled/planned topology from the authored scenario; no live substrate realized. Network CIDRs and "
            "gateways are authored values, not host-private libvirt addresses."
        ),
        "networks": networks,
        "nodes": nodes,
        "network_attachment_matrix": {node["name"]: node["networks"] for node in nodes},
    }
    if native_snapshot is not None:
        section["native_surface"] = expected_surface(native_snapshot)
    if unrealized_capabilities:
        section["unrealized_capabilities"] = list(unrealized_capabilities)
        section["unrealized_capabilities_disclosure"] = (
            "The libvirt backend realizes the provisioning substrate (VMs and networks) only. The capabilities listed "
            "above (content placement, orchestration, and evaluation) are not realized by this backend and remain "
            "evaluator-only or translated; this is the n=2 backend-diversity limitation, not a substrate-realization "
            "failure."
        )
    return section


def _invariant_ledger_refs(model: CompiledModel, scenario_section: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "scenario_name": model.scenario_name,
        "scenario_content_sha256": scenario_section["content_sha256"],
        "participant_behaviors": sorted(model.participant_behaviors),
        "action_contracts": sorted(model.action_contracts),
        "observation_boundaries": sorted(model.observation_boundaries),
        "evidence_refs": [
            "participant_action_proof",
            "terminal_observation",
            "defensive_evidence",
            "negative_boundary_checks",
            "evaluator_outcome",
        ],
        "note": (
            "Stable RAES addresses and evidence refs for the OpenRAE/rae#600 cross-backend invariant ledger; "
            "no libvirt domain UUIDs, host paths, or APTL-private identifiers."
        ),
    }
