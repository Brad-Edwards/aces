"""Observation-capability admission for authored realization demands."""

from raes_contracts.apparatus import RealizationSupportDeclaration
from raes_contracts.vocabulary import observation_strength_satisfies, verification_scope_satisfies

from .realization_requirement import CompiledRealizationRequirement


def has_required_observation_support(
    requirement: CompiledRealizationRequirement,
    declarations: list[RealizationSupportDeclaration],
    *,
    observation_kind: str,
) -> bool:
    """Return whether one declaration meets the requirement's evidence floor."""

    return any(
        (capability := declaration.observation_capabilities.get(observation_kind)) is not None
        and (
            requirement.verification_scope is None
            or verification_scope_satisfies(capability.verification_scope, requirement.verification_scope)
        )
        and (
            requirement.required_observation_strength is None
            or observation_strength_satisfies(
                capability.observation_strength,
                requirement.required_observation_strength,
            )
        )
        for declaration in declarations
    )
