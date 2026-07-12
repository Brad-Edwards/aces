"""Host-side probes and readback helpers for native TechVault libvirt runs."""

from __future__ import annotations

import socket
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ProbeResult:
    """One native runtime probe result."""

    ok: bool
    detail: str = ""


@dataclass
class NativeLibvirtProbe:
    """Host-side probes for the native libvirt appliance surface."""

    timeout_seconds: float = 1.5

    def ping(self, ip: str) -> ProbeResult:
        try:
            proc = subprocess.run(
                ["ping", "-c", "1", "-W", str(max(1, int(self.timeout_seconds))), ip],
                text=True,
                capture_output=True,
                timeout=max(2, int(self.timeout_seconds) + 1),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ProbeResult(False, "probe failed")
        return ProbeResult(proc.returncode == 0, "" if proc.returncode == 0 else "probe failed")

    def tcp(self, ip: str, port: int) -> ProbeResult:
        try:
            with socket.create_connection((ip, port), timeout=self.timeout_seconds):
                return ProbeResult(True)
        except OSError:
            return ProbeResult(False, "connection failed")


def expected_surface(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Return bounded native names from the driver's daemon-observed report."""

    domains = [domain for domain in _as_sequence(snapshot.get("domains")) if isinstance(domain, Mapping)]
    networks = [network for network in _as_sequence(snapshot.get("networks")) if isinstance(network, Mapping)]
    return {
        "source": snapshot.get("source"),
        "substrate": snapshot.get("substrate"),
        "domains": tuple(sorted(str(domain.get("name", "")) for domain in domains if domain.get("name"))),
        "networks": tuple(sorted(str(network.get("name", "")) for network in networks if network.get("name"))),
    }


def check_native_readiness(
    snapshot: Mapping[str, object],
    *,
    probe: NativeLibvirtProbe,
    timeout_seconds: int = 180,
    poll_seconds: int = 5,
) -> tuple[bool, list[str]]:
    """Decline guest-readiness inference from the daemon-observed substrate."""

    del snapshot, probe, timeout_seconds, poll_seconds
    return False, ["guest readiness requires concern-specific guest observation"]


def native_soc_readback(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Disclose that daemon substrate state is not guest SOC observation."""

    del snapshot
    return {
        "status": "not-observed",
        "observation_source": "none",
        "reason": "guest SOC state requires concern-specific guest observation",
    }


def _as_sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, list | tuple) else ()
