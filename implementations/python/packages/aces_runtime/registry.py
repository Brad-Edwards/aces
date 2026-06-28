"""Registry for runtime targets."""

from collections.abc import Callable
from dataclasses import dataclass
from inspect import Signature, signature
from typing import Any

from aces_backend_protocols.capabilities import BackendManifest
from aces_backend_protocols.protocols import (
    Evaluator,
    Orchestrator,
    ParticipantRuntime,
    Provisioner,
)
from aces_contracts.contracts import (
    ParticipantImplementationManifestModel,
    ParticipantImplementationSelectionModel,
)
from aces_contracts.participant_binding import ParticipantActionAdmissionRequest


def _require_invokable_method(
    component: object | None,
    *,
    label: str,
    method_name: str,
    invocation_args: tuple[object, ...],
) -> None:
    if component is None:
        return
    method = getattr(component, method_name, None)
    if not callable(method):
        raise ValueError(f"registry.target-contract-mismatch: {label} is missing callable method '{method_name}'.")
    try:
        method_signature = signature(method)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"registry.target-contract-mismatch: {label}.{method_name} has a non-inspectable signature."
        ) from exc
    try:
        method_signature.bind(*invocation_args)
    except TypeError as exc:
        rendered_signature = _render_signature(method_signature)
        raise ValueError(
            "registry.target-contract-mismatch: "
            f"{label}.{method_name}{rendered_signature} is incompatible with "
            f"the runtime call shape for {label}.{method_name}."
        ) from exc


def _render_signature(method_signature: Signature) -> str:
    return str(method_signature)


def _validate_runtime_target_shape(
    *,
    manifest: BackendManifest | None,
    provisioner: Provisioner | None,
    orchestrator: Orchestrator | None,
    evaluator: Evaluator | None,
    participant_runtime: ParticipantRuntime | None,
) -> None:
    if manifest is None:
        raise ValueError("RuntimeTarget requires an explicit manifest.")
    if provisioner is None:
        raise ValueError("RuntimeTarget requires a provisioner.")
    _validate_optional_component_presence(
        manifest,
        orchestrator=orchestrator,
        evaluator=evaluator,
        participant_runtime=participant_runtime,
    )
    sample_plan = object()
    sample_snapshot = object()
    sample_request = object()
    sample_admission_request = _sample_participant_action_admission_request()
    _validate_provisioner_methods(provisioner, sample_plan, sample_snapshot)
    _validate_orchestrator_methods(orchestrator, sample_plan, sample_snapshot)
    _validate_evaluator_methods(evaluator, sample_plan, sample_snapshot)
    _validate_participant_runtime_methods(
        participant_runtime, sample_request, sample_admission_request, sample_snapshot
    )


def _validate_optional_component_presence(
    manifest: BackendManifest,
    *,
    orchestrator: Orchestrator | None,
    evaluator: Evaluator | None,
    participant_runtime: ParticipantRuntime | None,
) -> None:
    if manifest.has_orchestrator != (orchestrator is not None):
        raise ValueError("registry.target-shape-mismatch: orchestrator presence does not match the manifest.")
    if manifest.has_evaluator != (evaluator is not None):
        raise ValueError("registry.target-shape-mismatch: evaluator presence does not match the manifest.")
    if manifest.has_participant_runtime != (participant_runtime is not None):
        raise ValueError("registry.target-shape-mismatch: participant_runtime presence does not match the manifest.")


def _validate_provisioner_methods(
    provisioner: Provisioner,
    sample_plan: object,
    sample_snapshot: object,
) -> None:
    _require_invokable_method(
        provisioner,
        label="provisioner",
        method_name="validate",
        invocation_args=(sample_plan,),
    )
    _require_invokable_method(
        provisioner,
        label="provisioner",
        method_name="apply",
        invocation_args=(sample_plan, sample_snapshot),
    )


def _validate_orchestrator_methods(
    orchestrator: Orchestrator | None,
    sample_plan: object,
    sample_snapshot: object,
) -> None:
    _require_invokable_method(
        orchestrator,
        label="orchestrator",
        method_name="start",
        invocation_args=(sample_plan, sample_snapshot),
    )
    _require_invokable_method(
        orchestrator,
        label="orchestrator",
        method_name="status",
        invocation_args=(),
    )
    _require_invokable_method(
        orchestrator,
        label="orchestrator",
        method_name="results",
        invocation_args=(),
    )
    _require_invokable_method(
        orchestrator,
        label="orchestrator",
        method_name="history",
        invocation_args=(),
    )
    _require_invokable_method(
        orchestrator,
        label="orchestrator",
        method_name="stop",
        invocation_args=(sample_snapshot,),
    )


def _validate_evaluator_methods(
    evaluator: Evaluator | None,
    sample_plan: object,
    sample_snapshot: object,
) -> None:
    _require_invokable_method(
        evaluator,
        label="evaluator",
        method_name="start",
        invocation_args=(sample_plan, sample_snapshot),
    )
    _require_invokable_method(
        evaluator,
        label="evaluator",
        method_name="status",
        invocation_args=(),
    )
    _require_invokable_method(
        evaluator,
        label="evaluator",
        method_name="results",
        invocation_args=(),
    )
    _require_invokable_method(
        evaluator,
        label="evaluator",
        method_name="history",
        invocation_args=(),
    )
    _require_invokable_method(
        evaluator,
        label="evaluator",
        method_name="stop",
        invocation_args=(sample_snapshot,),
    )


def _validate_participant_runtime_methods(
    participant_runtime: ParticipantRuntime | None,
    sample_request: object,
    sample_admission_request: ParticipantActionAdmissionRequest,
    sample_snapshot: object,
) -> None:
    _require_invokable_method(
        participant_runtime,
        label="participant_runtime",
        method_name="initialize",
        invocation_args=(sample_request, sample_snapshot),
    )
    _require_invokable_method(
        participant_runtime,
        label="participant_runtime",
        method_name="reset",
        invocation_args=(sample_request, sample_snapshot),
    )
    _require_invokable_method(
        participant_runtime,
        label="participant_runtime",
        method_name="restart",
        invocation_args=(sample_request, sample_snapshot),
    )
    _require_invokable_method(
        participant_runtime,
        label="participant_runtime",
        method_name="terminate",
        invocation_args=(sample_request, sample_snapshot),
    )
    _require_invokable_method(
        participant_runtime,
        label="participant_runtime",
        method_name="admit_action",
        invocation_args=(sample_admission_request, sample_snapshot),
    )
    _require_invokable_method(
        participant_runtime,
        label="participant_runtime",
        method_name="status",
        invocation_args=(),
    )
    _require_invokable_method(
        participant_runtime,
        label="participant_runtime",
        method_name="results",
        invocation_args=(),
    )
    _require_invokable_method(
        participant_runtime,
        label="participant_runtime",
        method_name="history",
        invocation_args=(),
    )


def _sample_participant_action_admission_request() -> ParticipantActionAdmissionRequest:
    manifest = ParticipantImplementationManifestModel.model_validate(
        {
            "schema_version": "participant-implementation-manifest/v1",
            "identity": {"name": "registry-shape-probe", "version": "1.0.0"},
            "implementation_kind": "agent",
            "supported_contract_versions": [
                "participant-implementation-manifest-v1",
                "participant-implementation-provenance-v1",
                "participant-episode-state-envelope-v1",
                "participant-behavior-history-event-stream-v1",
            ],
            "compatibility": {"participant_runtimes": ["registry"], "processors": [], "backends": []},
            "concept_bindings": [
                {"scope": "implementation_kind", "family": "apparatus-declarations"},
                {
                    "scope": "capabilities.supported_participant_contracts",
                    "family": "apparatus-declarations",
                },
                {
                    "scope": "capabilities.supported_decision_surface_modes",
                    "family": "apparatus-declarations",
                },
                {
                    "scope": "capabilities.tool_affordance_expectations",
                    "family": "tools-and-artifacts",
                },
                {"scope": "capabilities.exposure_policy_kinds", "family": "provenance-and-evidence"},
            ],
            "capabilities": {
                "supported_participant_contracts": [
                    "participant-episode-state-envelope-v1",
                    "participant-behavior-history-event-stream-v1",
                ],
                "supported_decision_surface_modes": ["policy-directed"],
                "tool_affordance_expectations": ["shell"],
                "exposure_policy_kinds": ["task-statement"],
            },
        }
    )
    selection = ParticipantImplementationSelectionModel.model_validate(
        {
            "participant_address": "participant.behavior.registry-probe",
            "implementation_identity": {"name": "registry-shape-probe", "version": "1.0.0"},
            "manifest_ref": "registry://participant-implementation-manifest",
            "manifest_digest": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
            "selected_decision_surface_mode": "policy-directed",
            "participant_contract_versions": [
                "participant-episode-state-envelope-v1",
                "participant-behavior-history-event-stream-v1",
            ],
            "exposure_policy": {
                "policy_id": "registry-shape-probe-policy",
                "exposure_policy_kinds": ["task-statement"],
                "disclosed_refs": ["scenario.registry-probe"],
            },
        }
    )
    return ParticipantActionAdmissionRequest(
        participant_address="participant.behavior.registry-probe",
        action_contract_address="participant.action-contract.registry-probe",
        observation_boundary_address="participant.observation-boundary.registry-probe",
        action_instance_id="registry-probe-action",
        implementation_manifest=manifest,
        implementation_selection=selection,
    )


@dataclass(frozen=True)
class RuntimeTarget:
    """A fully configured runtime target."""

    name: str
    manifest: BackendManifest
    provisioner: Provisioner
    orchestrator: Orchestrator | None = None
    evaluator: Evaluator | None = None
    participant_runtime: ParticipantRuntime | None = None

    def __post_init__(self) -> None:
        _validate_runtime_target_shape(
            manifest=self.manifest,
            provisioner=self.provisioner,
            orchestrator=self.orchestrator,
            evaluator=self.evaluator,
            participant_runtime=self.participant_runtime,
        )


@dataclass(frozen=True)
class RuntimeTargetComponents:
    """Instantiated runtime target components without a manifest."""

    provisioner: Provisioner
    orchestrator: Orchestrator | None = None
    evaluator: Evaluator | None = None
    participant_runtime: ParticipantRuntime | None = None


@dataclass(frozen=True)
class RuntimeTargetDescriptor:
    """Factories for manifest introspection and target creation."""

    name: str
    manifest_factory: Callable[..., BackendManifest]
    components_factory: Callable[..., RuntimeTargetComponents]


class BackendRegistry:
    """Registry of runtime target descriptors."""

    def __init__(self) -> None:
        self._descriptors: dict[str, RuntimeTargetDescriptor] = {}

    def register(
        self,
        name: str,
        manifest_factory: Callable[..., BackendManifest],
        components_factory: Callable[..., RuntimeTargetComponents],
    ) -> None:
        if name in self._descriptors:
            raise ValueError(f"Backend '{name}' is already registered and cannot be replaced.")
        self._descriptors[name] = RuntimeTargetDescriptor(
            name=name,
            manifest_factory=manifest_factory,
            components_factory=components_factory,
        )

    def describe(self, name: str) -> RuntimeTargetDescriptor:
        if name not in self._descriptors:
            registered = sorted(self._descriptors)
            raise KeyError(f"Unknown backend '{name}'. Registered backends: {registered}")
        return self._descriptors[name]

    def manifest(self, name: str, **config: Any) -> BackendManifest:
        return self.describe(name).manifest_factory(**config)

    def create(self, name: str, **config: Any) -> RuntimeTarget:
        descriptor = self.describe(name)
        manifest = descriptor.manifest_factory(**config)
        components = descriptor.components_factory(manifest=manifest, **config)

        if hasattr(components, "evaluators"):
            raise ValueError("registry.target-shape-mismatch: legacy evaluator collections are not supported.")

        _validate_runtime_target_shape(
            manifest=manifest,
            provisioner=components.provisioner,
            orchestrator=components.orchestrator,
            evaluator=components.evaluator,
            participant_runtime=components.participant_runtime,
        )

        return RuntimeTarget(
            name=name,
            manifest=manifest,
            provisioner=components.provisioner,
            orchestrator=components.orchestrator,
            evaluator=components.evaluator,
            participant_runtime=components.participant_runtime,
        )

    def list_backends(self) -> list[str]:
        return sorted(self._descriptors)

    def is_registered(self, name: str) -> bool:
        return name in self._descriptors
