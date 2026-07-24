"""DSL-437 deterministic range-bound live-activity contract."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest
import yaml
from aces_backend_protocols.capabilities import BackendManifest, LiveActivityCapabilities
from aces_backend_stubs.stubs import create_stub_manifest
from aces_contracts.live_activity_addressing import (
    activity_occurrence_context,
    derive_activity_occurrence_identities,
    validate_activity_occurrence_context,
)
from aces_processor.compiler import compile_runtime_model
from aces_processor.planner import plan
from aces_sdl import SDLParseError, SDLValidationError, parse_sdl
from live_activity_fixtures import valid_live_activity_payload


def _parse(payload: dict[str, object]):
    return parse_sdl(yaml.safe_dump(payload, sort_keys=False))


def _profile(payload: dict[str, object]) -> dict[str, object]:
    return payload["activity_profiles"]["ordinary-records"]  # type: ignore[index,return-value]


def _with_second_action(payload: dict[str, object]) -> dict[str, object]:
    profile = _profile(payload)
    profile["actions"]["update-second"] = deepcopy(profile["actions"]["update-record"])  # type: ignore[index]
    profile["readback"]["action_refs"].append("update-second")  # type: ignore[index]
    profile["budgets"][0]["action_demands"]["update-second"] = {  # type: ignore[index]
        "numerator": 1,
        "denominator": 1,
    }
    return profile


def _assert_validation_code(payload: dict[str, object], code: str) -> None:
    with pytest.raises(SDLValidationError) as exc_info:
        _parse(payload)
    assert f"[{code}]" in str(exc_info.value)


def _bind_case_service(payload: dict[str, object]) -> None:
    payload["nodes"]["archive"]["services"].append({"name": "cases", "port": 9443})  # type: ignore[index]
    payload["persistent_volumes"]["tenant-cases"] = {  # type: ignore[index]
        "lifecycle": "ephemeral",
        "access_mode": "read_write_once",
        "consumers": [
            {
                "node": "archive",
                "mount_destination": "/var/lib/cases",
                "access_mode": "read_write",
            }
        ],
    }
    payload["relationships"]["cases-reset-owner"] = {  # type: ignore[index]
        "type": "uses_shared_service",
        "source": "range-a",
        "target": "nodes.archive.services.cases",
        "shared_service": {
            "tenant_isolation": "none",
            "workload_authentication": "workload_identity",
            "mutable_state_refs": ["tenant-cases"],
            "mutable_state_owner": "consumer_tenant",
            "reset_generation_owner": "consumer_tenant",
        },
    }
    case_binding = payload["historical_baselines"]["enterprise"]["materialization_bindings"]["case-native"]  # type: ignore[index]
    case_binding["target_service_ref"] = "nodes.archive.services.cases"  # type: ignore[index]
    case_binding["reset_owner_relationship_ref"] = "cases-reset-owner"  # type: ignore[index]


def test_complete_provider_neutral_activity_profile_is_admitted() -> None:
    scenario = _parse(valid_live_activity_payload())

    assert scenario.activity_templates["record-update"].capability.operation.value == "update"
    assert scenario.activity_profiles["ordinary-records"].historical_baseline_ref == "enterprise"


@pytest.mark.parametrize(
    "field",
    [
        "command",
        "credentials",
        "endpoint",
        "url",
        "headers",
        "body",
        "query",
        "environment",
        "provider_options",
        "scheduler",
        "worker",
        "broker",
        "store",
        "receipt",
    ],
)
def test_executable_provider_and_runtime_authority_fields_are_unrepresentable(field: str) -> None:
    payload = valid_live_activity_payload()
    _profile(payload)["execution_contexts"]["records-api"][field] = "forbidden"  # type: ignore[index]

    with pytest.raises(SDLParseError):
        _parse(payload)


def test_activity_actor_entity_must_be_disjoint_from_participant_agents() -> None:
    payload = valid_live_activity_payload()
    payload["agents"] = {"blue": {"entity": "operations"}}

    with pytest.raises(SDLValidationError, match="Activity actor.*participant"):
        _parse(payload)


def test_activity_actor_account_must_be_disjoint_from_participant_bindings() -> None:
    payload = valid_live_activity_payload()
    payload["entities"]["participant"] = {"name": "Participant", "role": "blue"}  # type: ignore[index]
    payload["agents"] = {
        "blue": {
            "entity": "participant",
            "starting_accounts": ["records-operator"],
        }
    }

    with pytest.raises(SDLValidationError, match="account.*participant"):
        _parse(payload)


def test_activity_actor_disjointness_uses_canonical_participant_references() -> None:
    payload = valid_live_activity_payload()
    payload["agents"] = {
        "blue": {
            "entity": "entities.operations",
            "starting_accounts": ["accounts.records-operator"],
        }
    }

    with pytest.raises(SDLValidationError, match="Activity actor.*participant|account.*participant"):
        _parse(payload)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("actors", "records-clerk", "deployment_tenant_ref"), "other", "tenant"),
        (("actors", "records-clerk", "account_ref"), "missing", "account"),
        (("execution_contexts", "records-api", "target_service_ref"), "archive", "service"),
        (("historical_baseline_ref",), "missing", "historical baseline"),
    ],
)
def test_activity_bindings_fail_closed_on_wrong_authority(
    path: tuple[str, ...],
    value: str,
    message: str,
) -> None:
    payload = valid_live_activity_payload()
    target = _profile(payload)
    for segment in path[:-1]:
        target = target[segment]  # type: ignore[assignment,index]
    target[path[-1]] = value

    with pytest.raises(SDLValidationError, match=message):
        _parse(payload)


def test_context_may_target_any_native_materialization_binding_in_the_baseline() -> None:
    payload = valid_live_activity_payload()
    _bind_case_service(payload)
    _profile(payload)["execution_contexts"]["records-api"]["target_service_ref"] = (  # type: ignore[index]
        "nodes.archive.services.cases"
    )
    _profile(payload)["actors"]["records-clerk"]["operating_scope_refs"] = [  # type: ignore[index]
        "nodes.archive.services.cases"
    ]

    scenario = _parse(payload)

    assert (
        scenario.activity_profiles["ordinary-records"].execution_contexts["records-api"].target_service_ref
        == "nodes.archive.services.cases"
    )


def test_context_rejects_a_service_without_a_native_materialization_binding() -> None:
    payload = valid_live_activity_payload()
    payload["nodes"]["archive"]["services"].append({"name": "unbound", "port": 9443})  # type: ignore[index]
    _profile(payload)["execution_contexts"]["records-api"]["target_service_ref"] = (  # type: ignore[index]
        "nodes.archive.services.unbound"
    )
    _profile(payload)["actors"]["records-clerk"]["operating_scope_refs"] = [  # type: ignore[index]
        "nodes.archive.services.unbound"
    ]

    with pytest.raises(SDLValidationError) as exc_info:
        _parse(payload)

    assert "[live-activity.context-materialization-target-mismatch]" in str(exc_info.value)


def test_action_context_must_use_actor_account_and_operating_scope() -> None:
    payload = valid_live_activity_payload()
    payload["accounts"]["secondary"] = {  # type: ignore[index]
        "username": "secondary",
        "node": "archive",
    }
    _profile(payload)["execution_contexts"]["records-api"]["account_ref"] = "secondary"  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="actor account"):
        _parse(payload)

    payload = valid_live_activity_payload()
    _profile(payload)["actors"]["records-clerk"]["operating_scope_refs"] = ["message-metadata"]  # type: ignore[index]
    with pytest.raises(SDLValidationError, match="operating scope"):
        _parse(payload)


def test_parameter_binding_requires_an_existing_reference_of_the_declared_kind() -> None:
    payload = valid_live_activity_payload()
    binding = _profile(payload)["actions"]["update-record"]["parameter_bindings"][0]  # type: ignore[index]
    binding["value_ref"] = "historical_baselines.enterprise.objects.missing"  # type: ignore[index]

    with pytest.raises(SDLValidationError, match="parameter.*does not resolve"):
        _parse(payload)


def test_compiler_reuses_exact_historical_baseline_digest_and_emits_no_jobs() -> None:
    model = compile_runtime_model(_parse(valid_live_activity_payload()))
    compiled = model.activity_profiles["ordinary-records"]

    assert compiled.baseline_digest is model.historical_baseline_digests["enterprise"]
    assert compiled.baseline_digest.value == model.historical_baseline_digests["enterprise"].value
    assert compiled.budget_envelopes[0].range_capacity.numerator == 10
    assert compiled.budget_envelopes[0].participant_reservation.numerator == 4
    assert not hasattr(model, "scheduler_jobs")
    assert not hasattr(compiled, "occurrences")


def test_compiler_preserves_action_dependency_kinds_and_orders() -> None:
    payload = valid_live_activity_payload()
    profile = _with_second_action(payload)
    profile["dependencies"] = [
        {
            "action_ref": "update-second",
            "depends_on_ref": "update-record",
            "kind": "ordering",
        },
        {
            "action_ref": "update-second",
            "depends_on_ref": "update-record",
            "kind": "refresh",
        },
    ]

    compiled = compile_runtime_model(_parse(payload)).activity_profiles["ordinary-records"]

    assert compiled.dependency_order == ["update-record", "update-second"]
    assert compiled.reverse_teardown_order == ["update-second", "update-record"]
    assert compiled.actions["update-second"].ordering_dependencies == ["update-record"]
    assert compiled.actions["update-second"].refresh_dependencies == ["update-record"]
    assert compiled.required_dependency_kinds == ["ordering", "refresh"]


def test_occurrence_identity_is_stable_and_mutates_for_every_identity_coordinate() -> None:
    model = compile_runtime_model(_parse(valid_live_activity_payload()))
    compiled = model.activity_profiles["ordinary-records"]
    context = activity_occurrence_context(
        compiled,
        action_id="update-record",
        logical_time_seconds=15,
        occurrence_ordinal=1,
    )
    first = derive_activity_occurrence_identities([context])[0]
    second = derive_activity_occurrence_identities([context])[0]

    assert first == second
    assert first.value.startswith("lao1:")
    for field, replacement in (
        ("deployment_tenant_id", "range-b"),
        ("range_instance_id", "range-instance-002"),
        ("reset_generation_id", "generation-002"),
        ("activity_profile_id", "other-profile"),
        ("logical_time_seconds", 30),
        ("occurrence_ordinal", 2),
        ("action_id", "activity_profiles.ordinary-records.actions.other"),
        ("target_service_id", "nodes.archive.services.other"),
        ("schedule_profile", "finite-logical-schedule/v2"),
        ("transform_profile", "bounded-integer/v2"),
        ("address_profile", "activity-random-address/v2"),
    ):
        changed = context.model_copy(update={field: replacement})
        assert derive_activity_occurrence_identities([changed])[0].value != first.value


def test_occurrence_batch_rejects_duplicate_coordinates_atomically() -> None:
    compiled = compile_runtime_model(_parse(valid_live_activity_payload())).activity_profiles["ordinary-records"]
    context = activity_occurrence_context(
        compiled,
        action_id="update-record",
        logical_time_seconds=15,
        occurrence_ordinal=1,
    )
    with pytest.raises(ValueError, match="duplicate"):
        derive_activity_occurrence_identities([context, context])


def test_schedule_dependency_retry_and_budget_fail_closed() -> None:
    payload = valid_live_activity_payload()
    action = _profile(payload)["actions"]["update-record"]  # type: ignore[index]
    action["retry"]["max_attempts"] = 0  # type: ignore[index]
    with pytest.raises(SDLParseError):
        _parse(payload)

    payload = valid_live_activity_payload()
    _profile(payload)["schedules"]["steady"]["max_occurrences"] = 0  # type: ignore[index]
    with pytest.raises(SDLParseError):
        _parse(payload)

    payload = valid_live_activity_payload()
    budget = _profile(payload)["budgets"][0]  # type: ignore[index]
    budget["participant_reservation"] = {"numerator": 11, "denominator": 1}
    with pytest.raises(SDLValidationError, match="participant reservation"):
        _parse(payload)

    payload = valid_live_activity_payload()
    profile = _profile(payload)
    profile["actions"]["update-second"] = deepcopy(profile["actions"]["update-record"])  # type: ignore[index]
    profile["readback"]["action_refs"].append("update-second")  # type: ignore[index]
    budget = profile["budgets"][0]  # type: ignore[index]
    budget["action_demands"] = {  # type: ignore[index]
        "update-record": {"numerator": 4, "denominator": 1},
        "update-second": {"numerator": 4, "denominator": 1},
    }
    with pytest.raises(SDLValidationError, match="aggregate action demand"):
        _parse(payload)

    payload = valid_live_activity_payload()
    _profile(payload)["budgets"][0]["range_capacity"] = {  # type: ignore[index]
        "numerator": 2,
        "denominator": 2,
    }
    with pytest.raises(SDLParseError, match="lowest terms"):
        _parse(payload)

    payload = valid_live_activity_payload()
    _profile(payload)["dependencies"] = [
        {
            "action_ref": "update-record",
            "depends_on_ref": "update-record",
            "kind": "ordering",
        }
    ]
    with pytest.raises(SDLValidationError, match="cycle|itself"):
        _parse(payload)

    payload = valid_live_activity_payload()
    profile = _profile(payload)
    profile["actions"]["update-second"] = deepcopy(profile["actions"]["update-record"])  # type: ignore[index]
    profile["readback"]["action_refs"].append("update-second")  # type: ignore[index]
    profile["budgets"][0]["action_demands"]["update-second"] = {  # type: ignore[index]
        "numerator": 1,
        "denominator": 1,
    }
    profile["dependencies"] = [
        {
            "action_ref": "update-record",
            "depends_on_ref": "update-second",
            "kind": "ordering",
        },
        {
            "action_ref": "update-second",
            "depends_on_ref": "update-record",
            "kind": "refresh",
        },
    ]
    with pytest.raises(SDLValidationError, match="dependency cycle"):
        _parse(payload)


@pytest.mark.parametrize(
    ("case", "code"),
    [
        ("dependency-duplicate", "live-activity.dependency-duplicate"),
        ("dependency-unresolved", "live-activity.dependency-unresolved"),
        ("dependency-self", "live-activity.dependency-self"),
        ("dependency-cycle", "live-activity.dependency-cycle"),
        ("budget-duplicate", "live-activity.budget-duplicate"),
        ("budget-unit-mismatch", "live-activity.budget-unit-mismatch"),
        ("budget-action-coverage", "live-activity.budget-action-coverage"),
        ("participant-reservation", "live-activity.participant-reservation-exceeded"),
        ("range-capacity", "live-activity.range-capacity-exceeded"),
        ("action-demand", "live-activity.action-demand-exceeded"),
        ("aggregate-demand", "live-activity.aggregate-demand-exceeded"),
        ("readback-observability", "live-activity.readback-observability-unresolved"),
        ("readback-evidence", "live-activity.readback-evidence-unresolved"),
        ("telemetry-observability", "live-activity.telemetry-observability-unresolved"),
        ("telemetry-evidence", "live-activity.telemetry-evidence-unresolved"),
    ],
)
def test_live_activity_policy_diagnostic_codes(case: str, code: str) -> None:
    payload = valid_live_activity_payload()
    profile = _profile(payload)
    budget = profile["budgets"][0]  # type: ignore[index]

    if case == "dependency-duplicate":
        _with_second_action(payload)
        dependency = {
            "action_ref": "update-second",
            "depends_on_ref": "update-record",
            "kind": "ordering",
        }
        profile["dependencies"] = [dependency, deepcopy(dependency)]
    elif case == "dependency-unresolved":
        profile["dependencies"] = [
            {
                "action_ref": "update-record",
                "depends_on_ref": "missing",
                "kind": "ordering",
            }
        ]
    elif case == "dependency-self":
        profile["dependencies"] = [
            {
                "action_ref": "update-record",
                "depends_on_ref": "update-record",
                "kind": "ordering",
            }
        ]
    elif case == "dependency-cycle":
        _with_second_action(payload)
        profile["dependencies"] = [
            {
                "action_ref": "update-record",
                "depends_on_ref": "update-second",
                "kind": "ordering",
            },
            {
                "action_ref": "update-second",
                "depends_on_ref": "update-record",
                "kind": "refresh",
            },
        ]
    elif case == "budget-duplicate":
        profile["budgets"].append(deepcopy(budget))  # type: ignore[union-attr]
    elif case == "budget-unit-mismatch":
        budget["unit"] = "byte"  # type: ignore[index]
    elif case == "budget-action-coverage":
        _with_second_action(payload)
        del budget["action_demands"]["update-second"]  # type: ignore[index]
    elif case == "participant-reservation":
        budget["participant_reservation"] = {"numerator": 11, "denominator": 1}  # type: ignore[index]
    elif case == "range-capacity":
        budget["range_capacity"] = {"numerator": 101, "denominator": 1}  # type: ignore[index]
    elif case == "action-demand":
        budget["action_demands"]["update-record"] = {"numerator": 7, "denominator": 1}  # type: ignore[index]
    elif case == "aggregate-demand":
        _with_second_action(payload)
        budget["action_demands"] = {  # type: ignore[index]
            "update-record": {"numerator": 4, "denominator": 1},
            "update-second": {"numerator": 4, "denominator": 1},
        }
    elif case.endswith("-observability"):
        policy = case.removesuffix("-observability")
        profile[policy]["observability_refs"] = ["nodes.archive.services.records"]  # type: ignore[index]
    else:
        policy = case.removesuffix("-evidence")
        profile[policy]["evidence_requirement_refs"] = ["missing"]  # type: ignore[index]

    _assert_validation_code(payload, code)


def test_occurrence_builder_enforces_schedule_time_and_finite_bound() -> None:
    compiled = compile_runtime_model(_parse(valid_live_activity_payload())).activity_profiles["ordinary-records"]

    with pytest.raises(ValueError, match="logical time"):
        activity_occurrence_context(
            compiled,
            action_id="update-record",
            logical_time_seconds=16,
            occurrence_ordinal=1,
        )
    with pytest.raises(ValueError, match="finite schedule"):
        activity_occurrence_context(
            compiled,
            action_id="update-record",
            logical_time_seconds=60,
            occurrence_ordinal=4,
        )


def _with_live_capability(
    manifest: BackendManifest,
    capability: LiveActivityCapabilities | None,
    *,
    include_live_contracts: bool = True,
) -> BackendManifest:
    supported_contract_versions = manifest.supported_contract_versions
    if include_live_contracts:
        supported_contract_versions |= frozenset({"live-activity-profile-v1", "live-activity-occurrence-v1"})
    else:
        supported_contract_versions -= frozenset({"live-activity-profile-v1", "live-activity-occurrence-v1"})
    return BackendManifest(
        identity=manifest.identity,
        supported_contract_versions=supported_contract_versions,
        compatibility=manifest.compatibility,
        realization_support=manifest.realization_support,
        concept_bindings=manifest.concept_bindings,
        constraints=manifest.constraints,
        provisioner=manifest.provisioner,
        orchestrator=manifest.orchestrator,
        evaluator=manifest.evaluator,
        participant_runtime=manifest.participant_runtime,
        observation=manifest.observation,
        historical_state=manifest.historical_state,
        live_activity=capability,
        realization_envelope=manifest.realization_envelope,
    )


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


def test_planner_rejects_absent_and_partial_capability_then_accepts_exact_support() -> None:
    model = compile_runtime_model(_parse(valid_live_activity_payload()))
    base = create_stub_manifest()

    absent = plan(model, base)
    assert any(diag.code == "live-activity.capability-missing" for diag in absent.diagnostics)

    partial_capability = deepcopy(_exact_capability())
    partial = _with_live_capability(
        base,
        LiveActivityCapabilities(
            supported_contract_profiles=partial_capability.supported_contract_profiles,
            supported_operation_profiles=frozenset(),
            supported_schedule_profiles=partial_capability.supported_schedule_profiles,
            supported_readback_profiles=partial_capability.supported_readback_profiles,
            supported_lifecycle_profiles=partial_capability.supported_lifecycle_profiles,
            supported_resource_dimensions=partial_capability.supported_resource_dimensions,
            supported_dependency_kinds=partial_capability.supported_dependency_kinds,
            supports_bounded_retry=True,
            supports_generation_lifecycle=True,
            supports_participant_reservation=True,
            supports_readback_provenance=True,
        ),
    )
    assert any(diag.code == "live-activity.operation-unsupported" for diag in plan(model, partial).diagnostics)

    exact = plan(model, _with_live_capability(base, _exact_capability()))
    assert not any(diag.code.startswith("live-activity.") for diag in exact.diagnostics)


def test_planner_requires_published_live_activity_contracts() -> None:
    model = compile_runtime_model(_parse(valid_live_activity_payload()))
    manifest = _with_live_capability(
        create_stub_manifest(),
        _exact_capability(),
        include_live_contracts=False,
    )

    assert "live-activity.contract-unsupported" in {diagnostic.code for diagnostic in plan(model, manifest).diagnostics}


@pytest.mark.parametrize(
    ("field", "unsupported_value", "code", "requires_dependency"),
    [
        ("supported_contract_profiles", frozenset(), "live-activity.profile-unsupported", False),
        ("supported_operation_profiles", frozenset(), "live-activity.operation-unsupported", False),
        ("supported_schedule_profiles", frozenset(), "live-activity.schedule-unsupported", False),
        ("supported_readback_profiles", frozenset(), "live-activity.readback-unsupported", False),
        ("supported_lifecycle_profiles", frozenset(), "live-activity.lifecycle-unsupported", False),
        ("supported_resource_dimensions", frozenset(), "live-activity.resource-dimension-unsupported", False),
        ("supported_dependency_kinds", frozenset(), "live-activity.dependency-kind-unsupported", True),
        ("supports_bounded_retry", False, "live-activity.bounded-retry-unsupported", False),
        ("supports_generation_lifecycle", False, "live-activity.generation-lifecycle-unsupported", False),
        ("supports_participant_reservation", False, "live-activity.participant-reservation-unsupported", False),
        ("supports_readback_provenance", False, "live-activity.readback-provenance-unsupported", False),
    ],
)
def test_planner_live_activity_capability_diagnostic_codes(
    field: str,
    unsupported_value: object,
    code: str,
    requires_dependency: bool,
) -> None:
    payload = valid_live_activity_payload()
    if requires_dependency:
        profile = _with_second_action(payload)
        profile["dependencies"] = [
            {
                "action_ref": "update-second",
                "depends_on_ref": "update-record",
                "kind": "ordering",
            }
        ]
    model = compile_runtime_model(_parse(payload))
    capability = replace(_exact_capability(), **{field: unsupported_value})
    manifest = _with_live_capability(create_stub_manifest(), capability)

    assert code in {diagnostic.code for diagnostic in plan(model, manifest).diagnostics}


def test_planner_rejects_selected_profile_aggregate_above_fleet_capacity() -> None:
    payload = valid_live_activity_payload()
    first = _profile(payload)
    first["budgets"][0]["range_capacity"] = {"numerator": 60, "denominator": 1}  # type: ignore[index]
    payload["activity_profiles"]["other-records"] = deepcopy(first)  # type: ignore[index]
    model = compile_runtime_model(_parse(payload))
    manifest = _with_live_capability(create_stub_manifest(), _exact_capability())

    assert any(
        diagnostic.code == "live-activity.fleet-capacity-exceeded" for diagnostic in plan(model, manifest).diagnostics
    )


def test_planner_rejects_conflicting_fleet_budget_envelopes() -> None:
    payload = valid_live_activity_payload()
    second = deepcopy(_profile(payload))
    second["budgets"][0]["fleet_capacity"] = {"numerator": 101, "denominator": 1}  # type: ignore[index]
    payload["activity_profiles"]["other-records"] = second  # type: ignore[index]
    model = compile_runtime_model(_parse(payload))
    manifest = _with_live_capability(create_stub_manifest(), _exact_capability())

    assert "live-activity.fleet-envelope-conflict" in {
        diagnostic.code for diagnostic in plan(model, manifest).diagnostics
    }


def test_live_activity_lowers_exact_sem_218_requirements_to_target_service() -> None:
    model = compile_runtime_model(_parse(valid_live_activity_payload()))
    requirements = [
        item
        for item in model.realization_requirements
        if item.field_path.startswith("activity_profiles.ordinary-records")
    ]

    assert requirements
    assert {item.address for item in requirements} == {"provision.node.archive.service.records"}
    assert all(item.explicitness.value == "exact" for item in requirements)
    assert {item.requirement_kind.split(":", 1)[0] for item in requirements} >= {
        "live-activity-operation",
        "live-activity-schedule",
        "live-activity-readback",
        "live-activity-lifecycle",
        "live-activity-resource-dimension",
    }


def test_stale_generation_occurrence_is_rejected() -> None:
    compiled = compile_runtime_model(_parse(valid_live_activity_payload())).activity_profiles["ordinary-records"]
    context = activity_occurrence_context(
        compiled,
        action_id="update-record",
        logical_time_seconds=15,
        occurrence_ordinal=1,
    )

    validate_activity_occurrence_context(compiled, context)
    with pytest.raises(ValueError, match="stale reset generation"):
        validate_activity_occurrence_context(
            compiled,
            context.model_copy(update={"reset_generation_id": "generation-stale"}),
        )


def test_readback_and_telemetry_are_evidence_only() -> None:
    profile = _parse(valid_live_activity_payload()).activity_profiles["ordinary-records"]

    assert profile.readback.participant_proof is False
    assert profile.telemetry.participant_proof is False
    assert profile.telemetry.emits_participant_receipts is False
    assert profile.telemetry.establishes_objective_truth is False


@pytest.mark.parametrize(
    ("policy", "field"),
    [
        ("readback", "participant_proof"),
        ("telemetry", "participant_proof"),
        ("telemetry", "emits_participant_receipts"),
        ("telemetry", "establishes_objective_truth"),
    ],
)
def test_activity_evidence_policy_rejects_participant_authority(policy: str, field: str) -> None:
    payload = valid_live_activity_payload()
    _profile(payload)[policy][field] = True  # type: ignore[index]

    with pytest.raises(SDLParseError):
        _parse(payload)


def test_absent_activity_sections_preserve_existing_scenarios() -> None:
    payload = valid_live_activity_payload()
    del payload["activity_templates"]
    del payload["activity_profiles"]
    scenario = _parse(payload)
    model = compile_runtime_model(scenario)

    assert scenario.activity_templates == {}
    assert scenario.activity_profiles == {}
    assert model.activity_profiles == {}
