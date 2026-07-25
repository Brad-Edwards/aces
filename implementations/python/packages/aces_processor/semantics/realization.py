"""SEM-218 compiled realization demand, apparatus matching, and disclosure.

The normative boundary is ``explicitness-and-realization.md``. Domain and kind
strings remain opaque; matching is exact membership plus support compatibility.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace

from aces_backend_protocols.capabilities import BackendManifest
from aces_contracts.addressing import require_compiled_address
from aces_contracts.apparatus import (
    DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND,
    RUNTIME_REALIZATION_DOMAIN,
)
from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import ChangeAction, ProvisioningPlan, ProvisionOp
from aces_contracts.realization_envelope import (
    ClosureOverlay,
    EnvelopeBinding,
    EnvelopeScope,
    Posture,
    RealizationEnvelopeModel,
)
from aces_contracts.runtime_state import RealizationProvenanceEntry, RuntimeSnapshot
from aces_contracts.vocabulary import Closure, RealizationSupportMode
from raes.explicitness import ExplicitnessClass, ExplicitnessProvenance
from raes.realization_envelope import effective_constraints, subsumes, tokenize_path

__all__ = [
    "CONCERN_PAYLOAD_PATH",
    "EXACT_REQUIREMENT_KIND",
    "REALIZATION_DOMAIN",
    "ApparatusRealizationDefaultResolver",
    "CompiledRealizationRequirement",
    "materialize_realization_requirements",
    "realization_disclosure",
    "realization_envelope_diagnostics",
    "realization_support_diagnostics",
    "registered_realization_concerns",
    "resolve_realization_concern",
]

_BACKEND_CONTRACT_INVALID = "runtime.backend-contract-invalid"
_MISSING_CONCERN_VALUE = object()

# The single coarse realization domain string already published by backend
# manifests (see ``aces_backend_stubs.stubs``). Kept opaque per the SEM-218
# extensibility seam.
REALIZATION_DOMAIN = RUNTIME_REALIZATION_DOMAIN

# The exact-requirement kind every concrete (exact) author declaration maps to.
# A backend that honors exact declarations lists this in
# ``supported_exact_requirement_kinds``; one that cannot must reject (I2).
EXACT_REQUIREMENT_KIND = DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND

# Authored realization concerns mapped onto the published constraint-kind
# vocabulary, keyed by (head section, leaf field) of the classifier path. The
# node/content instance name is the wildcard middle segment. This is the
# realization-concern set the planner already validates against backend
# capabilities — not a general per-field designation authority (that is staged
# under the SEM-218 coverage row).
_CONCERN_KIND_BY_PATH: dict[tuple[str, str], str] = {
    ("nodes", "type"): "node-type",
    ("nodes", "os"): "os-family",
    ("content", "type"): "content-type",
}

# Where each realization concern's realized value lives inside the backend's
# provisioning resource payload (``resource_payload``). The runtime
# non-approximation gate uses this to locate the value the backend realized for
# an exact concern and compare it against the author declaration. Mirrors the
# concern set in ``_CONCERN_KIND_BY_PATH``; a concern absent here is not gated at
# runtime (no published payload slot to compare).
CONCERN_PAYLOAD_PATH: dict[str, tuple[str, ...]] = {
    "os-family": ("os_family",),
    "node-type": ("node_type",),
    "content-type": ("spec", "type"),
    "domain-topology": ("domain_topology",),
    "generated-artifact": ("spec",),
    "persistent-volume": ("spec",),
    "service-content-materialization": ("service_materialization",),
}


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

    def __post_init__(self) -> None:
        require_compiled_address(self.address)
        if self.delegated != (self.explicitness is None):
            raise ValueError("delegated realization requirements must carry unresolved explicitness")


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


def registered_realization_concerns(
    *,
    declaration_names: Mapping[str, Iterable[str]],
) -> tuple[tuple[str, str, str, str], ...]:
    """Enumerate ``(section, declaration, leaf, kind)`` registrations."""

    return tuple(
        (section, declaration_name, leaf_field, concern_kind)
        for (section, leaf_field), concern_kind in _CONCERN_KIND_BY_PATH.items()
        for declaration_name in declaration_names.get(section, ())
    )


def resolve_realization_concern(
    field_path: str,
    *,
    declaration_names: Mapping[str, Iterable[str]],
) -> str | None:
    """Return the realization concern kind for a classifier path, or ``None``.

    Only the concerns the planner validates against backend capabilities map to
    a kind today; every other authored field is not a realization concern with
    a published kind and yields ``None``.
    """

    for section, declaration_name, leaf_field, concern_kind in registered_realization_concerns(
        declaration_names=declaration_names
    ):
        if field_path == f"{section}.{declaration_name}.{leaf_field}":
            return concern_kind
    return None


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

    diagnostics: list[Diagnostic] = []
    for requirement in requirements:
        explicitness = _effective_explicitness(requirement, manifest, apparatus_default)
        declarations = [
            declaration for declaration in manifest.realization_support if declaration.domain == requirement.domain
        ]
        if explicitness is ExplicitnessClass.OPEN:
            supported = any(
                declaration.support_mode is RealizationSupportMode.OPEN_REALIZATION for declaration in declarations
            )
            if not supported:
                diagnostics.append(
                    Diagnostic(
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
                )
            continue
        if explicitness is ExplicitnessClass.EXACT:
            supported = any(
                EXACT_REQUIREMENT_KIND in declaration.supported_exact_requirement_kinds for declaration in declarations
            )
            if not supported:
                diagnostics.append(
                    Diagnostic(
                        code="realization.unsupported-exact-requirement",
                        domain=requirement.domain,
                        address=requirement.address,
                        message=(
                            f"Backend declares no exact realization support "
                            f"('{EXACT_REQUIREMENT_KIND}') for exact "
                            f"'{requirement.requirement_kind}' requirement at "
                            f"'{requirement.field_path}' in domain "
                            f"'{requirement.domain}'."
                        ),
                        severity=Severity.ERROR,
                    )
                )
        elif explicitness is ExplicitnessClass.CONSTRAINED:
            supported = any(
                requirement.requirement_kind in declaration.supported_constraint_kinds for declaration in declarations
            )
            if not supported:
                diagnostics.append(
                    Diagnostic(
                        code="realization.unsupported-constraint-requirement",
                        domain=requirement.domain,
                        address=requirement.address,
                        message=(
                            f"Backend declares no constraint realization support "
                            f"for constraint kind '{requirement.requirement_kind}' at "
                            f"'{requirement.field_path}' in domain "
                            f"'{requirement.domain}'."
                        ),
                        severity=Severity.ERROR,
                    )
                )
    return diagnostics


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
    adapter (``aces_runtime``) invokes it at the backend-call boundary.
    """

    diagnostics: list[Diagnostic] = []
    provenance: list[RealizationProvenanceEntry] = []
    declared_ops = {op.address: op for op in declared_plan.operations}
    for requirement in requirements:
        diagnostic, entry = _evaluate_realization(requirement, declared_ops, returned_snapshot)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
        if entry is not None:
            provenance.append(entry)
    return diagnostics, tuple(provenance)


def _evaluate_realization(
    requirement: CompiledRealizationRequirement,
    declared_ops: dict[str, ProvisionOp],
    returned_snapshot: RuntimeSnapshot,
) -> tuple[Diagnostic | None, RealizationProvenanceEntry | None]:
    """Gate one compiled requirement against its realized value.

    Returns ``(diagnostic, entry)`` where at most one is non-None: a diagnostic
    for an exact requirement the backend realized dishonestly, or a provenance
    entry for a located realized concern. Both are None when there is no author
    baseline to enforce (no plan op / a ``DELETE`` op / no declared value) or
    when a non-exact concern was left unrealized.
    """

    diagnostic: Diagnostic | None = None
    entry: RealizationProvenanceEntry | None = None
    path = CONCERN_PAYLOAD_PATH.get(requirement.requirement_kind)
    op = declared_ops.get(requirement.address)
    if requirement.explicitness is None or path is None or op is None or op.action is ChangeAction.DELETE:
        return diagnostic, entry
    snapshot_entry = returned_snapshot.entries.get(requirement.address)
    realized_value = (
        _concern_value(snapshot_entry.payload, path) if snapshot_entry is not None else _MISSING_CONCERN_VALUE
    )
    if requirement.explicitness is ExplicitnessClass.OPEN:
        if realized_value is not _MISSING_CONCERN_VALUE:
            entry = _realization_provenance_entry(requirement, False)
        return diagnostic, entry
    declared_value = _concern_value(op.payload, path)
    if declared_value is not _MISSING_CONCERN_VALUE:
        honoured = realized_value == declared_value
        if requirement.explicitness is ExplicitnessClass.EXACT and not honoured:
            # The backend realized the exact concern with a different value or omitted
            # it entirely; both are forbidden silent approximation (I2).
            diagnostic = _silent_approximation_diagnostic(requirement)
        elif realized_value is not _MISSING_CONCERN_VALUE:
            # A located realized concern: disclose its provenance. (A non-exact concern
            # the backend left unrealized falls through with nothing to disclose.)
            entry = _realization_provenance_entry(requirement, honoured)
    return diagnostic, entry


def _realization_provenance_entry(
    requirement: CompiledRealizationRequirement,
    honoured: bool,
) -> RealizationProvenanceEntry:
    return RealizationProvenanceEntry(
        address=requirement.address,
        field_path=requirement.field_path,
        domain=requirement.domain,
        requirement_kind=requirement.requirement_kind,
        explicitness=requirement.explicitness,
        provenance=(requirement.provenance if honoured else ExplicitnessProvenance.BACKEND_REALIZED),
        governing_scope=requirement.governing_scope,
    )


def _silent_approximation_diagnostic(requirement: CompiledRealizationRequirement) -> Diagnostic:
    return Diagnostic(
        code=_BACKEND_CONTRACT_INVALID,
        domain=requirement.domain,
        address=requirement.address,
        message=(
            f"Backend did not realize the exact '{requirement.requirement_kind}' requirement at "
            f"'{requirement.field_path}' as the author declared it (the realized value is absent "
            f"or differs); silent approximation or omission of an exact declaration is forbidden "
            f"(SEM-218 I2)."
        ),
        severity=Severity.ERROR,
    )


def _concern_value(payload: dict[str, object], path: tuple[str, ...]) -> object:
    current: object = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return _MISSING_CONCERN_VALUE
        current = current[key]
    return current
