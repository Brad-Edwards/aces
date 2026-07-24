"""Composition, publication, and determinism tests for DSL-437."""

from __future__ import annotations

import hashlib
import json
import textwrap
from pathlib import Path

import pytest
import yaml
from aces_backend_protocols.capabilities import BackendManifest, LiveActivityCapabilities
from aces_backend_protocols.manifest import backend_manifest_from_v2_model, backend_manifest_payload
from aces_backend_stubs.stubs import create_stub_manifest
from aces_contracts.contracts import BackendManifestV2Model, schema_bundle
from aces_contracts.contracts.live_activity import (
    ActivityGovernedEntropyIdentityModel,
    ActivityOccurrenceContextModel,
)
from aces_contracts.live_activity_addressing import (
    LIVE_ACTIVITY_OCCURRENCE_DOMAIN,
    LIVE_ACTIVITY_PROFILE_DIGEST_DOMAIN,
    activity_occurrence_context,
    canonical_activity_occurrence_bytes,
    canonical_activity_profile_bytes,
    derive_activity_occurrence_identities,
)
from aces_processor.compiler import compile_runtime_model
from aces_sdl import (
    SDLInstantiationError,
    SDLParseError,
    instantiate_scenario,
    parse_sdl,
    parse_sdl_file,
)
from jsonschema import Draft202012Validator
from live_activity_fixtures import valid_live_activity_payload
from pydantic import ValidationError


def _parse(payload: dict[str, object]):
    return parse_sdl(yaml.safe_dump(payload, sort_keys=False))


def _profile(payload: dict[str, object]) -> dict[str, object]:
    return payload["activity_profiles"]["ordinary-records"]  # type: ignore[index,return-value]


def _exact_capability() -> LiveActivityCapabilities:
    return LiveActivityCapabilities(
        supported_contract_profiles=frozenset({"aces-live-activity/v1"}),
        supported_operation_profiles=frozenset({"protocol-operation/v1:http_api:update"}),
        supported_schedule_profiles=frozenset({"finite-logical-schedule/v1"}),
        supported_readback_profiles=frozenset({"evidence-readback/v1"}),
        supported_lifecycle_profiles=frozenset({"range-lifecycle/v1"}),
        supported_resource_dimensions=frozenset({"operations"}),
        supported_dependency_kinds=frozenset({"ordering", "refresh"}),
        supports_bounded_retry=True,
        supports_generation_lifecycle=True,
        supports_participant_reservation=True,
        supports_readback_provenance=True,
    )


def _manifest_with_activity() -> BackendManifest:
    base = create_stub_manifest()
    return BackendManifest(
        identity=base.identity,
        supported_contract_versions=base.supported_contract_versions
        | frozenset({"live-activity-profile-v1", "live-activity-occurrence-v1"}),
        compatibility=base.compatibility,
        realization_support=base.realization_support,
        concept_bindings=base.concept_bindings,
        constraints=base.constraints,
        provisioner=base.provisioner,
        orchestrator=base.orchestrator,
        evaluator=base.evaluator,
        participant_runtime=base.participant_runtime,
        observation=base.observation,
        historical_state=base.historical_state,
        live_activity=_exact_capability(),
    )


def test_backend_manifest_live_activity_capability_round_trips_exactly() -> None:
    manifest = _manifest_with_activity()
    payload = backend_manifest_payload(manifest)
    reconstructed = backend_manifest_from_v2_model(BackendManifestV2Model.model_validate(payload))

    assert reconstructed.live_activity == manifest.live_activity
    assert payload["capabilities"]["live_activity"]["supports_bounded_retry"] is True


def test_backend_live_activity_capability_schema_rejects_unknown_profile_terms() -> None:
    payload = backend_manifest_payload(_manifest_with_activity())
    payload["capabilities"]["live_activity"]["supported_schedule_profiles"] = ["cron/v1"]

    with pytest.raises(ValidationError, match="schedule|literal"):
        BackendManifestV2Model.model_validate(payload)


def test_activity_profile_jcs_is_independent_of_mapping_insertion_order() -> None:
    first_scenario = _parse(valid_live_activity_payload())
    second_payload = valid_live_activity_payload()
    profile_payload = _profile(second_payload)
    profile_payload["actors"] = dict(reversed(list(profile_payload["actors"].items())))  # type: ignore[union-attr]
    profile_payload["execution_contexts"] = dict(
        reversed(list(profile_payload["execution_contexts"].items()))  # type: ignore[union-attr]
    )
    second_scenario = _parse(second_payload)
    first_model = compile_runtime_model(first_scenario)
    second_model = compile_runtime_model(second_scenario)
    first_profile = first_scenario.activity_profiles["ordinary-records"]
    second_profile = second_scenario.activity_profiles["ordinary-records"]

    assert canonical_activity_profile_bytes(
        "ordinary-records",
        first_profile,
        first_model.historical_baseline_digests["enterprise"],
    ) == canonical_activity_profile_bytes(
        "ordinary-records",
        second_profile,
        second_model.historical_baseline_digests["enterprise"],
    )
    assert (
        first_model.activity_profiles["ordinary-records"].activity_digest
        == second_model.activity_profiles["ordinary-records"].activity_digest
    )


def test_published_formal_replay_vector_matches_example() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    vector = json.loads(
        (repo_root / "docs/research/formal-semantic-validation/live-activity-replay-v1.json").read_text(
            encoding="utf-8"
        )
    )
    scenario = parse_sdl_file(repo_root / vector["source"])
    compiled = compile_runtime_model(scenario).activity_profiles[vector["activity_profile_id"]]
    profile_bytes = canonical_activity_profile_bytes(
        vector["activity_profile_id"],
        scenario.activity_profiles[vector["activity_profile_id"]],
        compiled.baseline_digest,
    )
    context = ActivityOccurrenceContextModel.model_validate(vector["occurrence_context"])
    occurrence_bytes = canonical_activity_occurrence_bytes(context)

    assert vector["profile_digest_domain_hex"] == LIVE_ACTIVITY_PROFILE_DIGEST_DOMAIN.hex()
    assert vector["occurrence_digest_domain_hex"] == LIVE_ACTIVITY_OCCURRENCE_DOMAIN.hex()
    assert vector["historical_baseline_digest"] == compiled.baseline_digest.value
    assert vector["activity_digest"] == compiled.activity_digest.value
    assert vector["profile_canonical_sha256"] == hashlib.sha256(profile_bytes).hexdigest()
    assert vector["occurrence_canonical_sha256"] == hashlib.sha256(occurrence_bytes).hexdigest()
    assert vector["occurrence_identity"] == derive_activity_occurrence_identities([context])[0].value


def test_occurrence_collision_simulation_fails_atomically(monkeypatch: pytest.MonkeyPatch) -> None:
    from aces_contracts import live_activity_addressing

    compiled = compile_runtime_model(_parse(valid_live_activity_payload())).activity_profiles["ordinary-records"]
    first = activity_occurrence_context(
        compiled,
        action_id="update-record",
        logical_time_seconds=15,
        occurrence_ordinal=1,
    )
    second = activity_occurrence_context(
        compiled,
        action_id="update-record",
        logical_time_seconds=30,
        occurrence_ordinal=2,
    )
    monkeypatch.setattr(live_activity_addressing, "_digest_occurrence", lambda _canonical: b"\x00" * 32)

    with pytest.raises(ValueError, match="digest collision"):
        derive_activity_occurrence_identities([first, second])


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("activity_digest", "sha256:" + "1" * 64),
        ("historical_baseline_digest", "sha256:" + "2" * 64),
        ("template_id", "activity_templates.other"),
        ("execution_context_id", "activity_profiles.ordinary-records.execution_contexts.other"),
        ("random_stream_profile", "blake3-xof-v2"),
        (
            "entropy_identity",
            ActivityGovernedEntropyIdentityModel(
                kind="governed-reference",
                reference_id="entropy-other",
                reference_version="2",
            ),
        ),
    ],
)
def test_occurrence_identity_mutates_for_remaining_required_coordinates(
    field: str,
    replacement: object,
) -> None:
    compiled = compile_runtime_model(_parse(valid_live_activity_payload())).activity_profiles["ordinary-records"]
    context = activity_occurrence_context(
        compiled,
        action_id="update-record",
        logical_time_seconds=15,
        occurrence_ordinal=1,
    )
    original = derive_activity_occurrence_identities([context])[0]
    changed = context.model_copy(update={field: replacement})

    assert derive_activity_occurrence_identities([changed])[0].value != original.value


def test_composition_namespaces_all_external_activity_references(tmp_path: Path) -> None:
    payload = valid_live_activity_payload()
    exported_sections = (
        "nodes",
        "entities",
        "content",
        "persistent_volumes",
        "accounts",
        "deployment_tenants",
        "deployment_cells",
        "evidence_requirements",
        "propositions",
        "assertions",
        "observation_boundaries",
        "relationships",
        "historical_baselines",
        "activity_templates",
        "activity_profiles",
    )
    payload["module"] = {
        "id": "aces/live-activity",
        "version": "1.0.0",
        "exports": {
            section: list(payload[section])  # type: ignore[arg-type]
            for section in exported_sections
        },
    }
    module = tmp_path / "activity.yaml"
    module.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    root = tmp_path / "root.yaml"
    root.write_text(
        textwrap.dedent(
            """
            name: root
            imports:
              - path: activity.yaml
                namespace: office
                version: 1.0.0
            """
        ),
        encoding="utf-8",
    )

    scenario = parse_sdl_file(root)
    profile = scenario.activity_profiles["office.ordinary-records"]

    assert profile.historical_baseline_ref == "office.enterprise"
    assert profile.actors["records-clerk"].entity_ref == "office.operations"
    assert profile.actors["records-clerk"].account_ref == "office.records-operator"
    assert profile.execution_contexts["records-api"].target_service_ref == "nodes.office.archive.services.records"
    assert profile.actions["update-record"].template_ref == "office.record-update"
    assert (
        profile.actions["update-record"].parameter_bindings[0].value_ref
        == "historical_baselines.office.enterprise.objects.message-001"
    )
    assert profile.telemetry.evidence_requirement_refs == ["office.native-readback"]


def test_activity_reference_variables_defer_then_revalidate() -> None:
    payload = valid_live_activity_payload()
    payload["variables"] = {
        "tenant": {"type": "string", "default": "range-a"},
        "interval": {"type": "string", "default": "15s"},
    }
    profile = _profile(payload)
    profile["actors"]["records-clerk"]["deployment_tenant_ref"] = "${tenant}"  # type: ignore[index]
    profile["execution_contexts"]["records-api"]["deployment_tenant_ref"] = "${tenant}"  # type: ignore[index]
    profile["schedules"]["steady"]["interval_seconds"] = "${interval}"  # type: ignore[index]

    authored = _parse(payload)
    instantiated = instantiate_scenario(authored)
    assert instantiated.activity_profiles["ordinary-records"].schedules["steady"].interval_seconds == 15

    with pytest.raises(SDLInstantiationError, match="tenant"):
        instantiate_scenario(authored, parameters={"tenant": "other", "interval": "15s"})


def test_identity_profile_fields_reject_unresolved_variables() -> None:
    payload = valid_live_activity_payload()
    payload["variables"] = {"profile": {"type": "string", "default": "finite-logical-schedule/v1"}}
    _profile(payload)["schedules"]["steady"]["profile"] = "${profile}"  # type: ignore[index]

    with pytest.raises(SDLParseError):
        _parse(payload)


def test_all_scenario_schema_surfaces_and_backend_manifest_publish_activity_shape() -> None:
    bundle = schema_bundle()
    payload = valid_live_activity_payload()
    instantiated = {
        **payload,
        "instantiation_provenance": {
            "authored_digest": {
                "profile": "aces-sdl-semantic/v1",
                "algorithm": "sha256",
                "value": "sha256:" + "a" * 64,
            }
        },
    }

    assert Draft202012Validator(bundle["sdl-authoring-input-v1"]).is_valid(payload)
    assert Draft202012Validator(bundle["instantiated-scenario-v1"]).is_valid(instantiated)
    assert Draft202012Validator(bundle["instantiated-scenario-snapshot-v1"]).is_valid(
        {
            "profile": "aces-sdl-instantiated-snapshot/v1",
            "scenario": instantiated,
        }
    )
    backend_schema = bundle["backend-manifest-v2"]
    assert Draft202012Validator(backend_schema).is_valid(backend_manifest_payload(_manifest_with_activity()))


@pytest.mark.parametrize(
    "contract_id",
    ["live-activity-profile-v1", "live-activity-occurrence-v1"],
)
def test_published_live_activity_fixtures_enforce_closed_contracts(contract_id: str) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    fixture_root = repo_root / "contracts/fixtures/live-activity" / contract_id
    validator = Draft202012Validator(schema_bundle()[contract_id])

    valid = sorted((fixture_root / "valid").glob("*.json"))
    invalid = sorted((fixture_root / "invalid").glob("*.json"))
    assert valid and invalid
    assert all(validator.is_valid(json.loads(path.read_text(encoding="utf-8"))) for path in valid)
    assert all(not validator.is_valid(json.loads(path.read_text(encoding="utf-8"))) for path in invalid)


def test_profile_does_not_redeclare_baseline_identity_authorities() -> None:
    profile_fields = set(schema_bundle()["sdl-authoring-input-v1"]["$defs"]["ActivityProfile"]["properties"])

    assert {
        "range_instance_id",
        "reset_generation_id",
        "historical_baseline_digest",
    }.isdisjoint(profile_fields)
