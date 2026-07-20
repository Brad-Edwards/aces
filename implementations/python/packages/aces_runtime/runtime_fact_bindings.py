"""Run-local typed fact storage and trusted action-input binding."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from aces_contracts.contracts.runtime_facts import (
    RuntimeFactAbsenceDisposition,
    RuntimeFactAudience,
    RuntimeFactBindingDisposition,
    RuntimeFactBindingEventModel,
    RuntimeFactBindingRequestModel,
    RuntimeFactDeclarationModel,
    RuntimeFactProjectionModel,
    RuntimeFactSensitivity,
    RuntimeFactSinkModel,
    RuntimeFactSourceKind,
    RuntimeFactVersionModel,
)
from aces_contracts.diagnostics import Diagnostic

from .runtime_fact_dispatch import (
    RuntimeFactBindingAdmission,
    RuntimeFactDispatchCommand,
    _RuntimeFactDispatchBinding,
    _RuntimeFactDispatchFailure,
)


class RuntimeFactActionDisposition(str, Enum):
    """Aggregate action-dispatch outcome across all compiled sinks."""

    BOUND = "bound"
    BLOCKED = "blocked"
    FAILED = "failed"
    INAPPLICABLE = "inapplicable"


@dataclass(frozen=True)
class RuntimeFactBindingResult:
    """Value-free portable outcome and binding evidence."""

    accepted: bool
    action_disposition: RuntimeFactActionDisposition
    events: tuple[RuntimeFactBindingEventModel, ...]
    diagnostics: tuple[Diagnostic, ...]


class RuntimeFactBindingPlane:
    """Append-only fact plane whose dispatch policy comes from trusted admission."""

    def __init__(
        self,
        *,
        admissions: Iterable[RuntimeFactBindingAdmission] = (),
        action_dispatcher: Callable[[RuntimeFactDispatchCommand], None] | None = None,
        supported_source_kinds: Iterable[RuntimeFactSourceKind] | None = None,
    ) -> None:
        self._declarations: dict[str, RuntimeFactDeclarationModel] = {}
        self._versions: dict[str, list[RuntimeFactVersionModel]] = {}
        self._version_ids: set[str] = set()
        self._binding_events: list[RuntimeFactBindingEventModel] = []
        self._bound_action_instances: set[tuple[str, str, str, str | None, str, str]] = set()
        self._admissions: dict[tuple[str, str, str, str | None, str, str], RuntimeFactBindingAdmission] = {}
        for admission in admissions:
            if admission.action_key in self._admissions:
                raise ValueError("trusted binding admissions must identify unique action instances")
            self._admissions[admission.action_key] = admission
        self._action_dispatcher = action_dispatcher
        self._supported_source_kinds = frozenset(
            RuntimeFactSourceKind if supported_source_kinds is None else supported_source_kinds
        )

    def declare(self, declaration: RuntimeFactDeclarationModel) -> None:
        current = self._declarations.get(declaration.fact_id)
        if current is not None and current != declaration:
            raise ValueError(f"fact_id {declaration.fact_id!r} is already declared differently")
        self._declarations[declaration.fact_id] = declaration
        self._versions.setdefault(declaration.fact_id, [])

    def append(self, version: RuntimeFactVersionModel) -> None:
        declaration = self._declarations.get(version.fact_id)
        if declaration is None:
            raise ValueError(f"fact_id {version.fact_id!r} is not declared")
        if version.version_id in self._version_ids:
            raise ValueError(f"version_id {version.version_id!r} already exists")
        if (
            version.value_type != declaration.value_type
            or version.source_kind != declaration.source_kind
            or version.sensitivity != declaration.sensitivity
        ):
            raise ValueError("fact version type, source, and sensitivity must match its declaration")
        history = self._versions[version.fact_id]
        expected_sequence = len(history) + 1
        if version.sequence != expected_sequence:
            raise ValueError(f"fact version sequence must be {expected_sequence}")
        history.append(version)
        self._version_ids.add(version.version_id)

    def history(self, fact_id: str) -> tuple[RuntimeFactVersionModel, ...]:
        return tuple(self._versions.get(fact_id, ()))

    def bind_action_inputs(self, request: RuntimeFactBindingRequestModel) -> RuntimeFactBindingResult:
        action_key = _action_key(request)
        if action_key in self._bound_action_instances:
            raise ValueError(
                f"action_instance_id {request.action_instance_id!r} already has immutable fact binding history"
            )
        admission = self._admissions.get(action_key)
        if admission is None:
            return RuntimeFactBindingResult(
                accepted=False,
                action_disposition=RuntimeFactActionDisposition.FAILED,
                events=(),
                diagnostics=(self._diagnostic(request.action_contract_address, "unauthorized"),),
            )

        events: list[RuntimeFactBindingEventModel] = []
        diagnostics: list[Diagnostic] = []
        action_failures: list[RuntimeFactActionDisposition] = []
        dispatch_bindings: list[_RuntimeFactDispatchBinding] = []
        bound_selections: list[tuple[int, RuntimeFactSinkModel, RuntimeFactVersionModel]] = []
        for index, selection in enumerate(admission.selections, start=1):
            sink = selection.sink
            candidates = self._visible_candidates(
                request,
                admission,
                sink,
                selection.candidate_fact_ids,
            )
            if len(candidates) != 1:
                disposition = (
                    RuntimeFactBindingDisposition.ABSENT if not candidates else RuntimeFactBindingDisposition.AMBIGUOUS
                )
                events.append(self._event(request, admission, sink, index, disposition=disposition))
                diagnostics.append(self._diagnostic(sink.sink_id, disposition.value))
                action_failures.append(
                    _absence_action_disposition(sink.absence_disposition)
                    if disposition is RuntimeFactBindingDisposition.ABSENT
                    else RuntimeFactActionDisposition.FAILED
                )
                continue
            version = candidates[0]
            declaration = self._declarations[version.fact_id]
            disposition = self._validate_binding(admission, sink, declaration, version)
            if disposition is not RuntimeFactBindingDisposition.BOUND:
                safe_version = (
                    None
                    if disposition
                    in {
                        RuntimeFactBindingDisposition.UNAUTHORIZED,
                        RuntimeFactBindingDisposition.WRONG_SCOPE,
                    }
                    else version
                )
                events.append(
                    self._event(
                        request,
                        admission,
                        sink,
                        index,
                        disposition=disposition,
                        version=safe_version,
                    )
                )
                diagnostics.append(self._diagnostic(sink.sink_id, disposition.value))
                action_failures.append(RuntimeFactActionDisposition.FAILED)
                continue
            dispatch_bindings.append(
                _RuntimeFactDispatchBinding(
                    sink=sink,
                    value=version.value,
                    secret_ref=version.secret_ref,
                )
            )
            bound_selections.append((index, sink, version))

        if diagnostics:
            return self._record_result(action_key, events, diagnostics, action_failures)

        dispatch_disposition = self._dispatch(tuple(dispatch_bindings))
        if dispatch_disposition is not RuntimeFactBindingDisposition.BOUND:
            for index, sink, version in bound_selections:
                events.append(
                    self._event(
                        request,
                        admission,
                        sink,
                        index,
                        disposition=dispatch_disposition,
                        version=version,
                    )
                )
                diagnostics.append(self._diagnostic(sink.sink_id, dispatch_disposition.value))
            action_failures.append(RuntimeFactActionDisposition.FAILED)
            return self._record_result(action_key, events, diagnostics, action_failures)

        for index, sink, version in bound_selections:
            events.append(
                self._event(
                    request,
                    admission,
                    sink,
                    index,
                    disposition=RuntimeFactBindingDisposition.BOUND,
                    version=version,
                )
            )
        return self._record_result(action_key, events, diagnostics, action_failures)

    def _dispatch(self, bindings: tuple[_RuntimeFactDispatchBinding, ...]) -> RuntimeFactBindingDisposition:
        if self._action_dispatcher is None:
            return RuntimeFactBindingDisposition.DISPATCH_FAILED
        command = RuntimeFactDispatchCommand(bindings)
        try:
            self._action_dispatcher(command)
        except _RuntimeFactDispatchFailure as exc:
            return exc.disposition
        except Exception:
            return RuntimeFactBindingDisposition.DISPATCH_FAILED
        if not command.completed:
            return RuntimeFactBindingDisposition.DISPATCH_FAILED
        return RuntimeFactBindingDisposition.BOUND

    def _record_result(
        self,
        action_key: tuple[str, str, str, str | None, str, str],
        events: list[RuntimeFactBindingEventModel],
        diagnostics: list[Diagnostic],
        action_failures: list[RuntimeFactActionDisposition],
    ) -> RuntimeFactBindingResult:
        self._binding_events.extend(events)
        self._bound_action_instances.add(action_key)
        return RuntimeFactBindingResult(
            accepted=not diagnostics,
            action_disposition=_aggregate_action_disposition(action_failures),
            events=tuple(events),
            diagnostics=tuple(diagnostics),
        )

    def _visible_candidates(
        self,
        request: RuntimeFactBindingRequestModel,
        admission: RuntimeFactBindingAdmission,
        sink: RuntimeFactSinkModel,
        candidate_fact_ids: list[str],
    ) -> list[RuntimeFactVersionModel]:
        visible: list[RuntimeFactVersionModel] = []
        requested_at = _parse_datetime(admission.requested_at)
        for fact_id in candidate_fact_ids:
            history = self._versions.get(fact_id)
            if not history:
                continue
            eligible = [version for version in history if _parse_datetime(version.observed_at) <= requested_at]
            if not eligible:
                continue
            version = max(
                eligible,
                key=lambda item: (_parse_datetime(item.observed_at), item.sequence),
            )
            declaration = self._declarations[fact_id]
            if not self._candidate_visible(request, sink, declaration, version):
                continue
            visible.append(version)
        return visible

    @staticmethod
    def _candidate_visible(
        request: RuntimeFactBindingRequestModel,
        sink: RuntimeFactSinkModel,
        declaration: RuntimeFactDeclarationModel,
        version: RuntimeFactVersionModel,
    ) -> bool:
        if version.scope.run_id != request.run_id:
            return False
        if version.scope.participant_address not in {None, request.participant_address}:
            return False
        if version.scope.episode_id not in {None, request.episode_id}:
            return False
        if version.scope.workflow_address not in {None, request.workflow_address}:
            return False
        if sink.audience is RuntimeFactAudience.WORKFLOW:
            return bool(
                request.workflow_address and request.workflow_address in declaration.visibility.workflow_addresses
            )
        return request.participant_address in declaration.visibility.participant_addresses

    def binding_history(self) -> tuple[RuntimeFactBindingEventModel, ...]:
        return tuple(self._binding_events)

    def project_for_participant(
        self,
        *,
        run_id: str,
        participant_address: str,
        episode_id: str,
    ) -> tuple[RuntimeFactProjectionModel, ...]:
        return self._project(
            run_id=run_id,
            participant_address=participant_address,
            episode_id=episode_id,
        )

    def project_for_workflow(
        self,
        *,
        run_id: str,
        workflow_address: str,
    ) -> tuple[RuntimeFactProjectionModel, ...]:
        return self._project(run_id=run_id, workflow_address=workflow_address)

    def _project(
        self,
        *,
        run_id: str,
        participant_address: str | None = None,
        episode_id: str | None = None,
        workflow_address: str | None = None,
    ) -> tuple[RuntimeFactProjectionModel, ...]:
        projections: list[RuntimeFactProjectionModel] = []
        for fact_id in sorted(self._versions):
            history = self._versions[fact_id]
            if not history:
                continue
            version = history[-1]
            declaration = self._declarations[fact_id]
            if version.scope.run_id != run_id:
                continue
            if participant_address is not None:
                if participant_address not in declaration.visibility.participant_addresses:
                    continue
                if version.scope.participant_address not in {None, participant_address}:
                    continue
                if version.scope.episode_id not in {None, episode_id}:
                    continue
            elif workflow_address is not None:
                if workflow_address not in declaration.visibility.workflow_addresses:
                    continue
                if version.scope.workflow_address not in {None, workflow_address}:
                    continue
            projections.append(self._projection(version))
        return tuple(projections)

    @staticmethod
    def _projection(version: RuntimeFactVersionModel) -> RuntimeFactProjectionModel:
        secret = version.sensitivity is RuntimeFactSensitivity.SECRET
        return RuntimeFactProjectionModel(
            fact_id=version.fact_id,
            fact_version_id=version.version_id,
            value_type=version.value_type,
            source_kind=version.source_kind,
            sensitivity=version.sensitivity,
            scope=version.scope,
            observed_at=version.observed_at,
            value=None if secret else version.value,
            redacted=secret,
            secret_reference_present=secret,
            confidence=version.confidence,
            evidence_refs=list(version.evidence_refs),
            provenance_refs=list(version.provenance_refs),
        )

    def _validate_binding(
        self,
        admission: RuntimeFactBindingAdmission,
        sink: RuntimeFactSinkModel,
        declaration: RuntimeFactDeclarationModel,
        version: RuntimeFactVersionModel,
    ) -> RuntimeFactBindingDisposition:
        if version.source_kind not in self._supported_source_kinds:
            return RuntimeFactBindingDisposition.UNSUPPORTED
        if version.value_type != sink.value_type:
            return RuntimeFactBindingDisposition.WRONG_TYPE
        if version.source_kind not in sink.allowed_source_kinds:
            return RuntimeFactBindingDisposition.UNSUPPORTED
        if version.scope.kind not in sink.allowed_scope_kinds:
            return RuntimeFactBindingDisposition.WRONG_SCOPE
        if version.sensitivity not in sink.allowed_sensitivities:
            return RuntimeFactBindingDisposition.UNAUTHORIZED
        if sink.audience is not RuntimeFactAudience.PROTECTED_SINK and (
            version.sensitivity is RuntimeFactSensitivity.SECRET
        ):
            return RuntimeFactBindingDisposition.UNAUTHORIZED
        required_authority = set(declaration.authority_refs) | set(sink.authority_refs)
        if not required_authority.issubset(admission.authority_refs):
            return RuntimeFactBindingDisposition.UNAUTHORIZED
        if sink.max_age_seconds is not None:
            requested_at = _parse_datetime(admission.requested_at)
            observed_at = _parse_datetime(version.observed_at)
            if observed_at > requested_at:
                return RuntimeFactBindingDisposition.STALE
            if (requested_at - observed_at).total_seconds() > sink.max_age_seconds:
                return RuntimeFactBindingDisposition.STALE
        if version.expires_at is not None and _parse_datetime(admission.requested_at) > _parse_datetime(
            version.expires_at
        ):
            return RuntimeFactBindingDisposition.STALE
        return RuntimeFactBindingDisposition.BOUND

    @staticmethod
    def _event(
        request: RuntimeFactBindingRequestModel,
        admission: RuntimeFactBindingAdmission,
        sink: RuntimeFactSinkModel,
        index: int,
        *,
        disposition: RuntimeFactBindingDisposition,
        version: RuntimeFactVersionModel | None = None,
    ) -> RuntimeFactBindingEventModel:
        return RuntimeFactBindingEventModel(
            event_id=f"fact-binding.{request.action_instance_id}.{index}",
            run_id=request.run_id,
            participant_address=request.participant_address,
            episode_id=request.episode_id,
            workflow_address=request.workflow_address,
            action_instance_id=request.action_instance_id,
            action_contract_address=request.action_contract_address,
            sink_id=sink.sink_id,
            target_field=sink.target_field,
            fact_id=version.fact_id if version is not None else None,
            fact_version_id=version.version_id if version is not None else None,
            disposition=disposition,
            sensitivity=version.sensitivity if version is not None else None,
            evidence_refs=list(version.evidence_refs) if version is not None else [],
            provenance_refs=list(version.provenance_refs) if version is not None else [],
            authorization_refs=sorted(admission.authority_refs),
            redacted=bool(version is not None and version.secret_ref is not None),
            reason_code=None
            if disposition is RuntimeFactBindingDisposition.BOUND
            else f"runtime.fact-binding.{disposition.value}",
        )

    @staticmethod
    def _diagnostic(sink_id: str, reason: str) -> Diagnostic:
        return Diagnostic(
            code=f"runtime.fact-binding.{reason}",
            domain="runtime",
            address=sink_id,
            message=f"runtime fact binding failed: {reason}",
        )


def _action_key(
    request: RuntimeFactBindingRequestModel,
) -> tuple[str, str, str, str | None, str, str]:
    return (
        request.run_id,
        request.participant_address,
        request.episode_id,
        request.workflow_address,
        request.action_instance_id,
        request.action_contract_address,
    )


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00").replace("z", "+00:00"))


def _absence_action_disposition(
    disposition: RuntimeFactAbsenceDisposition,
) -> RuntimeFactActionDisposition:
    return {
        RuntimeFactAbsenceDisposition.BLOCK: RuntimeFactActionDisposition.BLOCKED,
        RuntimeFactAbsenceDisposition.FAIL: RuntimeFactActionDisposition.FAILED,
        RuntimeFactAbsenceDisposition.INAPPLICABLE: RuntimeFactActionDisposition.INAPPLICABLE,
    }[disposition]


def _aggregate_action_disposition(
    failures: list[RuntimeFactActionDisposition],
) -> RuntimeFactActionDisposition:
    if not failures:
        return RuntimeFactActionDisposition.BOUND
    if RuntimeFactActionDisposition.FAILED in failures:
        return RuntimeFactActionDisposition.FAILED
    if RuntimeFactActionDisposition.BLOCKED in failures:
        return RuntimeFactActionDisposition.BLOCKED
    return RuntimeFactActionDisposition.INAPPLICABLE


__all__ = (
    "RuntimeFactActionDisposition",
    "RuntimeFactBindingAdmission",
    "RuntimeFactBindingPlane",
    "RuntimeFactBindingResult",
    "RuntimeFactDispatchCommand",
)
