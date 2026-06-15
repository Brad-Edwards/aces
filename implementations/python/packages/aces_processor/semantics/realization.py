"""SEM-218 realization-support semantics: typed compiled requirements and the
manifest-bound planner gate.

The normative boundary lives in
``specs/formal/realization/explicitness-and-realization.md``. The compiler
lowers each authored realization concern into a
``CompiledRealizationRequirement`` carrying its SEM-218 explicitness class
(part 1's ``aces_sdl.explicitness`` classifier output). The planner consumes
that compiled metadata directly and matches it against the selected backend's
``realization_support`` declarations. An unsupported exact or constrained
requirement kind becomes a stable error ``Diagnostic`` before deployment,
enforcing invariants I1/I2/I4 without silent approximation.

The match is a single manifest-bound helper over
``BackendManifest.realization_support`` / ``RealizationSupportDeclaration``.
``domain`` and the kind strings are opaque non-empty strings today (the
extensibility seam; a governed vocabulary is future work), so matching is
exact string membership plus support-mode compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass

from aces_backend_protocols.capabilities import BackendManifest
from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import ChangeAction, ProvisioningPlan, ProvisionOp
from aces_contracts.runtime_state import RealizationProvenanceEntry, RuntimeSnapshot
from aces_sdl.explicitness import ExplicitnessClass, ExplicitnessProvenance

__all__ = [
    "CONCERN_PAYLOAD_PATH",
    "EXACT_REQUIREMENT_KIND",
    "REALIZATION_DOMAIN",
    "CompiledRealizationRequirement",
    "realization_disclosure",
    "realization_support_diagnostics",
    "resolve_realization_concern",
]

_BACKEND_CONTRACT_INVALID = "runtime.backend-contract-invalid"
_MISSING_CONCERN_VALUE = object()

# The single coarse realization domain string already published by backend
# manifests (see ``aces_backend_stubs.stubs``). Kept opaque per the SEM-218
# extensibility seam.
REALIZATION_DOMAIN = "runtime-realization"

# The exact-requirement kind every concrete (exact) author declaration maps to.
# A backend that honors exact declarations lists this in
# ``supported_exact_requirement_kinds``; one that cannot must reject (I2).
EXACT_REQUIREMENT_KIND = "declared-capability-match"

# Authored realization concerns mapped onto the published constraint-kind
# vocabulary, keyed by (head section, leaf field) of the classifier path. The
# node/content instance name is the wildcard middle segment. This is the
# realization-concern set the planner already validates against backend
# capabilities — not a general per-field designation authority (that is staged
# under the SEM-218 coverage row).
_CONCERN_KIND_BY_PATH: dict[tuple[str, str], str] = {
    ("nodes", "os"): "os-family",
    ("nodes", "type"): "node-type",
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
}


@dataclass(frozen=True)
class CompiledRealizationRequirement:
    """A compiled realization concern carrying its SEM-218 explicitness class.

    Owned by ``RuntimeModel`` as model-side metadata — like the existing
    ``node_variable_refs`` provenance it never enters the backend-facing
    ``resource_payload()`` envelope — and consumed directly by the planner gate.
    """

    field_path: str
    address: str
    domain: str
    requirement_kind: str
    explicitness: ExplicitnessClass


def resolve_realization_concern(field_path: str) -> str | None:
    """Return the realization concern kind for a classifier path, or ``None``.

    Only the concerns the planner validates against backend capabilities map to
    a kind today; every other authored field is not a realization concern with
    a published kind and yields ``None``.
    """

    parts = field_path.split(".")
    if len(parts) != 3:
        return None
    head, _name, leaf = parts
    return _CONCERN_KIND_BY_PATH.get((head, leaf))


def realization_support_diagnostics(
    requirements: tuple[CompiledRealizationRequirement, ...],
    manifest: BackendManifest,
) -> list[Diagnostic]:
    """Match compiled requirements against the manifest's ``realization_support``.

    Exact requirements need ``EXACT_REQUIREMENT_KIND`` in some matching-domain
    declaration's ``supported_exact_requirement_kinds``; constrained
    requirements need their concern kind in ``supported_constraint_kinds``.
    Unsupported kinds become stable error diagnostics naming the resource
    address, SDL field path, requirement kind, and missing capability. Open
    requirements are not emitted by the compiler and so are not gated here.

    Diagnostics deliberately name only the field path and kind strings, never
    the exact author value, which may carry sensitive material (SEM-218
    security / host-exposure gate).
    """

    diagnostics: list[Diagnostic] = []
    for requirement in requirements:
        declarations = [
            declaration for declaration in manifest.realization_support if declaration.domain == requirement.domain
        ]
        if requirement.explicitness is ExplicitnessClass.EXACT:
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
        elif requirement.explicitness is ExplicitnessClass.CONSTRAINED:
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

    path = CONCERN_PAYLOAD_PATH.get(requirement.requirement_kind)
    if path is None:
        return None, None
    op = declared_ops.get(requirement.address)
    # No realization is owed when the plan declares no op for this resource or
    # removes it (a DELETE op — expected absence); neither is a backend fault.
    if op is None or op.action is ChangeAction.DELETE:
        return None, None
    declared_value = _concern_value(op.payload, path)
    if declared_value is _MISSING_CONCERN_VALUE:
        # The plan op carries no value for this concern: no author baseline to
        # enforce (an upstream processor invariant, not a backend contract).
        return None, None
    snapshot_entry = returned_snapshot.entries.get(requirement.address)
    realized_value = (
        _concern_value(snapshot_entry.payload, path) if snapshot_entry is not None else _MISSING_CONCERN_VALUE
    )
    honoured = realized_value == declared_value
    if requirement.explicitness is ExplicitnessClass.EXACT and not honoured:
        # The backend realized the exact concern with a different value or omitted
        # it entirely; both are forbidden silent approximation (I2).
        return _silent_approximation_diagnostic(requirement), None
    if realized_value is _MISSING_CONCERN_VALUE:
        # A non-exact concern the backend left unrealized: nothing to disclose.
        return None, None
    return None, _realization_provenance_entry(requirement, honoured)


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
        provenance=(ExplicitnessProvenance.AUTHOR_DECLARED if honoured else ExplicitnessProvenance.BACKEND_REALIZED),
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
