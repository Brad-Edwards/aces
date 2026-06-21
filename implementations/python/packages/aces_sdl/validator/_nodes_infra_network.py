"""SemanticValidator _NodesInfraNetworkMixin (split from validator.py).

Part of the SemanticValidator mixin composition; see __init__.py.
"""

from ipaddress import ip_address, ip_network

from ..infrastructure import SimpleProperties
from ..nodes import MAX_NODE_NAME_LENGTH, NodeType


class _NodesInfraNetworkMixin:
    # ------------------------------------------------------------------
    # OCR validation passes
    # ------------------------------------------------------------------

    def _verify_nodes(self) -> None:
        for name, node in self._s.nodes.items():
            if len(name) > MAX_NODE_NAME_LENGTH:
                self._err(f"Node '{name}' name exceeds 35 characters")
            self._verify_node_ref_role_map(name, node, node.features, self._s.features, kind="feature")
            self._verify_node_ref_role_map(name, node, node.conditions, self._s.conditions, kind="condition")
            self._verify_node_ref_role_map(name, node, node.injects, self._s.injects, kind="inject")
            for vuln_name in node.vulnerabilities:
                if self._is_unresolved_var(vuln_name):
                    continue
                if vuln_name not in self._s.vulnerabilities:
                    self._err(f"Node '{name}' references undefined vulnerability '{vuln_name}'")

    def _verify_node_ref_role_map(
        self, name: str, node: object, mapping: dict[str, str], valid: object, *, kind: str
    ) -> None:
        for ref_name, role_name in mapping.items():
            if ref_name not in valid:
                self._err(f"Node '{name}' references undefined {kind} '{ref_name}'")
            if role_name and not self._is_unresolved_var(role_name) and role_name not in node.roles:
                self._err(f"Node '{name}' {kind} '{ref_name}' references undefined role '{role_name}'")

    def _verify_infrastructure(self) -> None:
        for name, infra in self._s.infrastructure.items():
            if name not in self._s.nodes:
                self._err(f"Infrastructure '{name}' does not match any defined node")
            self._verify_infra_links(name, infra)
            self._verify_infra_dependencies(name, infra)
            self._verify_infra_count(name, infra)
            self._verify_infra_property_ips(name, infra)
            self._verify_infra_acls(name, infra)

    def _verify_infra_links(self, name: str, infra: object) -> None:
        for link in infra.links:
            if self._is_unresolved_var(link):
                continue
            if link not in self._s.infrastructure:
                self._err(f"Infrastructure '{name}' links to undefined '{link}'")
            elif not self._is_switch_node(link):
                self._err(f"Infrastructure '{name}' link '{link}' must reference a switch/network entry")

    def _verify_infra_dependencies(self, name: str, infra: object) -> None:
        for dep in infra.dependencies:
            if self._is_unresolved_var(dep):
                continue
            if dep not in self._s.infrastructure:
                self._err(f"Infrastructure '{name}' depends on undefined '{dep}'")

    def _verify_infra_count(self, name: str, infra: object) -> None:
        # Switch nodes cannot have count > 1.
        if name not in self._s.nodes:
            return
        node = self._s.nodes[name]
        if node.type == NodeType.SWITCH and isinstance(infra.count, int) and infra.count > 1:
            self._err(f"Switch node '{name}' cannot have count > 1")
        if node.type == NodeType.VM and node.conditions and isinstance(infra.count, int) and infra.count > 1:
            self._err(f"Node '{name}' has conditions and cannot have count > 1")

    def _verify_infra_property_ips(self, name: str, infra: object) -> None:
        # Validate complex-properties IP assignments within their linked CIDR.
        if not isinstance(infra.properties, list):
            return
        for prop_entry in infra.properties:
            for link_name, ip_str in prop_entry.items():
                self._verify_property_ip(name, infra, link_name, ip_str)

    def _verify_property_ip(self, name: str, infra: object, link_name: str, ip_str: str) -> None:
        if self._is_unresolved_var(link_name):
            return
        if link_name not in infra.links:
            self._err(f"Infrastructure '{name}' property references unlinked node '{link_name}'")
        if not self._is_switch_node(link_name):
            self._err(f"Infrastructure '{name}' property link '{link_name}' must reference a switch/network entry")
            return
        linked_infra = self._s.infrastructure.get(link_name)
        if linked_infra is None or not isinstance(linked_infra.properties, SimpleProperties):
            if linked_infra is not None:
                self._err(
                    f"Infrastructure '{name}' property link '{link_name}' must reference a network with CIDR properties"
                )
            return
        cidr = linked_infra.properties.cidr
        if not self._is_unresolved_var(ip_str) and not self._is_unresolved_var(cidr):
            self._verify_property_ip_in_cidr(name, link_name, ip_str, cidr)

    def _verify_property_ip_in_cidr(self, name: str, link_name: str, ip_str: str, cidr: str) -> None:
        try:
            net = ip_network(cidr, strict=False)
        except ValueError:
            self._err(f"Infrastructure '{link_name}' has invalid CIDR {cidr}")
            return
        try:
            addr = ip_address(ip_str)
        except ValueError:
            self._err(f"Infrastructure '{name}' has invalid IP assignment '{ip_str}' for link '{link_name}'")
            return
        if addr not in net:
            self._err(f"Infrastructure '{name}' IP {ip_str} not within '{link_name}' CIDR {cidr}")

    def _verify_infra_acls(self, name: str, infra: object) -> None:
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
                # malformed addresses are reported by the model-level validator
                continue
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
        owner_label = f"Node '{node_name}' runtime network sensor '{sensor.network_sensor_id}'"
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
                sensor_id=sensor.network_sensor_id,
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
            sensor_ids = {sensor.network_sensor_id for sensor in runtime.network_sensors}
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
        owner_label = f"Node '{node_name}' runtime network detection engine '{engine.network_detection_engine_id}'"
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
        self._verify_detection_network_sets(owner_label, engine)
        for stream in engine.output_streams:
            self._verify_dns_file_refs(
                f"{owner_label} output_stream '{stream.stream_id}'",
                [stream.path] if stream.path else [],
                field_name="path",
                observed_paths=observed_paths,
            )
        self._verify_detection_control_channels(node_name, owner_label, engine, service_names, observed_paths)

    def _verify_detection_network_sets(self, owner_label: str, engine: object) -> None:
        for network_set in engine.network_sets:
            set_label = f"{owner_label} network_set '{network_set.set_id}'"
            for network_ref in network_set.network_refs:
                self._verify_network_detection_network_ref(set_label, network_ref)

    def _verify_detection_control_channels(
        self, node_name: str, owner_label: str, engine: object, service_names: set[str], observed_paths: set[str]
    ) -> None:
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
