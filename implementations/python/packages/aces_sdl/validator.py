"""Semantic validation for SDL scenarios.

Goes beyond Pydantic structural checks to enforce cross-reference
integrity, dependency cycle detection, IP/CIDR consistency, and
domain-specific rules. Collects all errors rather than failing on
the first one.
"""

from collections import defaultdict, deque
from ipaddress import ip_address, ip_network

from pydantic import BaseModel

from ._base import extract_variable_name, is_variable_ref
from ._errors import SDLValidationError
from ._runtime_mail_semantics import (
    collect_qualified_mail_refs,
    verify_relationship_mail_access,
    verify_runtime_mail_services,
)
from .entities import flatten_entities
from .infrastructure import SimpleProperties
from .nodes import MAX_NODE_NAME_LENGTH, NodeType
from .orchestration import Workflow, WorkflowPredicate, WorkflowStep, WorkflowStepType
from .runtime_database import DatabaseObjectType
from .runtime_ssh_server import SshMatchCriterionKind
from .scenario import Scenario
from .semantics.assessment import AssessmentIssue, analyze_assessment_pipeline
from .semantics.objective_semantics import (
    AssessmentResourceCatalog,
    ObjectiveIssue,
    WindowResourceCatalog,
    analyze_objective_semantics,
)
from .semantics.participant_behavior import (
    ParticipantBehaviorIssue,
    analyze_participant_behavior,
)
from .semantics.participant_outcome import (
    ParticipantOutcomeIssue,
    analyze_participant_outcome_interpretations,
)
from .semantics.workflow import branch_closure, workflow_step_semantic_contract

# Common ref-path prefix used by qualified runtime/service refs (e.g.
# ``nodes.vm.services.http``, ``nodes.vm.runtime.applications.webapp``).
_NODES_PREFIX = "nodes."

# Renders an objective-semantics issue (machine-readable code from
# ``aces_sdl.semantics.objective_semantics``) into the authoring-error string
# the SDL surface has always used. Keyed by issue code so a new code is a new
# line here rather than a new branch in a growing conditional.
_OBJECTIVE_ISSUE_RENDERERS = {
    "objective.actor-agent-undeclared": (
        lambda i: f"Objective '{i.objective_name}' references undefined agent '{i.ref}'"
    ),
    "objective.actor-entity-undeclared": (
        lambda i: f"Objective '{i.objective_name}' references undefined entity '{i.ref}'"
    ),
    "objective.action-not-declared": (
        lambda i: f"Objective '{i.objective_name}' action '{i.ref}' is not declared by agent '{i.actor_name}'"
    ),
    "objective.target-unresolvable": (
        lambda i: f"Objective '{i.objective_name}' target '{i.ref}' does not reference any defined targetable element"
    ),
    "objective.target-ambiguous": (
        lambda i: f"Objective '{i.objective_name}' target '{i.ref}' is ambiguous; use one of: {', '.join(i.candidates)}"
    ),
    "objective.success-condition-undeclared": (
        lambda i: f"Objective '{i.objective_name}' references undefined condition '{i.ref}' in success criteria"
    ),
    "objective.success-metric-undeclared": (
        lambda i: f"Objective '{i.objective_name}' references undefined metric '{i.ref}' in success criteria"
    ),
    "objective.success-evaluation-undeclared": (
        lambda i: f"Objective '{i.objective_name}' references undefined evaluation '{i.ref}' in success criteria"
    ),
    "objective.success-tlo-undeclared": (
        lambda i: f"Objective '{i.objective_name}' references undefined TLO '{i.ref}' in success criteria"
    ),
    "objective.success-goal-undeclared": (
        lambda i: f"Objective '{i.objective_name}' references undefined goal '{i.ref}' in success criteria"
    ),
    "objective.window.story-unbound": (
        lambda i: f"Objective '{i.objective_name}' references undefined story '{i.ref}' in window"
    ),
    "objective.window.script-unbound": (
        lambda i: f"Objective '{i.objective_name}' references undefined script '{i.ref}' in window"
    ),
    "objective.window.script-outside-window-stories": (
        lambda i: f"Objective '{i.objective_name}' window script '{i.ref}' is not included by the referenced stories"
    ),
    "objective.window.event-unbound": (
        lambda i: f"Objective '{i.objective_name}' references undefined event '{i.ref}' in window"
    ),
    "objective.window.event-outside-window-scripts": (
        lambda i: f"Objective '{i.objective_name}' window event '{i.ref}' is not included by the referenced scripts"
    ),
    "objective.window.workflow-unbound": (
        lambda i: f"Objective '{i.objective_name}' references undefined workflow '{i.ref}' in window"
    ),
    "objective.window.step-requires-workflow-window": (
        lambda i: f"Objective '{i.objective_name}' window steps require at least one referenced workflow"
    ),
    "objective.window.step-invalid-format": (
        lambda i: f"Objective '{i.objective_name}' window step '{i.ref}' must use '<workflow>.<step>' syntax"
    ),
    "objective.window.step-workflow-unbound": (
        lambda i: (
            f"Objective '{i.objective_name}' window step '{i.ref}' references undefined workflow '{i.workflow_name}'"
        )
    ),
    "objective.window.step-workflow-outside-window": (
        lambda i: f"Objective '{i.objective_name}' window step '{i.ref}' is not part of the referenced workflows"
    ),
    "objective.window.step-unbound": (
        lambda i: f"Objective '{i.objective_name}' window step '{i.ref}' references undefined step '{i.step_name}'"
    ),
    "objective.dependency-undeclared": (
        lambda i: f"Objective '{i.objective_name}' depends on undefined objective '{i.ref}'"
    ),
    "objective.dependency-cycle": lambda _i: "Objective dependency graph contains a cycle",
}

_PARTICIPANT_BEHAVIOR_ISSUE_RENDERERS = {
    "participant.action-contract-unbound": (
        lambda i: f"Agent '{i.participant_name}' action '{i.ref}' does not reference a declared action_contract"
    ),
    "participant.observation-boundary-unbound": (
        lambda i: (
            f"Agent '{i.participant_name}' observation_boundary '{i.ref}' "
            "does not reference a declared observation_boundary"
        )
    ),
    "participant.interaction-action-unbound": (
        lambda i: (
            f"Action contract '{i.action_name}' interaction related_action '{i.ref}' "
            "does not reference a declared action_contract"
        )
    ),
    "participant.view-rule-ref-unbound": (
        lambda i: (
            f"Observation boundary '{i.boundary_name}' view_rule information_ref '{i.ref}' "
            "is not declared by observable_refs, hidden_refs, or evidence_refs"
        )
    ),
    "participant.view-rule-evidence-unbound": (
        lambda i: (
            f"Observation boundary '{i.boundary_name}' view_rule evidence_ref '{i.ref}' "
            "is not declared by evidence_refs"
        )
    ),
    "participant.view-transition-ref-unbound": (
        lambda i: (
            f"Observation boundary '{i.boundary_name}' view_transition '{i.transition_id}' "
            f"information_ref '{i.ref}' is not declared by observable_refs, hidden_refs, or evidence_refs"
        )
    ),
    "participant.view-transition-evidence-unbound": (
        lambda i: (
            f"Observation boundary '{i.boundary_name}' view_transition '{i.transition_id}' "
            f"evidence_ref '{i.ref}' is not declared by evidence_refs"
        )
    ),
}

_PARTICIPANT_OUTCOME_ISSUE_RENDERERS = {
    "participant.outcome.source-action-unbound": (
        lambda i: f"Outcome interpretation rule '{i.rule_name}' source '{i.ref}' references undefined action contract"
    ),
    "participant.outcome.source-objective-unbound": (
        lambda i: f"Outcome interpretation rule '{i.rule_name}' source '{i.ref}' references undefined objective"
    ),
    "participant.outcome.source-workflow-unbound": (
        lambda i: f"Outcome interpretation rule '{i.rule_name}' source '{i.ref}' references undefined workflow"
    ),
    "participant.outcome.source-evaluation-unbound": (
        lambda i: f"Outcome interpretation rule '{i.rule_name}' source '{i.ref}' references undefined evaluation"
    ),
    "participant.outcome.target-objective-unbound": (
        lambda i: f"Outcome interpretation rule '{i.rule_name}' target '{i.ref}' references undefined objective"
    ),
    "participant.outcome.target-workflow-unbound": (
        lambda i: f"Outcome interpretation rule '{i.rule_name}' target '{i.ref}' references undefined workflow"
    ),
    "participant.outcome.target-evaluation-unbound": (
        lambda i: f"Outcome interpretation rule '{i.rule_name}' target '{i.ref}' references undefined evaluation"
    ),
}


def _topological_sort(graph: dict[str, list[str]]) -> list[str] | None:
    """Return topological order or None if a cycle exists."""
    in_degree: dict[str, int] = defaultdict(int)
    for node in graph:
        in_degree.setdefault(node, 0)
    for deps in graph.values():
        for dep in deps:
            in_degree[dep] += 1

    queue = deque(n for n, d in in_degree.items() if d == 0)
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for dep in graph.get(node, []):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)

    return order if len(order) == len(in_degree) else None


class SemanticValidator:
    """Validates a Scenario beyond structural Pydantic checks.

    Call ``validate()`` to run all passes. Raises ``SDLValidationError``
    with all collected errors if any pass fails.
    """

    def __init__(self, scenario: Scenario) -> None:
        self._s = scenario
        self._errors: list[str] = []
        self._warnings: list[str] = []

    def _err(self, msg: str) -> None:
        self._errors.append(msg)

    def _warn(self, msg: str) -> None:
        self._warnings.append(msg)

    def _is_unresolved_var(self, value: object) -> bool:
        return is_variable_ref(value)

    def _node_type(self, node_name: str) -> NodeType | None:
        node = self._s.nodes.get(node_name)
        return node.type if node is not None else None

    def _is_switch_node(self, node_name: str) -> bool:
        return self._node_type(node_name) == NodeType.SWITCH

    def _is_vm_node(self, node_name: str) -> bool:
        return self._node_type(node_name) == NodeType.VM

    def _all_entity_names(self) -> set[str]:
        return set(flatten_entities(self._s.entities).keys())

    def _qualified_service_refs(self) -> set[str]:
        refs: set[str] = set()
        for node_name, node in self._s.nodes.items():
            for service in node.services:
                if service.name:
                    refs.add(f"nodes.{node_name}.services.{service.name}")
        return refs

    def _qualified_runtime_refs(self) -> set[str]:
        """Qualified refs for node-scoped runtime inventories.

        These let a top-level relationship endpoint resolve to a runtime
        application surface, database service / logical database, DNS service
        / zone / RRset, identity-authority object, or security-monitoring
        manager object. This keeps
        runtime-observed logical state targetable without promoting those
        records to top-level SDL sections.
        """
        refs: set[str] = set()
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None:
                continue
            refs.update(self._qualified_service_listener_refs(node_name))
            refs.update(self._qualified_application_refs(node_name))
            refs.update(self._qualified_database_refs(node_name))
            refs.update(self._qualified_dns_refs(node_name))
            refs.update(self._qualified_identity_refs(node_name))
            refs.update(self._qualified_network_sensor_refs(node_name))
            refs.update(self._qualified_network_detection_refs(node_name))
            refs.update(self._qualified_security_monitoring_refs(node_name))
        refs.update(collect_qualified_mail_refs(self._s))
        return refs

    def _qualified_application_refs(self, node_name: str) -> set[str]:
        runtime = self._s.nodes[node_name].runtime
        return {f"nodes.{node_name}.runtime.applications.{app.application_id}" for app in runtime.applications}

    def _qualified_service_listener_refs(self, node_name: str) -> set[str]:
        runtime = self._s.nodes[node_name].runtime
        return {
            f"nodes.{node_name}.runtime.service_listeners.{listener.listener_id}"
            for listener in runtime.service_listeners
        }

    def _qualified_database_refs(self, node_name: str) -> set[str]:
        refs: set[str] = set()
        runtime = self._s.nodes[node_name].runtime
        for dbsvc in runtime.database_services:
            base = f"nodes.{node_name}.runtime.database_services.{dbsvc.database_service_id}"
            refs.add(base)
            refs.update(f"{base}.databases.{database.database_id}" for database in dbsvc.databases)
        return refs

    def _qualified_dns_refs(self, node_name: str) -> set[str]:
        refs: set[str] = set()
        runtime = self._s.nodes[node_name].runtime
        for dns_service in runtime.dns_services:
            base = f"nodes.{node_name}.runtime.dns_services.{dns_service.dns_service_id}"
            refs.add(base)
            for zone in dns_service.zones:
                zone_base = f"{base}.zones.{zone.zone_id}"
                refs.add(zone_base)
                refs.update(f"{zone_base}.rrsets.{rrset.rrset_id}" for rrset in zone.rrsets)
        return refs

    def _qualified_identity_refs(self, node_name: str) -> set[str]:
        refs: set[str] = set()
        runtime = self._s.nodes[node_name].runtime
        for authority in runtime.identity_authorities:
            base = f"nodes.{node_name}.runtime.identity_authorities.{authority.authority_id}"
            refs.add(base)
            refs.update(f"{base}.services.{service.service_id}" for service in authority.services)
            refs.update(f"{base}.subjects.{subject.subject_id}" for subject in authority.subjects)
            refs.update(f"{base}.policies.{policy.policy_id}" for policy in authority.policies)
            refs.update(
                f"{base}.relationships.{relationship.relationship_id}" for relationship in authority.relationships
            )
        return refs

    def _qualified_network_sensor_refs(self, node_name: str) -> set[str]:
        refs: set[str] = set()
        runtime = self._s.nodes[node_name].runtime
        for sensor in runtime.network_sensors:
            refs.add(f"nodes.{node_name}.runtime.network_sensors.{sensor.sensor_id}")
        return refs

    def _qualified_network_detection_refs(self, node_name: str) -> set[str]:
        refs: set[str] = set()
        runtime = self._s.nodes[node_name].runtime
        for engine in runtime.network_detection_engines:
            base = f"nodes.{node_name}.runtime.network_detection_engines.{engine.engine_id}"
            refs.add(base)
            for collection_name, id_field in (
                ("rule_sources", "source_id"),
                ("network_sets", "set_id"),
                ("output_streams", "stream_id"),
                ("control_channels", "channel_id"),
            ):
                refs.update(
                    f"{base}.{collection_name}.{getattr(item, id_field)}" for item in getattr(engine, collection_name)
                )
        return refs

    def _qualified_security_monitoring_refs(self, node_name: str) -> set[str]:
        refs: set[str] = set()
        runtime = self._s.nodes[node_name].runtime
        for manager in runtime.security_monitoring_managers:
            base = f"nodes.{node_name}.runtime.security_monitoring_managers.{manager.manager_id}"
            refs.add(base)
            for collection_name, id_field in (
                ("listeners", "listener_id"),
                ("components", "component_id"),
                ("agents", "agent_id"),
                ("agent_groups", "group_id"),
                ("content_sets", "content_id"),
                ("settings", "setting_id"),
            ):
                refs.update(
                    f"{base}.{collection_name}.{getattr(item, id_field)}" for item in getattr(manager, collection_name)
                )
        return refs

    def _qualified_acl_refs(self) -> set[str]:
        refs: set[str] = set()
        for infra_name, infra in self._s.infrastructure.items():
            for acl in infra.acls:
                if acl.name:
                    refs.add(f"infrastructure.{infra_name}.acls.{acl.name}")
        return refs

    def _workflow_step_refs(self) -> set[str]:
        refs: set[str] = set()
        for workflow_name, workflow in self._s.workflows.items():
            for step_name in workflow.steps:
                refs.add(f"{workflow_name}.{step_name}")
        return refs

    def _named_ref_index(self, *, targetable: bool = False) -> dict[str, set[str]]:
        """Build the alias map for generic relationship/objective refs.

        Bare refs stay available for most top-level sections when they are
        unambiguous. Qualified refs are always accepted for top-level sections,
        and are required for infrastructure entries because those keys
        intentionally mirror node names.
        """
        index: dict[str, set[str]] = defaultdict(set)
        self._populate_named_ref_index(index)
        if not targetable:
            return {alias: set(candidates) for alias, candidates in index.items()}
        return self._filter_targetable_aliases(index)

    _NAMED_REF_TOP_LEVEL_SECTIONS = (
        ("nodes", True),
        ("features", True),
        ("conditions", True),
        ("vulnerabilities", True),
        ("infrastructure", False),
        ("metrics", True),
        ("evaluations", True),
        ("tlos", True),
        ("goals", True),
        ("content", True),
        ("accounts", True),
        ("agents", True),
        ("action_contracts", True),
        ("observation_boundaries", True),
        ("objectives", True),
        ("workflows", True),
        ("relationships", True),
        ("variables", True),
        ("injects", True),
        ("events", True),
        ("scripts", True),
        ("stories", True),
    )

    _TARGETABLE_DISALLOWED_PREFIXES = (
        "variables.",
        "objectives.",
        "workflows.",
    )

    def _populate_named_ref_index(self, index: dict[str, set[str]]) -> None:
        self._add_top_level_section_aliases(index)
        self._add_entity_aliases(index)
        self._add_content_item_aliases(index)
        self._add_qualified_aliases(index)

    def _add_top_level_section_aliases(self, index: dict[str, set[str]]) -> None:
        for section_name, allow_bare in self._NAMED_REF_TOP_LEVEL_SECTIONS:
            for name in getattr(self._s, section_name):
                canonical = f"{section_name}.{name}"
                index[canonical].add(canonical)
                if allow_bare:
                    index[name].add(canonical)

    def _add_entity_aliases(self, index: dict[str, set[str]]) -> None:
        for entity_name in self._all_entity_names():
            canonical = f"entities.{entity_name}"
            index[canonical].add(canonical)
            index[entity_name].add(canonical)

    def _add_content_item_aliases(self, index: dict[str, set[str]]) -> None:
        for content_name, content in self._s.content.items():
            for item in content.items:
                if not item.name:
                    continue
                canonical = f"content.{content_name}.items.{item.name}"
                index[canonical].add(canonical)
                index[item.name].add(canonical)

    def _add_qualified_aliases(self, index: dict[str, set[str]]) -> None:
        for qualified_refs in (
            self._qualified_service_refs(),
            self._qualified_acl_refs(),
            self._qualified_runtime_refs(),
        ):
            for ref in qualified_refs:
                index[ref].add(ref)

    def _filter_targetable_aliases(self, index: dict[str, set[str]]) -> dict[str, set[str]]:
        filtered: dict[str, set[str]] = {}
        for alias, candidates in index.items():
            keep = {
                candidate for candidate in candidates if not candidate.startswith(self._TARGETABLE_DISALLOWED_PREFIXES)
            }
            if keep:
                filtered[alias] = keep
        return filtered

    def _operating_scope_ref_index(self) -> dict[str, set[str]]:
        """Build the alias map for ACT-601 ``Agent.operating_scope``.

        ADR-020 §2 defines operating scope as the declarative boundary for
        where the participant may act or observe — concretely subnets,
        hosts, services, and content (and content items). The split here
        mirrors the pre-existing scope-validation patterns:

        - hosts come from ``nodes.*`` but only VM nodes (matches
          ``initial_knowledge.hosts``).
        - subnets come from ``infrastructure.*`` but only switch-backed
          entries (matches ``allowed_subnets``).
        - services come from declared services on VM nodes.
        - content references stay open across content sections and items.

        Non-spatial, non-resource elements (conditions, metrics, accounts,
        relationships, objectives, …) are not scope boundaries even though
        they appear in the generic targetable index.
        """
        index: dict[str, set[str]] = defaultdict(set)

        # Hosts: VM nodes only. Both bare (`vm`) and qualified (`nodes.vm`)
        # aliases are accepted. Switch nodes go through the subnets path,
        # never the host path.
        for node_name, node in self._s.nodes.items():
            if node.type != NodeType.VM:
                continue
            canonical = f"nodes.{node_name}"
            index[node_name].add(canonical)
            index[canonical].add(canonical)

        # Subnets: switch-backed infrastructure only. Both bare and
        # qualified aliases. VM-backed infrastructure entries (which
        # mirror VM nodes' names) go through the host path's `nodes.*`
        # alias, not here.
        for infra_name, _infra in self._s.infrastructure.items():
            if not self._is_switch_node(infra_name):
                continue
            canonical = f"infrastructure.{infra_name}"
            index[infra_name].add(canonical)
            index[canonical].add(canonical)

        # Services: qualified `nodes.<vm>.services.<svc>` refs plus bare
        # service names. The service-ref helper only emits names declared
        # on VM nodes (a service on a switch is meaningless), so no extra
        # filtering is needed here.
        for ref in self._qualified_service_refs():
            index[ref].add(ref)
            tail = ref.rsplit(".", 1)[-1]
            if tail:
                index[tail].add(ref)

        # Content: sections and items keep the unrestricted aliasing from
        # the targetable index; ADR-020 does not split content by sub-type.
        for content_name in self._s.content:
            canonical = f"content.{content_name}"
            index[content_name].add(canonical)
            index[canonical].add(canonical)
        for content_name, content in self._s.content.items():
            for item in content.items:
                if not item.name:
                    continue
                canonical = f"content.{content_name}.items.{item.name}"
                index[item.name].add(canonical)
                index[canonical].add(canonical)

        return {alias: set(candidates) for alias, candidates in index.items()}

    def _validate_operating_scope_ref(self, ref: str, *, owner_label: str) -> None:
        """Validate ``operating_scope`` against the spatial/resource index."""
        index = self._operating_scope_ref_index()
        candidates = index.get(ref)
        if not candidates:
            self._err(f"{owner_label} operating_scope '{ref}' does not reference any defined targetable element")
            return
        if len(candidates) > 1:
            choices = ", ".join(sorted(candidates))
            self._err(f"{owner_label} operating_scope '{ref}' is ambiguous; use one of: {choices}")

    def _validate_named_ref(
        self,
        ref: str,
        *,
        owner_label: str,
        ref_label: str,
        targetable: bool = False,
    ) -> None:
        """Validate a generic reference against the named-element index."""
        index = self._named_ref_index(targetable=targetable)
        candidates = index.get(ref)
        if not candidates:
            qualifier = "targetable " if targetable else ""
            self._err(f"{owner_label} {ref_label} '{ref}' does not reference any defined {qualifier}element")
            return

        if len(candidates) > 1:
            choices = ", ".join(sorted(candidates))
            self._err(f"{owner_label} {ref_label} '{ref}' is ambiguous; use one of: {choices}")

    def validate(self) -> None:
        """Run all validation passes and raise on errors."""
        self._errors = []
        self._warnings = []

        # OCR passes
        self._verify_nodes()
        self._verify_infrastructure()
        self._verify_runtime_network()
        self._verify_runtime_network_sensors()
        self._verify_runtime_network_detection_engines()
        self._verify_runtime_service_listeners()
        self._verify_runtime_application()
        self._verify_runtime_capability_overrides()
        self._verify_runtime_database_services()
        self._verify_runtime_dns_services()
        self._verify_runtime_ssh_servers()
        self._verify_runtime_service_manager_units()
        self._verify_runtime_identity_authorities()
        self._verify_runtime_file_services()
        self._verify_runtime_security_monitoring_managers()
        verify_runtime_mail_services(self)
        self._verify_features()
        self._verify_conditions()
        self._verify_vulnerabilities()
        self._verify_assessment_pipeline()
        self._verify_entities()
        self._verify_injects()
        self._verify_events()
        self._verify_scripts()
        self._verify_stories()
        self._verify_roles()

        # New section passes
        self._verify_content()
        self._verify_accounts()
        self._verify_relationships()
        self._verify_relationship_database_access()
        verify_relationship_mail_access(self)
        self._verify_agents()
        self._verify_participant_behavior()
        self._verify_objectives()
        self._verify_workflows()
        self._verify_participant_outcomes()
        self._verify_variables()
        self._collect_advisories()

        if self._errors:
            raise SDLValidationError(self._errors)

    @property
    def warnings(self) -> list[str]:
        """Return non-fatal advisories collected during validation."""
        return list(self._warnings)

    def _collect_advisories(self) -> None:
        self._warn_missing_vm_resources()

    def _warn_missing_vm_resources(self) -> None:
        for name, node in self._s.nodes.items():
            if node.type != NodeType.VM:
                continue
            if node.resources is None:
                self._warn(
                    f"Node '{name}' is a VM without 'resources'. This is "
                    "valid SDL, but may be undeployable unless the backend "
                    "supplies defaults."
                )

    # ------------------------------------------------------------------
    # OCR validation passes
    # ------------------------------------------------------------------

    def _verify_nodes(self) -> None:
        for name, node in self._s.nodes.items():
            if len(name) > MAX_NODE_NAME_LENGTH:
                self._err(f"Node '{name}' name exceeds 35 characters")

            for feat_name, role_name in node.features.items():
                if feat_name not in self._s.features:
                    self._err(f"Node '{name}' references undefined feature '{feat_name}'")
                if role_name and not self._is_unresolved_var(role_name) and role_name not in node.roles:
                    self._err(f"Node '{name}' feature '{feat_name}' references undefined role '{role_name}'")

            for cond_name, role_name in node.conditions.items():
                if cond_name not in self._s.conditions:
                    self._err(f"Node '{name}' references undefined condition '{cond_name}'")
                if role_name and not self._is_unresolved_var(role_name) and role_name not in node.roles:
                    self._err(f"Node '{name}' condition '{cond_name}' references undefined role '{role_name}'")

            for inj_name, role_name in node.injects.items():
                if inj_name not in self._s.injects:
                    self._err(f"Node '{name}' references undefined inject '{inj_name}'")
                if role_name and not self._is_unresolved_var(role_name) and role_name not in node.roles:
                    self._err(f"Node '{name}' inject '{inj_name}' references undefined role '{role_name}'")

            for vuln_name in node.vulnerabilities:
                if self._is_unresolved_var(vuln_name):
                    continue
                if vuln_name not in self._s.vulnerabilities:
                    self._err(f"Node '{name}' references undefined vulnerability '{vuln_name}'")

    def _verify_infrastructure(self) -> None:
        for name, infra in self._s.infrastructure.items():
            if name not in self._s.nodes:
                self._err(f"Infrastructure '{name}' does not match any defined node")

            for link in infra.links:
                if self._is_unresolved_var(link):
                    continue
                if link not in self._s.infrastructure:
                    self._err(f"Infrastructure '{name}' links to undefined '{link}'")
                elif not self._is_switch_node(link):
                    self._err(f"Infrastructure '{name}' link '{link}' must reference a switch/network entry")

            for dep in infra.dependencies:
                if self._is_unresolved_var(dep):
                    continue
                if dep not in self._s.infrastructure:
                    self._err(f"Infrastructure '{name}' depends on undefined '{dep}'")

            # Switch nodes cannot have count > 1
            if name in self._s.nodes:
                if self._s.nodes[name].type == NodeType.SWITCH and isinstance(infra.count, int) and infra.count > 1:
                    self._err(f"Switch node '{name}' cannot have count > 1")
                if (
                    self._s.nodes[name].type == NodeType.VM
                    and self._s.nodes[name].conditions
                    and isinstance(infra.count, int)
                    and infra.count > 1
                ):
                    self._err(f"Node '{name}' has conditions and cannot have count > 1")

            # Validate complex properties IP within linked CIDR
            if isinstance(infra.properties, list):
                for prop_entry in infra.properties:
                    for link_name, ip_str in prop_entry.items():
                        if self._is_unresolved_var(link_name):
                            continue
                        if link_name not in infra.links:
                            self._err(f"Infrastructure '{name}' property references unlinked node '{link_name}'")
                        if not self._is_switch_node(link_name):
                            self._err(
                                f"Infrastructure '{name}' property link "
                                f"'{link_name}' must reference a switch/network entry"
                            )
                            continue
                        # Check IP is within the linked node's CIDR
                        linked_infra = self._s.infrastructure.get(link_name)
                        if linked_infra is None:
                            continue
                        if not isinstance(linked_infra.properties, SimpleProperties):
                            self._err(
                                f"Infrastructure '{name}' property link "
                                f"'{link_name}' must reference a network with CIDR "
                                "properties"
                            )
                            continue
                        if self._is_unresolved_var(ip_str):
                            continue
                        if self._is_unresolved_var(linked_infra.properties.cidr):
                            continue
                        try:
                            net = ip_network(linked_infra.properties.cidr, strict=False)
                        except ValueError:
                            self._err(f"Infrastructure '{link_name}' has invalid CIDR {linked_infra.properties.cidr}")
                            continue
                        try:
                            addr = ip_address(ip_str)
                        except ValueError:
                            self._err(
                                f"Infrastructure '{name}' has invalid IP assignment '{ip_str}' for link '{link_name}'"
                            )
                            continue
                        if addr not in net:
                            self._err(
                                f"Infrastructure '{name}' IP {ip_str} "
                                f"not within '{link_name}' CIDR "
                                f"{linked_infra.properties.cidr}"
                            )

            # Validate ACL network references
            for acl in infra.acls:
                for ref in (acl.from_net, acl.to_net):
                    if self._is_unresolved_var(ref):
                        continue
                    if ref and ref not in self._s.infrastructure:
                        self._err(f"Infrastructure '{name}' ACL references undefined network '{ref}'")
                    elif ref and not self._is_switch_node(ref):
                        self._err(f"Infrastructure '{name}' ACL reference '{ref}' must point to a switch/network entry")

    def _verify_runtime_network(self) -> None:
        """Validate observed runtime network endpoints against declared topology.

        Each endpoint's ``network`` must resolve to a switch-backed
        infrastructure entry; concrete endpoint IPs and gateways are checked
        against the referenced network CIDR when one is declared (ADR-025).
        """
        for name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or runtime.network is None:
                continue
            for endpoint in runtime.network.endpoints:
                net = endpoint.network
                if self._is_unresolved_var(net):
                    continue
                if net not in self._s.infrastructure:
                    self._err(f"Node '{name}' runtime network endpoint references undefined network '{net}'")
                    continue
                if not self._is_switch_node(net):
                    self._err(
                        f"Node '{name}' runtime network endpoint network '{net}' must reference a switch/network entry"
                    )
                    continue
                self._verify_endpoint_addressing(name, net, endpoint)

    def _verify_endpoint_addressing(self, node_name: str, net: str, endpoint: object) -> None:
        infra = self._s.infrastructure.get(net)
        props = infra.properties if infra is not None else None
        if not isinstance(props, SimpleProperties):
            return
        cidr = props.cidr
        if not cidr or self._is_unresolved_var(cidr):
            return
        try:
            network = ip_network(cidr, strict=False)
        except ValueError:
            return
        for label in ("ip_address", "gateway"):
            value = getattr(endpoint, label, "")
            if not value or self._is_unresolved_var(value):
                continue
            try:
                addr = ip_address(value)
            except ValueError:
                continue  # malformed addresses are reported by the model-level validator
            if addr.version == network.version and addr not in network:
                self._err(
                    f"Node '{node_name}' runtime network endpoint {label} {value} "
                    f"is not within network '{net}' CIDR {cidr}"
                )

    def _verify_runtime_network_sensors(self) -> None:
        """Validate observed network-sensor monitoring scope.

        A network sensor explicitly states which declared network resources it
        observes. Runtime endpoint attachment is a separate fact, so when the
        node records endpoint inventory, the monitored networks must be among
        those endpoint attachments.
        """
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.network_sensors:
                continue
            observed_paths = self._node_observed_paths(node)
            attached_networks = self._runtime_endpoint_networks(runtime)
            for sensor in runtime.network_sensors:
                self._verify_network_sensor(
                    node_name=node_name,
                    sensor=sensor,
                    observed_paths=observed_paths,
                    attached_networks=attached_networks,
                )

    @staticmethod
    def _runtime_endpoint_networks(runtime: object) -> set[str]:
        network = getattr(runtime, "network", None)
        if network is None:
            return set()
        return {endpoint.network for endpoint in network.endpoints if endpoint.network}

    def _verify_network_sensor(
        self,
        *,
        node_name: str,
        sensor: object,
        observed_paths: set[str],
        attached_networks: set[str],
    ) -> None:
        owner_label = f"Node '{node_name}' runtime network sensor '{sensor.sensor_id}'"
        for field_name in ("configuration_file_refs", "log_file_refs", "evidence_refs"):
            self._verify_dns_file_refs(
                owner_label,
                getattr(sensor, field_name, []),
                field_name=field_name,
                observed_paths=observed_paths,
            )
        for network_ref in sensor.monitored_network_refs:
            self._verify_network_sensor_monitored_ref(
                node_name=node_name,
                sensor_id=sensor.sensor_id,
                network_ref=network_ref,
                attached_networks=attached_networks,
            )

    def _verify_network_sensor_monitored_ref(
        self,
        *,
        node_name: str,
        sensor_id: str,
        network_ref: str,
        attached_networks: set[str],
    ) -> None:
        if self._is_unresolved_var(network_ref):
            return
        label = f"Node '{node_name}' runtime network sensor '{sensor_id}'"
        if network_ref not in self._s.infrastructure:
            self._err(f"{label} monitored_network_ref '{network_ref}' references undefined network")
            return
        if not self._is_switch_node(network_ref):
            self._err(f"{label} monitored_network_ref '{network_ref}' must reference a switch/network entry")
            return
        if attached_networks and network_ref not in attached_networks:
            self._err(f"{label} monitored_network_ref '{network_ref}' is not attached to node '{node_name}'")

    def _verify_runtime_network_detection_engines(self) -> None:
        """Validate observed IDS/NDR detection-engine inventories.

        Detection engines may point at a same-node network sensor, filesystem
        evidence, switch-backed network/address sets, and bounded control
        channels. Raw rules, packet payloads, and alert telemetry stay outside
        the SDL model.
        """
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.network_detection_engines:
                continue
            service_names = self._node_service_names(node)
            observed_paths = self._node_observed_paths(node)
            sensor_ids = {sensor.sensor_id for sensor in runtime.network_sensors}
            for engine in runtime.network_detection_engines:
                self._verify_network_detection_engine(
                    node_name=node_name,
                    engine=engine,
                    service_names=service_names,
                    observed_paths=observed_paths,
                    sensor_ids=sensor_ids,
                )

    def _verify_network_detection_engine(
        self,
        *,
        node_name: str,
        engine: object,
        service_names: set[str],
        observed_paths: set[str],
        sensor_ids: set[str],
    ) -> None:
        owner_label = f"Node '{node_name}' runtime network detection engine '{engine.engine_id}'"
        sensor_ref = getattr(engine, "sensor_ref", "")
        if sensor_ref and not self._is_unresolved_var(sensor_ref) and sensor_ref not in sensor_ids:
            self._err(f"{owner_label} sensor_ref '{sensor_ref}' does not resolve to a same-node network sensor")
        for field_name in ("configuration_file_refs", "log_file_refs", "evidence_refs"):
            self._verify_dns_file_refs(
                owner_label,
                getattr(engine, field_name, []),
                field_name=field_name,
                observed_paths=observed_paths,
            )
        for source in engine.rule_sources:
            self._verify_dns_file_refs(
                f"{owner_label} rule_source '{source.source_id}'",
                getattr(source, "file_refs", []),
                field_name="file_refs",
                observed_paths=observed_paths,
            )
        for network_set in engine.network_sets:
            set_label = f"{owner_label} network_set '{network_set.set_id}'"
            for network_ref in network_set.network_refs:
                self._verify_network_detection_network_ref(set_label, network_ref)
        for stream in engine.output_streams:
            self._verify_dns_file_refs(
                f"{owner_label} output_stream '{stream.stream_id}'",
                [stream.path] if stream.path else [],
                field_name="path",
                observed_paths=observed_paths,
            )
        for channel in engine.control_channels:
            channel_label = f"{owner_label} control_channel '{channel.channel_id}'"
            self._verify_owned_service_ref(
                node_name,
                getattr(channel, "service", ""),
                service_names,
                owner_label=channel_label,
            )
            self._verify_dns_file_refs(
                channel_label,
                [channel.path] if channel.path else [],
                field_name="path",
                observed_paths=observed_paths,
            )

    def _verify_network_detection_network_ref(self, owner_label: str, network_ref: str) -> None:
        if self._is_unresolved_var(network_ref):
            return
        if network_ref not in self._s.infrastructure:
            self._err(f"{owner_label} network_ref '{network_ref}' references undefined network")
            return
        if not self._is_switch_node(network_ref):
            self._err(f"{owner_label} network_ref '{network_ref}' must reference a switch/network entry")

    def _verify_runtime_application(self) -> None:
        """Validate observed runtime application surfaces against the scenario.

        Each surface's owning service must resolve to a service on the same
        node; route vulnerability refs must resolve to top-level
        ``vulnerabilities``; and template/static refs should resolve to the
        node's observed file inventory when one is recorded (ADR-026).
        """
        for name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.applications:
                continue
            service_names = self._node_service_names(node)
            observed_paths = self._node_observed_paths(node)
            for application in runtime.applications:
                self._verify_application_service(name, application, service_names)
                for route in application.routes:
                    self._verify_route_refs(name, application, route, observed_paths)

    @staticmethod
    def _node_service_names(node: object) -> set[str]:
        return {service.name for service in getattr(node, "services", []) if service.name}

    @staticmethod
    def _node_services_by_name(node: object) -> dict[str, object]:
        return {service.name: service for service in getattr(node, "services", []) if service.name}

    @staticmethod
    def _node_observed_paths(node: object) -> set[str]:
        """Collect file paths the node observably exposes for template/static refs."""
        paths: set[str] = set()
        runtime = getattr(node, "runtime", None)
        if runtime is not None:
            paths.update(entry.path for entry in runtime.filesystem_inventory if entry.path)
        source = getattr(node, "source", None)
        build = getattr(source, "build", None) if source is not None else None
        if build is not None:
            paths.update(item.destination_path for item in build.copied_sources if item.destination_path)
            paths.update(item.destination_path for item in build.source_inputs if item.destination_path)
        return paths

    def _verify_application_service(self, node_name: str, application: object, service_names: set[str]) -> None:
        self._verify_owned_service_ref(
            node_name,
            getattr(application, "service", ""),
            service_names,
            owner_label=f"Node '{node_name}' runtime application '{application.application_id}'",
        )

    def _verify_owned_service_ref(
        self,
        node_name: str,
        ref: str,
        service_names: set[str],
        *,
        owner_label: str,
    ) -> None:
        """Validate a runtime surface's owning transport-service reference.

        The ref is a bare ``Node.services[].name`` or the qualified
        ``nodes.<node>.services.<name>`` form, and must resolve to a service on
        the same node. Shared by runtime applications, database services, and
        identity authority services.
        """
        if not ref or self._is_unresolved_var(ref):
            return
        service_name = ref
        if ref.startswith(_NODES_PREFIX):
            parts = ref.split(".")
            if len(parts) != 4 or parts[2] != "services":
                self._err(
                    f"{owner_label} service ref '{ref}' must be a bare service name or 'nodes.<node>.services.<name>'"
                )
                return
            if parts[1] != node_name:
                self._err(f"{owner_label} service ref '{ref}' must reference a service on the same node")
                return
            service_name = parts[3]
        if service_name not in service_names:
            self._err(f"{owner_label} references undefined service '{service_name}'")

    def _resolve_owned_service_ref(
        self,
        node_name: str,
        ref: str,
        services_by_name: dict[str, object],
        *,
        owner_label: str,
    ) -> object | None:
        if not ref or self._is_unresolved_var(ref):
            return None
        service_name = ref
        if ref.startswith(_NODES_PREFIX):
            parts = ref.split(".")
            if len(parts) != 4 or parts[2] != "services":
                self._err(
                    f"{owner_label} service ref '{ref}' must be a bare service name or 'nodes.<node>.services.<name>'"
                )
                return None
            if parts[1] != node_name:
                self._err(f"{owner_label} service ref '{ref}' must reference a service on the same node")
                return None
            service_name = parts[3]
        service = services_by_name.get(service_name)
        if service is None:
            self._err(f"{owner_label} references undefined service '{service_name}'")
        return service

    def _verify_runtime_service_listeners(self) -> None:
        """Validate observed service listeners against same-node runtime facts."""
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.service_listeners:
                continue
            services_by_name = self._node_services_by_name(node)
            process_refs = self._node_runtime_process_refs(node)
            published_ports = self._node_published_port_keys(node)
            for listener in runtime.service_listeners:
                label = f"Node '{node_name}' runtime service listener '{listener.listener_id}'"
                service = self._resolve_owned_service_ref(
                    node_name,
                    getattr(listener, "service", ""),
                    services_by_name,
                    owner_label=label,
                )
                if service is not None:
                    self._verify_listener_service_binding(label, listener, service)
                self._verify_listener_process_ref(label, listener, process_refs)
                self._verify_listener_published_port_refs(label, listener, published_ports)

    def _verify_listener_service_binding(self, label: str, listener: object, service: object) -> None:
        listener_port = getattr(listener, "port", None)
        listener_protocol = self._enum_or_raw(getattr(listener, "protocol", ""))
        service_port = getattr(service, "port", None)
        service_protocol = getattr(service, "protocol", "")
        if any(self._is_unresolved_var(v) for v in (listener_port, listener_protocol, service_port, service_protocol)):
            return
        if listener_port is None:
            return
        if listener_port != service_port or str(listener_protocol).lower() != str(service_protocol).lower():
            self._err(f"{label} port/protocol must match service '{service.name}'")

    @staticmethod
    def _enum_or_raw(value: object) -> object:
        return value.value if hasattr(value, "value") else value

    def _verify_listener_process_ref(self, label: str, listener: object, process_refs: set[str]) -> None:
        ref = getattr(listener, "process_ref", "")
        if not ref or self._is_unresolved_var(ref):
            return
        if ref not in process_refs:
            self._err(f"{label} process_ref '{ref}' does not resolve to a runtime process name or pid")

    def _verify_listener_published_port_refs(
        self,
        label: str,
        listener: object,
        published_ports: set[tuple[str, int | str | None, int | str, str]],
    ) -> None:
        listener_port = getattr(listener, "port", None)
        listener_protocol = self._enum_or_raw(getattr(listener, "protocol", ""))
        for ref in getattr(listener, "published_port_refs", []):
            values = (ref.host_ip, ref.host_port, ref.container_port, ref.protocol)
            if any(self._is_unresolved_var(v) for v in values):
                continue
            if any(self._is_unresolved_var(v) for v in (listener_port, listener_protocol)):
                continue
            if listener_port is not None and (
                ref.container_port != listener_port or ref.protocol != str(listener_protocol).lower()
            ):
                self._err(f"{label} published_port_refs entry must match listener port/protocol")
                continue
            if values not in published_ports:
                self._err(f"{label} published_port_refs entry does not resolve to runtime.network.published_ports")

    def _node_runtime_process_refs(self, node: object) -> set[str]:
        runtime = getattr(node, "runtime", None)
        if runtime is None:
            return set()
        refs: set[str] = set()
        processes = [getattr(runtime, "process", None), *getattr(runtime, "processes", [])]
        for process in processes:
            if process is None:
                continue
            name = getattr(process, "name", "")
            pid = getattr(process, "pid", None)
            if name and not self._is_unresolved_var(name):
                refs.add(str(name))
            if pid is not None and not self._is_unresolved_var(pid):
                refs.add(str(pid))
        return refs

    @staticmethod
    def _node_published_port_keys(node: object) -> set[tuple[str, int | str | None, int | str, str]]:
        runtime = getattr(node, "runtime", None)
        network = getattr(runtime, "network", None) if runtime is not None else None
        if network is None:
            return set()
        return {
            (binding.host_ip, binding.host_port, binding.container_port, binding.protocol)
            for binding in network.published_ports
        }

    def _verify_route_refs(
        self,
        node_name: str,
        application: object,
        route: object,
        observed_paths: set[str],
    ) -> None:
        app_id = application.application_id
        route_id = route.route_id
        for ref in route.vulnerability_refs:
            if self._is_unresolved_var(ref):
                continue
            if ref not in self._s.vulnerabilities:
                self._err(
                    f"Node '{node_name}' runtime application '{app_id}' route '{route_id}' "
                    f"references undefined vulnerability '{ref}'"
                )
        if not observed_paths:
            return
        for field_name in ("templates", "static_assets"):
            for ref in getattr(route, field_name):
                if self._is_unresolved_var(ref):
                    continue
                if ref not in observed_paths:
                    self._err(
                        f"Node '{node_name}' runtime application '{app_id}' route '{route_id}' "
                        f"{field_name} ref '{ref}' does not resolve to an observed file on the node"
                    )

    def _verify_runtime_service_manager_units(self) -> None:
        """Validate observed service-manager unit inventories (ADR-035).

        Each ``ServiceManagerUnit.service`` ref, when set and not a variable,
        must resolve to a service on the same node (bare name OR
        ``nodes.<this-node>.services.<name>``). When a ``unit_file_path`` is set
        and ``runtime.filesystem_inventory`` is non-empty, the path SHOULD
        appear in that inventory; otherwise we emit a soft semantic error so
        downstream consumers can tell unit-file evidence and filesystem
        inventory apart.
        """
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.service_manager_units:
                continue
            service_names = self._node_service_names(node)
            observed_paths = self._node_observed_paths(node)
            for unit in runtime.service_manager_units:
                owner_label = f"Node '{node_name}' runtime service_manager_unit '{unit.unit_id}'"
                self._verify_owned_service_ref(
                    node_name,
                    getattr(unit, "service", ""),
                    service_names,
                    owner_label=owner_label,
                )
                unit_file_path = getattr(unit, "unit_file_path", "")
                if (
                    unit_file_path
                    and observed_paths
                    and not self._is_unresolved_var(unit_file_path)
                    and unit_file_path not in observed_paths
                ):
                    self._err(
                        f"{owner_label} unit_file_path '{unit_file_path}' does not resolve to an "
                        f"observed file on the node"
                    )

    def _verify_runtime_ssh_servers(self) -> None:
        """Validate observed SSH server configurations against the scenario.

        Each ``SshServerConfig.service`` must resolve to a service on the
        same node (bare name OR ``nodes.<this-node>.services.<name>``).
        Each ``Match`` rule's ``LOCAL_USER`` criterion whose pattern is a
        concrete (non-wildcard, non-variable) literal MAY be cross-checked
        against ``runtime.local_identity.users`` when that inventory is
        present and non-empty (ADR-031 § "Semantic validation gate").
        """
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.ssh_servers:
                continue
            service_names = self._node_service_names(node)
            local_usernames = self._node_local_usernames(node)
            for server in runtime.ssh_servers:
                self._verify_ssh_server_service(node_name, server, service_names)
                for rule in server.match_rules:
                    self._verify_ssh_match_rule(node_name, server, rule, local_usernames)

    @staticmethod
    def _node_local_usernames(node: object) -> set[str]:
        runtime = getattr(node, "runtime", None)
        if runtime is None:
            return set()
        identity = getattr(runtime, "local_identity", None)
        if identity is None:
            return set()
        return {user.username for user in identity.users if user.username}

    def _verify_ssh_server_service(
        self,
        node_name: str,
        server: object,
        service_names: set[str],
    ) -> None:
        ref = getattr(server, "service", "")
        if not ref or self._is_unresolved_var(ref):
            return
        server_id = server.server_id
        service_name = ref
        if ref.startswith("nodes."):
            parts = ref.split(".")
            if len(parts) != 4 or parts[2] != "services":
                self._err(
                    f"Node '{node_name}' runtime ssh_server '{server_id}' service ref '{ref}' "
                    f"must be a bare service name or 'nodes.<node>.services.<name>'"
                )
                return
            if parts[1] != node_name:
                self._err(
                    f"Node '{node_name}' runtime ssh_server '{server_id}' service ref '{ref}' "
                    f"must reference a service on the same node"
                )
                return
            service_name = parts[3]
        if service_name not in service_names:
            self._err(
                f"Node '{node_name}' runtime ssh_server '{server_id}' references undefined service '{service_name}'"
            )

    def _verify_ssh_match_rule(
        self,
        node_name: str,
        server: object,
        rule: object,
        local_usernames: set[str],
    ) -> None:
        if not local_usernames:
            return
        for criterion in rule.criteria:
            if criterion.kind != SshMatchCriterionKind.LOCAL_USER:
                continue
            pattern = criterion.pattern
            if self._is_unresolved_var(pattern):
                continue
            if any(ch in pattern for ch in "*?!,"):
                # Wildcard or comma-separated list — not a single concrete identity.
                continue
            if pattern not in local_usernames:
                self._err(
                    f"Node '{node_name}' runtime ssh_server '{server.server_id}' "
                    f"match rule '{rule.match_id}' references local user '{pattern}' "
                    f"not present in runtime.local_identity.users"
                )

    def _verify_runtime_capability_overrides(self) -> None:
        """Cross-check ``linux_capabilities.process_overrides`` selectors.

        Per ADR-030, scoped capability records identify a subject via
        ``RuntimeProcessIdentity`` selectors and the capability list ships
        through the same closed-world Pydantic gates as the container-wide
        lists. The only check that cannot live on the model itself is the
        scenario-level cross-reference: when an override's
        ``subject.name`` is a literal value and the enclosing node declares
        ``runtime.processes``, the name SHOULD match one of those observed
        processes. A miss is reported as an error so inventories that
        forget to add the new process surface fail fast rather than ship a
        scoped-policy claim that points at nothing.
        """
        for node_name, node in self._s.nodes.items():
            overrides = self._capability_overrides_for(node)
            if not overrides:
                continue
            observed = self._observed_process_names(node)
            if not observed:
                # No declared process inventory to cross-check against — the
                # override stands on its own selectors.
                continue
            self._check_override_subject_names(node_name, overrides, observed)

    def _capability_overrides_for(self, node: object) -> list[object]:
        runtime = getattr(node, "runtime", None)
        if runtime is None:
            return []
        capability_policy = getattr(runtime, "linux_capabilities", None)
        if capability_policy is None:
            return []
        return list(getattr(capability_policy, "process_overrides", None) or [])

    def _observed_process_names(self, node: object) -> set[str]:
        runtime = getattr(node, "runtime", None)
        if runtime is None:
            return set()
        names = {
            process.name
            for process in (runtime.processes or [])
            if process.name and not self._is_unresolved_var(process.name)
        }
        primary = getattr(runtime, "process", None)
        if primary is not None and primary.name and not self._is_unresolved_var(primary.name):
            names.add(primary.name)
        return names

    def _check_override_subject_names(
        self,
        node_name: str,
        overrides: list[object],
        observed: set[str],
    ) -> None:
        for override in overrides:
            subject_name = override.subject.name
            if not subject_name or self._is_unresolved_var(subject_name):
                continue
            if subject_name not in observed:
                self._err(
                    f"Node '{node_name}' runtime capability override subject "
                    f"'{subject_name}' does not match any process declared in "
                    "'runtime.processes' or 'runtime.process'"
                )

    def _verify_runtime_identity_authorities(self) -> None:
        """Validate observed identity authorities against the scenario.

        Authority endpoint ``service`` refs resolve like other node-scoped
        runtime service ownership claims. Relationship and policy refs are
        local to the authority inventory so membership and trust facts cannot
        silently point at missing users, groups, policies, or the authority
        record itself.
        """
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.identity_authorities:
                continue
            service_names = self._node_service_names(node)
            for authority in runtime.identity_authorities:
                self._verify_identity_authority_services(node_name, authority, service_names)
                local_refs = self._identity_authority_local_refs(authority)
                self._verify_identity_authority_relationships(node_name, authority, local_refs)
                self._verify_identity_authority_policies(node_name, authority, local_refs)

    def _verify_identity_authority_services(
        self,
        node_name: str,
        authority: object,
        service_names: set[str],
    ) -> None:
        for service in authority.services:
            self._verify_owned_service_ref(
                node_name,
                getattr(service, "service", ""),
                service_names,
                owner_label=(
                    f"Node '{node_name}' runtime identity authority '{authority.authority_id}' "
                    f"service '{service.service_id}'"
                ),
            )

    @staticmethod
    def _identity_authority_local_refs(authority: object) -> set[str]:
        refs = {authority.authority_id}
        refs.update(service.service_id for service in authority.services)
        refs.update(subject.subject_id for subject in authority.subjects)
        refs.update(policy.policy_id for policy in authority.policies)
        refs.update(relationship.relationship_id for relationship in authority.relationships)
        return refs

    def _verify_identity_authority_relationships(
        self,
        node_name: str,
        authority: object,
        local_refs: set[str],
    ) -> None:
        label = f"Node '{node_name}' runtime identity authority '{authority.authority_id}'"
        for relationship in authority.relationships:
            rel_label = f"{label} relationship '{relationship.relationship_id}'"
            self._verify_identity_ref(
                getattr(relationship, "source_ref", ""),
                local_refs,
                label=rel_label,
                field_name="source_ref",
            )
            if relationship.target_ref:
                self._verify_identity_ref(
                    relationship.target_ref,
                    local_refs,
                    label=rel_label,
                    field_name="target_ref",
                )

    def _verify_identity_authority_policies(
        self,
        node_name: str,
        authority: object,
        local_refs: set[str],
    ) -> None:
        label = f"Node '{node_name}' runtime identity authority '{authority.authority_id}'"
        for policy in authority.policies:
            policy_label = f"{label} policy '{policy.policy_id}'"
            for ref in policy.applies_to_refs:
                self._verify_identity_ref(
                    ref,
                    local_refs,
                    label=policy_label,
                    field_name="applies_to_ref",
                )

    def _verify_identity_ref(
        self,
        ref: str,
        local_refs: set[str],
        *,
        label: str,
        field_name: str,
    ) -> None:
        if self._is_unresolved_var(ref):
            return
        if ref not in local_refs:
            self._err(f"{label} {field_name} '{ref}' does not resolve inside identity authority")

    # File-service surface (ADR-037).

    _FILE_SERVICE_SUBJECT_LITERALS: frozenset[str] = frozenset({"anonymous", "guest"})

    def _verify_runtime_file_services(self) -> None:
        """Validate observed runtime file services against the scenario.

        Each service's owning transport service must resolve to a service on
        the same node (mirroring ``runtime.applications``). Rule/observation
        ``subject_ref`` resolves against service-local principal ids plus the
        reserved literals ``anonymous`` and ``guest``. ``resource_ref``
        resolves against service-local share ids; a ``share_id:path`` form is
        allowed for narrowed resources. Optional ``local_user_ref`` and
        ``directory_subject_ref`` on a principal are checked against
        ``runtime.local_identity.users`` and the qualified identity-authority
        ref shape, respectively, when present.
        """
        identity_subject_refs = self._identity_authority_subject_refs()
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.file_services:
                continue
            service_names = self._node_service_names(node)
            local_user_names = self._node_local_user_names(node)
            for service in runtime.file_services:
                owner_label = f"Node '{node_name}' runtime file service '{service.service_id}'"
                self._verify_owned_service_ref(
                    node_name,
                    getattr(service, "service", ""),
                    service_names,
                    owner_label=owner_label,
                )
                self._verify_file_service_principals(
                    owner_label,
                    service,
                    local_user_names,
                    identity_subject_refs,
                )
                share_ids = {share.share_id for share in service.shares}
                subject_refs = {
                    principal.principal_id for principal in service.principals
                } | self._FILE_SERVICE_SUBJECT_LITERALS
                for rule in service.access_rules:
                    self._verify_file_service_ref(
                        rule.subject_ref,
                        subject_refs,
                        label=f"{owner_label} rule '{rule.rule_id}'",
                        field_name="subject_ref",
                    )
                    self._verify_file_service_resource_ref(
                        rule.resource_ref,
                        share_ids,
                        label=f"{owner_label} rule '{rule.rule_id}'",
                    )
                for observation in service.access_observations:
                    self._verify_file_service_ref(
                        observation.subject_ref,
                        subject_refs,
                        label=f"{owner_label} observation '{observation.observation_id}'",
                        field_name="subject_ref",
                    )
                    self._verify_file_service_resource_ref(
                        observation.resource_ref,
                        share_ids,
                        label=f"{owner_label} observation '{observation.observation_id}'",
                    )

    @staticmethod
    def _node_local_user_names(node: object) -> set[str]:
        runtime = getattr(node, "runtime", None)
        local_identity = getattr(runtime, "local_identity", None) if runtime is not None else None
        if local_identity is None:
            return set()
        return {user.username for user in getattr(local_identity, "users", []) if user.username}

    def _identity_authority_subject_refs(self) -> set[str]:
        """Qualified subject refs across all node-scoped identity authorities.

        Shape: ``nodes.<node>.runtime.identity_authorities.<authority>.subjects.<subject>``.
        Used by file-service ``directory_subject_ref`` resolution so a
        principal cannot smuggle a dangling pointer at a missing authority or
        subject past semantic validation.
        """
        refs: set[str] = set()
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None:
                continue
            for authority in runtime.identity_authorities:
                base = f"{_NODES_PREFIX}{node_name}.runtime.identity_authorities.{authority.authority_id}"
                for subject in authority.subjects:
                    refs.add(f"{base}.subjects.{subject.subject_id}")
        return refs

    def _verify_file_service_principals(
        self,
        owner_label: str,
        service: object,
        local_user_names: set[str],
        identity_subject_refs: set[str],
    ) -> None:
        for principal in service.principals:
            local_user_ref = getattr(principal, "local_user_ref", "")
            if local_user_ref and not self._is_unresolved_var(local_user_ref):
                if local_user_names and local_user_ref not in local_user_names:
                    self._err(
                        f"{owner_label} principal '{principal.principal_id}' local_user_ref "
                        f"'{local_user_ref}' does not resolve to a runtime.local_identity user"
                    )
            directory_ref = getattr(principal, "directory_subject_ref", "")
            if not directory_ref or self._is_unresolved_var(directory_ref):
                continue
            if not directory_ref.startswith(_NODES_PREFIX):
                self._err(
                    f"{owner_label} principal '{principal.principal_id}' "
                    f"directory_subject_ref '{directory_ref}' must be a qualified "
                    f"'nodes.<node>.runtime.identity_authorities.<id>.subjects.<id>' reference"
                )
                continue
            if directory_ref not in identity_subject_refs:
                self._err(
                    f"{owner_label} principal '{principal.principal_id}' "
                    f"directory_subject_ref '{directory_ref}' does not resolve to a known "
                    "identity-authority subject"
                )

    def _verify_file_service_ref(
        self,
        ref: str,
        local_refs: set[str],
        *,
        label: str,
        field_name: str,
    ) -> None:
        if not ref or self._is_unresolved_var(ref):
            return
        if ref not in local_refs:
            self._err(f"{label} {field_name} '{ref}' does not resolve inside file service")

    def _verify_file_service_resource_ref(
        self,
        ref: str,
        share_ids: set[str],
        *,
        label: str,
    ) -> None:
        if not ref or self._is_unresolved_var(ref):
            return
        share_segment = ref.split(":", 1)[0]
        if share_segment not in share_ids:
            self._err(f"{label} resource_ref '{ref}' does not resolve to a share in the file service")

    def _verify_runtime_database_services(self) -> None:
        """Validate observed database services against the scenario.

        Each service's owning transport service must resolve to a service on
        the same node (mirroring ``runtime.applications``); grant grantee/object
        refs must resolve to roles and logical objects within the same service
        (ADR-029 §6).
        """
        for name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.database_services:
                continue
            service_names = self._node_service_names(node)
            for dbsvc in runtime.database_services:
                self._verify_owned_service_ref(
                    name,
                    getattr(dbsvc, "service", ""),
                    service_names,
                    owner_label=f"Node '{name}' runtime database service '{dbsvc.database_service_id}'",
                )
                self._verify_database_grants(name, dbsvc)

    def _verify_database_grants(self, node_name: str, dbsvc: object) -> None:
        role_ids = {role.role_id for role in dbsvc.roles}
        objects_by_type: dict[str, set[str]] = {
            "database": {db.database_id for db in dbsvc.databases},
            "schema": {schema.schema_id for db in dbsvc.databases for schema in db.schemas},
            "table": {table.table_id for db in dbsvc.databases for schema in db.schemas for table in schema.tables},
        }
        label = f"Node '{node_name}' runtime database service '{dbsvc.database_service_id}'"
        for grant in dbsvc.grants:
            if not self._is_unresolved_var(grant.grantee_role_ref) and grant.grantee_role_ref not in role_ids:
                self._err(f"{label} grant grantee_role_ref '{grant.grantee_role_ref}' is not a role in the service")
            object_type = grant.object_type
            type_value = object_type.value if isinstance(object_type, DatabaseObjectType) else object_type
            if self._is_unresolved_var(grant.object_ref) or self._is_unresolved_var(type_value):
                continue
            if grant.object_ref not in objects_by_type.get(type_value, set()):
                self._err(f"{label} grant object_ref '{grant.object_ref}' is not a {type_value} in the service")

    def _verify_runtime_dns_services(self) -> None:
        """Validate observed DNS services against the scenario.

        Each DNS service's owning transport service must resolve to a service
        on the same node. Optional configuration, log, and zone-file refs are
        checked against ``runtime.filesystem_inventory`` when the node has an
        observed file inventory, keeping evidence paths tied to node-scoped
        runtime facts without embedding raw zone-file content.
        """
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.dns_services:
                continue
            service_names = self._node_service_names(node)
            observed_paths = self._node_observed_paths(node)
            for dns_service in runtime.dns_services:
                owner_label = f"Node '{node_name}' runtime DNS service '{dns_service.dns_service_id}'"
                self._verify_owned_service_ref(
                    node_name,
                    getattr(dns_service, "service", ""),
                    service_names,
                    owner_label=owner_label,
                )
                self._verify_dns_file_refs(
                    owner_label,
                    getattr(dns_service, "configuration_file_refs", []),
                    field_name="configuration_file_refs",
                    observed_paths=observed_paths,
                )
                self._verify_dns_file_refs(
                    owner_label,
                    getattr(dns_service, "log_file_refs", []),
                    field_name="log_file_refs",
                    observed_paths=observed_paths,
                )
                for zone in dns_service.zones:
                    self._verify_dns_file_refs(
                        f"{owner_label} zone '{zone.zone_id}'",
                        getattr(zone, "zone_file_refs", []),
                        field_name="zone_file_refs",
                        observed_paths=observed_paths,
                    )

    def _verify_dns_file_refs(
        self,
        owner_label: str,
        refs: list[str],
        *,
        field_name: str,
        observed_paths: set[str],
    ) -> None:
        if not observed_paths:
            return
        for ref in refs:
            if self._is_unresolved_var(ref):
                continue
            if ref not in observed_paths:
                self._err(f"{owner_label} {field_name} ref '{ref}' does not resolve to an observed file on the node")

    def _verify_runtime_security_monitoring_managers(self) -> None:
        """Validate observed SIEM/security-monitoring manager inventories.

        Manager and listener service refs are node-local transport ownership
        claims. File refs are checked only when a filesystem inventory exists,
        matching the DNS and mail runtime surfaces' evidence-bound posture.
        Agent/group and setting/component refs are manager-local stable ids.
        """
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.security_monitoring_managers:
                continue
            service_names = self._node_service_names(node)
            observed_paths = self._node_observed_paths(node)
            for manager in runtime.security_monitoring_managers:
                self._verify_security_monitoring_manager(
                    node_name=node_name,
                    manager=manager,
                    service_names=service_names,
                    observed_paths=observed_paths,
                )

    def _verify_security_monitoring_manager(
        self,
        *,
        node_name: str,
        manager: object,
        service_names: set[str],
        observed_paths: set[str],
    ) -> None:
        owner_label = f"Node '{node_name}' runtime security-monitoring manager '{manager.manager_id}'"
        self._verify_owned_service_ref(
            node_name,
            getattr(manager, "service", ""),
            service_names,
            owner_label=owner_label,
        )
        self._verify_dns_file_refs(
            owner_label,
            getattr(manager, "configuration_file_refs", []),
            field_name="configuration_file_refs",
            observed_paths=observed_paths,
        )
        self._verify_dns_file_refs(
            owner_label,
            getattr(manager, "log_file_refs", []),
            field_name="log_file_refs",
            observed_paths=observed_paths,
        )
        self._verify_dns_file_refs(
            owner_label,
            getattr(manager, "evidence_refs", []),
            field_name="evidence_refs",
            observed_paths=observed_paths,
        )
        self._verify_security_monitoring_children(
            node_name=node_name,
            manager=manager,
            owner_label=owner_label,
            service_names=service_names,
            observed_paths=observed_paths,
        )

    def _verify_security_monitoring_children(
        self,
        *,
        node_name: str,
        manager: object,
        owner_label: str,
        service_names: set[str],
        observed_paths: set[str],
    ) -> None:
        component_ids = {component.component_id for component in manager.components}
        agent_ids = {agent.agent_id for agent in manager.agents}
        group_ids = {group.group_id for group in manager.agent_groups}
        for listener in manager.listeners:
            self._verify_owned_service_ref(
                node_name,
                getattr(listener, "service", ""),
                service_names,
                owner_label=f"{owner_label} listener '{listener.listener_id}'",
            )
        for group in manager.agent_groups:
            group_label = f"{owner_label} agent_group '{group.group_id}'"
            self._verify_dns_file_refs(
                group_label,
                getattr(group, "configuration_file_refs", []),
                field_name="configuration_file_refs",
                observed_paths=observed_paths,
            )
            for member_ref in group.member_refs:
                self._verify_security_monitoring_local_ref(
                    member_ref,
                    agent_ids,
                    owner_label=group_label,
                    field_name="member_ref",
                    target_label="agent",
                )
        for agent in manager.agents:
            agent_label = f"{owner_label} agent '{agent.agent_id}'"
            for group_ref in agent.group_refs:
                self._verify_security_monitoring_local_ref(
                    group_ref,
                    group_ids,
                    owner_label=agent_label,
                    field_name="group_ref",
                    target_label="agent group",
                )
        for content_set in manager.content_sets:
            self._verify_dns_file_refs(
                f"{owner_label} content_set '{content_set.content_id}'",
                getattr(content_set, "file_refs", []),
                field_name="file_refs",
                observed_paths=observed_paths,
            )
        for setting in manager.settings:
            setting_label = f"{owner_label} setting '{setting.setting_id}'"
            self._verify_security_monitoring_local_ref(
                getattr(setting, "component_ref", ""),
                component_ids,
                owner_label=setting_label,
                field_name="component_ref",
                target_label="component",
            )
            self._verify_dns_file_refs(
                setting_label,
                [setting.source_path] if setting.source_path else [],
                field_name="source_path",
                observed_paths=observed_paths,
            )

    def _verify_security_monitoring_local_ref(
        self,
        ref: str,
        local_refs: set[str],
        *,
        owner_label: str,
        field_name: str,
        target_label: str,
    ) -> None:
        if not ref or self._is_unresolved_var(ref):
            return
        if ref not in local_refs:
            self._err(
                f"{owner_label} {field_name} '{ref}' does not resolve to a "
                f"{target_label} in the security-monitoring manager"
            )

    def _split_runtime_ref(self, ref: object, *, surface: str) -> tuple[str, str] | None:
        """Split ``nodes.<node>.runtime.<surface>.<rest>`` into (node, rest).

        Module composition rewrites the node segment to a dotted namespaced
        form (``shared.web``), so we cannot split on ``.`` and index by
        position. Partition on the surface marker instead so the node name
        survives an arbitrary number of namespace prefixes.
        """
        if not isinstance(ref, str) or not ref.startswith(_NODES_PREFIX):
            return None
        marker = f".runtime.{surface}."
        head, sep, tail = ref[len(_NODES_PREFIX) :].partition(marker)
        if not sep or not head or not tail:
            return None
        return head, tail

    def _resolve_database_service_ref(self, ref: object) -> object | None:
        """Resolve a qualified ``nodes.<node>.runtime.database_services.<id>`` ref.

        Accepts the database-service form and the ``.databases.<id>`` form; both
        resolve to the owning :class:`DatabaseService` so a relationship's
        ``database_access`` can be checked against it.
        """
        split = self._split_runtime_ref(ref, surface="database_services")
        if split is None:
            return None
        node_name, tail = split
        tail_parts = tail.split(".")
        # tail is ``<svc_id>`` (1 part) or ``<svc_id>.databases.<db_id>`` (3).
        if len(tail_parts) == 1 or (len(tail_parts) == 3 and tail_parts[1] == "databases"):
            svc_id = tail_parts[0]
        else:
            return None
        node = self._s.nodes.get(node_name)
        runtime = getattr(node, "runtime", None) if node is not None else None
        if runtime is None:
            return None
        for dbsvc in runtime.database_services:
            if dbsvc.database_service_id == svc_id:
                return dbsvc
        return None

    def _resolve_application_ref(self, ref: object) -> object | None:
        """Resolve a qualified ``nodes.<node>.runtime.applications.<id>`` ref.

        Returns the owning :class:`RuntimeApplicationSurface` so a relationship's
        ``database_access`` source endpoint can be confirmed to be a runtime
        application (ADR-029 §4).
        """
        split = self._split_runtime_ref(ref, surface="applications")
        if split is None:
            return None
        node_name, tail = split
        if "." in tail:
            return None
        node = self._s.nodes.get(node_name)
        runtime = getattr(node, "runtime", None) if node is not None else None
        if runtime is None:
            return None
        for application in runtime.applications:
            if application.application_id == tail:
                return application
        return None

    def _verify_relationship_database_access(self) -> None:
        """Validate typed ``database_access`` blocks on relationship edges.

        When a relationship carries ``database_access``, its ``source`` must
        resolve to a runtime application and its ``target`` must resolve to a
        database service (or logical database); the access ``role_ref`` must
        name a role in that service (ADR-029 §4).
        """
        for name, rel in self._s.relationships.items():
            access = rel.database_access
            if access is None:
                continue
            label = f"Relationship '{name}'"
            self._check_database_access_source(rel.source, label)
            dbsvc = self._check_database_access_target(rel.target, label)
            if dbsvc is not None:
                self._check_database_access_role(access.role_ref, dbsvc, label)

    def _check_database_access_source(self, source: str, label: str) -> None:
        if self._is_unresolved_var(source) or self._resolve_application_ref(source) is not None:
            return
        self._err(f"{label} has database_access but source '{source}' does not resolve to a runtime application")

    def _check_database_access_target(self, target: str, label: str) -> object | None:
        dbsvc = self._resolve_database_service_ref(target)
        if dbsvc is not None or self._is_unresolved_var(target):
            return dbsvc
        self._err(
            f"{label} has database_access but target '{target}' does not resolve to a database service or database"
        )
        return None

    def _check_database_access_role(self, role_ref: str, dbsvc: object, label: str) -> None:
        if not role_ref or self._is_unresolved_var(role_ref):
            return
        if role_ref not in {role.role_id for role in dbsvc.roles}:
            self._err(
                f"{label} database_access role_ref '{role_ref}' "
                f"is not a role in database service '{dbsvc.database_service_id}'"
            )

    def _verify_content(self) -> None:
        for name, item in self._s.content.items():
            if item.target and not self._is_unresolved_var(item.target) and item.target not in self._s.nodes:
                self._err(f"Content '{name}' targets undefined node '{item.target}'")
            elif item.target and not self._is_unresolved_var(item.target) and not self._is_vm_node(item.target):
                self._err(f"Content '{name}' target '{item.target}' must be a VM node")

    def _verify_accounts(self) -> None:
        for name, acct in self._s.accounts.items():
            if acct.node and not self._is_unresolved_var(acct.node) and acct.node not in self._s.nodes:
                self._err(f"Account '{name}' references undefined node '{acct.node}'")
            elif acct.node and not self._is_unresolved_var(acct.node) and not self._is_vm_node(acct.node):
                self._err(f"Account '{name}' node '{acct.node}' must be a VM node")

    def _verify_relationships(self) -> None:
        for name, rel in self._s.relationships.items():
            if not self._is_unresolved_var(rel.source):
                self._validate_named_ref(
                    rel.source,
                    owner_label=f"Relationship '{name}'",
                    ref_label="source",
                )
            if not self._is_unresolved_var(rel.target):
                self._validate_named_ref(
                    rel.target,
                    owner_label=f"Relationship '{name}'",
                    ref_label="target",
                )

    def _verify_agents(self) -> None:
        flat_entity_names = self._all_entity_names()
        service_names = {service.name for node in self._s.nodes.values() for service in node.services if service.name}

        for name, agent in self._s.agents.items():
            if agent.entity and not self._is_unresolved_var(agent.entity) and agent.entity not in flat_entity_names:
                self._err(f"Agent '{name}' references undefined entity '{agent.entity}'")
            for acct_name in agent.starting_accounts:
                if self._is_unresolved_var(acct_name):
                    continue
                if acct_name not in self._s.accounts:
                    self._err(f"Agent '{name}' starting_account '{acct_name}' not in accounts section")
            for subnet in agent.allowed_subnets:
                if self._is_unresolved_var(subnet):
                    continue
                if subnet not in self._s.infrastructure:
                    self._err(f"Agent '{name}' allowed_subnet '{subnet}' not in infrastructure section")
                elif not self._is_switch_node(subnet):
                    self._err(f"Agent '{name}' allowed_subnet '{subnet}' must reference a switch/network entry")
            if agent.initial_knowledge:
                for host in agent.initial_knowledge.hosts:
                    if self._is_unresolved_var(host):
                        continue
                    if host not in self._s.nodes:
                        self._err(f"Agent '{name}' initial_knowledge host '{host}' not in nodes section")
                    elif not self._is_vm_node(host):
                        self._err(f"Agent '{name}' initial_knowledge host '{host}' must reference a VM node")
                for subnet in agent.initial_knowledge.subnets:
                    if self._is_unresolved_var(subnet):
                        continue
                    if subnet not in self._s.infrastructure:
                        self._err(f"Agent '{name}' initial_knowledge subnet '{subnet}' not in infrastructure section")
                    elif not self._is_switch_node(subnet):
                        self._err(
                            f"Agent '{name}' initial_knowledge subnet '{subnet}' must reference a switch/network entry"
                        )
                for service_name in agent.initial_knowledge.services:
                    if self._is_unresolved_var(service_name):
                        continue
                    if service_name not in service_names:
                        self._err(
                            f"Agent '{name}' initial_knowledge service '{service_name}' not in node service names"
                        )
                for acct_name in agent.initial_knowledge.accounts:
                    if self._is_unresolved_var(acct_name):
                        continue
                    if acct_name not in self._s.accounts:
                        self._err(f"Agent '{name}' initial_knowledge account '{acct_name}' not in accounts section")
            for cond_name in agent.starting_conditions:
                if self._is_unresolved_var(cond_name):
                    continue
                # ADR-020 §6 publishes starting_conditions as accepting bare
                # (`health`) or section-qualified (`conditions.health`)
                # references. Strip the `conditions.` prefix when present so
                # both forms resolve against the same dict.
                bare_name = cond_name.removeprefix("conditions.")
                if bare_name not in self._s.conditions:
                    self._err(f"Agent '{name}' starting_condition '{cond_name}' not in conditions section")
            for anchor in agent.authority_anchors:
                if self._is_unresolved_var(anchor):
                    continue
                self._validate_named_ref(
                    anchor,
                    owner_label=f"Agent '{name}'",
                    ref_label="authority_anchor",
                    targetable=False,
                )
            for scope in agent.operating_scope:
                if self._is_unresolved_var(scope):
                    continue
                self._validate_operating_scope_ref(scope, owner_label=f"Agent '{name}'")

    def _verify_participant_behavior(self) -> None:
        analysis = analyze_participant_behavior(
            agents_by_name=self._s.agents,
            action_contracts=self._s.action_contracts,
            observation_boundaries=self._s.observation_boundaries,
            is_unresolved=self._is_unresolved_var,
        )
        for issue in analysis.issues:
            self._err(self._format_participant_behavior_issue(issue))
        self._verify_participant_interaction_refs()

    def _verify_participant_interaction_refs(self) -> None:
        for action_name, action_contract in self._s.action_contracts.items():
            for index, interaction in enumerate(action_contract.interactions):
                owner_label = f"Action contract '{action_name}' interaction[{index}]"
                if not self._is_unresolved_var(interaction.target):
                    self._validate_named_ref(
                        interaction.target,
                        owner_label=owner_label,
                        ref_label="target",
                        targetable=True,
                    )
                for ref in interaction.shared_state_refs:
                    if self._is_unresolved_var(ref):
                        continue
                    self._validate_named_ref(
                        ref,
                        owner_label=owner_label,
                        ref_label="shared_state_ref",
                        targetable=True,
                    )

    def _verify_participant_outcomes(self) -> None:
        analysis = analyze_participant_outcome_interpretations(
            outcome_interpretation_rules=self._s.outcome_interpretation_rules,
            action_contracts=self._s.action_contracts,
            objectives=self._s.objectives,
            workflows=self._s.workflows,
            evaluations=self._s.evaluations,
            is_unresolved=self._is_unresolved_var,
        )
        for issue in analysis.issues:
            self._err(self._format_participant_outcome_issue(issue))

    def _verify_objectives(self) -> None:
        # Declarative-objective semantics — actor binding, target resolution,
        # success interpretation, windows, and dependency ordering (SEM-207).
        # The name-level reference graph, ordering/refresh-role model, and
        # fail-closed issue set live in ``aces_sdl.semantics.objective_semantics``;
        # this pass renders the machine-readable issues it reports as authoring
        # errors.
        analysis = analyze_objective_semantics(
            objectives_by_name=self._s.objectives,
            agents_by_name=self._s.agents,
            entity_names=self._all_entity_names(),
            assessment_resources=AssessmentResourceCatalog(
                conditions=self._s.conditions,
                metrics=self._s.metrics,
                evaluations=self._s.evaluations,
                tlos=self._s.tlos,
                goals=self._s.goals,
            ),
            window_resources=WindowResourceCatalog(
                stories=self._s.stories,
                scripts=self._s.scripts,
                events=self._s.events,
                workflows=self._s.workflows,
            ),
            targetable_name_index=self._named_ref_index(targetable=True),
            is_unresolved=self._is_unresolved_var,
        )
        for issue in analysis.issues:
            self._err(self._format_objective_issue(issue))

    @staticmethod
    def _format_objective_issue(issue: ObjectiveIssue) -> str:
        try:
            renderer = _OBJECTIVE_ISSUE_RENDERERS[issue.code]
        except KeyError:  # pragma: no cover - defensive: a new code without a renderer
            raise AssertionError(f"unhandled objective-semantics issue code: {issue.code}") from None
        return renderer(issue)

    @staticmethod
    def _format_participant_behavior_issue(issue: ParticipantBehaviorIssue) -> str:
        try:
            renderer = _PARTICIPANT_BEHAVIOR_ISSUE_RENDERERS[issue.code]
        except KeyError:  # pragma: no cover - defensive: a new code without a renderer
            raise AssertionError(f"unhandled participant-behavior issue code: {issue.code}") from None
        return renderer(issue)

    @staticmethod
    def _format_participant_outcome_issue(issue: ParticipantOutcomeIssue) -> str:
        try:
            renderer = _PARTICIPANT_OUTCOME_ISSUE_RENDERERS[issue.code]
        except KeyError:  # pragma: no cover - defensive: a new code without a renderer
            raise AssertionError(f"unhandled participant-outcome issue code: {issue.code}") from None
        return renderer(issue)

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
