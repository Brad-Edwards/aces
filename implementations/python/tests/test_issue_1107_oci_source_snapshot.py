"""Issue #1107: descriptor-bound OCI source snapshots close cache TOCTOU gaps."""

from __future__ import annotations

import gzip
import hashlib
import io
import os
import stat
import tarfile
from pathlib import Path, PurePosixPath

import pytest
import raes.module_registry as module_registry
import raes.module_registry._verified_sources as verified_sources
import raes.module_registry.resolution as module_registry_resolution
from raes._errors import SDLParseError
from raes._source_profile import DEFAULT_SOURCE_PARSE_OPTIONS, SDLParserLimits, SDLSourceParseOptions
from raes.composition import expand_sdl_modules


def _entry(path: Path, relative: str, *, digest: str | None = None) -> dict[str, object]:
    metadata = path.lstat()
    payload = path.read_bytes() if stat.S_ISREG(metadata.st_mode) else b""
    return {
        "path": relative,
        "type": "file",
        "size": metadata.st_size,
        "mode": stat.S_IMODE(metadata.st_mode),
        "digest": digest or f"sha256:{hashlib.sha256(payload).hexdigest()}",
    }


def _manifest(root: Path, relative_paths: list[str]) -> dict[str, object]:
    entries: list[object] = [None, {"path": ".", "type": "directory"}]
    entries.extend(_entry(root.joinpath(*PurePosixPath(relative).parts), relative) for relative in relative_paths)
    return {"entries": entries}


def _bundle(members: list[tuple[str, bytes]]) -> bytes:
    compressed = io.BytesIO()
    with (
        gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as stream,
        tarfile.open(fileobj=stream, mode="w") as archive,
    ):
        for name, payload in members:
            member = tarfile.TarInfo(name=name)
            member.mode = 0o644
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
    return compressed.getvalue()


def test_verified_snapshot_cache_miss_and_hit_capture_nested_graph(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_payload = b"""name: root
module: {id: acme/root, version: 1.0.0}
imports:
  - source: local:child.yaml
    namespace: child
"""
    child_payload = b"name: child\nmodule: {id: acme/child, version: 1.0.0}\n"
    bundle = _bundle([("nested/module.yaml", root_payload), ("nested/child.yaml", child_payload)])
    digest = f"sha256:{module_registry._sha256_digest(bundle)}"
    arguments = {
        "bundle_bytes": bundle,
        "manifest_digest": "snapshot-hit",
        "content_digest": digest,
        "root_file": "nested/module.yaml",
        "base_dir": tmp_path,
        "source_options": DEFAULT_SOURCE_PARSE_OPTIONS,
    }

    missed = module_registry._extract_bundle_to_cache(**arguments)

    assert isinstance(missed, module_registry._VerifiedSourceBundle)
    assert list(missed.documents) == ["nested/child.yaml", "nested/module.yaml"]
    assert (
        missed.resolve_local(base_dir=missed.cache_root / "nested", relative="child.yaml")[1].raw_bytes == child_payload
    )

    def forbid_staging(*_args, **_kwargs):
        pytest.fail("an admitted cache hit must not stage or extract another version")

    monkeypatch.setattr(module_registry, "_new_version_stage", forbid_staging)
    monkeypatch.setattr(tarfile.TarFile, "extractall", forbid_staging)
    hit = module_registry._extract_bundle_to_cache(**arguments)

    assert isinstance(hit, module_registry._VerifiedSourceBundle)
    assert hit.cache_root == missed.cache_root
    assert hit.documents == missed.documents


def test_verified_bundle_paths_are_lexical_confined_and_immutable(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    (root / "nested").mkdir(parents=True)
    (root / "nested" / "module.yaml").write_text(
        """name: root
imports:
  - source: local:../common.yaml
    namespace: common
""",
        encoding="utf-8",
    )
    (root / "common.yaml").write_text(
        """name: common
imports:
  - source: local:nested/module.yaml
    namespace: cycle
  - source: oci:registry.example/acme/remote
    namespace: remote
""",
        encoding="utf-8",
    )
    snapshot = verified_sources._read_verified_source_bundle(
        cache_root=root,
        expected_manifest=_manifest(root, ["nested/module.yaml", "common.yaml"]),
        root_relative=PurePosixPath("nested/module.yaml"),
        source_options=DEFAULT_SOURCE_PARSE_OPTIONS,
    )

    assert list(snapshot.documents) == ["common.yaml", "nested/module.yaml"]
    assert snapshot.identity_path(root / "common.yaml") == root.absolute() / "common.yaml"
    assert verified_sources._cache_relative_path(root, root) == "."
    assert snapshot.resolve_local(base_dir=root / "nested", relative=r"..\common.yaml")[0] == root / "common.yaml"
    with pytest.raises(TypeError):
        snapshot.documents["new.yaml"] = snapshot.documents["common.yaml"]  # type: ignore[index]
    with pytest.raises(SDLParseError, match="not found"):
        snapshot.resolve_local(base_dir=root, relative="absent.yaml")
    with pytest.raises(SDLParseError, match="escapes the verified"):
        snapshot.identity_path(tmp_path / "outside.yaml")


@pytest.mark.parametrize(
    ("base_relative", "relative"),
    [
        (".", ""),
        (".", "bad\x00name"),
        (".", "/absolute.yaml"),
        (".", "C:/windows.yaml"),
        (".", "../escape.yaml"),
        ("nested", ".."),
    ],
)
def test_verified_bundle_path_normalization_rejects_escape(
    base_relative: str,
    relative: str,
) -> None:
    with pytest.raises(SDLParseError, match="escapes base directory"):
        verified_sources._normalize_bundle_path(base_relative, relative)


@pytest.mark.parametrize("mismatch", ["type", "size", "mode"])
def test_verified_source_rejects_initial_metadata_mismatch(tmp_path: Path, mismatch: str) -> None:
    path = tmp_path / "source.yaml"
    path.write_bytes(b"name: source\n")
    expected = _entry(path, path.name)
    if mismatch == "type":
        path.unlink()
        path.mkdir()
        expected["size"] = path.stat().st_size
        expected["mode"] = stat.S_IMODE(path.stat().st_mode)
    elif mismatch == "size":
        expected["size"] = int(expected["size"]) + 1
    else:
        expected["mode"] = int(expected["mode"]) ^ 0o100

    with pytest.raises(SDLParseError, match="integrity validation"):
        verified_sources._read_verified_cache_source(
            path,
            expected_entry=expected,
            source_options=DEFAULT_SOURCE_PARSE_OPTIONS,
        )


def _changed_stat(metadata: os.stat_result, mismatch: str) -> os.stat_result:
    values = list(metadata)
    if mismatch == "type":
        values[0] = stat.S_IFDIR | stat.S_IMODE(metadata.st_mode)
    elif mismatch == "identity":
        values[2] = metadata.st_dev + 1
    elif mismatch == "size":
        values[6] = metadata.st_size + 1
    else:
        values[0] ^= 0o100
    return os.stat_result(values)


@pytest.mark.parametrize("mismatch", ["type", "identity", "size", "mode"])
def test_verified_source_rejects_opened_descriptor_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    path = tmp_path / "source.yaml"
    path.write_bytes(b"name: source\n")
    expected = _entry(path, path.name)
    real_fstat = os.fstat

    def changed_fstat(descriptor: int) -> os.stat_result:
        return _changed_stat(real_fstat(descriptor), mismatch)

    monkeypatch.setattr(verified_sources.os, "fstat", changed_fstat)
    with pytest.raises(SDLParseError, match="integrity validation"):
        verified_sources._read_verified_cache_source(
            path,
            expected_entry=expected,
            source_options=DEFAULT_SOURCE_PARSE_OPTIONS,
        )


@pytest.mark.parametrize("mismatch", ["identity", "size", "mode"])
def test_verified_source_rejects_descriptor_change_while_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    path = tmp_path / "source.yaml"
    path.write_bytes(b"name: source\n")
    expected = _entry(path, path.name)
    real_fstat = os.fstat
    calls = 0

    def changed_second_fstat(descriptor: int) -> os.stat_result:
        nonlocal calls
        calls += 1
        metadata = real_fstat(descriptor)
        return metadata if calls == 1 else _changed_stat(metadata, mismatch)

    monkeypatch.setattr(verified_sources.os, "fstat", changed_second_fstat)
    with pytest.raises(SDLParseError, match="integrity validation"):
        verified_sources._read_verified_cache_source(
            path,
            expected_entry=expected,
            source_options=DEFAULT_SOURCE_PARSE_OPTIONS,
        )


def test_verified_source_rejects_io_digest_utf8_and_source_limit_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "source.yaml"
    path.write_bytes(b"name: source\n")
    expected = _entry(path, path.name)
    with pytest.raises(SDLParseError, match="integrity validation"):
        verified_sources._read_verified_cache_source(
            tmp_path / "missing.yaml",
            expected_entry=expected,
            source_options=DEFAULT_SOURCE_PARSE_OPTIONS,
        )

    bad_digest = dict(expected, digest="sha256:" + "0" * 64)
    with pytest.raises(SDLParseError, match="integrity validation"):
        verified_sources._read_verified_cache_source(
            path,
            expected_entry=bad_digest,
            source_options=DEFAULT_SOURCE_PARSE_OPTIONS,
        )

    path.write_bytes(b"\xff")
    invalid_utf8 = _entry(path, path.name)
    with pytest.raises(SDLParseError, match="UTF-8"):
        verified_sources._read_verified_cache_source(
            path,
            expected_entry=invalid_utf8,
            source_options=DEFAULT_SOURCE_PARSE_OPTIONS,
        )

    oversized = b"name: source\n" * 100_000
    path.write_bytes(oversized)
    oversized_entry = _entry(path, path.name)
    limited = SDLSourceParseOptions(limits=SDLParserLimits(max_input_bytes=1))
    with pytest.raises(SDLParseError, match="byte limit"):
        verified_sources._read_verified_cache_source(
            path,
            expected_entry=oversized_entry,
            source_options=limited,
        )

    path.write_bytes(b"name: source\n")
    expected = _entry(path, path.name)

    def fail_fdopen(*_args, **_kwargs):
        raise OSError("sensitive descriptor failure")

    monkeypatch.setattr(verified_sources.os, "fdopen", fail_fdopen)
    with pytest.raises(SDLParseError) as exc_info:
        verified_sources._read_verified_cache_source(
            path,
            expected_entry=expected,
            source_options=DEFAULT_SOURCE_PARSE_OPTIONS,
        )
    assert str(exc_info.value) == "OCI module cache tree failed integrity validation"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"name: root\nimports: {}\n", "structurally invalid"),
        (b"name: root\nimports: [7]\n", "structurally invalid"),
        (
            b"name: root\nimports:\n  - source: local:missing.yaml\n    namespace: missing\n",
            "not found",
        ),
    ],
)
def test_verified_graph_rejects_invalid_or_missing_imports(
    tmp_path: Path,
    payload: bytes,
    message: str,
) -> None:
    root = tmp_path / "module.yaml"
    root.write_bytes(payload)
    with pytest.raises(SDLParseError, match=message):
        verified_sources._read_verified_source_bundle(
            cache_root=tmp_path,
            expected_manifest=_manifest(tmp_path, ["module.yaml"]),
            root_relative=PurePosixPath("module.yaml"),
            source_options=DEFAULT_SOURCE_PARSE_OPTIONS,
        )


def test_legacy_cache_result_remains_a_path(tmp_path: Path) -> None:
    root = tmp_path / "module.yaml"
    assert (
        verified_sources._cache_source_result(
            root,
            expected_manifest={"entries": []},
            root_relative=PurePosixPath("module.yaml"),
            source_options=None,
        )
        == root
    )


def test_verified_expansion_context_has_a_safe_default_trust_policy(tmp_path: Path) -> None:
    root = tmp_path / "module.yaml"
    root.write_text("name: root\n", encoding="utf-8")
    snapshot = verified_sources._read_verified_source_bundle(
        cache_root=tmp_path,
        expected_manifest=_manifest(tmp_path, ["module.yaml"]),
        root_relative=PurePosixPath("module.yaml"),
        source_options=DEFAULT_SOURCE_PARSE_OPTIONS,
    )

    expanded, _provenance = expand_sdl_modules(
        {"name": "root"},
        path=root,
        _verified_sources=snapshot,
    )

    assert expanded["name"] == "root"


def test_ordinary_local_resolution_preserves_missing_and_unsigned_policy_errors(tmp_path: Path) -> None:
    missing = module_registry.ImportDecl(source="local:missing.yaml", namespace="missing")
    with pytest.raises(SDLParseError, match="Imported SDL file not found"):
        module_registry.resolve_import(missing, base_dir=tmp_path)

    (tmp_path / "module.yaml").write_text(
        "name: local\nmodule: {id: acme/local, version: 1.0.0}\n",
        encoding="utf-8",
    )
    local = module_registry.ImportDecl(source="local:module.yaml", namespace="local")
    with pytest.raises(SDLParseError, match="unsigned local sources are not allowed"):
        module_registry.resolve_import(
            local,
            base_dir=tmp_path,
            trust_policy=module_registry.TrustPolicy(allow_unsigned_local_sources=False),
        )


def test_oci_resolution_requires_verified_source_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = "oci:registry.example/acme/module"
    digest = "sha256:" + "0" * 64
    import_decl = module_registry.ImportDecl(source=source, namespace="module")
    monkeypatch.setattr(
        module_registry_resolution,
        "_resolve_oci_manifest",
        lambda **_kwargs: (digest, {}),
    )
    monkeypatch.setattr(
        module_registry_resolution,
        "_resolve_oci_config",
        lambda **_kwargs: (
            {"module": {"id": "acme/module", "version": "1.0.0"}},
            digest,
        ),
    )
    monkeypatch.setattr(module_registry_resolution, "_fetch_oci_bundle", lambda **_kwargs: b"bundle")
    monkeypatch.setattr(module_registry, "_extract_bundle_to_cache", lambda **_kwargs: tmp_path / "module.yaml")

    with pytest.raises(SDLParseError, match="did not return verified source documents"):
        module_registry_resolution._resolve_oci_import(
            import_decl,
            source,
            base_dir=tmp_path,
            lockfile=None,
            trust_policy=module_registry.TrustPolicy(
                registries={"registry.example": module_registry.RegistryTrustPolicy(require_signatures=False)}
            ),
            source_options=DEFAULT_SOURCE_PARSE_OPTIONS,
        )
