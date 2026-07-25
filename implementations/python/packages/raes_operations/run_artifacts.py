"""Shared run-archive helpers for operational proof artifacts.

Both the TechVault native live gate and the libvirt scenario-evidence producer write
JSON artifacts under a ``runs/<run-id>/<subdir>/`` archive. They share one
definition of a safe run-id filesystem label and one atomic JSON writer here
rather than carrying parallel copies.

The run-id label rule matches the historical TechVault convention
(``^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$``): a leading alphanumeric, then up to 127
characters drawn from alphanumerics, underscore, dot, and hyphen. It rejects path
separators, ``..`` traversal, and leading dots so a caller-supplied run id can
never escape the archive directory.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

RUN_ID_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def is_valid_run_id_label(run_id: str) -> bool:
    """Return True when ``run_id`` is a safe, containment-validated filesystem label."""
    return bool(RUN_ID_LABEL_PATTERN.match(run_id))


def portable_artifact_ref(path: Path) -> str:
    """Return a repository-portable reference without exposing a host path."""

    for anchor in ("examples", "contracts", "specs", "docs"):
        if anchor in path.parts:
            return "/".join(path.parts[path.parts.index(anchor) :])
    return path.name


def run_artifact_path(output_dir: Path, run_id: str, subdir: str, filename: str) -> Path:
    """Return the archive path ``<output_dir>/runs/<run_id>/<subdir>/<filename>``.

    Raises ``ValueError`` when ``run_id`` is not a safe filesystem label so the
    path is never constructed from an unvalidated label.
    """
    if not is_valid_run_id_label(run_id):
        raise ValueError("run id must be a safe filesystem label")
    return output_dir / "runs" / run_id / subdir / filename


def serialize_run_artifact(payload: Mapping[str, Any]) -> str:
    """Serialize a run artifact to canonical JSON text (indent=2, sorted keys, trailing newline)."""
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def atomic_write_json_artifact(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically write ``payload`` as canonical JSON to ``path``.

    Creates the parent directory, writes to a temp file in the same directory, then
    ``os.replace`` to swap it into place so a reader never observes a partial write.
    Cleans up the temp file on any failure before re-raising.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = serialize_run_artifact(payload)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
