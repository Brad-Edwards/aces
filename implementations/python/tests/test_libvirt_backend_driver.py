"""Issue #601: libvirt driver adapter behavior."""

from __future__ import annotations

from aces_backend_libvirt.driver import DomainSpec, NetworkSpec
from aces_backend_libvirt.drivers.libvirt import LibvirtDeploymentDriver


class _NativeObject:
    def __init__(self) -> None:
        self.created = False
        self.destroyed = False
        self.undefined = False

    def create(self):
        self.created = True

    def destroy(self):
        self.destroyed = True

    def undefine(self):
        self.undefined = True


class _FakeConnection:
    def __init__(self, *, fail_define: bool = False) -> None:
        self.fail_define = fail_define
        self.network_xml: list[str] = []
        self.domain_xml: list[str] = []
        self.networks: dict[str, _NativeObject] = {}
        self.domains: dict[str, _NativeObject] = {}

    def networkDefineXML(self, xml: str):  # noqa: N802 - mirrors libvirt API
        if self.fail_define:
            raise RuntimeError("native failure with /secret/path and TOKEN")
        self.network_xml.append(xml)
        native = _NativeObject()
        self.networks[_name_from_xml(xml)] = native
        return native

    def defineXML(self, xml: str):  # noqa: N802 - mirrors libvirt API
        if self.fail_define:
            raise RuntimeError("native failure with /secret/path and TOKEN")
        self.domain_xml.append(xml)
        native = _NativeObject()
        self.domains[_name_from_xml(xml)] = native
        return native

    def networkLookupByName(self, name: str):  # noqa: N802 - mirrors libvirt API
        return self.networks[name]

    def lookupByName(self, name: str):  # noqa: N802 - mirrors libvirt API
        return self.domains[name]


def _name_from_xml(xml: str) -> str:
    start = xml.index("<name>") + len("<name>")
    end = xml.index("</name>")
    return xml[start:end]


def test_libvirt_driver_realize_defines_networks_and_domains_with_safe_names():
    connection = _FakeConnection()
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test")

    result = driver.realize(
        networks=(NetworkSpec(address="provision.network.lan", name="lan<>"),),
        domains=(
            DomainSpec(
                address="provision.node.web",
                name="web/vm",
                image_ref="/var/lib/libvirt/images/base.qcow2",
                memory_mib=1024,
                vcpus=2,
                networks=("provision.network.lan",),
            ),
        ),
    )

    assert not result.diagnostics
    assert "aces-test-lan" in connection.network_xml[0]
    assert "aces-test-web-vm" in connection.domain_xml[0]
    assert "lan<>" not in connection.network_xml[0]
    assert "web/vm" not in connection.domain_xml[0]
    assert 'source network="aces-test-lan"' in connection.domain_xml[0]
    assert driver.realized_addresses() == frozenset({"provision.network.lan", "provision.node.web"})


def test_libvirt_driver_diagnostics_do_not_leak_native_exception_or_image_path():
    connection = _FakeConnection(fail_define=True)
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test")

    result = driver.realize(
        networks=(),
        domains=(
            DomainSpec(
                address="provision.node.web",
                name="web",
                image_ref="/secret/path/base.qcow2",
                memory_mib=512,
                vcpus=1,
            ),
        ),
    )

    assert result.diagnostics
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "libvirt-backend.driver.operation-failed"
    assert "/secret/path" not in diagnostic.message
    assert "TOKEN" not in diagnostic.message
    assert "provision.node.web" in diagnostic.message


def test_libvirt_driver_destroy_uses_previously_realized_names():
    connection = _FakeConnection()
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test")
    driver.realize(
        networks=(NetworkSpec(address="provision.network.lan", name="lan"),),
        domains=(DomainSpec(address="provision.node.web", name="web", image_ref=None),),
    )

    result = driver.destroy(networks=("provision.network.lan",), domains=("provision.node.web",))

    assert not result.diagnostics
    assert connection.networks["aces-test-lan"].destroyed is True
    assert connection.networks["aces-test-lan"].undefined is True
    assert connection.domains["aces-test-web"].destroyed is True
    assert connection.domains["aces-test-web"].undefined is True
    assert driver.realized_addresses() == frozenset()
