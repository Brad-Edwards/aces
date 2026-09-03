"""The libvirt backend safely records suppressed failures for operators.

Each case forces one broad exception-collapse site and pins two things at
once: the portable behavior is unchanged (value-free diagnostic, None, or
empty result), and bounded failure classification is recorded on the
``raes_backend_libvirt`` logger at DEBUG without exception text or traceback.
"""

from __future__ import annotations

import logging
import sys
from types import ModuleType, SimpleNamespace

import pytest
from raes_backend_libvirt import _initramfs, _observability
from raes_backend_libvirt._observability import record_suppressed_failure
from raes_backend_libvirt._techvault_native_ops import _ensure_name_available
from raes_backend_libvirt.driver import DomainSpec, NetworkSpec
from raes_backend_libvirt.drivers.libvirt import _native
from raes_backend_libvirt.drivers.libvirt import deployment as _deployment
from raes_backend_libvirt.drivers.libvirt.deployment import LibvirtDeploymentDriver
from raes_backend_libvirt.techvault_lifecycle import (
    _invoke_native_action,
    _list_native,
    _native_name,
    _resolve_by_name,
)
from raes_backend_libvirt.techvault_native import _define
from raes_backend_libvirt.techvault_native._driver import TechVaultNativeLibvirtDriver

_OBSERVABILITY_LOGGER = "raes_backend_libvirt"
_SUPPRESSED = "suppressed backend failure"
_SENSITIVE_DETAIL = "token=do-not-record"


class _NativeError(RuntimeError):
    def __init__(self, code: int, *, domain: int = 10, level: int = 2) -> None:
        super().__init__(_SENSITIVE_DETAIL)
        self._code = code
        self._domain = domain
        self._level = level

    def get_error_code(self) -> int:
        return self._code

    def get_error_domain(self) -> int:
        return self._domain

    def get_error_level(self) -> int:
        return self._level


class _ForeignCodeError(RuntimeError):
    """A non-libvirt exception that happens to expose a libvirt-like method."""

    def __init__(self, code: int) -> None:
        super().__init__(_SENSITIVE_DETAIL)
        self._code = code

    def get_error_code(self) -> int:
        return self._code


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
    assert all(record.exc_info is None for record in records)
    assert all("exception_type=" in record.getMessage() for record in records)
    assert all(_SENSITIVE_DETAIL not in record.getMessage() for record in records)


@pytest.fixture(autouse=True)
def _capture_debug(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
    libvirt = ModuleType("libvirt")
    libvirt.libvirtError = _NativeError
    monkeypatch.setitem(sys.modules, "libvirt", libvirt)
    caplog.set_level(logging.DEBUG, logger=_OBSERVABILITY_LOGGER)
    return caplog


def test_failure_record_is_bounded_and_uses_only_safe_classification(caplog: pytest.LogCaptureFixture) -> None:
    record_suppressed_failure("safe_operation", _NativeError(77), native_code=77)

    _assert_recorded(caplog, "safe_operation")
    message = caplog.records[-1].getMessage()
    assert "native_code=77" in message
    assert len(message) < 256


def test_failure_record_bounds_every_caller_supplied_field(caplog: pytest.LogCaptureFixture) -> None:
    huge_integer = 10**1000

    record_suppressed_failure(
        "unsafe/" + ("operation" * 100), OSError(huge_integer, _SENSITIVE_DETAIL), native_code=huge_integer
    )

    message = caplog.records[-1].getMessage()
    assert len(message) < 256
    assert _SENSITIVE_DETAIL not in message
    assert str(huge_integer) not in message


def test_failure_record_does_not_interfere_when_errno_access_raises(caplog: pytest.LogCaptureFixture) -> None:
    class _HostileOSError(OSError):
        @property
        def errno(self) -> int:
            raise RuntimeError(_SENSITIVE_DETAIL)

    record_suppressed_failure("safe_operation", _HostileOSError())

    _assert_recorded(caplog, "safe_operation")


def test_failure_record_does_not_interfere_when_logger_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_observability.LOGGER, "debug", _raiser)

    record_suppressed_failure("safe_operation", RuntimeError(_SENSITIVE_DETAIL))


def test_error_code_records_a_raising_classifier(caplog: pytest.LogCaptureFixture) -> None:
    class _WeirdError(_NativeError):
        def __init__(self) -> None:
            super().__init__(1)

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


def test_lookup_keeps_expected_native_absence_silent(caplog: pytest.LogCaptureFixture) -> None:
    def absent(_name: str) -> object:
        raise _NativeError(42)

    assert _native._lookup(SimpleNamespace(lookupByName=absent), "lookupByName", "missing") is None
    assert not [record for record in caplog.records if _SUPPRESSED in record.getMessage()]


def test_lookup_keeps_expected_nwfilter_absence_silent(caplog: pytest.LogCaptureFixture) -> None:
    def absent(_name: str) -> object:
        raise _NativeError(62)

    assert _native._lookup(SimpleNamespace(nwfilterLookupByName=absent), "nwfilterLookupByName", "missing") is None
    assert not [record for record in caplog.records if _SUPPRESSED in record.getMessage()]


def test_lookup_records_non_absence_failure(caplog: pytest.LogCaptureFixture) -> None:
    assert _native._lookup(SimpleNamespace(lookupByName=_raiser), "lookupByName", "missing") is None
    _assert_recorded(caplog, "_lookup")


def test_lookup_does_not_misclassify_a_foreign_code_bearing_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def foreign_absence(_name: str) -> object:
        raise _ForeignCodeError(42)

    assert _native._lookup(SimpleNamespace(lookupByName=foreign_absence), "lookupByName", "missing") is None
    _assert_recorded(caplog, "_lookup")


def test_lookup_does_not_accept_another_native_resource_type_absence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def network_absence_during_domain_lookup(_name: str) -> object:
        raise _NativeError(43)

    assert (
        _native._lookup(
            SimpleNamespace(lookupByName=network_absence_during_domain_lookup),
            "lookupByName",
            "missing",
        )
        is None
    )
    _assert_recorded(caplog, "_lookup")


def test_find_native_does_not_misclassify_a_foreign_code_bearing_exception() -> None:
    def foreign_absence(_name: str) -> object:
        raise _ForeignCodeError(42)

    with pytest.raises(_native._NativeLookupError):
        _native._find_native(SimpleNamespace(lookupByName=foreign_absence), "lookupByName", "missing")


def test_find_native_rejects_another_native_resource_type_absence() -> None:
    def network_absence_during_domain_lookup(_name: str) -> object:
        raise _NativeError(43)

    with pytest.raises(_native._NativeLookupError):
        _native._find_native(
            SimpleNamespace(lookupByName=network_absence_during_domain_lookup),
            "lookupByName",
            "missing",
        )


def test_stop_native_does_not_tolerate_a_foreign_operation_invalid_code() -> None:
    def foreign_inactive() -> None:
        raise _ForeignCodeError(55)

    with pytest.raises(_ForeignCodeError):
        _native._stop_native(SimpleNamespace(destroy=foreign_inactive))


def test_resolve_by_name_records_non_absence_failure(caplog: pytest.LogCaptureFixture) -> None:
    assert _resolve_by_name(object(), _raiser, "listAllDomains", "provision.node.web", "web") is None
    _assert_recorded(caplog, "_resolve_by_name")


def test_resolve_by_name_does_not_verify_absence_for_a_foreign_code_bearing_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    list_calls: list[str] = []

    def foreign_absence(_name: str) -> object:
        raise _ForeignCodeError(42)

    connection = SimpleNamespace(listAllDomains=lambda: list_calls.append("listed") or [])

    assert _resolve_by_name(connection, foreign_absence, "listAllDomains", "provision.node.web", "web") is None
    assert list_calls == []
    _assert_recorded(caplog, "_resolve_by_name")


def test_resolve_by_name_does_not_verify_another_native_resource_type_absence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    list_calls: list[str] = []

    def domain_absence_during_network_lookup(_name: str) -> object:
        raise _NativeError(42)

    connection = SimpleNamespace(listAllNetworks=lambda: list_calls.append("listed") or [])

    assert (
        _resolve_by_name(
            connection,
            domain_absence_during_network_lookup,
            "listAllNetworks",
            "provision.network.lan",
            "lan",
        )
        is None
    )
    assert list_calls == []
    _assert_recorded(caplog, "_resolve_by_name")


def test_native_action_records_non_tolerated_failure(caplog: pytest.LogCaptureFixture) -> None:
    assert not _invoke_native_action(SimpleNamespace(destroy=_raiser), "destroy", {42, 43})
    _assert_recorded(caplog, "_invoke_native_action")


def test_native_action_keeps_tolerated_failure_silent(caplog: pytest.LogCaptureFixture) -> None:
    def absent() -> None:
        raise _NativeError(42)

    assert _invoke_native_action(SimpleNamespace(destroy=absent), "destroy", {42, 43})
    assert not [record for record in caplog.records if _SUPPRESSED in record.getMessage()]


def test_native_action_does_not_tolerate_a_foreign_code_bearing_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def foreign_absence() -> None:
        raise _ForeignCodeError(42)

    assert not _invoke_native_action(SimpleNamespace(destroy=foreign_absence), "destroy", {42, 43})
    _assert_recorded(caplog, "_invoke_native_action")


def test_native_action_does_not_tolerate_an_unlisted_native_absence_code(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def network_absence() -> None:
        raise _NativeError(43)

    assert not _invoke_native_action(SimpleNamespace(destroy=network_absence), "destroy", {42})
    _assert_recorded(caplog, "_invoke_native_action")


def test_name_availability_does_not_treat_a_foreign_code_bearing_exception_as_absence() -> None:
    def foreign_absence(_name: str) -> object:
        raise _ForeignCodeError(42)

    with pytest.raises(_ForeignCodeError):
        _ensure_name_available(
            SimpleNamespace(lookupByName=foreign_absence),
            "lookupByName",
            "raestest-web",
            "provision.node.web",
        )


def test_name_availability_rejects_another_native_resource_type_absence() -> None:
    def domain_absence_during_network_lookup(_name: str) -> object:
        raise _NativeError(42)

    with pytest.raises(_NativeError):
        _ensure_name_available(
            SimpleNamespace(networkLookupByName=domain_absence_during_network_lookup),
            "networkLookupByName",
            "raestest-lan",
            "provision.network.lan",
        )


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


def test_deployment_destroy_records_a_non_absence_lookup_failure(caplog: pytest.LogCaptureFixture) -> None:
    connection = SimpleNamespace(lookupByName=_raiser)
    driver = _deployment_driver(connection=connection)

    assert not driver._destroy_one(connection, "lookupByName", "provision.node.web")
    _assert_recorded(caplog, "_destroy_one")


def test_deployment_nwfilter_cleanup_records_a_non_absence_failure(
    monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    native = SimpleNamespace(undefine=_raiser)
    driver = _deployment_driver(connection=object())
    driver._filters["provision.node.web"] = "raestest-web-acl"
    monkeypatch.setattr(_deployment, "_find_native", lambda *_args: native)
    monkeypatch.setattr(_deployment, "_existing_uuid", lambda _native: "owned")
    monkeypatch.setattr(_deployment, "_filter_owner_uuid", lambda _address: "owned")

    driver._undefine_nwfilter(object(), "provision.node.web")

    _assert_recorded(caplog, "_undefine_nwfilter")


def test_atomic_write_does_not_misclassify_a_propagated_filesystem_failure(
    tmp_path, monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(_initramfs, "_fsync_directory", _raiser)

    with pytest.raises(RuntimeError, match="forced native failure"):
        _initramfs.atomic_write(tmp_path / "artifact", b"payload", mode=0o600)

    assert not [record for record in caplog.records if _SUPPRESSED in record.getMessage()]


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
