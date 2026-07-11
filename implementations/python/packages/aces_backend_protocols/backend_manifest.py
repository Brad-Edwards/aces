"""Aggregate backend manifest contract built from domain capability types."""

from __future__ import annotations

from dataclasses import dataclass

from aces_contracts.apparatus import ApparatusIdentity, ConceptBinding, RealizationSupportDeclaration
from aces_contracts.manifest_authority import validate_backend_supported_contract_versions
from aces_contracts.realization_envelope import BackendRealizationEnvelopeModel

from .capabilities import (
    BackendCapabilitySet,
    EvaluatorCapabilities,
    ObservationCapabilities,
    OrchestratorCapabilities,
    ParticipantRuntimeCapabilities,
    ProvisionerCapabilities,
)


@dataclass(frozen=True)
class BackendCompatibility:
    """Backend compatibility claims against processor surfaces."""

    processors: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.processors:
            raise ValueError("BackendCompatibility.processors must not be empty")
        if any(not processor.strip() for processor in self.processors):
            raise ValueError("BackendCompatibility.processors must not contain empty strings")


@dataclass(frozen=True, init=False)
class BackendManifest:
    """Complete runtime target capability declaration."""

    identity: ApparatusIdentity
    supported_contract_versions: frozenset[str]
    compatibility: BackendCompatibility
    realization_support: tuple[RealizationSupportDeclaration, ...]
    concept_bindings: tuple[ConceptBinding, ...]
    constraints: dict[str, str]
    capabilities: BackendCapabilitySet
    realization_envelope: BackendRealizationEnvelopeModel | None

    def __init__(
        self,
        *,
        identity: ApparatusIdentity | None = None,
        supported_contract_versions: frozenset[str] = frozenset(),
        compatibility: BackendCompatibility | None = None,
        realization_support: tuple[RealizationSupportDeclaration, ...] = (),
        concept_bindings: tuple[ConceptBinding, ...] = (),
        constraints: dict[str, str] | None = None,
        capabilities: BackendCapabilitySet | None = None,
        name: str | None = None,
        version: str = "0.0.0+unknown",
        compatible_processors: frozenset[str] = frozenset(),
        provisioner: ProvisionerCapabilities | None = None,
        orchestrator: OrchestratorCapabilities | None = None,
        evaluator: EvaluatorCapabilities | None = None,
        participant_runtime: ParticipantRuntimeCapabilities | None = None,
        observation: ObservationCapabilities | None = None,
        realization_envelope: BackendRealizationEnvelopeModel | None = None,
    ) -> None:
        if identity is None:
            if name is None:
                raise ValueError("BackendManifest requires either identity or name.")
            identity = ApparatusIdentity(name=name, version=version)
        if compatibility is None:
            compatibility = BackendCompatibility(processors=frozenset(compatible_processors))
        if capabilities is None:
            if provisioner is None:
                raise ValueError("BackendManifest requires either capabilities or provisioner.")
            capabilities = BackendCapabilitySet(
                provisioner=provisioner,
                orchestrator=orchestrator,
                evaluator=evaluator,
                participant_runtime=participant_runtime,
                observation=observation,
            )
        supported_contract_versions = frozenset(supported_contract_versions)
        if not supported_contract_versions:
            raise ValueError("BackendManifest.supported_contract_versions must not be empty")
        if any(not contract_id.strip() for contract_id in supported_contract_versions):
            raise ValueError("BackendManifest.supported_contract_versions must not contain empty strings")
        validate_backend_supported_contract_versions(supported_contract_versions)
        envelope_contract_declared = "realization-envelope-v1" in supported_contract_versions
        if realization_envelope is not None and not envelope_contract_declared:
            raise ValueError("realization_envelope requires realization-envelope-v1 support")
        if envelope_contract_declared and realization_envelope is None:
            raise ValueError("realization-envelope-v1 support requires realization_envelope")
        realization_support = tuple(realization_support)
        if not realization_support:
            raise ValueError("BackendManifest.realization_support must not be empty")
        concept_bindings = tuple(concept_bindings)
        if not concept_bindings:
            raise ValueError("BackendManifest.concept_bindings must not be empty")
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "supported_contract_versions", supported_contract_versions)
        object.__setattr__(self, "compatibility", compatibility)
        object.__setattr__(self, "realization_support", realization_support)
        object.__setattr__(self, "concept_bindings", concept_bindings)
        object.__setattr__(self, "constraints", {} if constraints is None else dict(constraints))
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "realization_envelope", realization_envelope)

    @property
    def name(self) -> str:
        return self.identity.name

    @property
    def version(self) -> str:
        return self.identity.version

    @property
    def compatible_processors(self) -> frozenset[str]:
        return self.compatibility.processors

    @property
    def provisioner(self) -> ProvisionerCapabilities:
        return self.capabilities.provisioner

    @property
    def orchestrator(self) -> OrchestratorCapabilities | None:
        return self.capabilities.orchestrator

    @property
    def evaluator(self) -> EvaluatorCapabilities | None:
        return self.capabilities.evaluator

    @property
    def participant_runtime(self) -> ParticipantRuntimeCapabilities | None:
        return self.capabilities.participant_runtime

    @property
    def observation(self) -> ObservationCapabilities | None:
        return self.capabilities.observation

    @property
    def has_orchestrator(self) -> bool:
        return self.orchestrator is not None

    @property
    def has_evaluator(self) -> bool:
        return self.evaluator is not None

    @property
    def has_participant_runtime(self) -> bool:
        return self.participant_runtime is not None

    @property
    def has_observation(self) -> bool:
        return self.observation is not None

    @property
    def evaluator_supported_sections(self) -> frozenset[str]:
        return self.evaluator.supported_sections if self.evaluator is not None else frozenset()

    @property
    def supports_scoring(self) -> bool:
        return self.evaluator.supports_scoring if self.evaluator is not None else False

    @property
    def supports_objectives(self) -> bool:
        return self.evaluator.supports_objectives if self.evaluator is not None else False


__all__ = ["BackendCompatibility", "BackendManifest"]
