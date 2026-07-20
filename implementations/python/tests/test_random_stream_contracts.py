"""DTO validation/serialization tests for the EXP-718 random-stream contracts.

Covers ``RootEntropyModel``/``RandomDrawOutcomeModel`` closed unions,
``StreamAddressModel`` identifier/vocabulary enforcement, the
``RandomStreamControlBindingModel``/``RandomStreamDrawRecordModel`` shapes, and
the non-disclosure property for governed sensitive entropy/outcomes (they must
never serialize resolved bytes -- only reference id/version fields).
"""

from __future__ import annotations

import json

import pytest
from aces_contracts.contracts import ExperimentReferenceModel
from aces_contracts.contracts.random_stream import (
    GovernedEntropyRefModel,
    GovernedRandomOutcomeRefModel,
    PublicRandomOutcomeModel,
    PublicSeedModel,
    RandomStreamControlBindingModel,
    RandomStreamDrawRecordModel,
    RandomStreamProfileReferenceModel,
    StreamAddressModel,
    TrialCoordinateModel,
)
from pydantic import ValidationError

VALID_HEX_SEED = "00" * 31 + "01"


def _profile_ref() -> RandomStreamProfileReferenceModel:
    return RandomStreamProfileReferenceModel(
        ref_kind="profile", ref_id="blake3-xof-v1", ref_version="random-stream-profile/v1"
    )


def _address(**overrides: object) -> StreamAddressModel:
    fields = {
        "namespace": "study-namespace",
        "trial_coordinate": TrialCoordinateModel(condition_id="condition-a", block_id=None, replicate_id=None),
        "selection_policy_id": "policy-a",
        "variation_point_id": "point-a",
        "draw_purpose": "condition-assignment",
        "local_coordinate": 0,
    }
    fields.update(overrides)
    return StreamAddressModel(**fields)


class TestPublicSeedModel:
    def test_accepts_fixed_width_hex(self) -> None:
        seed = PublicSeedModel(kind="public-seed", encoding="hex-fixed-width", value=VALID_HEX_SEED)
        assert seed.value == VALID_HEX_SEED

    def test_rejects_short_hex(self) -> None:
        with pytest.raises(ValidationError):
            PublicSeedModel(kind="public-seed", encoding="hex-fixed-width", value="00")

    def test_rejects_uppercase_hex(self) -> None:
        with pytest.raises(ValidationError):
            PublicSeedModel(kind="public-seed", encoding="hex-fixed-width", value="AB" + "00" * 30)

    def test_rejects_non_hex_characters(self) -> None:
        with pytest.raises(ValidationError):
            PublicSeedModel(kind="public-seed", encoding="hex-fixed-width", value="zz" + "00" * 30)

    def test_forbids_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            PublicSeedModel.model_validate(
                {"kind": "public-seed", "encoding": "hex-fixed-width", "value": VALID_HEX_SEED, "extra": 1}
            )


class TestGovernedEntropyRefModel:
    def test_never_carries_raw_bytes(self) -> None:
        ref = GovernedEntropyRefModel(kind="governed-reference", reference_id="secret-seed-1", reference_version="1")
        dumped = ref.model_dump(mode="json")
        assert set(dumped) == {"kind", "reference_id", "reference_version"}
        serialized = ref.model_dump_json()
        assert "value" not in json.loads(serialized)

    def test_forbids_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            GovernedEntropyRefModel.model_validate(
                {"kind": "governed-reference", "reference_id": "secret-seed-1", "reference_version": "1", "value": "x"}
            )


class TestRandomStreamControlBindingModel:
    def test_accepts_public_seed(self) -> None:
        binding = RandomStreamControlBindingModel(
            profile_ref=_profile_ref(),
            namespace="study-namespace",
            root_entropy=PublicSeedModel(kind="public-seed", encoding="hex-fixed-width", value=VALID_HEX_SEED),
        )
        assert binding.root_entropy.kind == "public-seed"

    def test_accepts_governed_reference(self) -> None:
        binding = RandomStreamControlBindingModel(
            profile_ref=_profile_ref(),
            namespace="study-namespace",
            root_entropy=GovernedEntropyRefModel(
                kind="governed-reference", reference_id="ref-1", reference_version="1"
            ),
        )
        assert binding.root_entropy.kind == "governed-reference"

    def test_root_entropy_union_is_closed_to_declared_kinds(self) -> None:
        payload = {
            "profile_ref": _profile_ref().model_dump(mode="json"),
            "namespace": "study-namespace",
            "root_entropy": {"kind": "raw-value", "value": "danger"},
        }
        with pytest.raises(ValidationError):
            RandomStreamControlBindingModel.model_validate(payload)

    def test_requires_profile_kind_reference(self) -> None:
        bad_ref = ExperimentReferenceModel(ref_kind="task", ref_id="blake3-xof-v1")
        root_entropy = PublicSeedModel(kind="public-seed", encoding="hex-fixed-width", value=VALID_HEX_SEED)
        with pytest.raises(ValidationError):
            RandomStreamControlBindingModel(
                profile_ref=bad_ref,
                namespace="study-namespace",
                root_entropy=root_entropy,
            )

    def test_seed_without_profile_ref_is_rejected(self) -> None:
        """SVR-012: a seed alone, with no generator/derivation identity, is not executable control."""
        with pytest.raises(ValidationError):
            RandomStreamControlBindingModel.model_validate(
                {
                    "namespace": "study-namespace",
                    "root_entropy": {"kind": "public-seed", "encoding": "hex-fixed-width", "value": VALID_HEX_SEED},
                }
            )


class TestTrialCoordinateModel:
    def test_all_fields_optional(self) -> None:
        coordinate = TrialCoordinateModel()
        assert coordinate.condition_id is None
        assert coordinate.block_id is None
        assert coordinate.replicate_id is None

    def test_forbids_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            TrialCoordinateModel.model_validate({"condition_id": "c1", "worker_id": "w1"})


class TestStreamAddressModel:
    def test_accepts_governed_draw_purpose(self) -> None:
        address = _address(draw_purpose="condition-assignment")
        assert address.draw_purpose == "condition-assignment"

    def test_rejects_unknown_draw_purpose(self) -> None:
        with pytest.raises(ValidationError, match="draw_purpose|controlled vocabulary"):
            _address(draw_purpose="not-a-real-purpose")

    def test_rejects_non_portable_namespace(self) -> None:
        with pytest.raises(ValidationError):
            _address(namespace="Not Portable!")

    def test_rejects_negative_local_coordinate(self) -> None:
        with pytest.raises(ValidationError):
            _address(local_coordinate=-1)

    def test_forbids_worker_or_process_fields(self) -> None:
        payload = _address().model_dump(mode="json")
        payload["worker_id"] = "worker-1"
        with pytest.raises(ValidationError):
            StreamAddressModel.model_validate(payload)

    def test_forbids_unbounded_metadata_map(self) -> None:
        payload = _address().model_dump(mode="json")
        payload["metadata"] = {"anything": "goes"}
        with pytest.raises(ValidationError):
            StreamAddressModel.model_validate(payload)


class TestRandomStreamDrawRecordModel:
    def test_accepts_public_outcome(self) -> None:
        record = RandomStreamDrawRecordModel(
            control_id="control-1",
            address=_address(local_coordinate=3),
            transform_id="bounded-integer",
            transform_version="1",
            local_coordinate=3,
            outcome=PublicRandomOutcomeModel(kind="public-value", value="7"),
            rejection_attempts=0,
            rejection_exhausted=False,
        )
        assert record.outcome.value == "7"

    def test_accepts_governed_outcome_without_raw_value(self) -> None:
        record = RandomStreamDrawRecordModel(
            control_id="control-1",
            address=_address(local_coordinate=3),
            transform_id="bounded-integer",
            transform_version="1",
            local_coordinate=3,
            outcome=GovernedRandomOutcomeRefModel(
                kind="governed-reference", reference_id="ref-9", reference_version="1"
            ),
        )
        dumped = record.model_dump(mode="json")
        assert dumped["outcome"] == {"kind": "governed-reference", "reference_id": "ref-9", "reference_version": "1"}
        assert "value" not in dumped["outcome"]

    def test_local_coordinate_must_match_address(self) -> None:
        address = _address(local_coordinate=3)
        outcome = PublicRandomOutcomeModel(kind="public-value", value="7")
        with pytest.raises(ValidationError, match="local_coordinate"):
            RandomStreamDrawRecordModel(
                control_id="control-1",
                address=address,
                transform_id="bounded-integer",
                transform_version="1",
                local_coordinate=4,
                outcome=outcome,
            )

    def test_exhausted_outcome_defaults_are_rejection_facts(self) -> None:
        record = RandomStreamDrawRecordModel(
            control_id="control-1",
            address=_address(local_coordinate=3),
            transform_id="bounded-integer",
            transform_version="1",
            local_coordinate=3,
            outcome=GovernedRandomOutcomeRefModel(
                kind="governed-reference", reference_id="ref-9", reference_version="1"
            ),
            rejection_attempts=5,
            rejection_exhausted=False,
        )
        assert record.rejection_attempts == 5
        assert record.rejection_exhausted is False

    def test_rejection_exhausted_record_omits_outcome(self) -> None:
        record = RandomStreamDrawRecordModel(
            control_id="control-1",
            address=_address(local_coordinate=3),
            transform_id="bounded-integer",
            transform_version="1",
            local_coordinate=3,
            rejection_attempts=32,
            rejection_exhausted=True,
        )
        assert record.outcome is None
        assert record.rejection_exhausted is True

    def test_rejection_exhausted_record_with_outcome_is_rejected(self) -> None:
        address = _address(local_coordinate=3)
        outcome = PublicRandomOutcomeModel(kind="public-value", value="7")
        with pytest.raises(ValidationError, match="rejection_exhausted"):
            RandomStreamDrawRecordModel(
                control_id="control-1",
                address=address,
                transform_id="bounded-integer",
                transform_version="1",
                local_coordinate=3,
                outcome=outcome,
                rejection_attempts=32,
                rejection_exhausted=True,
            )

    def test_non_exhausted_record_without_outcome_is_rejected(self) -> None:
        address = _address(local_coordinate=3)
        with pytest.raises(ValidationError, match="rejection_exhausted"):
            RandomStreamDrawRecordModel(
                control_id="control-1",
                address=address,
                transform_id="bounded-integer",
                transform_version="1",
                local_coordinate=3,
                rejection_attempts=0,
                rejection_exhausted=False,
            )
