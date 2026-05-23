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


def test_language_completions_cover_contexts_and_filters() -> None:
    sdl = """\
name: completion-contexts
nodes:
  web: {type: VM, os: linux, resources: {ram: 2 GiB, cpu: 1}}
conditions:
  alive: {command: "true", interval: 5}
metrics:
  uptime: {type: CONDITIONAL, condition: alive}
relationships:
  app-to-web: {type: hosted_on, source: web, target: uptime}
workflows:
  flow:
    start: start-here
    steps:
      start-here: {type: end}
"""

    section_fields = language_completions(sdl, cursor_path="/nodes/web", prefix="res")
    assert section_fields["context"] == "section:nodes"
    assert [item["label"] for item in section_fields["items"]] == ["resources"]

    success_refs = language_completions(sdl, cursor_path="/objectives/goal/success/conditions")
    assert success_refs["context"] == "reference:conditions"
    assert [item["label"] for item in success_refs["items"]] == ["alive"]

    any_refs = language_completions(sdl, cursor_path="/relationships/app-to-web/source")
    assert any(item["detail"] == "nodes.web" for item in any_refs["items"])
    assert any(item["detail"] == "metrics.uptime" for item in any_refs["items"])

    workflow_refs = language_completions(sdl, cursor_path="/workflows/flow/start")
    assert workflow_refs["context"] == "reference:workflow_steps"
    assert workflow_refs["items"][0]["detail"] == "workflows.flow.steps.start-here"


def test_language_completions_report_parse_and_size_errors() -> None:
    parse_error = language_completions("name: [\n", cursor_path="/")
    assert parse_error["status"] == "invalid"
    assert parse_error["diagnostics"][0]["code"] == "sdl.parse"

    size_error = language_completions("x" * (64 * 1024 + 1), cursor_path="/")
    assert size_error["status"] == "invalid"
    assert size_error["diagnostics"][0]["code"] == "sdl.input_too_large"


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


def test_language_references_cover_empty_invalid_sequence_and_nested_entities() -> None:
    empty = language_references("", "web")
    assert empty["definitions"] == []
    assert empty["occurrences"] == []

    invalid = language_references("name: [\n", "web")
    assert invalid["status"] == "invalid"
    assert invalid["diagnostics"][0]["code"] == "sdl.parse"
    assert invalid["diagnostics"][0]["range"]["start"]["line"] == 2

    sequence = language_references("- web\n", "web")
    assert sequence["definitions"] == []
    assert sequence["occurrences"][0]["path"] == "/0"

    nested = language_references(
        """\
name: nested-entity-test
entities:
  team:
    name: Team
    entities:
      alice: {name: Alice}
""",
        "entities.team.alice",
    )
    assert [item["qualified_name"] for item in nested["definitions"]] == ["entities.team.alice"]


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


def test_language_format_reports_parse_error() -> None:
    payload = language_format("name: [\n")

    assert payload["status"] == "invalid"
    assert payload["diagnostics"][0]["code"] == "sdl.parse"


def test_language_diagnostics_are_structured() -> None:
    payload = language_diagnostics(INVALID_REFERENCE_SDL)

    assert payload["status"] == "invalid"
    assert payload["diagnostics"][0]["stage"] == "semantic_validation"
    assert payload["diagnostics"][0]["code"] == "sdl.semantic"
    assert "ghost-feature" in payload["diagnostics"][0]["message"]


def test_language_diagnostics_support_parse_only_mode_and_parse_errors() -> None:
    parse_only = language_diagnostics(INVALID_REFERENCE_SDL, semantic_validation=False)
    assert parse_only == {"status": "valid", "stage": "parse", "diagnostics": []}

    parse_error = language_diagnostics("name: [\n")
    assert parse_error["status"] == "invalid"
    assert parse_error["diagnostics"][0]["code"] == "sdl.parse"


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


def test_structured_edit_handles_root_and_list_mutations() -> None:
    root = apply_structured_edit(SAMPLE_SDL, operation="set", pointer="", value={"name": "replacement"})
    assert root["status"] == "edited"
    assert root["content"] == "name: replacement\n"

    list_set = apply_structured_edit(SAMPLE_SDL, operation="set", pointer="/infrastructure/web/links/0", value="net2")
    assert list_set["status"] == "edited"
    assert "- net2" in list_set["content"]

    list_delete = apply_structured_edit(SAMPLE_SDL, operation="delete", pointer="/infrastructure/web/links/0")
    assert list_delete["status"] == "edited"
    assert "links: []" in list_delete["content"]

    created = apply_structured_edit(SAMPLE_SDL, operation="set", pointer="/nodes/web/custom/value", value=True)
    assert created["status"] == "edited_with_diagnostics"
    assert "custom:" in created["content"]


def test_structured_edit_reports_invalid_edit_requests() -> None:
    cases = [
        ("delete", "", None, "root pointer supports only the set operation"),
        ("replace", "/description", "x", "operation must be one of"),
        ("set", "description", "x", "pointer must be empty or start with '/'"),
        ("append", "/name", "x", "is not a list"),
        ("delete", "/missing", None, "missing path segment"),
        ("delete", "/infrastructure/web/links/nope", None, "is not an integer"),
        ("delete", "/infrastructure/web/links/10", None, "out of range"),
        ("set", "/infrastructure/web/links/0/name", "x", "does not address a mapping or list"),
    ]

    for operation, pointer, value, expected in cases:
        payload = apply_structured_edit(SAMPLE_SDL, operation=operation, pointer=pointer, value=value)
        assert payload["status"] == "invalid"
        assert expected in payload["diagnostics"][0]["message"]
