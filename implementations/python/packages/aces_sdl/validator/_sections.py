"""SemanticValidator _SectionsMixin (split from validator.py).

Part of the SemanticValidator mixin composition; see __init__.py.
"""

from pydantic import BaseModel

from .._base import extract_variable_name
from ..entities import flatten_entities
from ..explicitness import classify_scenario_explicitness
from ..scenario import Scenario
from ..semantics.assessment import AssessmentIssue, analyze_assessment_pipeline
from ._support import _topological_sort


class _SectionsMixin:
    def _verify_variables(self) -> None:
        defined = set(self._s.variables.keys())

        def visit(value: object, path: str) -> None:
            if isinstance(value, BaseModel):
                for field_name in value.__class__.model_fields:
                    if isinstance(value, Scenario) and field_name == "variables":
                        continue
                    child = getattr(value, field_name)
                    child_path = f"{path}.{field_name}" if path else field_name
                    visit(child, child_path)
                return

            if isinstance(value, dict):
                for key, child in value.items():
                    child_path = f"{path}.{key}" if path else str(key)
                    visit(child, child_path)
                return

            if isinstance(value, list):
                for index, child in enumerate(value):
                    child_path = f"{path}[{index}]"
                    visit(child, child_path)
                return

            if self._is_unresolved_var(value):
                variable_name = extract_variable_name(value)
                if variable_name and variable_name not in defined:
                    self._err(f"Undefined variable '{variable_name}' referenced at '{path}'")

        visit(self._s, "")

    def _verify_explicitness(self) -> None:
        result = classify_scenario_explicitness(self._s)
        self._s._set_explicitness(result.records)
        for error in result.errors:
            self._err(error)

    def _all_named_elements(self) -> set[str]:
        """Collect all named element keys across all scenario sections."""
        return set(self._named_ref_index().keys())

    def _all_targetable_elements(self) -> set[str]:
        """Collect named elements that can serve as objective targets."""
        return set(self._named_ref_index(targetable=True).keys())

    def _verify_features(self) -> None:
        # Check vulnerability references
        for name, feat in self._s.features.items():
            for vuln_name in feat.vulnerabilities:
                if self._is_unresolved_var(vuln_name):
                    continue
                if vuln_name not in self._s.vulnerabilities:
                    self._err(f"Feature '{name}' references undefined vulnerability '{vuln_name}'")

        # Check dependency references and detect cycles
        dep_graph: dict[str, list[str]] = {}
        for name, feat in self._s.features.items():
            dep_graph[name] = []
            for dep in feat.dependencies:
                if self._is_unresolved_var(dep):
                    continue
                if dep not in self._s.features:
                    self._err(f"Feature '{name}' depends on undefined feature '{dep}'")
                else:
                    dep_graph[name].append(dep)

        if dep_graph and _topological_sort(dep_graph) is None:
            self._err("Feature dependency graph contains a cycle")

    def _verify_conditions(self) -> None:
        # Individual condition validation is handled by Pydantic model_validator.
        # This pass checks for consistency with the broader scenario.
        pass

    def _verify_vulnerabilities(self) -> None:
        # CWE format validation is handled by the Pydantic field_validator.
        pass

    def _verify_assessment_pipeline(self) -> None:
        # The condition -> metric -> evaluation -> TLO -> goal scoring chain.
        # Reference, aggregation, and dependency-role semantics live in
        # ``aces_sdl.semantics.assessment`` (SEM-206); this pass renders the
        # machine-readable issues it reports as authoring errors.
        analysis = analyze_assessment_pipeline(
            conditions_by_name=self._s.conditions,
            metrics_by_name=self._s.metrics,
            evaluations_by_name=self._s.evaluations,
            tlos_by_name=self._s.tlos,
            goals_by_name=self._s.goals,
            is_unresolved=self._is_unresolved_var,
        )
        for issue in analysis.issues:
            self._err(self._format_assessment_issue(issue))

    @staticmethod
    def _format_assessment_issue(issue: AssessmentIssue) -> str:
        name, ref = issue.resource_name, issue.ref
        if issue.code == "metric.condition-undeclared":
            return f"Metric '{name}' references undefined condition '{ref}'"
        if issue.code == "metric.condition-multiply-scored":
            return f"Condition '{name}' is referenced by multiple metrics"
        if issue.code == "evaluation.metric-undeclared":
            return f"Evaluation '{name}' references undefined metric '{ref}'"
        if issue.code == "evaluation.min-score-exceeds-metric-total":
            return (
                f"Evaluation '{name}' absolute min-score "
                f"({issue.observed}) exceeds sum of "
                f"metric max-scores ({issue.limit})"
            )
        if issue.code == "tlo.evaluation-undeclared":
            return f"TLO '{name}' references undefined evaluation '{ref}'"
        if issue.code == "goal.tlo-undeclared":
            return f"Goal '{name}' references undefined TLO '{ref}'"
        raise AssertionError(f"unhandled assessment-pipeline issue code: {issue.code}")

    def _verify_entities(self) -> None:
        flat = flatten_entities(self._s.entities)

        def check_entity(name: str, entity: "Entity") -> None:
            for tlo_name in entity.tlos:
                if self._is_unresolved_var(tlo_name):
                    continue
                if tlo_name not in self._s.tlos:
                    self._err(f"Entity '{name}' references undefined TLO '{tlo_name}'")
            for vuln_name in entity.vulnerabilities:
                if self._is_unresolved_var(vuln_name):
                    continue
                if vuln_name not in self._s.vulnerabilities:
                    self._err(f"Entity '{name}' references undefined vulnerability '{vuln_name}'")
            for event_name in entity.events:
                if self._is_unresolved_var(event_name):
                    continue
                if event_name not in self._s.events:
                    self._err(f"Entity '{name}' references undefined event '{event_name}'")

        for name, entity in flat.items():
            check_entity(name, entity)

    def _verify_injects(self) -> None:
        flat_names = self._all_entity_names()

        for name, inject in self._s.injects.items():
            if (
                inject.from_entity
                and not self._is_unresolved_var(inject.from_entity)
                and inject.from_entity not in flat_names
            ):
                self._err(f"Inject '{name}' from_entity '{inject.from_entity}' is not a defined entity")
            for to_name in inject.to_entities:
                if self._is_unresolved_var(to_name):
                    continue
                if to_name not in flat_names:
                    self._err(f"Inject '{name}' to_entity '{to_name}' is not a defined entity")
            for tlo_name in inject.tlos:
                if self._is_unresolved_var(tlo_name):
                    continue
                if tlo_name not in self._s.tlos:
                    self._err(f"Inject '{name}' references undefined TLO '{tlo_name}'")

    def _verify_events(self) -> None:
        for name, event in self._s.events.items():
            for cond_name in event.conditions:
                if self._is_unresolved_var(cond_name):
                    continue
                if cond_name not in self._s.conditions:
                    self._err(f"Event '{name}' references undefined condition '{cond_name}'")
            for inj_name in event.injects:
                if self._is_unresolved_var(inj_name):
                    continue
                if inj_name not in self._s.injects:
                    self._err(f"Event '{name}' references undefined inject '{inj_name}'")

    def _verify_scripts(self) -> None:
        for name, script in self._s.scripts.items():
            for event_name in script.events:
                if self._is_unresolved_var(event_name):
                    continue
                if event_name not in self._s.events:
                    self._err(f"Script '{name}' references undefined event '{event_name}'")

    def _verify_stories(self) -> None:
        for name, story in self._s.stories.items():
            for script_name in story.scripts:
                if self._is_unresolved_var(script_name):
                    continue
                if script_name not in self._s.scripts:
                    self._err(f"Story '{name}' references undefined script '{script_name}'")

    def _verify_roles(self) -> None:
        flat_names = self._all_entity_names()

        for node_name, node in self._s.nodes.items():
            for role_name, role in node.roles.items():
                for entity_ref in role.entities:
                    if self._is_unresolved_var(entity_ref):
                        continue
                    if entity_ref not in flat_names:
                        self._err(f"Node '{node_name}' role '{role_name}' references undefined entity '{entity_ref}'")
