"""Issue #603: pure NoCloud cloud-init rendering for the libvirt backend."""

from __future__ import annotations

import json

from raes_backend_libvirt.cloudinit import (
    CloudInitFile,
    CloudInitSpec,
    CloudInitUser,
    render_meta_data,
    render_user_data,
    safe_path_component,
)


def test_safe_path_component_neutralizes_traversal_and_separators():
    assert safe_path_component("../../cron.d/raes", fallback="x") == "cron.d_raes"
    assert safe_path_component("/etc/passwd", fallback="x") == "etc_passwd"
    assert safe_path_component("..", fallback="fallback") == "fallback"
    assert safe_path_component("", fallback="fallback") == "fallback"
    # An already-safe value is preserved unchanged.
    assert safe_path_component("wazuh-agent", fallback="x") == "wazuh-agent"
    # The result is always a single separator-free component.
    assert "/" not in safe_path_component("a/b/c", fallback="x")


def _parse_body(user_data: str) -> dict:
    header, _, body = user_data.partition("\n")
    assert header == "#cloud-config"
    return json.loads(body)


def test_empty_spec_is_empty():
    assert CloudInitSpec().is_empty is True
    assert CloudInitSpec(hostname="web").is_empty is False
    assert CloudInitSpec(packages=("nginx",)).is_empty is False


def test_user_data_starts_with_cloud_config_header():
    user_data = render_user_data(CloudInitSpec(hostname="web"))

    assert user_data.startswith("#cloud-config\n")
    assert _parse_body(user_data) == {"hostname": "web"}


def test_user_data_renders_account_with_all_features():
    spec = CloudInitSpec(
        users=(
            CloudInitUser(  # noqa: S604 - `shell` is a cloud-init user field, not a subprocess shell
                name="svc",
                groups=("sudo", "docker"),
                shell="/bin/bash",
                home="/home/svc",
                lock_passwd=True,
                ssh_authorized_keys=("ssh-ed25519 AAAA",),
            ),
        ),
    )

    body = _parse_body(render_user_data(spec))

    assert body["users"] == [
        {
            "name": "svc",
            "groups": ["sudo", "docker"],
            "shell": "/bin/bash",
            "homedir": "/home/svc",
            "lock_passwd": True,
            "ssh_authorized_keys": ["ssh-ed25519 AAAA"],
        }
    ]


def test_user_data_omits_empty_account_fields():
    body = _parse_body(render_user_data(CloudInitSpec(users=(CloudInitUser(name="alice"),))))

    assert body["users"] == [{"name": "alice"}]


def test_user_data_renders_write_files_packages_and_runcmd():
    spec = CloudInitSpec(
        write_files=(CloudInitFile(path="/srv/flag.txt", content="ctf{x}\n", permissions="0600"),),
        packages=("wazuh-agent",),
        runcmd=(("systemctl", "enable", "--now", "wazuh-agent"),),
    )

    body = _parse_body(render_user_data(spec))

    assert body["write_files"] == [{"path": "/srv/flag.txt", "content": "ctf{x}\n", "permissions": "0600"}]
    assert body["packages"] == ["wazuh-agent"]
    # runcmd is argv-list form so cloud-init runs it without a shell (no injection).
    assert body["runcmd"] == [["systemctl", "enable", "--now", "wazuh-agent"]]


def test_user_data_is_deterministic():
    spec = CloudInitSpec(
        hostname="web",
        users=(CloudInitUser(name="b"), CloudInitUser(name="a")),
        packages=("z", "a"),
    )

    assert render_user_data(spec) == render_user_data(spec)


def test_user_data_handles_multiline_and_special_content():
    content = "line1\n  indented: value\n\ttab\n"
    body = _parse_body(render_user_data(CloudInitSpec(write_files=(CloudInitFile(path="/c", content=content),))))

    assert body["write_files"][0]["content"] == content


def test_meta_data_instance_id_is_hostname_prefixed_and_content_derived():
    meta = json.loads(render_meta_data(CloudInitSpec(hostname="web")))

    assert meta["local-hostname"] == "web"
    assert meta["instance-id"].startswith("web-")
    # Identical content is stable, so an unchanged plan does not re-run cloud-init.
    assert meta == json.loads(render_meta_data(CloudInitSpec(hostname="web")))


def test_meta_data_instance_id_changes_when_seed_content_changes():
    # A converged UPDATE that changes content must get a new instance-id so
    # cloud-init re-runs in the guest instead of treating the seed as consumed.
    base = render_meta_data(CloudInitSpec(hostname="web"))
    changed = render_meta_data(CloudInitSpec(hostname="web", packages=("nginx",)))

    assert json.loads(base)["instance-id"] != json.loads(changed)["instance-id"]


def test_meta_data_without_hostname_has_content_derived_instance_id():
    meta = json.loads(render_meta_data(CloudInitSpec()))

    assert meta["instance-id"].startswith("raes-")
    assert "local-hostname" not in meta
