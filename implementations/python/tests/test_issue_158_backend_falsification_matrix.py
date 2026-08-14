"""Does the backend boundary falsify dishonest realization claims? (issue #158)

Issue #158 is a falsification protocol, not an implementation design. Its claim
under test: *backend agnosticism is credible only if conformance can reject
dishonest, incomplete, or overbroad backend claims instead of merely validating
happy-path stubs.*

Method. Each case is the **real** `ReferenceProvisioner` perturbed by exactly one
lie, so a rejection is attributable to that lie rather than to an incomplete
hand-rolled double. `test_honest_baseline_is_accepted` is the control: without a
perturbation the same construction is admitted, which is what makes the other
results meaningful.

Every fabrication below is refused at the boundary: the runtime returns the
untouched baseline snapshot with ``runtime.backend-contract-invalid``, so no lie
survives into the authoritative snapshot. "Realizes nothing" is refused by the
SEM-218 realization gate; the other four are refused by the plan-conformance
gate (``raes_runtime.backend_plan_conformance``), which holds the returned
snapshot to the submitted plan's addresses, resource types, domains, and
disclosed changes.

These probes bound the runtime backend boundary (`RuntimeManager.apply`) only.
`run_target_conformance` is not used as the discriminator because with default
arguments it also fails the honest reference backend, for the reason recorded in
issue #663: its default scenario is not universally realizable.
"""

from __future__ import annotations

import dataclasses

from raes import parse_sdl
from raes_contracts.planning import RuntimeDomain
from raes_contracts.runtime_state import ApplyResult
from raes_reference_backend import create_reference_backend_target
from raes_reference_backend.provisioner import ReferenceProvisioner
from raes_runtime.manager import RuntimeManager

_SCENARIO = """
name: backend-falsification
nodes:
  lab: {type: switch}
  web: {type: compute, resources: {ram: 1 gib, cpu: 1}}
infrastructure:
  lab: {count: 1, properties: {cidr: 10.0.0.0/24, gateway: 10.0.0.1}}
  web: {count: 1, links: [lab]}
"""

_SMUGGLED_ADDRESS = "provision.node.smuggled"


class _RealizesNothing(ReferenceProvisioner):
    """Reports success and every address as changed, returning the predecessor."""

    def apply(self, plan, snapshot):
        super().apply(plan, snapshot)
        return ApplyResult(
            success=True,
            snapshot=snapshot,
            changed_addresses=[operation.address for operation in plan.operations],
        )


class _InventsResource(ReferenceProvisioner):
    """Realizes the plan, then adds a resource the scenario never authored."""

    def apply(self, plan, snapshot):
        result = super().apply(plan, snapshot)
        if not result.success:
            return result
        entries = dict(result.snapshot.entries)
        entries[_SMUGGLED_ADDRESS] = dataclasses.replace(next(iter(entries.values())), address=_SMUGGLED_ADDRESS)
        return dataclasses.replace(
            result,
            snapshot=result.snapshot.with_entries(entries),
            changed_addresses=[*result.changed_addresses, _SMUGGLED_ADDRESS],
        )


class _SubstitutesResourceType(ReferenceProvisioner):
    """Realizes the planned addresses but relabels a node as a network."""

    def apply(self, plan, snapshot):
        result = super().apply(plan, snapshot)
        if not result.success:
            return result
        entries = dict(result.snapshot.entries)
        for address, entry in entries.items():
            if entry.resource_type == "node":
                entries[address] = dataclasses.replace(entry, resource_type="network")
                break
        return dataclasses.replace(result, snapshot=result.snapshot.with_entries(entries))


class _UnderReportsChanges(ReferenceProvisioner):
    """Mutates the snapshot but reports no changed addresses."""

    def apply(self, plan, snapshot):
        result = super().apply(plan, snapshot)
        if not result.success:
            return result
        return dataclasses.replace(result, changed_addresses=[])


class _ForgesDomain(ReferenceProvisioner):
    """Files provisioning results under the evaluation domain."""

    def apply(self, plan, snapshot):
        result = super().apply(plan, snapshot)
        if not result.success:
            return result
        entries = {
            address: dataclasses.replace(entry, domain=RuntimeDomain.EVALUATION)
            for address, entry in result.snapshot.entries.items()
        }
        return dataclasses.replace(result, snapshot=result.snapshot.with_entries(entries))


def _apply_with(provisioner_class=None):
    """Apply the scenario through the reference target, optionally perturbed.

    The perturbed provisioner is built from the honest one's driver and
    realization envelope, so the only difference from the control is the lie.
    """

    target = create_reference_backend_target()
    if provisioner_class is not None:
        honest = target.provisioner
        target = dataclasses.replace(
            target,
            provisioner=provisioner_class(
                honest._driver,  # noqa: SLF001 - perturbing the real provisioner is the method
                realization_envelope=honest._realization_envelope,  # noqa: SLF001
            ),
        )
    manager = RuntimeManager(target)
    return manager.apply(manager.plan(parse_sdl(_SCENARIO)))


def test_honest_baseline_is_accepted():
    """The control. Without it, a rejection below would prove nothing."""

    result = _apply_with()

    assert result.success, [diagnostic.message for diagnostic in result.diagnostics]
    assert sorted(result.snapshot.entries) == ["provision.network.lab", "provision.node.web"]


def test_a_backend_that_realizes_nothing_is_refused():
    """The one fabrication the boundary already refuses."""

    result = _apply_with(_RealizesNothing)

    assert result.success is False
    assert "runtime.backend-contract-invalid" in {diagnostic.code for diagnostic in result.diagnostics}


def test_a_backend_cannot_invent_resources_the_scenario_never_authored():
    result = _apply_with(_InventsResource)

    assert result.success is False
    assert "runtime.backend-contract-invalid" in {diagnostic.code for diagnostic in result.diagnostics}
    assert _SMUGGLED_ADDRESS not in result.snapshot.entries


def test_a_backend_cannot_misreport_what_kind_of_resource_it_realized():
    result = _apply_with(_SubstitutesResourceType)

    assert result.success is False
    assert "runtime.backend-contract-invalid" in {diagnostic.code for diagnostic in result.diagnostics}
    realized = {entry.resource_type for entry in result.snapshot.entries.values()}
    assert "node" not in realized or realized == {"network", "node"}


def test_a_backend_cannot_mutate_state_while_reporting_no_changes():
    result = _apply_with(_UnderReportsChanges)

    assert result.success is False
    assert "runtime.backend-contract-invalid" in {diagnostic.code for diagnostic in result.diagnostics}
    assert result.snapshot.entries == {}


def test_a_backend_cannot_file_provisioning_results_under_another_domain():
    result = _apply_with(_ForgesDomain)

    assert result.success is False
    assert "runtime.backend-contract-invalid" in {diagnostic.code for diagnostic in result.diagnostics}
    domains = {getattr(entry.domain, "value", entry.domain) for entry in result.snapshot.entries.values()}
    assert "evaluation" not in domains
