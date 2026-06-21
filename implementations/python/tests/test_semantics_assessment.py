"""Shared assessment-pipeline semantic tests (SEM-206).

Exercises the name-level source of truth for the SDL scoring chain
``condition bindings -> metrics -> evaluations -> TLOs -> goals``:
reference resolution, score aggregation, dependency-role derivation, and
fail-closed issue reporting.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from aces.core.sdl.parser import parse_sdl_file
from aces.core.semantics.assessment import (
    ASSESSMENT_DEPENDENCY_ROLES,
    AssessmentDependencyRole,
    AssessmentPipelineAnalysis,
    AssessmentResourceKind,
    analyze_assessment_pipeline,
    partition_assessment_dependencies,
)


def _metric(*, condition: object = None, max_score: object = 10) -> SimpleNamespace:
    return SimpleNamespace(condition=condition, max_score=max_score)


def _evaluation(metrics: list[str], *, absolute: object = None, percentage: object = None) -> SimpleNamespace:
    return SimpleNamespace(
        metrics=list(metrics),
        min_score=SimpleNamespace(absolute=absolute, percentage=percentage),
    )


def _tlo(evaluation: str) -> SimpleNamespace:
    return SimpleNamespace(evaluation=evaluation)


def _goal(tlos: list[str]) -> SimpleNamespace:
    return SimpleNamespace(tlos=list(tlos))


def _is_var(value: object) -> bool:
    return isinstance(value, str) and value.startswith("${") and value.endswith("}")


def _write_assessment_scenario(path: Path, *, namespace: str = "") -> None:
    prefix = f"{namespace}." if namespace else ""
    path.write_text(
        f"""
name: {namespace or "assessment"}
version: 1.0.0
conditions:
  {prefix}health:
    command: /bin/true
    interval: 15
metrics:
  {prefix}health-metric:
    type: conditional
    condition: {prefix}health
    max-score: 7
  {prefix}manual-metric:
    type: manual
    max-score: 5
evaluations:
  {prefix}readiness:
    metrics: [{prefix}health-metric, {prefix}manual-metric]
    min-score:
      absolute: 10
tlos:
  {prefix}ready-tlo:
    evaluation: {prefix}readiness
goals:
  {prefix}ready-goal:
    tlos: [{prefix}ready-tlo]
""",
        encoding="utf-8",
    )


def _write_importing_root(path: Path, imported_name: str, *, namespace: str) -> None:
    path.write_text(
        f"""
name: root
imports:
  - path: {imported_name}
    namespace: {namespace}
    version: 1.0.0
""",
        encoding="utf-8",
    )


def _assessment_analysis_from_file(path: Path) -> AssessmentPipelineAnalysis:
    scenario = parse_sdl_file(path)
    return analyze_assessment_pipeline(
        conditions_by_name=scenario.conditions,
        metrics_by_name=scenario.metrics,
        evaluations_by_name=scenario.evaluations,
        tlos_by_name=scenario.tlos,
        goals_by_name=scenario.goals,
    )


def _assessment_reference_signature(analysis: AssessmentPipelineAnalysis) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            ref.raw,
            ref.source_kind,
            ref.source_name,
            ref.target_kind,
            ref.target_name,
            ref.dependency_roles,
            ref.namespace_path,
        )
        for ref in analysis.references
    )


def _strip_shared(name: str) -> str:
    return name.removeprefix("shared.")


class TestAssessmentPipelineSemantics:
    def test_well_formed_pipeline_normalizes_references_and_dependencies(self) -> None:
        analysis = analyze_assessment_pipeline(
            conditions_by_name={"health": object()},
            metrics_by_name={
                "m1": _metric(condition="health", max_score=10),
                "m2": _metric(condition=None, max_score=5),
            },
            evaluations_by_name={"e1": _evaluation(["m1", "m2"], absolute=12)},
            tlos_by_name={"t1": _tlo("e1")},
            goals_by_name={"g1": _goal(["t1"])},
        )

        assert not analysis.has_issues
        assert [
            (ref.source_kind, ref.source_name, ref.target_kind, ref.target_name) for ref in analysis.references
        ] == [
            (AssessmentResourceKind.METRIC, "m1", AssessmentResourceKind.CONDITION, "health"),
            (AssessmentResourceKind.EVALUATION, "e1", AssessmentResourceKind.METRIC, "m1"),
            (AssessmentResourceKind.EVALUATION, "e1", AssessmentResourceKind.METRIC, "m2"),
            (AssessmentResourceKind.TLO, "t1", AssessmentResourceKind.EVALUATION, "e1"),
            (AssessmentResourceKind.GOAL, "g1", AssessmentResourceKind.TLO, "t1"),
        ]
        for ref in analysis.references:
            assert ref.dependency_roles == ASSESSMENT_DEPENDENCY_ROLES

        m1_deps = analysis.dependencies_for(AssessmentResourceKind.METRIC, "m1")
        assert m1_deps.ordering_names == ("health",)
        assert m1_deps.refresh_names == ("health",)
        assert analysis.dependencies_for(AssessmentResourceKind.METRIC, "m2").ordering_names == ()
        assert analysis.dependencies_for(AssessmentResourceKind.EVALUATION, "e1").ordering_names == ("m1", "m2")
        assert analysis.dependencies_for(AssessmentResourceKind.TLO, "t1").ordering_names == ("e1",)
        assert analysis.dependencies_for(AssessmentResourceKind.GOAL, "g1").refresh_names == ("t1",)
        assert analysis.evaluation_metric_totals == {"e1": 15}

    def test_metric_with_unresolved_condition_is_skipped(self) -> None:
        analysis = analyze_assessment_pipeline(
            conditions_by_name={},
            metrics_by_name={"m1": _metric(condition="${cond}", max_score=10)},
            evaluations_by_name={},
            tlos_by_name={},
            goals_by_name={},
            is_unresolved=_is_var,
        )

        assert not analysis.has_issues
        assert analysis.references == ()
        assert analysis.dependencies_for(AssessmentResourceKind.METRIC, "m1").ordering_names == ()

    def test_undeclared_condition_reference_is_reported(self) -> None:
        analysis = analyze_assessment_pipeline(
            conditions_by_name={},
            metrics_by_name={"m1": _metric(condition="missing", max_score=10)},
            evaluations_by_name={},
            tlos_by_name={},
            goals_by_name={},
        )

        assert [issue.code for issue in analysis.issues] == ["metric.condition-undeclared"]
        issue = analysis.issues[0]
        assert issue.resource_kind == AssessmentResourceKind.METRIC
        assert issue.resource_name == "m1"
        assert issue.ref == "missing"
        assert analysis.references == ()
        assert analysis.dependencies_for(AssessmentResourceKind.METRIC, "m1").ordering_names == ()

    def test_condition_referenced_by_multiple_metrics_is_reported_per_extra(self) -> None:
        analysis = analyze_assessment_pipeline(
            conditions_by_name={"c": object()},
            metrics_by_name={
                "m1": _metric(condition="c"),
                "m2": _metric(condition="c"),
                "m3": _metric(condition="c"),
            },
            evaluations_by_name={},
            tlos_by_name={},
            goals_by_name={},
        )

        shared = analysis.issues_of_code("metric.condition-multiply-scored")
        assert len(shared) == 2
        assert all(
            issue.resource_kind == AssessmentResourceKind.CONDITION and issue.resource_name == "c" for issue in shared
        )

    def test_evaluation_undeclared_metric_is_reported(self) -> None:
        analysis = analyze_assessment_pipeline(
            conditions_by_name={},
            metrics_by_name={},
            evaluations_by_name={"e1": _evaluation(["nope"])},
            tlos_by_name={},
            goals_by_name={},
        )

        issues = analysis.issues_of_code("evaluation.metric-undeclared")
        assert len(issues) == 1
        assert issues[0].resource_name == "e1"
        assert issues[0].ref == "nope"

    def test_evaluation_absolute_min_score_over_metric_total_is_reported(self) -> None:
        analysis = analyze_assessment_pipeline(
            conditions_by_name={},
            metrics_by_name={"m1": _metric(condition=None, max_score=10)},
            evaluations_by_name={"e1": _evaluation(["m1"], absolute=100)},
            tlos_by_name={},
            goals_by_name={},
        )
        issue = analysis.issues_of_code("evaluation.min-score-exceeds-metric-total")[0]
        assert issue.resource_name == "e1"
        assert issue.observed == 100
        assert issue.limit == 10

        ok = analyze_assessment_pipeline(
            conditions_by_name={},
            metrics_by_name={"m1": _metric(condition=None, max_score=10)},
            evaluations_by_name={"e1": _evaluation(["m1"], percentage=75)},
            tlos_by_name={},
            goals_by_name={},
        )
        assert not ok.issues_of_code("evaluation.min-score-exceeds-metric-total")

    def test_evaluation_metric_total_unknown_with_var_or_nonint_max_score(self) -> None:
        analysis = analyze_assessment_pipeline(
            conditions_by_name={},
            metrics_by_name={"m1": _metric(condition=None, max_score="${max}")},
            evaluations_by_name={"e1": _evaluation(["m1", "${m}"], absolute=999)},
            tlos_by_name={},
            goals_by_name={},
            is_unresolved=_is_var,
        )

        assert analysis.evaluation_metric_totals == {"e1": None}
        assert not analysis.issues_of_code("evaluation.min-score-exceeds-metric-total")

    def test_tlo_and_goal_undeclared_references_are_reported(self) -> None:
        analysis = analyze_assessment_pipeline(
            conditions_by_name={},
            metrics_by_name={},
            evaluations_by_name={},
            tlos_by_name={"t1": _tlo("missing-eval")},
            goals_by_name={"g1": _goal(["missing-tlo"])},
        )

        codes = {issue.code for issue in analysis.issues}
        assert "tlo.evaluation-undeclared" in codes
        assert "goal.tlo-undeclared" in codes

    def test_issue_iteration_follows_pipeline_order(self) -> None:
        analysis = analyze_assessment_pipeline(
            conditions_by_name={},
            metrics_by_name={"m1": _metric(condition="missing")},
            evaluations_by_name={"e1": _evaluation(["nope"])},
            tlos_by_name={"t1": _tlo("missing-eval")},
            goals_by_name={"g1": _goal(["missing-tlo"])},
        )
        assert [issue.code for issue in analysis.issues] == [
            "metric.condition-undeclared",
            "evaluation.metric-undeclared",
            "tlo.evaluation-undeclared",
            "goal.tlo-undeclared",
        ]

    def test_composition_ready_invariant_layout_variation_preserves_normalized_references_and_aggregation(
        self, tmp_path: Path
    ) -> None:
        flat = tmp_path / "flat.yaml"
        imported = tmp_path / "assessment-module.yaml"
        root = tmp_path / "root.yaml"
        _write_assessment_scenario(flat, namespace="shared")
        _write_assessment_scenario(imported)
        _write_importing_root(root, imported.name, namespace="shared")

        flat_analysis = _assessment_analysis_from_file(flat)
        imported_analysis = _assessment_analysis_from_file(root)

        assert not flat_analysis.has_issues
        assert not imported_analysis.has_issues
        assert _assessment_reference_signature(imported_analysis) == _assessment_reference_signature(flat_analysis)
        assert (
            imported_analysis.evaluation_metric_totals
            == flat_analysis.evaluation_metric_totals
            == {"shared.readiness": 12}
        )

    def test_composition_ready_invariant_module_expansion_occurs_before_assessment_analysis(
        self, tmp_path: Path
    ) -> None:
        imported = tmp_path / "assessment-module.yaml"
        root = tmp_path / "root.yaml"
        _write_assessment_scenario(imported)
        _write_importing_root(root, imported.name, namespace="shared")

        analysis = _assessment_analysis_from_file(root)

        assert not analysis.has_issues
        assert [ref.raw for ref in analysis.references] == [
            "shared.health",
            "shared.health-metric",
            "shared.manual-metric",
            "shared.readiness",
            "shared.ready-tlo",
        ]

    def test_composition_ready_invariant_namespace_extends_identity_without_changing_kinds_roles_or_aggregation(
        self, tmp_path: Path
    ) -> None:
        plain = tmp_path / "plain.yaml"
        namespaced = tmp_path / "namespaced.yaml"
        _write_assessment_scenario(plain)
        _write_assessment_scenario(namespaced, namespace="shared")

        plain_analysis = _assessment_analysis_from_file(plain)
        namespaced_analysis = _assessment_analysis_from_file(namespaced)

        assert [
            (ref.source_kind, ref.target_kind, ref.dependency_roles, ref.namespace_path)
            for ref in namespaced_analysis.references
        ] == [
            (ref.source_kind, ref.target_kind, ref.dependency_roles, ref.namespace_path)
            for ref in plain_analysis.references
        ]
        assert [
            (_strip_shared(ref.source_name), _strip_shared(ref.target_name)) for ref in namespaced_analysis.references
        ] == [(ref.source_name, ref.target_name) for ref in plain_analysis.references]
        assert list(namespaced_analysis.evaluation_metric_totals.values()) == list(
            plain_analysis.evaluation_metric_totals.values()
        )


class TestAssessmentDependencyPartition:
    def test_partition_returns_ordering_and_refresh_copies(self) -> None:
        ordering, refresh = partition_assessment_dependencies(["a", "b"])
        assert ordering == ("a", "b")
        assert refresh == ("a", "b")
        assert AssessmentDependencyRole.ORDERING in ASSESSMENT_DEPENDENCY_ROLES
        assert AssessmentDependencyRole.REFRESH in ASSESSMENT_DEPENDENCY_ROLES

    def test_partition_handles_empty_inputs(self) -> None:
        assert partition_assessment_dependencies([]) == ((), ())
        assert partition_assessment_dependencies(()) == ((), ())
