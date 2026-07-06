"""Objective-success resource-kind tag (SEM-206).

Per ADR-073 the OCR-inherited SDL scoring chain
(``metric -> evaluation -> TLO -> goal``) was removed from the SDL. Graded
scoring, reward, and evaluation outputs live in the experiment/evaluator plane
(ADR-055/064/069), not in authored SDL.

What remains here is the resource-kind qualifier that objective success
references carry. Objective success references observable state only, so
``CONDITION`` is the sole member; the enum is retained as the kind-qualifier
seam so a future ADR that admits another observable-state carrier adds a member
here rather than reviving the removed scoring sections. Per ADR-015 this helper
lives with the SDL package and has no processor-runtime dependencies; per
ADR-016 it is part of the realized artifact set for SEM-206.
"""

from __future__ import annotations

from enum import Enum


class AssessmentResourceKind(str, Enum):
    """Resource kinds an objective's success may reference (post ADR-073)."""

    CONDITION = "condition"
