"""Backend capability profiles, corpus roots, and profile loading."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from aces_contracts.backend_profiles import (
    BackendProfileModel,
    backend_profile_path,
    backend_profiles_root,
    load_backend_profile_from_path,
)
from aces_contracts.corpus import FIXTURES, corpus_family_root
from aces_contracts.diagnostics import Diagnostic
from pydantic import ValidationError

from aces_conformance.conformance.diagnostics import _diagnostic


class BackendCapabilityProfile(str, Enum):
    """Known backend capability profile ids the runner can map to known runtime surfaces.

    The published ``contracts/profiles/backend/*.json`` corpus is the authority
    for profile *contract sets* — this enum is intentionally NOT used to gate
    which profile ids the CLI / API will accept. It is the inference target of
    :func:`profile_for_manifest` and the dispatch key for capability-gap and
    live-probe behavior that depends on a *known* runtime surface (e.g. only
    the FULL_REMOTE_CONTROL_PLANE family drives the participant-episode probe).
    Unknown profile ids loaded from the JSON corpus are still validated and
    fixture-tested; they just skip capability and live-probe behavior because
    their runtime surface contract is not known to this implementation.
    """

    PROVISIONING_ONLY = "provisioning-only"
    ORCHESTRATION_CAPABLE = "orchestration-capable"
    ORCHESTRATION_EVALUATION = "orchestration-evaluation"
    FULL_REMOTE_CONTROL_PLANE = "full-remote-control-plane"


BackendProfileSelector = str | BackendCapabilityProfile
"""Type alias for any callable that accepts either a free-form profile id string
or a known :class:`BackendCapabilityProfile` enum member. The CLI and runner
accept either so adding a new published profile JSON does not require a
Python-side enum edit."""


def _to_profile_id(profile: BackendProfileSelector) -> str:
    """Normalize a profile selector to its published id string."""

    return profile.value if isinstance(profile, BackendCapabilityProfile) else profile


def _to_known_profile(profile: BackendProfileSelector) -> BackendCapabilityProfile | None:
    """Return the matching :class:`BackendCapabilityProfile` when ``profile`` is
    a known runtime surface, else ``None``. Used to gate capability-gap and
    live-probe behavior, both of which depend on knowing the runtime surface
    contract for the profile."""

    if isinstance(profile, BackendCapabilityProfile):
        return profile
    try:
        return BackendCapabilityProfile(profile)
    except ValueError:
        return None


def fixtures_root() -> Path:
    return corpus_family_root(FIXTURES)


def profiles_root() -> Path:
    return backend_profiles_root()


def _fixture_contract_root(root: Path, contract_name: str) -> Path:
    matches = sorted(path for path in root.glob(f"**/{contract_name}") if path.is_dir())
    if matches:
        return matches[0]
    return root / contract_name


def _load_backend_profile(
    profile: BackendProfileSelector,
    *,
    profiles_root: Path | None = None,
) -> BackendProfileModel:
    """Load a published backend profile from ``contracts/profiles/backend``.

    ``profiles_root`` lets tests redirect the loader at a temporary corpus,
    matching how ``run_fixture_suite`` accepts a ``root`` override for fixtures.
    Identity checks (filename stem == payload ``profile``) and profile-id
    grammar validation are enforced by the shared
    :func:`load_backend_profile_from_path` helper. The override path here
    *also* confines the resolved path to under the supplied ``profiles_root``
    so a caller cannot escape it even if the grammar check were ever relaxed.
    """

    profile_id = _to_profile_id(profile)
    if profiles_root is None:
        path = backend_profile_path(profile_id)
    else:
        root = profiles_root.resolve()
        candidate = (root / f"{profile_id}.json").resolve()
        if not _path_is_within(candidate, root):
            raise ValueError(
                f"backend profile id {profile_id!r} resolves to {candidate} "
                f"which is outside the configured profiles root {root}; refusing to load."
            )
        path = candidate
    return load_backend_profile_from_path(profile_id, path)


def _path_is_within(candidate: Path, root: Path) -> bool:
    """Return ``True`` iff ``candidate`` is the same as or under ``root``."""

    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def required_contracts(
    profile: BackendProfileSelector,
    *,
    profiles_root: Path | None = None,
) -> frozenset[str]:
    """Return the contracts a backend must honor for ``profile``.

    The contract set is loaded from the published
    ``contracts/profiles/backend/<profile>.json`` artifact — that file is the
    single source of truth for the profile-to-contract mapping (ASR-502).
    ``profile`` may be a free-form profile id string (the discoverable artifact
    name) or a known :class:`BackendCapabilityProfile` enum member. Raises
    ``FileNotFoundError`` / ``json.JSONDecodeError`` / ``ValidationError`` /
    ``ValueError`` when the artifact is missing, malformed, or mislabeled;
    the runner-facing :func:`_resolve_required_contracts` wraps those into
    structured conformance diagnostics.
    """

    return frozenset(_load_backend_profile(profile, profiles_root=profiles_root).required_contracts)


def _resolve_required_contracts(
    profile: BackendProfileSelector,
    *,
    profiles_root: Path | None = None,
) -> tuple[frozenset[str], tuple[Diagnostic, ...]]:
    """Load the profile's contract set, converting load failures to diagnostics.

    Profile JSON loading is now a hard prerequisite of every conformance run
    (ASR-502), but the runner's public contract is to return a
    :class:`BackendConformanceReport` rather than raise. Any failure to load
    the published profile — missing file, malformed JSON, schema-rejected
    payload, swapped artifact — therefore surfaces as a
    ``conformance.profile-load-failed`` diagnostic on the report so the CLI
    can still print the structured response and CI gates can still parse it.
    """

    profile_id = _to_profile_id(profile)
    try:
        return required_contracts(profile, profiles_root=profiles_root), ()
    except (FileNotFoundError, ValueError) as exc:
        return frozenset(), (
            _diagnostic(
                "conformance.profile-load-failed",
                profile_id,
                f"Failed to load published backend profile {profile_id!r}: {_sanitize_load_error(exc)}",
            ),
        )


def _sanitize_load_error(exc: Exception) -> str:
    """Render a profile-load exception without echoing rejected file contents.

    Pydantic's ``ValidationError`` carries the rejected ``input_value`` and can
    surface it in ``str(exc)``. For a profile-load failure the diagnostic
    should describe *what* went wrong (file missing, malformed JSON, identity
    mismatch, schema-rejected) without quoting the failed input back to the
    caller — that would turn a malformed-profile failure into a file-content
    disclosure oracle when the loader is wrapped behind a less-trusted
    boundary.
    """

    if isinstance(exc, FileNotFoundError):
        message = "profile artifact not found"
    elif isinstance(exc, json.JSONDecodeError):
        message = "profile artifact is not valid JSON"
    elif isinstance(exc, ValidationError):
        message = f"profile artifact failed closed-world validation ({exc.error_count()} error(s))"
    else:
        message = f"{type(exc).__name__}: {exc}"
    return message
