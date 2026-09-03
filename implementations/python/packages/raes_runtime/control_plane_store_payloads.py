"""Serialized-payload builders for the durable runtime-snapshot envelope."""

from __future__ import annotations

from typing import Any

from raes_contracts.account_credentials import (
    account_placement_has_credential_bindings,
    value_free_account_placement_payload,
)
from raes_contracts.runtime_state import RuntimeSnapshot


def _entry_payloads(snapshot: RuntimeSnapshot) -> dict[str, dict[str, Any]]:
    entries = {
        address: {
            "address": entry.address,
            "domain": entry.domain.value,
            "resource_type": entry.resource_type,
            "payload": dict(entry.payload),
            "ordering_dependencies": list(entry.ordering_dependencies),
            "refresh_dependencies": list(entry.refresh_dependencies),
            "status": entry.status,
        }
        for address, entry in snapshot.entries.items()
    }
    for entry in entries.values():
        if entry["resource_type"] != "account-placement":
            continue
        entry_payload = entry["payload"]
        if account_placement_has_credential_bindings(entry_payload):
            entry["payload"] = value_free_account_placement_payload(entry_payload)
    return entries


def _realization_provenance_payload(snapshot: RuntimeSnapshot) -> list[dict[str, Any]]:
    return [
        {
            "address": entry.address,
            "field_path": entry.field_path,
            "domain": entry.domain,
            "requirement_kind": entry.requirement_kind,
            "explicitness": entry.explicitness.value,
            "provenance": entry.provenance.value,
            "governing_scope": entry.governing_scope,
            "artifact_satisfaction": (
                entry.artifact_satisfaction.model_dump(mode="json") if entry.artifact_satisfaction is not None else None
            ),
        }
        for entry in snapshot.realization_provenance
    ]


def _realization_observations_payload(snapshot: RuntimeSnapshot) -> list[dict[str, Any]]:
    return [
        {
            "address": entry.address,
            "field_path": entry.field_path,
            "domain": entry.domain,
            "requirement_kind": entry.requirement_kind,
            "verification_scope": entry.verification_scope.value,
            "observation_strength": entry.observation_strength.value,
            **(
                {
                    "observed_value": entry.observed_value,
                    "operating_system": (
                        {
                            "family": entry.operating_system.family,
                            "distribution": entry.operating_system.distribution,
                            "version": entry.operating_system.version,
                        }
                        if entry.operating_system is not None
                        else None
                    ),
                    "operation_id": entry.operation_id,
                    "envelope_digest": entry.envelope_digest,
                    "configuration_digest": entry.configuration_digest,
                    "observer_version": entry.observer_version,
                    "sequence": entry.sequence,
                    "binding_verified": entry.binding_verified,
                }
                if entry.requirement_kind in {"compute-substrate", "operating-system"}
                else {}
            ),
        }
        for entry in snapshot.realization_observations
    ]
