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
