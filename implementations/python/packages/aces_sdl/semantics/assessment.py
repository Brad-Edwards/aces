"""Objective-success resource-kind tag (SEM-206).

Per ADR-073 the OCR-inherited SDL scoring chain
(``metric -> evaluation -> TLO -> goal``) was removed from the SDL. Graded
scoring, reward, and evaluation outputs live in the experiment/evaluator plane
(ADR-055/064/069), not in authored SDL.

What remains here is the resource-kind qualifier that objective success
references carry. Objective success composes assertions over propositions;
executable conditions are probe realizations and are not success resources.
"""

from __future__ import annotations

from enum import Enum


class AssessmentResourceKind(str, Enum):
    """Resource kinds an objective's success may reference (post ADR-073)."""

    ASSERTION = "assertion"
