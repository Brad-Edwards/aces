"""Exact offline resolution for caller-supplied domain-profile definitions."""

from __future__ import annotations

from dataclasses import dataclass

from ._domain_profile_contracts import (
    DomainProfileCoordinateModel,
    DomainProfileDefinitionModel,
    DomainProfileDefinitionProvenanceModel,
    DomainProfileResolutionContextModel,
    DomainProfileResolutionOutcome,
)
from .diagnostics import Diagnostic


@dataclass(frozen=True, slots=True)
class DomainProfileDefinitionResolution:
    outcome: DomainProfileResolutionOutcome
    definition: DomainProfileDefinitionModel | None
    provenance: DomainProfileDefinitionProvenanceModel | None
    diagnostics: tuple[Diagnostic, ...]

    @property
    def resolved(self) -> bool:
        return self.outcome is DomainProfileResolutionOutcome.RESOLVED


def _resolution_failure(
    outcome: DomainProfileResolutionOutcome,
    message: str,
) -> DomainProfileDefinitionResolution:
    return DomainProfileDefinitionResolution(
        outcome=outcome,
        definition=None,
        provenance=None,
        diagnostics=(
            Diagnostic(
                code=f"domain-profile.{outcome.value}",
                domain="domain-profile",
                address="#",
                message=message,
            ),
        ),
    )


def resolve_domain_profile_definition(
    coordinate: DomainProfileCoordinateModel,
    context: DomainProfileResolutionContextModel,
) -> DomainProfileDefinitionResolution:
    """Resolve one exact profile from supplied local data without discovery."""

    namespace_rows = [
        admission for admission in context.namespace_admissions if admission.namespace == coordinate.namespace
    ]
    admitted_authorities = {admission.authority for admission in namespace_rows}
    if len(admitted_authorities) > 1:
        return _resolution_failure(
            DomainProfileResolutionOutcome.NAMESPACE_COLLISION,
            "the profile namespace resolves to conflicting admitted authorities",
        )
    if admitted_authorities != {coordinate.authority}:
        return _resolution_failure(
            DomainProfileResolutionOutcome.NAMESPACE_UNADMITTED,
            "the profile namespace is not admitted for the requested authority",
        )

    identity_matches = [
        item
        for item in context.definitions
        if item.definition.coordinate.namespace == coordinate.namespace
        and item.definition.coordinate.authority == coordinate.authority
        and item.definition.coordinate.profile_id == coordinate.profile_id
    ]
    if not identity_matches:
        return _resolution_failure(
            DomainProfileResolutionOutcome.DEFINITION_UNAVAILABLE,
            "the requested profile definition is absent from the supplied local context",
        )

    revision_matches = [item for item in identity_matches if item.definition.coordinate.revision == coordinate.revision]
    if not revision_matches:
        return _resolution_failure(
            DomainProfileResolutionOutcome.INCOMPATIBLE_REVISION,
            "the supplied profile definitions do not contain the exact requested revision",
        )

    available_digests = {item.definition.coordinate.definition_digest for item in revision_matches}
    if len(available_digests) > 1:
        return _resolution_failure(
            DomainProfileResolutionOutcome.COORDINATE_COLLISION,
            "the same logical profile coordinate resolves to conflicting definition digests",
        )
    exact = [
        item
        for item in revision_matches
        if item.definition.coordinate.definition_digest == coordinate.definition_digest
    ]
    if not exact:
        return _resolution_failure(
            DomainProfileResolutionOutcome.DIGEST_MISMATCH,
            "the supplied profile definition digest does not match the exact request",
        )
    if len(exact) > 1:
        return _resolution_failure(
            DomainProfileResolutionOutcome.COORDINATE_COLLISION,
            "the exact profile coordinate resolves to multiple supplied definitions",
        )
    selected = exact[0]
    return DomainProfileDefinitionResolution(
        outcome=DomainProfileResolutionOutcome.RESOLVED,
        definition=selected.definition,
        provenance=selected.provenance,
        diagnostics=(),
    )
