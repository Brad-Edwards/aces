"""Shared interface fixtures for the libvirt guest init-script generators.

`techvault_appliance` and `guest_appliance` build the same root-run init script
and share one validated interface renderer, so their tests assert the same
guarantees against two entry points. The fixtures live here so neither test
module duplicates the other.
"""

from __future__ import annotations

VALID_INTERFACE = {"mac": "52:54:00:00:00:01", "ip": "192.0.2.10", "cidr_prefix": 24}

# Each case pairs a hostile or ill-typed field with the message fragment the
# generator must raise. Shell metacharacters must be refused outright rather
# than escaped: a field that is not the shape it claims to be is a bug in the
# plan, not text to quote into a root-run command.
HOSTILE_INTERFACE_CASES = (
    ({**VALID_INTERFACE, "mac": "aa:bb:cc:dd:ee:ff) ; rm -rf /outside #"}, "mac is not a MAC"),
    ({**VALID_INTERFACE, "ip": "192.0.2.10$(touch /pwned)"}, "ip is not an IP"),
    ({**VALID_INTERFACE, "ip": "`reboot`"}, "ip is not an IP"),
    ({**VALID_INTERFACE, "cidr_prefix": "24; rm -rf /"}, "cidr_prefix is not an integer"),
    ({**VALID_INTERFACE, "cidr_prefix": 33}, "cidr_prefix is out of range"),
    ({**VALID_INTERFACE, "ip": 3221225994}, "ip is not an IP"),
    ({**VALID_INTERFACE, "ip": None}, "ip is not an IP"),
    ({**VALID_INTERFACE, "cidr_prefix": True}, "cidr_prefix is not an integer"),
    ({**VALID_INTERFACE, "cidr_prefix": "²"}, "cidr_prefix is not an integer"),
    ({**VALID_INTERFACE, "cidr_prefix": 24.5}, "cidr_prefix is not an integer"),
)

QUOTED_MAC_ARM = "    '52:54:00:00:00:01')"
QUOTED_ADDRESS_COMMAND = "ip addr add '192.0.2.10/24' dev \"$iface\""


def domain_with_interface(**interface: object) -> dict[str, object]:
    return {"name": "webapp", "interfaces": [interface]}


def domain_with_malformed_entry() -> dict[str, object]:
    return {"name": "webapp", "interfaces": ["not-a-mapping", VALID_INTERFACE]}
