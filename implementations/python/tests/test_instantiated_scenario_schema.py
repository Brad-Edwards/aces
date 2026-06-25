"""Issue #500 — instantiated-scenario contract differentiated from authoring-input.

`sdl-authoring-input-v1` and `instantiated-scenario-v1` were byte-identical
apart from `$id`/title/description: the authoring-vs-instantiated distinction
lived only in `InstantiatedScenario` private attributes that never reached the
JSON Schema. These tests pin the differentiation: the instantiated contract
rejects unresolved ``${var}`` tokens (embedded and full-string) at both the
Pydantic model boundary and the published JSON Schema boundary, while the
authoring contract still accepts them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aces_contracts.contracts import schema_bundle
from aces_sdl._base import VARIABLE_TOKEN_PATTERN
from aces_sdl.scenario import InstantiatedScenario, Scenario
from jsonschema import Draft202012Validator
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
SDL_SCHEMA_DIR = REPO_ROOT / "contracts" / "schemas" / "sdl"
FIXTURE_DIR = REPO_ROOT / "contracts" / "fixtures" / "sdl" / "instantiated-scenario-v1"

_CONCRETE = {"name": "concrete-scenario", "description": "a fully concrete scenario"}
_EMBEDDED_VAR = {"name": "concrete-scenario", "description": "deploy ${region} cluster"}
_FULL_VAR = {"name": "concrete-scenario", "description": "${environment}"}
_COUNT_VAR = {"name": "concrete-scenario", "infrastructure": {"net": {"count": "${replicas}"}}}
_BEHAVIOR_SPEC_EXTENSION_VAR = {
    "name": "concrete-scenario",
    "behavior_specifications": {
        "blue-response": {
            "semantic_version": "1.0.0",
            "participant_refs": ["blue-operator"],
            "action_contract_refs": ["triage"],
            "extensions": {"x-acme:note": {"nested": ["ready", "${secret}"]}},
        }
    },
}

_VAR_PAYLOADS = [_EMBEDDED_VAR, _FULL_VAR, _COUNT_VAR, _BEHAVIOR_SPEC_EXTENSION_VAR]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# The token pattern's backslashes are escaped once serialized into a schema's
# `not.pattern`; match the serialized form, not the raw Python string.
_PATTERN_IN_JSON = json.dumps(VARIABLE_TOKEN_PATTERN)[1:-1]


# --- Model boundary -------------------------------------------------------


@pytest.mark.parametrize("payload", _VAR_PAYLOADS)
def test_authoring_model_accepts_unresolved_variables(payload: dict) -> None:
    """No regression: the authoring model still accepts ``${var}`` placeholders."""
    scenario = Scenario.model_validate(payload)
    assert scenario.name == payload["name"]


def test_instantiated_model_accepts_concrete_scenario() -> None:
    instantiated = InstantiatedScenario.model_validate(_CONCRETE)
    assert instantiated.name == "concrete-scenario"


@pytest.mark.parametrize("payload", _VAR_PAYLOADS)
def test_instantiated_model_rejects_unresolved_variables(payload: dict) -> None:
    with pytest.raises(ValidationError):
        InstantiatedScenario.model_validate(payload)


# --- JSON Schema boundary (live bundle) -----------------------------------


def test_bundle_instantiated_schema_constraints_differ_from_authoring() -> None:
    """Acceptance (a): the schemas differ in *constraints*, not just metadata."""
    bundle = schema_bundle()
    authoring = json.dumps(bundle["sdl-authoring-input-v1"])
    instantiated = json.dumps(bundle["instantiated-scenario-v1"])
    assert _PATTERN_IN_JSON not in authoring
    assert instantiated.count(_PATTERN_IN_JSON) > 1


@pytest.mark.parametrize("payload", _VAR_PAYLOADS)
def test_bundle_instantiated_schema_rejects_unresolved_variables(payload: dict) -> None:
    """Acceptance (b): a ``${var}`` payload fails instantiated-schema validation."""
    bundle = schema_bundle()
    assert not Draft202012Validator(bundle["instantiated-scenario-v1"]).is_valid(payload)
    # The same payload is valid against the authoring contract.
    assert Draft202012Validator(bundle["sdl-authoring-input-v1"]).is_valid(payload)


def test_bundle_instantiated_schema_accepts_concrete_scenario() -> None:
    bundle = schema_bundle()
    Draft202012Validator(bundle["instantiated-scenario-v1"]).validate(_CONCRETE)


# --- Published artifacts + fixtures ---------------------------------------


def test_published_schemas_differ_in_constraints() -> None:
    """Acceptance (a) against the published, shipped schema files."""
    authoring = _load(SDL_SCHEMA_DIR / "sdl-authoring-input-v1.json")
    instantiated = _load(SDL_SCHEMA_DIR / "instantiated-scenario-v1.json")
    assert _PATTERN_IN_JSON not in json.dumps(authoring)
    assert json.dumps(instantiated).count(_PATTERN_IN_JSON) > 1


def test_published_valid_fixture_passes() -> None:
    schema = _load(SDL_SCHEMA_DIR / "instantiated-scenario-v1.json")
    fixture = _load(FIXTURE_DIR / "valid" / "minimal.json")
    Draft202012Validator(schema).validate(fixture)


def test_published_invalid_fixture_fails() -> None:
    """Acceptance (b), fixture-proven (check_json_artifacts only checks valid/)."""
    schema = _load(SDL_SCHEMA_DIR / "instantiated-scenario-v1.json")
    fixture = _load(FIXTURE_DIR / "invalid" / "unresolved-variable.json")
    assert not Draft202012Validator(schema).is_valid(fixture)
    # The invalid fixture is otherwise well-formed: it only fails because of the
    # unresolved ${var}, so it still validates against the authoring contract.
    authoring = _load(SDL_SCHEMA_DIR / "sdl-authoring-input-v1.json")
    Draft202012Validator(authoring).validate(fixture)
