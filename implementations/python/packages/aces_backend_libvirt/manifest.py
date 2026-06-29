"""Backend manifest for the libvirt/QEMU provisioning backend."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

from aces_backend_protocols.capabilities import (
    BackendCapabilitySet,
    BackendManifest,
    ParticipantFeatureSupport,
    ParticipantRuntimeCapabilities,
    ProvisionerCapabilities,
)
from aces_contracts.apparatus import ConceptBinding, RealizationSupportDeclaration
from aces_contracts.vocabulary import ParticipantFeatureSupportLevel, RealizationSupportMode

LIBVIRT_BACKEND_NAME = "libvirt-qemu"

_LIBVIRT_BASE_CONTRACT_VERSIONS = frozenset(
    {
        "backend-manifest-v2",
        "operation-receipt-v1",
        "operation-status-v1",
        "provisioning-plan-v1",
        "runtime-snapshot-v1",
    }
)

_LIBVIRT_PARTICIPANT_CONTRACT_VERSIONS = frozenset(
    {
        "participant-episode-state-envelope-v1",
        "participant-episode-history-event-stream-v1",
        "participant-behavior-history-event-stream-v1",
        "participant-shared-state-record-v1",
        "participant-joint-action-record-v1",
        "participant-time-management-context-v1",
    }
)

# Union used when participant_runtime=True is requested
LIBVIRT_SUPPORTED_CONTRACT_VERSIONS = _LIBVIRT_BASE_CONTRACT_VERSIONS

_LIBVIRT_PARTICIPANT_RUNTIME_DISCLOSURE_REF = "docs/decisions/issue-614-libvirt-participant-runtime.md"


def _current_backend_version() -> str:
    try:
        return distribution_version("aces-sdl")
    except PackageNotFoundError:
        return "0.0.0+unknown"


def _participant_runtime_capabilities() -> ParticipantRuntimeCapabilities:
    """Return ParticipantRuntimeCapabilities for the libvirt deterministic participant runtime."""
    disclosure_ref = _LIBVIRT_PARTICIPANT_RUNTIME_DISCLOSURE_REF
    return ParticipantRuntimeCapabilities(
        name="libvirt-deterministic-participant-runtime",
        supported_participant_roles=frozenset({"red"}),
        supported_behavior_features=frozenset(
            {
                "action_contracts",
                "observation_boundaries",
                "behavior_history",
                "state_transitions",
            }
        ),
        supported_interaction_features=frozenset({"contention"}),
        feature_support=(
            ParticipantFeatureSupport(
                feature="action_contracts",
                support_level=ParticipantFeatureSupportLevel.DISCLOSED_WEAK,
                disclosure_refs=(disclosure_ref,),
            ),
            ParticipantFeatureSupport(
                feature="observation_boundaries",
                support_level=ParticipantFeatureSupportLevel.DISCLOSED_WEAK,
                disclosure_refs=(disclosure_ref,),
            ),
            ParticipantFeatureSupport(
                feature="behavior_history",
                support_level=ParticipantFeatureSupportLevel.DISCLOSED_WEAK,
                disclosure_refs=(disclosure_ref,),
            ),
            ParticipantFeatureSupport(
                feature="state_transitions",
                support_level=ParticipantFeatureSupportLevel.DISCLOSED_WEAK,
                disclosure_refs=(disclosure_ref,),
            ),
            ParticipantFeatureSupport(
                feature="contention",
                support_level=ParticipantFeatureSupportLevel.DISCLOSED_WEAK,
                disclosure_refs=(disclosure_ref,),
            ),
        ),
        constraints={
            "simulation_disclosure": (
                "deterministic-simulation: no live libvirt domain execution; "
                "see docs/decisions/issue-614-libvirt-participant-runtime.md"
            )
        },
    )


def create_libvirt_manifest(**config: object) -> BackendManifest:
    """Return the libvirt backend manifest.

    Pass ``participant_runtime=True`` to declare participant episode support
    (``LibvirtParticipantRuntime`` with the deterministic domain adapter).
    Without the flag the manifest remains provisioning-only.
    """
    enable_participant_runtime = bool(config.get("participant_runtime", False))

    supported_contract_versions = (
        _LIBVIRT_BASE_CONTRACT_VERSIONS | _LIBVIRT_PARTICIPANT_CONTRACT_VERSIONS
        if enable_participant_runtime
        else _LIBVIRT_BASE_CONTRACT_VERSIONS
    )

    participant_runtime_cap = _participant_runtime_capabilities() if enable_participant_runtime else None

    return BackendManifest(
        name=LIBVIRT_BACKEND_NAME,
        version=_current_backend_version(),
        supported_contract_versions=supported_contract_versions,
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
                supported_node_types=frozenset({"switch", "vm"}),
                supported_os_families=frozenset({"linux", "windows", "freebsd", "other"}),
                supported_content_types=frozenset(),
                supported_account_features=frozenset(),
                max_total_nodes=None,
                supports_acls=False,
                supports_accounts=False,
            ),
            participant_runtime=participant_runtime_cap,
        ),
    )
