"""Shared fixtures for the libvirt participant-runtime tests and proof driver.

The deterministic participant-implementation manifest, selection, action-result,
and admission helpers now live in
``aces_operations.deterministic_participant_fixtures`` (contracts-only, importable
by both the tests and the shipped paper-evidence producer). This module re-exports
them for the existing acceptance tests and adds the test-only ``NullLibvirtDriver``
(which depends on ``aces_backend_libvirt`` and so cannot live in the operations
package under the ADR-036 module boundary).
"""

from __future__ import annotations

from aces_operations.deterministic_participant_fixtures import (
    AGENT_IDENTITY,
    MANIFEST_DIGEST,
    MANIFEST_REF,
    POLICY_DIGEST,
    POLICY_ID,
    POLICY_VERSION,
    WITHHELD_REFS,
    build_action_result,
    build_implementation_manifest,
    build_implementation_selection,
)

__all__ = [
    "AGENT_IDENTITY",
    "MANIFEST_DIGEST",
    "MANIFEST_REF",
    "POLICY_DIGEST",
    "POLICY_ID",
    "POLICY_VERSION",
    "WITHHELD_REFS",
    "NullLibvirtDriver",
    "build_action_result",
    "build_implementation_manifest",
    "build_implementation_selection",
]


class NullLibvirtDriver:
    """No-op libvirt driver for structural tests that never call realize()."""

    def realize(self, *, networks, domains):
        from aces_backend_libvirt.driver import DriverResult

        return DriverResult()

    def destroy(self, *, networks, domains):
        from aces_backend_libvirt.driver import DriverResult

        return DriverResult()

    def realized_addresses(self):
        return frozenset()
