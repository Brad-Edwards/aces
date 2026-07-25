"""Reference emulation backend (RUN-314).

A concrete, container-backed reference backend implementing the four
``raes_backend_protocols.protocols`` roles (Provisioner, Orchestrator,
Evaluator, ParticipantRuntime). It publishes identity/capability through
the standard ``BackendManifest`` and registers on the existing
``BackendRegistry`` descriptor seam under the name ``reference-emulation``.

The default driver is the hermetic in-process driver; an opt-in OCI driver
realizes plans against a real container runtime (docker/podman). Only
portable RAES facts ever reach manifests, snapshots, diagnostics, or
conformance reports -- never container/VM/network ids, host paths,
environment, credentials, argv, or backend-native reprs.
"""

from __future__ import annotations

from .driver import (
    ContainerHandle,
    ContainerSpec,
    DeploymentDriver,
    NetworkHandle,
    NetworkSpec,
    ServiceSpec,
)
from .manifest import REFERENCE_BACKEND_NAME, create_reference_backend_manifest
from .realization import Realization, interpret_provisioning_plan
from .target import (
    create_reference_backend_components,
    create_reference_backend_target,
    register_reference_backend,
)

__all__ = [
    "REFERENCE_BACKEND_NAME",
    "ContainerHandle",
    "ContainerSpec",
    "DeploymentDriver",
    "NetworkHandle",
    "NetworkSpec",
    "ServiceSpec",
    "Realization",
    "create_reference_backend_components",
    "create_reference_backend_manifest",
    "create_reference_backend_target",
    "interpret_provisioning_plan",
    "register_reference_backend",
]
