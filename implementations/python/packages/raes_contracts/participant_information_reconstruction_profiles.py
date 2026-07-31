"""Closed loaders for ACT-604 participant information reconstruction profiles."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from raes.identifiers import is_portable_identifier

from .contracts import ParticipantInformationReconstructionProfileModel
from .corpus import PROFILES, corpus_family_root

SUPPORTED_PARTICIPANT_INFORMATION_RECONSTRUCTION_PROFILE_IDS = frozenset({"occurrence-prefix-evidence-v1"})


def participant_information_reconstruction_profiles_root() -> Path:
    return corpus_family_root(PROFILES) / "participant-information-reconstruction"


def _validate_profile_id(profile_id: str) -> None:
    if not is_portable_identifier(profile_id):
        raise ValueError(
            f"participant information reconstruction profile id {profile_id!r} must be a portable SDL identifier: "
            "1-64 lowercase ASCII letters, digits, hyphens, or underscores, starting with a letter or digit"
        )
    if profile_id not in SUPPORTED_PARTICIPANT_INFORMATION_RECONSTRUCTION_PROFILE_IDS:
        supported = ", ".join(sorted(SUPPORTED_PARTICIPANT_INFORMATION_RECONSTRUCTION_PROFILE_IDS))
        raise ValueError(
            f"unsupported participant information reconstruction profile id {profile_id!r}; supported ids: {supported}"
        )


def participant_information_reconstruction_profile_path(profile_id: str) -> Path:
    _validate_profile_id(profile_id)
    return participant_information_reconstruction_profiles_root() / f"{profile_id}.json"


def load_participant_information_reconstruction_profile_from_path(
    profile_id: str,
    path: Path,
) -> ParticipantInformationReconstructionProfileModel:
    _validate_profile_id(profile_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    profile = ParticipantInformationReconstructionProfileModel.model_validate(payload)
    if profile.profile_id != profile_id:
        raise ValueError("participant information reconstruction profile artifact identity does not match request")
    return profile


@cache
def load_participant_information_reconstruction_profile(
    profile_id: str,
) -> ParticipantInformationReconstructionProfileModel:
    return load_participant_information_reconstruction_profile_from_path(
        profile_id,
        participant_information_reconstruction_profile_path(profile_id),
    )


__all__ = (
    "SUPPORTED_PARTICIPANT_INFORMATION_RECONSTRUCTION_PROFILE_IDS",
    "load_participant_information_reconstruction_profile",
    "load_participant_information_reconstruction_profile_from_path",
    "participant_information_reconstruction_profile_path",
    "participant_information_reconstruction_profiles_root",
)
