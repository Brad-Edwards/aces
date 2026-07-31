"""Shared deterministic report and SDL-selection helpers."""

from __future__ import annotations

from collections.abc import Mapping

from raes_contracts.canonical import canonical_json_digest
from raes_contracts.contracts import (
    ArtifactTransformationCheckModel,
    ArtifactTransformationKind,
    ArtifactTransformationLossKind,
    ArtifactTransformationLossModel,
    ArtifactTransformationPreservationModel,
    ArtifactTransformationReportModel,
    ArtifactTransformationStatus,
    PreservationOutcome,
    TransformationCheckOutcome,
)
from raes_contracts.diagnostics import Diagnostic, Severity, diagnostic_model

from ._declarations import Declaration, DeclarationIndex
from ._module_symbols import HASHMAP_SECTIONS
from ._transformation_types import (
    ArtifactTransformationPolicy,
    RemoveSDLDeclarationRequest,
    RenameSDLDeclarationRequest,
    SDLAuthoringArtifact,
    SDLTransformationResult,
)
from .canonical import SDLCanonicalDigest

REPORT_DOMAIN = "artifact-transformation"
RENAME_PROFILE = "rename-sdl-declaration/v1"
REMOVE_PROFILE = "remove-sdl-declaration/v1"
IDENTITY_TRANSPORT_PROFILE = "sdl-declaration-identity-transport/v1"
EXPLICIT_LOSS_PROFILE = "explicit-loss-accounting/v1"
CANONICAL_IDENTITY_PROFILE = "canonical-artifact-identity"
PORTABLE_CANONICAL_PROFILE = "rfc8785-jcs-sha256/v1"
PORTABLE_CANONICALIZE_PROFILE = "canonicalize-portable-contract/v1"
SDL_CONTRACT_PROFILE = "sdl-authoring-input/v1"
DEFAULT_POLICY_PAYLOAD: dict[str, list[str]] = {"allowed_loss_kinds": []}


def diagnostic(
    code: str,
    message: str,
    *,
    address: str = "",
    severity: Severity = Severity.ERROR,
):
    return diagnostic_model(
        Diagnostic(
            code=code,
            domain=REPORT_DOMAIN,
            address=address,
            message=message,
            severity=severity,
        )
    )


def check(
    check_id: str,
    outcome: TransformationCheckOutcome,
    *diagnostic_codes: str,
) -> ArtifactTransformationCheckModel:
    return ArtifactTransformationCheckModel(
        check_id=check_id,
        outcome=outcome,
        diagnostic_codes=tuple(sorted(set(diagnostic_codes))),
    )


def default_policy_digest() -> str:
    return canonical_json_digest(DEFAULT_POLICY_PAYLOAD)


def transformation_policy_digest(policy: ArtifactTransformationPolicy) -> str:
    return canonical_json_digest({"allowed_loss_kinds": [item.value for item in policy.allowed_loss_kinds]})


def rename_derivation_digest(
    *,
    source_digest: str,
    policy_digest: str,
    request: RenameSDLDeclarationRequest,
) -> str:
    return canonical_json_digest(
        {
            "operation_profile": RENAME_PROFILE,
            "policy_digest": policy_digest,
            "request": {
                "new_local_name": request.new_local_name,
                "target_address": request.target_address,
            },
            "source_digest": source_digest,
        }
    )


def remove_derivation_digest(
    *,
    source_digest: str,
    policy_digest: str,
    request: RemoveSDLDeclarationRequest,
) -> str:
    return canonical_json_digest(
        {
            "operation_profile": REMOVE_PROFILE,
            "policy_digest": policy_digest,
            "request": {"target_address": request.target_address},
            "source_digest": source_digest,
        }
    )


def refused_rename(
    *,
    source_digest: SDLCanonicalDigest,
    request: RenameSDLDeclarationRequest,
    diagnostic_code: str,
    message: str,
    passed_checks: tuple[str, ...] = ("source-admitted",),
    affected_identities: tuple[str, ...] = (),
) -> SDLTransformationResult:
    policy_digest = default_policy_digest()
    failed_check = {
        "artifact-transformation.target-not-exact": "target-exact",
        "artifact-transformation.target-unsupported": "target-supported",
        "artifact-transformation.identity-collision": "target-injective",
        "artifact-transformation.linked-artifact-stale": "linked-artifacts-current",
        "artifact-transformation.target-invalid": "target-admitted",
        "artifact-transformation.preservation-failed": "round-trip-canonical-identity",
    }.get(diagnostic_code, "target-admitted")
    checks = [check(check_id, TransformationCheckOutcome.PASSED) for check_id in passed_checks]
    checks.append(check(failed_check, TransformationCheckOutcome.FAILED, diagnostic_code))
    report = ArtifactTransformationReportModel(
        operation_profile=RENAME_PROFILE,
        status=ArtifactTransformationStatus.REFUSED,
        artifact_kind=ArtifactTransformationKind.SDL_AUTHORING,
        source_profile=SDL_CONTRACT_PROFILE,
        target_profile=SDL_CONTRACT_PROFILE,
        canonicalization_profile=source_digest.profile,
        source_digest=source_digest.value,
        policy_digest=policy_digest,
        derivation_digest=rename_derivation_digest(
            source_digest=source_digest.value,
            policy_digest=policy_digest,
            request=request,
        ),
        preconditions=tuple(sorted(checks, key=lambda item: item.check_id)),
        affected_identities=tuple(sorted(set(affected_identities))),
        preservation=ArtifactTransformationPreservationModel(
            profile=IDENTITY_TRANSPORT_PROFILE,
            outcome=PreservationOutcome.FAILED,
            limitations=("Finite verification does not establish behavioral equivalence.",),
        ),
        diagnostics=(diagnostic(diagnostic_code, message, address="/request/target_address"),),
    )
    return SDLTransformationResult(output=None, binding_documents=(), report=report)


def top_level_declaration(
    scenario: SDLAuthoringArtifact,
    index: DeclarationIndex,
    address: str,
) -> tuple[Declaration, str, str] | None:
    declaration = index.declaration_for(address)
    if declaration is None or "." not in address:
        return None
    section, local_key = address.split(".", 1)
    if section not in HASHMAP_SECTIONS:
        return None
    section_value = getattr(scenario, section, None)
    if not isinstance(section_value, Mapping) or local_key not in section_value:
        return None
    if declaration.model_path != f"{section}.{local_key}":
        return None
    return declaration, section, local_key


def removal_loss(
    target_address: str,
    *,
    severity: Severity,
) -> ArtifactTransformationLossModel:
    return ArtifactTransformationLossModel(
        kind=ArtifactTransformationLossKind.DECLARATION_REMOVED,
        affected_identity=target_address,
        diagnostic=diagnostic(
            "artifact-transformation.declaration-removed",
            "The selected declaration is absent from the transformed artifact.",
            severity=severity,
        ),
    )


def refused_removal(
    *,
    source_digest: SDLCanonicalDigest,
    request: RemoveSDLDeclarationRequest,
    policy: ArtifactTransformationPolicy,
    diagnostic_code: str,
    message: str,
    passed_checks: tuple[str, ...] = ("source-admitted",),
    include_loss: bool = False,
) -> SDLTransformationResult:
    policy_digest = transformation_policy_digest(policy)
    failed_check = {
        "artifact-transformation.target-not-exact": "target-exact",
        "artifact-transformation.loss-not-authorized": "loss-authorized",
        "artifact-transformation.target-invalid": "target-admitted",
        "artifact-transformation.linked-artifact-unsupported": "linked-artifacts-supported",
    }.get(diagnostic_code, "target-admitted")
    checks = [check(check_id, TransformationCheckOutcome.PASSED) for check_id in passed_checks]
    checks.append(check(failed_check, TransformationCheckOutcome.FAILED, diagnostic_code))
    report = ArtifactTransformationReportModel(
        operation_profile=REMOVE_PROFILE,
        status=ArtifactTransformationStatus.REFUSED,
        artifact_kind=ArtifactTransformationKind.SDL_AUTHORING,
        source_profile=SDL_CONTRACT_PROFILE,
        target_profile=SDL_CONTRACT_PROFILE,
        canonicalization_profile=source_digest.profile,
        source_digest=source_digest.value,
        policy_digest=policy_digest,
        derivation_digest=remove_derivation_digest(
            source_digest=source_digest.value,
            policy_digest=policy_digest,
            request=request,
        ),
        preconditions=tuple(sorted(checks, key=lambda item: item.check_id)),
        affected_identities=(request.target_address,),
        preservation=ArtifactTransformationPreservationModel(
            profile=EXPLICIT_LOSS_PROFILE,
            outcome=PreservationOutcome.NOT_APPLICABLE,
            limitations=("Removal does not preserve the selected declaration.",),
        ),
        losses=((removal_loss(request.target_address, severity=Severity.ERROR),) if include_loss else ()),
        diagnostics=(diagnostic(diagnostic_code, message, address="/request/target_address"),),
    )
    return SDLTransformationResult(output=None, binding_documents=(), report=report)


__all__ = [
    "CANONICAL_IDENTITY_PROFILE",
    "DEFAULT_POLICY_PAYLOAD",
    "EXPLICIT_LOSS_PROFILE",
    "IDENTITY_TRANSPORT_PROFILE",
    "PORTABLE_CANONICAL_PROFILE",
    "PORTABLE_CANONICALIZE_PROFILE",
    "REMOVE_PROFILE",
    "RENAME_PROFILE",
    "SDL_CONTRACT_PROFILE",
    "check",
    "default_policy_digest",
    "refused_removal",
    "refused_rename",
    "removal_loss",
    "remove_derivation_digest",
    "rename_derivation_digest",
    "top_level_declaration",
    "transformation_policy_digest",
]
