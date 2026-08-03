"""Property-based coverage for the experiment-core contract boundary (FM2).

Delivers the ``property_based_or_differential_tests`` artifact kind for the
``experiment-core`` formal-spec subsystem (``specs/formal/experiment-core``,
FM2) recorded in ``specs/formal/assurance-fulfillment.yaml`` (issue #521). The
existing ``test_runtime_contracts.py`` coverage of the EXP-701..705 contracts is
example-based; this file adds property-based coverage of one of the
cross-artifact semantic-graph constraints standard JSON Schema cannot portably
enforce (README "Separation" invariant 6): every ``metric_definitions`` object
key MUST equal its embedded ``metric_id``.

The property is exercised as a metamorphic mutation of a *published valid
fixture*: across the space of alternative identifiers, breaking the key/id
correspondence is always rejected, while a *consistent* rename of both the key
and the embedded id is always accepted. The unmutated fixture is the positive
anchor.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError
from raes_contracts.contracts import ExperimentTaskModel

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VALID_TASK = json.loads(
    (_REPO_ROOT / "contracts/fixtures/experiment-core/experiment-task-v1/valid/reference.json").read_text()
)
_METRIC_KEY = next(iter(_VALID_TASK["evaluation_protocol"]["metric_definitions"]))

# Alternative identifiers that are guaranteed distinct from the fixture's metric
# key (the ``metric-`` prefix cannot collide with ``foothold-achieved``) and are
# valid NonEmptyString values, so the only invariant a mismatch can trip is the
# key/metric_id correspondence itself.
_ALT_SUFFIXES = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20)


def test_reference_task_fixture_validates() -> None:
    ExperimentTaskModel.model_validate(copy.deepcopy(_VALID_TASK))


class TestMetricDefinitionKeyInvariant:
    @given(_ALT_SUFFIXES)
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_embedded_metric_id_must_match_its_key(self, suffix: str) -> None:
        alternate_id = f"metric-{suffix}"
        payload = copy.deepcopy(_VALID_TASK)
        payload["evaluation_protocol"]["metric_definitions"][_METRIC_KEY]["metric_id"] = alternate_id
        with pytest.raises(ValidationError) as exc_info:
            ExperimentTaskModel.model_validate(payload)
        assert "metric_definitions keys must match embedded metric_id" in str(exc_info.value)

    @given(_ALT_SUFFIXES)
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_consistent_key_and_id_rename_preserves_validity(self, suffix: str) -> None:
        alternate_id = f"metric-{suffix}"
        payload = copy.deepcopy(_VALID_TASK)
        definitions = payload["evaluation_protocol"]["metric_definitions"]
        definition = definitions.pop(_METRIC_KEY)
        definition["metric_id"] = alternate_id
        definitions[alternate_id] = definition
        ExperimentTaskModel.model_validate(payload)
