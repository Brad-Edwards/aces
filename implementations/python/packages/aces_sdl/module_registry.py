"""Registry-aware SDL module resolution and publishing."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import yaml
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import Field, ValidationError

from ._base import SDLModel
from ._errors import SDLParseDiagnostic, SDLParseError
from ._source_profile import DEFAULT_SOURCE_PARSE_OPTIONS, SDLSourceParseOptions
from .scenario import ImportDecl, ModuleDescriptor, Scenario

LOCKFILE_NAME = "aces.lock.json"
TRUST_POLICY_NAME = "aces-trust.yaml"
OCI_LAYOUT_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
OCI_CONFIG_MEDIA_TYPE = "application/vnd.aces.module.config.v1+json"
OCI_BUNDLE_MEDIA_TYPE = "application/vnd.aces.module.bundle.v1+tar+gzip"
LOCKFILE_SCHEMA_VERSION = "aces-lock/v1"
TRUST_POLICY_SCHEMA_VERSION = "aces-trust/v1"
OCI_LAYOUT_SCHEMA_VERSION = "aces-module-oci/v1"


def _sha256_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _descriptor_digest(exports: dict[str, list[str]]) -> str:
    return _sha256_digest(json.dumps(exports, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _normalize_exact_or_range(version: str) -> SpecifierSet | None:
    value = (version or "*").strip()
    if value in {"", "*"}:
        return None
    if any(token in value for token in "<>!=~"):
        return SpecifierSet(value)
    return SpecifierSet(f"=={value}")


def _satisfies_version(actual: str, requested: str) -> bool:
    spec = _normalize_exact_or_range(requested)
    if spec is None:
        return True
    try:
        version = Version(actual)
    except InvalidVersion:
        return actual == requested
    return version in spec


class RegistryTrustPolicy(SDLModel):
    require_signatures: bool = True
    trusted_signers: dict[str, str] = Field(default_factory=dict)
    allow_insecure_http: bool = False


class TrustPolicy(SDLModel):
    schema_version: str = TRUST_POLICY_SCHEMA_VERSION
    allow_unsigned_local_sources: bool = True
    registries: dict[str, RegistryTrustPolicy] = Field(default_factory=dict)


class LockRecord(SDLModel):
    source: str
    namespace: str
    requested_version: str = "*"
    resolved_source: str
    module_id: str
    module_version: str
    manifest_digest: str
    content_digest: str
    export_hash: str
    signer_id: str = ""


class Lockfile(SDLModel):
    schema_version: str = LOCKFILE_SCHEMA_VERSION
    imports: list[LockRecord] = Field(default_factory=list)


@dataclass(frozen=True)
class ResolvedModule:
    import_decl: ImportDecl
    module_descriptor: ModuleDescriptor
    root_file: Path
    resolved_source: str
    manifest_digest: str = ""
    content_digest: str = ""
    export_hash: str = ""
    signer_id: str = ""


def _scenario_module_descriptor(scenario: Scenario, *, source_id: str) -> ModuleDescriptor:
    if scenario.module is not None:
        return scenario.module
    raise SDLParseError(
        "Imported SDL units require an explicit module descriptor",
        path=Path(source_id),
    )


def load_trust_policy(base_dir: Path) -> TrustPolicy:
    path = base_dir / TRUST_POLICY_NAME
    if not path.exists():
        return TrustPolicy()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return TrustPolicy.model_validate(payload)


def load_lockfile(base_dir: Path) -> Lockfile | None:
    path = base_dir / LOCKFILE_NAME
    if not path.exists():
        return None
    return Lockfile.model_validate_json(path.read_text(encoding="utf-8"))


def write_lockfile(base_dir: Path, lockfile: Lockfile) -> Path:
    path = base_dir / LOCKFILE_NAME
    path.write_text(
        json.dumps(lockfile.model_dump(mode="python"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _public_key_bytes(encoded_key: str) -> bytes:
    try:
        return base64.b64decode(encoded_key.encode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        raise SDLParseError(f"Invalid trusted signer public key: {exc}") from exc


def _signable_payload(
    module_descriptor: ModuleDescriptor,
    *,
    content_digest: str,
    root_file: str,
) -> bytes:
    """Canonical bytes an Ed25519 signature binds for an OCI module (issue #14).

    The payload binds ``root_file`` alongside the module identity, exports, and
    bundle ``content_digest`` so a compromised registry cannot repoint the module
    entrypoint to a different file inside an otherwise-signed bundle. This is the
    single canonical signer-payload builder: publishing and resolving must produce
    the identical shape or verification fails closed.
    """
    return json.dumps(
        {
            "module_id": module_descriptor.id,
            "module_version": module_descriptor.version,
            "exports": module_descriptor.exports,
            "content_digest": content_digest,
            "root_file": root_file,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _verify_signatures(
    *,
    signatures: list[dict[str, str]],
    trust_policy: RegistryTrustPolicy,
    module_descriptor: ModuleDescriptor,
    content_digest: str,
    root_file: str,
) -> str:
    payload = _signable_payload(module_descriptor, content_digest=content_digest, root_file=root_file)
    for signature_entry in signatures:
        signer_id = str(signature_entry.get("signer_id", ""))
        signature_b64 = str(signature_entry.get("signature", ""))
        public_key = trust_policy.trusted_signers.get(signer_id)
        if not signer_id or not signature_b64 or not public_key:
            continue
        try:
            key = Ed25519PublicKey.from_public_bytes(_public_key_bytes(public_key))
            key.verify(base64.b64decode(signature_b64.encode("utf-8")), payload)
            return signer_id
        except (InvalidSignature, ValueError):
            continue
    raise SDLParseError("No valid trusted signer signature found for OCI module")


def _parse_oci_source(source: str) -> tuple[str, str]:
    ref = source.removeprefix("oci:")
    if "://" in ref:
        ref = ref.split("://", 1)[1]
    if "/" not in ref:
        raise SDLParseError(f"Invalid OCI source '{source}'")
    registry, repository = ref.split("/", 1)
    if not registry or not repository:
        raise SDLParseError(f"Invalid OCI source '{source}'")
    return registry, repository


def _registry_base_url(registry: str, *, allow_insecure_http: bool) -> str:
    if registry.startswith("http://") or registry.startswith("https://"):
        return registry.rstrip("/")
    if allow_insecure_http or registry.startswith(("localhost:", "127.0.0.1:", "localhost/", "127.0.0.1/")):
        return f"http://{registry}".rstrip("/")
    return f"https://{registry}".rstrip("/")


_HTTP_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class _OCIResourceLimits:
    """Bounds for remote OCI fetches and bundle extraction (issue #12).

    The OCI import path pulls attacker-influenceable bytes from allowlisted
    registries; without caps a compromised registry, mirror, or oversized module
    can exhaust process memory (buffering an unbounded response) or disk/CPU
    (extracting an unbounded bundle). Compressed-download limits are kept separate
    from extracted-archive limits because a small gzip can expand into a large tar
    payload. This is the single extensibility seam: operator-tunable overrides
    should later extend ``RegistryTrustPolicy`` and merge with these defaults,
    rather than threading limit arguments through parser/compiler/runtime/CLI.
    """

    timeout_seconds: int = _HTTP_TIMEOUT_SECONDS
    max_metadata_bytes: int = 8 * 1024 * 1024
    max_bundle_bytes: int = 128 * 1024 * 1024
    max_bundle_members: int = 8192
    max_member_bytes: int = 64 * 1024 * 1024
    max_total_bytes: int = 256 * 1024 * 1024


_OCI_LIMITS = _OCIResourceLimits()


class _CappableResponse(Protocol):
    """Minimal HTTP-response surface the bounded reader depends on.

    Structural view of ``http.client.HTTPResponse`` (the ``urlopen`` return) so the
    reader is typed without a bare ``Any``: it only needs a size-capped ``read`` and,
    optionally, response headers for the advisory Content-Length pre-check.
    """

    def read(self, amt: int = ..., /) -> bytes: ...


def _declared_content_length(response: _CappableResponse) -> int | None:
    """Return a validated Content-Length, or ``None`` when the header is absent.

    Content-Length is advisory and attacker-controlled, so it is only ever used to
    reject early - never to size a buffer or to substitute for counting the bytes
    actually read.
    """
    headers = getattr(response, "headers", None)
    raw = headers.get("Content-Length") if headers is not None else None
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise SDLParseError(f"OCI response declares an invalid Content-Length: {raw!r}") from exc
    if value < 0:
        raise SDLParseError(f"OCI response declares a negative Content-Length: {value}")
    return value


def _read_capped(response: _CappableResponse, *, url: str, max_bytes: int) -> bytes:
    """Read at most ``max_bytes`` from ``response``, failing closed if exceeded.

    Rejecting an oversized advisory ``Content-Length`` avoids even starting the
    read; the authoritative check reads ``max_bytes + 1`` so the in-memory buffer
    stays bounded and a registry cannot force the resolver to buffer an unbounded
    blob. Messages name the limit and the safe URL only - never the body.
    """
    declared = _declared_content_length(response)
    if declared is not None and declared > max_bytes:
        raise SDLParseError(
            f"OCI response from {url} declares Content-Length {declared} bytes, exceeding the {max_bytes}-byte limit"
        )
    data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise SDLParseError(f"OCI response from {url} exceeds the {max_bytes}-byte limit")
    return data


def _json_request(url: str, *, headers: dict[str, str] | None = None, max_bytes: int | None = None) -> dict[str, Any]:
    request = Request(url, headers=headers or {})
    limit = _OCI_LIMITS.max_metadata_bytes if max_bytes is None else max_bytes
    try:
        with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(_read_capped(response, url=url, max_bytes=limit).decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        raise SDLParseError(f"Failed to fetch OCI metadata from {url}: {exc}") from exc


def _bytes_request(url: str, *, headers: dict[str, str] | None = None, max_bytes: int | None = None) -> bytes:
    request = Request(url, headers=headers or {})
    limit = _OCI_LIMITS.max_metadata_bytes if max_bytes is None else max_bytes
    try:
        with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            return _read_capped(response, url=url, max_bytes=limit)
    except (HTTPError, URLError) as exc:
        raise SDLParseError(f"Failed to fetch OCI blob from {url}: {exc}") from exc


def _select_tag(tags: list[str], requested_version: str) -> str:
    spec = _normalize_exact_or_range(requested_version)
    if spec is None:
        versions = []
        for tag in tags:
            try:
                versions.append((Version(tag), tag))
            except InvalidVersion:
                continue
        if versions:
            return max(versions)[1]
        if tags:
            return sorted(tags)[-1]
        raise SDLParseError("OCI module has no published tags")
    matching: list[tuple[Version, str]] = []
    for tag in tags:
        try:
            version = Version(tag)
        except InvalidVersion:
            continue
        if version in spec:
            matching.append((version, tag))
    if matching:
        return max(matching)[1]
    raise SDLParseError(f"No OCI module tag satisfies requested version '{requested_version}'")


def _oci_cache_dir(base_dir: Path) -> Path:
    return base_dir / ".aces" / "module-cache"


def _validate_tar_member_shape(
    member: tarfile.TarInfo,
    *,
    dest: Path,
    resolved_dest: Path,
    seen_paths: set[str],
    limits: _OCIResourceLimits,
) -> None:
    """Fail closed on an unsafe or oversized single tar member (issues #12/#13).

    Rejects path traversal, symlinks, hard links, special files, and duplicate
    normalized paths, and enforces the per-member extracted-size cap. Records the
    member's normalized path in ``seen_paths`` so a later duplicate is caught.
    """
    member_path = (dest / member.name).resolve()
    if not member_path.is_relative_to(resolved_dest):
        raise SDLParseError(f"Path traversal detected in OCI bundle tar member: {member.name!r}")
    if member.issym() or member.islnk():
        raise SDLParseError(f"Links are not allowed in OCI bundle tar: {member.name!r}")
    if not (member.isfile() or member.isdir()):
        raise SDLParseError(f"Unsupported tar member type in OCI bundle: {member.name!r}")
    normalized = member_path.as_posix()
    if normalized in seen_paths:
        raise SDLParseError(f"Duplicate tar member path in OCI bundle: {member.name!r}")
    seen_paths.add(normalized)
    # Account by the logical member size so a sparse or padded member cannot
    # understate the bytes it will extract.
    if member.isfile() and member.size > limits.max_member_bytes:
        raise SDLParseError(
            f"OCI bundle member {member.name!r} exceeds the {limits.max_member_bytes}-byte per-member limit"
        )


def _safe_tar_members(
    tar: tarfile.TarFile,
    dest: Path,
) -> list[tarfile.TarInfo]:
    """Validate every tar member before extraction (fail closed).

    The OCI bundle bytes are attacker-controlled even after registry allowlisting,
    digest pinning, and signature verification, so this validation is the
    filesystem-write boundary for module import resolution. It must hold on every
    supported runtime, not just on Python 3.12+ where ``extractall(filter="data")``
    is available, because the PEP 706 ``filter`` keyword was backported only in
    Python 3.11.4 while the project supports ``>=3.11``. Validation therefore
    matches the ``data`` filter's guarantees: reject path traversal, symlinks,
    hard links, and special files, and strip setuid/setgid/sticky bits.

    It is also the resource-exhaustion boundary (issue #12): the archive member
    count, per-member extracted size, and total extracted bytes are bounded by
    ``_OCI_LIMITS`` and duplicate normalized paths are rejected, so a malicious or
    oversized bundle cannot exhaust disk or CPU during extraction.
    """
    limits = _OCI_LIMITS
    safe: list[tarfile.TarInfo] = []
    resolved_dest = dest.resolve()
    seen_paths: set[str] = set()
    total_bytes = 0
    # Iterate lazily rather than materialising ``tar.getmembers()`` so a bundle that
    # declares an unbounded member list, or expands into an unbounded extraction, is
    # rejected as soon as a cap is crossed - before the remainder of the archive is
    # decompressed (issue #12).
    for member_count, member in enumerate(tar, start=1):
        if member_count > limits.max_bundle_members:
            raise SDLParseError(f"OCI bundle exceeds the maximum of {limits.max_bundle_members} archive members")
        _validate_tar_member_shape(
            member,
            dest=dest,
            resolved_dest=resolved_dest,
            seen_paths=seen_paths,
            limits=limits,
        )
        if member.isfile():
            total_bytes += member.size
            if total_bytes > limits.max_total_bytes:
                raise SDLParseError(f"OCI bundle exceeds the {limits.max_total_bytes}-byte total extraction limit")
        # Drop setuid/setgid/sticky bits.
        member.mode &= 0o777
        safe.append(member)
    return safe


def _extract_bundle_to_cache(
    *,
    bundle_bytes: bytes,
    manifest_digest: str,
    root_file: str,
    base_dir: Path,
) -> Path:
    cache_dir = _oci_cache_dir(base_dir) / manifest_digest
    if ".." in Path(root_file).parts or Path(root_file).is_absolute():
        raise SDLParseError(f"Invalid OCI root_file path: {root_file!r}")
    resolved_cache = cache_dir.resolve()
    root_path = cache_dir / root_file
    if not root_path.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(bundle_bytes), mode="r:gz") as tar:
            # Validate every member up front so the security property is identical on
            # all supported runtimes and never depends on the runtime's tarfile filter
            # support. ``filter="data"`` is applied as defense in depth where available
            # (Python 3.11.4+/3.12+); on 3.11.0–3.11.3 the keyword is absent and the
            # already-validated members are the guarantee. No path falls back to an
            # unfiltered ``tar.extractall(cache_dir)``.
            safe_members = _safe_tar_members(tar, cache_dir)
            try:
                tar.extractall(cache_dir, members=safe_members, filter="data")
            # Python 3.11.0–3.11.3 lack the PEP 706 filter keyword.
            except TypeError:
                tar.extractall(cache_dir, members=safe_members)
    # Enforce the root-file containment contract on EVERY return path, including
    # the cache-hit fast path: a stale cache (e.g. one populated by an earlier
    # unsafe extractor) could hold a symlink or a non-regular file at root_file
    # that resolves outside the digest cache. Validating here fails closed
    # regardless of whether extraction ran this call.
    if not root_path.is_file() or not root_path.resolve().is_relative_to(resolved_cache):
        raise SDLParseError(f"Resolved OCI module bundle is missing declared root file '{root_file}'")
    return root_path


def _lock_record_for(lockfile: Lockfile | None, import_decl: ImportDecl) -> LockRecord | None:
    if lockfile is None:
        return None
    for record in lockfile.imports:
        if (
            record.source == import_decl.normalized_source
            and record.namespace == import_decl.namespace
            and record.requested_version == (import_decl.version or "*")
        ):
            return record
    return None


def _verify_allowed_parameters(
    import_decl: ImportDecl,
    descriptor: ModuleDescriptor,
) -> None:
    allowed = set(descriptor.parameters)
    disallowed = sorted(name for name in import_decl.parameters if name not in allowed)
    if disallowed:
        raise SDLParseError(f"Import parameters not allowed by module '{descriptor.id}': " + ", ".join(disallowed))


def _validate_digest_pin(actual_digest: str, expected_digest: str, *, source: str) -> None:
    if not expected_digest:
        return
    normalized_actual = actual_digest.removeprefix("sha256:")
    normalized_expected = expected_digest.removeprefix("sha256:")
    if normalized_actual != normalized_expected:
        raise SDLParseError(f"Digest mismatch for import '{source}': {expected_digest!r} != {actual_digest!r}")


def _local_resolved_source(import_path: Path, base_dir: Path) -> str:
    """Persisted lock identity for a ``local:`` import (issue #551).

    The lockfile is committed and verified across machines and CI, so a local
    import's ``resolved_source`` must be a checkout-independent identity rather
    than an absolute, machine-specific path. Express it relative to the SDL base
    directory using POSIX separators so the same lockfile verifies on any
    checkout. ``ResolvedModule.root_file`` remains the absolute runtime ``Path``
    used for reads, digesting, parsing, and cycle detection; this is the single
    normalization seam for persisted local lock identity (OCI imports keep their
    registry/digest identity).
    """
    relative = os.path.relpath(import_path, base_dir.resolve())
    return Path(relative).as_posix()


def resolve_import(
    import_decl: ImportDecl,
    *,
    base_dir: Path,
    lockfile: Lockfile | None = None,
    trust_policy: TrustPolicy | None = None,
    source_options: SDLSourceParseOptions = DEFAULT_SOURCE_PARSE_OPTIONS,
    source_diagnostics: list[SDLParseDiagnostic] | None = None,
) -> ResolvedModule:
    trust_policy = trust_policy or TrustPolicy()
    source = import_decl.normalized_source
    if source.startswith("locked:"):
        locked_ref = source.removeprefix("locked:")
        if lockfile is None:
            raise SDLParseError(f"Locked import '{source}' requires {LOCKFILE_NAME}")
        record = next(
            (
                candidate
                for candidate in lockfile.imports
                if candidate.resolved_source == locked_ref or candidate.source == locked_ref
            ),
            None,
        )
        if record is None:
            raise SDLParseError(f"Locked import '{source}' is not present in {LOCKFILE_NAME}")
        delegated = ImportDecl(
            source=record.source,
            namespace=import_decl.namespace or record.namespace,
            version=record.requested_version,
            parameters=dict(import_decl.parameters),
            digest=import_decl.digest or record.content_digest,
        )
        return resolve_import(
            delegated,
            base_dir=base_dir,
            lockfile=lockfile,
            trust_policy=trust_policy,
            source_options=source_options,
            source_diagnostics=source_diagnostics,
        )
    if source.startswith("local:"):
        relative = source.removeprefix("local:")
        import_path = (base_dir / relative).resolve()
        if not import_path.is_relative_to(base_dir.resolve()):
            raise SDLParseError(f"Local import path escapes base directory: {relative!r}")
        if not import_path.exists():
            raise SDLParseError(f"Imported SDL file not found: {relative}")
        from .parser import _load_normalized_data

        imported_raw = _load_normalized_data(
            import_path.read_text(encoding="utf-8"),
            path=import_path,
            source_format=source_options.source_format,
            migration_policy=source_options.migration_policy,
            limits=source_options.limits,
            source_diagnostics=source_diagnostics,
        )
        imported_scenario = Scenario.model_validate(imported_raw)
        descriptor = _scenario_module_descriptor(
            imported_scenario,
            source_id=relative.replace("\\", "/"),
        )
        content_digest = f"sha256:{_sha256_digest(import_path.read_bytes())}"
        if not _satisfies_version(descriptor.version, import_decl.version):
            raise SDLParseError(
                f"Import '{relative}' requested version {import_decl.version!r} "
                f"but module declares {descriptor.version!r}"
            )
        if not trust_policy.allow_unsigned_local_sources:
            raise SDLParseError(
                "Local SDL imports are disabled by trust policy because unsigned local sources are not allowed"
            )
        _validate_digest_pin(content_digest, import_decl.digest, source=source)
        locked = _lock_record_for(lockfile, import_decl)
        if locked is not None and locked.content_digest:
            _validate_digest_pin(content_digest, locked.content_digest, source=source)
        _verify_allowed_parameters(import_decl, descriptor)
        return ResolvedModule(
            import_decl=import_decl,
            module_descriptor=descriptor,
            root_file=import_path,
            resolved_source=_local_resolved_source(import_path, base_dir),
            content_digest=content_digest,
            export_hash=_descriptor_digest(descriptor.exports),
        )

    if not source.startswith("oci:"):
        raise SDLParseError(f"Unsupported import source '{source}'")

    registry, repository = _parse_oci_source(source)
    registry_policy = trust_policy.registries.get(registry)
    if registry_policy is None:
        raise SDLParseError(f"Registry '{registry}' is not allowed by trust policy")
    base_url = _registry_base_url(
        registry,
        allow_insecure_http=registry_policy.allow_insecure_http,
    )
    locked = _lock_record_for(lockfile, import_decl)
    manifest_ref = locked.manifest_digest if locked is not None else None
    if manifest_ref is None:
        tags_payload = _json_request(f"{base_url}/v2/{quote(repository, safe='/')}/tags/list")
        tags = list(tags_payload.get("tags") or [])
        manifest_ref = _select_tag(tags, import_decl.version)
    manifest_bytes = _bytes_request(
        f"{base_url}/v2/{quote(repository, safe='/')}/manifests/{quote(str(manifest_ref), safe=':@/')}",
        headers={"Accept": OCI_LAYOUT_MEDIA_TYPE},
    )
    manifest_digest = f"sha256:{_sha256_digest(manifest_bytes)}"
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if locked is not None and locked.manifest_digest != manifest_digest:
        raise SDLParseError(
            f"Lockfile digest mismatch for import '{source}': {locked.manifest_digest!r} != {manifest_digest!r}"
        )
    config = manifest.get("config", {})
    layer = next(
        (candidate for candidate in manifest.get("layers", []) if candidate.get("mediaType") == OCI_BUNDLE_MEDIA_TYPE),
        None,
    )
    if not config or not layer:
        raise SDLParseError(f"OCI module '{source}' is missing config or bundle layer")
    config_digest = str(config.get("digest", ""))
    layer_digest = str(layer.get("digest", ""))
    # Verify the config blob bytes hash to the manifest's config.digest BEFORE
    # decoding the JSON (issue #14). Fetching by digest is not integrity: a
    # compromised registry can serve arbitrary bytes for the config endpoint, and
    # those bytes carry the unsigned-by-default root_file that selects the module
    # entrypoint. Hash the exact bytes received - never a reserialized object -
    # and reuse the bundle's digest spelling.
    config_bytes = _bytes_request(
        f"{base_url}/v2/{quote(repository, safe='/')}/blobs/{quote(config_digest, safe=':@/')}"
    )
    if f"sha256:{_sha256_digest(config_bytes)}" != config_digest:
        raise SDLParseError(f"OCI module '{source}' config digest verification failed")
    config_payload = json.loads(config_bytes.decode("utf-8"))
    bundle_bytes = _bytes_request(
        f"{base_url}/v2/{quote(repository, safe='/')}/blobs/{quote(layer_digest, safe=':@/')}",
        max_bytes=_OCI_LIMITS.max_bundle_bytes,
    )
    if f"sha256:{_sha256_digest(bundle_bytes)}" != layer_digest:
        raise SDLParseError(f"OCI module '{source}' bundle digest verification failed")
    try:
        descriptor = ModuleDescriptor.model_validate(config_payload.get("module", {}))
    except ValidationError as exc:
        raise SDLParseError(f"OCI module '{source}' has invalid module descriptor: {exc}") from exc
    if locked is not None and locked.module_id != descriptor.id:
        raise SDLParseError(
            f"Lockfile module id mismatch for import '{source}': {locked.module_id!r} != {descriptor.id!r}"
        )
    if not _satisfies_version(descriptor.version, import_decl.version):
        raise SDLParseError(
            f"OCI import '{source}' requested version {import_decl.version!r} "
            f"but resolved module declares {descriptor.version!r}"
        )
    content_digest = layer_digest
    _validate_digest_pin(content_digest, import_decl.digest, source=source)
    # Resolve the config-declared root_file as a single string before it reaches
    # the signature payload or extraction (issue #14). Signing and extracting the
    # SAME value closes the gap where a signature verified over a default root_file
    # while a different attacker-declared root_file was extracted.
    raw_root_file = config_payload.get("root_file", "module.yaml")
    if not isinstance(raw_root_file, str):
        raise SDLParseError(f"OCI module '{source}' declares a non-string root_file")
    root_file = raw_root_file
    signer_id = ""
    if registry_policy.require_signatures:
        signer_id = _verify_signatures(
            signatures=list(config_payload.get("signatures", [])),
            trust_policy=registry_policy,
            module_descriptor=descriptor,
            content_digest=content_digest,
            root_file=root_file,
        )
    resolved_root = _extract_bundle_to_cache(
        bundle_bytes=bundle_bytes,
        manifest_digest=manifest_digest.replace("sha256:", ""),
        root_file=root_file,
        base_dir=base_dir,
    )
    _verify_allowed_parameters(import_decl, descriptor)
    export_hash = _descriptor_digest(descriptor.exports)
    if locked is not None and locked.export_hash != export_hash:
        raise SDLParseError(f"Lockfile export hash mismatch for import '{source}'")
    return ResolvedModule(
        import_decl=import_decl,
        module_descriptor=descriptor,
        root_file=resolved_root,
        resolved_source=f"{registry}/{repository}@{manifest_digest}",
        manifest_digest=manifest_digest,
        content_digest=content_digest,
        export_hash=export_hash,
        signer_id=signer_id,
    )


def resolve_lock_records(
    root_path: Path,
    *,
    trust_policy: TrustPolicy | None = None,
) -> Lockfile:
    from .parser import _load_normalized_data

    trust_policy = trust_policy or load_trust_policy(root_path.parent)
    root_data = _load_normalized_data(root_path.read_text(encoding="utf-8"), path=root_path)
    imports = [ImportDecl.model_validate(item) for item in root_data.get("imports", [])]
    records: list[LockRecord] = []
    for import_decl in imports:
        resolved = resolve_import(
            import_decl,
            base_dir=root_path.parent,
            trust_policy=trust_policy,
        )
        records.append(
            LockRecord(
                source=import_decl.normalized_source,
                namespace=import_decl.namespace,
                requested_version=import_decl.version or "*",
                resolved_source=resolved.resolved_source,
                module_id=resolved.module_descriptor.id,
                module_version=resolved.module_descriptor.version,
                manifest_digest=resolved.manifest_digest,
                content_digest=resolved.content_digest,
                export_hash=resolved.export_hash,
                signer_id=resolved.signer_id,
            )
        )
    return Lockfile(imports=records)


def _collect_local_bundle_files(
    root_path: Path,
    *,
    seen: set[Path] | None = None,
) -> dict[Path, bytes]:
    from .parser import _load_normalized_data

    seen = set() if seen is None else set(seen)
    resolved = root_path.resolve()
    if resolved in seen:
        raise SDLParseError(f"Import cycle detected at {resolved}")
    seen.add(resolved)
    payload = _load_normalized_data(root_path.read_text(encoding="utf-8"), path=root_path)
    files = {resolved: root_path.read_bytes()}
    for raw_import in payload.get("imports", []):
        import_decl = ImportDecl.model_validate(raw_import)
        source = import_decl.normalized_source
        if not source.startswith("local:"):
            raise SDLParseError(
                "Publishing modules with remote OCI imports is not supported; "
                "publish a self-contained local module graph"
            )
        child_path = (resolved.parent / source.removeprefix("local:")).resolve()
        if not child_path.is_relative_to(resolved.parent):
            raise SDLParseError(f"Local import path escapes base directory: {source!r}")
        files.update(_collect_local_bundle_files(child_path, seen=seen))
    return files


def publish_module_to_oci_layout(
    root_path: Path,
    *,
    output_dir: Path,
    signer_id: str = "",
    private_key_path: Path | None = None,
) -> dict[str, Any]:
    from .parser import parse_sdl_file

    scenario = parse_sdl_file(root_path, skip_semantic_validation=True)
    descriptor = _scenario_module_descriptor(
        scenario,
        source_id=str(root_path.name),
    )
    files = _collect_local_bundle_files(root_path)
    relative_files = {path.relative_to(root_path.parent).as_posix(): content for path, content in files.items()}
    bundle_buffer = io.BytesIO()
    with tarfile.open(fileobj=bundle_buffer, mode="w:gz") as tar:
        for relative_name, content in sorted(relative_files.items()):
            info = tarfile.TarInfo(name=relative_name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    bundle_bytes = bundle_buffer.getvalue()
    content_digest = f"sha256:{_sha256_digest(bundle_bytes)}"
    signatures: list[dict[str, str]] = []
    if signer_id and private_key_path is not None:
        private_key = serialization.load_pem_private_key(
            private_key_path.read_bytes(),
            password=None,
        )
        if not isinstance(private_key, Ed25519PrivateKey):
            raise SDLParseError("Publishing key must be an Ed25519 private key")
        signature = private_key.sign(
            _signable_payload(descriptor, content_digest=content_digest, root_file=root_path.name)
        )
        signatures.append(
            {
                "signer_id": signer_id,
                "signature": base64.b64encode(signature).decode("utf-8"),
            }
        )
    config_payload = {
        "schema_version": OCI_LAYOUT_SCHEMA_VERSION,
        "root_file": root_path.name,
        "module": descriptor.model_dump(mode="python", by_alias=True),
        "signatures": signatures,
    }
    config_bytes = json.dumps(config_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    config_digest = f"sha256:{_sha256_digest(config_bytes)}"
    manifest_payload = {
        "schemaVersion": 2,
        "mediaType": OCI_LAYOUT_MEDIA_TYPE,
        "config": {
            "mediaType": OCI_CONFIG_MEDIA_TYPE,
            "digest": config_digest,
            "size": len(config_bytes),
        },
        "layers": [
            {
                "mediaType": OCI_BUNDLE_MEDIA_TYPE,
                "digest": content_digest,
                "size": len(bundle_bytes),
            }
        ],
        "annotations": {
            "org.opencontainers.image.ref.name": descriptor.version,
            "io.aces.module.id": descriptor.id,
        },
    }
    manifest_bytes = json.dumps(manifest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_digest = f"sha256:{_sha256_digest(manifest_bytes)}"
    layout_dir = output_dir / f"{descriptor.id.replace('/', '_')}-{descriptor.version}.oci"
    blobs_dir = layout_dir / "blobs" / "sha256"
    blobs_dir.mkdir(parents=True, exist_ok=True)
    (layout_dir / "oci-layout").write_text('{"imageLayoutVersion":"1.0.0"}\n', encoding="utf-8")
    (blobs_dir / config_digest.removeprefix("sha256:")).write_bytes(config_bytes)
    (blobs_dir / content_digest.removeprefix("sha256:")).write_bytes(bundle_bytes)
    (blobs_dir / manifest_digest.removeprefix("sha256:")).write_bytes(manifest_bytes)
    (layout_dir / "index.json").write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "manifests": [
                    {
                        "mediaType": OCI_LAYOUT_MEDIA_TYPE,
                        "digest": manifest_digest,
                        "size": len(manifest_bytes),
                        "annotations": {
                            "org.opencontainers.image.ref.name": descriptor.version,
                            "io.aces.module.id": descriptor.id,
                        },
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "layout_dir": str(layout_dir),
        "module_id": descriptor.id,
        "module_version": descriptor.version,
        "manifest_digest": manifest_digest,
        "content_digest": content_digest,
        "export_hash": _descriptor_digest(descriptor.exports),
        "signer_id": signer_id,
    }
