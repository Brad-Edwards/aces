"""Typed desired-state resources for stateful service prerequisites."""

from __future__ import annotations

import textwrap

import pytest

from aces.backends.stubs import create_stub_manifest
from aces.core.runtime.compiler import compile_runtime_model
from aces.core.runtime.planner import plan
from aces.core.sdl import SDLParseError, parse_sdl


def _scenario(extra: str = ""):
    return parse_sdl(
        textwrap.dedent(
            f"""
            name: stateful-service
            nodes:
              indexer: {{type: vm, os: linux}}
              manager: {{type: vm, os: linux}}
            generated_artifacts:
              indexer-certs:
                generator: certificate_bundle
                lifecycle: regenerate_on_change
                provenance: config/certs.yml
                outputs:
                  - {{name: root-ca, path: root-ca.pem, sensitivity: public}}
                  - {{name: indexer-key, path: wazuh.indexer-key.pem, sensitivity: secret}}
                  - {{name: indexer-cert, path: wazuh.indexer.pem, sensitivity: public}}
                consumers:
                  - node: indexer
                    mount_destination: /usr/share/wazuh-indexer/certs
                    access_mode: read_only
              manager-config:
                generator: rendered_config
                lifecycle: regenerate_on_change
                provenance: config/wazuh_cluster/wazuh_manager.conf
                outputs:
                  - {{name: ossec-conf, path: ossec.conf, sensitivity: restricted}}
                consumers:
                  - node: manager
                    mount_destination: /wazuh-config-mount/etc/ossec.conf
                    access_mode: read_only
                ordering_dependencies: [generated_artifacts.indexer-certs]
            persistent_volumes:
              indexer-data:
                lifecycle: retain
                access_mode: read_write_once
                consumers:
                  - node: indexer
                    mount_destination: /var/lib/wazuh-indexer
                    access_mode: read_write
                ordering_dependencies: [generated_artifacts.indexer-certs]
            {extra}
            """
        )
    )


def test_stateful_resources_parse_compile_and_plan_in_dependency_order():
    manifest = create_stub_manifest()
    assert manifest.provisioner.supports_generated_artifacts
    assert manifest.provisioner.supports_persistent_volumes
    model = compile_runtime_model(_scenario())

    assert tuple(model.generated_artifacts) == (
        "provision.generated-artifact.indexer-certs",
        "provision.generated-artifact.manager-config",
    )
    assert tuple(model.persistent_volumes) == ("provision.persistent-volume.indexer-data",)

    execution = plan(model, manifest)
    operations = execution.provisioning.operations
    addresses = [operation.address for operation in operations]
    assert addresses.index("provision.generated-artifact.indexer-certs") < addresses.index(
        "provision.generated-artifact.manager-config"
    )
    assert addresses.index("provision.generated-artifact.indexer-certs") < addresses.index(
        "provision.persistent-volume.indexer-data"
    )
    artifact = execution.provisioning.resources["provision.generated-artifact.indexer-certs"]
    assert artifact.resource_type == "generated-artifact"
    assert artifact.payload["spec"]["outputs"][1]["sensitivity"] == "secret"
    assert artifact.payload["spec"]["consumers"][0]["target_address"] == "provision.node.indexer"
    requirements = {
        requirement.address: requirement
        for requirement in model.realization_requirements
        if requirement.requirement_kind in {"generated-artifact", "persistent-volume"}
    }
    assert requirements["provision.generated-artifact.indexer-certs"].field_path == (
        "generated_artifacts.indexer-certs"
    )
    assert requirements["provision.persistent-volume.indexer-data"].explicitness.value == "exact"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            "generated_artifacts:\n  manager-config:\n    ordering_dependencies: [generated_artifacts.missing]",
            "missing",
        ),
        (
            "persistent_volumes:\n  indexer-data:\n    consumers:\n      - node: missing\n        mount_destination: /data\n        access_mode: read_write",
            "missing",
        ),
    ],
)
def test_stateful_resources_reject_unknown_references(mutation: str, message: str):
    if mutation.startswith("generated_artifacts"):
        mutation = mutation.replace(
            "    ordering_dependencies:",
            "    generator: rendered_config\n"
            "    lifecycle: regenerate_on_change\n"
            "    provenance: template.yml\n"
            "    outputs: [{name: config, path: config.yml, sensitivity: restricted}]\n"
            "    consumers: [{node: indexer, mount_destination: /etc/config.yml, access_mode: read_only}]\n"
            "    ordering_dependencies:",
        )
    else:
        mutation = mutation.replace(
            "    consumers:",
            "    lifecycle: retain\n    access_mode: read_write_once\n    consumers:",
        )
    with pytest.raises(SDLParseError, match=message):
        parse_sdl(textwrap.dedent(f"name: invalid\nnodes:\n  indexer: {{type: vm, os: linux}}\n{mutation}\n"))


def test_stateful_resource_dependency_cycle_fails_before_backend_dispatch():
    scenario = parse_sdl(
        textwrap.dedent(
            """
            name: cycle
            nodes:
              indexer: {type: vm, os: linux}
            persistent_volumes:
              a:
                lifecycle: retain
                access_mode: read_write_once
                consumers:
                  - {node: indexer, mount_destination: /a, access_mode: read_write}
                ordering_dependencies: [persistent_volumes.b]
              b:
                lifecycle: retain
                access_mode: read_write_once
                consumers:
                  - {node: indexer, mount_destination: /b, access_mode: read_write}
                ordering_dependencies: [persistent_volumes.a]
            """
        )
    )

    execution = plan(compile_runtime_model(scenario), create_stub_manifest())
    assert not execution.is_valid
    assert any(diagnostic.code == "provisioning.ordering-cycle" for diagnostic in execution.diagnostics)
