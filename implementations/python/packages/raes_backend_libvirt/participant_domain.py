"""Participant domain adapter protocol and deterministic implementation.

The ``LibvirtParticipantDomainAdapter`` is the boundary between the
``LibvirtParticipantRuntime`` episode machinery and the actual domain execution
(e.g. running a probe inside a libvirt VM). The deterministic implementation
is the default: it models the action without any live domain call, which
makes the runtime suitable for structural conformance proofs and CI pipelines.
"""

from __future__ import annotations

from typing import Protocol

from raes_contracts.participant_binding import ParticipantActionAdmissionRequest


class LibvirtParticipantDomainAdapter(Protocol):
    """Domain side-effect boundary for ``LibvirtParticipantRuntime``.

    Implementations model what happens to the libvirt domain when the
    participant takes an action. ``LibvirtParticipantRuntime.admit_action``
    calls ``model_action`` before recording behavior history events, so the
    adapter can inject ``evidence_refs``, ``action_result``, or other
    admission-request fields derived from the domain outcome.

    The returned request must remain structurally valid (same participant and
    action contract addresses as the original). Implementations that cannot
    realize the full domain effect MUST disclose the limitation in the
    manifest's ``feature_support`` disclosure_refs.
    """

    def model_action(
        self,
        request: ParticipantActionAdmissionRequest,
    ) -> ParticipantActionAdmissionRequest:
        """Return an updated admission request with domain-side artifacts.

        The default implementation (``DeterministicParticipantDomainAdapter``)
        returns the request unchanged. Live implementations replace or augment
        fields such as ``visible_refs``, ``evidence_refs``, or ``action_result``
        based on what the domain actually observed.
        """
        ...


class DeterministicParticipantDomainAdapter:
    """Address-driven deterministic domain adapter.

    Returns the admission request unchanged — no live libvirt domain is
    invoked. The proof caller is responsible for supplying a structurally
    valid admission request (including any required SEM-211 ``action_result``
    for contracts with precondition/effect/failure classes).

    Disclosed limitation: this adapter does NOT invoke real libvirt VM
    actions, network connectivity checks, or Wazuh evidence collection. It
    is suitable for structural conformance proofs and CI pipelines that
    cannot provision live infrastructure. See the decision record at
    ``docs/decisions/issue-614-libvirt-participant-runtime.md``.
    """

    @staticmethod
    def model_action(
        request: ParticipantActionAdmissionRequest,
    ) -> ParticipantActionAdmissionRequest:
        return request
