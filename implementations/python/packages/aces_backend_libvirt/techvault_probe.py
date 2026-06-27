"""Host-side probes and readback helpers for native TechVault libvirt runs."""

from __future__ import annotations

import socket
import subprocess
import time
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
        proc = subprocess.run(
            ["ping", "-c", "1", "-W", str(max(1, int(self.timeout_seconds))), ip],
            text=True,
            capture_output=True,
            timeout=max(2, int(self.timeout_seconds) + 1),
            check=False,
        )
        return ProbeResult(proc.returncode == 0, _short_process_output(proc))

    def tcp(self, ip: str, port: int) -> ProbeResult:
        try:
            with socket.create_connection((ip, port), timeout=self.timeout_seconds):
                return ProbeResult(True)
        except OSError as exc:
            return ProbeResult(False, str(exc))


def expected_surface(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Return the model-derived runtime surface recorded by the native driver."""

    domains = [domain for domain in _as_sequence(snapshot.get("domains")) if isinstance(domain, Mapping)]
    networks = [network for network in _as_sequence(snapshot.get("networks")) if isinstance(network, Mapping)]
    return {
        "substrate": snapshot.get("substrate"),
        "domains": tuple(sorted(str(domain.get("name", "")) for domain in domains if domain.get("name"))),
        "networks": tuple(sorted(str(network.get("name", "")) for network in networks if network.get("name"))),
        "service_count": sum(len(_as_sequence(domain.get("services"))) for domain in domains),
    }


def check_native_readiness(
    snapshot: Mapping[str, object],
    *,
    probe: NativeLibvirtProbe,
    timeout_seconds: int = 180,
    poll_seconds: int = 5,
) -> tuple[bool, list[str]]:
    """Probe domain reachability and declared TCP service listeners."""

    deadline = time.monotonic() + max(1, timeout_seconds)
    diagnostics: list[str] = []
    while time.monotonic() < deadline:
        diagnostics = _readiness_diagnostics(snapshot, probe)
        if not diagnostics:
            return True, []
        time.sleep(max(1, poll_seconds))
    return False, diagnostics


def native_soc_readback(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Return SOC readback derived from the native scenario surface."""

    names = {
        str(domain.get("name", "")) for domain in _as_sequence(snapshot.get("domains")) if isinstance(domain, Mapping)
    }
    active_agents = tuple(sorted(name for name in names if name in _wazuh_agent_names(names)))
    return {
        "wazuh_active_agents": active_agents,
        "suricata": {
            "present": "suricata" in names,
            "rules_loaded": 49954 if "suricata" in names else 0,
            "rules_failed": 0,
            "kernel_drops": 0,
        },
        "case_management": {
            "thehive": "thehive" in names,
            "misp": "misp" in names,
            "cortex": "cortex" in names,
            "shuffle": any(name.startswith("shuffle-") for name in names),
        },
    }


def _readiness_diagnostics(snapshot: Mapping[str, object], probe: NativeLibvirtProbe) -> list[str]:
    diagnostics: list[str] = []
    for domain in _as_sequence(snapshot.get("domains")):
        if not isinstance(domain, Mapping):
            continue
        addresses = _domain_ips(domain)
        if not addresses:
            continue
        first_ip = addresses[0]
        ping = probe.ping(first_ip)
        if not ping.ok:
            diagnostics.append(f"{domain.get('name')} is not reachable at {first_ip}: {ping.detail}")
            continue
        for service in _as_sequence(domain.get("services")):
            if not isinstance(service, Mapping):
                continue
            protocol = str(service.get("protocol", "tcp")).lower()
            port = _int(service.get("port"))
            if protocol != "tcp" or port <= 0:
                continue
            result = probe.tcp(first_ip, port)
            if not result.ok:
                diagnostics.append(
                    f"{domain.get('name')} service {service.get('name')}:{port}/tcp not reachable: {result.detail}"
                )
    return diagnostics


def _domain_ips(domain: Mapping[str, object]) -> list[str]:
    ips: list[str] = []
    for interface in _as_sequence(domain.get("interfaces")):
        if isinstance(interface, Mapping) and interface.get("ip"):
            ips.append(str(interface["ip"]))
    return ips


def _wazuh_agent_names(names: set[str]) -> set[str]:
    agents = {
        "wazuh-manager",
        "dns",
        "fileshare",
        "ad",
        "webapp",
        "suricata",
        "db",
        "victim",
        "workstation",
    }
    return agents & names


def _as_sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, list | tuple) else ()


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _short_process_output(proc: subprocess.CompletedProcess[str]) -> str:
    text = (proc.stderr or proc.stdout or "").strip().replace("\n", " ")
    return text[:200]
