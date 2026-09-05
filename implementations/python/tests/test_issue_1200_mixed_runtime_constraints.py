"""Constraint preservation through compiled and portable realization authority."""

from copy import deepcopy
from dataclasses import replace

import pytest
from raes import parse_sdl
from raes.explicitness import ExplicitnessClass
from raes_contracts.apparatus import RealizationObservationCapability
from raes_contracts.contracts import ProvisioningPlanModel
from raes_contracts.plan_projection import provisioning_plan_model
from raes_contracts.realization_observation import RealizationObservationDisclosure
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot, SnapshotEntry
from raes_contracts.vocabulary import ObservationStrength, RealizationSupportMode, RealizationVerificationScope
from raes_processor.compiler import compile_runtime_model
from raes_processor.planner import plan
from raes_processor.semantics.realization_concerns import realization_concern_descriptors
from raes_processor.semantics.realization_runtime_evaluation import evaluate_registered_realization
from raes_runtime.backend_calls import _call_backend_apply, _RealizationApplyContext
from raes_runtime.control_plane_api_models import _provisioning_plan
from test_issue_1066_runtime_resource_limits import _supporting_manifest


def _fixture(runtime, *, open_packages=False, allow_invalid=False, scope=None, closed_scopes=()):
    import yaml

    source = {"name": "mixed-constraints", "nodes": {"host": {"type": "compute", "runtime": runtime}}}
    if open_packages or scope:
        source["realization"] = {
            "default": "closed",
            "scopes": [
                {"field_pointer": scope or "/nodes/host/runtime/packages", "posture": "open"},
                *({"field_pointer": pointer, "posture": "closed"} for pointer in closed_scopes),
            ],
        }
    model = compile_runtime_model(parse_sdl(yaml.safe_dump(source)))
    # Synthetic capability declarations admit the test scope; the callback
    # supplies the observed values. No live backend behavior is claimed.
    base = _supporting_manifest(mode=RealizationSupportMode.OPEN_REALIZATION)
    kinds = {descriptor.concern_kind for descriptor in realization_concern_descriptors()}
    manifest = replace(
        base,
        realization_support=tuple(
            replace(
                declaration,
                support_mode=RealizationSupportMode.OPEN_REALIZATION,
                supported_exact_requirement_kinds=declaration.supported_exact_requirement_kinds | kinds,
                supported_constraint_kinds=declaration.supported_constraint_kinds | kinds,
                observation_capabilities={
                    **declaration.observation_capabilities,
                    **{
                        kind: RealizationObservationCapability(
                            verification_scope=RealizationVerificationScope.CONFIGURATION,
                            observation_strength=ObservationStrength.GUEST_OBSERVED,
                        )
                        for kind in kinds
                    },
                },
            )
            for declaration in base.realization_support
        ),
    )
    execution = plan(model, manifest)
    if allow_invalid:
        return model, execution, manifest
    assert execution.is_valid, [(d.code, d.message) for d in execution.diagnostics]
    portable = _provisioning_plan(
        ProvisioningPlanModel.model_validate_json(provisioning_plan_model(execution.provisioning).model_dump_json())
    )
    return model, portable, manifest


def _returned(plan_value, runtime):
    entries = {}
    for op in plan_value.operations:
        payload = deepcopy(op.payload)
        payload["spec"]["node"]["runtime"] = runtime
        entries[op.address] = SnapshotEntry(
            address=op.address, domain="provisioning", resource_type=op.resource_type, payload=payload
        )
    return RuntimeSnapshot(
        entries=entries,
        realization_envelope=plan_value.realization_envelope,
        realization_observations=tuple(
            RealizationObservationDisclosure(
                address=authority.address,
                field_path=authority.field_path,
                domain=authority.domain,
                requirement_kind=authority.requirement_kind,
                verification_scope=authority.verification_scope,
                observation_strength=authority.required_observation_strength,
            )
            for authority in plan_value.realization_authority
            if authority.requirement_kind in {"runtime-database-services", "runtime-packages", "runtime-dns-services"}
            and authority.mode.value != "closed"
        ),
    )


def _apply(plan_value, manifest, runtime, *, observe=True):
    calls = []
    baseline = RuntimeSnapshot()

    def backend(submitted, snapshot):
        calls.append(submitted)
        returned = _returned(submitted, runtime)
        if not observe:
            returned = replace(returned, realization_observations=())
        return ApplyResult(success=True, snapshot=returned)

    result = _call_backend_apply(
        backend,
        plan_value,
        baseline,
        address="runtime.test.mixed-constraints",
        snapshot=baseline,
        realization=_RealizationApplyContext(plan=plan_value, manifest=manifest),
    )
    assert len(calls) == 1, result.diagnostics
    return result


@pytest.mark.parametrize("identity, accepted", [("db", True), ("different-db", False)])
def test_exact_database_identity_survives_open_engine_through_apply(identity, accepted):
    _, portable, manifest = _fixture({"database_services": [{"database_service_id": "db", "engine": "other"}]})
    result = _apply(portable, manifest, {"database_services": [{"database_service_id": identity, "engine": "sqlite"}]})
    assert result.success is accepted, result.diagnostics
    if not accepted:
        assert result.snapshot.entries == {}
        assert result.diagnostics[0].code == "runtime.backend-contract-invalid"


def test_direct_counterexample_retains_exact_negative_control():
    model, portable, manifest = _fixture({"database_services": [{"database_service_id": "db", "engine": "other"}]})
    requirement = next(r for r in model.realization_requirements if r.requirement_kind == "runtime-database-services")
    returned = _returned(portable, {"database_services": [{"database_service_id": "different-db", "engine": "other"}]})
    for candidate in (requirement, replace(requirement, explicitness=ExplicitnessClass.EXACT)):
        diagnostic, provenance = evaluate_registered_realization(candidate, portable, returned, manifest=manifest)
        assert diagnostic is not None
        assert diagnostic.code == "runtime.backend-contract-invalid"
        assert provenance is None


@pytest.mark.parametrize("version, accepted", [("7.95", True), ("7.94", False)])
@pytest.mark.parametrize("scope", ["/nodes/host/runtime/packages", "/nodes/host/runtime"])
def test_inherited_open_packages_preserve_exact_nmap(version, accepted, scope):
    nmap = {"manager": "apt", "name": "nmap", "version": "7.95"}
    _, portable, manifest = _fixture({"packages": [nmap]}, scope=scope)
    result = _apply(
        portable,
        manifest,
        {"packages": [{"manager": "apt", "name": "curl", "version": "8.0"}, {**nmap, "version": version}]},
    )
    assert result.success is accepted, result.diagnostics
    if not accepted:
        assert result.snapshot.entries == {}


@pytest.mark.parametrize("engine", ["unknown", "other"])
def test_unresolved_database_observation_cannot_claim_satisfaction(engine):
    _, portable, manifest = _fixture({"database_services": [{"database_service_id": "db", "engine": "other"}]})
    result = _apply(portable, manifest, {"database_services": [{"database_service_id": "db", "engine": engine}]})
    assert result.success is False
    assert result.snapshot.realization_provenance == ()


@pytest.mark.parametrize(
    "packages, accepted",
    [
        ([], False),
        ([{"manager": "apt", "name": "renamed", "version": "7.95"}], False),
        ([{"manager": "apt", "name": "nmap", "version": "7.95"}] * 2, False),
        ([{"manager": "apt", "name": "nmap", "version": "7.95", "source": "backend-choice"}], True),
        ([{"manager": "apt", "name": "nmap", "version": "7.95", "architecture": "amd64"}], True),
    ],
)
def test_open_package_membership_is_keyed_and_preserves_required_member(packages, accepted):
    _, portable, manifest = _fixture(
        {"packages": [{"manager": "apt", "name": "nmap", "version": "7.95"}]}, open_packages=True
    )
    assert _apply(portable, manifest, {"packages": packages}).success is accepted


def test_dns_numeric_extension_is_exact_without_reclassifying_literal_strings():
    from raes.explicitness import classify_model_explicitness
    from raes.runtime_dns_records import DnsResourceRecordSet
    from raes.runtime_packages import RuntimePackage

    rrset = DnsResourceRecordSet.model_validate(
        {
            "rrset_id": "custom",
            "owner": "example.test.",
            "record_type": "other",
            "type_code": 65280,
            "records": [{"rdata": "opaque"}],
        }
    )
    records = classify_model_explicitness(rrset).records
    assert records["record_type"].classification is ExplicitnessClass.EXACT
    assert records["type_code"].classification is ExplicitnessClass.EXACT
    literal = RuntimePackage(manager="other", name="unknown", version="other")
    assert all(
        r.classification is ExplicitnessClass.EXACT for r in classify_model_explicitness(literal).records.values()
    )


def test_unrepresentable_mixed_collection_rejects_with_actionable_admission_diagnostic():
    _, execution, _ = _fixture(
        {"forwarding_agents": [{"forwarding_agent_id": "agent", "agent_kind": "other", "implementation": "other"}]},
        allow_invalid=True,
    )
    assert not execution.is_valid
    assert any(
        d.code == "realization.authority-bound-unavailable" and "forwarding-agents" in d.message
        for d in execution.diagnostics
    )


@pytest.mark.parametrize("corruption", ["members", "baseline"])
def test_malformed_structural_demand_is_rejected_before_backend_mutation(corruption):
    from raes_processor.planner import realization_authority_diagnostics

    _, portable, manifest = _fixture(
        {"packages": [{"manager": "apt", "name": "nmap", "version": "7.95"}]}, open_packages=True
    )
    authority = next(a for a in portable.realization_authority if a.requirement_kind == "runtime-packages")
    if corruption == "members":
        malformed = replace(authority, structure=authority.structure.model_copy(update={"members": {}}))
        altered = replace(
            portable,
            realization_authority=tuple(malformed if a is authority else a for a in portable.realization_authority),
        )
    else:
        payload = deepcopy(portable.operations[0].payload)
        del payload["spec"]["node"]["runtime"]["packages"]
        altered = replace(portable, operations=[replace(portable.operations[0], payload=payload)])
    assert realization_authority_diagnostics(altered, manifest)


def test_nested_scope_delegates_only_the_omitted_package_field():
    package = {"manager": "apt", "name": "nmap", "version": "7.95"}
    _, portable, manifest = _fixture({"packages": [package]}, scope="/nodes/host/runtime/packages/0/source")
    assert _apply(portable, manifest, {"packages": [{**package, "source": "backend-choice"}]}).success
    assert not _apply(
        portable, manifest, {"packages": [{**package, "source": "backend-choice", "version": "7.94"}]}
    ).success


@pytest.mark.parametrize("closed", [False, True])
@pytest.mark.parametrize("field, choice", [("source", "backend-choice"), ("architecture", "amd64")])
def test_closed_child_scope_survives_open_parent_and_portable_apply(closed, field, choice):
    package = {"manager": "apt", "name": "nmap", "version": "7.95"}
    _, portable, manifest = _fixture(
        {"packages": [package]},
        open_packages=True,
        closed_scopes=(f"/nodes/host/runtime/packages/0/{field}",) if closed else (),
    )
    assert _apply(portable, manifest, {"packages": [package]}).success
    result = _apply(portable, manifest, {"packages": [{**package, field: choice}]})
    assert result.success is not closed, result.diagnostics
    if closed:
        assert result.snapshot.entries == {}
        assert result.snapshot.realization_provenance == ()


@pytest.mark.parametrize("code, accepted", [(65280, True), (65281, False)])
def test_dns_numeric_extension_preserved_through_admitted_result(code, accepted):
    dns = {
        "dns_service_id": "dns",
        "zones": [
            {
                "zone_id": "zone",
                "name": "example.test.",
                "rrsets": [
                    {
                        "rrset_id": "custom",
                        "owner": "example.test.",
                        "record_type": "other",
                        "type_code": 65280,
                        "records": [{"rdata": "opaque"}],
                    }
                ],
            }
        ],
    }
    _, portable, manifest = _fixture({"dns_services": [dns]})
    actual = deepcopy(dns)
    actual["zones"][0]["rrsets"][0]["type_code"] = code
    assert _apply(portable, manifest, {"dns_services": [actual]}).success is accepted


def test_legacy_closed_package_collection_rejects_excess_members():
    package = {"manager": "apt", "name": "nmap", "version": "7.95"}
    _, portable, manifest = _fixture({"packages": [package]})
    assert _apply(portable, manifest, {"packages": [package]}).success
    assert not _apply(portable, manifest, {"packages": [package, {**package, "name": "curl"}]}).success


def test_open_support_does_not_replace_exact_child_capability_admission():
    from raes_processor.planner import realization_authority_diagnostics

    model, portable, manifest = _fixture({"database_services": [{"database_service_id": "db", "engine": "other"}]})
    open_only = replace(
        manifest,
        realization_support=tuple(
            replace(
                d, supported_exact_requirement_kinds=d.supported_exact_requirement_kinds - {"runtime-database-services"}
            )
            for d in manifest.realization_support
        ),
    )
    execution = plan(model, open_only)
    assert not execution.is_valid
    assert any(d.code == "realization.unsupported-exact-requirement" for d in execution.diagnostics)
    assert realization_authority_diagnostics(portable, open_only)


def test_published_plan_schema_and_closed_reader_preserve_structural_authority():
    import json
    from pathlib import Path

    from jsonschema import Draft202012Validator
    from pydantic import ValidationError

    _, portable, _ = _fixture({"packages": [{"manager": "apt", "name": "nmap", "version": "7.95"}]}, open_packages=True)
    payload = provisioning_plan_model(portable).model_dump(mode="json")
    schema = json.loads((Path(__file__).parents[3] / "contracts/schemas/plans/provisioning-plan-v1.json").read_text())
    Draft202012Validator(schema).validate(payload)
    authority = next(a for a in payload["realization_authority"] if a["requirement_kind"] == "runtime-packages")
    assert "nmap" not in json.dumps(authority["structure"])
    assert "7.95" not in json.dumps(authority["structure"])
    legacy = deepcopy(schema)
    del legacy["$defs"]["ResolvedRealizationAuthorityModel"]["properties"]["structure"]
    assert list(Draft202012Validator(legacy).iter_errors(payload))
    authority["structure"]["unrecognized_permission"] = True
    assert list(Draft202012Validator(schema).iter_errors(payload))
    with pytest.raises(ValidationError):
        ProvisioningPlanModel.model_validate(payload)
    authority["structure"] = {"taxonomy_sentinel": True}
    assert list(Draft202012Validator(schema).iter_errors(payload))
    with pytest.raises(ValidationError):
        ProvisioningPlanModel.model_validate(payload)


@pytest.mark.parametrize(
    "identities, accepted",
    [
        (["first", "second"], True),
        (["second"], False),
        (["first", "second", "extra"], False),
        (["first", "first"], False),
    ],
)
def test_mixed_database_collection_preserves_membership_across_reordering(identities, accepted):
    _, portable, manifest = _fixture(
        {
            "database_services": [
                {"database_service_id": "second", "engine": "other"},
                {"database_service_id": "first", "engine": "other"},
            ]
        }
    )
    assert (
        _apply(
            portable,
            manifest,
            {"database_services": [{"database_service_id": identity, "engine": "sqlite"} for identity in identities]},
        ).success
        is accepted
    )


@pytest.mark.parametrize("missing", ["value", "observation"])
def test_missing_value_or_observation_does_not_establish_satisfaction(missing):
    _, portable, manifest = _fixture({"database_services": [{"database_service_id": "db", "engine": "other"}]})
    runtime = {} if missing == "value" else {"database_services": [{"database_service_id": "db", "engine": "sqlite"}]}
    result = _apply(portable, manifest, runtime, observe=missing != "observation")
    assert not result.success
    assert not result.snapshot.realization_provenance
