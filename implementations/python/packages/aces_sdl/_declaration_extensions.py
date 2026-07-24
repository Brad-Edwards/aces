"""Nested declaration helpers kept outside the source-size-limited index."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol


class _ScenarioDeclarations(Protocol):
    historical_baselines: Mapping[str, object]
    activity_templates: Mapping[str, object]
    activity_profiles: Mapping[str, object]


def add_historical_declarations(
    index: object,
    scenario: _ScenarioDeclarations,
    *,
    add: Callable[..., None],
    qualified_parts: Callable[[str], tuple[str, ...]],
) -> None:
    for baseline_name, baseline in scenario.historical_baselines.items():
        baseline_parts = qualified_parts(baseline_name)
        for collection_name, kind, targetable in (
            ("actors", "historical-actor", False),
            ("objects", "historical-object", True),
            ("events", "historical-event", False),
            ("materialization_bindings", "historical-materialization-binding", False),
            ("readback_requirements", "historical-readback-requirement", False),
        ):
            for declaration_id in getattr(baseline, collection_name):
                add(
                    index,
                    kind=kind,
                    address_parts=(
                        "historical_baselines",
                        *baseline_parts,
                        collection_name,
                        declaration_id,
                    ),
                    model_path=f"historical_baselines.{baseline_name}.{collection_name}.{declaration_id}",
                    referenceable=True,
                    targetable=targetable,
                )


def add_live_activity_declarations(
    index: object,
    scenario: _ScenarioDeclarations,
    *,
    add: Callable[..., None],
    qualified_parts: Callable[[str], tuple[str, ...]],
) -> None:
    for template_name, template in scenario.activity_templates.items():
        template_parts = qualified_parts(template_name)
        for parameter_id in template.parameters:
            add(
                index,
                kind="activity-template-parameter",
                address_parts=("activity_templates", *template_parts, "parameters", parameter_id),
                model_path=f"activity_templates.{template_name}.parameters.{parameter_id}",
                referenceable=True,
            )
    for profile_name, profile in scenario.activity_profiles.items():
        profile_parts = qualified_parts(profile_name)
        for collection_name, kind in (
            ("actors", "background-activity-actor"),
            ("execution_contexts", "activity-execution-context"),
            ("schedules", "activity-schedule"),
            ("actions", "activity-action"),
        ):
            for declaration_id in getattr(profile, collection_name):
                add(
                    index,
                    kind=kind,
                    address_parts=("activity_profiles", *profile_parts, collection_name, declaration_id),
                    model_path=f"activity_profiles.{profile_name}.{collection_name}.{declaration_id}",
                    referenceable=True,
                )


__all__ = ["add_historical_declarations", "add_live_activity_declarations"]
