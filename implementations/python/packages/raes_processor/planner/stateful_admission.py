"""Shared admission for generated-artifact plan payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from raes.stateful_resources import GeneratedArtifact
from raes_backend_protocols.capabilities import ProvisionerCapabilities
from raes_contracts.addressing import render_compiled_address

from ..models import Diagnostic


def generated_artifact_payload_diagnostic(
    *,
    address: str,
    spec: object,
    provisioner: ProvisionerCapabilities,
) -> Diagnostic | None:
    """Validate one compiled or directly submitted generated-artifact spec."""

    try:
        if not isinstance(spec, Mapping):
            raise ValueError("generated artifact spec must be an object")
        canonical_spec: dict[str, Any] = dict(spec)
        consumers = canonical_spec.get("consumers")
        if isinstance(consumers, list):
            canonical_consumers: list[object] = []
            for consumer in consumers:
                if not isinstance(consumer, Mapping):
                    canonical_consumers.append(consumer)
                    continue
                canonical_consumer = dict(consumer)
                target_address = canonical_consumer.pop("target_address", None)
                if target_address is not None and target_address != render_compiled_address(
                    "provision",
                    "node",
                    str(canonical_consumer.get("node", "")),
                ):
                    raise ValueError("generated artifact consumer target_address does not match node")
                canonical_consumers.append(canonical_consumer)
            canonical_spec["consumers"] = canonical_consumers
        artifact = GeneratedArtifact.model_validate(canonical_spec)
    except (TypeError, ValueError):
        return Diagnostic(
            code="provisioner.generated-artifact-invalid",
            domain="provisioning",
            address=address,
            message="Submitted generated artifact payload is invalid.",
        )

    if artifact.generator not in provisioner.supported_generated_artifact_kinds:
        return Diagnostic(
            code="provisioner.unsupported-generated-artifact-kind",
            domain="provisioning",
            address=address,
            message=f"Provisioner does not support generated artifact kind '{artifact.generator.value}'.",
        )
    return None


__all__ = ["generated_artifact_payload_diagnostic"]
