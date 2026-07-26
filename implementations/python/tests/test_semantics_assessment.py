"""Assessment resource-kind tests (SEM-206, post ADR-073).

Per ADR-073 the OCR-inherited SDL scoring chain
(``metric -> evaluation -> TLO -> goal``) was removed from the language. Graded
scoring, reward, and evaluation outputs live in the experiment/evaluator plane
(ADR-055/064/069), not in authored SDL. What remains in
``raes.semantics.assessment`` is the resource-kind qualifier that objective
success references carry: objective success composes backend-neutral assertions,
so ``ASSERTION`` is the sole member.

These tests pin that reduced surface so a future revival of the removed scoring
sections is a visible, deliberate change rather than an accident.
"""

from __future__ import annotations

from enum import Enum

from raes.semantics import assessment as compat_assessment
from raes.semantics.assessment import AssessmentResourceKind


class TestAssessmentResourceKind:
    def test_assertion_is_the_only_member(self) -> None:
        assert [kind.name for kind in AssessmentResourceKind] == ["ASSERTION"]

    def test_assertion_value(self) -> None:
        assert AssessmentResourceKind.ASSERTION.value == "assertion"

    def test_is_str_enum(self) -> None:
        assert issubclass(AssessmentResourceKind, str)
        assert issubclass(AssessmentResourceKind, Enum)

    def test_removed_scoring_symbols_are_gone(self) -> None:
        # The OCR scoring pipeline surface (ADR-073) must not reappear.
        for removed in (
            "Metric",
            "Evaluation",
            "TLO",
            "Goal",
            "analyze_assessment_pipeline",
            "AssessmentReference",
            "AssessmentIssue",
            "AssessmentPipelineAnalysis",
            "AssessmentResourceDependencies",
            "AssessmentDependencyRole",
            "ASSESSMENT_DEPENDENCY_ROLES",
            "partition_assessment_dependencies",
        ):
            assert not hasattr(compat_assessment, removed)

    def test_removed_kinds_are_gone(self) -> None:
        for removed in ("METRIC", "EVALUATION", "TLO", "GOAL"):
            assert removed not in AssessmentResourceKind.__members__
