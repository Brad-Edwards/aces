"""Helpers for rendering backend manifests as external contract payloads."""

from __future__ import annotations

from typing import Any

from aces_contracts.contracts import (
    ApparatusIdentityModel,
    BackendCompatibilityModel,
    BackendManifestV2Model,
    ConceptBindingEntryModel,
    ObservationCapabilitiesModel,
    ParticipantFeatureSupportModel,
    RealizationSupportDeclarationModel,
)
from aces_contracts.manifest_authority import BACKEND_SUPPORTED_CONTRACT_IDS

from .capabilities import BackendManifest


def backend_manifest_v2_model(manifest: BackendManifest) -> BackendManifestV2Model:
    """Render a backend manifest as the authoritative v2 contract model."""

    return BackendManifestV2Model(
        identity=ApparatusIdentityModel(
            name=manifest.identity.name,
            version=manifest.identity.version,
        ),
        supported_contract_versions=[
            contract_id
            for contract_id in BACKEND_SUPPORTED_CONTRACT_IDS
            if contract_id in manifest.supported_contract_versions
        ],
        compatibility=BackendCompatibilityModel(
            processors=sorted(manifest.compatible_processors),
        ),
        realization_support=[
            RealizationSupportDeclarationModel(
                domain=declaration.domain,
                support_mode=declaration.support_mode,
                supported_constraint_kinds=sorted(declaration.supported_constraint_kinds),
                supported_exact_requirement_kinds=sorted(declaration.supported_exact_requirement_kinds),
                disclosure_kinds=sorted(declaration.disclosure_kinds),
                constraints=dict(declaration.constraints),
            )
            for declaration in manifest.realization_support
        ],
        realization_envelope=(
            manifest.realization_envelope.identity.model_dump(mode="json")
            if manifest.realization_envelope is not None
            else None
        ),
        concept_bindings=[
            ConceptBindingEntryModel(scope=binding.scope, family=binding.family)
            for binding in manifest.concept_bindings
        ],
        constraints=dict(manifest.constraints),
        capabilities={
            "provisioner": {
                "name": manifest.provisioner.name,
                "supported_node_types": sorted(manifest.provisioner.supported_node_types),
                "supported_os_families": sorted(manifest.provisioner.supported_os_families),
                "supported_content_types": sorted(manifest.provisioner.supported_content_types),
                "supported_account_features": sorted(manifest.provisioner.supported_account_features),
                "max_total_nodes": manifest.provisioner.max_total_nodes,
                "supports_acls": manifest.provisioner.supports_acls,
                "supports_accounts": manifest.provisioner.supports_accounts,
                "constraints": dict(manifest.provisioner.constraints),
            },
            "orchestrator": (
                {
                    "name": manifest.orchestrator.name,
                    "supported_sections": sorted(manifest.orchestrator.supported_sections),
                    "supports_workflows": manifest.orchestrator.supports_workflows,
                    "supports_condition_refs": manifest.orchestrator.supports_condition_refs,
                    "supports_inject_bindings": manifest.orchestrator.supports_inject_bindings,
                    "supported_workflow_features": sorted(
                        feature for feature in manifest.orchestrator.supported_workflow_features
                    ),
                    "supported_workflow_state_predicates": sorted(
                        feature for feature in manifest.orchestrator.supported_workflow_state_predicates
                    ),
                    "constraints": dict(manifest.orchestrator.constraints),
                }
                if manifest.orchestrator is not None
                else None
            ),
            "evaluator": (
                {
                    "name": manifest.evaluator.name,
                    "supported_sections": sorted(manifest.evaluator.supported_sections),
                    "supports_scoring": manifest.evaluator.supports_scoring,
                    "supports_objectives": manifest.evaluator.supports_objectives,
                    "constraints": dict(manifest.evaluator.constraints),
                }
                if manifest.evaluator is not None
                else None
            ),
            "participant_runtime": (
                {
                    "name": manifest.participant_runtime.name,
                    "supported_participant_roles": sorted(manifest.participant_runtime.supported_participant_roles),
                    "supported_behavior_features": sorted(manifest.participant_runtime.supported_behavior_features),
                    "supported_interaction_features": sorted(
                        manifest.participant_runtime.supported_interaction_features
                    ),
                    "feature_support": [
                        ParticipantFeatureSupportModel(
                            feature=entry.feature,
                            support_level=entry.support_level,
                            constraint_refs=list(entry.constraint_refs),
                            disclosure_refs=list(entry.disclosure_refs),
                        )
                        for entry in manifest.participant_runtime.feature_support
                    ],
                    "constraints": dict(manifest.participant_runtime.constraints),
                }
                if manifest.participant_runtime is not None
                else None
            ),
            "observation": (
                ObservationCapabilitiesModel(
                    name=manifest.observation.name,
                    supported_capture_kinds=sorted(manifest.observation.supported_capture_kinds),
                    supported_channel_kinds=sorted(manifest.observation.supported_channel_kinds),
                    supported_evidence_contracts=sorted(manifest.observation.supported_evidence_contracts),
                    supported_media_types=sorted(manifest.observation.supported_media_types),
                    supported_sealing_modes=sorted(manifest.observation.supported_sealing_modes),
                    supports_redaction=manifest.observation.supports_redaction,
                    supports_loss_disclosure=manifest.observation.supports_loss_disclosure,
                    supports_chain_of_custody=manifest.observation.supports_chain_of_custody,
                    constraints=dict(manifest.observation.constraints),
                ).model_dump(mode="json")
                if manifest.observation is not None
                else None
            ),
        },
    )


def backend_manifest_payload(manifest: BackendManifest) -> dict[str, Any]:
    """Render a backend manifest as JSON-ready data."""

    payload = backend_manifest_v2_model(manifest).model_dump(mode="json")
    if payload.get("realization_envelope") is None:
        payload.pop("realization_envelope", None)
    return payload
