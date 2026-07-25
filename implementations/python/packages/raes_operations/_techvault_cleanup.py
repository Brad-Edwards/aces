"""Verified cleanup for captured TechVault native-substrate reports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from raes_backend_libvirt.techvault_native import TechVaultNativeLibvirtDriver


def cleanup_native_snapshot(
    driver: TechVaultNativeLibvirtDriver,
    snapshot: Mapping[str, object],
) -> tuple[bool, tuple[str, ...]]:
    """Destroy every captured native address and require explicit absence handles."""

    domains = _addresses(snapshot.get("domains"))
    networks = _addresses(snapshot.get("networks"))
    if not domains:
        return False, ("native cleanup requires a captured domain inventory",)
    try:
        result = driver.destroy(networks=networks, domains=domains)
    except Exception:
        return False, ("native cleanup failed",)
    diagnostics = tuple(f"{item.code} at {item.address}" for item in result.diagnostics)
    verified = (
        not diagnostics
        and _absence_handles(result.domains, domains)
        and _absence_handles(result.networks, networks)
        and driver.last_snapshot == {}
    )
    if not verified and not diagnostics:
        diagnostics = ("native cleanup did not return a complete verified-absence inventory",)
    return verified, diagnostics


def _addresses(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list | tuple):
        return ()
    return tuple(
        str(item["address"])
        for item in raw
        if isinstance(item, Mapping) and isinstance(item.get("address"), str) and item.get("address")
    )


def _absence_handles(
    handles: Sequence[object],
    requested: tuple[str, ...],
) -> bool:
    return (
        len(handles) == len(requested)
        and {getattr(handle, "address", None) for handle in handles} == set(requested)
        and all(getattr(handle, "realized", None) is False for handle in handles)
    )


__all__ = ["cleanup_native_snapshot"]
