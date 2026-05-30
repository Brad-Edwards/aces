"""Runtime scheduled-job SDL surface tests (shared cadence primitive)."""

from __future__ import annotations

import pytest
from aces_sdl.runtime_scheduled_job import (
    RuntimeScheduledJob,
    RuntimeScheduledJobLastResult,
    RuntimeScheduledJobRunState,
    RuntimeScheduledJobSchedule,
    RuntimeScheduledJobScheduleKind,
)
from pydantic import ValidationError


def _job(**overrides) -> dict:
    job = {
        "scheduled_job_id": "misp-suricata-sync",
        "name": "MISP -> Suricata IOC sync",
        "command_ref": "misp-suricata-sync",
        "enabled": True,
        "schedule": {"kind": "interval", "spec": "300s", "enabled": True},
        "run_state": {
            "last_run": "2026-05-30T00:00:00Z",
            "next_run": "2026-05-30T00:05:00Z",
            "last_result": "success",
        },
    }
    job.update(overrides)
    return job


def test_scheduled_job_full_inventory() -> None:
    job = RuntimeScheduledJob(**_job())

    assert job.scheduled_job_id == "misp-suricata-sync"
    assert job.enabled is True
    assert isinstance(job.schedule, RuntimeScheduledJobSchedule)
    assert job.schedule.kind == RuntimeScheduledJobScheduleKind.INTERVAL
    assert isinstance(job.run_state, RuntimeScheduledJobRunState)
    assert job.run_state.last_result == RuntimeScheduledJobLastResult.SUCCESS


def test_scheduled_job_id_rejects_empty() -> None:
    with pytest.raises(ValidationError, match="scheduled_job_id must be a non-empty string"):
        RuntimeScheduledJob(**_job(scheduled_job_id=""))


def test_scheduled_job_id_rejects_variable_placeholder() -> None:
    with pytest.raises(ValidationError, match="scheduled_job_id must be a stable identifier"):
        RuntimeScheduledJob(**_job(scheduled_job_id="${job_id}"))


def test_schedule_kind_closed_enum_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError, match="kind must be one of: interval, cron, calendar"):
        RuntimeScheduledJob(**_job(schedule={"kind": "event", "spec": "irrelevant"}))


def test_schedule_kind_closed_enum_rejects_unknown_sentinel() -> None:
    # The CLOSED structural vocab carries no ``unknown``/``other`` sentinel.
    with pytest.raises(ValidationError):
        RuntimeScheduledJob(**_job(schedule={"kind": "unknown"}))
    with pytest.raises(ValidationError):
        RuntimeScheduledJob(**_job(schedule={"kind": "other"}))


def test_schedule_kind_normalizes_kebab_case() -> None:
    job = RuntimeScheduledJob(**_job(schedule={"kind": "CRON", "spec": "*/5 * * * *"}))
    assert job.schedule.kind == RuntimeScheduledJobScheduleKind.CRON


def test_last_result_open_enum_normalizes() -> None:
    job = RuntimeScheduledJob(**_job(run_state={"last_result": "FAILURE"}))
    assert job.run_state.last_result == RuntimeScheduledJobLastResult.FAILURE


def test_last_result_open_enum_accepts_other_sentinel() -> None:
    job = RuntimeScheduledJob(**_job(run_state={"last_result": "other"}))
    assert job.run_state.last_result == RuntimeScheduledJobLastResult.OTHER


def test_last_result_defaults_to_unknown_sentinel() -> None:
    job = RuntimeScheduledJob(**_job(run_state={"last_run": "2026-05-30T00:00:00Z"}))
    assert job.run_state.last_result == RuntimeScheduledJobLastResult.UNKNOWN


def test_last_result_rejects_unrecognized_value() -> None:
    with pytest.raises(ValidationError, match="last_result must be one of"):
        RuntimeScheduledJob(**_job(run_state={"last_result": "exploded"}))


def test_enabled_bool_parses_string_truthy_and_falsy() -> None:
    enabled_job = RuntimeScheduledJob(**_job(enabled="yes"))
    assert enabled_job.enabled is True

    disabled_job = RuntimeScheduledJob(**_job(enabled="off"))
    assert disabled_job.enabled is False


def test_schedule_enabled_bool_parses() -> None:
    job = RuntimeScheduledJob(**_job(schedule={"kind": "interval", "enabled": "false"}))
    assert job.schedule.enabled is False


def test_enabled_accepts_variable_placeholder() -> None:
    job = RuntimeScheduledJob(**_job(enabled="${job_enabled}"))
    assert job.enabled == "${job_enabled}"


def test_scheduled_job_forbids_unknown_field() -> None:
    with pytest.raises(ValidationError):
        RuntimeScheduledJob(**_job(inputs=["/some/input"]))


def test_minimal_scheduled_job_omits_nested_models() -> None:
    job = RuntimeScheduledJob(scheduled_job_id="bare-job")
    assert job.schedule is None
    assert job.run_state is None
    assert job.enabled is None
