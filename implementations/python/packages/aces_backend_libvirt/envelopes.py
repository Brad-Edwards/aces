"""Configuration-bound realization envelopes for the libvirt backend."""

from __future__ import annotations

import json
from enum import Enum

from aces_contracts.corpus import REALIZATION_ENVELOPES, corpus_family_root
from aces_contracts.realization_envelope import BackendRealizationEnvelopeModel, realizer_configuration_digest


class LibvirtDriverMode(str, Enum):
    GENERIC = "generic"
    TECHVAULT_APPLIANCE = "techvault-appliance"


_ARTIFACTS = {
    LibvirtDriverMode.GENERIC: "generic-v1.json",
    LibvirtDriverMode.TECHVAULT_APPLIANCE: "techvault-appliance-v1.json",
}


def load_libvirt_realization_envelope(mode: LibvirtDriverMode | str) -> BackendRealizationEnvelopeModel:
    """Load and validate the packaged envelope for one material driver mode."""

    normalized = LibvirtDriverMode(mode)
    path = corpus_family_root(REALIZATION_ENVELOPES) / "libvirt-qemu" / _ARTIFACTS[normalized]
    payload = json.loads(path.read_text(encoding="utf-8"))
    envelope = BackendRealizationEnvelopeModel.model_validate(payload)
    if envelope.configuration.mode != normalized.value:
        raise ValueError("libvirt realization envelope mode does not match selected driver mode")
    if envelope.configuration.configuration_digest != realizer_configuration_digest(envelope.configuration):
        raise ValueError("libvirt realization envelope configuration digest does not match selected driver mode")
    return envelope


__all__ = ["LibvirtDriverMode", "load_libvirt_realization_envelope"]
