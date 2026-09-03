"""Configuration-bound realization envelopes for the reference backend."""

from __future__ import annotations

import json
from enum import Enum

from raes_contracts.corpus import REALIZATION_ENVELOPES, corpus_family_root
from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel


class ReferenceDriverMode(str, Enum):
    IN_PROCESS_EMULATION = "in-process-emulation"
    OCI_CONTAINER = "oci-container"


_ARTIFACTS = {
    ReferenceDriverMode.IN_PROCESS_EMULATION: "in-process-v1.json",
    ReferenceDriverMode.OCI_CONTAINER: "oci-container-v1.json",
}


def load_reference_realization_envelope(
    mode: ReferenceDriverMode | str,
) -> BackendRealizationEnvelopeModel:
    """Load the published envelope for the selected material driver mode."""

    normalized = ReferenceDriverMode(mode)
    path = corpus_family_root(REALIZATION_ENVELOPES) / "reference-emulation" / _ARTIFACTS[normalized]
    envelope = BackendRealizationEnvelopeModel.model_validate(json.loads(path.read_text(encoding="utf-8")))
    if envelope.configuration.mode != normalized.value:
        raise ValueError("reference realization envelope mode does not match selected driver mode")
    return envelope


__all__ = ["ReferenceDriverMode", "load_reference_realization_envelope"]
