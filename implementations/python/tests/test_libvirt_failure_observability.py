"""The libvirt backend records every suppressed native failure for operators.

Each case forces one broad exception-collapse site and pins two things at
once: the portable behavior is unchanged (value-free diagnostic, None, or
empty result), and the suppressed native failure is recorded on the
``raes_backend_libvirt`` logger at DEBUG with the failing operation named --
the operator-side observability contract added for the field-debuggability
gap (no native detail crosses the portable boundary).
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from raes_backend_libvirt.driver import DomainSpec, NetworkSpec
from raes_backend_libvirt.drivers.libvirt import _native
from raes_backend_libvirt.drivers.libvirt.deployment import LibvirtDeploymentDriver
from raes_backend_libvirt.techvault_lifecycle import _list_native, _native_name
from raes_backend_libvirt.techvault_native import _define
from raes_backend_libvirt.techvault_native._driver import TechVaultNativeLibvirtDriver

_OBSERVABILITY_LOGGER = "raes_backend_libvirt"
_SUPPRESSED = "suppressed a native libvirt failure"


def _raiser(*_args: object, **_kwargs: object) -> object:
    raise RuntimeError("forced native failure")


def _assert_recorded(caplog: pytest.LogCaptureFixture, operation: str) -> None:
    records = [
        record
        for record in caplog.records
        if record.name == _OBSERVABILITY_LOGGER and _SUPPRESSED in record.getMessage()
    ]
    assert records, f"no suppressed-failure record for {operation!r}"
    assert any(operation in record.getMessage() for record in records)
    assert all(record.levelno == logging.DEBUG for record in records)
    assert any(record.exc_info is not None for record in records)


@pytest.fixture(autouse=True)
def _capture_debug(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.DEBUG, logger=_OBSERVABILITY_LOGGER)
    return caplog


def test_error_code_records_a_raising_classifier(caplog: pytest.LogCaptureFixture) -> None:
    class _WeirdError(Exception):
        def get_error_code(self) -> int:
            raise RuntimeError("classifier exploded")

    assert _native._error_code(_WeirdError()) is None
    _assert_recorded(caplog, "_error_code")


def test_existing_uuid_records_a_raising_reader(caplog: pytest.LogCaptureFixture) -> None:
    assert _native._existing_uuid(SimpleNamespace(UUIDString=_raiser)) is None
    _assert_recorded(caplog, "_existing_uuid")


def test_native_name_records_a_raising_reader(caplog: pytest.LogCaptureFixture) -> None:
    assert _native_name(SimpleNamespace(name=_raiser)) == ""
    _assert_recorded(caplog, "_native_name")


def test_list_native_records_a_raising_lister(caplog: pytest.LogCaptureFixture) -> None:
    assert _list_native(SimpleNamespace(listAllDomains=_raiser), "listAllDomains") is None
    _assert_recorded(caplog, "_list_native")


def _deployment_driver(**kwargs: object) -> LibvirtDeploymentDriver:
    return LibvirtDeploymentDriver(name_prefix="raestest", **kwargs)


def test_deployment_observe_records_a_raising_connector(caplog: pytest.LogCaptureFixture) -> None:
    result = _deployment_driver(connector=_raiser).observe(domains=())

    assert result.diagnostics
    assert result.diagnostics[0].code.endswith("unavailable")
    _assert_recorded(caplog, "observe")


def test_deployment_destroy_records_a_raising_connector(caplog: pytest.LogCaptureFixture) -> None:
    result = _deployment_driver(connector=_raiser).destroy(networks=(), domains=())

    assert result.diagnostics
    assert result.diagnostics[0].code.endswith("unavailable")
    _assert_recorded(caplog, "destroy")


def test_deployment_substrate_observation_records_a_raising_lookup(caplog: pytest.LogCaptureFixture) -> None:
    connection = SimpleNamespace(lookupByName=_raiser)
    driver = _deployment_driver(connection=connection)
    spec = DomainSpec(address="provision.node.web", name="web", image_ref=None, memory_mib=256)

    result = driver.observe(domains=(spec,))

    assert result.observations == ()
    _assert_recorded(caplog, "_compute_substrate_observation")


def test_deployment_realize_network_records_a_raising_define(caplog: pytest.LogCaptureFixture) -> None:
    connection = SimpleNamespace(networkLookupByName=_raiser, networkDefineXML=_raiser)
    driver = _deployment_driver(connection=connection)
    spec = NetworkSpec(address="provision.network.lan", name="lan", cidr="10.0.0.0/24", gateway="10.0.0.1")

    result = driver.realize(networks=(spec,), domains=())

    assert result.diagnostics
    _assert_recorded(caplog, "_realize_network")


def _techvault_driver(tmp_path, **kwargs: object) -> TechVaultNativeLibvirtDriver:
    kernel = tmp_path / "kernel"
    kernel.write_bytes(b"kernel")
    return TechVaultNativeLibvirtDriver(state_dir=tmp_path / "state", kernel_path=kernel, **kwargs)


def test_techvault_destroy_records_a_raising_connector(tmp_path, caplog: pytest.LogCaptureFixture) -> None:
    driver = _techvault_driver(tmp_path, connector=_raiser)

    result = driver.destroy(networks=(), domains=())

    assert result.diagnostics
    assert result.diagnostics[0].code.endswith("unavailable")
    _assert_recorded(caplog, "destroy")


def test_techvault_observe_records_a_raising_connector(tmp_path, caplog: pytest.LogCaptureFixture) -> None:
    driver = _techvault_driver(tmp_path, connector=_raiser)

    result = driver.observe(domains=())

    assert result.diagnostics
    assert result.diagnostics[0].code.endswith("unavailable")
    _assert_recorded(caplog, "observe")


def test_techvault_observed_domain_records_a_raising_resolution(
    tmp_path, monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    from raes_backend_libvirt.techvault_native import _driver as _techvault_module

    monkeypatch.setattr(_techvault_module, "_resolve_native", _raiser)
    driver = _techvault_driver(tmp_path, connection=object())
    spec = DomainSpec(address="provision.node.web", name="web", image_ref=None, memory_mib=256)

    result = driver.observe(domains=(spec,))

    assert result.observations == ()
    _assert_recorded(caplog, "_observed_domain")


def test_techvault_try_destroy_records_a_raising_teardown(
    tmp_path, monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    driver = _techvault_driver(tmp_path, connection=object())
    monkeypatch.setattr(driver, "_destroy_one", _raiser)

    assert driver._try_destroy(object(), "lookupByName", "provision.node.web") is False
    _assert_recorded(caplog, "_try_destroy")


def _define_driver(tmp_path) -> TechVaultNativeLibvirtDriver:
    return _techvault_driver(tmp_path, connection=object())


def test_define_network_records_a_raising_define(tmp_path, monkeypatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr(_define, "_ensure_name_available", lambda *args, **kwargs: None)
    monkeypatch.setattr(_define, "_call", _raiser)
    driver = _define_driver(tmp_path)
    network = {"address": "provision.network.lan", "runtime_name": "raestest-lan"}

    handle, diagnostic, observations = _define.define_network(driver, object(), network)

    assert handle is None
    assert diagnostic is not None
    assert observations == ()
    _assert_recorded(caplog, "define_network")


def test_define_network_records_a_raising_readback(tmp_path, monkeypatch, caplog: pytest.LogCaptureFixture) -> None:
    native = SimpleNamespace(create=lambda: None)
    monkeypatch.setattr(_define, "_ensure_name_available", lambda *args, **kwargs: None)
    monkeypatch.setattr(_define, "_call", lambda *args, **kwargs: native)
    monkeypatch.setattr(_define, "network_observations", _raiser)
    driver = _define_driver(tmp_path)
    network = {"address": "provision.network.lan", "runtime_name": "raestest-lan"}

    handle, diagnostic, observations = _define.define_network(driver, object(), network)

    assert handle is not None
    assert handle.realized
    assert diagnostic is not None
    assert diagnostic.code.endswith("readback-failed")
    assert observations == ()
    _assert_recorded(caplog, "define_network")


def test_define_domain_records_a_raising_readback(tmp_path, monkeypatch, caplog: pytest.LogCaptureFixture) -> None:
    native = SimpleNamespace(create=lambda: None)
    artifact = tmp_path / "artifact"
    artifact.write_bytes(b"artifact")
    monkeypatch.setattr(_define, "_ensure_name_available", lambda *args, **kwargs: None)
    monkeypatch.setattr(_define, "copy_kernel_for_libvirt", lambda *args, **kwargs: artifact)
    monkeypatch.setattr(_define, "make_libvirt_readable", lambda *args, **kwargs: None)
    monkeypatch.setattr(_define, "_call", lambda *args, **kwargs: native)
    monkeypatch.setattr(_define, "domain_observations", _raiser)
    driver = _define_driver(tmp_path)
    monkeypatch.setattr(driver, "initramfs_builder", SimpleNamespace(build=lambda **kwargs: artifact))
    monkeypatch.setattr(driver, "_render_domain_xml", lambda *args, **kwargs: "<domain/>")
    domain = {"address": "provision.node.web", "runtime_name": "raestest-web"}

    handle, diagnostic, observations = _define.define_domain(driver, object(), domain, {})

    assert handle is not None
    assert handle.realized
    assert diagnostic is not None
    assert diagnostic.code.endswith("readback-failed")
    assert observations == ()
    _assert_recorded(caplog, "define_domain")
