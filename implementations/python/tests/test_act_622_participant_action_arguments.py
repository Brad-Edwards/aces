"""ACT-622 portable participant action-argument semantics."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from aces_processor.compiler import compile_runtime_model
from aces_processor.compiler.participant_contracts import _compile_action_contracts
from aces_processor.models import resolve_participant_action_arguments
from pydantic import ValidationError
from raes.instantiate import instantiate_scenario
from raes.participant_behavior import ParticipantActionContract
from raes.scenario import Scenario

ACTION_ADDRESS = "participant.action-contract.respond"


def _contract_payload() -> dict[str, object]:
    return {
        "semantic_version": "1.0.0",
        "behavioral_granularity": "atomic",
        "procedure_basis": "portable response operation",
        "realization_profile": "backend-declared",
        "fidelity_claim": "preserves governed response arguments",
        "arguments": {
            "target": {
                "value_type": "reference",
                "allowed_values": ["accounts.alice", "accounts.bob"],
                "normalization": "identity",
                "normalization_disclosure_ref": "arguments.target.normalization.identity",
                "omission": "reject",
                "omission_disclosure_ref": "arguments.target.omission.reject",
                "loss_disclosure_ref": "arguments.target.loss.none",
            },
            "attempts": {
                "value_type": "integer",
                "default": 2,
                "minimum": 1,
                "maximum": 3,
                "normalization": "identity",
                "normalization_disclosure_ref": "arguments.attempts.normalization.identity",
                "omission": "use_default",
                "omission_disclosure_ref": "arguments.attempts.omission.default",
                "default_disclosure_ref": "arguments.attempts.default.two",
                "loss_disclosure_ref": "arguments.attempts.loss.none",
            },
            "fields": {
                "value_type": "string",
                "cardinality": "many",
                "allowed_values": ["hostname", "owner", "status"],
                "min_items": 1,
                "max_items": 2,
                "normalization": "trim",
                "normalization_disclosure_ref": "arguments.fields.normalization.trim",
                "omission": "omit",
                "omission_disclosure_ref": "arguments.fields.omission.explicit",
                "loss_disclosure_ref": "arguments.fields.loss.none",
            },
        },
        "preconditions": [
            {
                "precondition_id": "authority",
                "precondition_class": "authority",
                "description": "participant has response authority",
                "support_refs": ["authorities.response"],
            }
        ],
        "effects": [
            {
                "effect_id": "response-recorded",
                "effect_class": "intended_effect",
                "description": "records the portable response",
                "target_refs": ["response.target"],
            }
        ],
        "failure_classes": ["precondition_unsatisfied", "unknown"],
    }


def _compiled_contract():
    contract = ParticipantActionContract.model_validate(_contract_payload())
    scenario = SimpleNamespace(action_contracts={"respond": contract})
    return _compile_action_contracts(scenario)[ACTION_ADDRESS]


def test_authored_argument_shape_is_closed_and_typed() -> None:
    contract = ParticipantActionContract.model_validate(_contract_payload())

    assert set(contract.arguments) == {"target", "attempts", "fields"}
    assert contract.arguments["target"].value_type.value == "reference"

    payload = _contract_payload()
    payload["arguments"]["target"]["backend_command"] = "run-native"  # type: ignore[index]
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ParticipantActionContract.model_validate(payload)


@pytest.mark.parametrize(
    ("argument_name", "updates", "message"),
    (
        ("attempts", {"default": 4}, "default must satisfy"),
        ("attempts", {"minimum": 4, "maximum": 3}, "minimum must not exceed maximum"),
        ("target", {"normalization": "trim"}, "reference arguments require identity normalization"),
        ("fields", {"min_items": 3, "max_items": 2}, "min_items must not exceed max_items"),
    ),
)
def test_authored_argument_shape_rejects_incoherent_domains(
    argument_name: str,
    updates: dict[str, object],
    message: str,
) -> None:
    payload = _contract_payload()
    payload["arguments"][argument_name].update(updates)  # type: ignore[index,union-attr]

    with pytest.raises(ValidationError, match=message):
        ParticipantActionContract.model_validate(payload)


def test_authored_domain_literals_are_normalized_before_validation_and_compilation() -> None:
    payload = _contract_payload()
    payload["arguments"]["fields"].update(  # type: ignore[index,union-attr]
        {
            "default": [" hostname "],
            "allowed_values": [" hostname ", " status "],
            "omission": "use_default",
            "default_disclosure_ref": "arguments.fields.default.hostname",
        }
    )

    contract = ParticipantActionContract.model_validate(payload)
    compiled = _compile_action_contracts(SimpleNamespace(action_contracts={"respond": contract}))[ACTION_ADDRESS]
    fields = next(definition for definition in compiled.argument_definitions if definition["name"] == "fields")

    assert contract.arguments["fields"].allowed_values == ["hostname", "status"]
    assert contract.arguments["fields"].default == ["hostname"]
    assert fields["allowed_values"] == ["hostname", "status"]
    assert fields["default"] == ["hostname"]


@pytest.mark.parametrize(
    ("updates", "message"),
    (
        ({"allowed_values": [" hostname ", "hostname"]}, "duplicates"),
        ({"allowed_values": [" x "], "min_length": 2}, "min_length"),
    ),
)
def test_authored_domain_constraints_are_evaluated_after_normalization(
    updates: dict[str, object],
    message: str,
) -> None:
    payload = _contract_payload()
    payload["arguments"]["fields"].update(updates)  # type: ignore[index,union-attr]

    with pytest.raises(ValidationError, match=message):
        ParticipantActionContract.model_validate(payload)


def test_compiler_binds_argument_shape_identity_to_compiled_action() -> None:
    compiled = _compiled_contract()

    assert compiled.argument_shape_ref.startswith(f"{ACTION_ADDRESS}.argument-shape.sha256-")
    assert {definition["name"] for definition in compiled.argument_definitions} == {
        "target",
        "attempts",
        "fields",
    }

    changed_payload = _contract_payload()
    changed_payload["arguments"]["attempts"]["maximum"] = 4  # type: ignore[index]
    changed = ParticipantActionContract.model_validate(changed_payload)
    changed_runtime = _compile_action_contracts(SimpleNamespace(action_contracts={"respond": changed}))[ACTION_ADDRESS]
    assert changed_runtime.argument_shape_ref != compiled.argument_shape_ref


def test_argument_shape_survives_scenario_instantiation_and_public_compilation() -> None:
    authored = Scenario.model_validate(
        {
            "name": "act-622",
            "action_contracts": {"respond": _contract_payload()},
        }
    )

    instantiated = instantiate_scenario(authored, {})
    runtime = compile_runtime_model(instantiated)

    assert instantiated.action_contracts["respond"].arguments["attempts"].default == 2
    assert runtime.action_contracts[ACTION_ADDRESS].argument_shape_ref.startswith(
        f"{ACTION_ADDRESS}.argument-shape.sha256-"
    )


def test_concrete_arguments_are_normalized_before_backend_admission() -> None:
    compiled = _compiled_contract()

    validated = resolve_participant_action_arguments(
        compiled,
        action_contract_address=ACTION_ADDRESS,
        argument_shape_ref=compiled.argument_shape_ref,
        proposal_ref="proposals.respond.1",
        proposed_arguments={
            "target": "accounts.alice",
            "fields": [" hostname ", "status"],
        },
    )

    assert validated.argument_map == {
        "attempts": 2,
        "fields": ("hostname", "status"),
        "target": "accounts.alice",
    }
    assert validated.defaulted_argument_names == ("attempts",)
    assert validated.omitted_argument_names == ()
    assert validated.argument_shape_ref == compiled.argument_shape_ref


@pytest.mark.parametrize(
    ("arguments", "message"),
    (
        ({"target": "accounts.alice", "unknown": "value"}, "unknown arguments"),
        ({"target": "accounts.mallory"}, "allowed_values"),
        ({"target": "accounts.alice", "attempts": 4}, "maximum"),
        ({"target": "accounts.alice", "fields": ["hostname", "owner", "status"]}, "max_items"),
        ({"target": "accounts.alice", "fields": ["hostname", "hostname"]}, "unique"),
        ({"target": 1}, "reference"),
    ),
)
def test_concrete_arguments_fail_closed(
    arguments: dict[str, object],
    message: str,
) -> None:
    compiled = _compiled_contract()

    with pytest.raises(ValueError, match=message):
        resolve_participant_action_arguments(
            compiled,
            action_contract_address=ACTION_ADDRESS,
            argument_shape_ref=compiled.argument_shape_ref,
            proposal_ref="proposals.respond.invalid",
            proposed_arguments=arguments,
        )


def test_normalized_carrier_is_backend_independent_and_immutable() -> None:
    compiled = _compiled_contract()
    kwargs = {
        "action_contract_address": ACTION_ADDRESS,
        "argument_shape_ref": compiled.argument_shape_ref,
        "proposal_ref": "proposals.respond.1",
        "proposed_arguments": {"target": "accounts.bob", "fields": ["owner"]},
    }

    left = resolve_participant_action_arguments(compiled, **kwargs)
    right = resolve_participant_action_arguments(compiled, **kwargs)

    assert left == right
    with pytest.raises((AttributeError, TypeError)):
        left.normalized_arguments += (("target", "accounts.mallory"),)
