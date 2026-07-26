"""Issue #605: shared provisioner account-feature extraction.

``provisioner_account_features`` is the single spec->feature-term mapping shared
by the processor planner gate (``_validate_manifest``) and the libvirt backend's
capability-envelope diagnostics, so the two never diverge.
"""

from __future__ import annotations

from raes_backend_protocols.account_features import provisioner_account_features


def test_empty_spec_uses_no_features():
    assert provisioner_account_features({}) == frozenset()


def test_full_spec_exercises_every_governed_feature():
    spec = {
        "username": "administrator",
        "groups": ["sudo"],
        "mail": "admin@example.test",
        "spn": "HTTP/host",
        "shell": "/bin/bash",
        "home": "/home/administrator",
        "disabled": True,
        "auth_method": "ssh-key",
    }

    assert provisioner_account_features(spec) == frozenset(
        {"groups", "mail", "spn", "shell", "home", "disabled", "auth_method"}
    )


def test_descriptive_defaults_are_not_features():
    # A username alone, an enabled account, and a plain password login are not
    # account "features"; only opt-in, non-default values count.
    spec = {"username": "alice", "disabled": False, "auth_method": "password"}

    assert provisioner_account_features(spec) == frozenset()


def test_empty_collection_values_are_not_features():
    assert provisioner_account_features({"groups": [], "shell": "", "home": ""}) == frozenset()
