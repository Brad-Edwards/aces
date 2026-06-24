"""Registry-aware SDL composition and packaging tests."""

from __future__ import annotations

import base64
import io
import json
import shutil
import tarfile
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import aces_sdl.module_registry as module_registry
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from typer.testing import CliRunner

from aces.cli.main import app
from aces.core.runtime.compiler import compile_runtime_model
from aces.core.sdl._errors import SDLParseError, SDLValidationError
from aces.core.sdl.module_registry import (
    LOCKFILE_NAME,
    load_lockfile,
    publish_module_to_oci_layout,
)
from aces.core.sdl.parser import parse_sdl_file


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return path


def _local_module(path: Path, *, version: str = "1.2.3", exports: str = "nodes: [vm]\ninfrastructure: [vm]") -> Path:
    exports_block = "\n".join(f"    {line}" for line in textwrap.dedent(exports).strip().splitlines())
    return _write(
        path,
        "\n".join(
            [
                "name: shared",
                f"version: {version}",
                "module:",
                "  id: acme/shared",
                f"  version: {version}",
                "  exports:",
                exports_block,
                "nodes:",
                "  vm:",
                "    type: vm",
                "    os: linux",
                "    resources: {ram: 1 gib, cpu: 1}",
                "infrastructure:",
                "  vm: 1",
            ]
        ),
    )


def _flat_equivalent(path: Path) -> Path:
    return _write(
        path,
        """
        name: flat
        nodes:
          shared.vm:
            type: vm
            os: linux
            resources: {ram: 1 gib, cpu: 1}
        infrastructure:
          shared.vm: 1
        """,
    )


def _root_import(path: Path, import_body: str) -> Path:
    lines = textwrap.dedent(import_body).strip().splitlines()
    import_lines = [f"  - {lines[0].strip()}"]
    import_lines.extend(f"    {line.strip()}" for line in lines[1:])
    import_block = "\n".join(import_lines)
    return _write(
        path,
        "\n".join(
            [
                "name: root",
                "imports:",
                import_block,
            ]
        ),
    )


class _OCIHandler(BaseHTTPRequestHandler):
    repo = ""
    tag = ""
    manifest_digest = ""
    manifest_bytes = b""
    blobs: dict[str, bytes] = {}

    def do_GET(self) -> None:  # noqa: N802
        if self.path == f"/v2/{self.repo}/tags/list":
            payload = json.dumps({"name": self.repo, "tags": [self.tag]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path in {
            f"/v2/{self.repo}/manifests/{self.tag}",
            f"/v2/{self.repo}/manifests/{self.manifest_digest}",
        }:
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.oci.image.manifest.v1+json")
            self.send_header("Content-Length", str(len(self.manifest_bytes)))
            self.end_headers()
            self.wfile.write(self.manifest_bytes)
            return
        blob_prefix = f"/v2/{self.repo}/blobs/"
        if self.path.startswith(blob_prefix):
            digest = self.path.removeprefix(blob_prefix)
            blob = self.blobs.get(digest)
            if blob is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)
            return
        self.send_error(404)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        del format, args


class _OCIRegistry:
    def __init__(self, layout_dir: Path, repo: str) -> None:
        index_payload = json.loads((layout_dir / "index.json").read_text(encoding="utf-8"))
        manifest_digest = index_payload["manifests"][0]["digest"]
        tag = index_payload["manifests"][0]["annotations"]["org.opencontainers.image.ref.name"]
        manifest_bytes = (layout_dir / "blobs" / "sha256" / manifest_digest.removeprefix("sha256:")).read_bytes()
        blobs = {f"sha256:{blob.name}": blob.read_bytes() for blob in (layout_dir / "blobs" / "sha256").iterdir()}
        handler = type(
            "Handler",
            (_OCIHandler,),
            {
                "repo": repo,
                "tag": tag,
                "manifest_digest": manifest_digest,
                "manifest_bytes": manifest_bytes,
                "blobs": blobs,
            },
        )
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.host, self.port = self._server.server_address
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> _OCIRegistry:
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


def test_local_path_source_and_locked_imports_compile_equivalently(tmp_path: Path):
    module_path = _local_module(tmp_path / "shared.yaml")
    root_path = _root_import(
        tmp_path / "root-path.yaml",
        "path: shared.yaml\n            namespace: shared",
    )
    root_source = _root_import(
        tmp_path / "root-source.yaml",
        "source: local:shared.yaml\n            namespace: shared\n            version: 1.2.3",
    )
    flat = _flat_equivalent(tmp_path / "flat.yaml")

    runner = CliRunner()
    resolve_result = runner.invoke(app, ["sdl", "resolve", str(root_source)])
    assert resolve_result.exit_code == 0, resolve_result.output
    lockfile = load_lockfile(tmp_path)
    assert lockfile is not None
    record = lockfile.imports[0]

    root_locked = _root_import(
        tmp_path / "root-locked.yaml",
        f"source: locked:{record.resolved_source}\n            namespace: shared",
    )

    path_model = compile_runtime_model(parse_sdl_file(root_path))
    source_model = compile_runtime_model(parse_sdl_file(root_source))
    locked_model = compile_runtime_model(parse_sdl_file(root_locked))
    flat_model = compile_runtime_model(parse_sdl_file(flat))

    assert (
        path_model.node_deployments.keys()
        == source_model.node_deployments.keys()
        == locked_model.node_deployments.keys()
        == flat_model.node_deployments.keys()
    )
    assert (
        path_model.networks.keys()
        == source_model.networks.keys()
        == locked_model.networks.keys()
        == flat_model.networks.keys()
    )
    assert module_path.exists()


def test_local_import_digest_mismatch_fails_closed(tmp_path: Path):
    _local_module(tmp_path / "shared.yaml")
    root = _root_import(
        tmp_path / "root.yaml",
        "source: local:shared.yaml\n            namespace: shared\n            digest: sha256:deadbeef",
    )

    with pytest.raises(SDLParseError, match="Digest mismatch"):
        parse_sdl_file(root)


def test_module_exports_are_enforced_for_importers(tmp_path: Path):
    _write(
        tmp_path / "shared.yaml",
        """
        name: shared
        version: 1.2.3
        module:
          id: acme/shared
          version: 1.2.3
          exports:
            nodes: [vm]
            infrastructure: [vm]
        nodes:
          vm:
            type: vm
            os: linux
            resources: {ram: 1 gib, cpu: 1}
            conditions: {health: ops}
            roles: {ops: operator}
        infrastructure:
          vm: 1
        conditions:
          health: {command: /bin/true, interval: 15}
        """,
    )
    root = _write(
        tmp_path / "root.yaml",
        """
        name: root
        imports:
          - source: local:shared.yaml
            namespace: shared
        metrics:
          uptime:
            type: conditional
            condition: shared.health
            max-score: 100
        """,
    )

    with pytest.raises(SDLValidationError, match=r"Metric 'uptime' references undefined condition 'shared\.health'"):
        parse_sdl_file(root)


def test_import_cycles_and_namespace_collisions_are_rejected(tmp_path: Path):
    a = _write(
        tmp_path / "a.yaml",
        """
        name: a
        imports:
          - source: local:b.yaml
            namespace: other
        """,
    )
    _write(
        tmp_path / "b.yaml",
        """
        name: b
        imports:
          - source: local:a.yaml
            namespace: other
        """,
    )
    with pytest.raises(SDLParseError, match="Import cycle detected"):
        parse_sdl_file(a)

    _local_module(tmp_path / "one.yaml")
    _local_module(tmp_path / "two.yaml")
    root = _write(
        tmp_path / "collision.yaml",
        """
        name: collision
        imports:
          - source: local:one.yaml
            namespace: shared
          - source: local:two.yaml
            namespace: shared
        """,
    )
    with pytest.raises(SDLParseError, match="collides on nodes"):
        parse_sdl_file(root)


def test_sdl_resolve_and_verify_detect_lockfile_drift(tmp_path: Path):
    _local_module(tmp_path / "shared.yaml")
    root = _root_import(
        tmp_path / "root.yaml",
        "source: local:shared.yaml\n            namespace: shared",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["sdl", "resolve", str(root)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / LOCKFILE_NAME).exists()

    verify = runner.invoke(app, ["sdl", "verify-imports", str(root)])
    assert verify.exit_code == 0, verify.output

    _local_module(tmp_path / "shared.yaml", version="1.2.4")
    stale = runner.invoke(app, ["sdl", "verify-imports", str(root)])
    assert stale.exit_code != 0
    assert "stale" in stale.output.lower()


def test_local_import_lockfile_is_checkout_independent(tmp_path: Path):
    # Author the scenario under one absolute checkout path, with the imported
    # module in a subdirectory so the persisted identity is a multi-segment
    # relative path rather than a bare filename.
    checkout_a = tmp_path / "checkout_a"
    _local_module(checkout_a / "nodes" / "shared.yaml")
    root_a = _root_import(
        checkout_a / "root.yaml",
        "source: local:nodes/shared.yaml\n            namespace: shared",
    )
    runner = CliRunner()

    resolve_result = runner.invoke(app, ["sdl", "resolve", str(root_a)])
    assert resolve_result.exit_code == 0, resolve_result.output

    # Acceptance: `resolve` writes no absolute machine paths for local: imports.
    lock_text = (checkout_a / LOCKFILE_NAME).read_text(encoding="utf-8")
    assert str(checkout_a) not in lock_text
    lockfile = load_lockfile(checkout_a)
    assert lockfile is not None
    record = lockfile.imports[0]
    assert not Path(record.resolved_source).is_absolute()
    assert record.resolved_source == "nodes/shared.yaml"

    # Acceptance: `verify-imports` passes on a checkout at a different absolute
    # path than the one that generated the lock.
    checkout_b = tmp_path / "checkout_b"
    shutil.copytree(checkout_a, checkout_b)
    verify = runner.invoke(app, ["sdl", "verify-imports", str(checkout_b / "root.yaml")])
    assert verify.exit_code == 0, verify.output

    # ...and still fails when the imported content actually changes.
    _local_module(checkout_b / "nodes" / "shared.yaml", version="1.2.4")
    stale = runner.invoke(app, ["sdl", "verify-imports", str(checkout_b / "root.yaml")])
    assert stale.exit_code != 0
    assert "stale" in stale.output.lower()


def test_local_imports_cannot_escape_base_dir(tmp_path: Path):
    _local_module(tmp_path / "shared.yaml")
    root = _root_import(
        tmp_path / "scenario" / "root.yaml",
        "source: local:../shared.yaml\n            namespace: shared",
    )

    with pytest.raises(SDLParseError, match="escapes base directory"):
        parse_sdl_file(root)


def test_publishing_local_bundle_rejects_import_escape(tmp_path: Path):
    _local_module(tmp_path / "shared.yaml")
    root = _write(
        tmp_path / "scenario" / "root.yaml",
        """
        name: root
        version: 1.0.0
        module:
          id: acme/root
          version: 1.0.0
          exports:
            nodes: [vm]
            infrastructure: [vm]
        imports:
          - source: local:../shared.yaml
            namespace: shared
        nodes:
          vm:
            type: vm
            os: linux
            resources: {ram: 1 gib, cpu: 1}
        infrastructure:
          vm: 1
        """,
    )

    with pytest.raises(SDLParseError, match="escapes base directory"):
        publish_module_to_oci_layout(root, output_dir=tmp_path / "dist")


def test_oci_registry_requests_use_bounded_timeouts(monkeypatch: pytest.MonkeyPatch):
    responses = [b'{"ok": true}', b"bundle-bytes"]
    timeouts: list[float | None] = []

    class _Response:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        def read(self) -> bytes:
            return self._payload

    def fake_urlopen(request, *, timeout=None):
        del request
        timeouts.append(timeout)
        return _Response(responses.pop(0))

    monkeypatch.setattr(module_registry, "urlopen", fake_urlopen)

    assert module_registry._json_request("https://registry.example/v2/acme/tags/list") == {"ok": True}
    assert module_registry._bytes_request("https://registry.example/v2/acme/blobs/sha256:abc") == b"bundle-bytes"
    assert timeouts == [module_registry._HTTP_TIMEOUT_SECONDS, module_registry._HTTP_TIMEOUT_SECONDS]


def test_oci_bundle_rejects_root_file_escape(tmp_path: Path):
    with pytest.raises(SDLParseError, match="Invalid OCI root_file path"):
        module_registry._extract_bundle_to_cache(
            bundle_bytes=b"",
            manifest_digest="abc123",
            root_file="../module.yaml",
            base_dir=tmp_path,
        )


def test_oci_bundle_rejects_unsafe_tar_members(tmp_path: Path):
    bundle_buffer = io.BytesIO()
    with tarfile.open(fileobj=bundle_buffer, mode="w:gz") as tar:
        payload = b"name: unsafe\n"
        member = tarfile.TarInfo(name="../escape.yaml")
        member.size = len(payload)
        tar.addfile(member, io.BytesIO(payload))
    bundle_buffer.seek(0)

    with (
        tarfile.open(fileobj=bundle_buffer, mode="r:gz") as tar,
        pytest.raises(SDLParseError, match="Path traversal detected"),
    ):
        module_registry._safe_tar_members(tar, tmp_path / "cache")


def test_oci_bundle_rejects_special_member_types(tmp_path: Path):
    bundle_buffer = io.BytesIO()
    with tarfile.open(fileobj=bundle_buffer, mode="w:gz") as tar:
        fifo = tarfile.TarInfo(name="pipe")
        fifo.type = tarfile.FIFOTYPE
        tar.addfile(fifo)
    bundle_buffer.seek(0)

    with (
        tarfile.open(fileobj=bundle_buffer, mode="r:gz") as tar,
        pytest.raises(SDLParseError, match="Unsupported tar member"),
    ):
        module_registry._safe_tar_members(tar, tmp_path / "cache")


def test_oci_bundle_rejects_symlink_members(tmp_path: Path):
    # A symlink whose own name passes the traversal check (e.g. name='module.yaml')
    # but whose linkname escapes the cache is a distinct attack vector and must be
    # rejected before extraction.
    bundle_buffer = io.BytesIO()
    with tarfile.open(fileobj=bundle_buffer, mode="w:gz") as tar:
        member = tarfile.TarInfo(name="module.yaml")
        member.type = tarfile.SYMTYPE
        member.linkname = "../outside.yaml"
        tar.addfile(member)
    bundle_buffer.seek(0)

    with (
        tarfile.open(fileobj=bundle_buffer, mode="r:gz") as tar,
        pytest.raises(SDLParseError, match="Links are not allowed"),
    ):
        module_registry._safe_tar_members(tar, tmp_path / "cache")


def test_oci_bundle_rejects_hardlink_members(tmp_path: Path):
    bundle_buffer = io.BytesIO()
    with tarfile.open(fileobj=bundle_buffer, mode="w:gz") as tar:
        target = tarfile.TarInfo(name="module.yaml")
        target.size = 0
        tar.addfile(target, io.BytesIO(b""))
        link = tarfile.TarInfo(name="link.yaml")
        link.type = tarfile.LNKTYPE
        link.linkname = "module.yaml"
        tar.addfile(link)
    bundle_buffer.seek(0)

    with (
        tarfile.open(fileobj=bundle_buffer, mode="r:gz") as tar,
        pytest.raises(SDLParseError, match="Links are not allowed"),
    ):
        module_registry._safe_tar_members(tar, tmp_path / "cache")


def test_oci_bundle_strips_dangerous_mode_bits(tmp_path: Path):
    payload = b"name: m\n"
    bundle_buffer = io.BytesIO()
    with tarfile.open(fileobj=bundle_buffer, mode="w:gz") as tar:
        member = tarfile.TarInfo(name="module.yaml")
        member.size = len(payload)
        member.mode = 0o4755  # setuid bit set by an attacker-controlled bundle
        tar.addfile(member, io.BytesIO(payload))
    bundle_buffer.seek(0)

    with tarfile.open(fileobj=bundle_buffer, mode="r:gz") as tar:
        safe = module_registry._safe_tar_members(tar, tmp_path / "cache")

    assert safe[0].mode & 0o7000 == 0
    assert safe[0].mode == 0o755


def test_oci_bundle_extracts_safe_members(tmp_path: Path):
    payload = b"name: ok\n"
    bundle_buffer = io.BytesIO()
    with tarfile.open(fileobj=bundle_buffer, mode="w:gz") as tar:
        member = tarfile.TarInfo(name="module.yaml")
        member.size = len(payload)
        tar.addfile(member, io.BytesIO(payload))
    bundle_buffer.seek(0)

    root_path = module_registry._extract_bundle_to_cache(
        bundle_bytes=bundle_buffer.getvalue(),
        manifest_digest="deadbeef",
        root_file="module.yaml",
        base_dir=tmp_path,
    )

    assert root_path.is_file()
    assert root_path.read_bytes() == payload
    cache = module_registry._oci_cache_dir(tmp_path) / "deadbeef"
    assert root_path.resolve().is_relative_to(cache.resolve())


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_oci_bundle_fallback_extraction_validates_members(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Simulate Python 3.11.0–3.11.3, where TarFile.extractall lacks the PEP 706
    # `filter` keyword (backported in 3.11.4). The fallback path must still extract
    # only validated members rather than performing an unfiltered extraction.
    real_extractall = tarfile.TarFile.extractall

    def no_filter_extractall(self, path=None, members=None, **kwargs):
        if "filter" in kwargs:
            raise TypeError("extractall() got an unexpected keyword argument 'filter'")
        return real_extractall(self, path, members=members)

    monkeypatch.setattr(tarfile.TarFile, "extractall", no_filter_extractall)

    payload = b"name: ok\n"
    bundle_buffer = io.BytesIO()
    with tarfile.open(fileobj=bundle_buffer, mode="w:gz") as tar:
        member = tarfile.TarInfo(name="module.yaml")
        member.size = len(payload)
        tar.addfile(member, io.BytesIO(payload))
    bundle_buffer.seek(0)

    root_path = module_registry._extract_bundle_to_cache(
        bundle_bytes=bundle_buffer.getvalue(),
        manifest_digest="cafef00d",
        root_file="module.yaml",
        base_dir=tmp_path,
    )

    assert root_path.is_file()
    assert root_path.read_bytes() == payload


def test_oci_bundle_fallback_rejects_traversal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # The fallback path used on Python 3.11.0–3.11.3 must still reject traversal.
    real_extractall = tarfile.TarFile.extractall

    def no_filter_extractall(self, path=None, members=None, **kwargs):
        if "filter" in kwargs:
            raise TypeError("extractall() got an unexpected keyword argument 'filter'")
        return real_extractall(self, path, members=members)

    monkeypatch.setattr(tarfile.TarFile, "extractall", no_filter_extractall)

    payload = b"owned\n"
    bundle_buffer = io.BytesIO()
    with tarfile.open(fileobj=bundle_buffer, mode="w:gz") as tar:
        member = tarfile.TarInfo(name="../escape.yaml")
        member.size = len(payload)
        tar.addfile(member, io.BytesIO(payload))
    bundle_buffer.seek(0)

    with pytest.raises(SDLParseError, match="Path traversal detected"):
        module_registry._extract_bundle_to_cache(
            bundle_bytes=bundle_buffer.getvalue(),
            manifest_digest="badbad",
            root_file="module.yaml",
            base_dir=tmp_path,
        )
    assert not (tmp_path / "escape.yaml").exists()


def test_oci_bundle_rejects_root_file_directory(tmp_path: Path):
    bundle_buffer = io.BytesIO()
    with tarfile.open(fileobj=bundle_buffer, mode="w:gz") as tar:
        directory = tarfile.TarInfo(name="module.yaml")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        tar.addfile(directory)
    bundle_buffer.seek(0)

    with pytest.raises(SDLParseError, match="root file"):
        module_registry._extract_bundle_to_cache(
            bundle_bytes=bundle_buffer.getvalue(),
            manifest_digest="d1rd1r",
            root_file="module.yaml",
            base_dir=tmp_path,
        )


def test_oci_bundle_cache_hit_enforces_root_file_containment(tmp_path: Path):
    # Simulate a cache populated by an earlier unsafe extractor: a symlink at the
    # root_file location resolving outside the digest cache. The cache-hit fast path
    # must still fail closed rather than returning the escaping path.
    cache_root = module_registry._oci_cache_dir(tmp_path) / "stale"
    cache_root.mkdir(parents=True)
    outside = tmp_path / "outside.yaml"
    outside.write_text("name: evil\n", encoding="utf-8")
    (cache_root / "module.yaml").symlink_to(outside)

    with pytest.raises(SDLParseError, match="root file"):
        module_registry._extract_bundle_to_cache(
            bundle_bytes=b"",
            manifest_digest="stale",
            root_file="module.yaml",
            base_dir=tmp_path,
        )


def test_signed_oci_import_resolution_and_publish_cli(tmp_path: Path):
    module_path = _local_module(tmp_path / "shared.yaml")
    runner = CliRunner()

    private_key = Ed25519PrivateKey.generate()
    private_key_path = tmp_path / "signing-key.pem"
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    publish = runner.invoke(
        app,
        [
            "sdl",
            "publish",
            str(module_path),
            "--output-dir",
            str(tmp_path / "dist"),
            "--signer-id",
            "test-signer",
            "--private-key",
            str(private_key_path),
        ],
    )
    assert publish.exit_code == 0, publish.output
    publish_payload = json.loads(publish.stdout)
    layout_dir = Path(publish_payload["layout_dir"])

    with _OCIRegistry(layout_dir, repo="acme/shared") as registry:
        _write(
            tmp_path / "aces-trust.yaml",
            f"""
            schema_version: aces-trust/v1
            registries:
              "127.0.0.1:{registry.port}":
                require_signatures: true
                allow_insecure_http: true
                trusted_signers:
                  test-signer: "{base64.b64encode(public_key).decode("utf-8")}"
            """,
        )
        root = _root_import(
            tmp_path / "root-oci.yaml",
            f"source: oci:127.0.0.1:{registry.port}/acme/shared\n            namespace: shared\n            version: '>=1.0,<2.0'",
        )
        resolve = runner.invoke(app, ["sdl", "resolve", str(root)])
        assert resolve.exit_code == 0, resolve.output

        lockfile = load_lockfile(tmp_path)
        assert lockfile is not None
        assert lockfile.imports[0].module_version == "1.2.3"

        locked = _root_import(
            tmp_path / "root-locked.yaml",
            f"source: locked:{lockfile.imports[0].resolved_source}\n            namespace: shared",
        )
        flat = _flat_equivalent(tmp_path / "flat.yaml")
        remote_model = compile_runtime_model(parse_sdl_file(root))
        locked_model = compile_runtime_model(parse_sdl_file(locked))
        flat_model = compile_runtime_model(parse_sdl_file(flat))

        assert (
            remote_model.node_deployments.keys()
            == locked_model.node_deployments.keys()
            == flat_model.node_deployments.keys()
        )


def test_untrusted_and_unsigned_oci_imports_fail_closed(tmp_path: Path):
    module_path = _local_module(tmp_path / "shared.yaml")
    unsigned = publish_module_to_oci_layout(module_path, output_dir=tmp_path / "dist")
    layout_dir = Path(unsigned["layout_dir"])

    with _OCIRegistry(layout_dir, repo="acme/shared") as registry:
        root = _root_import(
            tmp_path / "root-oci.yaml",
            f"source: oci:127.0.0.1:{registry.port}/acme/shared\n            namespace: shared\n            version: 1.2.3",
        )
        with pytest.raises(SDLParseError, match="not allowed by trust policy"):
            parse_sdl_file(root)

        _write(
            tmp_path / "aces-trust.yaml",
            f"""
            schema_version: aces-trust/v1
            registries:
              "127.0.0.1:{registry.port}":
                require_signatures: true
                allow_insecure_http: true
                trusted_signers: {{}}
            """,
        )
        with pytest.raises(SDLParseError, match="No valid trusted signer signature found"):
            parse_sdl_file(root)


def test_database_and_application_refs_survive_module_namespacing():
    """Qualified runtime DB/application refs are rewritten when namespaced.

    ADR-027 §2: refs published into the named-reference index must also be
    rewritten by module composition so an application-to-database relationship
    survives being imported under a namespace.
    """
    from aces_sdl._module_symbols import symbol_index

    from aces.core.sdl.scenario import ModuleDescriptor, Scenario

    scenario = Scenario(
        name="db-module",
        nodes={
            "db": {
                "type": "vm",
                "services": [{"port": 5432, "name": "pg"}],
                "runtime": {
                    "database_services": [
                        {
                            "database_service_id": "tv-pg",
                            "service": "pg",
                            "engine": "postgresql",
                            "protocol": "postgresql",
                            "databases": [{"database_id": "tv-db", "name": "techvault"}],
                        }
                    ]
                },
            },
            "web": {
                "type": "vm",
                "services": [{"port": 8080, "name": "http"}],
                "runtime": {"applications": [{"application_id": "webapp", "service": "http"}]},
            },
        },
    )
    index = symbol_index(
        scenario,
        namespace="shared",
        descriptor=ModuleDescriptor(id="aces/db-module", version="1.0.0"),
    )
    named = index["named"]
    assert named["nodes.db.runtime.database_services.tv-pg"] == ("nodes.shared.db.runtime.database_services.tv-pg")
    assert named["nodes.db.runtime.database_services.tv-pg.databases.tv-db"] == (
        "nodes.shared.db.runtime.database_services.tv-pg.databases.tv-db"
    )
    assert named["nodes.web.runtime.applications.webapp"] == ("nodes.shared.web.runtime.applications.webapp")
