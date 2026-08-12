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
from libvirt_interface_fixtures import (
    HOSTILE_INTERFACE_CASES,
    QUOTED_ADDRESS_COMMAND,
    QUOTED_MAC_ARM,
    VALID_INTERFACE,
    domain_with_interface,
    domain_with_malformed_entry,
)
from raes_backend_libvirt.guest_appliance import _init_script


def test_guest_init_script_quotes_valid_interface_addressing():
    script = _init_script(domain_with_interface(**VALID_INTERFACE))

    assert QUOTED_MAC_ARM in script
    assert QUOTED_ADDRESS_COMMAND in script


@pytest.mark.parametrize(("interface", "match"), HOSTILE_INTERFACE_CASES)
def test_guest_init_script_rejects_hostile_interface_fields(interface, match):
    with pytest.raises(ValueError, match=match):
        _init_script(domain_with_interface(**interface))


def test_guest_init_script_quotes_the_hostname():
    script = _init_script({"name": "web; rm -rf /", "interfaces": []})

    assert "hostname 'web; rm -rf /'" in script


def test_guest_init_script_skips_malformed_interface_entries():
    script = _init_script(domain_with_malformed_entry())

    assert QUOTED_MAC_ARM in script
    assert "not-a-mapping" not in script
