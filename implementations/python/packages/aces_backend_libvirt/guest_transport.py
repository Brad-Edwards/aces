"""Credential-free guest-fact transport for guest-certified libvirt runs.

The guest-certified appliance writes a bounded, line-oriented fact report to a
dedicated file-backed serial channel (``/dev/ttyS1`` in the guest maps to a
run-local host file). The host reads that file through the :class:`GuestFactTransport`
seam and parses it into a bounded structured mapping. This transport carries no
credential and is not a general command channel: the guest emits fixed,
read-only, size-bounded facts and nothing else. A future libvirt guest-agent
transport can replace this implementation without changing the observer, the
concern taxonomy, or the evidence schema.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

FACT_HEADER = "ACES-GUEST-FACTS v1"
INIT_COMPLETE_MARKER = "init complete"

# Bounds keep a hostile or malfunctioning guest from flooding host memory or the
# evidence artifact. A well-formed report is far under every limit.
_MAX_FACT_BYTES = 64 * 1024
_MAX_LINES = 512
_MAX_LINE_CHARS = 512
_MAX_ENTRIES = 64

# Stable transport-stage failure suffixes (namespaced by the observer).
FAILURE_UNAVAILABLE = "transport-unavailable"
FAILURE_TIMEOUT = "boot-timeout"


class GuestFactTransport(Protocol):
    """Read one guest's bounded fact report through the disclosed channel."""

    def read(self, *, address: str, fact_channel_path: Path, deadline_seconds: float) -> tuple[str | None, str | None]:
        """Return ``(text, None)`` on success or ``(None, failure_suffix)`` on failure."""
        ...


@dataclass(frozen=True)
class FileSerialGuestFactTransport:
    """Read the guest fact report from a file-backed serial channel.

    Polls the run-local host file the guest serial device is bound to until the
    guest has emitted its terminal ``init complete`` marker or the deadline
    elapses. Never raises: an unreadable channel is reported as a typed failure
    suffix so the caller emits a redacted diagnostic instead of an exception.
    """

    poll_seconds: float = 0.5

    def read(self, *, address: str, fact_channel_path: Path, deadline_seconds: float) -> tuple[str | None, str | None]:
        del address
        deadline = time.monotonic() + max(0.0, deadline_seconds)
        saw_channel = False
        while True:
            text = _read_bounded(fact_channel_path)
            if text is not None:
                saw_channel = True
                if _contains_terminal_marker(text):
                    return text, None
            if time.monotonic() >= deadline:
                if saw_channel:
                    return None, FAILURE_TIMEOUT
                return None, FAILURE_UNAVAILABLE
            time.sleep(self.poll_seconds)


def _read_bounded(path: Path) -> str | None:
    try:
        with path.open("rb") as stream:
            payload = stream.read(_MAX_FACT_BYTES + 1)
    except OSError:
        return None
    if len(payload) > _MAX_FACT_BYTES:
        payload = payload[:_MAX_FACT_BYTES]
    return payload.decode("utf-8", errors="replace")


def _contains_terminal_marker(text: str) -> bool:
    return any(line.strip() == INIT_COMPLETE_MARKER for line in text.splitlines())


def parse_guest_facts(text: str) -> Mapping[str, object] | None:
    """Parse the bounded line-oriented guest report into a structured mapping.

    Returns ``None`` when the header is absent or the report is unparseable.
    Unknown lines are ignored; bounds are enforced so a malformed report cannot
    produce an unbounded structure.
    """

    lines = text.splitlines()[:_MAX_LINES]
    if not lines or lines[0].strip() != FACT_HEADER:
        return None
    facts: dict[str, object] = {
        "challenge": None,
        "init_complete": False,
        "architecture": None,
        "vcpus": None,
        "memory_mib": None,
        "interfaces": [],
        "content": [],
        "accounts": [],
        "services": [],
        "duplicate": False,
    }
    seen: set[str] = set()
    for raw in lines[1:]:
        _consume_line(facts, raw[:_MAX_LINE_CHARS].rstrip("\n"), seen)
    return facts


_SCALAR_KEYS = frozenset({"challenge", "architecture", "vcpus", "memory_mib"})


def _consume_line(facts: dict[str, object], line: str, seen: set[str]) -> None:
    stripped = line.strip()
    if stripped == INIT_COMPLETE_MARKER:
        facts["init_complete"] = True
        return
    parts = stripped.split(" ")
    key = parts[0] if parts else ""
    fields = parts[1:]
    handler = _LINE_HANDLERS.get(key)
    if handler is None:
        return
    # A repeated singleton fact (same key) or an identical repeated list line is a
    # duplicate observation: record it distinctly rather than silently collapsing it.
    marker = key if key in _SCALAR_KEYS else stripped
    if marker in seen:
        facts["duplicate"] = True
    else:
        seen.add(marker)
    handler(facts, fields)


def _set_scalar(name: str, cast: object):
    def _apply(facts: dict[str, object], fields: list[str]) -> None:
        if fields:
            facts[name] = cast(fields[0]) if cast is not str else fields[0]  # type: ignore[operator]

    return _apply


def _append(name: str, arity: int, build):
    def _apply(facts: dict[str, object], fields: list[str]) -> None:
        bucket = facts[name]
        if isinstance(bucket, list) and len(bucket) < _MAX_ENTRIES and len(fields) >= arity:
            entry = build(fields)
            if entry is not None:
                bucket.append(entry)

    return _apply


def _to_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _iface_entry(fields: list[str]) -> dict[str, object]:
    return {"mac": fields[0], "ipv4": fields[1], "up": fields[2] == "1"}


def _content_entry(fields: list[str]) -> dict[str, object]:
    return {"path": fields[0], "sha256": fields[1], "mode": fields[2]}


def _account_entry(fields: list[str]) -> dict[str, object]:
    # The trailing groups field is optional: an account with no supplemental groups
    # emits five fields (the empty groups token is trimmed away by the transport).
    groups = [group for group in fields[5].split(",") if group] if len(fields) > 5 else []
    return {
        "name": fields[0],
        "uid": _to_int(fields[1]),
        "home": fields[2],
        "shell": fields[3],
        "disabled": fields[4] == "1",
        "groups": sorted(groups),
    }


def _service_entry(fields: list[str]) -> dict[str, object]:
    return {
        "name": fields[0],
        "port": _to_int(fields[1]),
        "listening": fields[2] == "1",
        "pid_present": fields[3] == "1",
    }


_LINE_HANDLERS = {
    "challenge": _set_scalar("challenge", str),
    "architecture": _set_scalar("architecture", str),
    "vcpus": _set_scalar("vcpus", _to_int),
    "memory_mib": _set_scalar("memory_mib", _to_int),
    "iface": _append("interfaces", 3, _iface_entry),
    "content": _append("content", 3, _content_entry),
    "account": _append("accounts", 5, _account_entry),
    "service": _append("services", 4, _service_entry),
}


__all__ = [
    "FACT_HEADER",
    "FAILURE_TIMEOUT",
    "FAILURE_UNAVAILABLE",
    "INIT_COMPLETE_MARKER",
    "FileSerialGuestFactTransport",
    "GuestFactTransport",
    "parse_guest_facts",
]
