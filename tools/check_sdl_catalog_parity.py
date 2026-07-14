#!/usr/bin/env python3
# ruff: noqa: E402, I001
"""Prove that the normative SDL catalogs cover the live language surface.

The published schema and normative prose remain independently governed
authorities. This read-only check compares both with the reference
implementation registries so drift is reported instead of silently generated
away.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGES = REPO_ROOT / "implementations" / "python" / "packages"
for import_root in (REPO_ROOT, PYTHON_PACKAGES):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from aces_sdl._language_metadata import REFERENCE_COMPLETION_TARGETS
from aces_sdl._mapping_scopes import HASHMAP_SECTIONS
from aces_sdl._module_symbols import HASHMAP_SECTIONS as MODULE_HASHMAP_SECTIONS
from aces_sdl._runtime_service_families import (
    RUNTIME_SERVICE_FAMILIES,
    RuntimeReferenceChild,
)
from aces_sdl.scenario import Scenario
from tools.policy.common import (
    PolicyFailure,
    apply_exceptions,
    failures_to_json,
    load_exceptions,
)

SECTIONS_PATH = "specs/sdl/sections.md"
REFERENCES_PATH = "specs/sdl/references.md"
RUNTIME_PATH = "specs/sdl/runtime-inventory.md"
SCHEMA_PATH = "contracts/schemas/sdl/sdl-authoring-input-v1.json"

_TOP_LEVEL_HEADING = "## Complete top-level field catalog"
_REFERENCE_HEADING = "## 6. Machine-checkable reference-edge index"
_RUNTIME_HEADING = "## 2. Family index"
_SUMMARY_RE = re.compile(
    r"<!-- sdl-catalog-summary "
    r"top-level=(?P<top>\d+) metadata-composition=(?P<meta>\d+) "
    r"sections=(?P<sections>\d+) maps=(?P<maps>\d+) lists=(?P<lists>\d+) -->"
)
_SEPARATOR_RE = re.compile(r"^:?-{2,}:?$")
_BACKTICK_RE = re.compile(r"`([^`]+)`")
_VALID_KINDS = frozenset({"metadata", "composition", "section"})
_VALID_SHAPES = frozenset({"scalar", "mapping", "map", "list"})
_VALID_LIFECYCLE = frozenset({"normalized", "expanded", "instantiated", "expanded-empty", "instantiated-empty"})
_MAX_CATALOG_BYTES = 512 * 1024
_MAX_CATALOG_ROWS = 512
_METADATA_FIELDS = frozenset({"name", "version", "description"})
_COMPOSITION_FIELDS = frozenset({"module", "imports", "realization"})

_NODE_VALIDATOR = "[node validator](../../implementations/python/packages/aces_sdl/validator/_nodes_infra_network.py)"
_INFRASTRUCTURE_VALIDATOR = (
    "[infrastructure validator](../../implementations/python/packages/aces_sdl/validator/_nodes_infra_network.py)"
)
_SECTION_VALIDATOR = "[section validator](../../implementations/python/packages/aces_sdl/validator/_sections.py)"
_CONTENT_VALIDATOR = (
    "[content validator](../../implementations/python/packages/aces_sdl/validator/_content_objectives.py)"
)
_ACCOUNT_VALIDATOR = (
    "[account validator](../../implementations/python/packages/aces_sdl/validator/_content_objectives.py)"
)
_RELATIONSHIP_VALIDATOR = (
    "[relationship validator](../../implementations/python/packages/aces_sdl/validator/_relationships.py)"
)
_DOMAIN_TOPOLOGY_SEMANTICS = (
    "[domain topology semantics](../../implementations/python/packages/aces_sdl/semantics/domain_topology.py)"
)
_PARTICIPANT_VALIDATOR = (
    "[participant validator](../../implementations/python/packages/aces_sdl/validator/_content_objectives.py)"
)
_PARTICIPANT_SEMANTICS = (
    "[participant semantics](../../implementations/python/packages/aces_sdl/semantics/participant_behavior.py)"
)
_OUTCOME_SEMANTICS = (
    "[outcome semantics](../../implementations/python/packages/aces_sdl/semantics/participant_outcome.py)"
)
_BEHAVIOR_SEMANTICS = (
    "[behavior semantics](../../implementations/python/packages/aces_sdl/semantics/participant_behavior.py)"
)
_BEHAVIOR_VALIDATOR = (
    "[behavior validator](../../implementations/python/packages/aces_sdl/validator/_content_objectives.py)"
)
_BEHAVIOR_MODEL = "[behavior model](behavior-specifications.md)"
_EVIDENCE_VALIDATOR = (
    "[evidence validator](../../implementations/python/packages/aces_sdl/validator/_evidence_requirements.py)"
)
_OBJECTIVE_SEMANTICS = "[objective semantics](objective-semantics.md)"
_WORKFLOW_SEMANTICS = "[workflow semantics](workflow-semantics.md)"
_PROPOSITION_VALIDATOR = (
    "[proposition validator](../../implementations/python/packages/aces_sdl/validator/_propositions.py)"
)
_SEMANTIC = "semantic validation"
_STRUCTURAL = "structural validation"
_DANGLING = "fatal dangling or ambiguous"

# This independently owned expectation makes every normative reference row a
# checked contract. The catalog is not generated from this registry; changing
# either authority requires an explicit, reviewable reconciliation.
_REFERENCE_EDGE_EXPECTATIONS: dict[str, tuple[str, str, str, str]] = {
    "nodes.*.features[]": ("features", _SEMANTIC, _DANGLING, _NODE_VALIDATOR),
    "nodes.*.conditions[]": ("conditions", _SEMANTIC, _DANGLING, _NODE_VALIDATOR),
    "conditions.*.proposition": (
        "propositions",
        _SEMANTIC,
        "fatal dangling or ambiguous when present",
        _PROPOSITION_VALIDATOR,
    ),
    "propositions.*.subjects[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _PROPOSITION_VALIDATOR,
    ),
    "propositions.*.evidence_requirements[]": (
        "evidence_requirements",
        _SEMANTIC,
        _DANGLING,
        _PROPOSITION_VALIDATOR,
    ),
    "assertions.*.proposition": (
        "propositions",
        _SEMANTIC,
        _DANGLING,
        _PROPOSITION_VALIDATOR,
    ),
    "nodes.*.injects[]": ("injects", _SEMANTIC, _DANGLING, _NODE_VALIDATOR),
    "nodes.*.vulnerabilities[]": (
        "vulnerabilities",
        _SEMANTIC,
        _DANGLING,
        _NODE_VALIDATOR,
    ),
    "infrastructure.*.links[]": (
        "infrastructure",
        _SEMANTIC,
        _DANGLING,
        _INFRASTRUCTURE_VALIDATOR,
    ),
    "infrastructure.*.dependencies[]": (
        "infrastructure",
        _SEMANTIC,
        _DANGLING,
        _INFRASTRUCTURE_VALIDATOR,
    ),
    "features.*.dependencies[]": (
        "features",
        _SEMANTIC,
        "fatal dangling, ambiguous, or cyclic",
        _SECTION_VALIDATOR,
    ),
    "entities.*.vulnerabilities[]": (
        "vulnerabilities",
        _SEMANTIC,
        _DANGLING,
        _SECTION_VALIDATOR,
    ),
    "injects.*.from_entity": ("entities", _SEMANTIC, _DANGLING, _SECTION_VALIDATOR),
    "injects.*.to_entities[]": ("entities", _SEMANTIC, _DANGLING, _SECTION_VALIDATOR),
    "events.*.assertions[]": (
        "assertions",
        _SEMANTIC,
        "fatal dangling, ambiguous, or non-precondition role",
        _PROPOSITION_VALIDATOR,
    ),
    "events.*.injects[]": ("injects", _SEMANTIC, _DANGLING, _SECTION_VALIDATOR),
    "scripts.*.events[]": ("events", _SEMANTIC, _DANGLING, _SECTION_VALIDATOR),
    "stories.*.scripts[]": ("scripts", _SEMANTIC, _DANGLING, _SECTION_VALIDATOR),
    "content.*.target": (
        "nodes",
        _SEMANTIC,
        "fatal unless target is a vm node",
        _CONTENT_VALIDATOR,
    ),
    "accounts.*.domain_ref": (
        "identity_domains",
        _SEMANTIC,
        "fatal dangling, ambiguous, or inconsistent topology",
        _DOMAIN_TOPOLOGY_SEMANTICS,
    ),
    "identity_domains.*.authority_account_ref": (
        "accounts",
        _SEMANTIC,
        "fatal dangling, ambiguous, or authority outside domain controllers",
        _DOMAIN_TOPOLOGY_SEMANTICS,
    ),
    "accounts.*.node": (
        "nodes",
        _SEMANTIC,
        "fatal unless target is a vm node",
        _ACCOUNT_VALIDATOR,
    ),
    "relationships.*.source": (
        "targetable",
        _SEMANTIC,
        "fatal dangling or ambiguous; subtype may narrow domain",
        _RELATIONSHIP_VALIDATOR,
    ),
    "relationships.*.target": (
        "targetable",
        _SEMANTIC,
        "fatal dangling or ambiguous; subtype may narrow domain",
        _RELATIONSHIP_VALIDATOR,
    ),
    "relationships.*.domain_join.controller_refs[]": (
        "nodes",
        _SEMANTIC,
        "fatal dangling, ambiguous, or controller outside target domain",
        _DOMAIN_TOPOLOGY_SEMANTICS,
    ),
    "agents.*.entity": ("entities", _SEMANTIC, _DANGLING, _PARTICIPANT_VALIDATOR),
    "agents.*.starting_accounts[]": (
        "accounts",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_VALIDATOR,
    ),
    "agents.*.starting_assertions[]": (
        "assertions",
        _SEMANTIC,
        "fatal dangling, ambiguous, or non-precondition role",
        _PROPOSITION_VALIDATOR,
    ),
    "action_contracts.*.interactions.*.related_action_ref": (
        "action_contracts",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_SEMANTICS,
    ),
    "observation_boundaries.*.view_rules.*.information_refs[]": (
        "derived:boundary_information",
        _SEMANTIC,
        "fatal outside declared boundary information",
        _PARTICIPANT_SEMANTICS,
    ),
    "outcome_interpretation_rules.*.source_ref": (
        "action_contracts,objectives,workflows",
        _SEMANTIC,
        _DANGLING,
        _OUTCOME_SEMANTICS,
    ),
    "behavior_specifications.*.participant_refs[]": (
        "agents",
        _SEMANTIC,
        _DANGLING,
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.participant_role_refs[]": (
        "derived:agent_roles",
        _SEMANTIC,
        "fatal unless bound by a referenced participant",
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.action_contract_refs[]": (
        "action_contracts",
        _SEMANTIC,
        _DANGLING,
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.observation_boundary_refs[]": (
        "observation_boundaries",
        _SEMANTIC,
        _DANGLING,
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.outcome_interpretation_rule_refs[]": (
        "outcome_interpretation_rules",
        _SEMANTIC,
        _DANGLING,
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.authority_scope_refs[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _BEHAVIOR_VALIDATOR,
    ),
    "behavior_specifications.*.behavior_mode": (
        "vocabulary:behavior_mode",
        _STRUCTURAL,
        "fatal invalid vocabulary value",
        _BEHAVIOR_MODEL,
    ),
    "behavior_specifications.*.ai_offensive_behavior_refs[]": (
        "vocabulary:ai_offensive_behavior",
        _SEMANTIC,
        "fatal unknown vocabulary identifier",
        _BEHAVIOR_MODEL,
    ),
    "behavior_specifications.*.offensive_behavior_refs[]": (
        "vocabulary:offensive_behavior",
        _SEMANTIC,
        "fatal unknown vocabulary identifier",
        _BEHAVIOR_MODEL,
    ),
    "behavior_specifications.*.realization_profile_ref": (
        "opaque:realization_profile",
        _STRUCTURAL,
        "fatal invalid reference shape; resolution belongs to realization",
        _BEHAVIOR_MODEL,
    ),
    "behavior_specifications.*.backend_feature_support_refs[]": (
        "registry:behavior_features",
        _SEMANTIC,
        "fatal unsupported feature identifier",
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.evidence_contract_refs[]": (
        "contract:participant_evidence",
        _SEMANTIC,
        "fatal unknown contract identifier",
        _BEHAVIOR_SEMANTICS,
    ),
    "evidence_requirements.*.source_refs[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _EVIDENCE_VALIDATOR,
    ),
    "evidence_requirements.*.scope_refs[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _EVIDENCE_VALIDATOR,
    ),
    "evidence_requirements.*.channel_refs[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _EVIDENCE_VALIDATOR,
    ),
    "evidence_requirements.*.trigger_ref": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _EVIDENCE_VALIDATOR,
    ),
    "evidence_requirements.*.boundary_ref": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _EVIDENCE_VALIDATOR,
    ),
    "objectives.*.agent": ("agents", _SEMANTIC, _DANGLING, _OBJECTIVE_SEMANTICS),
    "objectives.*.entity": ("entities", _SEMANTIC, _DANGLING, _OBJECTIVE_SEMANTICS),
    "objectives.*.targets[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _OBJECTIVE_SEMANTICS,
    ),
    "objectives.*.success.assertions[]": (
        "assertions",
        _SEMANTIC,
        "fatal dangling, ambiguous, or precondition role",
        _OBJECTIVE_SEMANTICS,
    ),
    "objectives.*.depends_on[]": (
        "objectives",
        _SEMANTIC,
        "fatal dangling, ambiguous, or cyclic",
        _OBJECTIVE_SEMANTICS,
    ),
    "workflows.*.start": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling step",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.when.assertions[]": (
        "assertions",
        _SEMANTIC,
        "fatal dangling, ambiguous, or non-precondition role",
        _WORKFLOW_SEMANTICS,
    ),
}


class CatalogParseError(ValueError):
    """A normative catalog table is absent or malformed."""


@dataclass(frozen=True)
class TopLevelRow:
    field: str
    kind: str
    shape: str
    lifecycle: tuple[str, ...]
    presence: str
    identity: str
    references: str
    owner: str
    line_no: int


@dataclass(frozen=True)
class ReferenceRow:
    source_path: str
    domain: str
    phase: str
    failure: str
    owner: str
    line_no: int

    @property
    def key(self) -> tuple[str, str]:
        parts = self.source_path.replace("[]", "").split(".")
        return parts[0], parts[-1]


@dataclass(frozen=True)
class RuntimeRow:
    key: str
    collection: str
    primary_id: str
    child_paths: tuple[str, ...]
    owner: str
    line_no: int


def _cells(line: str) -> list[str]:
    parts = [part.strip() for part in line.strip().split("|")]
    if parts and not parts[0]:
        parts.pop(0)
    if parts and not parts[-1]:
        parts.pop()
    return parts


def _unquote(cell: str) -> str:
    match = _BACKTICK_RE.fullmatch(cell.strip())
    return match.group(1) if match else cell.strip()


def _table(text: str, heading: str, columns: int) -> list[tuple[int, list[str]]]:
    size = len(text.encode("utf-8"))
    if size > _MAX_CATALOG_BYTES:
        raise CatalogParseError(f"catalog exceeds {_MAX_CATALOG_BYTES}-byte size limit")
    lines = text.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == heading) + 1
    except StopIteration as exc:
        raise CatalogParseError(f"missing catalog heading: {heading}") from exc
    table: list[tuple[int, list[str]]] = []
    started = False
    for index, line in enumerate(lines[start:], start=start):
        if line.startswith("## "):
            break
        if line.lstrip().startswith("|"):
            started = True
            table.append((index + 1, _cells(line)))
            if len(table) > _MAX_CATALOG_ROWS + 2:
                raise CatalogParseError(f"catalog exceeds {_MAX_CATALOG_ROWS}-row limit")
        elif started:
            break
    if len(table) < 3:
        raise CatalogParseError(f"catalog under {heading!r} requires a header, separator, and data rows")
    if len(table[0][1]) != columns:
        raise CatalogParseError(f"catalog under {heading!r} has {len(table[0][1])} columns; expected {columns}")
    separator = table[1][1]
    if len(separator) != columns or not all(_SEPARATOR_RE.fullmatch(cell) for cell in separator):
        raise CatalogParseError(f"catalog under {heading!r} has a malformed separator row")
    for line_no, cells in table[2:]:
        if len(cells) != columns:
            raise CatalogParseError(f"catalog row at line {line_no} has {len(cells)} columns; expected {columns}")
    return table[2:]


def _unique(rows: list[Any], key_name: str, label: str) -> None:
    seen: dict[str, int] = {}
    for row in rows:
        key = getattr(row, key_name)
        if key in seen:
            raise CatalogParseError(f"duplicate {label} {key!r} at lines {seen[key]} and {row.line_no}")
        seen[key] = row.line_no


def parse_top_level_catalog(text: str) -> list[TopLevelRow]:
    rows = [
        TopLevelRow(
            field=_unquote(cells[0]),
            kind=cells[1].lower(),
            shape=cells[2].lower(),
            lifecycle=tuple(token.strip().lower() for token in cells[3].split(",") if token.strip()),
            presence=cells[4].strip().lower(),
            identity=_unquote(cells[5]),
            references=cells[6].strip().lower(),
            owner=cells[7].strip(),
            line_no=line_no,
        )
        for line_no, cells in _table(text, _TOP_LEVEL_HEADING, 8)
    ]
    _unique(rows, "field", "top-level field")
    return rows


def parse_reference_catalog(text: str) -> list[ReferenceRow]:
    rows = [
        ReferenceRow(
            source_path=_unquote(cells[0]),
            domain=_unquote(cells[1]),
            phase=cells[2].strip().lower(),
            failure=cells[3].strip().lower(),
            owner=cells[4].strip(),
            line_no=line_no,
        )
        for line_no, cells in _table(text, _REFERENCE_HEADING, 5)
    ]
    seen: dict[tuple[str, str], int] = {}
    for row in rows:
        if row.key in seen:
            raise CatalogParseError(f"duplicate reference edge {row.key!r} at lines {seen[row.key]} and {row.line_no}")
        seen[row.key] = row.line_no
    return rows


def parse_runtime_catalog(text: str) -> list[RuntimeRow]:
    rows = [
        RuntimeRow(
            key=_unquote(cells[0]),
            collection=_unquote(cells[1]),
            primary_id=_unquote(cells[2]),
            child_paths=tuple(token.strip() for token in _unquote(cells[3]).split(",") if token.strip() != "none"),
            owner=cells[4].strip(),
            line_no=line_no,
        )
        for line_no, cells in _table(text, _RUNTIME_HEADING, 5)
    ]
    _unique(rows, "key", "runtime family")
    return rows


def _failure(rule_id: str, message: str, path: str) -> PolicyFailure:
    return PolicyFailure(rule_id, message, path)


def _expected_kind(field: str) -> str:
    if field in _METADATA_FIELDS:
        return "metadata"
    if field in _COMPOSITION_FIELDS:
        return "composition"
    return "section"


def _schema_shape(schema: dict[str, Any]) -> str:
    schema_type = schema.get("type")
    if schema_type == "string":
        return "scalar"
    if schema_type == "array":
        return "list"
    if schema_type == "object":
        return "map"
    if schema_type is None and schema.get("default") is None:
        return "mapping"
    return "unknown"


def _expected_presence(field: str) -> str:
    model_field = Scenario.model_fields[field]
    if model_field.is_required():
        return "required"
    value = model_field.default_factory() if model_field.default_factory is not None else model_field.default
    if value == "*":
        return "optional; default `*`"
    if value == "":
        return "optional; default empty string"
    if value is None:
        return "optional; default null"
    if value == []:
        return "optional; default empty list"
    if value == {}:
        return "optional; default empty map"
    return f"optional; default `{value}`"


def _expected_identity(field: str, shape: str) -> str:
    if field == "name":
        return "scenario_name"
    if field == "module":
        return "module.id"
    if field == "imports":
        return "namespace"
    if field == "forwarding_agents":
        return "forwarding_agent_id"
    if shape == "map":
        return "map_key"
    return "none"


def _flatten_children(children: tuple[RuntimeReferenceChild, ...], prefix: str = "") -> tuple[str, ...]:
    paths: list[str] = []
    for child in children:
        path = (
            f"{prefix}/{child.collection_name}:{child.id_field}"
            if prefix
            else f"{child.collection_name}:{child.id_field}"
        )
        paths.append(path)
        paths.extend(_flatten_children(child.children, path))
    return tuple(paths)


def _check_top_level(text: str, schema: dict[str, Any]) -> tuple[list[PolicyFailure], list[TopLevelRow]]:
    failures: list[PolicyFailure] = []
    try:
        rows = parse_top_level_catalog(text)
    except CatalogParseError as exc:
        return [_failure("sdl-catalog-parse", str(exc), SECTIONS_PATH)], []
    by_field = {row.field: row for row in rows}
    model_fields = set(Scenario.model_fields)
    schema_fields = set(schema.get("properties", {}))
    catalog_fields = set(by_field)
    if model_fields != schema_fields or catalog_fields != model_fields:
        failures.append(
            _failure(
                "sdl-catalog-field-set",
                f"field sets differ: catalog-only={sorted(catalog_fields - model_fields)}, "
                f"model-only={sorted(model_fields - catalog_fields)}, "
                f"schema-only={sorted(schema_fields - model_fields)}, model-only-vs-schema={sorted(model_fields - schema_fields)}",
                SECTIONS_PATH,
            )
        )
    for field in sorted(catalog_fields & model_fields & schema_fields):
        row = by_field[field]
        expected_shape = _schema_shape(schema["properties"][field])
        if field in HASHMAP_SECTIONS:
            expected_shape = "map"
        if row.shape != expected_shape:
            failures.append(
                _failure(
                    "sdl-catalog-field-shape",
                    f"{field!r} is {expected_shape}, catalog says {row.shape}",
                    SECTIONS_PATH,
                )
            )
        expected_presence = _expected_presence(field)
        if row.presence != expected_presence:
            failures.append(
                _failure(
                    "sdl-catalog-field-default",
                    f"{field!r} is {expected_presence}, catalog says {row.presence}",
                    SECTIONS_PATH,
                )
            )
        expected_identity = _expected_identity(field, expected_shape)
        if row.identity != expected_identity:
            failures.append(
                _failure(
                    "sdl-catalog-field-identity",
                    f"{field!r} identity is {expected_identity!r}, catalog says {row.identity!r}",
                    SECTIONS_PATH,
                )
            )
        if row.kind != _expected_kind(field) or row.kind not in _VALID_KINDS:
            failures.append(
                _failure(
                    "sdl-catalog-field-kind",
                    f"{field!r} has invalid kind {row.kind!r}",
                    SECTIONS_PATH,
                )
            )
        if not row.lifecycle or not set(row.lifecycle) <= _VALID_LIFECYCLE:
            failures.append(
                _failure(
                    "sdl-catalog-lifecycle",
                    f"{field!r} has invalid lifecycle tokens {row.lifecycle!r}",
                    SECTIONS_PATH,
                )
            )
        if row.shape not in _VALID_SHAPES or not row.identity or not row.owner:
            failures.append(
                _failure(
                    "sdl-catalog-row-incomplete",
                    f"{field!r} has an incomplete classification",
                    SECTIONS_PATH,
                )
            )
    map_fields = {row.field for row in rows if row.shape == "map"}
    if map_fields != set(HASHMAP_SECTIONS):
        failures.append(
            _failure(
                "sdl-catalog-map-set",
                f"map fields differ from mapping registry: {sorted(map_fields ^ set(HASHMAP_SECTIONS))}",
                SECTIONS_PATH,
            )
        )
    if not set(MODULE_HASHMAP_SECTIONS) <= map_fields:
        failures.append(
            _failure(
                "sdl-catalog-module-map-set",
                "module export maps are not a subset of catalogued maps",
                SECTIONS_PATH,
            )
        )
    summary = _SUMMARY_RE.search(text)
    actual = {
        "top": len(rows),
        "meta": sum(row.kind != "section" for row in rows),
        "sections": sum(row.kind == "section" for row in rows),
        "maps": sum(row.shape == "map" for row in rows),
        "lists": sum(row.shape == "list" and row.kind == "section" for row in rows),
    }
    if summary is None or any(int(summary.group(key)) != value for key, value in actual.items()):
        failures.append(
            _failure(
                "sdl-catalog-summary",
                f"checked summary is absent or stale; expected {actual}",
                SECTIONS_PATH,
            )
        )
    required = set(schema.get("required", []))
    model_required = {name for name, field in Scenario.model_fields.items() if field.is_required()}
    if required != model_required:
        failures.append(
            _failure(
                "sdl-catalog-schema-required",
                f"published schema required set differs from model: {sorted(required ^ model_required)}",
                SCHEMA_PATH,
            )
        )
    return failures, rows


def _check_references(text: str, top_rows: list[TopLevelRow]) -> list[PolicyFailure]:
    try:
        rows = parse_reference_catalog(text)
    except CatalogParseError as exc:
        return [_failure("sdl-catalog-reference-parse", str(exc), REFERENCES_PATH)]
    failures: list[PolicyFailure] = []
    by_source = {row.source_path: (row.domain, row.phase, row.failure, row.owner) for row in rows}
    if by_source != _REFERENCE_EDGE_EXPECTATIONS:
        differing = sorted(
            source
            for source in by_source.keys() | _REFERENCE_EDGE_EXPECTATIONS.keys()
            if by_source.get(source) != _REFERENCE_EDGE_EXPECTATIONS.get(source)
        )
        failures.append(
            _failure(
                "sdl-catalog-reference-row",
                f"reference-edge contract differs for: {differing}",
                REFERENCES_PATH,
            )
        )
    by_key = {row.key: row for row in rows}
    for key, domain in sorted(REFERENCE_COMPLETION_TARGETS.items()):
        row = by_key.get(key)
        if row is None or row.domain != domain:
            actual = None if row is None else row.domain
            failures.append(
                _failure(
                    "sdl-catalog-reference-domain",
                    f"{key!r} expects domain {domain!r}, catalog says {actual!r}",
                    REFERENCES_PATH,
                )
            )
    behavior_expectations = {
        source: expected
        for source, expected in _REFERENCE_EDGE_EXPECTATIONS.items()
        if source.startswith("behavior_specifications.*.")
    }
    for source, expected in behavior_expectations.items():
        if by_source.get(source) != expected:
            failures.append(
                _failure(
                    "sdl-catalog-behavior-edge",
                    f"{source} must match its behavior reference contract",
                    REFERENCES_PATH,
                )
            )
    source_sections = {row.key[0] for row in rows}
    top_by_field = {row.field: row for row in top_rows}
    for section in source_sections:
        top = top_by_field.get(section)
        if top is None or top.references != "catalogued":
            failures.append(
                _failure(
                    "sdl-catalog-reference-coverage",
                    f"reference source section {section!r} is not marked catalogued",
                    SECTIONS_PATH,
                )
            )
    for row in top_rows:
        if row.references == "catalogued" and row.field not in source_sections:
            failures.append(
                _failure(
                    "sdl-catalog-reference-coverage",
                    f"{row.field!r} is marked catalogued but has no edge row",
                    REFERENCES_PATH,
                )
            )
    return failures


def _check_runtime(text: str) -> list[PolicyFailure]:
    try:
        rows = parse_runtime_catalog(text)
    except CatalogParseError as exc:
        return [_failure("sdl-catalog-runtime-parse", str(exc), RUNTIME_PATH)]
    actual = {row.key: (row.collection, row.primary_id, row.child_paths) for row in rows}
    expected = {
        family.key: (
            family.collection_name,
            family.id_field,
            _flatten_children(family.child_refs),
        )
        for family in RUNTIME_SERVICE_FAMILIES
    }
    if actual != expected:
        differing = sorted(key for key in actual.keys() | expected.keys() if actual.get(key) != expected.get(key))
        return [
            _failure(
                "sdl-catalog-runtime-family",
                f"runtime-family catalog differs for: {differing}",
                RUNTIME_PATH,
            )
        ]
    return []


def evaluate_sdl_catalog_parity(repo_root: Path) -> list[PolicyFailure]:
    """Return deterministic parity failures for the normative SDL catalogs."""
    required_paths = (SECTIONS_PATH, REFERENCES_PATH, RUNTIME_PATH, SCHEMA_PATH)
    missing = [relative for relative in required_paths if not (repo_root / relative).is_file()]
    if missing:
        return [
            _failure(
                "sdl-catalog-missing",
                f"required catalog authority is missing: {relative}",
                relative,
            )
            for relative in missing
        ]
    try:
        schema = json.loads((repo_root / SCHEMA_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_failure("sdl-catalog-schema-parse", str(exc), SCHEMA_PATH)]
    sections_text = (repo_root / SECTIONS_PATH).read_text(encoding="utf-8")
    top_failures, top_rows = _check_top_level(sections_text, schema)
    failures = list(top_failures)
    failures.extend(_check_references((repo_root / REFERENCES_PATH).read_text(encoding="utf-8"), top_rows))
    failures.extend(_check_runtime((repo_root / RUNTIME_PATH).read_text(encoding="utf-8")))
    return failures


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate normative SDL catalog parity.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true", help="Emit JSON failures.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    failures = evaluate_sdl_catalog_parity(args.repo_root)
    exceptions_path = args.repo_root / "tools" / "policy" / "exceptions.yaml"
    if exceptions_path.is_file():
        failures = apply_exceptions(failures, load_exceptions(args.repo_root))
    if failures:
        if args.json:
            print(failures_to_json(failures))
        else:
            for failure in failures:
                print(failure.render(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
