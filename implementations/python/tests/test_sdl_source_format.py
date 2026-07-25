"""Conformance tests for the canonical ``sdl-yaml/v1`` source profile."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from paths import REPO_ROOT
from raes import (
    SDL_SOURCE_FORMAT,
    SDLMigrationPolicy,
    SDLParseError,
    SDLParserLimits,
    load_sdl_fragment,
    parse_sdl,
    parse_sdl_file,
)


def _diagnostic_codes(error: SDLParseError) -> set[str]:
    return {item.code for item in error.diagnostics}


def test_yaml_12_core_scalar_resolution_is_portable() -> None:
    payload = load_sdl_fragment(
        textwrap.dedent(
            """
            yes_value: yes
            no_value: NO
            on_value: on
            off_value: Off
            true_value: true
            false_value: FALSE
            decimal: 012
            octal: 0o12
            hexadecimal: 0x0a
            date_like: 2026-07-11
            null_value: null
            underscore_integer: 1_000
            signed_hexadecimal: -0x0a
            """
        )
    )

    assert payload == {
        "yes_value": "yes",
        "no_value": "NO",
        "on_value": "on",
        "off_value": "Off",
        "true_value": True,
        "false_value": False,
        "decimal": 12,
        "octal": 10,
        "hexadecimal": 10,
        "date_like": "2026-07-11",
        "null_value": None,
        "underscore_integer": "1_000",
        "signed_hexadecimal": "-0x0a",
    }


@pytest.mark.parametrize(
    ("content", "code"),
    [
        ("value: !!str yes\n", "sdl.explicit_tag"),
        ("%YAML 1.2\n---\nvalue: yes\n", "sdl.directive"),
        ("value: .inf\n", "sdl.non_json_value"),
        ("value: .nan\n", "sdl.non_json_value"),
        ("true: value\n", "sdl.mapping_key_type"),
    ],
)
def test_non_profile_yaml_constructs_fail_before_model_construction(content: str, code: str) -> None:
    with pytest.raises(SDLParseError) as exc_info:
        load_sdl_fragment(content)

    assert code in _diagnostic_codes(exc_info.value)


def test_canonical_structural_fields_are_exact_snake_case() -> None:
    with pytest.raises(SDLParseError) as exc_info:
        parse_sdl("Name: canonical-name\n")

    diagnostic = exc_info.value.diagnostics[0]
    assert diagnostic.code == "sdl.noncanonical_field"
    assert diagnostic.pointer == "/name"
    assert diagnostic.authored_keys == ("Name", "name")
    assert diagnostic.severity == "error"


def test_migration_policy_accepts_aliases_with_source_ranged_advisories(tmp_path: Path) -> None:
    path = tmp_path / "legacy.sdl.yaml"
    path.write_text(
        textwrap.dedent(
            """
            Name: migrated
            workflows:
              response-flow:
                start: finish
                steps:
                  finish:
                    type: objective
                    objective: objective-ref
                    on-success: done
                  done:
                    type: end
            """
        ),
        encoding="utf-8",
    )

    scenario = parse_sdl_file(
        path,
        migration_policy=SDLMigrationPolicy.ACCEPT,
        skip_semantic_validation=True,
    )

    assert scenario.name == "migrated"
    assert [item.code for item in scenario.source_diagnostics] == [
        "sdl.noncanonical_field",
        "sdl.noncanonical_field",
    ]
    assert [item.pointer for item in scenario.source_diagnostics] == [
        "/name",
        "/workflows/response-flow/steps/finish/on_success",
    ]
    assert all(item.severity == "warning" for item in scenario.source_diagnostics)
    assert all(item.source == str(path) for item in scenario.source_diagnostics)


def test_literal_identifiers_are_not_migration_aliases() -> None:
    with pytest.raises(SDLParseError) as exc_info:
        parse_sdl(
            textwrap.dedent(
                """
                name: literal-ids
                nodes:
                  Web-App: {type: switch}
                  web_app: {type: switch}
                """
            ),
            migration_policy=SDLMigrationPolicy.ACCEPT,
        )

    assert _diagnostic_codes(exc_info.value) == {"sdl.identifier.invalid"}


def test_merge_keys_are_migration_only_and_conflicts_remain_fatal() -> None:
    content = textwrap.dedent(
        """
        name: merge-migration
        nodes:
          template: &template
            type: switch
          inherited:
            <<: *template
        """
    )

    with pytest.raises(SDLParseError) as strict_exc:
        parse_sdl(content)
    assert "sdl.noncanonical_merge" in _diagnostic_codes(strict_exc.value)

    scenario = parse_sdl(content, migration_policy=SDLMigrationPolicy.ACCEPT)
    assert scenario.nodes["inherited"].type.value == "switch"
    assert [item.code for item in scenario.source_diagnostics] == ["sdl.noncanonical_merge"]

    conflicting = content.replace("<<: *template", "<<: *template\n    type: vm")
    with pytest.raises(SDLParseError) as conflict_exc:
        parse_sdl(conflicting, migration_policy=SDLMigrationPolicy.ACCEPT)
    assert "sdl.mapping_key_conflict" in _diagnostic_codes(conflict_exc.value)


@pytest.mark.parametrize(
    ("limits", "content"),
    [
        (SDLParserLimits(max_input_bytes=8), "value: too-long\n"),
        (SDLParserLimits(max_scalar_bytes=3), "value: four\n"),
        (SDLParserLimits(max_depth=2), "value:\n  nested:\n    leaf: true\n"),
        (SDLParserLimits(max_nodes=2), "first: 1\nsecond: 2\n"),
        (SDLParserLimits(max_aliases=1), "base: &base [1]\nvalues: [*base, *base]\n"),
        (
            SDLParserLimits(max_expanded_nodes=8),
            "base: &base [1, 2, 3]\nvalues: [*base, *base, *base]\n",
        ),
    ],
)
def test_parser_limits_fail_with_one_stable_operational_diagnostic(
    limits: SDLParserLimits,
    content: str,
) -> None:
    with pytest.raises(SDLParseError) as exc_info:
        load_sdl_fragment(content, limits=limits)

    assert _diagnostic_codes(exc_info.value) == {"sdl.source_limit"}


def test_parse_sdl_file_bounds_raw_bytes_before_decoding(tmp_path: Path) -> None:
    path = tmp_path / "oversized.sdl.yaml"
    path.write_bytes(b"name: oversized\n" + b"x" * 64)
    limits = SDLParserLimits(max_input_bytes=16)

    with pytest.raises(SDLParseError, match="byte limit"):
        parse_sdl_file(path, limits=limits)


def test_alias_reuse_is_checked_at_its_effective_expanded_depth() -> None:
    content = """\
base: &base
  child:
    leaf: true
nested:
  inner: *base
"""

    with pytest.raises(SDLParseError) as exc_info:
        load_sdl_fragment(
            content,
            mapping_keys="literal",
            limits=SDLParserLimits(max_depth=4),
        )

    assert _diagnostic_codes(exc_info.value) == {"sdl.source_limit"}


def test_unknown_source_format_fails_closed() -> None:
    assert SDL_SOURCE_FORMAT == "sdl-yaml/v1"
    with pytest.raises(SDLParseError) as exc_info:
        parse_sdl("name: example\n", source_format="sdl-yaml/v2")

    assert _diagnostic_codes(exc_info.value) == {"sdl.source_format"}


def test_unknown_migration_policy_fails_with_a_structured_diagnostic() -> None:
    with pytest.raises(SDLParseError) as exc_info:
        parse_sdl("name: example\n", migration_policy="guess")

    assert _diagnostic_codes(exc_info.value) == {"sdl.migration_policy"}


def test_source_must_be_one_mapping_document() -> None:
    with pytest.raises(SDLParseError, match="single document"):
        parse_sdl("---\nname: first\n---\nname: second\n")

    with pytest.raises(SDLParseError, match="YAML mapping"):
        parse_sdl("- name\n- second\n")


def test_unpaired_unicode_surrogate_fails_as_invalid_utf8() -> None:
    with pytest.raises(SDLParseError) as exc_info:
        parse_sdl("name: \ud800\n")

    assert _diagnostic_codes(exc_info.value) == {"sdl.utf8"}


def test_invalid_utf8_file_has_a_structured_source_diagnostic(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_bytes(b"name: \xff\n")

    with pytest.raises(SDLParseError) as exc_info:
        parse_sdl_file(path)

    diagnostic = exc_info.value.diagnostics[0]
    assert diagnostic.code == "sdl.utf8"
    assert diagnostic.source == str(path)
    assert diagnostic.primary_range.start.line == 1


def test_migration_policy_and_source_identity_propagate_through_imports(tmp_path: Path) -> None:
    module = tmp_path / "module.yaml"
    module.write_text(
        """\
Name: imported
module:
  id: acme/imported
  version: 1.0.0
  exports: {}
""",
        encoding="utf-8",
    )
    root = tmp_path / "root.yaml"
    root.write_text(
        """\
name: root
imports:
  - path: module.yaml
    namespace: imported
""",
        encoding="utf-8",
    )

    with pytest.raises(SDLParseError):
        parse_sdl_file(root)

    scenario = parse_sdl_file(root, migration_policy=SDLMigrationPolicy.ACCEPT)
    assert [item.code for item in scenario.source_diagnostics] == ["sdl.noncanonical_field"]
    assert scenario.source_diagnostics[0].source == str(module)


def test_indentation_is_not_silently_rewritten() -> None:
    with pytest.raises(SDLParseError):
        parse_sdl("  name: indented-root\nother: value\n")


def test_normative_source_profile_fixture_corpus() -> None:
    fixture_root = REPO_ROOT / "contracts" / "fixtures" / "sdl" / "sdl-yaml-v1"
    valid = sorted((fixture_root / "valid").glob("*.yaml"))
    invalid = sorted((fixture_root / "invalid").glob("*.yaml"))
    migration = sorted((fixture_root / "migration").glob("*.yaml"))
    assert valid and invalid and migration

    for path in valid:
        parse_sdl_file(path, skip_semantic_validation=True)
    for path in invalid:
        with pytest.raises(SDLParseError):
            parse_sdl_file(path, skip_semantic_validation=True)
    for path in migration:
        with pytest.raises(SDLParseError):
            parse_sdl_file(path, skip_semantic_validation=True)
        scenario = parse_sdl_file(
            path,
            migration_policy=SDLMigrationPolicy.ACCEPT,
            skip_semantic_validation=True,
        )
        assert scenario.source_diagnostics
