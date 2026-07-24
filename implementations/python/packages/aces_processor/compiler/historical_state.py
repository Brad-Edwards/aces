"""Compiler projection for deterministic historical semantic addresses."""

from __future__ import annotations

from aces_contracts.contracts.historical_state import (
    HistoricalBaselineDigestModel,
    HistoricalSemanticAddressContextModel,
    HistoricalSemanticAddressModel,
)
from aces_contracts.historical_addressing import (
    derive_historical_baseline_digest,
    derive_historical_semantic_addresses,
)
from aces_sdl.scenario import InstantiatedScenario
from aces_sdl.semantics.domain_topology import resolve_section_ref
from aces_sdl.semantics.historical_state import historical_object_ref


def compile_historical_object_addresses(
    scenario: InstantiatedScenario,
) -> dict[str, HistoricalSemanticAddressModel]:
    """Derive one address per admitted semantic object without plan resources."""

    entries: list[tuple[str, HistoricalSemanticAddressContextModel]] = []
    for baseline_id in sorted(scenario.historical_baselines):
        baseline = scenario.historical_baselines[baseline_id]
        tenant_id = resolve_section_ref(
            baseline.deployment_tenant_ref,
            "deployment_tenants",
            scenario.deployment_tenants,
        )
        if tenant_id is None:
            raise ValueError("admitted historical baseline has an unresolved deployment tenant")
        for object_id in sorted(baseline.objects):
            entries.append(
                (
                    historical_object_ref(baseline_id, object_id),
                    HistoricalSemanticAddressContextModel(
                        address_profile=baseline.address_profile,
                        range_instance_id=baseline.range_instance_id,
                        deployment_tenant_id=tenant_id,
                        reset_generation_id=baseline.reset_generation_id,
                        baseline_id=baseline_id,
                        baseline_version=baseline.version,
                        object_id=object_id,
                    ),
                )
            )
    derived = derive_historical_semantic_addresses(context for _address, context in entries)
    return {
        declaration_address: semantic_address
        for (declaration_address, _context), semantic_address in zip(entries, derived, strict=True)
    }


def compile_historical_baseline_digests(
    scenario: InstantiatedScenario,
) -> dict[str, HistoricalBaselineDigestModel]:
    """Derive one complete digest carrier per admitted historical baseline."""

    return {
        baseline_id: derive_historical_baseline_digest(baseline_id, scenario.historical_baselines[baseline_id])
        for baseline_id in sorted(scenario.historical_baselines)
    }


__all__ = ["compile_historical_baseline_digests", "compile_historical_object_addresses"]
