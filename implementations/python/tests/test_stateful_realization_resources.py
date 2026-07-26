"""Typed desired-state resources for stateful service prerequisites."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from raes import SDLParseError, SDLValidationError, parse_sdl, parse_sdl_file
from raes_backend_stubs.stubs import create_stub_manifest
from raes_contracts.contracts import schema_bundle
from raes_processor.compiler import compile_runtime_model
from raes_processor.planner import plan


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
    invalid_sdl = textwrap.dedent(f"name: invalid\nnodes:\n  indexer: {{type: vm, os: linux}}\n{mutation}\n")
    with pytest.raises(SDLValidationError, match=message):
        parse_sdl(invalid_sdl)


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


def test_stateful_resources_reject_ambiguous_bare_dependency_during_semantic_admission():
    invalid_sdl = textwrap.dedent(
        """
        name: ambiguous-stateful-dependency
        nodes:
          vm: {type: vm, os: linux}
        generated_artifacts:
          shared:
            generator: rendered_config
            lifecycle: regenerate_on_change
            provenance: config.yml
            outputs: [{name: config, path: config.yml, sensitivity: restricted}]
            consumers: [{node: vm, mount_destination: /etc/config.yml, access_mode: read_only}]
          consumer:
            generator: rendered_config
            lifecycle: regenerate_on_change
            provenance: consumer.yml
            outputs: [{name: consumer, path: consumer.yml, sensitivity: restricted}]
            consumers: [{node: vm, mount_destination: /etc/consumer.yml, access_mode: read_only}]
            ordering_dependencies: [shared]
        persistent_volumes:
          shared:
            lifecycle: retain
            access_mode: read_write_once
            consumers: [{node: vm, mount_destination: /var/lib/shared, access_mode: read_write}]
        """
    )

    with pytest.raises(SDLValidationError, match="ambiguous.*generated_artifacts.shared.*persistent_volumes.shared"):
        parse_sdl(invalid_sdl)


def test_composed_stateful_resources_reject_ambiguous_bare_dependency(tmp_path: Path):
    module = tmp_path / "stateful-module.yaml"
    module.write_text(
        textwrap.dedent(
            """
            name: stateful-module
            version: 1.0.0
            module:
              id: acme/stateful-module
              version: 1.0.0
              exports:
                nodes: [vm]
                generated_artifacts: [shared, consumer]
                persistent_volumes: [shared]
            nodes:
              vm: {type: vm, os: linux}
            generated_artifacts:
              shared:
                generator: rendered_config
                lifecycle: regenerate_on_change
                provenance: shared.yml
                outputs: [{name: shared, path: shared.yml, sensitivity: restricted}]
                consumers: [{node: vm, mount_destination: /etc/shared.yml, access_mode: read_only}]
              consumer:
                generator: rendered_config
                lifecycle: regenerate_on_change
                provenance: consumer.yml
                outputs: [{name: consumer, path: consumer.yml, sensitivity: restricted}]
                consumers: [{node: vm, mount_destination: /etc/consumer.yml, access_mode: read_only}]
                ordering_dependencies: [shared]
            persistent_volumes:
              shared:
                lifecycle: retain
                access_mode: read_write_once
                consumers: [{node: vm, mount_destination: /var/lib/shared, access_mode: read_write}]
            """
        ),
        encoding="utf-8",
    )
    root = tmp_path / "root.yaml"
    root.write_text(
        textwrap.dedent(
            """
            name: root
            imports:
              - source: local:stateful-module.yaml
                namespace: imported
                version: 1.0.0
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(SDLValidationError, match="ambiguous.*generated_artifacts.shared.*persistent_volumes.shared"):
        parse_sdl_file(root)


@pytest.mark.parametrize(
    ("resources", "message", "error_type"),
    [
        (
            """
            generated_artifacts:
              config:
                generator: rendered_config
                lifecycle: regenerate_on_change
                provenance: config.yml
                outputs: [{name: config, path: config.yml, sensitivity: restricted}]
                consumers: [{node: first, mount_destination: /srv/shared, access_mode: read_only}]
            persistent_volumes:
              data:
                lifecycle: retain
                access_mode: read_write_once
                consumers: [{node: first, mount_destination: /srv/shared, access_mode: read_write}]
            """,
            "mount_destination.*already consumed",
            SDLValidationError,
        ),
        (
            """
            generated_artifacts:
              config:
                generator: rendered_config
                lifecycle: regenerate_on_change
                provenance: config.yml
                outputs: [{name: config, path: config.yml, sensitivity: restricted}]
                consumers: [{node: first, mount_destination: /etc/config.yml, access_mode: read_write}]
            """,
            "generated artifact consumers must be read_only",
            SDLParseError,
        ),
        (
            """
            persistent_volumes:
              data:
                lifecycle: retain
                access_mode: read_write_once
                consumers:
                  - {node: first, mount_destination: /srv/first, access_mode: read_write}
                  - {node: second, mount_destination: /srv/second, access_mode: read_write}
            """,
            "read_write_once.*at most one writer node",
            SDLParseError,
        ),
        (
            """
            persistent_volumes:
              data:
                lifecycle: retain
                access_mode: read_write_once
                consumers: [{node: windows, mount_destination: /srv/data, access_mode: read_write}]
            """,
            "POSIX.*Windows",
            SDLValidationError,
        ),
        (
            """
            persistent_volumes:
              data:
                lifecycle: retain
                access_mode: read_write_once
                consumers: [{node: first, mount_destination: //srv/data, access_mode: read_write}]
            """,
            "canonical contained POSIX",
            SDLParseError,
        ),
    ],
)
def test_stateful_resources_reject_cross_resource_access_conflicts(
    resources: str,
    message: str,
    error_type: type[Exception],
):
    invalid_sdl = textwrap.dedent(
        """
        name: invalid-stateful-access
        nodes:
          first: {type: vm, os: linux}
          second: {type: vm, os: linux}
          windows: {type: vm, os: windows}
        """
    ) + textwrap.dedent(resources)

    with pytest.raises(error_type, match=message):
        parse_sdl(invalid_sdl)


@pytest.mark.parametrize(
    "invalid_path",
    [
        ".",
        "config//app.yml",
        "config/./app.yml",
        "config\\app.yml",
    ],
)
def test_generated_artifact_output_paths_must_be_canonical_posix(invalid_path: str):
    invalid_sdl = textwrap.dedent(
        f"""
        name: invalid-output-path
        nodes:
          vm: {{type: vm, os: linux}}
        generated_artifacts:
          config:
            generator: rendered_config
            lifecycle: regenerate_on_change
            provenance: config.yml
            outputs: [{{name: config, path: {invalid_path!r}, sensitivity: restricted}}]
            consumers: [{{node: vm, mount_destination: /etc/config.yml, access_mode: read_only}}]
        """
    )

    with pytest.raises(SDLParseError, match="canonical contained POSIX"):
        parse_sdl(invalid_sdl)


def test_stateful_collection_schema_rejects_exact_duplicates():
    payload = {
        "name": "duplicate-stateful-members",
        "nodes": {"vm": {"type": "vm", "os": "linux"}},
        "generated_artifacts": {
            "config": {
                "generator": "rendered_config",
                "lifecycle": "regenerate_on_change",
                "provenance": "config.yml",
                "outputs": [
                    {"name": "config", "path": "config.yml", "sensitivity": "restricted"},
                    {"name": "config", "path": "config.yml", "sensitivity": "restricted"},
                ],
                "consumers": [{"node": "vm", "mount_destination": "/etc/config.yml", "access_mode": "read_only"}],
            }
        },
    }

    schema = schema_bundle()["sdl-authoring-input-v1"]
    assert not Draft202012Validator(schema).is_valid(payload)


def test_stateful_schema_discloses_model_only_semantic_invariants():
    schema = schema_bundle()["sdl-authoring-input-v1"]
    invariant_ids = {entry["id"] for entry in schema["x-aces-invariants"]}

    assert {
        "stateful-generated-artifact-semantics",
        "stateful-persistent-volume-semantics",
        "stateful-cross-resource-semantics",
    } <= invariant_ids
    assert schema["x-aces-semantic-profile"]["required"] is True
