"""Shared result types for deterministic live-activity analysis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class LiveActivityIssue:
    code: str
    message: str


def activity_issue(code: str, message: str) -> LiveActivityIssue:
    return LiveActivityIssue(code=code, message=message)


__all__ = ["LiveActivityIssue", "activity_issue"]
