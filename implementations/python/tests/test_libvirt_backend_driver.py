"""Issue #601: libvirt driver adapter behavior."""

from __future__ import annotations

import re
from pathlib import Path

from aces_backend_libvirt.cloudinit import CloudInitSpec, CloudInitUser
from aces_backend_libvirt.driver import DomainSpec, NetworkAcl, NetworkSpec
from aces_backend_libvirt.drivers.libvirt import LibvirtDeploymentDriver


def _xml_attr(xml: str, attr: str) -> str:
    match = re.search(rf'{attr}="([^"]+)"', xml)
    return match.group(1) if match else ""


class _NativeObject:
    def __init__(self, uuid: str = "") -> None:
        self.uuid = uuid
        self.created = False
        self.destroyed = False
        self.undefined = False

    def create(self):
        self.created = True

    def destroy(self):
        self.destroyed = True

    def undefine(self):
        self.undefined = True

    def UUIDString(self):  # noqa: N802 - mirrors libvirt API
        return self.uuid


class _FakeConnection:
    def __init__(self, *, fail_define: bool = False) -> None:
        self.fail_define = fail_define
        self.network_xml: list[str] = []
        self.domain_xml: list[str] = []
        self.nwfilter_xml: list[str] = []
        self.networks: dict[str, _NativeObject] = {}
        self.domains: dict[str, _NativeObject] = {}
        self.nwfilters: dict[str, _NativeObject] = {}

    def nwfilterDefineXML(self, xml: str):  # noqa: N802 - mirrors libvirt API
        self.nwfilter_xml.append(xml)
        native = _NativeObject(_uuid_from_xml(xml))
        self.nwfilters[_xml_attr(xml, "name")] = native
        return native

    def nwfilterLookupByName(self, name: str):  # noqa: N802 - mirrors libvirt API
        return self.nwfilters[name]

    def networkDefineXML(self, xml: str):  # noqa: N802 - mirrors libvirt API
        if self.fail_define:
            raise RuntimeError("native failure with /secret/path and TOKEN")
        self.network_xml.append(xml)
        native = _NativeObject(_uuid_from_xml(xml))
        self.networks[_name_from_xml(xml)] = native
        return native

    def defineXML(self, xml: str):  # noqa: N802 - mirrors libvirt API
        if self.fail_define:
            raise RuntimeError("native failure with /secret/path and TOKEN")
        self.domain_xml.append(xml)
        native = _NativeObject(_uuid_from_xml(xml))
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


def _uuid_from_xml(xml: str) -> str:
    match = re.search(r"<uuid>([^<]+)</uuid>", xml)
    return match.group(1) if match else ""


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


class _FakeSeedBuilder:
    def __init__(self) -> None:
        self.seed_dirs: list[Path] = []

    def build(self, *, seed_dir: Path) -> Path:
        seed = seed_dir / "seed.iso"
        seed.write_bytes(b"cidata")
        self.seed_dirs.append(seed_dir)
        return seed


def test_libvirt_driver_realizes_cloud_init_seed_as_readonly_cdrom(tmp_path):
    connection = _FakeConnection()
    seed_builder = _FakeSeedBuilder()
    driver = LibvirtDeploymentDriver(
        connection=connection,
        name_prefix="aces-test",
        workspace=tmp_path,
        seed_builder=seed_builder,
    )

    result = driver.realize(
        networks=(),
        domains=(
            DomainSpec(
                address="provision.node.web",
                name="web",
                image_ref="/img/base.qcow2",
                cloud_init=CloudInitSpec(hostname="web", users=(CloudInitUser(name="alice"),)),
            ),
        ),
    )

    assert not result.diagnostics
    seed_dir = tmp_path / "aces-test-web"
    assert (seed_dir / "user-data").read_text().startswith("#cloud-config")
    assert (seed_dir / "meta-data").exists()
    assert seed_builder.seed_dirs == [seed_dir]
    domain_xml = connection.domain_xml[0]
    assert 'device="cdrom"' in domain_xml
    assert str(seed_dir / "seed.iso") in domain_xml
    assert "<readonly" in domain_xml


def _realize_seed_domain(driver):
    return driver.realize(
        networks=(),
        domains=(
            DomainSpec(
                address="provision.node.web",
                name="web",
                image_ref=None,
                cloud_init=CloudInitSpec(hostname="web", users=(CloudInitUser(name="alice"),)),
            ),
        ),
    )


def test_libvirt_seed_artifacts_use_private_modes(tmp_path):
    driver = LibvirtDeploymentDriver(
        connection=_FakeConnection(),
        name_prefix="aces-test",
        workspace=tmp_path,
        seed_builder=_FakeSeedBuilder(),
    )

    _realize_seed_domain(driver)

    seed_dir = tmp_path / "aces-test-web"
    # Directories are traversable (so the QEMU process can reach the attached ISO)
    # but not listable; the rendered source files stay 0o600-private.
    assert seed_dir.stat().st_mode & 0o777 == 0o711
    assert tmp_path.stat().st_mode & 0o777 == 0o711
    assert (seed_dir / "user-data").stat().st_mode & 0o777 == 0o600
    assert (seed_dir / "meta-data").stat().st_mode & 0o777 == 0o600


def test_libvirt_seed_write_neutralizes_pre_positioned_symlink(tmp_path):
    # A pre-positioned symlink where user-data would be written must never be
    # followed: the stale entry is cleared (target untouched) and the seed is
    # created fresh inside an owner-private directory, so re-apply still succeeds.
    seed_dir = tmp_path / "aces-test-web"
    seed_dir.mkdir(parents=True)
    target = tmp_path / "victim"
    target.write_text("original")
    (seed_dir / "user-data").symlink_to(target)
    driver = LibvirtDeploymentDriver(
        connection=_FakeConnection(),
        name_prefix="aces-test",
        workspace=tmp_path,
        seed_builder=_FakeSeedBuilder(),
    )

    result = _realize_seed_domain(driver)

    assert not result.diagnostics
    assert target.read_text() == "original"  # the symlink target was never written through
    user_data = seed_dir / "user-data"
    assert not user_data.is_symlink()
    assert user_data.read_text().startswith("#cloud-config")
    assert user_data.stat().st_mode & 0o777 == 0o600


def test_libvirt_seed_write_clears_stale_seed_dir_for_clean_reapply(tmp_path):
    # A leftover seed directory from a crashed prior apply is replaced wholesale,
    # so exclusive (O_EXCL) creation of the new seed files never collides.
    seed_dir = tmp_path / "aces-test-web"
    seed_dir.mkdir(parents=True)
    (seed_dir / "user-data").write_text("stale")
    (seed_dir / "leftover").write_text("debris")
    driver = LibvirtDeploymentDriver(
        connection=_FakeConnection(),
        name_prefix="aces-test",
        workspace=tmp_path,
        seed_builder=_FakeSeedBuilder(),
    )

    result = _realize_seed_domain(driver)

    assert not result.diagnostics
    assert not (seed_dir / "leftover").exists()
    assert (seed_dir / "user-data").read_text().startswith("#cloud-config")


def test_libvirt_driver_destroy_cleans_up_seed_media(tmp_path):
    connection = _FakeConnection()
    driver = LibvirtDeploymentDriver(
        connection=connection,
        name_prefix="aces-test",
        workspace=tmp_path,
        seed_builder=_FakeSeedBuilder(),
    )
    driver.realize(
        networks=(),
        domains=(
            DomainSpec(
                address="provision.node.web",
                name="web",
                image_ref=None,
                cloud_init=CloudInitSpec(hostname="web", users=(CloudInitUser(name="alice"),)),
            ),
        ),
    )
    seed_dir = tmp_path / "aces-test-web"
    assert seed_dir.exists()

    driver.destroy(networks=(), domains=("provision.node.web",))

    assert not seed_dir.exists()


def test_libvirt_driver_converges_existing_objects_without_duplicating(tmp_path):
    connection = _FakeConnection()
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test", seed_builder=_FakeSeedBuilder())
    specs = dict(
        networks=(NetworkSpec(address="provision.network.lan", name="lan"),),
        domains=(DomainSpec(address="provision.node.web", name="web", image_ref=None),),
    )

    first = driver.realize(**specs)
    prior_domain = connection.domains["aces-test-web"]
    prior_network = connection.networks["aces-test-lan"]
    second = driver.realize(**specs)

    assert not first.diagnostics and not second.diagnostics
    # Re-apply converges: the prior objects are stopped and undefined, then the
    # desired state is redefined — so each name resolves to exactly one object
    # (no duplicate) and the new definition genuinely takes effect.
    assert prior_domain.destroyed and prior_domain.undefined
    assert prior_network.destroyed and prior_network.undefined
    assert len(connection.domains) == 1
    assert len(connection.networks) == 1
    assert len(connection.domain_xml) == 2
    assert second.domains[0].realized is True


def test_libvirt_convergence_refuses_to_replace_a_foreign_object(tmp_path):
    # A pre-existing object that shares the runtime name but is NOT the ACES object
    # for this address (different/unknown UUID) must never be destroyed: apply fails
    # closed with an ownership-conflict diagnostic and the foreign object survives.
    connection = _FakeConnection()
    foreign = _NativeObject(uuid="11111111-2222-3333-4444-555555555555")
    connection.domains["aces-test-web"] = foreign
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test", seed_builder=_FakeSeedBuilder())

    result = driver.realize(
        networks=(),
        domains=(DomainSpec(address="provision.node.web", name="web", image_ref=None),),
    )

    assert [d.code for d in result.diagnostics] == ["libvirt-backend.driver.ownership-conflict"]
    assert not foreign.destroyed and not foreign.undefined
    assert connection.domains["aces-test-web"] is foreign  # never replaced
    assert connection.domain_xml == []  # nothing redefined


def test_libvirt_domain_xml_carries_deterministic_aces_uuid():
    connection = _FakeConnection()
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test", seed_builder=_FakeSeedBuilder())

    first = driver.realize(networks=(), domains=(DomainSpec(address="provision.node.web", name="web", image_ref=None),))
    uuid_first = _uuid_from_xml(connection.domain_xml[0])

    # Re-realizing the same address reproduces the same UUID (proves ownership);
    # a different address would derive a different UUID.
    driver.realize(networks=(), domains=(DomainSpec(address="provision.node.web", name="web", image_ref=None),))
    uuid_second = _uuid_from_xml(connection.domain_xml[1])

    assert not first.diagnostics
    assert uuid_first and uuid_first == uuid_second


def test_libvirt_network_xml_realizes_cidr_into_ip_and_dhcp_range():
    connection = _FakeConnection()
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test")

    driver.realize(
        networks=(
            NetworkSpec(
                address="provision.network.lan",
                name="lan",
                cidr="192.168.50.0/24",
                gateway="192.168.50.1",
            ),
        ),
        domains=(),
    )

    network_xml = connection.network_xml[0]
    assert 'address="192.168.50.1"' in network_xml
    assert 'netmask="255.255.255.0"' in network_xml
    assert 'start="192.168.50.2"' in network_xml
    assert 'end="192.168.50.254"' in network_xml


def test_libvirt_driver_realizes_network_acls_as_nwfilter(tmp_path):
    connection = _FakeConnection()
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test")
    acl = NetworkAcl(
        name="allow-http",
        action="accept",
        direction="in",
        protocol="tcp",
        src_cidr="10.0.0.0/24",
        dst_cidr="192.168.1.0/24",
        ports=(80,),
    )

    driver.realize(
        networks=(),
        domains=(
            DomainSpec(
                address="provision.node.web",
                name="web",
                image_ref=None,
                networks=("provision.network.lan",),
                network_acls=(acl,),
            ),
        ),
    )

    nwfilter_xml = connection.nwfilter_xml[0]
    filter_name = _xml_attr(nwfilter_xml, "name")
    assert nwfilter_xml.startswith(f'<filter name="{filter_name}" chain="root">')
    assert '<rule action="accept" direction="in"' in nwfilter_xml
    assert "<tcp " in nwfilter_xml
    assert 'srcipaddr="10.0.0.0"' in nwfilter_xml
    assert 'srcipmask="255.255.255.0"' in nwfilter_xml
    assert 'dstipaddr="192.168.1.0"' in nwfilter_xml
    assert 'dstportstart="80"' in nwfilter_xml
    # The domain interface references the nwfilter so the host enforces the ACL.
    assert f'<filterref filter="{filter_name}"' in connection.domain_xml[0]


def test_libvirt_reapply_enforces_tightened_acl_via_redefined_nwfilter(tmp_path):
    # A re-apply that tightens an ACL (allow -> deny) must redefine the nwfilter so
    # the new rule is genuinely enforced, not recorded-but-skipped behind a stale
    # filter the host still applies.
    connection = _FakeConnection()
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test")
    allow = NetworkAcl(name="allow-http", action="accept", direction="in", protocol="tcp", ports=(80,))
    deny = NetworkAcl(name="deny-http", action="drop", direction="in", protocol="tcp", ports=(80,))

    driver.realize(
        networks=(),
        domains=(DomainSpec(address="provision.node.web", name="web", image_ref=None, network_acls=(allow,)),),
    )
    second = driver.realize(
        networks=(),
        domains=(DomainSpec(address="provision.node.web", name="web", image_ref=None, network_acls=(deny,)),),
    )

    assert not second.diagnostics
    # The filter was redefined (two define calls) and the live definition is the
    # tightened deny rule, with no lingering accept rule.
    assert len(connection.nwfilter_xml) == 2
    assert '<rule action="drop" direction="in"' in connection.nwfilter_xml[1]
    assert "accept" not in connection.nwfilter_xml[1]


def test_libvirt_driver_destroy_undefines_nwfilter(tmp_path):
    connection = _FakeConnection()
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test")
    acl = NetworkAcl(name="deny", action="drop", direction="inout", protocol="all")
    driver.realize(
        networks=(),
        domains=(DomainSpec(address="provision.node.web", name="web", image_ref=None, network_acls=(acl,)),),
    )
    filter_name = _xml_attr(connection.nwfilter_xml[0], "name")
    assert filter_name in connection.nwfilters

    driver.destroy(networks=(), domains=("provision.node.web",))

    assert connection.nwfilters[filter_name].undefined is True


def test_libvirt_nwfilter_define_refuses_to_overwrite_a_foreign_filter():
    # An ACL whose runtime filter name collides with a pre-existing, non-ACES
    # filter must not redefine it: apply fails closed and the foreign filter is
    # left untouched (no redefine), so other domains' filtering is not weakened.
    connection = _FakeConnection()
    foreign = _NativeObject(uuid="99999999-8888-7777-6666-555555555555")
    connection.nwfilters["aces-test-web-acl"] = foreign
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test")
    acl = NetworkAcl(name="allow-all", action="accept", direction="inout", protocol="all")

    result = driver.realize(
        networks=(),
        domains=(DomainSpec(address="provision.node.web", name="web", image_ref=None, network_acls=(acl,)),),
    )

    assert [d.code for d in result.diagnostics] == ["libvirt-backend.driver.ownership-conflict"]
    assert connection.nwfilter_xml == []  # the foreign filter was never redefined
    assert connection.nwfilters["aces-test-web-acl"] is foreign


def test_libvirt_destroy_refuses_to_remove_a_foreign_object():
    # A DELETE whose runtime name collides with a foreign object must not destroy
    # it: the ownership guard applies to deletion, not just convergence.
    connection = _FakeConnection()
    foreign = _NativeObject(uuid="11111111-2222-3333-4444-555555555555")
    connection.domains["aces-test-web"] = foreign
    driver = LibvirtDeploymentDriver(connection=connection, name_prefix="aces-test")

    result = driver.destroy(networks=(), domains=("provision.node.web",))

    assert [d.code for d in result.diagnostics] == ["libvirt-backend.driver.ownership-conflict"]
    assert not foreign.destroyed and not foreign.undefined
    assert connection.domains["aces-test-web"] is foreign


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
