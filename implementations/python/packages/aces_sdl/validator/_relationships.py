"""SemanticValidator _RelationshipsMixin (split from validator.py).

Part of the SemanticValidator mixin composition; see __init__.py.
"""

from ..runtime_forwarding_agent_vocab import RuntimeForwardingProtocol
from ..runtime_security_monitoring import RuntimeSecurityMonitoringListenerRole
from ._support import _NODES_PREFIX


class _RelationshipsMixin:
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

    # ------------------------------------------------------------------ #
    # Typed relationship subtypes (SCN-010 §5.7)
    # ------------------------------------------------------------------ #

    def _verify_relationship_forwarding_edges(self) -> None:
        """Validate typed ``forwarding_edge`` blocks on relationship edges.

        ``forwarder_ref`` must resolve to a ``RuntimeForwardingAgent`` (by
        ``forwarding_agent_id``) on some node. AGREEMENT GUARD: when that agent
        carries ``ship_targets``, the edge's ``target_listener_role`` and
        ``protocol`` — where both sides are concrete — must be consistent with
        at least one ship_target, so the inter-node trust edge and the
        agent-side shipping state cannot disagree (SCN-010 §5.7).
        """
        for name, rel in self._s.relationships.items():
            edge = rel.forwarding_edge
            if edge is None:
                continue
            label = f"Relationship '{name}'"
            ref = edge.forwarder_ref
            if not ref or self._is_unresolved_var(ref):
                continue
            agents = self._resolve_forwarding_agent_refs(ref)
            if not agents:
                self._err(
                    f"{label} forwarding_edge forwarder_ref '{ref}' does not resolve to a forwarding agent "
                    "on any node or in scenario forwarding_agents"
                )
                continue
            if len(agents) > 1:
                self._err(
                    f"{label} forwarding_edge forwarder_ref '{ref}' resolves to multiple forwarding agents; "
                    "forwarding_agent_id values must be unique across scenario forwarding_agents and node runtimes"
                )
                continue
            self._check_forwarding_edge_agreement(edge, agents[0], label)

    def _resolve_forwarding_agent_refs(self, ref: str) -> list[object]:
        """Resolve a ``forwarding_agent_id`` across node and scenario registries."""
        matches: list[object] = [agent for agent in self._s.forwarding_agents if agent.forwarding_agent_id == ref]
        for node in self._s.nodes.values():
            runtime = getattr(node, "runtime", None)
            if runtime is None:
                continue
            for agent in getattr(runtime, "forwarding_agents", []):
                if agent.forwarding_agent_id == ref:
                    matches.append(agent)
        return matches

    def _check_forwarding_edge_agreement(self, edge: object, agent: object, label: str) -> None:
        ship_targets = list(getattr(agent, "ship_targets", []))
        if not ship_targets:
            return
        agent_id = agent.forwarding_agent_id
        self._check_forwarding_edge_protocol_agreement(edge, ship_targets, agent_id, label)
        self._check_forwarding_edge_role_agreement(edge, ship_targets, agent_id, label)

    def _check_forwarding_edge_protocol_agreement(
        self, edge: object, ship_targets: list, agent_id: str, label: str
    ) -> None:
        # The edge ``protocol`` is a free string; agreement is asserted only
        # against ship_target protocols that are concrete enum members. If no
        # ship_target carries a concrete protocol, nothing concrete to compare.
        edge_protocol = getattr(edge, "protocol", "")
        if not edge_protocol or self._is_unresolved_var(edge_protocol):
            return
        target_protocols = [t.protocol.value for t in ship_targets if isinstance(t.protocol, RuntimeForwardingProtocol)]
        if not target_protocols:
            return
        if edge_protocol not in target_protocols:
            self._err(
                f"{label} forwarding_edge protocol '{edge_protocol}' does not match any ship_target "
                f"protocol on forwarding agent '{agent_id}' (one of: {', '.join(sorted(set(target_protocols)))})"
            )

    def _check_forwarding_edge_role_agreement(
        self, edge: object, ship_targets: list, agent_id: str, label: str
    ) -> None:
        # An ``agent_event_ingestion`` listener role requires a ship_target with
        # an ingestion endpoint; an ``agent_enrollment`` role requires one with
        # an enrollment endpoint. Other roles impose no ship_target shape.
        role = getattr(edge, "target_listener_role", None)
        if not isinstance(role, RuntimeSecurityMonitoringListenerRole):
            return
        if role is RuntimeSecurityMonitoringListenerRole.AGENT_EVENT_INGESTION:
            if not any(t.has_ingestion_endpoint() for t in ship_targets):
                self._err(
                    f"{label} forwarding_edge target_listener_role 'agent_event_ingestion' has no agreeing "
                    f"ship_target carrying an ingestion endpoint on forwarding agent '{agent_id}'"
                )
        elif role is RuntimeSecurityMonitoringListenerRole.AGENT_ENROLLMENT:
            if not any(t.has_enrollment_endpoint() for t in ship_targets):
                self._err(
                    f"{label} forwarding_edge target_listener_role 'agent_enrollment' has no agreeing "
                    f"ship_target carrying an enrollment endpoint on forwarding agent '{agent_id}'"
                )

    def _verify_relationship_service_integrations(self) -> None:
        """Validate typed ``service_integration`` blocks on relationship edges.

        ``consumer_ref``/``engine_ref`` (when concrete) must resolve to platform
        applications by ``platform_application_id``; a concrete
        ``auth_principal_ref`` must resolve to the engine application's
        referenced ``app_authorization`` store when ``authorization_ref`` is set
        (the integration authenticates into the engine's internal RBAC store).
        """
        for name, rel in self._s.relationships.items():
            integration = rel.service_integration
            if integration is None:
                continue
            label = f"Relationship '{name}'"
            self._check_service_integration_endpoint(integration.consumer_ref, "consumer_ref", label)
            engine = self._check_service_integration_endpoint(integration.engine_ref, "engine_ref", label)
            self._check_service_integration_auth_principal(integration.auth_principal_ref, engine, label)

    def _check_service_integration_endpoint(self, ref: str, field_name: str, label: str) -> object | None:
        if not ref or self._is_unresolved_var(ref):
            return None
        resolved = self._resolve_platform_application_ref(ref)
        if resolved is None:
            self._err(
                f"{label} service_integration {field_name} '{ref}' does not resolve to a "
                f"platform application on any node"
            )
            return None
        return resolved[1]

    def _resolve_platform_application_ref(self, ref: str) -> tuple[str, object] | None:
        """Resolve a ``platform_application_id`` to (node_name, application)."""
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None:
                continue
            for application in getattr(runtime, "platform_applications", []):
                if application.platform_application_id == ref:
                    return node_name, application
        return None

    def _check_service_integration_auth_principal(self, ref: str, engine: object | None, label: str) -> None:
        if not ref or self._is_unresolved_var(ref) or engine is None:
            return
        node_name = self._node_name_of_platform_application(engine)
        if node_name is None:
            return
        node = self._s.nodes.get(node_name)
        runtime = getattr(node, "runtime", None) if node is not None else None
        authorizations = list(getattr(runtime, "app_authorizations", []))
        authorization_ref = getattr(engine, "authorization_ref", "")
        if authorization_ref and not self._is_unresolved_var(authorization_ref):
            authorizations = [
                authorization
                for authorization in authorizations
                if getattr(authorization, "app_authorization_id", "") == authorization_ref
            ]
            if not authorizations:
                # The runtime platform application validator reports the bad
                # authorization_ref; avoid emitting a misleading principal-scope
                # error from this relationship pass as well.
                return
        principal_ids = {
            principal.principal_id for authorization in authorizations for principal in authorization.principals
        }
        if ref not in principal_ids:
            scope = (
                f"authorization '{authorization_ref}'"
                if authorization_ref and not self._is_unresolved_var(authorization_ref)
                else "an app_authorization principal"
            )
            self._err(
                f"{label} service_integration auth_principal_ref '{ref}' does not resolve to "
                f"{scope} on the engine application's node '{node_name}'"
            )

    def _node_name_of_platform_application(self, application: object) -> str | None:
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None:
                continue
            if application in getattr(runtime, "platform_applications", []):
                return node_name
        return None

    def _verify_relationship_proxy_upstreams(self) -> None:
        """Validate typed ``proxy_upstream`` blocks on relationship edges.

        ``route_ref`` must resolve to an application route (by ``route_id``) on
        the relationship's ``source`` proxy; ``upstream_node_ref`` /
        ``upstream_service_ref`` (when concrete) must resolve. AGREEMENT GUARD:
        when the referenced route ALSO carries an ``upstream_target``, the shared
        facts (target node, target service, and the TLS-termination boolean) MUST
        agree between ``route.upstream_target`` and the ``RelationshipProxyUpstream``
        so the same fact recorded at two scopes is never silently duplicated and
        contradictory (SCN-010 §5.7).
        """
        for name, rel in self._s.relationships.items():
            upstream = rel.proxy_upstream
            if upstream is None:
                continue
            label = f"Relationship '{name}'"
            target_node_name = self._check_proxy_upstream_node_ref(
                upstream.upstream_node_ref,
                label,
                context="proxy_upstream",
                field_name="upstream_node_ref",
            )
            self._check_proxy_upstream_service_ref(
                upstream.upstream_service_ref,
                upstream_node_ref=target_node_name or "",
                relationship_target=rel.target,
                label=label,
                context="proxy_upstream",
                field_name="upstream_service_ref",
            )
            route = self._check_proxy_upstream_route_ref(upstream.route_ref, rel.source, label)
            if route is not None:
                self._check_proxy_upstream_agreement(upstream, route, label, relationship_target=rel.target)

    def _check_proxy_upstream_node_ref(
        self,
        node_ref: str,
        label: str,
        *,
        context: str,
        field_name: str,
    ) -> str | None:
        if not node_ref or self._is_unresolved_var(node_ref):
            return None
        if node_ref not in self._s.nodes:
            self._err(f"{label} {context} {field_name} '{node_ref}' does not resolve to a defined node")
            return None
        return node_ref

    def _check_proxy_upstream_service_ref(
        self,
        service_ref: str,
        *,
        upstream_node_ref: str,
        relationship_target: str,
        label: str,
        context: str,
        field_name: str,
    ) -> None:
        if not service_ref or self._is_unresolved_var(service_ref):
            return
        resolved = self._resolve_upstream_service_ref(
            service_ref,
            upstream_node_ref=upstream_node_ref,
            relationship_target=relationship_target,
        )
        if resolved is None:
            self._err(
                f"{label} {context} {field_name} '{service_ref}' cannot be resolved without a concrete upstream node"
            )
            return
        node_name, service_name = resolved
        expected_node_name = upstream_node_ref or self._node_name_from_relationship_target(relationship_target)
        if expected_node_name and node_name != expected_node_name:
            self._err(
                f"{label} {context} {field_name} '{service_ref}' must reference a service "
                f"on upstream node '{expected_node_name}'"
            )
            return
        node = self._s.nodes.get(node_name)
        if node is None:
            self._err(f"{label} {context} upstream service node '{node_name}' does not resolve to a defined node")
            return
        if service_name not in self._node_service_names(node):
            self._err(
                f"{label} {context} {field_name} '{service_ref}' does not resolve to a service on node '{node_name}'"
            )

    def _resolve_upstream_service_ref(
        self,
        service_ref: str,
        *,
        upstream_node_ref: str,
        relationship_target: str,
    ) -> tuple[str, str] | None:
        split = self._split_node_service_ref(service_ref)
        if split is not None:
            return split
        node_name = ""
        if upstream_node_ref and not self._is_unresolved_var(upstream_node_ref):
            node_name = upstream_node_ref
        else:
            target_node_name = self._node_name_from_relationship_target(relationship_target)
            if target_node_name is not None:
                node_name = target_node_name
        if not node_name:
            return None
        return node_name, service_ref

    def _node_name_from_relationship_target(self, target: object) -> str | None:
        if not isinstance(target, str) or self._is_unresolved_var(target):
            return None
        if target in self._s.nodes:
            return target
        service_split = self._split_node_service_ref(target)
        if service_split is not None:
            node_name, _service_name = service_split
            return node_name if node_name in self._s.nodes else None
        if target.startswith(_NODES_PREFIX):
            node_name, sep, _tail = target[len(_NODES_PREFIX) :].partition(".runtime.")
            if sep and node_name in self._s.nodes:
                return node_name
        return None

    def _check_proxy_upstream_route_ref(self, route_ref: str, source: str, label: str) -> object | None:
        if not route_ref or self._is_unresolved_var(route_ref):
            return None
        routes = self._source_application_routes(source)
        if routes is None:
            # The source does not resolve to a runtime application surface; the
            # generic relationship endpoint check already reports an unresolved
            # source, so the route_ref check is deferred rather than duplicated.
            return None
        route = routes.get(route_ref)
        if route is None:
            self._err(
                f"{label} proxy_upstream route_ref '{route_ref}' does not resolve to an "
                f"application route on source '{source}'"
            )
        return route

    def _source_application_routes(self, source: str) -> dict[str, object] | None:
        """Collect ``route_id``->route for every application surface on ``source``.

        ``source`` may be a qualified ``nodes.<node>.runtime.applications.<id>``
        ref or a bare node name; either way the proxy route lives on that node's
        application surface(s).
        """
        application = self._resolve_application_ref(source)
        if application is not None:
            return {route.route_id: route for route in application.routes}
        node = self._s.nodes.get(source)
        runtime = getattr(node, "runtime", None) if node is not None else None
        if runtime is None:
            return None
        routes: dict[str, object] = {}
        for application in getattr(runtime, "applications", []):
            for route in application.routes:
                routes[route.route_id] = route
        return routes

    def _check_proxy_upstream_agreement(
        self,
        upstream: object,
        route: object,
        label: str,
        *,
        relationship_target: str,
    ) -> None:
        target = getattr(route, "upstream_target", None)
        if target is None:
            return
        self._assert_shared_field_agreement(
            label,
            field_label="upstream node",
            relationship_value=getattr(upstream, "upstream_node_ref", ""),
            route_value=getattr(target, "target_node_ref", ""),
        )
        self._assert_shared_field_agreement(
            label,
            field_label="upstream service",
            relationship_value=getattr(upstream, "upstream_service_ref", ""),
            route_value=getattr(target, "target_service", ""),
            upstream_node_ref=getattr(upstream, "upstream_node_ref", "") or getattr(target, "target_node_ref", ""),
            relationship_target=relationship_target,
        )
        self._assert_shared_bool_agreement(
            label,
            field_label="TLS-termination",
            relationship_value=getattr(upstream, "client_tls_terminated", None),
            route_value=getattr(target, "tls_terminated_here", None),
        )

    def _assert_shared_field_agreement(
        self,
        label: str,
        *,
        field_label: str,
        relationship_value: str,
        route_value: str,
        upstream_node_ref: str = "",
        relationship_target: str = "",
    ) -> None:
        if not relationship_value or self._is_unresolved_var(relationship_value):
            return
        if not route_value or self._is_unresolved_var(route_value):
            return
        if self._shared_field_values_agree(
            field_label=field_label,
            relationship_value=relationship_value,
            route_value=route_value,
            upstream_node_ref=upstream_node_ref,
            relationship_target=relationship_target,
        ):
            return
        else:
            self._err(
                f"{label} proxy_upstream {field_label} '{relationship_value}' disagrees with the "
                f"route's upstream_target value '{route_value}'"
            )

    def _shared_field_values_agree(
        self,
        *,
        field_label: str,
        relationship_value: str,
        route_value: str,
        upstream_node_ref: str,
        relationship_target: str,
    ) -> bool:
        if field_label != "upstream service":
            return relationship_value == route_value
        relationship_ref = self._resolve_upstream_service_ref(
            relationship_value,
            upstream_node_ref=upstream_node_ref,
            relationship_target=relationship_target,
        )
        route_ref = self._resolve_upstream_service_ref(
            route_value,
            upstream_node_ref=upstream_node_ref,
            relationship_target=relationship_target,
        )
        if relationship_ref is None or route_ref is None:
            return relationship_value == route_value
        return relationship_ref == route_ref

    def _assert_shared_bool_agreement(
        self, label: str, *, field_label: str, relationship_value: object, route_value: object
    ) -> None:
        if not isinstance(relationship_value, bool) or not isinstance(route_value, bool):
            return
        if relationship_value != route_value:
            self._err(
                f"{label} proxy_upstream {field_label} '{relationship_value}' disagrees with the "
                f"route's upstream_target value '{route_value}'"
            )
