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
    """Return the provisioning-only libvirt backend manifest."""

    del config
    return BackendManifest(
        name=LIBVIRT_BACKEND_NAME,
        version=_current_backend_version(),
        supported_contract_versions=LIBVIRT_SUPPORTED_CONTRACT_VERSIONS,
        compatible_processors=frozenset({"aces-reference-processor"}),
        concept_bindings=(
            ConceptBinding(scope="capabilities.provisioner.supported_node_types", family="assets"),
            ConceptBinding(scope="capabilities.provisioner.supported_os_families", family="assets"),
        ),
        realization_support=(
            RealizationSupportDeclaration(
                domain="runtime-realization",
                support_mode=RealizationSupportMode.CONSTRAINED,
                supported_constraint_kinds=frozenset({"node-type", "os-family"}),
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
                supported_node_types=frozenset({"vm"}),
                supported_os_families=frozenset({"linux", "windows", "freebsd", "other"}),
                supported_content_types=frozenset(),
                supported_account_features=frozenset(),
                max_total_nodes=None,
                supports_acls=False,
                supports_accounts=False,
            )
        ),
    )
