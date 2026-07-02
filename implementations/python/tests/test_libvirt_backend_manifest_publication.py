"""Issue #602: published conformance acceptance bar for the libvirt manifest.

Issue #601 shipped the truthful libvirt/QEMU ``backend-manifest-v2`` builder but
left it bound only to the Python model. These tests *publish* that manifest by
binding it to the published contract authorities -- the checked-in JSON Schema,
the ``provisioning-only`` backend profile, and the target conformance runner --
so the issue #602 acceptance criteria are locked against regression:

1. the manifest validates against
   ``contracts/schemas/backend-manifest/backend-manifest-v2.json``;
2. ``supported_contract_versions`` covers the published provisioning-only
   profile contract set;
3. ``realization_support`` declares the node-type / os-family / content-type /
   account-feature kinds the substrate genuinely realizes, with no hollow
   (unbacked) declaration.

The manifest is the capability surface the planner checks plans against, so this
bar is the SEM-218 realization-honesty guard. Under issue #603 the libvirt
interpreter realizes ``node``, ``network``, ``account-placement``,
``content-placement``, and ``feature-binding`` provisioning resources via
cloud-init (see ``aces_backend_libvirt/realization.py``), so the manifest
declares the full governed vocabulary it actually realizes — every declared term
is backed, so it cannot over-claim. "Provisioning-only" remains true in the
domain sense (no orchestrator / evaluator / participant runtime).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
from aces_backend_libvirt import create_libvirt_manifest
from aces_backend_libvirt.target import create_libvirt_target
from aces_backend_protocols.manifest import backend_manifest_payload
from aces_contracts.backend_profiles import load_backend_profile
from aces_contracts.contracts import BackendManifestV2Model
from libvirt_conformance_fixtures import RecordingLibvirtDriver

from aces.core.runtime.conformance import (
    BackendCapabilityProfile,
    required_contracts,
    run_target_conformance,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_MANIFEST_V2_SCHEMA = REPO_ROOT / "contracts" / "schemas" / "backend-manifest" / "backend-manifest-v2.json"
PROVISIONING_ONLY_PROFILE = "provisioning-only"

# A realization-support constraint kind is truthful only when the provisioner
# capability surface that backs it is non-empty. The libvirt interpreter realizes
# all four kinds via cloud-init; this map validates that the manifest stays honest
# (every declared kind backed by a non-empty capability surface) after any future
# capability change.
_CONSTRAINT_KIND_TO_PROVISIONER_SURFACE = {
    "node-type": "supported_node_types",
    "os-family": "supported_os_families",
    "content-type": "supported_content_types",
    "account-feature": "supported_account_features",
}


def _published_payload() -> dict:
    return backend_manifest_payload(create_libvirt_manifest())


def test_libvirt_manifest_validates_against_published_schema():
    """AC1: the rendered payload validates against the checked-in JSON Schema and model."""
    payload = _published_payload()

    schema = json.loads(BACKEND_MANIFEST_V2_SCHEMA.read_text())
    jsonschema.validate(payload, schema)  # raises on any schema violation
    BackendManifestV2Model.model_validate(payload)


def test_libvirt_target_passes_provisioning_only_conformance():
    """AC1: the target conforms to the published provisioning-only profile, daemon-free.

    The live provisioning probe (issue #606) is exercised through a daemon-free
    recording driver that confirms realization, so conformance proves real
    snapshot mutation without a libvirt/QEMU daemon.
    """
    report = run_target_conformance(create_libvirt_target(driver=RecordingLibvirtDriver()))

    assert report.profile == BackendCapabilityProfile.PROVISIONING_ONLY
    assert report.passed is True, [diag.message for diag in report.diagnostics]
    assert not report.unsupported_contract_gaps
    assert not report.unsupported_capability_gaps

    live_manifest = next((case for case in report.cases if case.name == "live-manifest"), None)
    assert live_manifest is not None, "conformance must run the live-manifest validation case"
    assert live_manifest.passed, [diag.message for diag in live_manifest.diagnostics]


def test_supported_contract_versions_cover_provisioning_only_profile():
    """AC2: supported_contract_versions covers the published provisioning-only contract set."""
    manifest = create_libvirt_manifest()

    profile_required = set(load_backend_profile(PROVISIONING_ONLY_PROFILE).required_contracts)
    runner_required = set(required_contracts(BackendCapabilityProfile.PROVISIONING_ONLY))

    assert profile_required, "published provisioning-only profile must declare required contracts"
    assert profile_required <= manifest.supported_contract_versions
    assert runner_required <= manifest.supported_contract_versions


def test_realization_support_is_not_hollow():
    """AC3: every realization-support declaration discloses and is backed by real capability."""
    manifest = create_libvirt_manifest()
    provisioner = manifest.provisioner
    declarations = backend_manifest_payload(manifest)["realization_support"]

    assert declarations, "manifest must declare at least one realization-support domain"
    for declaration in declarations:
        assert declaration["disclosure_kinds"], "realization-support must disclose backend evidence kinds"
        for kind in declaration.get("supported_constraint_kinds", ()):
            surface = _CONSTRAINT_KIND_TO_PROVISIONER_SURFACE.get(kind)
            assert surface is not None, f"unmapped realization constraint kind {kind!r}"
            assert getattr(provisioner, surface), (
                f"realization declares constraint kind {kind!r} but provisioner surface "
                f"{surface!r} is empty (hollow over-claim)"
            )


def test_manifest_declares_full_realization_envelope():
    """AC3: libvirt declares — and realizes via cloud-init — the full governed vocabulary."""
    manifest = create_libvirt_manifest()
    provisioner = manifest.provisioner
    declared_kinds = {
        kind
        for declaration in backend_manifest_payload(manifest)["realization_support"]
        for kind in declaration.get("supported_constraint_kinds", ())
    }

    assert "content-type" in declared_kinds
    assert "account-feature" in declared_kinds
    assert provisioner.supported_content_types == frozenset({"file", "dataset", "directory"})
    assert provisioner.supported_account_features == frozenset(
        {"groups", "mail", "spn", "shell", "home", "disabled", "auth_method"}
    )
    assert provisioner.supports_accounts is True
    assert provisioner.supports_acls is True
    assert "macos" in provisioner.supported_os_families
