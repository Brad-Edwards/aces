"""SEM-218 compiled realization demand, apparatus matching, and disclosure.

The normative boundary is ``explicitness-and-realization.md``. Domain and kind
strings remain opaque; matching is exact membership plus support compatibility.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from raes.artifact_requirements import ArtifactRequirement
from raes.explicitness import ExplicitnessClass, ExplicitnessProvenance
from raes.realization_envelope import effective_constraints, subsumes, tokenize_path
from raes_backend_protocols.capabilities import BackendManifest
from raes_contracts.addressing import require_compiled_address
from raes_contracts.apparatus import (
    DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND,
    RUNTIME_REALIZATION_DOMAIN,
    RealizationSupportDeclaration,
)
from raes_contracts.artifact_requirements import ArtifactAvailabilityContext
from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.planning import ProvisioningPlan
from raes_contracts.realization_envelope import (
    ClosureOverlay,
    EnvelopeBinding,
    EnvelopeScope,
    Posture,
    RealizationEnvelopeModel,
)
from raes_contracts.runtime_state import RealizationProvenanceEntry, RuntimeSnapshot
from raes_contracts.vocabulary import (
    Closure,
    ObservationStrength,
    RealizationSupportMode,
    RealizationVerificationScope,
    verification_scope_satisfies,
)

from .artifact_realization import (
    artifact_requirement_diagnostics,
    evaluate_artifact_realization,
)
from .realization_concerns import (
    CONCERN_PAYLOAD_PATH,
    project_realization_concern,
    registered_realization_concern_descriptors,
    registered_realization_concerns,
    resolve_realization_concern,
)
from .realization_process_limits import (
    ProcessResourceLimitDemand,
    RealizationValueConstraint,
    process_resource_limit_support_diagnostic,
)
from .realization_runtime_evaluation import evaluate_registered_realization
from .realization_snapshot_sanitization import (
    sanitize_realization_snapshot,
)

__all__ = [
    "CONCERN_PAYLOAD_PATH",
    "EXACT_REQUIREMENT_KIND",
    "REALIZATION_DOMAIN",
    "ApparatusRealizationDefaultResolver",
    "CompiledRealizationRequirement",
    "ProcessResourceLimitDemand",
    "RealizationValueConstraint",
    "artifact_requirement_diagnostics",
    "materialize_realization_requirements",
    "project_realization_concern",
    "realization_disclosure",
    "realization_envelope_diagnostics",
    "realization_support_diagnostics",
    "registered_realization_concern_descriptors",
    "registered_realization_concerns",
    "resolve_realization_concern",
    "sanitize_realization_snapshot",
]

_BACKEND_CONTRACT_INVALID = "runtime.backend-contract-invalid"

# The single coarse realization domain string already published by backend
# manifests (see ``raes_backend_stubs.stubs``). Kept opaque per the SEM-218
# extensibility seam.
REALIZATION_DOMAIN = RUNTIME_REALIZATION_DOMAIN

# The exact-requirement kind every concrete (exact) author declaration maps to.
# A backend that honors exact declarations lists this in
# ``supported_exact_requirement_kinds``; one that cannot must reject (I2).
EXACT_REQUIREMENT_KIND = DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND


@dataclass(frozen=True)
class CompiledRealizationRequirement:
    """A compiled realization concern carrying its SEM-218 explicitness class.

    Owned by ``RuntimeModel`` as model-side metadata; like compiled capability
    constraints, it never enters the backend-facing
    ``resource_payload()`` envelope — and consumed directly by the planner gate.
    """

    field_path: str
    address: str
    domain: str
    requirement_kind: str
    explicitness: ExplicitnessClass | None
    provenance: ExplicitnessProvenance
    governing_scope: str | None = None
    delegated: bool = False
    artifact_requirement: ArtifactRequirement | None = None
    verification_scope: RealizationVerificationScope | None = None
    required_observation_strength: ObservationStrength | None = None
    value_constraints: tuple[RealizationValueConstraint, ...] = ()
    process_resource_limits: tuple[ProcessResourceLimitDemand, ...] = ()

    def __post_init__(self) -> None:
        require_compiled_address(self.address)
        if self.delegated != (self.explicitness is None):
            raise ValueError("delegated realization requirements must carry unresolved explicitness")
        if self.verification_scope is not None and not isinstance(
            self.verification_scope,
            RealizationVerificationScope,
        ):
            raise TypeError("verification_scope must be RealizationVerificationScope")
        if self.required_observation_strength is not None and not isinstance(
            self.required_observation_strength,
            ObservationStrength,
        ):
            raise TypeError("required_observation_strength must be ObservationStrength")
        if self.requirement_kind != "process-resource-limits" and (
            self.value_constraints or self.process_resource_limits
        ):
            raise ValueError("process-limit realization metadata requires process-resource-limits")
        if self.artifact_requirement is not None:
            if self.requirement_kind != "source-artifact":
                raise ValueError("artifact_requirement requires requirement_kind='source-artifact'")
            if self.explicitness is not self.artifact_requirement.explicitness:
                raise ValueError("compiled artifact requirement explicitness must match its source contract")


ApparatusRealizationDefaultResolver = Callable[
    [CompiledRealizationRequirement, BackendManifest],
    Closure,
]


def _closed_apparatus_default(
    _requirement: CompiledRealizationRequirement,
    _manifest: BackendManifest,
) -> Closure:
    return Closure.CLOSED_WORLD


def _effective_explicitness(
    requirement: CompiledRealizationRequirement,
    manifest: BackendManifest,
    apparatus_default: ApparatusRealizationDefaultResolver | None,
) -> ExplicitnessClass | None:
    if not requirement.delegated:
        return requirement.explicitness
    resolver = apparatus_default or _closed_apparatus_default
    closure = resolver(requirement, manifest)
    return ExplicitnessClass.OPEN if closure is Closure.OPEN_WORLD else None


def materialize_realization_requirements(
    requirements: tuple[CompiledRealizationRequirement, ...],
    manifest: BackendManifest,
    *,
    apparatus_default: ApparatusRealizationDefaultResolver | None = None,
) -> tuple[CompiledRealizationRequirement, ...]:
    """Resolve selected-apparatus delegation into the execution carrier."""

    materialized: list[CompiledRealizationRequirement] = []
    for requirement in requirements:
        if requirement.delegated:
            if _effective_explicitness(requirement, manifest, apparatus_default) is not ExplicitnessClass.OPEN:
                # A closed default carries no realizable demand into execution.
                continue
            requirement = replace(
                requirement,
                explicitness=ExplicitnessClass.OPEN,
                delegated=False,
            )
        materialized.append(requirement)
    return tuple(materialized)


def realization_support_diagnostics(
    requirements: tuple[CompiledRealizationRequirement, ...],
    manifest: BackendManifest,
    *,
    apparatus_default: ApparatusRealizationDefaultResolver | None = None,
) -> list[Diagnostic]:
    """Match compiled requirements against the manifest's ``realization_support``.

    Exact requirements need ``EXACT_REQUIREMENT_KIND`` in some matching-domain
    declaration's ``supported_exact_requirement_kinds``; constrained
    requirements need their concern kind in ``supported_constraint_kinds``.
    Unsupported kinds become stable error diagnostics naming the resource
    address, SDL field path, requirement kind, and missing capability. Open
    requirements require an explicit ``open-realization`` apparatus claim;
    unresolved delegation uses the agreed closed fallback.

    Diagnostics deliberately name only the field path and kind strings, never
    the exact author value, which may carry sensitive material (SEM-218
    security / host-exposure gate).
    """

    return [
        diagnostic
        for requirement in requirements
        if (
            diagnostic := _realization_support_diagnostic(
                requirement,
                manifest,
                apparatus_default,
            )
        )
        is not None
    ]


def _realization_support_diagnostic(
    requirement: CompiledRealizationRequirement,
    manifest: BackendManifest,
    apparatus_default: ApparatusRealizationDefaultResolver | None,
) -> Diagnostic | None:
    explicitness = _effective_explicitness(requirement, manifest, apparatus_default)
    declarations = [
        declaration for declaration in manifest.realization_support if declaration.domain == requirement.domain
    ]
    if requirement.requirement_kind == "process-resource-limits":
        diagnostic = process_resource_limit_support_diagnostic(
            requirement,
            declarations,
            explicitness,
            manifest.realization_envelope,
        )
    elif explicitness is ExplicitnessClass.OPEN:
        diagnostic = _open_support_diagnostic(requirement, declarations)
    elif explicitness is ExplicitnessClass.EXACT:
        diagnostic = _exact_support_diagnostic(requirement, declarations)
    elif explicitness is ExplicitnessClass.CONSTRAINED:
        diagnostic = _constraint_support_diagnostic(requirement, declarations)
    else:
        diagnostic = None
    return diagnostic


def _open_support_diagnostic(
    requirement: CompiledRealizationRequirement,
    declarations: list[RealizationSupportDeclaration],
) -> Diagnostic | None:
    if any(declaration.support_mode is RealizationSupportMode.OPEN_REALIZATION for declaration in declarations):
        return None
    return Diagnostic(
        code="realization.unsupported-open-requirement",
        domain=requirement.domain,
        address=requirement.address,
        message=(
            "Backend declares no open realization support for "
            f"'{requirement.requirement_kind}' requirement at "
            f"'{requirement.field_path}' in domain '{requirement.domain}'."
        ),
        severity=Severity.ERROR,
    )


def _exact_support_diagnostic(
    requirement: CompiledRealizationRequirement,
    declarations: list[RealizationSupportDeclaration],
) -> Diagnostic | None:
    exact_declarations = [
        declaration
        for declaration in declarations
        if EXACT_REQUIREMENT_KIND in declaration.supported_exact_requirement_kinds
    ]
    if not exact_declarations:
        return Diagnostic(
            code="realization.unsupported-exact-requirement",
            domain=requirement.domain,
            address=requirement.address,
            message=(
                f"Backend declares no exact realization support ('{EXACT_REQUIREMENT_KIND}') for exact "
                f"'{requirement.requirement_kind}' requirement at '{requirement.field_path}' in domain "
                f"'{requirement.domain}'."
            ),
            severity=Severity.ERROR,
        )
    if requirement.verification_scope is None or any(
        (capability := declaration.observation_capabilities.get(requirement.requirement_kind)) is not None
        and verification_scope_satisfies(capability.verification_scope, requirement.verification_scope)
        for declaration in exact_declarations
    ):
        return None
    return Diagnostic(
        code="realization.under-observed-exact-requirement",
        domain=requirement.domain,
        address=requirement.address,
        message=(
            f"Backend declares no '{requirement.verification_scope.value}' corroboration "
            f"for exact '{requirement.requirement_kind}' requirement at "
            f"'{requirement.field_path}' in domain '{requirement.domain}'."
        ),
        severity=Severity.ERROR,
    )


def _constraint_support_diagnostic(
    requirement: CompiledRealizationRequirement,
    declarations: list[RealizationSupportDeclaration],
) -> Diagnostic | None:
    if any(requirement.requirement_kind in declaration.supported_constraint_kinds for declaration in declarations):
        return None
    return Diagnostic(
        code="realization.unsupported-constraint-requirement",
        domain=requirement.domain,
        address=requirement.address,
        message=(
            "Backend declares no constraint realization support "
            f"for constraint kind '{requirement.requirement_kind}' at "
            f"'{requirement.field_path}' in domain '{requirement.domain}'."
        ),
        severity=Severity.ERROR,
    )


def realization_envelope_diagnostics(
    requirements: tuple[CompiledRealizationRequirement, ...],
    manifest: BackendManifest,
    *,
    apparatus_default: ApparatusRealizationDefaultResolver | None = None,
) -> list[Diagnostic]:
    """Check open compiled demand against the offered envelope via subsumption."""

    carrier = manifest.realization_envelope
    if carrier is None:
        return []
    open_paths = tuple(
        requirement.field_path
        for requirement in requirements
        if _effective_explicitness(requirement, manifest, apparatus_default) is ExplicitnessClass.OPEN
    )
    if not open_paths:
        return []
    requested = _open_request_envelope(open_paths)
    offered = _offered_open_projection(carrier.expression, open_paths)
    return list(subsumes(offered, requested).diagnostics)


def _open_request_envelope(paths: tuple[str, ...]) -> RealizationEnvelopeModel:
    return RealizationEnvelopeModel(
        id="compiled-open-realization-request",
        scope=EnvelopeScope.SCENARIO,
        bindings=[
            EnvelopeBinding(path=path, scope=EnvelopeScope.FIELD, posture=Posture.OPEN) for path in sorted(set(paths))
        ],
    )


def _offered_open_projection(
    offered: RealizationEnvelopeModel,
    paths: tuple[str, ...],
) -> RealizationEnvelopeModel:
    constraints, closed = effective_constraints(offered)
    domains = {}
    bindings = []
    for index, path in enumerate(sorted(set(paths))):
        constraint = constraints.get(path)
        if constraint is None:
            continue
        domain_name = f"offered-domain-{index}"
        domains[domain_name] = constraint.domain
        bindings.append(
            EnvelopeBinding(
                path=path,
                scope=EnvelopeScope.FIELD,
                posture=constraint.posture,
                domain=domain_name,
                overrideable=constraint.overrideable,
            )
        )
    excludes_open_path = any(_closed_scope_excludes(path, closed) for path in paths)
    closure = (
        [
            ClosureOverlay(
                path="",
                scope=EnvelopeScope.SCENARIO,
                closure=Closure.CLOSED_WORLD,
            )
        ]
        if excludes_open_path
        else []
    )
    return RealizationEnvelopeModel(
        id=f"{offered.id}.open-demand-projection",
        scope=offered.scope,
        domains=domains,
        bindings=bindings,
        closure=closure,
    )


def _closed_scope_excludes(path: str, closed: dict[str, set[str]]) -> bool:
    target = tuple(tokenize_path(path))
    for scope_path, admitted_children in closed.items():
        scope = tuple(tokenize_path(scope_path)) if scope_path else ()
        if len(scope) >= len(target) or target[: len(scope)] != scope:
            continue
        child = target[len(scope)]
        if not isinstance(child, str) or child not in admitted_children:
            return True
    return False


def realization_disclosure(
    requirements: tuple[CompiledRealizationRequirement, ...],
    declared_plan: ProvisioningPlan,
    returned_snapshot: RuntimeSnapshot,
    *,
    manifest: BackendManifest | None = None,
    artifact_availability: ArtifactAvailabilityContext | None = None,
) -> tuple[list[Diagnostic], tuple[RealizationProvenanceEntry, ...]]:
    """SEM-218 runtime non-approximation gate (I2) + provenance disclosure (I5).

    Compares each compiled realization concern's author-declared value (from the
    provisioning plan the processor emitted) against the value the backend
    realized in its returned snapshot. For an exact concern, a backend that
    realizes a *different* value — or *omits* the value entirely (a returned
    snapshot with no entry for the resource, or an entry missing the concern
    field) — is a silent approximation and yields a rejecting
    ``runtime.backend-contract-invalid`` diagnostic. Absent *backend* evidence is
    not a non-event: an exact declaration the backend never realized is exactly
    the I2 failure this gate exists to catch. This is the spec's Execution-phase
    non-approximation rule.

    Absent *plan-side* evidence is different and is not a backend fault: when the
    plan declares no provisioning op for the resource, removes it (a ``DELETE``
    op — expected absence), or carries no value for the concern, there is no
    author baseline for this run to enforce, so the requirement is skipped.

    Every honoured/realized concern is recorded as a
    ``RealizationProvenanceEntry``: ``author-declared`` when the backend honoured
    the declaration, ``backend-realized`` when it realized a different value for
    a constrained surface. Diagnostics and entries name the field path and kind
    only, never the realized value (SEM-218 host-exposure gate).

    This is the runtime sibling of ``realization_support_diagnostics``: the
    planner gate rejects an unrealizable exact requirement before deployment;
    this gate rejects a backend that realized one dishonestly. The runtime
    adapter (``raes_runtime``) invokes it at the backend-call boundary.
    """

    diagnostics: list[Diagnostic] = []
    provenance: list[RealizationProvenanceEntry] = []
    declared_ops = {op.address: op for op in declared_plan.operations}
    for requirement in requirements:
        if requirement.artifact_requirement is not None:
            diagnostic, entry = evaluate_artifact_realization(
                requirement,
                declared_ops,
                returned_snapshot,
                manifest=manifest,
                availability=artifact_availability,
            )
        else:
            diagnostic, entry = evaluate_registered_realization(
                requirement,
                declared_ops,
                returned_snapshot,
                manifest=manifest,
            )
        if diagnostic is not None:
            diagnostics.append(diagnostic)
        if entry is not None:
            provenance.append(entry)
    return diagnostics, tuple(provenance)
