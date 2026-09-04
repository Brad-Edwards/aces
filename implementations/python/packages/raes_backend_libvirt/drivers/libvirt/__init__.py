"""Lazy libvirt connection adapter for the libvirt/QEMU backend."""

from __future__ import annotations

from ._native import _ABSENCE_ERROR_CODES as _ABSENCE_ERROR_CODES
from ._native import _DEACTIVATE_TOLERATED_ERROR_CODES as _DEACTIVATE_TOLERATED_ERROR_CODES
from ._native import Connector as Connector
from ._native import _error_code as _error_code
from ._native import _existing_uuid as _existing_uuid
from ._native import _filter_owner_uuid as _filter_owner_uuid
from ._native import _is_absence_error as _is_absence_error
from ._native import _is_expected_list_absence as _is_expected_list_absence
from ._native import _is_expected_lookup_absence as _is_expected_lookup_absence
from ._native import _list_absence_error_codes as _list_absence_error_codes
from ._native import _raes_uuid as _raes_uuid
from .deployment import LibvirtDeploymentDriver as LibvirtDeploymentDriver
