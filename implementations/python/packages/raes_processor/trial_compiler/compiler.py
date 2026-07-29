"""Atomic deterministic compiler from admitted SCE-002 inputs to a sealed plan."""

from __future__ import annotations

from collections.abc import Mapping

from raes import (
    ExpandedScenarioBindingTargetResolver,
    canonical_sdl_digest,
    select_scenario_family,
    validate_experiment_selection_against_family,
)
from raes.realization_envelope import member
from raes_contracts.canonical import canonical_json_bytes, canonical_json_digest
from raes_contracts.contracts import (
    AdmittedBindingModel,
    AdmittedExecutionControlModel,
    AdmittedInstantiationProvenanceModel,
    AdmittedSelectionRecordModel,
    AdmittedTrialPlanAdmissionModel,
    ExperimentBindingDescriptorModel,
    ExperimentSelectionMemberOutcomeModel,
    ExperimentSelectionReferenceOutcomeModel,
    ExperimentSelectionSubsetOutcomeModel,
    LiteralBindingValueModel,
    ParticipantImplementationManifestModel,
    TrialCoordinateModel,
    seal_admitted_trial_entry,
    seal_admitted_trial_plan,
)
from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.experiment_bindings import (
    ApparatusManifest,
    ApparatusManifestKey,
    ParticipantManifestKey,
    validate_experiment_binding_targets,
)

from .apparatus import (
    validate_selected_apparatus,
    validate_selected_participant_manifests,
)
from .models import CompilationFailure, TrialCompilationRequest, TrialCompilationResult
from .policies import CoordinateSelections, ResolvedSelection, compile_coordinate_selections
from .profiles import admitted_profiles, coordinate_projection, derive_identity, replicate_id

_DOMAIN = "trial-compiler"


def _fail(code: str, address: str, message: str) -> CompilationFailure:
    return CompilationFailure(code, address, message)


def _diagnostic(failure: CompilationFailure) -> Diagnostic:
    return Diagnostic(
        code=f"{_DOMAIN}.{failure.code}",
        domain=_DOMAIN,
        address=failure.address,
        message=failure.safe_message,
        severity=Severity.ERROR,
    )


def _validate_input_identities(request: TrialCompilationRequest) -> None:
    refs = request.input_refs
    family_digest = canonical_sdl_digest(request.family).value
    authoring_digest = canonical_json_digest(request.experiment.model_dump(mode="json"))
    if refs.scenario_family_ref.ref_id != request.family.name or refs.scenario_family_ref.ref_digest != family_digest:
        raise _fail(
            "scenario-family-ref-mismatch",
            "/input_refs/scenario_family_ref",
            "scenario family reference does not match the admitted expanded family",
        )
    if (
        refs.authoring_input_ref.ref_id != request.experiment.spec_id
        or refs.authoring_input_ref.ref_version != request.experiment.spec_version
        or refs.authoring_input_ref.ref_digest != authoring_digest
    ):
        raise _fail(
            "authoring-input-ref-mismatch",
            "/input_refs/authoring_input_ref",
            "authoring input reference does not match the admitted experiment",
        )
    if refs.task_ref != request.experiment.task_ref:
        raise _fail(
            "task-ref-mismatch",
            "/input_refs/task_ref",
            "task reference does not match the admitted experiment",
        )
    descriptors = request.experiment.binding_descriptors
    descriptor_ref = refs.binding_descriptor_set_ref
    if descriptors is None and descriptor_ref is not None:
        raise _fail(
            "binding-set-ref-unexpected",
            "/input_refs/binding_descriptor_set_ref",
            "an unbound experiment must not carry a binding descriptor set reference",
        )
    if descriptors is not None:
        descriptor_digest = canonical_json_digest(descriptors.model_dump(mode="json"))
        if descriptor_ref is None or descriptor_ref.ref_digest != descriptor_digest:
            raise _fail(
                "binding-set-ref-mismatch",
                "/input_refs/binding_descriptor_set_ref",
                "binding descriptor set reference does not match the admitted descriptor set",
            )
    if request.apparatus.realization_envelope != request.realization_envelope.identity:
        raise _fail(
            "realization-envelope-ref-mismatch",
            "/apparatus/realization_envelope",
            "apparatus realization-envelope identity does not match the supplied carrier",
        )
    if refs.study_ref is not None or refs.associated_artifact_set_ref is not None:
        raise _fail(
            "referenced-input-payload-required",
            "/input_refs",
            "optional study or associated-artifact references require their exact typed payloads",
        )


def _coordinates(request: TrialCompilationRequest) -> list[TrialCoordinateModel]:
    run_plan = request.experiment.run_plan
    if run_plan.allocation is None:
        count = run_plan.target_run_count or 0
        if count == 0:
            raise _fail(
                "coordinate-set-empty",
                "/run_plan",
                "run allocation produced no logical trial coordinates",
            )
        if count > request.limits.max_coordinates:
            raise _fail(
                "coordinate-limit-exceeded",
                "/run_plan",
                "logical trial coordinates exceed the compilation limit",
            )
        return [TrialCoordinateModel(replicate_id=replicate_id(ordinal)) for ordinal in range(1, count + 1)]

    per_condition = run_plan.allocation.target_runs_per_condition
    condition_count = len(run_plan.allocation.compared_conditions)
    if condition_count == 0 or per_condition == 0:
        raise _fail(
            "coordinate-set-empty",
            "/run_plan",
            "run allocation produced no logical trial coordinates",
        )
    if condition_count > request.limits.max_coordinates // per_condition:
        raise _fail(
            "coordinate-limit-exceeded",
            "/run_plan",
            "logical trial coordinates exceed the compilation limit",
        )
    coordinates: list[TrialCoordinateModel] = []
    for condition_id in sorted(run_plan.allocation.compared_conditions):
        coordinates.extend(
            TrialCoordinateModel(
                condition_id=condition_id,
                replicate_id=replicate_id(ordinal),
            )
            for ordinal in range(1, per_condition + 1)
        )
    return coordinates


def _outcome_binding_value(
    request: TrialCompilationRequest,
    selection: ResolvedSelection,
) -> object | None:
    outcome = selection.outcome
    if isinstance(outcome, LiteralBindingValueModel):
        return outcome.value
    if isinstance(outcome, ExperimentSelectionReferenceOutcomeModel):
        return outcome.reference_id
    if isinstance(outcome, ExperimentSelectionMemberOutcomeModel):
        point = request.family.variation_points[selection.point_id]
        alternatives = getattr(point, "alternatives", {})
        member = alternatives.get(outcome.member_id)
        return member.reference if member is not None else None
    if isinstance(outcome, ExperimentSelectionSubsetOutcomeModel):
        return None
    return None


def _descriptor_matches_selection(
    request: TrialCompilationRequest,
    descriptor: ExperimentBindingDescriptorModel,
    selection: ResolvedSelection,
) -> bool:
    if getattr(descriptor.target, "variation_point_id", None) != selection.point_id:
        return False
    selected_value = _outcome_binding_value(request, selection)
    return isinstance(descriptor.value, LiteralBindingValueModel) and (
        type(descriptor.value.value) is type(selected_value) and descriptor.value.value == selected_value
    )


def _admitted_descriptors(
    request: TrialCompilationRequest,
    apparatus_manifests: Mapping[ApparatusManifestKey, ApparatusManifest],
    participant_manifests: Mapping[ParticipantManifestKey, ParticipantImplementationManifestModel],
) -> dict[str, ExperimentBindingDescriptorModel]:
    descriptors = request.experiment.binding_descriptors
    if descriptors is None:
        return {}
    try:
        admitted = validate_experiment_binding_targets(
            descriptors,
            scenario_resolver=ExpandedScenarioBindingTargetResolver(request.family),
            participant_manifests=participant_manifests,
            apparatus_manifests=apparatus_manifests,
        )
    except ValueError as exc:
        raise _fail(
            "binding-target-rejected",
            "/binding_descriptors",
            "a binding descriptor target failed authoritative admission",
        ) from exc
    return {descriptor.binding_id: descriptor for descriptor in admitted.descriptors}


def _entry_bindings(
    request: TrialCompilationRequest,
    row: CoordinateSelections,
    coordinate: TrialCoordinateModel,
    descriptors: Mapping[str, ExperimentBindingDescriptorModel],
) -> list[AdmittedBindingModel]:
    bindings: list[AdmittedBindingModel] = []
    for selection in row.selections:
        policy = request.experiment.run_plan.selection_policies[selection.policy_id]
        for descriptor_id in sorted(getattr(policy, "binding_descriptor_refs", ())):
            descriptor = descriptors.get(descriptor_id)
            if descriptor is None or descriptor.source_condition_id != coordinate.condition_id:
                continue
            if not _descriptor_matches_selection(request, descriptor, selection):
                raise _fail(
                    "binding-selection-mismatch",
                    f"/binding_descriptors/{descriptor_id}",
                    "a binding descriptor does not equal its selected variation outcome",
                )
            bindings.append(AdmittedBindingModel(descriptor=descriptor, origin="selection"))
    if len({binding.descriptor.binding_id for binding in bindings}) != len(bindings):
        raise _fail(
            "binding-duplicate",
            "/binding_descriptors",
            "an admitted binding descriptor is selected more than once",
        )
    if len(bindings) > request.limits.max_bindings_per_entry:
        raise _fail(
            "binding-limit-exceeded",
            "/binding_descriptors",
            "entry bindings exceed the compilation limit",
        )
    return bindings


def _selection_records(row: CoordinateSelections) -> list[AdmittedSelectionRecordModel]:
    return [
        AdmittedSelectionRecordModel(
            variation_point_id=selection.point_id,
            origin_policy_id=selection.policy_id,
            origin_policy_kind=selection.policy_kind,
            outcome=selection.outcome,
        )
        for selection in row.selections
    ]


def _validate_selected_scenario(
    request: TrialCompilationRequest,
    row: CoordinateSelections,
    coordinate: TrialCoordinateModel,
) -> None:
    outcomes = {selection.point_id: selection.outcome for selection in row.selections}
    try:
        selected = select_scenario_family(request.family, outcomes)
    except (TypeError, ValueError) as exc:
        raise _fail(
            "selected-scenario-rejected",
            "/entries/" + (coordinate.replicate_id or "coordinate"),
            "the complete selection failed SDL-owned whole-scenario admission",
        ) from exc
    envelope_result = member(selected, request.realization_envelope.expression)
    if not envelope_result.holds:
        raise _fail(
            "realization-envelope-membership-rejected",
            "/entries/" + (coordinate.replicate_id or "coordinate"),
            "the selected scenario is outside the admitted realization envelope",
        )


def _plan_intent(request: TrialCompilationRequest, coordinates: list[TrialCoordinateModel]) -> dict[str, object]:
    return {
        "profiles": admitted_profiles().model_dump(mode="json"),
        "input_refs": request.input_refs.model_dump(mode="json"),
        "apparatus": request.apparatus.model_dump(mode="json"),
        "execution_authority": request.execution_authority.model_dump(mode="json"),
        "coordinates": [coordinate_projection(coordinate) for coordinate in coordinates],
    }


def _visit_indices(
    coordinate_count: int,
    coordinate_partitions: tuple[tuple[int, ...], ...] | None,
) -> tuple[int, ...]:
    if coordinate_partitions is None:
        return tuple(range(coordinate_count))
    flattened = tuple(index for partition in coordinate_partitions for index in partition)
    if sorted(flattened) != list(range(coordinate_count)):
        raise _fail(
            "coordinate-partitions-invalid",
            "/run_plan",
            "coordinate partitions must cover every canonical coordinate exactly once",
        )
    return flattened


def _compile(
    request: TrialCompilationRequest,
    coordinate_partitions: tuple[tuple[int, ...], ...] | None,
):
    _validate_input_identities(request)
    apparatus_manifests = validate_selected_apparatus(request)
    participant_manifests = validate_selected_participant_manifests(request)
    try:
        validate_experiment_selection_against_family(request.experiment, family=request.family)
    except ValueError as exc:
        raise _fail(
            "selection-intent-rejected",
            "/run_plan/selection_policies",
            "selection policy intent failed scenario-family admission",
        ) from exc
    coordinates = _coordinates(request)
    rows = compile_coordinate_selections(
        family=request.family,
        spec=request.experiment,
        coordinates=coordinates,
        limits=request.limits,
    )
    descriptors = _admitted_descriptors(
        request,
        apparatus_manifests,
        participant_manifests,
    )
    plan_id = derive_identity("trial-plan", _plan_intent(request, coordinates))
    visit_indices = _visit_indices(len(coordinates), coordinate_partitions)
    entries = {}
    cleanup_plans = {}
    used_control_ids: set[str] = set()
    canonical_failure: CompilationFailure | None = None
    for coordinate_index in visit_indices:
        coordinate = coordinates[coordinate_index]
        row = rows[coordinate_index]
        try:
            _validate_selected_scenario(request, row, coordinate)
            identity_projection = {
                "plan_id": plan_id,
                "coordinate": coordinate_projection(coordinate),
            }
            entry_id = derive_identity("trial-entry", identity_projection)
            run_id = derive_identity("archival-run", identity_projection)
            cleanup_id = derive_identity(
                "trial-cleanup",
                {
                    "plan_entry_id": entry_id,
                    "run_id": run_id,
                    "template": request.execution_authority.cleanup.model_dump(mode="json"),
                },
            )
            cleanup = request.execution_authority.cleanup.bind(
                plan_id=cleanup_id,
                plan_entry_id=entry_id,
                run_id=run_id,
            )
            bindings = _entry_bindings(request, row, coordinate, descriptors)
            if len(row.draws) > request.limits.max_draws_per_entry:
                raise _fail(
                    "draw-limit-exceeded",
                    "/run_plan/stochastic_controls",
                    "entry random draws exceed the compilation limit",
                )
            entry = seal_admitted_trial_entry(
                plan_entry_id=entry_id,
                coordinate=coordinate,
                run_id=run_id,
                selections=_selection_records(row),
                bindings=bindings,
                stochastic_draws=list(row.draws),
                apparatus=request.apparatus,
                execution_controls=AdmittedExecutionControlModel(
                    attempt_timeout_seconds=request.execution_authority.attempt_timeout_seconds,
                    on_timeout=request.execution_authority.on_timeout,
                    on_cancellation=request.execution_authority.on_cancellation,
                    cleanup_plan_ref=cleanup_id,
                ),
                instantiation_provenance=AdmittedInstantiationProvenanceModel(
                    plan_id=plan_id,
                    plan_entry_id=entry_id,
                    run_id=run_id,
                    scenario_family_id=request.family.name,
                ),
            )
        except CompilationFailure as failure:
            candidate_failure = failure
        except (TypeError, ValueError) as exc:
            candidate_failure = _fail(
                "entry-invalid",
                "/entries/" + (coordinate.replicate_id or "coordinate"),
                "a trial entry failed closed construction",
            )
            candidate_failure.__cause__ = exc
        else:
            used_control_ids.update(draw.control_id for draw in row.draws)
            entries[entry_id] = entry
            cleanup_plans[cleanup_id] = cleanup
            continue
        if canonical_failure is None or (
            candidate_failure.address,
            candidate_failure.code,
            candidate_failure.safe_message,
        ) < (
            canonical_failure.address,
            canonical_failure.code,
            canonical_failure.safe_message,
        ):
            canonical_failure = candidate_failure
    if canonical_failure is not None:
        raise canonical_failure
    controls = {
        control.control_id: control
        for control in request.experiment.run_plan.stochastic_controls
        if control.control_id in used_control_ids
    }
    plan = seal_admitted_trial_plan(
        plan_id=plan_id,
        profiles=admitted_profiles(),
        input_refs=request.input_refs,
        stochastic_controls=controls,
        cleanup_plans=cleanup_plans,
        entries=entries,
        admission=AdmittedTrialPlanAdmissionModel(
            admitted_at_stage="admitted-sealed",
            entry_count=len(entries),
        ),
    )
    if len(canonical_json_bytes(plan.model_dump(mode="json"))) > request.limits.max_plan_bytes:
        raise _fail(
            "plan-byte-limit-exceeded",
            "",
            "canonical admitted plan bytes exceed the compilation limit",
        )
    return plan


def compile_admitted_trial_plan(
    request: TrialCompilationRequest,
    *,
    coordinate_partitions: tuple[tuple[int, ...], ...] | None = None,
) -> TrialCompilationResult:
    """Compile one request atomically, returning a sealed plan or safe diagnostics."""

    try:
        plan = _compile(request, coordinate_partitions)
    except CompilationFailure as failure:
        return TrialCompilationResult(plan=None, diagnostics=(_diagnostic(failure),))
    except (TypeError, ValueError) as exc:
        failure = _fail(
            "input-invalid",
            "",
            "trial compilation input failed closed validation",
        )
        failure.__cause__ = exc
        return TrialCompilationResult(plan=None, diagnostics=(_diagnostic(failure),))
    return TrialCompilationResult(plan=plan, diagnostics=())


__all__ = ["compile_admitted_trial_plan"]
