"""SemanticValidator _RuntimeOrchestrationMixin (split from _runtime_platform.py).

Part of the SemanticValidator mixin composition; see __init__.py.
"""

from .._base import is_variable_ref
from ..runtime_mounts import RuntimeControlInterfaceAccess, RuntimeControlInterfaceKind
from ..runtime_orchestration import RuntimeOrchestrationPrivilegeClass


class _RuntimeOrchestrationMixin:
    def _verify_runtime_orchestration_authorities(self) -> None:
        """Validate observed container-spawn orchestration-authority inventories.

        Each authority's ``control_interface_ref``, when present and concrete,
        must resolve to a :class:`RuntimeControlInterface` declared in the same
        node's ``runtime.local_control_interfaces`` (by ``control_interface_id``).
        For a ``host_root_equivalent`` privilege class, the referenced control
        interface must additionally be a read-write docker socket (a read-write
        unix socket whose path is a ``docker.sock``), making the host-root
        privilege-escalation fact resolvable at scenario scope. The
        model-local ``require_profile_for_privilege_class`` guard has already
        rejected a host-root-equivalent authority that carries no concrete
        ``control_interface_ref``.
        """
        for node_name, node in self._s.nodes.items():
            runtime = getattr(node, "runtime", None)
            if runtime is None or not runtime.orchestration_authorities:
                continue
            interfaces_by_id = {
                interface.control_interface_id: interface
                for interface in getattr(runtime, "local_control_interfaces", [])
                if interface.control_interface_id
            }
            for authority in runtime.orchestration_authorities:
                self._verify_orchestration_authority(
                    node_name=node_name,
                    authority=authority,
                    interfaces_by_id=interfaces_by_id,
                )

    def _verify_orchestration_authority(
        self,
        *,
        node_name: str,
        authority: object,
        interfaces_by_id: dict[str, object],
    ) -> None:
        owner_label = f"Node '{node_name}' runtime orchestration authority '{authority.orchestration_authority_id}'"
        ref = getattr(authority, "control_interface_ref", "")
        if not ref or self._is_unresolved_var(ref):
            return
        interface = interfaces_by_id.get(ref)
        if interface is None:
            self._err(
                f"{owner_label} control_interface_ref '{ref}' does not resolve to a "
                f"control interface in the same node's runtime.local_control_interfaces"
            )
            return
        privilege = getattr(authority, "privilege_class", None)
        if (
            isinstance(privilege, RuntimeOrchestrationPrivilegeClass)
            and privilege is RuntimeOrchestrationPrivilegeClass.HOST_ROOT_EQUIVALENT
        ):
            self._verify_host_root_control_interface(owner_label=owner_label, ref=ref, interface=interface)

    @staticmethod
    def _control_interface_is_docker_socket(interface: object) -> bool:
        """Return whether a control interface is a read-write docker unix socket."""
        access = getattr(interface, "access", None)
        kind = getattr(interface, "kind", None)
        path = getattr(interface, "path", "") or ""
        is_read_write = access is RuntimeControlInterfaceAccess.READ_WRITE
        is_unix_socket = kind is RuntimeControlInterfaceKind.UNIX_SOCKET
        is_docker_sock = isinstance(path, str) and path.endswith("docker.sock")
        return is_read_write and is_unix_socket and is_docker_sock

    def _verify_host_root_control_interface(
        self,
        *,
        owner_label: str,
        ref: str,
        interface: object,
    ) -> None:
        # ``${var}`` placeholders on the interface's access/kind/path are
        # permissive: a deferred discriminator cannot be proven non-conformant.
        access = getattr(interface, "access", None)
        kind = getattr(interface, "kind", None)
        path = getattr(interface, "path", "") or ""
        if is_variable_ref(access) or is_variable_ref(kind) or is_variable_ref(path):
            return
        if not self._control_interface_is_docker_socket(interface):
            self._err(
                f"{owner_label} privilege_class 'host_root_equivalent' control_interface_ref '{ref}' "
                f"must resolve to a read-write docker socket "
                f"(access 'read_write', kind 'unix_socket', path ending in 'docker.sock')"
            )
