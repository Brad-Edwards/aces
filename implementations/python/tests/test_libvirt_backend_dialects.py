"""Issue #603: OS-family-aware cloud-init realization dialects."""

from __future__ import annotations

from raes_backend_libvirt.dialects import dialect_for


def test_linux_dialect_uses_systemd_and_aliases():
    linux = dialect_for("linux")

    feature = linux.enable_feature("wazuh-agent")
    assert feature.packages == ("wazuh-agent",)
    assert ("systemctl", "enable", "--now", "wazuh-agent") in feature.runcmd

    mail = linux.mail_alias("alice", "alice@example.test")
    assert any(f.path == "/etc/aliases.d/aces-alice" for f in mail.write_files)
    assert ("newaliases",) in mail.runcmd


def test_freebsd_dialect_uses_sysrc_and_service():
    feature = dialect_for("freebsd").enable_feature("nginx")

    assert feature.packages == ("nginx",)
    assert ("sysrc", "nginx_enable=YES") in feature.runcmd
    assert ("service", "nginx", "start") in feature.runcmd


def test_windows_dialect_uses_choco_and_sc_with_discrete_argv():
    feature = dialect_for("windows").enable_feature("sysmon")

    # No cloud-init `packages:` on Windows; choco + sc.exe, each taking the name
    # as a discrete argv token (no shell), so a hostile name cannot inject.
    assert feature.packages == ()
    assert ("choco", "install", "-y", "--no-progress", "sysmon") in feature.runcmd
    assert ("sc.exe", "start", "sysmon") in feature.runcmd


def test_macos_dialect_uses_brew():
    feature = dialect_for("macos").enable_feature("osquery")

    assert ("brew", "install", "osquery") in feature.runcmd
    assert ("brew", "services", "start", "osquery") in feature.runcmd


def test_unknown_os_family_falls_back_to_portable_descriptor():
    feature = dialect_for("plan9").enable_feature("svc")

    assert feature.packages == ()
    assert feature.runcmd == ()
    assert any(f.path == "/etc/aces/features/svc.json" for f in feature.write_files)
