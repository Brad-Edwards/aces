"""Issue #603: placement realization into per-domain cloud-init."""

from __future__ import annotations

import pytest
from aces_backend_libvirt.realization import interpret_provisioning_plan
from aces_backend_protocols.capabilities import ProvisionerCapabilities
from aces_contracts.planning import PlannedResource, ProvisioningPlan, RuntimeDomain

NODE_ADDRESS = "provision.node.web"


def _narrowed_capabilities(**overrides) -> ProvisionerCapabilities:
    """A libvirt-shaped provisioner envelope narrowed for out-of-envelope tests.

    Libvirt's real manifest declares every governed account feature and both node
    types, so an out-of-envelope account-feature or switch term is only reachable
    against a deliberately narrower envelope injected via ``provisioner_capabilities``.
    """

    base: dict = {
        "name": "narrowed-provisioner",
        "supported_node_types": frozenset({"vm", "switch"}),
        "supported_os_families": frozenset({"linux"}),
        "supported_content_types": frozenset({"file"}),
        "supported_account_features": frozenset({"groups", "shell"}),
        "supports_acls": True,
        "supports_accounts": True,
    }
    base.update(overrides)
    return ProvisionerCapabilities(**base)


def _resource(resource_type: str, address: str, payload: dict) -> PlannedResource:
    return PlannedResource(
        address=address,
        domain=RuntimeDomain.PROVISIONING,
        resource_type=resource_type,
        payload=payload,
    )


def _node() -> PlannedResource:
    return _node_os("linux")


def _node_os(os_family: str) -> PlannedResource:
    return _resource(
        "node",
        NODE_ADDRESS,
        {
            "name": "web",
            "node_name": "web",
            "os_family": os_family,
            "spec": {
                "node": {"type": "vm", "source": {"name": "/img/base.qcow2"}, "resources": {"ram": 512, "cpu": 1}},
                "infrastructure": {"networks": ["lan"]},
            },
        },
    )


def _plan(*resources: PlannedResource) -> ProvisioningPlan:
    return ProvisioningPlan(resources={r.address: r for r in resources})


def _domain(realization, address: str = NODE_ADDRESS):
    return next(spec for spec in realization.domains if spec.address == address)


def test_node_without_placements_gets_hostname_only_cloud_init():
    realization = interpret_provisioning_plan(_plan(_node()))

    cloud_init = _domain(realization).cloud_init
    assert cloud_init.hostname == "web"
    assert cloud_init.is_empty is False  # hostname is present
    assert cloud_init.users == ()
    assert cloud_init.write_files == ()


def test_account_placement_realizes_user_with_all_features():
    account = _resource(
        "account-placement",
        "provision.account.admin",
        {
            "name": "admin",
            "account_name": "admin",
            "node_name": "web",
            "target_address": NODE_ADDRESS,
            "spec": {
                "username": "administrator",
                "groups": ["sudo", "wheel"],
                "shell": "/bin/bash",
                "home": "/home/administrator",
                "disabled": True,
                "auth_method": "ssh-key",
                "mail": "admin@example.test",
                "spn": "HTTP/web.example.test",
            },
        },
    )

    realization = interpret_provisioning_plan(_plan(_node(), account))
    cloud_init = _domain(realization).cloud_init

    user = cloud_init.users[0]
    assert user.name == "administrator"
    assert user.groups == ("sudo", "wheel")
    assert user.shell == "/bin/bash"
    assert user.home == "/home/administrator"
    assert user.lock_passwd is True  # disabled and/or non-password auth
    paths = {f.path: f.content for f in cloud_init.write_files}
    assert paths["/etc/aliases.d/aces-administrator"] == "administrator: admin@example.test\n"
    assert paths["/etc/aces/spn/administrator"] == "HTTP/web.example.test\n"
    assert ("newaliases",) in cloud_init.runcmd


def test_password_account_without_credentials_is_locked_closed():
    # A password account that carries no rendered credential must stay locked: an
    # unlocked account with no secret could permit a blank-password login.
    account = _resource(
        "account-placement",
        "provision.account.user",
        {
            "name": "user",
            "target_address": NODE_ADDRESS,
            "spec": {"username": "alice", "auth_method": "password"},
        },
    )

    realization = interpret_provisioning_plan(_plan(_node(), account))

    user = _domain(realization).cloud_init.users[0]
    assert user.lock_passwd is True
    assert user.ssh_authorized_keys == ()


def test_account_with_ssh_keys_renders_keys_and_stays_password_locked():
    account = _resource(
        "account-placement",
        "provision.account.ops",
        {
            "name": "ops",
            "target_address": NODE_ADDRESS,
            "spec": {"username": "ops", "ssh_authorized_keys": ["ssh-ed25519 AAAAKEY ops@host"]},
        },
    )

    realization = interpret_provisioning_plan(_plan(_node(), account))

    user = _domain(realization).cloud_init.users[0]
    assert user.ssh_authorized_keys == ("ssh-ed25519 AAAAKEY ops@host",)
    assert user.lock_passwd is True  # key auth does not require an unlocked password


def test_content_placement_file_with_text_becomes_write_file():
    content = _resource(
        "content-placement",
        "provision.content.flag",
        {
            "name": "flag",
            "target_node": "web",
            "target_address": NODE_ADDRESS,
            "spec": {"type": "file", "path": "/srv/flag.txt", "text": "ctf{libvirt}\n"},
        },
    )

    realization = interpret_provisioning_plan(_plan(_node(), content))
    files = {f.path: f.content for f in _domain(realization).cloud_init.write_files}

    assert files["/srv/flag.txt"] == "ctf{libvirt}\n"


def test_content_placement_directory_creates_dir_and_descriptor():
    content = _resource(
        "content-placement",
        "provision.content.data",
        {
            "name": "data",
            "target_address": NODE_ADDRESS,
            "spec": {"type": "directory", "destination": "/opt/data"},
        },
    )

    realization = interpret_provisioning_plan(_plan(_node(), content))
    cloud_init = _domain(realization).cloud_init

    assert ("mkdir", "-p", "/opt/data") in cloud_init.runcmd
    assert any(f.path == "/etc/aces/content/data.json" for f in cloud_init.write_files)


def test_feature_binding_service_installs_package_and_enables_service():
    feature = _resource(
        "feature-binding",
        "provision.feature.wazuh",
        {
            "name": "wazuh-agent",
            "node_name": "web",
            "node_address": NODE_ADDRESS,
            "spec": {"template": {"type": "service", "source": {"name": "wazuh-agent"}}},
        },
    )

    realization = interpret_provisioning_plan(_plan(_node(), feature))
    cloud_init = _domain(realization).cloud_init

    assert "wazuh-agent" in cloud_init.packages
    assert ("systemctl", "enable", "--now", "wazuh-agent") in cloud_init.runcmd


def test_account_descriptor_path_cannot_escape_via_malicious_username():
    # A username crafted to traverse out of the descriptor directory must not let
    # the cloud-init write_files target escape /etc/aces/spn/.
    account = _resource(
        "account-placement",
        "provision.account.evil",
        {
            "name": "evil",
            "target_address": NODE_ADDRESS,
            "spec": {"username": "../../etc/cron.d/aces", "spn": "HTTP/x", "ssh_authorized_keys": ["k"]},
        },
    )

    realization = interpret_provisioning_plan(_plan(_node(), account))
    paths = [f.path for f in _domain(realization).cloud_init.write_files]

    spn_paths = [p for p in paths if "/spn/" in p]
    assert spn_paths == ["/etc/aces/spn/etc_cron.d_aces"]
    assert not any(".." in p for p in paths)


def test_content_descriptor_path_cannot_escape_via_malicious_name():
    content = _resource(
        "content-placement",
        "provision.content.evil",
        {
            "name": "../../etc/cron.d/pwn",
            "target_address": NODE_ADDRESS,
            "spec": {"type": "dataset"},
        },
    )

    realization = interpret_provisioning_plan(_plan(_node(), content))
    paths = [f.path for f in _domain(realization).cloud_init.write_files]

    assert all(p.startswith("/etc/aces/content/") and ".." not in p for p in paths)


def test_runcmd_is_argv_form_so_malicious_paths_cannot_inject_shell():
    content = _resource(
        "content-placement",
        "provision.content.evil",
        {
            "name": "evil",
            "target_address": NODE_ADDRESS,
            "spec": {"type": "directory", "destination": "/opt/x; rm -rf /"},
        },
    )

    realization = interpret_provisioning_plan(_plan(_node(), content))

    # The metacharacter-bearing path is a single argv element, never split into
    # a shell command; cloud-init runs argv-list runcmd entries without a shell.
    assert ("mkdir", "-p", "/opt/x; rm -rf /") in _domain(realization).cloud_init.runcmd


def test_feature_realization_is_os_aware_for_windows():
    feature = _resource(
        "feature-binding",
        "provision.feature.sysmon",
        {
            "name": "sysmon",
            "node_address": NODE_ADDRESS,
            "spec": {"template": {"type": "service", "source": {"name": "sysmon"}}},
        },
    )

    realization = interpret_provisioning_plan(_plan(_node_os("windows"), feature))
    cloud_init = _domain(realization).cloud_init

    # Windows guest gets its native tooling, not Linux systemctl/apt.
    assert cloud_init.packages == ()
    assert ("choco", "install", "-y", "--no-progress", "sysmon") in cloud_init.runcmd
    assert not any("systemctl" in cmd for cmd in cloud_init.runcmd)


def test_node_acls_become_network_acls_on_the_domain():
    node = _resource(
        "node",
        NODE_ADDRESS,
        {
            "name": "web",
            "node_name": "web",
            "os_family": "linux",
            "spec": {
                "node": {"type": "vm"},
                "infrastructure": {
                    "networks": ["lan"],
                    "acls": [
                        {
                            "name": "allow-http",
                            "direction": "in",
                            "from_net": "wan",
                            "to_net": "lan",
                            "protocol": "tcp",
                            "ports": [80],
                            "action": "allow",
                        },
                        {"name": "deny-all", "protocol": "any", "action": "deny"},
                    ],
                },
            },
        },
    )
    wan = _resource(
        "network",
        "provision.network.wan",
        {"name": "wan", "spec": {"infrastructure": {"properties": {"cidr": "10.0.0.0/24"}}}},
    )
    lan = _resource(
        "network",
        "provision.network.lan",
        {"name": "lan", "spec": {"infrastructure": {"properties": {"cidr": "192.168.1.0/24"}}}},
    )

    realization = interpret_provisioning_plan(_plan(node, wan, lan))
    acls = _domain(realization).network_acls

    assert [a.name for a in acls] == ["allow-http", "deny-all"]
    http = acls[0]
    assert http.action == "accept"
    assert http.direction == "in"
    assert http.protocol == "tcp"
    assert http.src_cidr == "10.0.0.0/24"
    assert http.dst_cidr == "192.168.1.0/24"
    assert http.ports == (80,)
    assert acls[1].action == "drop"
    assert acls[1].protocol == "all"


def _node_with_acl(acl: dict) -> PlannedResource:
    return _resource(
        "node",
        NODE_ADDRESS,
        {
            "name": "web",
            "node_name": "web",
            "os_family": "linux",
            "spec": {"node": {"type": "vm"}, "infrastructure": {"networks": ["lan"], "acls": [acl]}},
        },
    )


def test_acl_with_unresolved_source_network_fails_closed_not_open():
    # An allow rule whose source network has no resolvable CIDR must NOT widen into
    # an allow-from-anywhere rule: it is rejected with an ERROR diagnostic.
    acl = {"name": "allow-http", "action": "allow", "protocol": "tcp", "ports": [80], "from_net": "typo-net"}

    realization = interpret_provisioning_plan(_plan(_node_with_acl(acl)))

    assert [d.code for d in realization.diagnostics] == ["libvirt-backend.realization.invalid-acl"]
    assert realization.diagnostics[0].severity.name == "ERROR"
    # The fail-open rule was never emitted onto the domain.
    assert _domain(realization).network_acls == ()


def test_acl_with_unknown_action_fails_closed():
    acl = {"name": "weird", "action": "permit-maybe", "protocol": "tcp", "ports": [22]}

    realization = interpret_provisioning_plan(_plan(_node_with_acl(acl)))

    assert [d.code for d in realization.diagnostics] == ["libvirt-backend.realization.invalid-acl"]
    assert _domain(realization).network_acls == ()


def test_acl_with_invalid_port_fails_closed():
    acl = {"name": "bad-port", "action": "allow", "protocol": "tcp", "ports": [70000]}

    realization = interpret_provisioning_plan(_plan(_node_with_acl(acl)))

    assert [d.code for d in realization.diagnostics] == ["libvirt-backend.realization.invalid-acl"]


def test_acl_with_wildcard_protocol_and_ports_fails_closed():
    # protocol=any + ports=[443] must not collapse into an all-protocol, all-port
    # allow: a port scope is only meaningful for tcp/udp, so reject it.
    acl = {"name": "wild", "action": "allow", "protocol": "any", "ports": [443]}

    realization = interpret_provisioning_plan(_plan(_node_with_acl(acl)))

    assert [d.code for d in realization.diagnostics] == ["libvirt-backend.realization.invalid-acl"]
    assert _domain(realization).network_acls == ()


def test_unsupported_resource_type_is_rejected_at_plan_admission():
    bogus = _resource("mystery", "provision.mystery.x", {"name": "x"})

    with pytest.raises(ValueError, match="resource_type must belong"):
        _plan(_node(), bogus)


def test_placement_targeting_unknown_node_fails_closed_with_diagnostic():
    # A placement that names a node absent from this plan must not be silently
    # dropped while apply reports success: it yields an ERROR diagnostic.
    orphan = _resource(
        "account-placement",
        "provision.account.ghost",
        {"name": "ghost", "target_address": "provision.node.missing", "spec": {"username": "ghost"}},
    )

    realization = interpret_provisioning_plan(_plan(_node(), orphan))

    assert [d.code for d in realization.diagnostics] == ["libvirt-backend.realization.unbound-placement"]
    assert realization.diagnostics[0].severity.name == "ERROR"
    # The orphaned placement contributed nothing to the real node's cloud-init.
    assert _domain(realization).cloud_init.users == ()


def test_placement_without_target_reference_fails_closed_with_diagnostic():
    untargeted = _resource(
        "feature-binding",
        "provision.feature.svc",
        {"name": "svc", "spec": {"service": "nginx"}},
    )

    realization = interpret_provisioning_plan(_plan(_node(), untargeted))

    assert [d.code for d in realization.diagnostics] == ["libvirt-backend.realization.unbound-placement"]


# --- issue #605: typed capability-envelope diagnostics --------------------------


def test_out_of_envelope_node_type_fails_closed():
    # A node type outside the declared manifest envelope (an ungoverned/extension
    # term the backend does not realize) must block rather than realize a domain.
    node = _resource(
        "node",
        NODE_ADDRESS,
        {
            "name": "gw",
            "node_name": "gw",
            "node_type": "router",
            "os_family": "linux",
            "spec": {"node": {"type": "router"}, "infrastructure": {}},
        },
    )

    realization = interpret_provisioning_plan(_plan(node))

    assert [d.code for d in realization.diagnostics] == ["libvirt-backend.realization.unsupported-node-type"]
    assert realization.diagnostics[0].severity.name == "ERROR"
    assert realization.diagnostics[0].address == NODE_ADDRESS
    assert "router" in realization.diagnostics[0].message


def test_out_of_envelope_os_family_fails_closed():
    realization = interpret_provisioning_plan(_plan(_node_os("solaris")))

    assert [d.code for d in realization.diagnostics] == ["libvirt-backend.realization.unsupported-os-family"]
    assert "solaris" in realization.diagnostics[0].message


def test_out_of_envelope_content_type_fails_closed():
    # An unsupported content type must NOT fall through to a silent no-op cloud-init
    # contribution: it yields a blocking diagnostic.
    content = _resource(
        "content-placement",
        "provision.content.disk",
        {"name": "disk", "target_address": NODE_ADDRESS, "spec": {"type": "raw-disk"}},
    )

    realization = interpret_provisioning_plan(_plan(_node(), content))

    assert [d.code for d in realization.diagnostics] == ["libvirt-backend.realization.unsupported-content-type"]
    assert "raw-disk" in realization.diagnostics[0].message
    # The unsupported content contributed nothing to the domain's cloud-init.
    assert _domain(realization).cloud_init.write_files == ()


def test_governed_vocabulary_realizes_without_envelope_error():
    # The full issue #603 governed vocabulary (all content types + account features)
    # is in-envelope and must realize without any capability-envelope diagnostic.
    account = _resource(
        "account-placement",
        "provision.account.admin",
        {
            "name": "admin",
            "target_address": NODE_ADDRESS,
            "spec": {
                "username": "administrator",
                "groups": ["sudo"],
                "shell": "/bin/bash",
                "home": "/home/administrator",
                "disabled": True,
                "auth_method": "ssh-key",
                "mail": "admin@example.test",
                "spn": "HTTP/web.example.test",
            },
        },
    )
    file_content = _resource(
        "content-placement",
        "provision.content.f",
        {"name": "f", "target_address": NODE_ADDRESS, "spec": {"type": "file", "path": "/srv/f", "text": "x\n"}},
    )
    dir_content = _resource(
        "content-placement",
        "provision.content.d",
        {"name": "d", "target_address": NODE_ADDRESS, "spec": {"type": "directory", "destination": "/opt/d"}},
    )
    dataset_content = _resource(
        "content-placement",
        "provision.content.ds",
        {"name": "ds", "target_address": NODE_ADDRESS, "spec": {"type": "dataset"}},
    )

    realization = interpret_provisioning_plan(_plan(_node(), account, file_content, dir_content, dataset_content))

    envelope_codes = [d.code for d in realization.diagnostics if "unsupported-" in d.code]
    assert envelope_codes == []


def test_account_feature_outside_narrowed_envelope_fails_closed():
    caps = _narrowed_capabilities(supported_account_features=frozenset({"groups"}))
    account = _resource(
        "account-placement",
        "provision.account.admin",
        {
            "name": "admin",
            "target_address": NODE_ADDRESS,
            "spec": {"username": "administrator", "groups": ["sudo"], "shell": "/bin/bash"},
        },
    )

    realization = interpret_provisioning_plan(_plan(_node(), account), provisioner_capabilities=caps)

    # 'groups' is in the narrowed envelope; 'shell' is not.
    assert [d.code for d in realization.diagnostics] == ["libvirt-backend.realization.unsupported-account-feature"]
    assert "shell" in realization.diagnostics[0].message
    assert realization.diagnostics[0].address == "provision.account.admin"


def test_switch_node_type_outside_narrowed_envelope_fails_closed():
    caps = _narrowed_capabilities(supported_node_types=frozenset({"vm"}))
    network = _resource(
        "network",
        "provision.network.lan",
        {"name": "lan", "spec": {"infrastructure": {"properties": {}}}},
    )

    realization = interpret_provisioning_plan(_plan(network), provisioner_capabilities=caps)

    assert [d.code for d in realization.diagnostics] == ["libvirt-backend.realization.unsupported-node-type"]
    assert "switch" in realization.diagnostics[0].message
