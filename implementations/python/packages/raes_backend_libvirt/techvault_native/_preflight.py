"""Boot-input admission for native TechVault domain operations."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

from raes_contracts.diagnostics import Diagnostic

from raes_backend_libvirt._observability import record_suppressed_failure as _record_suppressed_failure

from .._initramfs import builder_preflight
from .._techvault_native_ops import (
    _CODE_KERNEL_UNAVAILABLE,
    _CODE_TOOLCHAIN_UNAVAILABLE,
    _diagnostic,
)
from ..driver import DomainSpec
from ..techvault_appliance import InitramfsBuilder
from ..techvault_matrix import safe_name


def validate_driver_configuration(
    *,
    connection_uri: str,
    name_prefix: str,
    define_only: bool,
    clean_existing: bool,
) -> None:
    """Reject ambiguous or claim-incompatible native driver configuration."""

    if not connection_uri or not connection_uri.strip():
        raise ValueError("TechVaultNativeLibvirtDriver connection_uri must be non-empty.")
    parsed_uri = urlsplit(connection_uri)
    if parsed_uri.username is not None or parsed_uri.password is not None:
        raise ValueError("TechVaultNativeLibvirtDriver connection URI must not carry credentials.")
    if not name_prefix or not name_prefix.strip():
        raise ValueError("TechVaultNativeLibvirtDriver name_prefix must be non-empty.")
    if define_only:
        raise ValueError("TechVaultNativeLibvirtDriver define-only mode cannot make realization claims.")
    if clean_existing:
        raise ValueError("TechVaultNativeLibvirtDriver refuses unsafe prefix-wide cleanup.")
    if safe_name(name_prefix, fallback="raes-techvault", prefix="") != name_prefix:
        raise ValueError("TechVaultNativeLibvirtDriver name_prefix must already be libvirt-safe.")


def artifact_preflight_diagnostics(
    *,
    domains: tuple[DomainSpec, ...],
    kernel_path: Path | None,
    initramfs_builder: InitramfsBuilder,
) -> list[Diagnostic]:
    """Reject missing boot inputs before opening libvirt or mutating networks."""

    diagnostic = None
    if domains:
        assert kernel_path is not None
        if not kernel_path.is_file() or not os.access(kernel_path, os.R_OK):
            diagnostic = _diagnostic(_CODE_KERNEL_UNAVAILABLE, "runtime.libvirt.kernel")
        else:
            try:
                toolchain = builder_preflight(initramfs_builder)
            except Exception as exc:
                _record_suppressed_failure("artifact_preflight_diagnostics", exc)
                toolchain = None
            if toolchain is None or not toolchain.ready:
                diagnostic = _diagnostic(_CODE_TOOLCHAIN_UNAVAILABLE, "runtime.libvirt.initramfs")
    return [diagnostic] if diagnostic is not None else []
