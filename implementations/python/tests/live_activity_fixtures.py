"""Shared deterministic live-activity test payloads."""

from __future__ import annotations

from copy import deepcopy

from test_authored_historical_state import _valid_payload as _historical_payload


def valid_live_activity_payload() -> dict[str, object]:
    payload = deepcopy(_historical_payload())
    payload["accounts"] = {
        "records-operator": {
            "username": "records-operator",
            "node": "archive",
        }
    }
    archive = payload["nodes"]["archive"]  # type: ignore[index]
    archive["runtime"] = {  # type: ignore[index]
        "service_listeners": [
            {
                "service_listener_id": "records-observer",
                "service": "records",
                "address": "127.0.0.1",
                "port": 8443,
                "protocol": "tcp",
                "address_family": "ipv4",
                "scope": "loopback_only",
            }
        ]
    }
    payload["activity_templates"] = {
        "record-update": {
            "version": "1.0.0",
            "description": "Update one existing logical record through a governed operation.",
            "capability": {
                "profile": "protocol-operation/v1",
                "protocol": "http_api",
                "operation": "update",
            },
            "parameters": {
                "record": {
                    "kind": "historical_object_ref",
                    "required": True,
                }
            },
            "readback_class": "object_state",
        }
    }
    payload["activity_profiles"] = {
        "ordinary-records": {
            "version": "1.0.0",
            "historical_baseline_ref": "enterprise",
            "randomness": {
                "random_stream_profile": "blake3-xof-v1",
                "address_profile": "activity-random-address/v1",
                "transform_profile": "bounded-integer/v1",
                "root_entropy": {
                    "kind": "public-seed",
                    "encoding": "hex-fixed-width",
                    "value": "11" * 32,
                },
            },
            "actors": {
                "records-clerk": {
                    "entity_ref": "operations",
                    "account_ref": "records-operator",
                    "deployment_tenant_ref": "range-a",
                    "operating_scope_refs": ["nodes.archive.services.records"],
                }
            },
            "execution_contexts": {
                "records-api": {
                    "deployment_tenant_ref": "range-a",
                    "account_ref": "records-operator",
                    "target_service_ref": "nodes.archive.services.records",
                    "protocol": "http_api",
                }
            },
            "schedules": {
                "steady": {
                    "profile": "finite-logical-schedule/v1",
                    "time_domain": "logical",
                    "anchor_seconds": 0,
                    "interval_seconds": "15s",
                    "horizon_seconds": "60s",
                    "max_occurrences": 4,
                }
            },
            "actions": {
                "update-record": {
                    "template_ref": "record-update",
                    "actor_ref": "records-clerk",
                    "execution_context_ref": "records-api",
                    "schedule_ref": "steady",
                    "parameter_bindings": [
                        {
                            "parameter_ref": "record",
                            "value_ref": "historical_baselines.enterprise.objects.message-001",
                        }
                    ],
                    "retry": {
                        "max_attempts": 2,
                        "interval_seconds": "2s",
                    },
                }
            },
            "dependencies": [],
            "budgets": [
                {
                    "dimension": "operations",
                    "unit": "operation",
                    "window_seconds": "60s",
                    "action_demands": {"update-record": {"numerator": 1, "denominator": 1}},
                    "range_capacity": {"numerator": 10, "denominator": 1},
                    "fleet_capacity": {"numerator": 100, "denominator": 1},
                    "participant_reservation": {"numerator": 4, "denominator": 1},
                }
            ],
            "lifecycle": {
                "profile": "range-lifecycle/v1",
                "on_start": "admit_new",
                "on_resume": "admit_new",
                "on_pause": "suspend_new",
                "in_flight_on_pause": "finish",
                "on_drain": "drain",
                "on_reset_generation_advance": "discard_stale",
                "on_teardown": "discard_pending",
                "drain_timeout_seconds": "30s",
            },
            "readback": {
                "profile": "evidence-readback/v1",
                "action_refs": ["update-record"],
                "observability_refs": ["nodes.archive.runtime.service_listeners.records-observer"],
                "evidence_requirement_refs": ["native-readback"],
                "participant_proof": False,
            },
            "telemetry": {
                "profile": "evidence-provenance/v1",
                "observability_refs": ["nodes.archive.runtime.service_listeners.records-observer"],
                "evidence_requirement_refs": ["native-readback"],
                "participant_proof": False,
                "emits_participant_receipts": False,
                "establishes_objective_truth": False,
            },
        }
    }
    return payload


__all__ = ["valid_live_activity_payload"]
