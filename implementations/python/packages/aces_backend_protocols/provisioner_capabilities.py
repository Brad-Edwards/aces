"""Provisioner-specific runtime capability declarations."""

from dataclasses import dataclass, field

from aces_contracts.controlled_vocabularies import validate_controlled_vocabulary_scope_values

PROVISIONER_DOMAIN_PROFILE_SCOPE = "capabilities.provisioner.supported_domain_profiles"
PROVISIONER_SERVICE_MATERIALIZATION_PROFILE_SCOPE = (
    "capabilities.provisioner.supported_service_materialization_profiles"
)


@dataclass(frozen=True)
class ProvisionerCapabilities:
    name: str
    supported_node_types: frozenset[str] = frozenset()
    supported_os_families: frozenset[str] = frozenset()
    supported_content_types: frozenset[str] = frozenset()
    supported_account_features: frozenset[str] = frozenset()
    supported_domain_profiles: frozenset[str] = frozenset()
    supported_service_materialization_profiles: frozenset[str] = frozenset()
    max_total_nodes: int | None = None
    supports_acls: bool = False
    supports_accounts: bool = False
    supports_generated_artifacts: bool = False
    supports_persistent_volumes: bool = False
    constraints: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ProvisionerCapabilities.name must be non-empty")
        if not self.supported_node_types:
            raise ValueError("ProvisionerCapabilities.supported_node_types must not be empty")
        if any(not node_type.strip() for node_type in self.supported_node_types):
            raise ValueError("ProvisionerCapabilities.supported_node_types must not contain empty strings")
        if not self.supported_os_families:
            raise ValueError("ProvisionerCapabilities.supported_os_families must not be empty")
        if any(not os_family.strip() for os_family in self.supported_os_families):
            raise ValueError("ProvisionerCapabilities.supported_os_families must not contain empty strings")
        if any(not content_type.strip() for content_type in self.supported_content_types):
            raise ValueError("ProvisionerCapabilities.supported_content_types must not contain empty strings")
        if any(not feature.strip() for feature in self.supported_account_features):
            raise ValueError("ProvisionerCapabilities.supported_account_features must not contain empty strings")
        if any(not profile.strip() for profile in self.supported_domain_profiles):
            raise ValueError("ProvisionerCapabilities.supported_domain_profiles must not contain empty strings")
        if any(not profile.strip() for profile in self.supported_service_materialization_profiles):
            raise ValueError(
                "ProvisionerCapabilities.supported_service_materialization_profiles must not contain empty strings"
            )
        validate_controlled_vocabulary_scope_values(
            "capabilities.provisioner.supported_node_types",
            self.supported_node_types,
        )
        validate_controlled_vocabulary_scope_values(
            "capabilities.provisioner.supported_os_families",
            self.supported_os_families,
        )
        validate_controlled_vocabulary_scope_values(
            "capabilities.provisioner.supported_content_types",
            self.supported_content_types,
        )
        validate_controlled_vocabulary_scope_values(
            "capabilities.provisioner.supported_account_features",
            self.supported_account_features,
        )
        validate_controlled_vocabulary_scope_values(
            PROVISIONER_DOMAIN_PROFILE_SCOPE,
            self.supported_domain_profiles,
        )
        validate_controlled_vocabulary_scope_values(
            PROVISIONER_SERVICE_MATERIALIZATION_PROFILE_SCOPE,
            self.supported_service_materialization_profiles,
        )
        if self.max_total_nodes is not None and self.max_total_nodes < 1:
            raise ValueError("ProvisionerCapabilities.max_total_nodes must be positive when provided")
        if self.supports_accounts and not self.supported_account_features:
            raise ValueError("ProvisionerCapabilities that support accounts must declare supported_account_features")
        if not self.supports_accounts and self.supported_account_features:
            raise ValueError("supported_account_features require supports_accounts=True")


__all__ = [
    "PROVISIONER_DOMAIN_PROFILE_SCOPE",
    "PROVISIONER_SERVICE_MATERIALIZATION_PROFILE_SCOPE",
    "ProvisionerCapabilities",
]
