"""SemanticValidator _WorkflowVerifyMixin (split from validator.py).

Part of the SemanticValidator mixin composition; see __init__.py.
"""

from collections import defaultdict

from ..orchestration import WorkflowStepType
from ..semantics.workflow import branch_closure
from ._support import _topological_sort


class _WorkflowVerifyMixin:
    def _verify_workflows(self) -> None:
        workflow_call_graph: dict[str, set[str]] = {workflow_name: set() for workflow_name in self._s.workflows}
        workflow_compensation_graph: dict[str, set[str]] = {workflow_name: set() for workflow_name in self._s.workflows}
        compensation_target_workflows: set[str] = set()
        workflows_with_compensation_steps: set[str] = set()
        for workflow_name, workflow in self._s.workflows.items():
            if not self._is_unresolved_var(workflow.start) and workflow.start not in workflow.steps:
                self._err(f"Workflow '{workflow_name}' start step '{workflow.start}' is not defined")

            graph: dict[str, list[str]] = {step_name: [] for step_name in workflow.steps}
            predicate_step_refs: dict[str, list[str]] = {}
            join_targets: dict[str, list[str]] = defaultdict(list)

            for step_name, step in workflow.steps.items():
                if "." in step_name:
                    self._err(
                        f"Workflow '{workflow_name}' step '{step_name}' cannot "
                        "contain '.' because objective windows use "
                        "'<workflow>.<step>' syntax"
                    )

                if step.type == WorkflowStepType.OBJECTIVE:
                    if not self._is_unresolved_var(step.objective) and step.objective not in self._s.objectives:
                        self._err(
                            f"Workflow '{workflow_name}' step '{step_name}' "
                            f"references undefined objective '{step.objective}'"
                        )
                    self._verify_step_terminator_and_compensation(
                        workflow_name=workflow_name,
                        step_name=step_name,
                        step=step,
                        workflow=workflow,
                        graph=graph,
                        workflow_compensation_graph=workflow_compensation_graph,
                        compensation_target_workflows=compensation_target_workflows,
                        workflows_with_compensation_steps=workflows_with_compensation_steps,
                    )

                elif step.type == WorkflowStepType.DECISION:
                    predicate_step_refs[step_name] = self._validate_workflow_predicate(
                        workflow_name,
                        step_name,
                        step.when,
                        workflow.steps,
                    )

                    for branch_label, branch_ref in (
                        ("then", step.then_step),
                        ("else", step.else_step),
                    ):
                        resolved = self._validate_workflow_target_ref(
                            workflow_name,
                            step_name,
                            branch_label,
                            branch_ref,
                            workflow.steps,
                        )
                        if resolved is not None:
                            graph[step_name].append(resolved)

                elif step.type == WorkflowStepType.SWITCH:
                    aggregated_refs: list[str] = []
                    for case_index, case in enumerate(step.cases):
                        aggregated_refs.extend(
                            self._validate_workflow_predicate(
                                workflow_name,
                                f"{step_name}.case[{case_index}]",
                                case.when,
                                workflow.steps,
                            )
                        )
                        resolved = self._validate_workflow_target_ref(
                            workflow_name,
                            step_name,
                            f"case[{case_index}] next",
                            case.next_step,
                            workflow.steps,
                        )
                        if resolved is not None:
                            graph[step_name].append(resolved)
                    predicate_step_refs[step_name] = aggregated_refs
                    resolved_default = self._validate_workflow_target_ref(
                        workflow_name,
                        step_name,
                        "default",
                        step.default_step,
                        workflow.steps,
                    )
                    if resolved_default is not None:
                        graph[step_name].append(resolved_default)

                elif step.type == WorkflowStepType.PARALLEL:
                    for branch_ref in step.branches:
                        resolved = self._validate_workflow_target_ref(
                            workflow_name,
                            step_name,
                            "branch",
                            branch_ref,
                            workflow.steps,
                        )
                        if resolved is not None:
                            graph[step_name].append(resolved)
                    resolved_join = self._validate_workflow_target_ref(
                        workflow_name,
                        step_name,
                        "join",
                        step.join,
                        workflow.steps,
                    )
                    if resolved_join is not None:
                        join_targets[resolved_join].append(step_name)
                    resolved_failure = self._validate_workflow_target_ref(
                        workflow_name,
                        step_name,
                        "on-failure",
                        step.on_failure,
                        workflow.steps,
                    )
                    if resolved_failure is not None:
                        graph[step_name].append(resolved_failure)

                elif step.type == WorkflowStepType.JOIN:
                    resolved = self._validate_workflow_target_ref(
                        workflow_name,
                        step_name,
                        "next",
                        step.next,
                        workflow.steps,
                    )
                    if resolved is not None:
                        graph[step_name].append(resolved)

                elif step.type == WorkflowStepType.RETRY:
                    if not self._is_unresolved_var(step.objective) and step.objective not in self._s.objectives:
                        self._err(
                            f"Workflow '{workflow_name}' step '{step_name}' "
                            f"references undefined objective '{step.objective}'"
                        )
                    for field_name, target in (
                        ("on-success", step.on_success),
                        ("on-exhausted", step.on_exhausted),
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

                elif step.type == WorkflowStepType.CALL:
                    if not self._is_unresolved_var(step.workflow) and step.workflow not in self._s.workflows:
                        self._err(
                            f"Workflow '{workflow_name}' step '{step_name}' "
                            f"references undefined workflow '{step.workflow}'"
                        )
                    elif not self._is_unresolved_var(step.workflow):
                        workflow_call_graph.setdefault(workflow_name, set()).add(step.workflow)
                    self._verify_step_terminator_and_compensation(
                        workflow_name=workflow_name,
                        step_name=step_name,
                        step=step,
                        workflow=workflow,
                        graph=graph,
                        workflow_compensation_graph=workflow_compensation_graph,
                        compensation_target_workflows=compensation_target_workflows,
                        workflows_with_compensation_steps=workflows_with_compensation_steps,
                    )

                elif step.type == WorkflowStepType.END:
                    graph[step_name] = []

                if step_name not in graph:
                    graph[step_name] = []

            for join_step, sources in join_targets.items():
                if self._is_unresolved_var(join_step):
                    continue
                join_def = workflow.steps.get(join_step)
                if join_def is not None and join_def.type != WorkflowStepType.JOIN:
                    self._err(
                        f"Workflow '{workflow_name}' step '{join_step}' is used "
                        "as a parallel join but is not a join step"
                    )
                if len(sources) > 1:
                    self._err(
                        f"Workflow '{workflow_name}' join step '{join_step}' may only be targeted by one parallel step"
                    )

            for step_name, step in workflow.steps.items():
                if step.type != WorkflowStepType.JOIN:
                    continue
                sources = join_targets.get(step_name, [])
                if not sources:
                    self._err(
                        f"Workflow '{workflow_name}' join step '{step_name}' is not referenced by any parallel step"
                    )

            if graph and _topological_sort(graph) is None:
                self._err(f"Workflow '{workflow_name}' graph contains a cycle")

            if self._is_unresolved_var(workflow.start) or workflow.start not in workflow.steps:
                continue

            reachable: set[str] = set()
            stack = [workflow.start]
            while stack:
                current = stack.pop()
                if current in reachable:
                    continue
                reachable.add(current)
                stack.extend(graph.get(current, []))

            unreachable = sorted(set(workflow.steps) - reachable)
            if unreachable:
                self._err(f"Workflow '{workflow_name}' contains unreachable steps: " + ", ".join(unreachable))

            predecessors: dict[str, set[str]] = {step_name: set() for step_name in reachable}
            for source, edges in graph.items():
                if source not in reachable:
                    continue
                for target in edges:
                    if target in reachable:
                        predecessors[target].add(source)

            for _step_name, step in workflow.steps.items():
                if step.type != WorkflowStepType.PARALLEL:
                    continue
                if self._is_unresolved_var(step.join) or step.join not in workflow.steps or step.join not in reachable:
                    continue
                allowed_predecessors = branch_closure(
                    graph,
                    branches=(branch for branch in step.branches if branch in reachable and branch in workflow.steps),
                    join_step=step.join,
                )
                foreign_predecessors = sorted(
                    predecessor
                    for predecessor in predecessors.get(step.join, set())
                    if predecessor not in allowed_predecessors
                )
                if foreign_predecessors:
                    self._err(
                        f"Workflow '{workflow_name}' join step '{step.join}' "
                        "may only be entered from the owning parallel's branch "
                        "closure; unexpected predecessors: " + ", ".join(foreign_predecessors)
                    )

            available_memo: dict[str, set[str]] = {}
            branch_memo: dict[tuple[str, str], set[str]] = {}

            for step_name, refs in predicate_step_refs.items():
                if step_name not in reachable:
                    continue
                available_before = self._available_step_state_before(
                    step_name,
                    workflow.steps,
                    graph,
                    predecessors,
                    workflow.start,
                    join_targets,
                    available_memo=available_memo,
                    branch_memo=branch_memo,
                    visiting=set(),
                )
                for ref_name in refs:
                    if self._is_unresolved_var(ref_name):
                        continue
                    if ref_name not in available_before:
                        self._err(
                            f"Workflow '{workflow_name}' step '{step_name}' "
                            f"references step state '{ref_name}' that is not "
                            "guaranteed to be known before this predicate"
                        )

            for step_name, step in workflow.steps.items():
                if step.type != WorkflowStepType.PARALLEL:
                    continue
                if self._is_unresolved_var(step.join) or step.join not in workflow.steps:
                    continue
                for branch_ref in step.branches:
                    if self._is_unresolved_var(branch_ref) or branch_ref not in workflow.steps:
                        continue
                    if not self._all_paths_reach_join(
                        branch_ref,
                        step.join,
                        graph,
                        memo={},
                        visiting=set(),
                    ):
                        self._err(
                            f"Workflow '{workflow_name}' parallel step "
                            f"'{step_name}' requires every explicit branch path "
                            f"from '{branch_ref}' to converge on join "
                            f"'{step.join}'"
                        )

        if (
            workflow_call_graph
            and _topological_sort(
                {
                    workflow_name: sorted(callee for callee in callees if callee in workflow_call_graph)
                    for workflow_name, callees in workflow_call_graph.items()
                }
            )
            is None
        ):
            self._err("Workflow call graph contains a cycle")

        combined_workflow_graph = {
            workflow_name: sorted(
                workflow_call_graph.get(workflow_name, set()) | workflow_compensation_graph.get(workflow_name, set())
            )
            for workflow_name in self._s.workflows
        }
        if combined_workflow_graph and _topological_sort(combined_workflow_graph) is None:
            self._err("Combined workflow call/compensation graph contains a cycle")

        for workflow_name in sorted(compensation_target_workflows):
            if workflow_name in workflows_with_compensation_steps:
                self._err(
                    f"Workflow '{workflow_name}' cannot be used as a compensation "
                    "workflow because it also declares compensate-with steps"
                )
