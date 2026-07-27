"""Backend manifest for the libvirt/QEMU provisioning backend."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

from raes_backend_protocols.capabilities import (
    PARTICIPANT_RUNTIME_POLICY_FEATURES,
    BackendCapabilitySet,
    BackendManifest,
    ParticipantFeatureSupport,
    ParticipantRuntimeCapabilities,
    ProvisionerCapabilities,
)
from raes_contracts.apparatus import ConceptBinding, RealizationSupportDeclaration
from raes_contracts.vocabulary import ParticipantFeatureSupportLevel, RealizationSupportMode

from .envelopes import LibvirtDriverMode, load_libvirt_realization_envelope

LIBVIRT_BACKEND_NAME = "libvirt-qemu"


def _provisioner_capabilities(mode: LibvirtDriverMode) -> ProvisionerCapabilities:
    """Derive the coarse manifest projection from the selected governed envelope."""

    envelope = load_libvirt_realization_envelope(mode)
    configuration = envelope.configuration
    account_features = frozenset(configuration.supported_account_features)
    return ProvisionerCapabilities(
        name=(
            "libvirt-techvault-appliance-provisioner"
            if mode is LibvirtDriverMode.TECHVAULT_APPLIANCE
            else "libvirt-provisioner"
        ),
        supported_node_types=frozenset(configuration.supported_node_types),
        supported_os_families=frozenset(configuration.supported_os_families),
        supported_content_types=frozenset(configuration.supported_content_types),
        supported_account_features=account_features,
        supported_domain_profiles=frozenset(configuration.supported_domain_profiles),
        supported_service_materialization_profiles=frozenset(),
        max_total_nodes=None,
        supports_acls=configuration.supports_acls,
        supports_accounts=bool(account_features),
    )


# Compatibility exports remain, but their values are derived from the normative
# envelope artifacts so manifest and execution gates cannot drift independently.
LIBVIRT_PROVISIONER_CAPABILITIES = _provisioner_capabilities(LibvirtDriverMode.GENERIC)
TECHVAULT_PROVISIONER_CAPABILITIES = _provisioner_capabilities(LibvirtDriverMode.TECHVAULT_APPLIANCE)

_LIBVIRT_BASE_CONTRACT_VERSIONS = frozenset(
    {
        "backend-manifest-v2",
        "realization-envelope-v1",
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
        return distribution_version("raes")
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
            *(
                ParticipantFeatureSupport(
                    feature=feature,
                    support_level=ParticipantFeatureSupportLevel.UNSUPPORTED,
                    limitation_refs=(f"limitation:{feature}:not-realized",),
                    disclosure_refs=(disclosure_ref,),
                )
                for feature in sorted(PARTICIPANT_RUNTIME_POLICY_FEATURES)
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

    The manifest projects its governed provisioning vocabulary from the
    configuration-selected envelope. Generic qcow2/cloud-init and TechVault
    appliance modes therefore disclose distinct capabilities. "Provisioning-only"
    is domain scope only: by default the backend implements the Provisioner
    protocol, not the orchestrator or evaluator. Pass ``participant_runtime=True``
    to additionally declare participant episode support.
    """
    enable_participant_runtime = bool(config.get("participant_runtime", False))
    mode = LibvirtDriverMode(str(config.get("driver_mode", LibvirtDriverMode.GENERIC.value)))
    realization_envelope = load_libvirt_realization_envelope(mode)
    provisioner_capabilities = _provisioner_capabilities(mode)

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
        compatible_processors=frozenset({"raes-reference-processor"}),
        concept_bindings=(
            ConceptBinding(scope="capabilities.provisioner.supported_node_types", family="assets"),
            ConceptBinding(scope="capabilities.provisioner.supported_os_families", family="assets"),
            ConceptBinding(scope="capabilities.provisioner.supported_content_types", family="tools-and-artifacts"),
            ConceptBinding(scope="capabilities.provisioner.supported_account_features", family="identities"),
            ConceptBinding(scope="capabilities.provisioner.supported_domain_profiles", family="identities"),
            ConceptBinding(
                scope="capabilities.provisioner.supported_service_materialization_profiles",
                family="tools-and-artifacts",
            ),
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
            provisioner=provisioner_capabilities,
            participant_runtime=participant_runtime_cap,
        ),
        realization_envelope=realization_envelope,
    )
