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
from aces_sdl.explicitness import ExplicitnessClass

__all__ = [
    "EXACT_REQUIREMENT_KIND",
    "REALIZATION_DOMAIN",
    "CompiledRealizationRequirement",
    "realization_support_diagnostics",
    "resolve_realization_concern",
]

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
