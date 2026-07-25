"""MCP access to scientific-scenario intended-use profiles."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from aces_mcp.tools.operation_support import json_response

if TYPE_CHECKING:
    from aces_contracts.scientific_completeness import CompletenessProfileModel, ProfileCompletenessResult


def _authoring_tools(profile_id: str) -> list[str]:
    tools = [
        "sdl_overview",
        "sdl_section_reference",
        "sdl_scaffold",
        "sdl_diagnostics",
        "sdl_validate",
        "sdl_design_assessment",
        "sdl_plan",
        "sdl_claims_assessment",
    ]
    if profile_id in {"controlled-experiment-scenario", "reproducible-benchmark-study-input"}:
        tools.extend(["experiment_scaffold", "experiment_get_example", "experiment_validate"])
    return tools


def _profile_summary(
    profile: CompletenessProfileModel,
    outcome: ProfileCompletenessResult,
) -> dict[str, Any]:
    disposition_counts = Counter(disposition.value for disposition in profile.dispositions.values())
    return {
        "profile_id": profile.profile_id,
        "title": profile.title,
        "intended_claim": profile.intended_claim,
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "raes_delivery": {
            "complete": outcome.complete,
            "blocking_concern_count": len(outcome.blocking_concerns),
            "blocking_concern_ids": list(outcome.blocking_concerns),
        },
        "explicit_non_claims": list(profile.explicit_non_claims),
        "example_refs": list(profile.example_refs),
    }


def intended_use_profiles(profile_id: str = "") -> dict[str, Any]:
    """Return the canonical profile catalog or one selected profile."""

    from aces_contracts.scientific_completeness import (
        evaluate_profile_completeness,
        load_scientific_completeness_assessment,
        load_scientific_completeness_taxonomy,
    )

    taxonomy = load_scientific_completeness_taxonomy()
    assessment = load_scientific_completeness_assessment()
    outcomes = {item.profile_id: item for item in evaluate_profile_completeness(taxonomy, assessment)}
    profiles = {item.profile_id: item for item in taxonomy.profiles}
    selected_id = profile_id.strip()

    base: dict[str, Any] = {
        "status": "ok",
        "scope": "raes-delivery-capability",
        "profile_family": taxonomy.profile_family,
        "taxonomy_revision": taxonomy.revision,
        "assessment_revision": assessment.assessment_revision,
        "assessed_on": assessment.assessed_on,
        "scenario_assessment": {
            "performed": False,
            "status": "not-assessed",
            "reason": (
                "This tool reports whether RAES delivers the concerns required by an intended-use profile. "
                "It does not inspect or certify an individual scenario, experiment, backend, or run."
            ),
        },
    }
    if not selected_id:
        base["profiles"] = [_profile_summary(profile, outcomes[profile.profile_id]) for profile in taxonomy.profiles]
        base["next_action"] = "Select one profile_id before authoring or making readiness claims."
        return base

    if selected_id not in profiles:
        return {
            **base,
            "status": "invalid",
            "diagnostics": [
                {
                    "code": "raes.intended_use_profile.unknown",
                    "message": f"Unknown intended-use profile {selected_id!r}.",
                    "available_profile_ids": list(profiles),
                }
            ],
        }

    profile = profiles[selected_id]
    outcome = outcomes[selected_id]
    concerns = {item.concern_id: item for item in taxonomy.concerns}
    delivery = {item.concern_id: item for item in assessment.concerns}
    required_ids = sorted(
        concern_id for concern_id, disposition in profile.dispositions.items() if disposition.value == "required"
    )
    selected = _profile_summary(profile, outcome)
    selected["required_concerns"] = [
        {
            **concerns[concern_id].model_dump(mode="json"),
            **delivery[concern_id].model_dump(mode="json", exclude={"concern_id"}),
        }
        for concern_id in required_ids
    ]
    selected["next_tools"] = _authoring_tools(selected_id)
    base["profile"] = selected
    return base


def register(mcp: FastMCP) -> None:
    """Register intended-use profile discovery on the MCP server."""

    @mcp.tool(
        name="raes_intended_use_profiles",
        description=(
            "List RAES scientific-scenario intended-use profiles or inspect one profile's "
            "required concerns, current RAES delivery blockers, evidence, limitations, "
            "nonclaims, and recommended authoring tools. Call without profile_id to discover "
            "the catalog, then select a profile before authoring or making readiness claims. "
            "This assesses RAES delivery capability, not an individual scenario or run."
        ),
    )
    def raes_intended_use_profiles(profile_id: str = "") -> str:
        return json_response(intended_use_profiles(profile_id))


__all__ = ["intended_use_profiles", "register"]
