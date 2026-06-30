"""Backend manifest for the libvirt/QEMU provisioning backend."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

from aces_backend_protocols.capabilities import BackendCapabilitySet, BackendManifest, ProvisionerCapabilities
from aces_contracts.apparatus import ConceptBinding, RealizationSupportDeclaration
from aces_contracts.vocabulary import RealizationSupportMode

LIBVIRT_BACKEND_NAME = "libvirt-qemu"
LIBVIRT_SUPPORTED_CONTRACT_VERSIONS = frozenset(
    {
        "backend-manifest-v2",
        "operation-receipt-v1",
        "operation-status-v1",
        "provisioning-plan-v1",
        "runtime-snapshot-v1",
    }
)


def _current_backend_version() -> str:
    try:
        return distribution_version("aces-sdl")
    except PackageNotFoundError:
        return "0.0.0+unknown"


def create_libvirt_manifest(**config) -> BackendManifest:
    """Return the libvirt backend manifest.

    The manifest declares the *maximum* governed provisioning vocabulary the
    libvirt/QEMU driver realizes through cloud-init: all node types, all OS
    families, all content types (file/dataset/directory), and all account
    features. Because every declared term is genuinely realized, the manifest
    cannot over-claim. "Provisioning-only" here is domain scope only — the
    backend implements the Provisioner protocol, not the orchestrator,
    evaluator, or participant runtime.
    """

    del config
    return BackendManifest(
        name=LIBVIRT_BACKEND_NAME,
        version=_current_backend_version(),
        supported_contract_versions=LIBVIRT_SUPPORTED_CONTRACT_VERSIONS,
        compatible_processors=frozenset({"aces-reference-processor"}),
        concept_bindings=(
            ConceptBinding(scope="capabilities.provisioner.supported_node_types", family="assets"),
            ConceptBinding(scope="capabilities.provisioner.supported_os_families", family="assets"),
            ConceptBinding(scope="capabilities.provisioner.supported_content_types", family="tools-and-artifacts"),
            ConceptBinding(scope="capabilities.provisioner.supported_account_features", family="identities"),
        ),
        realization_support=(
            RealizationSupportDeclaration(
                domain="runtime-realization",
                support_mode=RealizationSupportMode.CONSTRAINED,
                supported_constraint_kinds=frozenset({"node-type", "os-family", "content-type", "account-feature"}),
                supported_exact_requirement_kinds=frozenset({"declared-capability-match"}),
                disclosure_kinds=frozenset(
                    {
                        "backend-manifest-v2",
                        "operation-status-v1",
                        "runtime-snapshot-v1",
                    }
                ),
            ),
        ),
        capabilities=BackendCapabilitySet(
            provisioner=ProvisionerCapabilities(
                name="libvirt-provisioner",
                supported_node_types=frozenset({"switch", "vm"}),
                supported_os_families=frozenset({"linux", "windows", "macos", "freebsd", "other"}),
                supported_content_types=frozenset({"file", "dataset", "directory"}),
                supported_account_features=frozenset(
                    {"groups", "mail", "spn", "shell", "home", "disabled", "auth_method"}
                ),
                max_total_nodes=None,
                supports_acls=True,
                supports_accounts=True,
            )
        ),
    )
