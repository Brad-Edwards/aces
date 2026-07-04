"""SemanticValidator _SectionsMixin (split from validator.py).

Part of the SemanticValidator mixin composition; see __init__.py.
"""

from pydantic import BaseModel

from .._base import VARIABLE_TOKEN_RE
from ..entities import flatten_entities
from ..explicitness import classify_scenario_explicitness
from ..scenario import Scenario
from ..semantics.assessment import AssessmentIssue, analyze_assessment_pipeline
from ._support import _topological_sort

# Renders an assessment-pipeline issue (machine-readable code from
# ``aces_sdl.semantics.assessment``) into the authoring-error string. Keyed by
# issue code so a new code is a new line here rather than a new conditional.
_ASSESSMENT_ISSUE_RENDERERS = {
    "metric.condition-undeclared": (lambda i: f"Metric '{i.resource_name}' references undefined condition '{i.ref}'"),
    "metric.condition-multiply-scored": (lambda i: f"Condition '{i.resource_name}' is referenced by multiple metrics"),
    "evaluation.metric-undeclared": (lambda i: f"Evaluation '{i.resource_name}' references undefined metric '{i.ref}'"),
    "evaluation.min-score-exceeds-metric-total": (
        lambda i: (
            f"Evaluation '{i.resource_name}' absolute min-score "
            f"({i.observed}) exceeds sum of "
            f"metric max-scores ({i.limit})"
        )
    ),
    "tlo.evaluation-undeclared": (lambda i: f"TLO '{i.resource_name}' references undefined evaluation '{i.ref}'"),
    "goal.tlo-undeclared": (lambda i: f"Goal '{i.resource_name}' references undefined TLO '{i.ref}'"),
}


class _SectionsMixin:
    def _verify_variables(self) -> None:
        defined = set(self._s.variables.keys())
        self._check_variable_refs(self._s, "", defined)

    def _check_variable_refs(self, value: object, path: str, defined: set[str]) -> None:
        if isinstance(value, BaseModel):
            self._check_model_variable_refs(value, path, defined)
        elif isinstance(value, dict):
            for key, child in value.items():
                self._check_variable_refs(child, f"{path}.{key}" if path else str(key), defined)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self._check_variable_refs(child, f"{path}[{index}]", defined)
        elif isinstance(value, str):
            for variable_name in dict.fromkeys(VARIABLE_TOKEN_RE.findall(value)):
                if variable_name not in defined:
                    self._err(f"Undefined variable '{variable_name}' referenced at '{path}'")

    def _check_model_variable_refs(self, value: BaseModel, path: str, defined: set[str]) -> None:
        for field_name in value.__class__.model_fields:
            if isinstance(value, Scenario) and field_name == "variables":
                continue
            child = getattr(value, field_name)
            child_path = f"{path}.{field_name}" if path else field_name
            self._check_variable_refs(child, child_path, defined)

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
        self._verify_feature_vulnerability_refs()
        self._verify_feature_dependency_cycles()

    def _verify_feature_vulnerability_refs(self) -> None:
        for name, feat in self._s.features.items():
            for vuln_name in feat.vulnerabilities:
                if self._is_unresolved_var(vuln_name):
                    continue
                if vuln_name not in self._s.vulnerabilities:
                    self._err(f"Feature '{name}' references undefined vulnerability '{vuln_name}'")

    def _verify_feature_dependency_cycles(self) -> None:
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
        renderer = _ASSESSMENT_ISSUE_RENDERERS.get(issue.code)
        if renderer is None:
            raise AssertionError(f"unhandled assessment-pipeline issue code: {issue.code}")
        return renderer(issue)

    def _verify_entities(self) -> None:
        for name, entity in flatten_entities(self._s.entities).items():
            self._verify_entity_refs(name, entity)

    def _verify_entity_refs(self, name: str, entity: object) -> None:
        self._verify_membership_refs(
            entity.tlos, self._s.tlos, lambda ref: f"Entity '{name}' references undefined TLO '{ref}'"
        )
        self._verify_membership_refs(
            entity.vulnerabilities,
            self._s.vulnerabilities,
            lambda ref: f"Entity '{name}' references undefined vulnerability '{ref}'",
        )
        self._verify_membership_refs(
            entity.events, self._s.events, lambda ref: f"Entity '{name}' references undefined event '{ref}'"
        )

    def _verify_injects(self) -> None:
        flat_names = self._all_entity_names()
        for name, inject in self._s.injects.items():
            self._verify_inject_refs(name, inject, flat_names)

    def _verify_inject_refs(self, name: str, inject: object, flat_names: set[str]) -> None:
        if (
            inject.from_entity
            and not self._is_unresolved_var(inject.from_entity)
            and inject.from_entity not in flat_names
        ):
            self._err(f"Inject '{name}' from_entity '{inject.from_entity}' is not a defined entity")
        self._verify_membership_refs(
            inject.to_entities, flat_names, lambda ref: f"Inject '{name}' to_entity '{ref}' is not a defined entity"
        )
        self._verify_membership_refs(
            inject.tlos, self._s.tlos, lambda ref: f"Inject '{name}' references undefined TLO '{ref}'"
        )

    def _verify_events(self) -> None:
        for name, event in self._s.events.items():
            self._verify_event_refs(name, event)

    def _verify_event_refs(self, name: str, event: object) -> None:
        self._verify_membership_refs(
            event.conditions, self._s.conditions, lambda ref: f"Event '{name}' references undefined condition '{ref}'"
        )
        self._verify_membership_refs(
            event.injects, self._s.injects, lambda ref: f"Event '{name}' references undefined inject '{ref}'"
        )

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
