"""Fail-closed tests for authored SDL mapping keys."""

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from raes import SDLMigrationPolicy, SDLParseDiagnostic, SDLParseError, parse_sdl, parse_sdl_file
from raes.language_service import (
    apply_structured_edit,
    language_completions,
    language_diagnostics,
    language_format,
    language_references,
)

FIXTURE_DIR = Path(__file__).parent / "data" / "sdl" / "invalid"


def _conflicts(source: str, *, migration: bool = True):
    with pytest.raises(SDLParseError) as excinfo:
        parse_sdl(
            source,
            skip_semantic_validation=True,
            migration_policy=SDLMigrationPolicy.ACCEPT if migration else SDLMigrationPolicy.REJECT,
        )
    diagnostics = excinfo.value.diagnostics
    assert diagnostics
    assert all(item.code == "sdl.mapping_key_conflict" for item in diagnostics)
    return diagnostics


def test_exact_duplicate_root_key_is_rejected_before_model_construction() -> None:
    diagnostics = _conflicts("name: first\nname: second\n")

    assert len(diagnostics) == 1
    assert diagnostics[0].pointer == "/name"
    assert diagnostics[0].authored_keys == ("name", "name")


def test_normalized_nested_field_aliases_conflict() -> None:
    diagnostics = _conflicts(
        """\
name: aliases
nodes:
  sw:
    Type: switch
    type: switch
"""
    )

    assert diagnostics[0].pointer == "/nodes/sw/type"
    assert diagnostics[0].authored_keys == ("Type", "type")


def test_exact_duplicate_literal_identifier_is_rejected() -> None:
    diagnostics = _conflicts(
        """\
name: literal-duplicate
nodes:
  sw: {type: switch}
  sw: {type: switch}
"""
    )

    assert diagnostics[0].pointer == "/nodes/sw"


def test_literal_identifiers_are_not_field_normalized() -> None:
    scenario = parse_sdl(
        """\
name: literal-identifiers
nodes:
  web-app: {type: switch}
  web_app: {type: switch}
"""
    )

    assert tuple(scenario.nodes) == ("web-app", "web_app")


def test_yaml_12_string_like_identifiers_remain_distinct_strings() -> None:
    scenario = parse_sdl(
        """\
name: boolean-like-identifiers
nodes:
  on: {type: switch}
  "true": {type: switch}
  off: {type: switch}
  "false": {type: switch}
"""
    )

    assert tuple(scenario.nodes) == ("on", "true", "off", "false")


def test_core_resolved_non_string_mapping_key_is_rejected_with_a_source_range() -> None:
    with pytest.raises(SDLParseError) as excinfo:
        parse_sdl("name: invalid-key\nnodes:\n  1: {type: switch}\n")

    diagnostic = excinfo.value.diagnostics[0]
    assert diagnostic.code == "sdl.mapping_key_type"
    assert diagnostic.pointer == "/nodes/1"
    assert diagnostic.primary_range.start.line == 3
    assert diagnostic.primary_range.start.column == 3


def test_merge_source_and_local_field_must_be_disjoint() -> None:
    diagnostics = _conflicts(
        """\
name: merge-conflict
nodes:
  first:
    type: vm
    resources: &resources
      ram: 1 gib
      cpu: 1
  second:
    type: vm
    resources:
      <<: *resources
      cpu: 2
""",
        migration=True,
    )

    assert diagnostics[0].pointer == "/nodes/second/resources/cpu"
    assert diagnostics[0].authored_keys == ("cpu", "cpu")


def test_merge_sources_must_be_pairwise_disjoint_and_collect_all_conflicts() -> None:
    diagnostics = _conflicts(
        """\
name: merge-sources
nodes:
  first:
    type: vm
    resources: &first
      ram: 1 gib
      cpu: 1
  second:
    type: vm
    resources: &second
      RAM: 2 gib
      CPU: 2
  third:
    type: vm
    resources:
      <<: [*first, *second]
""",
        migration=True,
    )

    assert [item.pointer for item in diagnostics] == [
        "/nodes/third/resources/ram",
        "/nodes/third/resources/cpu",
    ]
    assert diagnostics[0].authored_keys == ("ram", "RAM")


def test_disjoint_merge_is_valid_only_in_migration_mode() -> None:
    content = """\
name: merge-disjoint
nodes:
  first:
    type: vm
    resources: &resources
      ram: 1 gib
      cpu: 1
  second:
    type: vm
    resources:
      <<: *resources
"""
    with pytest.raises(SDLParseError) as excinfo:
        parse_sdl(content)
    assert excinfo.value.diagnostics[0].code == "sdl.noncanonical_merge"

    scenario = parse_sdl(
        content,
        migration_policy=SDLMigrationPolicy.ACCEPT,
    )

    assert scenario.nodes["second"].resources.cpu == 1
    assert [item.code for item in scenario.source_diagnostics] == ["sdl.noncanonical_merge"]


def test_cyclic_alias_graph_fails_cleanly() -> None:
    with pytest.raises(SDLParseError) as excinfo:
        parse_sdl(
            """\
name: cyclic-alias
nodes: &nodes
  sw:
    type: switch
    roles: *nodes
"""
        )

    assert excinfo.value.diagnostics[0].code == "sdl.alias_cycle"


def test_non_printable_input_fails_cleanly_across_loader_entry_points() -> None:
    with pytest.raises(SDLParseError, match="special characters are not allowed"):
        parse_sdl("\x1b")

    payload = language_references("\x1b", "symbol")
    assert payload["status"] == "invalid"
    assert payload["diagnostics"][0]["code"] == "sdl.parse"


def test_collects_conflicts_in_document_order() -> None:
    diagnostics = _conflicts(
        """\
Name: first
name: second
Version: 1.0.0
version: 2.0.0
"""
    )

    assert [item.pointer for item in diagnostics] == ["/name", "/version"]


def test_conflict_diagnostic_has_one_based_token_ranges() -> None:
    diagnostic = _conflicts("Name: first\nname: second\n")[0]

    assert diagnostic.primary_range.as_dict() == {
        "start": {"line": 2, "column": 1},
        "end": {"line": 2, "column": 5},
    }
    assert diagnostic.related_range.as_dict() == {
        "start": {"line": 1, "column": 1},
        "end": {"line": 1, "column": 5},
    }
    assert isinstance(diagnostic, SDLParseDiagnostic)


def test_conflict_diagnostic_never_exposes_mapping_values() -> None:
    with pytest.raises(SDLParseError) as excinfo:
        parse_sdl("name: public\nname: TOP-SECRET-VALUE\n")

    assert "TOP-SECRET-VALUE" not in str(excinfo.value)


def test_conflict_pointer_uses_rfc_6901_escaping() -> None:
    diagnostics = _conflicts(
        """\
name: escaped-pointer
nodes:
  "a/b~c": {type: switch}
  "a/b~c": {type: switch}
"""
    )

    assert diagnostics[0].pointer == "/nodes/a~1b~0c"


def test_file_entry_point_preserves_file_and_key_diagnostics(tmp_path: Path) -> None:
    source = tmp_path / "scenario.yaml"
    source.write_text("name: first\nname: second\n", encoding="utf-8")

    with pytest.raises(SDLParseError) as excinfo:
        parse_sdl_file(source)

    assert excinfo.value.path == source
    assert excinfo.value.diagnostics[0].pointer == "/name"


def test_language_diagnostics_preserve_structured_conflict_fields() -> None:
    payload = language_diagnostics("Name: first\nname: second\n")

    assert payload["status"] == "invalid"
    assert payload["diagnostics"] == [
        {
            "stage": "parse",
            "severity": "error",
            "code": "sdl.mapping_key_conflict",
            "message": "Structural field keys 'Name' and 'name' both address 'name'.",
            "path": "/name",
            "authored_keys": ["Name", "name"],
            "range": {
                "start": {"line": 2, "column": 1},
                "end": {"line": 2, "column": 5},
            },
            "related": [
                {
                    "message": "First authored key 'Name'.",
                    "range": {
                        "start": {"line": 1, "column": 1},
                        "end": {"line": 1, "column": 5},
                    },
                }
            ],
        }
    ]


def test_language_references_rejects_ambiguous_documents() -> None:
    payload = language_references(
        "name: refs\nnodes:\n  sw: {type: switch}\n  sw: {type: switch}\n",
        "sw",
    )

    assert payload["status"] == "invalid"
    assert payload["diagnostics"][0]["code"] == "sdl.mapping_key_conflict"


@pytest.mark.parametrize(
    "operation",
    [
        lambda source: language_format(source),
        lambda source: language_completions(source),
        lambda source: apply_structured_edit(source, operation="set", pointer="/description", value="x"),
    ],
    ids=["format", "completions", "structured-edit"],
)
def test_authoring_reads_reject_ambiguity_before_rewriting(operation) -> None:
    payload = operation("Name: first\nname: second\n")

    assert payload["status"] == "invalid"
    assert payload["diagnostics"][0]["code"] == "sdl.mapping_key_conflict"


def test_imported_module_uses_the_same_mapping_key_boundary(tmp_path: Path) -> None:
    imported = tmp_path / "common.yaml"
    imported.write_text("name: common\nnodes:\n  sw: {type: switch}\n  sw: {type: switch}\n", encoding="utf-8")
    root = tmp_path / "root.yaml"
    root.write_text(
        "name: root\nimports:\n  - path: common.yaml\n    namespace: shared\n",
        encoding="utf-8",
    )

    with pytest.raises(SDLParseError) as excinfo:
        parse_sdl_file(root)

    assert excinfo.value.path == imported
    assert excinfo.value.diagnostics[0].pointer == "/nodes/sw"


@pytest.mark.parametrize("fixture", sorted(FIXTURE_DIR.glob("mapping-key-*.yaml")), ids=lambda path: path.stem)
def test_negative_mapping_key_fixtures_fail_closed(fixture: Path) -> None:
    with pytest.raises(SDLParseError):
        parse_sdl_file(fixture, skip_semantic_validation=True)


_STRUCTURAL_ALIAS_PAIRS = st.sampled_from(
    [
        ("Password-Strength", "password_strength"),
        ("PASSWORD_STRENGTH", "password-strength"),
        ("password-strength", "Password_Strength"),
    ]
)


@given(_STRUCTURAL_ALIAS_PAIRS)
def test_property_distinct_structural_aliases_never_overwrite(pair: tuple[str, str]) -> None:
    first, second = pair
    diagnostics = _conflicts(
        f"""\
name: generated-aliases
nodes:
  host: {{type: switch}}
accounts:
  alice:
    username: alice
    node: host
    {first}: strong
    {second}: weak
"""
    )

    assert diagnostics[0].pointer == "/accounts/alice/password_strength"


@given(st.sampled_from([("web-app", "web_app"), ("db-1", "db_1"), ("a-b", "a_b")]))
def test_property_literal_identifier_aliases_remain_distinct(pair: tuple[str, str]) -> None:
    first, second = pair
    scenario = parse_sdl(
        f"""\
name: generated-identifiers
nodes:
  {first}: {{type: switch}}
  {second}: {{type: switch}}
"""
    )

    assert set(scenario.nodes) == {first, second}
