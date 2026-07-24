"""SemanticValidator adapter for authored historical state."""

from ..semantics.historical_state import HistoricalStateAnalysisContext, analyze_historical_state


class _HistoricalStateMixin:
    def _verify_historical_state(self) -> None:
        issues = analyze_historical_state(
            HistoricalStateAnalysisContext(
                historical_baselines=self._s.historical_baselines,
                entities=self._s.entities,
                agents=self._s.agents,
                accounts=self._s.accounts,
                nodes=self._s.nodes,
                content=self._s.content,
                propositions=self._s.propositions,
                assertions=self._s.assertions,
                observation_boundaries=self._s.observation_boundaries,
                deployment_tenants=self._s.deployment_tenants,
                deployment_cells=self._s.deployment_cells,
                relationships=self._s.relationships,
                is_unresolved=self._is_unresolved_var,
            )
        )
        for issue in issues:
            self._err(f"[{issue.code}] {issue.message}")
