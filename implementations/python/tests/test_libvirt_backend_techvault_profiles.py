"""TechVault profile selection for the libvirt operational driver."""

from __future__ import annotations

import json

from aces_backend_libvirt.techvault_profiles import select_profiles_for_nodes


def test_select_profiles_for_nodes_maps_aces_names_and_dependencies(tmp_path):
    (tmp_path / "aptl.json").write_text(
        json.dumps(
            {
                "containers": {
                    "wazuh": True,
                    "kali": True,
                    "enterprise": True,
                    "soc": True,
                    "victim": False,
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "docker-compose.yml").write_text(
        """
services:
  wazuh.manager:
    profiles: ["wazuh"]
    container_name: aptl-wazuh-manager
  thehive:
    profiles: ["soc"]
    container_name: aptl-thehive
    depends_on:
      cortex:
        condition: service_healthy
  cortex:
    profiles: ["soc"]
    container_name: aptl-cortex
  kali:
    profiles: ["kali"]
    container_name: aptl-kali
  workstation:
    profiles: ["enterprise"]
    container_name: aptl-workstation
  ignored:
    profiles: ["victim"]
    container_name: aptl-ignored
""",
        encoding="utf-8",
    )

    selection = select_profiles_for_nodes(tmp_path, ["wazuh-manager", "thehive", "kali", "workstation"])

    assert selection.profiles == ("wazuh", "kali", "enterprise", "soc", "otel")
    assert selection.unmapped_nodes == ()
    assert selection.mapped_nodes["wazuh-manager"] == ("wazuh",)
    assert selection.mapped_nodes["thehive"] == ("soc",)


def test_select_profiles_for_nodes_reports_unmapped_nodes(tmp_path):
    (tmp_path / "aptl.json").write_text('{"containers": {"wazuh": true}}', encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text(
        """
services:
  wazuh.manager:
    profiles: ["wazuh"]
    container_name: aptl-wazuh-manager
""",
        encoding="utf-8",
    )

    selection = select_profiles_for_nodes(tmp_path, ["wazuh-manager", "unknown-node"])

    assert selection.profiles == ("wazuh", "otel")
    assert selection.unmapped_nodes == ("unknown-node",)
