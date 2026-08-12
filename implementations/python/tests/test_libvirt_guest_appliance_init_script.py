"""Guest-appliance init script must reject hostile interface fields.

`guest_appliance` builds the same root-run init script as `techvault_appliance`
and shares its interface-rendering helper. Its own coverage lives in
`test_libvirt_backend_guest_certified.py`, which needs a static BusyBox and
`cpio` and therefore skips or fails on hosts without them; these tests exercise
the script generator directly so the second injection site stays covered
everywhere.
"""

from __future__ import annotations

import pytest
from raes_backend_libvirt.guest_appliance import _init_script

_VALID_INTERFACE = {"mac": "52:54:00:00:00:01", "ip": "192.0.2.10", "cidr_prefix": 24}


def _domain_with_interface(**interface: object) -> dict[str, object]:
    return {"name": "webapp", "interfaces": [interface]}


def test_guest_init_script_quotes_valid_interface_addressing():
    script = _init_script(_domain_with_interface(**_VALID_INTERFACE))

    assert "    '52:54:00:00:00:01')" in script
    assert "ip addr add '192.0.2.10/24' dev \"$iface\"" in script


@pytest.mark.parametrize(
    ("interface", "match"),
    (
        (
            {**_VALID_INTERFACE, "mac": "aa:bb:cc:dd:ee:ff) ; rm -rf /outside #"},
            "mac is not a MAC",
        ),
        ({**_VALID_INTERFACE, "ip": "192.0.2.10$(touch /pwned)"}, "ip is not an IP"),
        ({**_VALID_INTERFACE, "ip": "`reboot`"}, "ip is not an IP"),
        ({**_VALID_INTERFACE, "cidr_prefix": "24; rm -rf /"}, "cidr_prefix is not an integer"),
        ({**_VALID_INTERFACE, "cidr_prefix": 33}, "cidr_prefix is out of range"),
    ),
)
def test_guest_init_script_rejects_hostile_interface_fields(interface, match):
    with pytest.raises(ValueError, match=match):
        _init_script(_domain_with_interface(**interface))


def test_guest_init_script_quotes_the_hostname():
    script = _init_script({"name": "web; rm -rf /", "interfaces": []})

    assert "hostname 'web; rm -rf /'" in script


def test_guest_init_script_skips_malformed_interface_entries():
    script = _init_script({"name": "webapp", "interfaces": ["not-a-mapping", _VALID_INTERFACE]})

    assert "    '52:54:00:00:00:01')" in script
    assert "not-a-mapping" not in script
