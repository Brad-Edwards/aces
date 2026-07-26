"""Libvirt backend participant runtime.

``LibvirtParticipantRuntime`` drives RUN-311 episode lifecycle transitions via
the shared ``BaseParticipantRuntime`` machinery and delegates domain-side
action modeling to a pluggable ``LibvirtParticipantDomainAdapter``.

The default adapter (``DeterministicParticipantDomainAdapter``) is a structural
proof adapter: it returns admission requests unchanged without invoking real
libvirt domain operations. This makes the runtime suitable for conformance
proofs and CI pipelines that cannot provision live infrastructure.

Callers that need real domain execution (network probes, VM command dispatch,
Wazuh evidence collection) inject a custom ``LibvirtParticipantDomainAdapter``
implementation at construction time.
"""

from __future__ import annotations

from raes_backend_protocols.participant_runtime_base import BaseParticipantRuntime
from raes_contracts.participant_binding import ParticipantActionAdmissionRequest
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot

from .participant_domain import DeterministicParticipantDomainAdapter, LibvirtParticipantDomainAdapter


class LibvirtParticipantRuntime(BaseParticipantRuntime):
    """Libvirt backend participant runtime, driving RUN-311 transitions.

    Inherits the full episode state machine from ``BaseParticipantRuntime`` and
    decorates ``admit_action`` so the injected ``LibvirtParticipantDomainAdapter``
    can model the libvirt domain side-effect before the shared machinery records
    behavior history. With the default ``DeterministicParticipantDomainAdapter``
    no live libvirt domain is touched; that limitation is surfaced in the
    manifest's ``feature_support`` entries for each claimed behavior feature.
    """

    def __init__(
        self,
        domain_adapter: LibvirtParticipantDomainAdapter | None = None,
    ) -> None:
        super().__init__()
        self._domain_adapter: LibvirtParticipantDomainAdapter = (
            domain_adapter if domain_adapter is not None else DeterministicParticipantDomainAdapter()
        )

    def admit_action(
        self,
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
    ) -> ApplyResult:
        return super().admit_action(self._domain_adapter.model_action(request), snapshot)
