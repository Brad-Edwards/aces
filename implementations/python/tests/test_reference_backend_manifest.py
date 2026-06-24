"""RUN-314: reference emulation backend manifest tests."""

from __future__ import annotations

from aces_backend_protocols.manifest import backend_manifest_payload
from aces_contracts.contracts import BackendManifestV2Model
from aces_reference_backend import create_reference_backend_manifest

from aces.core.runtime.conformance import (
    BackendCapabilityProfile,
    profile_for_manifest,
)


def test_manifest_renders_as_valid_backend_manifest_v2():
    manifest = create_reference_backend_manifest()

    payload = backend_manifest_payload(manifest)
    model = BackendManifestV2Model.model_validate(payload)

    assert model.identity.name == "reference-emulation"


def test_manifest_infers_full_remote_control_plane_profile():
    manifest = create_reference_backend_manifest()

    assert profile_for_manifest(manifest) == BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE


def test_manifest_declares_orchestrator_evaluator_participant_runtime_and_observation():
    manifest = create_reference_backend_manifest()

    assert manifest.has_orchestrator
    assert manifest.has_evaluator
    assert manifest.has_participant_runtime
    assert manifest.has_observation


def test_manifest_accepts_and_ignores_extra_config_kwargs():
    # Config kwargs flow to both factories; the manifest factory must accept
    # and ignore extras such as ``driver``.
    manifest = create_reference_backend_manifest(driver=object(), workspace="/tmp/x")

    assert manifest.name == "reference-emulation"


def test_manifest_declares_only_evidence_backed_contract_ids():
    # The reference backend mirrors the stub's evidence-backed contract set;
    # it must not over-claim contracts it does not actually emit/validate.
    from aces_backend_stubs.stubs import create_stub_manifest

    reference = create_reference_backend_manifest()
    stub = create_stub_manifest()

    assert reference.supported_contract_versions == stub.supported_contract_versions
