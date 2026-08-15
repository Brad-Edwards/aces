"""Backend-local observability for native libvirt failures.

The portable driver boundary deliberately collapses native errors into
value-free diagnostics; this logger records the collapsed detail on the
operator's side of that boundary. It is silent unless the embedding
application configures logging for ``raes_backend_libvirt``.
"""

from __future__ import annotations

import logging

LOGGER = logging.getLogger("raes_backend_libvirt")
NATIVE_FAILURE_LOG = "%s suppressed a native libvirt failure"
