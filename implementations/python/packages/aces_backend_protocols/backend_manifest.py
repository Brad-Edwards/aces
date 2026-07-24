"""Aggregate backend manifest contract built from domain capability types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict, TypeVar, Unpack

from aces_contracts.apparatus import ApparatusIdentity, ConceptBinding, RealizationSupportDeclaration
from aces_contracts.manifest_authority import validate_backend_supported_contract_versions
from aces_contracts.realization_envelope import BackendRealizationEnvelopeModel

from .capabilities import (
    BackendCapabilitySet,
    EvaluatorCapabilities,
    HistoricalStateCapabilities,
    LiveActivityCapabilities,
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


class _BackendManifestOptions(TypedDict, total=False):
    identity: ApparatusIdentity | None
    supported_contract_versions: frozenset[str]
    compatibility: BackendCompatibility | None
    realization_support: tuple[RealizationSupportDeclaration, ...]
    concept_bindings: tuple[ConceptBinding, ...]
    constraints: dict[str, str] | None
    capabilities: BackendCapabilitySet | None
    name: str | None
    version: str
    compatible_processors: frozenset[str]
    provisioner: ProvisionerCapabilities | None
    orchestrator: OrchestratorCapabilities | None
    evaluator: EvaluatorCapabilities | None
    participant_runtime: ParticipantRuntimeCapabilities | None
    observation: ObservationCapabilities | None
    historical_state: HistoricalStateCapabilities | None
    live_activity: LiveActivityCapabilities | None
    realization_envelope: BackendRealizationEnvelopeModel | None


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

    def __init__(self, **options: Unpack[_BackendManifestOptions]) -> None:
        _reject_unknown_options(options)
        identity = _resolve_identity(options)
        compatibility = _resolve_compatibility(options)
        capabilities = _resolve_capabilities(options)
        supported_contract_versions = _validate_supported_contract_versions(options)
        realization_envelope = options.get("realization_envelope")
        _validate_realization_envelope_contract(supported_contract_versions, realization_envelope)
        realization_support = _require_non_empty_tuple(options.get("realization_support", ()), "realization_support")
        concept_bindings = _require_non_empty_tuple(options.get("concept_bindings", ()), "concept_bindings")
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "supported_contract_versions", supported_contract_versions)
        object.__setattr__(self, "compatibility", compatibility)
        object.__setattr__(self, "realization_support", realization_support)
        object.__setattr__(self, "concept_bindings", concept_bindings)
        constraints = options.get("constraints")
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
    def historical_state(self) -> HistoricalStateCapabilities | None:
        return self.capabilities.historical_state

    @property
    def live_activity(self) -> LiveActivityCapabilities | None:
        return self.capabilities.live_activity

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


def _reject_unknown_options(options: _BackendManifestOptions) -> None:
    unknown = set(options) - set(_BackendManifestOptions.__annotations__)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise TypeError(f"BackendManifest got unexpected keyword argument(s): {names}")


def _resolve_identity(options: _BackendManifestOptions) -> ApparatusIdentity:
    identity = options.get("identity")
    if identity is not None:
        return identity
    name = options.get("name")
    if name is None:
        raise ValueError("BackendManifest requires either identity or name.")
    return ApparatusIdentity(name=name, version=options.get("version", "0.0.0+unknown"))


def _resolve_compatibility(options: _BackendManifestOptions) -> BackendCompatibility:
    compatibility = options.get("compatibility")
    if compatibility is not None:
        return compatibility
    return BackendCompatibility(processors=frozenset(options.get("compatible_processors", frozenset())))


def _resolve_capabilities(options: _BackendManifestOptions) -> BackendCapabilitySet:
    capabilities = options.get("capabilities")
    if capabilities is not None:
        return capabilities
    provisioner = options.get("provisioner")
    if provisioner is None:
        raise ValueError("BackendManifest requires either capabilities or provisioner.")
    return BackendCapabilitySet(
        provisioner=provisioner,
        orchestrator=options.get("orchestrator"),
        evaluator=options.get("evaluator"),
        participant_runtime=options.get("participant_runtime"),
        observation=options.get("observation"),
        historical_state=options.get("historical_state"),
        live_activity=options.get("live_activity"),
    )


def _validate_supported_contract_versions(options: _BackendManifestOptions) -> frozenset[str]:
    versions = frozenset(options.get("supported_contract_versions", frozenset()))
    if not versions:
        raise ValueError("BackendManifest.supported_contract_versions must not be empty")
    if any(not contract_id.strip() for contract_id in versions):
        raise ValueError("BackendManifest.supported_contract_versions must not contain empty strings")
    validate_backend_supported_contract_versions(versions)
    return versions


def _validate_realization_envelope_contract(
    supported_contract_versions: frozenset[str],
    realization_envelope: BackendRealizationEnvelopeModel | None,
) -> None:
    envelope_contract_declared = "realization-envelope-v1" in supported_contract_versions
    if realization_envelope is not None and not envelope_contract_declared:
        raise ValueError("realization_envelope requires realization-envelope-v1 support")
    if envelope_contract_declared and realization_envelope is None:
        raise ValueError("realization-envelope-v1 support requires realization_envelope")


_T = TypeVar("_T")


def _require_non_empty_tuple(values: tuple[_T, ...], field_name: str) -> tuple[_T, ...]:
    result = tuple(values)
    if not result:
        raise ValueError(f"BackendManifest.{field_name} must not be empty")
    return result


__all__ = ["BackendCompatibility", "BackendManifest"]
