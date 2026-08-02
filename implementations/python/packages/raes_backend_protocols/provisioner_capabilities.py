"""Provisioner-specific runtime capability declarations."""

from dataclasses import dataclass, field

from raes_contracts.controlled_vocabularies import validate_controlled_vocabulary_scope_values
from raes_contracts.vocabulary import GeneratedArtifactKind

PROVISIONER_DOMAIN_PROFILE_SCOPE = "capabilities.provisioner.supported_domain_profiles"
PROVISIONER_SERVICE_MATERIALIZATION_PROFILE_SCOPE = (
    "capabilities.provisioner.supported_service_materialization_profiles"
)


def _require_string_values(name: str, values: frozenset[str], *, required: bool = False) -> None:
    if required and not values:
        raise ValueError(f"ProvisionerCapabilities.{name} must not be empty")
    if any(not value.strip() for value in values):
        raise ValueError(f"ProvisionerCapabilities.{name} must not contain empty strings")


def _validate_account_support(capabilities: "ProvisionerCapabilities") -> None:
    if capabilities.supports_accounts and not capabilities.supported_account_features:
        raise ValueError("ProvisionerCapabilities that support accounts must declare supported_account_features")
    if not capabilities.supports_accounts and capabilities.supported_account_features:
        raise ValueError("supported_account_features require supports_accounts=True")


@dataclass(frozen=True)
class ProvisionerCapabilities:
    name: str
    supported_node_types: frozenset[str] = frozenset()
    supported_os_families: frozenset[str] = frozenset()
    supported_node_architectures: frozenset[str] = frozenset()
    supported_content_types: frozenset[str] = frozenset()
    supported_account_features: frozenset[str] = frozenset()
    supported_domain_profiles: frozenset[str] = frozenset()
    supported_service_materialization_profiles: frozenset[str] = frozenset()
    max_total_nodes: int | None = None
    supports_acls: bool = False
    supports_accounts: bool = False
    supports_generated_artifacts: bool = False
    supported_generated_artifact_kinds: frozenset[GeneratedArtifactKind] = frozenset()
    supports_persistent_volumes: bool = False
    constraints: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ProvisionerCapabilities.name must be non-empty")
        _require_string_values("supported_node_types", self.supported_node_types, required=True)
        _require_string_values("supported_os_families", self.supported_os_families, required=True)
        _require_string_values("supported_node_architectures", self.supported_node_architectures)
        _require_string_values("supported_content_types", self.supported_content_types)
        _require_string_values("supported_account_features", self.supported_account_features)
        _require_string_values("supported_domain_profiles", self.supported_domain_profiles)
        _require_string_values(
            "supported_service_materialization_profiles",
            self.supported_service_materialization_profiles,
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
            "capabilities.provisioner.supported_node_architectures",
            self.supported_node_architectures,
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
        _validate_account_support(self)
        try:
            normalized_artifact_kinds = frozenset(
                GeneratedArtifactKind(kind) for kind in self.supported_generated_artifact_kinds
            )
        except ValueError as exc:
            raise ValueError("ProvisionerCapabilities contains an unknown generated artifact kind") from exc
        object.__setattr__(self, "supported_generated_artifact_kinds", normalized_artifact_kinds)
        if self.supports_generated_artifacts and not normalized_artifact_kinds:
            raise ValueError(
                "ProvisionerCapabilities that support generated artifacts must declare "
                "supported_generated_artifact_kinds"
            )
        if not self.supports_generated_artifacts and normalized_artifact_kinds:
            raise ValueError(
                "ProvisionerCapabilities supported_generated_artifact_kinds require supports_generated_artifacts=True"
            )


__all__ = [
    "PROVISIONER_DOMAIN_PROFILE_SCOPE",
    "PROVISIONER_SERVICE_MATERIALIZATION_PROFILE_SCOPE",
    "ProvisionerCapabilities",
]
