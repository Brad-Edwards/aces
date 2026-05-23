"""Language-service support for SDL authoring surfaces."""

from __future__ import annotations

from aces_sdl.language_service import (
    apply_structured_edit,
    language_completions,
    language_diagnostics,
    language_format,
    language_references,
)

SAMPLE_SDL = """\
name: language-service-test
nodes:
  net: {type: Switch}
  net2: {type: Switch}
  web: {type: VM, os: linux, resources: {ram: 2 GiB, cpu: 1}, features: {app: admin}, roles: {admin: www}}
infrastructure:
  net: {count: 1, properties: {cidr: 10.0.0.0/24, gateway: 10.0.0.1}}
  net2: {count: 1, properties: {cidr: 10.0.1.0/24, gateway: 10.0.1.1}}
  web: {count: 1, links: [net]}
features:
  app: {type: Service, source: webapp}
"""

INVALID_REFERENCE_SDL = """\
name: broken
nodes:
  web:
    type: VM
    os: linux
    features: {ghost-feature: admin}
"""


def test_language_completions_include_top_level_sections_and_reference_targets() -> None:
    top_level = language_completions("name: x\n", cursor_path="/")
    top_level_labels = {item["label"] for item in top_level["items"]}
    assert "nodes" in top_level_labels
    assert "workflows" in top_level_labels

    feature_refs = language_completions(
        SAMPLE_SDL,
        cursor_path="/nodes/web/features",
    )
    labels = {item["label"] for item in feature_refs["items"]}
    assert "app" in labels
    assert any(item["detail"] == "features.app" for item in feature_refs["items"])


def test_language_references_report_definitions_and_occurrences() -> None:
    payload = language_references(SAMPLE_SDL, "app")

    assert payload["status"] == "ok"
    assert any(item["qualified_name"] == "features.app" for item in payload["definitions"])
    assert any(item["path"] == "/nodes/web/features/app" for item in payload["occurrences"])


def test_qualified_language_references_do_not_match_other_sections() -> None:
    sdl = """\
name: qualified-reference-test
nodes:
  web: {type: VM, os: linux, resources: {ram: 2 GiB, cpu: 1}, features: {app: admin}, roles: {admin: www}}
features:
  app: {type: Service, source: webapp}
conditions:
  app: {command: "true", interval: 10}
"""

    payload = language_references(sdl, "features.app")

    assert [item["qualified_name"] for item in payload["definitions"]] == ["features.app"]
    assert any(item["path"] == "/nodes/web/features/app" for item in payload["occurrences"])
    assert not any(item["path"] == "/conditions/app" for item in payload["occurrences"])


def test_language_format_normalizes_field_keys() -> None:
    payload = language_format(
        """\
Name: formatting-test
Nodes:
  sw:
    Type: Switch
"""
    )

    assert payload["status"] == "formatted"
    assert payload["content"].startswith("name: formatting-test\nnodes:\n")
    assert "type: Switch" in payload["content"]


def test_language_diagnostics_are_structured() -> None:
    payload = language_diagnostics(INVALID_REFERENCE_SDL)

    assert payload["status"] == "invalid"
    assert payload["diagnostics"][0]["stage"] == "semantic_validation"
    assert payload["diagnostics"][0]["code"] == "sdl.semantic"
    assert "ghost-feature" in payload["diagnostics"][0]["message"]


def test_structured_edit_updates_yaml_and_revalidates() -> None:
    payload = apply_structured_edit(
        SAMPLE_SDL,
        operation="set",
        pointer="/description",
        value="Edited through the language service",
    )

    assert payload["status"] == "edited"
    assert "description: Edited through the language service" in payload["content"]
    assert payload["diagnostics"] == []


def test_structured_edit_deletes_value_and_revalidates() -> None:
    payload = apply_structured_edit(
        SAMPLE_SDL,
        operation="delete",
        pointer="/nodes/web/features/app",
    )

    assert payload["status"] == "edited"
    assert "app: admin" not in payload["content"]
    assert payload["diagnostics"] == []


def test_structured_edit_appends_value_and_revalidates() -> None:
    payload = apply_structured_edit(
        SAMPLE_SDL,
        operation="append",
        pointer="/infrastructure/web/links",
        value="net2",
    )

    assert payload["status"] == "edited"
    assert "- net2" in payload["content"]
    assert payload["diagnostics"] == []
