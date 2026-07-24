"""SemanticValidator adapter for deterministic live activity."""

from ..semantics.live_activity import analyze_live_activity


class _LiveActivityMixin:
    def _verify_live_activity(self) -> None:
        for issue in analyze_live_activity(self._s, is_unresolved=self._is_unresolved_var):
            self._err(f"[{issue.code}] {issue.message}")
