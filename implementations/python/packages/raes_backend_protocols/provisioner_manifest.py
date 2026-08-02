"""Provisioner capability translation for backend manifest contracts."""

from __future__ import annotations

from typing import Any

from raes_contracts.contracts import ProvisionerCapabilitiesModel

from .provisioner_capabilities import ProvisionerCapabilities


def provisioner_capability_payload(provisioner: ProvisionerCapabilities) -> dict[str, Any]:
    """Render portable provisioner capabilities as a contract payload."""

    return {
        "name": provisioner.name,
        "supported_node_types": sorted(provisioner.supported_node_types),
        "supported_os_families": sorted(provisioner.supported_os_families),
        "supported_node_architectures": sorted(provisioner.supported_node_architectures),
        "supported_content_types": sorted(provisioner.supported_content_types),
        "supported_account_features": sorted(provisioner.supported_account_features),
        "supported_domain_profiles": sorted(provisioner.supported_domain_profiles),
        "supported_service_materialization_profiles": sorted(provisioner.supported_service_materialization_profiles),
        "max_total_nodes": provisioner.max_total_nodes,
        "supports_acls": provisioner.supports_acls,
        "supports_accounts": provisioner.supports_accounts,
        "supports_generated_artifacts": provisioner.supports_generated_artifacts,
        "supported_generated_artifact_kinds": sorted(
            kind.value for kind in provisioner.supported_generated_artifact_kinds
        ),
        "supports_persistent_volumes": provisioner.supports_persistent_volumes,
        "constraints": dict(provisioner.constraints),
    }


def provisioner_from_model(model: ProvisionerCapabilitiesModel) -> ProvisionerCapabilities:
    """Restore protocol capabilities from the authoritative contract model."""

    return ProvisionerCapabilities(
        name=model.name,
        supported_node_types=frozenset(model.supported_node_types),
        supported_os_families=frozenset(model.supported_os_families),
        supported_node_architectures=frozenset(model.supported_node_architectures),
        supported_content_types=frozenset(model.supported_content_types),
        supported_account_features=frozenset(model.supported_account_features),
        supported_domain_profiles=frozenset(model.supported_domain_profiles),
        supported_service_materialization_profiles=frozenset(model.supported_service_materialization_profiles),
        max_total_nodes=model.max_total_nodes,
        supports_acls=model.supports_acls,
        supports_accounts=model.supports_accounts,
        supports_generated_artifacts=model.supports_generated_artifacts,
        supported_generated_artifact_kinds=frozenset(model.supported_generated_artifact_kinds),
        supports_persistent_volumes=model.supports_persistent_volumes,
        constraints=dict(model.constraints),
    )


__all__ = ["provisioner_capability_payload", "provisioner_from_model"]
