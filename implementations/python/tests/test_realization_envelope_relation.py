"""Tests for the realization-envelope relation (issue #668).

Covers the envelope contract's construction invariants and the four relation
kinds — membership, subsumption, witness generation, and negative probes — against
``specs/formal/realization/envelope-semantics.md`` R1-R8 and ADR-070 §2/§3. Property
tests prove decidability/determinism, that subsumption is set inclusion on the
admitted fragment, that witnesses are in-envelope, and that negative probes are
out-of-envelope.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aces_contracts.realization_envelope import (
    BooleanDomain,
    Closure,
    ClosureOverlay,
    EnumDomain,
    EnvelopeBinding,
    EnvelopeScope,
    ExactDomain,
    GovernedReferenceDomain,
    NumericIntervalDomain,
    NumericType,
    Posture,
    RealizationEnvelopeModel,
    RecordDomain,
    WitnessPolicy,
)
from aces_sdl import (
    SDLInstantiationError,
    SDLValidationError,
    instantiate_scenario,
    parse_sdl,
)
from aces_sdl._realization_envelope_domains import _MISSING, default_witness_value, out_of_domain_value
from aces_sdl.realization_envelope import generate_negative_probes, member, subsumes, witness
from aces_sdl.scenario import InstantiatedScenario, Scenario
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

_DATA = Path(__file__).parent / "data" / "realization_envelope"


# --------------------------------------------------------------------------- #
# Builders                                                                     #
# --------------------------------------------------------------------------- #


def _web_envelope(
    *,
    os_values: tuple[str, ...] = ("linux", "windows"),
    closed: bool = False,
    name: str = "web-family",
    selection: str | None = None,
) -> RealizationEnvelopeModel:
    return RealizationEnvelopeModel(
        id="web-family",
        scope=EnvelopeScope.SCENARIO,
        domains={
            "scenario_name": ExactDomain(value=name),
            "node_type": ExactDomain(value="vm"),
            "os": EnumDomain(values=list(os_values)),
        },
        bindings=[
            EnvelopeBinding(path="name", scope=EnvelopeScope.SCENARIO, posture=Posture.EXACT, domain="scenario_name"),
            EnvelopeBinding(path="nodes.web.type", scope=EnvelopeScope.NODE, posture=Posture.EXACT, domain="node_type"),
            EnvelopeBinding(path="nodes.web.os", scope=EnvelopeScope.FIELD, posture=Posture.CONSTRAINED, domain="os"),
        ],
        closure=(
            [ClosureOverlay(path="", scope=EnvelopeScope.SCENARIO, closure=Closure.CLOSED_WORLD)] if closed else []
        ),
        witness_policy=(WitnessPolicy(selections={"os": selection}) if selection is not None else None),
    )


def _instantiate(yaml_text: str) -> InstantiatedScenario:
    return instantiate_scenario(parse_sdl(yaml_text))


def _leaf_enum_env(values: set[str], envelope_id: str = "leaf") -> RealizationEnvelopeModel:
    """Single-leaf envelope over an arbitrary enum universe (no SDL binding)."""

    return RealizationEnvelopeModel(
        id=envelope_id,
        scope=EnvelopeScope.FIELD,
        domains={"leaf": EnumDomain(values=sorted(values))},
        bindings=[EnvelopeBinding(path="x", scope=EnvelopeScope.FIELD, posture=Posture.CONSTRAINED, domain="leaf")],
    )


def _leaf_int_interval_env(lower: int, upper: int, envelope_id: str = "leaf") -> RealizationEnvelopeModel:
    return RealizationEnvelopeModel(
        id=envelope_id,
        scope=EnvelopeScope.FIELD,
        domains={"leaf": NumericIntervalDomain(numeric_type=NumericType.INTEGER, lower=lower, upper=upper)},
        bindings=[EnvelopeBinding(path="x", scope=EnvelopeScope.FIELD, posture=Posture.CONSTRAINED, domain="leaf")],
    )


# --------------------------------------------------------------------------- #
# Contract fixtures                                                            #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("path", sorted((_DATA / "valid").glob("*.json")), ids=lambda p: p.stem)
def test_valid_fixtures_parse(path: Path) -> None:
    model = RealizationEnvelopeModel.model_validate(json.loads(path.read_text(encoding="utf-8")))
    assert model.schema_version == "realization-envelope/v1"
    # round-trips through JSON without loss
    reparsed = RealizationEnvelopeModel.model_validate(json.loads(model.model_dump_json()))
    assert reparsed == model


@pytest.mark.parametrize("path", sorted((_DATA / "invalid").glob("*.json")), ids=lambda p: p.stem)
def test_invalid_fixtures_rejected(path: Path) -> None:
    with pytest.raises(ValidationError):
        RealizationEnvelopeModel.model_validate(json.loads(path.read_text(encoding="utf-8")))


def test_contract_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        RealizationEnvelopeModel.model_validate({"id": "x", "scope": "scenario", "unexpected": True})


def test_contract_rejects_arbitrary_predicate_domain() -> None:
    # The closed discriminated union is the portability guarantee: no predicate
    # domain kind exists, so one cannot be expressed (envelope-semantics.md R3).
    with pytest.raises(ValidationError):
        RealizationEnvelopeModel.model_validate(
            {
                "id": "x",
                "scope": "field",
                "domains": {"p": {"kind": "predicate", "expr": "lambda v: True"}},
                "bindings": [],
            }
        )


# --------------------------------------------------------------------------- #
# Membership (R1, R3)                                                          #
# --------------------------------------------------------------------------- #


def test_member_accepts_in_envelope_instance() -> None:
    env = _web_envelope()
    inst = _instantiate("name: web-family\nnodes:\n  web:\n    type: vm\n    os: linux\n")
    assert member(inst, env).holds


def test_member_rejects_out_of_domain_value() -> None:
    env = _web_envelope(os_values=("linux",))
    inst = _instantiate("name: web-family\nnodes:\n  web:\n    type: vm\n    os: windows\n")
    result = member(inst, env)
    assert not result.holds
    assert any(d.code == "realization-envelope.membership.domain-mismatch" for d in result.diagnostics)
    assert all(d.address == "nodes.web.os" for d in result.diagnostics)


def test_member_rejects_wrong_exact_name() -> None:
    env = _web_envelope()
    inst = _instantiate("name: other\nnodes:\n  web:\n    type: vm\n    os: linux\n")
    assert not member(inst, env).holds


def test_member_reports_absent_constrained_path() -> None:
    env = _web_envelope()
    inst = _instantiate("name: web-family\nnodes:\n  web:\n    type: vm\n")
    result = member(inst, env)
    assert not result.holds
    assert any(d.code == "realization-envelope.membership.path-absent" for d in result.diagnostics)


def test_member_closed_world_rejects_unspecified_dimension() -> None:
    env = _web_envelope(closed=True)
    ok = _instantiate("name: web-family\nnodes:\n  web:\n    type: vm\n    os: linux\n")
    assert member(ok, env).holds
    extra = _instantiate('name: web-family\nversion: "2.0"\nnodes:\n  web:\n    type: vm\n    os: linux\n')
    result = member(extra, env)
    assert not result.holds
    assert any(d.code == "realization-envelope.membership.closed-world-extra" for d in result.diagnostics)


def test_member_diagnostics_are_secret_free() -> None:
    env = _web_envelope(os_values=("linux",))
    inst = _instantiate("name: web-family\nnodes:\n  web:\n    type: vm\n    os: windows\n")
    for diagnostic in member(inst, env).diagnostics:
        # Diagnostics name paths, ids, and domain kinds — never raw values (R8).
        assert "windows" not in diagnostic.message
        assert diagnostic.domain == "realization-envelope"


def test_member_governed_reference_and_numeric_interval() -> None:
    env = RealizationEnvelopeModel(
        id="host",
        scope=EnvelopeScope.NODE,
        domains={
            "name": ExactDomain(value="s"),
            "vm": ExactDomain(value="vm"),
            "cpu": NumericIntervalDomain(numeric_type=NumericType.INTEGER, lower=1, upper=4),
        },
        bindings=[
            EnvelopeBinding(path="name", scope=EnvelopeScope.SCENARIO, posture=Posture.EXACT, domain="name"),
            EnvelopeBinding(path="nodes.h.type", scope=EnvelopeScope.NODE, posture=Posture.EXACT, domain="vm"),
            EnvelopeBinding(
                path="nodes.h.resources.cpu", scope=EnvelopeScope.FIELD, posture=Posture.CONSTRAINED, domain="cpu"
            ),
        ],
    )
    within = _instantiate("name: s\nnodes:\n  h:\n    type: vm\n    resources:\n      ram: 2048\n      cpu: 2\n")
    outside = _instantiate("name: s\nnodes:\n  h:\n    type: vm\n    resources:\n      ram: 2048\n      cpu: 9\n")
    assert member(within, env).holds
    assert not member(outside, env).holds


# --------------------------------------------------------------------------- #
# Subsumption (R4)                                                            #
# --------------------------------------------------------------------------- #


def test_subsumption_reflexive() -> None:
    env = _web_envelope()
    assert subsumes(env, env).holds


def test_subsumption_wider_offered_contains_narrower() -> None:
    offered = _leaf_enum_env({"a", "b", "c"})
    requested = _leaf_enum_env({"a", "b"})
    assert subsumes(offered, requested).holds
    assert not subsumes(requested, offered).holds


def test_subsumption_requested_open_where_offered_constrained() -> None:
    offered = _leaf_enum_env({"a", "b"})
    requested = RealizationEnvelopeModel(
        id="req",
        scope=EnvelopeScope.FIELD,
        domains={"leaf": EnumDomain(values=["a", "b"])},
        bindings=[EnvelopeBinding(path="x", scope=EnvelopeScope.FIELD, posture=Posture.OPEN)],
    )
    result = subsumes(offered, requested)
    assert not result.holds
    assert any(d.code == "realization-envelope.subsumption.requested-unconstrained" for d in result.diagnostics)


def test_subsumption_closure_mismatch() -> None:
    offered = _web_envelope(closed=True)
    requested = _web_envelope(closed=False)
    result = subsumes(offered, requested)
    assert not result.holds
    assert any(d.code == "realization-envelope.subsumption.closure-mismatch" for d in result.diagnostics)


def test_subsumption_numeric_interval_types() -> None:
    number = RealizationEnvelopeModel(
        id="num",
        scope=EnvelopeScope.FIELD,
        domains={"leaf": NumericIntervalDomain(numeric_type=NumericType.NUMBER, lower=0.0, upper=10.0)},
        bindings=[EnvelopeBinding(path="x", scope=EnvelopeScope.FIELD, posture=Posture.CONSTRAINED, domain="leaf")],
    )
    integer = _leaf_int_interval_env(2, 5)
    # An integer sub-interval fits inside a real super-interval...
    assert subsumes(number, integer).holds
    # ...but a real interval is not contained in an integer one (it has non-ints).
    assert not subsumes(integer, number).holds


# --------------------------------------------------------------------------- #
# Witness (R5)                                                                #
# --------------------------------------------------------------------------- #


def test_witness_is_deterministic_and_in_envelope() -> None:
    env = _web_envelope()
    first = witness(env)
    second = witness(env)
    assert first.scenario is not None
    assert second.scenario is not None
    assert first.scenario.model_dump(mode="json") == second.scenario.model_dump(mode="json")
    assert member(first.scenario, env).holds


def test_witness_default_selects_lexicographically_first_enum() -> None:
    env = _web_envelope(os_values=("windows", "linux"))
    result = witness(env)
    assert result.scenario is not None
    assert result.scenario.nodes["web"].os.value == "linux"


def test_witness_policy_overrides_default() -> None:
    env = _web_envelope(selection="windows")
    result = witness(env)
    assert result.scenario is not None
    assert result.scenario.nodes["web"].os.value == "windows"


def test_witness_under_specified_envelope_yields_diagnostic() -> None:
    # Binds os but not the required scenario name/node type: no valid witness.
    env = RealizationEnvelopeModel(
        id="partial",
        scope=EnvelopeScope.FIELD,
        domains={"os": EnumDomain(values=["linux"])},
        bindings=[
            EnvelopeBinding(path="nodes.web.os", scope=EnvelopeScope.FIELD, posture=Posture.CONSTRAINED, domain="os")
        ],
    )
    result = witness(env)
    assert result.scenario is None
    assert result.diagnostics
    assert result.diagnostics[0].code.startswith("realization-envelope.witness.")


def test_witness_rejects_list_indexed_path() -> None:
    env = RealizationEnvelopeModel(
        id="listy",
        scope=EnvelopeScope.SCENARIO,
        domains={"name": ExactDomain(value="s"), "v": ExactDomain(value="x")},
        bindings=[
            EnvelopeBinding(path="name", scope=EnvelopeScope.SCENARIO, posture=Posture.EXACT, domain="name"),
            EnvelopeBinding(
                path="forwarding_agents[0].id", scope=EnvelopeScope.FIELD, posture=Posture.EXACT, domain="v"
            ),
        ],
    )
    result = witness(env)
    assert result.scenario is None
    assert any(d.code == "realization-envelope.witness.no-witness" for d in result.diagnostics)


# --------------------------------------------------------------------------- #
# Negative probes (R6)                                                        #
# --------------------------------------------------------------------------- #


def _probe_is_out_of_envelope(payload: dict, env: RealizationEnvelopeModel) -> bool:
    try:
        instance = instantiate_scenario(Scenario.model_validate(payload))
    except (ValidationError, SDLValidationError, SDLInstantiationError):
        # invalid SDL is never a member; any other exception is a real bug and must propagate
        return True
    return not member(instance, env).holds


def test_negative_probes_are_all_out_of_envelope() -> None:
    env = _web_envelope(closed=True)
    probes, diagnostics = generate_negative_probes(env)
    assert not diagnostics
    assert probes
    variations = {p.variation for p in probes}
    assert "value-outside-domain" in variations
    assert "extra-dimension" in variations
    assert "omitted-required-exact" in variations
    for probe in probes:
        assert _probe_is_out_of_envelope(probe.payload, env), probe.path


def test_negative_probes_without_witness_report_diagnostic() -> None:
    env = RealizationEnvelopeModel(
        id="no-witness",
        scope=EnvelopeScope.FIELD,
        domains={"os": EnumDomain(values=["linux"])},
        bindings=[
            EnvelopeBinding(path="nodes.web.os", scope=EnvelopeScope.FIELD, posture=Posture.CONSTRAINED, domain="os")
        ],
    )
    probes, diagnostics = generate_negative_probes(env)
    assert probes == ()
    assert any(d.code == "realization-envelope.negative-probe.no-witness" for d in diagnostics)


# --------------------------------------------------------------------------- #
# Property tests: decidability, determinism, set inclusion                     #
# --------------------------------------------------------------------------- #

_UNIVERSE = ("a", "b", "c", "d")
_enum_subsets = st.sets(st.sampled_from(_UNIVERSE), min_size=1)


@settings(max_examples=200, deadline=None)
@given(offered=_enum_subsets, requested=_enum_subsets)
def test_property_subsumption_is_enum_set_inclusion(offered: set[str], requested: set[str]) -> None:
    result = subsumes(_leaf_enum_env(offered, "off"), _leaf_enum_env(requested, "req"))
    assert result.holds == (requested <= offered)


@settings(max_examples=100, deadline=None)
@given(a=_enum_subsets, b=_enum_subsets, c=_enum_subsets)
def test_property_subsumption_transitive(a: set[str], b: set[str], c: set[str]) -> None:
    env_a, env_b, env_c = _leaf_enum_env(a, "a"), _leaf_enum_env(b, "b"), _leaf_enum_env(c, "c")
    if subsumes(env_a, env_b).holds and subsumes(env_b, env_c).holds:
        assert subsumes(env_a, env_c).holds


@settings(max_examples=100, deadline=None)
@given(
    lo=st.integers(min_value=-20, max_value=20),
    span=st.integers(min_value=0, max_value=20),
    lo2=st.integers(min_value=-20, max_value=20),
    span2=st.integers(min_value=0, max_value=20),
)
def test_property_integer_interval_subsumption_matches_int_ranges(lo: int, span: int, lo2: int, span2: int) -> None:
    offered = _leaf_int_interval_env(lo, lo + span, "off")
    requested = _leaf_int_interval_env(lo2, lo2 + span2, "req")
    expected = set(range(lo2, lo2 + span2 + 1)) <= set(range(lo, lo + span + 1))
    assert subsumes(offered, requested).holds == expected


@settings(max_examples=50, deadline=None)
@given(os_values=st.sets(st.sampled_from(("linux", "windows")), min_size=1))
def test_property_witness_is_member_and_deterministic(os_values: set[str]) -> None:
    env = _web_envelope(os_values=tuple(sorted(os_values)))
    first = witness(env)
    second = witness(env)
    assert first.scenario is not None
    assert first.scenario.model_dump(mode="json") == second.scenario.model_dump(mode="json")
    assert member(first.scenario, env).holds


@settings(max_examples=50, deadline=None)
@given(os_values=st.sets(st.sampled_from(("linux", "windows")), min_size=1))
def test_property_negative_probes_out_of_envelope(os_values: set[str]) -> None:
    env = _web_envelope(os_values=tuple(sorted(os_values)), closed=True)
    probes, diagnostics = generate_negative_probes(env)
    assert not diagnostics
    for probe in probes:
        assert _probe_is_out_of_envelope(probe.payload, env), probe.path


# --------------------------------------------------------------------------- #
# Record domains + open posture (R2)                                          #
# --------------------------------------------------------------------------- #


def _record_node_envelope(*, open_os: bool = False, record_overrideable: bool = False) -> RealizationEnvelopeModel:
    bindings = [
        EnvelopeBinding(path="name", scope=EnvelopeScope.SCENARIO, posture=Posture.EXACT, domain="name"),
        EnvelopeBinding(
            path="nodes.web",
            scope=EnvelopeScope.NODE,
            posture=Posture.CONSTRAINED,
            domain="node",
            overrideable=record_overrideable,
        ),
    ]
    if open_os:
        bindings.append(EnvelopeBinding(path="nodes.web.os", scope=EnvelopeScope.FIELD, posture=Posture.OPEN))
    return RealizationEnvelopeModel(
        id="record-node",
        scope=EnvelopeScope.SCENARIO,
        domains={
            "name": ExactDomain(value="rec"),
            "vm": ExactDomain(value="vm"),
            "os": EnumDomain(values=["linux", "windows"]),
            "node": RecordDomain(fields={"type": "vm", "os": "os"}, extra=False),
        },
        bindings=bindings,
    )


def test_record_domain_membership_and_witness() -> None:
    env = _record_node_envelope()
    result = witness(env)
    assert result.scenario is not None
    assert member(result.scenario, env).holds
    # A closed record rejects an undeclared field on the node.
    extra = _instantiate('name: rec\nnodes:\n  web:\n    type: vm\n    os: linux\n    os_version: "9"\n')
    rejected = member(extra, env)
    assert not rejected.holds
    assert any(d.code == "realization-envelope.membership.closed-world-extra" for d in rejected.diagnostics)


def test_open_posture_widens_overrideable_record_leaf() -> None:
    # The record binding is marked overrideable, so opening os at the field scope
    # legally widens the record's os constraint (most-specific-wins, R2).
    env = _record_node_envelope(open_os=True, record_overrideable=True)
    linux = _instantiate("name: rec\nnodes:\n  web:\n    type: vm\n    os: linux\n")
    windows = _instantiate("name: rec\nnodes:\n  web:\n    type: vm\n    os: windows\n")
    assert member(linux, env).holds
    assert member(windows, env).holds


def test_widening_non_overrideable_inherited_value_is_invalid() -> None:
    # Same shape but the record is NOT overrideable: opening os would widen a fixed
    # inherited value, which R2 makes an ill-formed envelope. The relation denies.
    env = _record_node_envelope(open_os=True, record_overrideable=False)
    linux = _instantiate("name: rec\nnodes:\n  web:\n    type: vm\n    os: linux\n")
    result = member(linux, env)
    assert not result.holds
    assert any(d.code == "realization-envelope.invalid.non-overrideable-widen" for d in result.diagnostics)
    witness_result = witness(env)
    assert witness_result.scenario is None
    assert any(d.code == "realization-envelope.invalid.non-overrideable-widen" for d in witness_result.diagnostics)
    assert not subsumes(env, env).holds


def test_subsumption_over_governed_and_boolean_domains() -> None:
    def governed(refs: list[str], name: str, authority: str = "reg") -> RealizationEnvelopeModel:
        return RealizationEnvelopeModel(
            id=name,
            scope=EnvelopeScope.FIELD,
            domains={"leaf": GovernedReferenceDomain(authority=authority, allowed_refs=refs)},
            bindings=[EnvelopeBinding(path="x", scope=EnvelopeScope.FIELD, posture=Posture.CONSTRAINED, domain="leaf")],
        )

    assert subsumes(governed(["a", "b", "c"], "o"), governed(["a"], "r")).holds
    assert not subsumes(governed(["a"], "o"), governed(["a", "b"], "r")).holds
    # Authority scopes the refs: overlapping ref strings under different authorities
    # must NOT subsume (governed-reference authority boundary — codex security finding).
    assert not subsumes(
        governed(["a", "b"], "o", authority="registry-x"),
        governed(["a"], "r", authority="registry-y"),
    ).holds


def test_subsumption_governed_reference_rejects_cross_kind() -> None:
    # A governed-reference domain and a raw enum with the same strings must not
    # subsume in either direction: the enum values are not authority-scoped refs.
    governed = RealizationEnvelopeModel(
        id="g",
        scope=EnvelopeScope.FIELD,
        domains={"leaf": GovernedReferenceDomain(authority="reg", allowed_refs=["a", "b"])},
        bindings=[EnvelopeBinding(path="x", scope=EnvelopeScope.FIELD, posture=Posture.CONSTRAINED, domain="leaf")],
    )
    enum = _leaf_enum_env({"a"}, "e")
    assert not subsumes(governed, enum).holds
    assert not subsumes(enum, governed).holds

    def boolean(value: bool | None, name: str) -> RealizationEnvelopeModel:
        return RealizationEnvelopeModel(
            id=name,
            scope=EnvelopeScope.FIELD,
            domains={"leaf": BooleanDomain(value=value)},
            bindings=[EnvelopeBinding(path="x", scope=EnvelopeScope.FIELD, posture=Posture.CONSTRAINED, domain="leaf")],
        )

    assert subsumes(boolean(None, "o"), boolean(True, "r")).holds
    assert not subsumes(boolean(True, "o"), boolean(None, "r")).holds


# --------------------------------------------------------------------------- #
# Deterministic selection rules (R5 default policy / R6 variation)            #
# --------------------------------------------------------------------------- #


def test_default_witness_selection_rules() -> None:
    assert default_witness_value(ExactDomain(value=5)) == (5, None)
    assert default_witness_value(EnumDomain(values=["b", "a", "c"])) == ("a", None)
    assert default_witness_value(BooleanDomain()) == (False, None)
    assert default_witness_value(BooleanDomain(value=True)) == (True, None)
    assert default_witness_value(GovernedReferenceDomain(authority="r", allowed_refs=["z", "a"])) == ("a", None)
    assert default_witness_value(NumericIntervalDomain(numeric_type=NumericType.INTEGER, lower=1, upper=8)) == (
        1,
        None,
    )
    assert default_witness_value(
        NumericIntervalDomain(numeric_type=NumericType.INTEGER, lower=1, upper=8, lower_closed=False)
    ) == (2, None)
    assert default_witness_value(NumericIntervalDomain(numeric_type=NumericType.NUMBER, lower=0.0, upper=1.0)) == (
        0.0,
        None,
    )
    # An open-lower but bounded real interval is non-empty: pick the interior midpoint.
    assert default_witness_value(
        NumericIntervalDomain(numeric_type=NumericType.NUMBER, lower=0.0, upper=1.0, lower_closed=False)
    ) == (0.5, None)
    # An integer interval that admits no integer (open both ends, adjacent bounds) has no witness.
    value, error = default_witness_value(
        NumericIntervalDomain(
            numeric_type=NumericType.INTEGER, lower=1, upper=2, lower_closed=False, upper_closed=False
        )
    )
    assert value is None and error is not None


def test_out_of_domain_variation_rules() -> None:
    assert out_of_domain_value(ExactDomain(value="x")) == "x-out-of-envelope"
    assert out_of_domain_value(ExactDomain(value=3)) == 4
    assert out_of_domain_value(ExactDomain(value=True)) is False
    assert out_of_domain_value(BooleanDomain(value=True)) is False
    assert out_of_domain_value(BooleanDomain()) is _MISSING
    assert out_of_domain_value(EnumDomain(values=["a", "b"])) not in {"a", "b"}
    assert out_of_domain_value(EnumDomain(values=[1, 2])) == 3
    assert out_of_domain_value(GovernedReferenceDomain(authority="r", allowed_refs=["a", "b"])) not in {"a", "b"}
    assert out_of_domain_value(NumericIntervalDomain(numeric_type=NumericType.INTEGER, lower=1, upper=4)) == 5
    assert (
        out_of_domain_value(
            NumericIntervalDomain(numeric_type=NumericType.NUMBER, lower=0.0, upper=1.0, upper_closed=False)
        )
        == 1.0
    )
