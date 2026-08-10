"""Backend-manifest adapters for typed portable process-limit domains."""

from collections.abc import Iterable

from raes_contracts.apparatus import ProcessResourceLimitCapability
from raes_contracts.contracts.capabilities import ProcessResourceLimitCapabilityModel


def process_resource_limit_models(
    capabilities: Iterable[ProcessResourceLimitCapability],
) -> list[ProcessResourceLimitCapabilityModel]:
    """Render typed apparatus declarations into published contract models."""

    return [
        ProcessResourceLimitCapabilityModel(
            resource=capability.resource,
            scopes=sorted(capability.scopes, key=lambda scope: scope.value),
            minimum=capability.minimum,
            maximum=capability.maximum,
            supports_unlimited=capability.supports_unlimited,
        )
        for capability in capabilities
    ]


def process_resource_limit_capabilities(
    models: Iterable[ProcessResourceLimitCapabilityModel],
) -> tuple[ProcessResourceLimitCapability, ...]:
    """Restore published process-limit domains to internal declarations."""

    return tuple(
        ProcessResourceLimitCapability(
            resource=model.resource,
            scopes=frozenset(model.scopes),
            minimum=model.minimum,
            maximum=model.maximum,
            supports_unlimited=model.supports_unlimited,
        )
        for model in models
    )
