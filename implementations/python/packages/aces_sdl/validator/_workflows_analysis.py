"""SemanticValidator _WorkflowAnalysisMixin (split from validator.py).

Part of the SemanticValidator mixin composition; see __init__.py.
"""

from ..orchestration import Workflow, WorkflowPredicate, WorkflowStep, WorkflowStepType
from ..semantics.workflow import workflow_step_semantic_contract


class _WorkflowAnalysisMixin:
    def _validate_workflow_predicate(
        self,
        workflow_name: str,
        step_name: str,
        predicate: WorkflowPredicate,
        workflow_steps: dict[str, WorkflowStep],
    ) -> list[str]:
        """Validate all references within a workflow predicate."""
        step_refs: list[str] = []
        predicate_sections = (
            ("condition", predicate.conditions, self._s.conditions),
            ("metric", predicate.metrics, self._s.metrics),
            ("evaluation", predicate.evaluations, self._s.evaluations),
            ("TLO", predicate.tlos, self._s.tlos),
            ("goal", predicate.goals, self._s.goals),
            ("objective", predicate.objectives, self._s.objectives),
        )
        for label, refs, section in predicate_sections:
            for ref in refs:
                if self._is_unresolved_var(ref):
                    continue
                if ref not in section:
                    self._err(
                        f"Workflow '{workflow_name}' step "
                        f"'{step_name}' references undefined "
                        f"{label} '{ref}' in predicate"
                    )
        for step_state in predicate.steps:
            if self._is_unresolved_var(step_state.step):
                continue
            if step_state.step not in workflow_steps:
                self._err(
                    f"Workflow '{workflow_name}' step '{step_name}' "
                    f"references undefined step state "
                    f"'{step_state.step}' in predicate"
                )
                continue
            if step_state.step == step_name:
                self._err(
                    f"Workflow '{workflow_name}' step '{step_name}' cannot reference its own state in a predicate"
                )
                continue
            ref_step = workflow_steps[step_state.step]
            contract = workflow_step_semantic_contract(ref_step.type.value)
            if not contract.state_observable:
                self._err(
                    f"Workflow '{workflow_name}' step '{step_name}' "
                    f"cannot reference non-executable step '{step_state.step}' "
                    "in a predicate"
                )
                continue
            invalid_outcomes = [
                outcome.value for outcome in step_state.outcomes if outcome.value not in contract.observable_outcomes
            ]
            if invalid_outcomes:
                allowed = ", ".join(contract.observable_outcomes)
                self._err(
                    f"Workflow '{workflow_name}' step '{step_name}' "
                    f"references step '{step_state.step}' with impossible "
                    f"outcomes {invalid_outcomes}; allowed outcomes are: {allowed}"
                )
                continue
            step_refs.append(step_state.step)
        return step_refs

    def _is_executable_workflow_step(self, step: WorkflowStep) -> bool:
        return workflow_step_semantic_contract(step.type.value).state_observable

    def _validate_workflow_target_ref(
        self,
        workflow_name: str,
        step_name: str,
        field_name: str,
        target: str,
        workflow_steps: dict[str, WorkflowStep],
    ) -> str | None:
        if not target:
            return None
        if self._is_unresolved_var(target):
            return None
        if target not in workflow_steps:
            self._err(f"Workflow '{workflow_name}' step '{step_name}' {field_name} step '{target}' is not defined")
            return None
        return target

    def _all_paths_reach_join(
        self,
        node: str,
        join: str,
        graph: dict[str, list[str]],
        *,
        memo: dict[str, bool],
        visiting: set[str],
    ) -> bool:
        if node == join:
            return True
        if node in memo:
            return memo[node]
        if node in visiting:
            return False

        visiting.add(node)
        successors = graph.get(node, [])
        if not successors:
            visiting.remove(node)
            memo[node] = False
            return False

        result = all(
            self._all_paths_reach_join(
                successor,
                join,
                graph,
                memo=memo,
                visiting=visiting,
            )
            for successor in successors
        )
        visiting.remove(node)
        memo[node] = result
        return result

    def _branch_guaranteed_states(
        self,
        node: str,
        join: str,
        graph: dict[str, list[str]],
        workflow_steps: dict[str, WorkflowStep],
        *,
        memo: dict[tuple[str, str], set[str]],
        visiting: set[tuple[str, str]],
    ) -> set[str]:
        if node == join:
            return set()

        key = (node, join)
        if key in memo:
            return set(memo[key])
        if key in visiting:
            return set()

        visiting.add(key)
        successors = graph.get(node, [])
        guaranteed_after: set[str] = set()
        if successors:
            successor_sets: list[set[str]] = []
            for successor in successors:
                if successor == join:
                    successor_sets.append(set())
                    continue
                if successor not in workflow_steps:
                    continue
                successor_sets.append(
                    self._branch_guaranteed_states(
                        successor,
                        join,
                        graph,
                        workflow_steps,
                        memo=memo,
                        visiting=visiting,
                    )
                )
            if successor_sets:
                guaranteed_after = set.intersection(*successor_sets)

        result = set(guaranteed_after)
        step = workflow_steps[node]
        if self._is_executable_workflow_step(step):
            result.add(node)

        visiting.remove(key)
        memo[key] = set(result)
        return result

    def _edge_available_state(
        self,
        step_name: str,
        successor: str,
        workflow_steps: dict[str, WorkflowStep],
        graph: dict[str, list[str]],
        predecessors: dict[str, set[str]],
        start: str,
        join_targets: dict[str, list[str]],
        *,
        available_memo: dict[str, set[str]],
        branch_memo: dict[tuple[str, str], set[str]],
        visiting: set[str],
    ) -> set[str]:
        available = self._available_step_state_before(
            step_name,
            workflow_steps,
            graph,
            predecessors,
            start,
            join_targets,
            available_memo=available_memo,
            branch_memo=branch_memo,
            visiting=visiting,
        )
        step = workflow_steps[step_name]
        if step.type in {
            WorkflowStepType.OBJECTIVE,
            WorkflowStepType.RETRY,
            WorkflowStepType.CALL,
        } or (step.type == WorkflowStepType.PARALLEL and step.on_failure and successor == step.on_failure):
            available.add(step_name)
        return available

    def _available_step_state_before(
        self,
        step_name: str,
        workflow_steps: dict[str, WorkflowStep],
        graph: dict[str, list[str]],
        predecessors: dict[str, set[str]],
        start: str,
        join_targets: dict[str, list[str]],
        *,
        available_memo: dict[str, set[str]],
        branch_memo: dict[tuple[str, str], set[str]],
        visiting: set[str],
    ) -> set[str]:
        if step_name in available_memo:
            return set(available_memo[step_name])
        if step_name in visiting:
            return set()

        visiting.add(step_name)
        step = workflow_steps[step_name]

        if step_name == start:
            result = set()
        elif step.type == WorkflowStepType.JOIN and join_targets.get(step_name):
            owner = join_targets[step_name][0]
            result = self._available_step_state_before(
                owner,
                workflow_steps,
                graph,
                predecessors,
                start,
                join_targets,
                available_memo=available_memo,
                branch_memo=branch_memo,
                visiting=visiting,
            )
            result.add(owner)
            owner_step = workflow_steps[owner]
            for branch in owner_step.branches:
                if branch not in workflow_steps:
                    continue
                result.update(
                    self._branch_guaranteed_states(
                        branch,
                        step_name,
                        graph,
                        workflow_steps,
                        memo=branch_memo,
                        visiting=set(),
                    )
                )
        else:
            incoming_states: list[set[str]] = []
            for predecessor in predecessors.get(step_name, set()):
                if predecessor not in workflow_steps:
                    continue
                incoming_states.append(
                    self._edge_available_state(
                        predecessor,
                        step_name,
                        workflow_steps,
                        graph,
                        predecessors,
                        start,
                        join_targets,
                        available_memo=available_memo,
                        branch_memo=branch_memo,
                        visiting=visiting,
                    )
                )
            result = set.intersection(*incoming_states) if incoming_states else set()

        visiting.remove(step_name)
        available_memo[step_name] = set(result)
        return result

    def _verify_step_terminator_and_compensation(
        self,
        *,
        workflow_name: str,
        step_name: str,
        step: WorkflowStep,
        workflow: Workflow,
        graph: dict[str, list[str]],
        workflow_compensation_graph: dict[str, set[str]],
        compensation_target_workflows: set[str],
        workflows_with_compensation_steps: set[str],
    ) -> None:
        """Shared validation for `on-success`/`on-failure` and `compensate_with`.

        OBJECTIVE and CALL workflow steps both carry the same terminator and
        compensation-handling shape, so this method centralizes the
        appended-edge bookkeeping and undefined-workflow error reporting
        for both call sites.
        """
        for field_name, target in (
            ("on-success", step.on_success),
            ("on-failure", step.on_failure),
        ):
            resolved = self._validate_workflow_target_ref(
                workflow_name,
                step_name,
                field_name,
                target,
                workflow.steps,
            )
            if resolved is not None:
                graph[step_name].append(resolved)
        if step.compensate_with:
            workflows_with_compensation_steps.add(workflow_name)
            if not self._is_unresolved_var(step.compensate_with) and step.compensate_with not in self._s.workflows:
                self._err(
                    f"Workflow '{workflow_name}' step '{step_name}' "
                    "references undefined compensation workflow "
                    f"'{step.compensate_with}'"
                )
            elif not self._is_unresolved_var(step.compensate_with):
                workflow_compensation_graph.setdefault(workflow_name, set()).add(step.compensate_with)
                compensation_target_workflows.add(step.compensate_with)
