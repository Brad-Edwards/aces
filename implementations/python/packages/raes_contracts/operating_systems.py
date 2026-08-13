"""Shared portable operating-system identity invariants."""

from __future__ import annotations

import re

OS_VERSION_PATTERN = r"^[!-~](?:[ -~]{0,126}[!-~])?$"
OS_VERSION_RE = re.compile(OS_VERSION_PATTERN)

CORE_DISTRIBUTION_FAMILIES = {
    "ubuntu": "linux",
    "debian": "linux",
    "rocky-linux": "linux",
    "red-hat-enterprise-linux": "linux",
    "windows-server": "windows",
    "windows-client": "windows",
    "solaris": "other",
}


def validate_operating_system_pair(family: str, distribution: str) -> None:
    """Reject a core distribution paired with the wrong portable family."""

    expected = CORE_DISTRIBUTION_FAMILIES.get(distribution)
    if expected is not None and family != expected:
        raise ValueError(f"operating-system distribution '{distribution}' requires family '{expected}', not '{family}'")


__all__ = [
    "CORE_DISTRIBUTION_FAMILIES",
    "OS_VERSION_PATTERN",
    "OS_VERSION_RE",
    "validate_operating_system_pair",
]
