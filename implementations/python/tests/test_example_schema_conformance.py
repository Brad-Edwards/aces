"""Issue #501 (review CT-4) — worked examples conform to the *published* JSON Schema.

``test_scenarios.py`` proves every ``examples/scenarios/*.sdl.yaml`` loads through the
Pydantic parser, but Pydantic acceptance is not published-schema conformance, and the
worked examples are the proof artifacts third parties read. This suite serializes each
example with the canonical, contract-shaped publication serialization
(``model_dump(mode="json", by_alias=True)`` — the same flags ``aces_processor/compiler.py``
uses) and validates the result against the *checked-in* published schema
``contracts/schemas/sdl/sdl-authoring-input-v1.json`` with ``Draft202012Validator``.

Validating the shipped schema artifact rather than ``schema_bundle()`` is deliberate: per
ADR-009 the published ``contracts/schemas/`` JSON is the normative authority, while
``schema_bundle()`` remains the drift/compatibility proof used by other gates.

A non-vacuity guard and a deliberate negative control keep the suite from passing
vacuously — a stale corpus path that collects zero cases, or a validator that accepts
everything, both fail loudly.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import pytest
from aces_contracts.corpus import corpus_family_root
from aces_sdl.scenario import Scenario
from aces_sdl.scenarios import load_scenario
from jsonschema import Draft202012Validator
from paths import EXAMPLES_DIR

# ``by_alias=True`` is load-bearing: the published schema is generated from the model with
# ``model_json_schema()`` (aliases on), so a field-name dump fails on YAML-facing aliases
# such as ``class``, ``on-success``, and ``max-attempts``. ``mode="json"`` yields JSON-native
# scalars (enum values, not enum members). These are the same flags the runtime compiler
# uses for its contract-shaped serialization.
_PUBLICATION_DUMP_KWARGS = {"mode": "json", "by_alias": True}


@dataclass(frozen=True)
class CorpusEntry:
    """One validation-corpus leg: a glob of example files checked against one published schema.

    The extension seam (issue #501 preflight): a future instantiated-example corpus adds a
    row to ``VALIDATION_CORPUS`` — root, glob, loader, contract id, schema file, and
    serialization kwargs — rather than a new loader, path convention, or validator wrapper.
    """

    contract_id: str
    root: Path
    glob: str
    loader: Callable[[Path], Scenario]
    schema_path: Path
    dump_kwargs: dict = field(default_factory=lambda: dict(_PUBLICATION_DUMP_KWARGS))

    def examples(self) -> list[Path]:
        return sorted(self.root.glob(self.glob))

    def validator(self) -> Draft202012Validator:
        return _validator_for(self.schema_path)


@cache
def _validator_for(schema_path: Path) -> Draft202012Validator:
    """Load the *checked-in* published schema artifact and build its validator once."""
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


_SDL_SCHEMA_DIR = corpus_family_root("schemas") / "sdl"

# Today the table has exactly one leg: the authoring example corpus against the published
# authoring-input contract. No instantiated-scenario *example* artifacts exist under
# ``examples/`` — the instantiated schema's fixtures under ``contracts/fixtures/sdl/`` are
# covered by ``test_instantiated_scenario_schema.py`` — so a future instantiated corpus adds
# a row here for ``instantiated-scenario-v1``.
VALIDATION_CORPUS = [
    CorpusEntry(
        contract_id="sdl-authoring-input-v1",
        root=EXAMPLES_DIR,
        glob="*.sdl.yaml",
        loader=load_scenario,
        schema_path=_SDL_SCHEMA_DIR / "sdl-authoring-input-v1.json",
    ),
]


def _example_cases() -> list[tuple[CorpusEntry, Path]]:
    return [(entry, path) for entry in VALIDATION_CORPUS for path in entry.examples()]


def _case_id(value: object) -> str:
    if isinstance(value, Path):
        return value.name
    if isinstance(value, CorpusEntry):
        return value.contract_id
    return str(value)


@pytest.mark.parametrize(("entry", "path"), _example_cases(), ids=_case_id)
def test_example_conforms_to_published_schema(entry: CorpusEntry, path: Path) -> None:
    """Every shipped example provably conforms to the published contract surface in CI.

    The serialization mirrors the runtime compiler's publication serialization, so the JSON
    validated here is the shape a downstream consumer reads — not an internal Pydantic-only
    projection.
    """
    scenario = entry.loader(path)
    payload = scenario.model_dump(**entry.dump_kwargs)

    errors = sorted(entry.validator().iter_errors(payload), key=lambda error: error.json_path)

    assert not errors, f"{path.name} violates {entry.contract_id}:\n" + "\n".join(
        f"  {error.json_path}: {error.message}" for error in errors
    )


@pytest.mark.parametrize("entry", VALIDATION_CORPUS, ids=_case_id)
def test_corpus_leg_is_nonempty(entry: CorpusEntry) -> None:
    """Non-vacuity guard: a stale/relocated corpus root must fail loudly, not collect zero cases."""
    assert entry.examples(), f"No examples for {entry.contract_id} under {entry.root} (glob {entry.glob!r})"


# --- Negative control: the validator must be engaged (the suite cannot pass vacuously) ---

_AUTHORING_ENTRY = VALIDATION_CORPUS[0]

_MINIMAL_VALID_PAYLOAD = {"name": "negative-control-baseline"}

# Each payload violates exactly one published-schema rule: ``required: ["name"]``,
# ``name`` typed ``string``, and top-level ``additionalProperties: false``. Kept inline,
# never as a file under ``examples/scenarios/``, so an invalid control never leaks into the
# reusable positive example corpus.
_INVALID_PAYLOADS = {
    "missing-required-name": {"description": "no name field"},
    "wrong-type-name": {"name": 123},
    "additional-top-level-property": {"name": "neg-control", "not_a_real_section": True},
}


def test_negative_control_baseline_is_accepted() -> None:
    """A minimal valid document validates, so the rejections below indicate the injected defect,
    not a validator that rejects everything."""
    _AUTHORING_ENTRY.validator().validate(_MINIMAL_VALID_PAYLOAD)


@pytest.mark.parametrize("payload", _INVALID_PAYLOADS.values(), ids=list(_INVALID_PAYLOADS))
def test_negative_control_invalid_payload_is_rejected(payload: dict) -> None:
    """A known-invalid payload must fail published-schema validation, proving the validator is engaged."""
    assert not _AUTHORING_ENTRY.validator().is_valid(payload)
