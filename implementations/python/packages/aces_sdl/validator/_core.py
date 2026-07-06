"""SemanticValidator _ValidatorCore (split from validator.py).

Part of the SemanticValidator mixin composition; see __init__.py.
"""

from collections import defaultdict

from .._base import is_variable_ref
from .._errors import SDLValidationError
from .._runtime_service_families import collect_qualified_runtime_family_refs
from ..entities import flatten_entities
from ..nodes import NodeType
from ..scenario import Scenario
from ._support import _NODES_PREFIX


class _ValidatorCore:
    def __init__(self, scenario: Scenario) -> None:
        self._s = scenario
        self._errors: list[str] = []
        self._warnings: list[str] = []

    def _err(self, msg: str) -> None:
        self._errors.append(msg)

    def _warn(self, msg: str) -> None:
        self._warnings.append(msg)

    @staticmethod
    def _is_unresolved_var(value: object) -> bool:
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

    @staticmethod
    def _split_node_service_ref(ref: object) -> tuple[str, str] | None:
        """Split ``nodes.<node>.services.<service>`` into node/service parts.

        Node names may contain dots (for example ``wazuh.manager``), so service
        refs must be partitioned on the ``.services.`` marker instead of split
        by position.
        """
        if not isinstance(ref, str) or not ref.startswith(_NODES_PREFIX):
            return None
        node_name, sep, service_name = ref[len(_NODES_PREFIX) :].partition(".services.")
        if not sep or not node_name or not service_name:
            return None
        return node_name, service_name

    def _qualified_runtime_refs(self) -> set[str]:
        """Qualified refs for node-scoped runtime inventories.

        These let a top-level relationship endpoint resolve to a runtime
        service family or stable child record. This keeps runtime-observed
        logical state targetable without promoting those records to top-level
        SDL sections.
        """
        return collect_qualified_runtime_family_refs(self._s)

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
        ("content", True),
        ("accounts", True),
        ("agents", True),
        ("action_contracts", True),
        ("observation_boundaries", True),
        ("behavior_specifications", True),
        ("evidence_requirements", True),
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
        "evidence_requirements.",
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

        Non-spatial, non-resource elements (conditions, accounts,
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

        self._add_operating_scope_service_aliases(index)
        self._add_operating_scope_content_aliases(index)

        return {alias: set(candidates) for alias, candidates in index.items()}

    def _add_operating_scope_service_aliases(self, index: dict[str, set[str]]) -> None:
        # Services: qualified `nodes.<vm>.services.<svc>` refs plus bare
        # service names. The service-ref helper only emits names declared
        # on VM nodes (a service on a switch is meaningless), so no extra
        # filtering is needed here.
        for ref in self._qualified_service_refs():
            index[ref].add(ref)
            tail = ref.rsplit(".", 1)[-1]
            if tail:
                index[tail].add(ref)

    def _add_operating_scope_content_aliases(self, index: dict[str, set[str]]) -> None:
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
        self._verify_runtime_app_authorizations()
        self._verify_runtime_service_manager_units()
        self._verify_runtime_identity_authorities()
        self._verify_runtime_file_services()
        self._verify_runtime_security_monitoring_managers()
        self._verify_runtime_datastore_services()
        self._verify_runtime_platform_applications()
        self._verify_runtime_forwarding_agents()
        self._verify_runtime_orchestration_authorities()
        self._verify_runtime_mail_services()
        self._verify_features()
        self._verify_conditions()
        self._verify_vulnerabilities()
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
        self._verify_relationship_mail_access()
        self._verify_relationship_forwarding_edges()
        self._verify_relationship_service_integrations()
        self._verify_relationship_proxy_upstreams()
        self._verify_agents()
        self._verify_participant_behavior()
        self._verify_objectives()
        self._verify_workflows()
        self._verify_participant_outcomes()
        self._verify_evidence_requirements()
        self._verify_variables()
        self._verify_explicitness()
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

    @staticmethod
    def _split_runtime_ref(ref: object, *, surface: str) -> tuple[str, str] | None:
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

    def _node_runtime(self, node_name: str) -> object | None:
        """Return the ``runtime`` surface for ``node_name``, or None."""
        node = self._s.nodes.get(node_name)
        return getattr(node, "runtime", None) if node is not None else None

    @staticmethod
    def _database_service_id_from_tail(tail: str) -> str | None:
        """Service id from a ``<svc_id>`` (1 part) or ``<svc_id>.databases.<db_id>`` (3) tail."""
        tail_parts = tail.split(".")
        if len(tail_parts) == 1 or (len(tail_parts) == 3 and tail_parts[1] == "databases"):
            return tail_parts[0]
        return None

    def _resolve_database_service_ref(self, ref: object) -> object | None:
        """Resolve a qualified ``nodes.<node>.runtime.database_services.<id>`` ref.

        Accepts the database-service form and the ``.databases.<id>`` form; both
        resolve to the owning :class:`RuntimeDatabaseService` so a relationship's
        ``database_access`` can be checked against it.
        """
        split = self._split_runtime_ref(ref, surface="database_services")
        if split is None:
            return None
        node_name, tail = split
        svc_id = self._database_service_id_from_tail(tail)
        runtime = self._node_runtime(node_name)
        if svc_id is None or runtime is None:
            return None
        return next((s for s in runtime.database_services if s.database_service_id == svc_id), None)

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
        runtime = self._node_runtime(node_name)
        if "." in tail or runtime is None:
            return None
        return next((a for a in runtime.applications if a.application_id == tail), None)
