"""Runtime target construction for the libvirt/QEMU backend."""

from __future__ import annotations

from typing import Any

from aces_backend_protocols.capabilities import BackendManifest
from aces_runtime.registry import BackendRegistry, RuntimeTarget, RuntimeTargetComponents

from .driver import LibvirtDriver
from .drivers.libvirt import LibvirtDeploymentDriver
from .manifest import LIBVIRT_BACKEND_NAME, create_libvirt_manifest
from .provisioner import LibvirtProvisioner


def create_libvirt_components(
    *,
    manifest: BackendManifest,
    driver: LibvirtDriver | None = None,
    **config: Any,
) -> RuntimeTargetComponents:
    """Build libvirt backend components for a manifest."""

    deployment_driver = driver if driver is not None else LibvirtDeploymentDriver(**_driver_config(config))
    if manifest.has_orchestrator or manifest.has_evaluator or manifest.has_participant_runtime:
        raise ValueError("libvirt backend is provisioning-only for issue #601.")
    return RuntimeTargetComponents(provisioner=LibvirtProvisioner(deployment_driver))


def create_libvirt_target(**config: Any) -> RuntimeTarget:
    """Return a fully configured libvirt provisioning target."""

    manifest = create_libvirt_manifest(**config)
    components = create_libvirt_components(manifest=manifest, **config)
    return RuntimeTarget(
        name=LIBVIRT_BACKEND_NAME,
        manifest=manifest,
        provisioner=components.provisioner,
        orchestrator=components.orchestrator,
        evaluator=components.evaluator,
        participant_runtime=components.participant_runtime,
    )


def register_libvirt_backend(registry: BackendRegistry) -> None:
    """Register the libvirt backend descriptor on ``registry``."""

    registry.register(LIBVIRT_BACKEND_NAME, create_libvirt_manifest, create_libvirt_components)


def _driver_config(config: dict[str, Any]) -> dict[str, Any]:
    accepted = {
        "connection",
        "connection_uri",
        "connector",
        "name_prefix",
        "workspace",
        "seed_builder",
    }
    driver_config = {key: value for key, value in config.items() if key in accepted}
    if "uri" in config and "connection_uri" not in driver_config:
        driver_config["connection_uri"] = config["uri"]
    return driver_config
