"""Guest-observing initramfs appliance for guest-certified libvirt runs.

Builds a BusyBox appliance that realizes bounded account, file, and service
placements inside the guest, then reads the *realized* system back (its own
``/proc``, ``/etc``, link state, file digests, service state) and emits a
bounded, line-oriented fact report to the file-backed serial fact channel. The
fresh per-run challenge is read from the kernel command line, so the appliance
image bytes (and therefore their digest) are independent of the challenge.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ._initramfs import InitramfsPreflight, atomic_write, deterministic_gzip, resolve_static_busybox
from .techvault_appliance import _cpio_newc, _interface_case_lines, _shell_quote

_BOOT_ARTIFACT_MODE = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
_PRIVATE_FILE_MODE = stat.S_IRUSR | stat.S_IWUSR

_APPLETS = (
    "sh", "mount", "mdev", "ip", "ifconfig", "sleep", "cat", "hostname", "printf", "echo",
    "uname", "nproc", "awk", "sed", "grep", "cut", "tr", "sort", "head", "wc",
    "sha256sum", "stat", "id", "mkdir", "chmod", "chown", "touch", "dirname", "basename",
    "netstat", "nc", "kill", "cp", "ls",
)  # fmt: skip

# Baseline account-database file lines written into the appliance rootfs. These
# are /etc/{passwd,group,shadow} record formats for the root account, not secrets.
_ROOT_ACCOUNT_LINE = "root:x:0:0:root:/root:/bin/sh\n"
_ROOT_GROUP_LINE = "root:x:0:\n"
_ROOT_SHADOW_LINE = "root:x:19000:0:99999:7:::\n"

# Shared shell guard reused across the account/service read loops.
_SKIP_IF_NO_NAME = '  [ -n "$name" ] || continue'


@dataclass
class GuestObservingInitramfsBuilder:
    """Build a guest-observing appliance that certifies concerns from inside."""

    busybox_path: Path | None = None
    search_path: str | None = None

    def preflight(self) -> InitramfsPreflight:
        """Resolve and validate the static target BusyBox before mutation."""

        return resolve_static_busybox(self.busybox_path, search_path=self.search_path)

    def build(self, *, domain: Mapping[str, object], target: Path) -> Path:
        busybox_path = self.preflight().require_executable()
        with tempfile.TemporaryDirectory(prefix="raes-guest-initramfs-") as tmp:
            root = Path(tmp)
            _write_guest_root(root, busybox_path, domain)
            payload = deterministic_gzip(_cpio_newc(root), compresslevel=6)
            return atomic_write(target, payload, mode=_BOOT_ARTIFACT_MODE)


def _write_guest_root(root: Path, busybox_path: Path, domain: Mapping[str, object]) -> None:
    bin_dir = root / "bin"
    etc_dir = root / "etc"
    guest_dir = etc_dir / "raes" / "guest"
    files_dir = guest_dir / "files"
    for directory in (
        bin_dir,
        files_dir,
        root / "proc",
        root / "sys",
        root / "dev",
        root / "tmp",
        root / "run",
        root / "home",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(busybox_path, bin_dir / "busybox")
    for applet in _APPLETS:
        (bin_dir / applet).symlink_to("busybox")
    _write_text(etc_dir / "passwd", _ROOT_ACCOUNT_LINE)
    _write_text(etc_dir / "group", _ROOT_GROUP_LINE)
    _write_text(etc_dir / "shadow", _ROOT_SHADOW_LINE)
    _write_placement_specs(guest_dir, files_dir, domain)
    _write_text(guest_dir / "domain.json", json.dumps(domain, indent=2, sort_keys=True) + "\n")
    init_path = root / "init"
    _write_text(init_path, _init_script(domain))
    os.chmod(init_path, 0o700)
    os.chmod(bin_dir / "busybox", 0o700)


def _write_placement_specs(guest_dir: Path, files_dir: Path, domain: Mapping[str, object]) -> None:
    accounts = [
        "|".join(
            (
                str(item.get("name", "")),
                ",".join(str(group) for group in _as_sequence(item.get("groups"))),
                str(item.get("shell", "")),
                str(item.get("home", "")),
                "1" if item.get("disabled") else "0",
            )
        )
        for item in _as_sequence(domain.get("accounts"))
        if isinstance(item, Mapping)
    ]
    content_lines = []
    for index, item in enumerate(_as_sequence(domain.get("content"))):
        if not isinstance(item, Mapping):
            continue
        _write_text(files_dir / str(index), str(item.get("content", "")))
        content_lines.append("|".join((str(item.get("path", "")), str(item.get("mode", "0644")), str(index))))
    services = [
        "|".join(
            (
                str(item.get("name", "")),
                str(item.get("protocol", "")),
                str(item.get("port", "")),
            )
        )
        for item in _as_sequence(domain.get("services"))
        if isinstance(item, Mapping)
    ]
    _write_text(guest_dir / "accounts", "\n".join(accounts) + ("\n" if accounts else ""))
    _write_text(guest_dir / "content", "\n".join(content_lines) + ("\n" if content_lines else ""))
    _write_text(guest_dir / "services", "\n".join(services) + ("\n" if services else ""))


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    os.chmod(path, _PRIVATE_FILE_MODE)


def _init_script(domain: Mapping[str, object]) -> str:
    lines = [
        "#!/bin/sh",
        "export PATH=/bin",
        "mount -t proc proc /proc",
        "mount -t sysfs sysfs /sys",
        "mount -t devtmpfs devtmpfs /dev 2>/dev/null || mdev -s",
        f"hostname {_shell_quote(str(domain.get('name', 'raes-node')))}",
        "ip link set lo up",
        "for iface_path in /sys/class/net/*; do",
        "  iface=${iface_path##*/}",
        '  [ "$iface" = lo ] && continue',
        '  mac=$(cat "$iface_path/address")',
        '  ip link set "$iface" up',
        '  case "$mac" in',
    ]
    for interface in _as_sequence(domain.get("interfaces")):
        if not isinstance(interface, Mapping):
            continue
        lines.extend(_interface_case_lines(interface))
    lines.extend(["  esac", "done"])
    lines.extend(_REALIZE_SNIPPET)
    lines.append("sleep 1")
    lines.append("challenge=$(cat /proc/cmdline | tr ' ' '\\n' | sed -n 's/^raes.challenge=//p')")
    lines.extend(_REPORT_SNIPPET)
    lines.append("while true; do sleep 3600; done")
    lines.append("")
    return "\n".join(lines)


_REALIZE_SNIPPET = [
    "if [ -f /etc/raes/guest/accounts ]; then",
    "while IFS='|' read name groups shell home disabled; do",
    _SKIP_IF_NO_NAME,
    '  [ -n "$home" ] || home=/home/$name',
    '  [ -n "$shell" ] || shell=/bin/sh',
    '  mkdir -p "$home"',
    "  uid=$(awk -F: 'BEGIN{m=1000}$3>=m{m=$3+1}END{print m}' /etc/passwd)",
    '  echo "$name:x:$uid:$uid:raes:$home:$shell" >> /etc/passwd',
    '  echo "$name:x:$uid:" >> /etc/group',
    '  if [ "$disabled" = 1 ]; then echo "$name:!:19000:0:99999:7:::" >> /etc/shadow;',
    '  else echo "$name:*:19000:0:99999:7:::" >> /etc/shadow; fi',
    "  oldifs=$IFS; IFS=,",
    "  for g in $groups; do",
    "    IFS=$oldifs",
    '    [ -n "$g" ] || { IFS=,; continue; }',
    '    if grep -q "^$g:" /etc/group; then',
    '      sed -i "s/^\\($g:[^:]*:[^:]*:\\)\\(.*\\)$/\\1\\2,$name/" /etc/group',
    "    else",
    "      gid=$(awk -F: 'BEGIN{m=2000}$3>=m{m=$3+1}END{print m}' /etc/group)",
    '      echo "$g:x:$gid:$name" >> /etc/group',
    "    fi",
    "    IFS=,",
    "  done",
    "  IFS=$oldifs",
    "done < /etc/raes/guest/accounts",
    "fi",
    "if [ -f /etc/raes/guest/content ]; then",
    "while IFS='|' read path mode idx; do",
    '  [ -n "$path" ] || continue',
    '  mkdir -p "$(dirname "$path")"',
    '  cp "/etc/raes/guest/files/$idx" "$path"',
    '  chmod "$mode" "$path"',
    "done < /etc/raes/guest/content",
    "fi",
    "if [ -f /etc/raes/guest/services ]; then",
    "while IFS='|' read name protocol port; do",
    _SKIP_IF_NO_NAME,
    '  [ "$protocol" = tcp ] || continue',
    '  ( while true; do echo raes-guest-service | nc -l -p "$port" >/dev/null 2>&1 || sleep 1; done ) &',
    "  echo $! > /run/raes-svc-$name.pid",
    "done < /etc/raes/guest/services",
    "fi",
]

_REPORT_SNIPPET = [
    "FC=/dev/ttyS1",
    "{",
    "echo 'RAES-GUEST-FACTS v1'",
    'echo "challenge $challenge"',
    'echo "architecture $(uname -m)"',
    'echo "vcpus $(nproc)"',
    "echo \"memory_mib $(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)\"",
    "for iface_path in /sys/class/net/*; do",
    '  iface=${iface_path##*/}; [ "$iface" = lo ] && continue',
    '  mac=$(cat "$iface_path/address")',
    "  ip4=$(ip -4 -o addr show dev \"$iface\" 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -n1)",
    '  up=0; [ "$(cat "$iface_path/operstate" 2>/dev/null)" = up ] && up=1',
    '  echo "iface $mac ${ip4:-none} $up"',
    "done",
    "if [ -f /etc/raes/guest/content ]; then",
    "while IFS='|' read path mode idx; do",
    '  [ -n "$path" ] || continue',
    '  [ -f "$path" ] || continue',
    "  d=$(sha256sum \"$path\" | cut -d' ' -f1)",
    "  m=$(stat -c '%a' \"$path\" 2>/dev/null)",
    '  echo "content $path $d $m"',
    "done < /etc/raes/guest/content",
    "fi",
    "if [ -f /etc/raes/guest/accounts ]; then",
    "while IFS='|' read name groups shell home disabled; do",
    _SKIP_IF_NO_NAME,
    '  entry=$(grep "^$name:" /etc/passwd) || continue',
    '  uid=$(echo "$entry" | cut -d: -f3)',
    '  h=$(echo "$entry" | cut -d: -f6)',
    '  sh=$(echo "$entry" | cut -d: -f7)',
    '  grps=$(awk -F: -v u="$name" \'{n=split($4,a,","); for(i=1;i<=n;i++) if(a[i]==u) print $1}\' /etc/group \\',
    "    | sort | tr '\\n' ',' | sed 's/,$//')",
    '  spw=$(grep "^$name:" /etc/shadow | cut -d: -f2)',
    "  dis=0; case \"$spw\" in '!'*|'*'*) dis=1;; esac",
    '  echo "account $name $uid $h $sh $dis $grps"',
    "done < /etc/raes/guest/accounts",
    "fi",
    "if [ -f /etc/raes/guest/services ]; then",
    "while IFS='|' read name protocol port; do",
    _SKIP_IF_NO_NAME,
    '  lis=0; [ "$protocol" = tcp ] && netstat -lnt 2>/dev/null | grep -q ":$port " && lis=1',
    '  pid=0; [ -f "/run/raes-svc-$name.pid" ] && kill -0 "$(cat /run/raes-svc-$name.pid)" 2>/dev/null && pid=1',
    '  echo "service $name $protocol $port $lis $pid"',
    "done < /etc/raes/guest/services",
    "fi",
    "echo 'init complete'",
    '} > "$FC" 2>/dev/null',
]


def _as_sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, list | tuple) else ()


__all__ = ["GuestObservingInitramfsBuilder"]
