"""Registry-aware SDL composition and packaging tests."""

from __future__ import annotations

import base64
import dataclasses
import io
import json
import shutil
import tarfile
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import raes.module_registry as module_registry
import raes.parser as sdl_parser
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from raes._errors import SDLParseError, SDLValidationError
from raes.module_registry import (
    LOCKFILE_NAME,
    load_lockfile,
    publish_module_to_oci_layout,
)
from raes.parser import parse_sdl_file
from raes_cli.main import app
from raes_processor.compiler import compile_runtime_model
from typer.testing import CliRunner


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
                "    type: compute",
                "    os: linux",
                "    resources: {ram: 1 gib, cpu: 1}",
                "infrastructure:",
                "  vm: 1",
            ]
        ),
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

    assert (
        path_model.node_deployments.keys()
        == source_model.node_deployments.keys()
        == locked_model.node_deployments.keys()
        == {"provision.node.shared.vm"}
    )
    assert path_model.networks.keys() == source_model.networks.keys() == locked_model.networks.keys() == set()
    assert module_path.exists()


def test_local_import_digest_mismatch_fails_closed(tmp_path: Path):
    _local_module(tmp_path / "shared.yaml")
    root = _root_import(
        tmp_path / "root.yaml",
        "source: local:shared.yaml\n            namespace: shared\n            digest: sha256:deadbeef",
    )

    with pytest.raises(SDLParseError, match="Digest mismatch"):
        parse_sdl_file(root)


def test_local_import_composes_the_exact_document_verified_by_resolution(tmp_path: Path, monkeypatch) -> None:
    module_path = _local_module(tmp_path / "shared.yaml")
    root = _root_import(
        tmp_path / "root.yaml",
        "source: local:shared.yaml\n            namespace: shared",
    )
    original_read = sdl_parser.read_sdl_source
    module_reads = 0

    def swap_after_verified_read(path: Path, **kwargs):
        nonlocal module_reads
        document = original_read(path, **kwargs)
        if path.resolve() == module_path.resolve():
            module_reads += 1
            if module_reads == 1:
                module_path.write_bytes(document.raw_bytes.replace(b"os: linux", b"os: windows"))
        return document

    monkeypatch.setattr(sdl_parser, "read_sdl_source", swap_after_verified_read)

    scenario = parse_sdl_file(root)

    assert module_reads == 1
    assert scenario.nodes["shared.vm"].os.value == "linux"


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
            type: compute
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
        entities:
          blue: {role: blue}
        objectives:
          check:
            entity: blue
            success:
              assertions: [shared.health]
        """,
    )

    with pytest.raises(
        SDLValidationError,
        match=r"Objective 'check' references undefined assertion 'shared\.health' in success criteria",
    ):
        parse_sdl_file(root)


@pytest.mark.parametrize("exported", [True, False])
def test_scenario_forwarding_agents_compose_by_stable_list_identity(tmp_path: Path, exported: bool):
    exports = "    forwarding_agents: [shipper]\n" if exported else ""
    _write(
        tmp_path / "shared.yaml",
        f"""
        name: shared
        version: 1.0.0
        module:
          id: raes/shared-forwarder
          version: 1.0.0
          exports:
            nodes: [source, sink]
            relationships: [shipping]
        {exports.rstrip()}
        nodes:
          source: {{type: switch}}
          sink: {{type: switch}}
        forwarding_agents:
          - forwarding_agent_id: shipper
        relationships:
          shipping:
            type: connects_to
            source: source
            target: sink
            forwarding_edge:
              forwarder_ref: shipper
        """,
    )
    root = _root_import(
        tmp_path / "root.yaml",
        "source: local:shared.yaml\n            namespace: shared",
    )

    scenario = parse_sdl_file(root)

    expected = "shared.shipper" if exported else "shared.__private.shipper"
    assert isinstance(scenario.forwarding_agents, list)
    assert [agent.forwarding_agent_id for agent in scenario.forwarding_agents] == [expected]
    assert scenario.relationships["shared.shipping"].forwarding_edge.forwarder_ref == expected


def test_import_cycles_and_namespace_collisions_are_rejected(tmp_path: Path):
    a = _write(
        tmp_path / "a.yaml",
        """
        name: a
        version: 1.0.0
        module:
          id: raes/a
          version: 1.0.0
        imports:
          - source: local:b.yaml
            namespace: other
        """,
    )
    _write(
        tmp_path / "b.yaml",
        """
        name: b
        version: 1.0.0
        module:
          id: raes/b
          version: 1.0.0
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
            type: compute
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

        def read(self, amt: int = -1) -> bytes:
            if amt is None or amt < 0:
                return self._payload
            return self._payload[:amt]

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


@pytest.mark.integration
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
            tmp_path / "raes-trust.yaml",
            f"""
            schema_version: raes-trust/v1
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
        remote_model = compile_runtime_model(parse_sdl_file(root))
        locked_model = compile_runtime_model(parse_sdl_file(locked))

        assert (
            remote_model.node_deployments.keys() == locked_model.node_deployments.keys() == {"provision.node.shared.vm"}
        )


@pytest.mark.integration
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
            tmp_path / "raes-trust.yaml",
            f"""
            schema_version: raes-trust/v1
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
    from raes._module_symbols import symbol_index
    from raes.scenario import ModuleDescriptor, Scenario

    scenario = Scenario(
        name="db-module",
        nodes={
            "db": {
                "type": "compute",
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
                "type": "compute",
                "services": [{"port": 8080, "name": "http"}],
                "runtime": {"applications": [{"application_id": "webapp", "service": "http"}]},
            },
        },
    )
    index = symbol_index(
        scenario,
        namespace="shared",
        descriptor=ModuleDescriptor(id="raes/db-module", version="1.0.0"),
    )
    named = index["named"]
    assert named["nodes.db.runtime.database_services.tv-pg"] == ("nodes.shared.db.runtime.database_services.tv-pg")
    assert named["nodes.db.runtime.database_services.tv-pg.databases.tv-db"] == (
        "nodes.shared.db.runtime.database_services.tv-pg.databases.tv-db"
    )
    assert named["nodes.web.runtime.applications.webapp"] == ("nodes.shared.web.runtime.applications.webapp")


# ---------------------------------------------------------------------------
# Issue #12: bound OCI import fetches (memory/disk exhaustion).
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal urlopen-response double for the bounded reader (issue #12)."""

    def __init__(self, payload: bytes, *, content_length: str | None = None) -> None:
        self._payload = payload
        self.headers = {} if content_length is None else {"Content-Length": content_length}

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb

    def read(self, amt: int = -1) -> bytes:
        if amt is None or amt < 0:
            return self._payload
        return self._payload[:amt]


def _fake_urlopen_returning(response: _FakeResponse):
    def fake_urlopen(request, *, timeout=None):
        del request, timeout
        return response

    return fake_urlopen


def _gzip_tar(members: list[tuple[str, bytes]]) -> io.BytesIO:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, payload in members:
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    buffer.seek(0)
    return buffer


def test_oci_resource_limits_separate_compressed_from_extracted():
    limits = module_registry._OCI_LIMITS
    # Compressed-download and extracted-archive caps are deliberately distinct so a
    # small gzip cannot smuggle a large extraction past the download limit.
    assert limits.max_bundle_bytes > limits.max_metadata_bytes
    assert limits.max_total_bytes >= limits.max_member_bytes


def test_oci_metadata_request_rejects_oversized_response(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        module_registry, "urlopen", _fake_urlopen_returning(_FakeResponse(b'{"tags":["' + b"a" * 64 + b'"]}'))
    )
    with pytest.raises(SDLParseError, match="exceeds"):
        module_registry._json_request("https://registry.example/v2/acme/tags/list", max_bytes=16)


def test_oci_bytes_request_rejects_oversized_response(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(module_registry, "urlopen", _fake_urlopen_returning(_FakeResponse(b"x" * 64)))
    with pytest.raises(SDLParseError, match="exceeds"):
        module_registry._bytes_request("https://registry.example/v2/acme/blobs/sha256:abc", max_bytes=16)


def test_oci_bytes_request_accepts_payload_at_limit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(module_registry, "urlopen", _fake_urlopen_returning(_FakeResponse(b"x" * 16)))
    assert (
        module_registry._bytes_request("https://registry.example/v2/acme/blobs/sha256:abc", max_bytes=16) == b"x" * 16
    )


def test_oci_response_rejects_oversized_content_length(monkeypatch: pytest.MonkeyPatch):
    # A registry cannot force a large buffer by declaring a huge Content-Length: the
    # advisory header is rejected before any bytes are read.
    monkeypatch.setattr(
        module_registry,
        "urlopen",
        _fake_urlopen_returning(_FakeResponse(b"x", content_length="1048576")),
    )
    with pytest.raises(SDLParseError, match="Content-Length"):
        module_registry._bytes_request("https://registry.example/v2/acme/blobs/sha256:abc", max_bytes=16)


def test_oci_response_rejects_invalid_content_length(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        module_registry,
        "urlopen",
        _fake_urlopen_returning(_FakeResponse(b"x", content_length="not-a-number")),
    )
    with pytest.raises(SDLParseError, match="Content-Length"):
        module_registry._bytes_request("https://registry.example/v2/acme/blobs/sha256:abc", max_bytes=16)


def test_oci_bundle_rejects_excess_member_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        module_registry,
        "_OCI_LIMITS",
        dataclasses.replace(module_registry._OCI_LIMITS, max_bundle_members=1),
    )
    buffer = _gzip_tar([("a.yaml", b"a\n"), ("b.yaml", b"b\n")])
    with (
        tarfile.open(fileobj=buffer, mode="r:gz") as tar,
        pytest.raises(SDLParseError, match="archive members"),
    ):
        module_registry._safe_tar_members(tar, tmp_path / "cache")


def test_oci_bundle_rejects_oversized_member(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        module_registry,
        "_OCI_LIMITS",
        dataclasses.replace(module_registry._OCI_LIMITS, max_member_bytes=4),
    )
    buffer = _gzip_tar([("big.yaml", b"x" * 16)])
    with (
        tarfile.open(fileobj=buffer, mode="r:gz") as tar,
        pytest.raises(SDLParseError, match="per-member"),
    ):
        module_registry._safe_tar_members(tar, tmp_path / "cache")


def test_oci_bundle_rejects_excess_total_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        module_registry,
        "_OCI_LIMITS",
        dataclasses.replace(module_registry._OCI_LIMITS, max_member_bytes=100, max_total_bytes=8),
    )
    buffer = _gzip_tar([("a.yaml", b"x" * 6), ("b.yaml", b"y" * 6)])
    with (
        tarfile.open(fileobj=buffer, mode="r:gz") as tar,
        pytest.raises(SDLParseError, match="total extraction"),
    ):
        module_registry._safe_tar_members(tar, tmp_path / "cache")


def test_oci_bundle_rejects_duplicate_member(tmp_path: Path):
    buffer = _gzip_tar([("dup.yaml", b"a\n"), ("dup.yaml", b"b\n")])
    with (
        tarfile.open(fileobj=buffer, mode="r:gz") as tar,
        pytest.raises(SDLParseError, match="Duplicate"),
    ):
        module_registry._safe_tar_members(tar, tmp_path / "cache")


# ---------------------------------------------------------------------------
# Issue #14: config-blob integrity + root_file signature binding.
# ---------------------------------------------------------------------------


def _rewrite_config_field(layout_dir: Path, field: str, value: object) -> None:
    """Rewrite a published OCI layout so the config's ``field`` becomes ``value``.

    Models a compromised registry that keeps the signer's signature intact but
    alters an unsigned config field, then re-derives the config digest, manifest
    digest, and index so every served blob is internally consistent. Fix 1
    (config-digest verification) therefore passes; only a signature that binds
    ``field`` can catch the tamper.
    """
    blobs = layout_dir / "blobs" / "sha256"
    index = json.loads((layout_dir / "index.json").read_text(encoding="utf-8"))
    manifest_digest = index["manifests"][0]["digest"]
    manifest = json.loads((blobs / manifest_digest.removeprefix("sha256:")).read_bytes())
    config_digest = manifest["config"]["digest"]
    config = json.loads((blobs / config_digest.removeprefix("sha256:")).read_bytes())
    config[field] = value
    new_config_bytes = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    new_config_digest = f"sha256:{module_registry._sha256_digest(new_config_bytes)}"
    (blobs / new_config_digest.removeprefix("sha256:")).write_bytes(new_config_bytes)
    manifest["config"]["digest"] = new_config_digest
    manifest["config"]["size"] = len(new_config_bytes)
    new_manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    new_manifest_digest = f"sha256:{module_registry._sha256_digest(new_manifest_bytes)}"
    (blobs / new_manifest_digest.removeprefix("sha256:")).write_bytes(new_manifest_bytes)
    index["manifests"][0]["digest"] = new_manifest_digest
    index["manifests"][0]["size"] = len(new_manifest_bytes)
    (layout_dir / "index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


@pytest.mark.integration
def test_oci_import_rejects_tampered_config_blob(tmp_path: Path):
    """A registry serving config bytes that do not hash to manifest ``config.digest``
    is rejected before the config JSON is trusted (issue #14, fix 1)."""
    module_path = _local_module(tmp_path / "shared.yaml")
    published = publish_module_to_oci_layout(module_path, output_dir=tmp_path / "dist")
    layout_dir = Path(published["layout_dir"])

    # Overwrite the config blob with bytes that no longer match its digest-keyed
    # filename, so the in-process registry serves them under the advertised
    # config.digest (the manifest is left untouched).
    index = json.loads((layout_dir / "index.json").read_text(encoding="utf-8"))
    manifest_digest = index["manifests"][0]["digest"]
    blobs = layout_dir / "blobs" / "sha256"
    manifest = json.loads((blobs / manifest_digest.removeprefix("sha256:")).read_bytes())
    config_blob = blobs / manifest["config"]["digest"].removeprefix("sha256:")
    tampered = json.loads(config_blob.read_bytes())
    tampered["root_file"] = "evil.yaml"
    config_blob.write_bytes(json.dumps(tampered, sort_keys=True, separators=(",", ":")).encode("utf-8"))

    with _OCIRegistry(layout_dir, repo="acme/shared") as registry:
        _write(
            tmp_path / "raes-trust.yaml",
            f"""
            schema_version: raes-trust/v1
            registries:
              "127.0.0.1:{registry.port}":
                require_signatures: false
                allow_insecure_http: true
            """,
        )
        root = _root_import(
            tmp_path / "root-oci.yaml",
            f"source: oci:127.0.0.1:{registry.port}/acme/shared\n            namespace: shared\n            version: 1.2.3",
        )
        with pytest.raises(SDLParseError, match="config digest verification failed"):
            parse_sdl_file(root)


@pytest.mark.integration
def test_oci_import_rejects_root_file_tampering(tmp_path: Path):
    """A compromised registry cannot repoint ``root_file`` inside an otherwise-signed
    bundle: ``root_file`` is bound into the signature payload, so altering it while
    keeping the original signature fails verification (issue #14, fix 2)."""
    module_path = _local_module(tmp_path / "shared.yaml")
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
    published = publish_module_to_oci_layout(
        module_path,
        output_dir=tmp_path / "dist",
        signer_id="test-signer",
        private_key_path=private_key_path,
    )
    layout_dir = Path(published["layout_dir"])
    # Keep the signature intact; only repoint the entrypoint.
    _rewrite_config_field(layout_dir, "root_file", "smuggled.yaml")

    with _OCIRegistry(layout_dir, repo="acme/shared") as registry:
        _write(
            tmp_path / "raes-trust.yaml",
            f"""
            schema_version: raes-trust/v1
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
            f"source: oci:127.0.0.1:{registry.port}/acme/shared\n            namespace: shared\n            version: 1.2.3",
        )
        with pytest.raises(SDLParseError, match="No valid trusted signer signature found"):
            parse_sdl_file(root)


@pytest.mark.integration
def test_oci_import_rejects_non_string_root_file(tmp_path: Path):
    """A config declaring a non-string ``root_file`` fails closed with SDLParseError
    rather than flowing a bad type into the signature payload / extraction and
    surfacing a confusing downstream TypeError (issue #14)."""
    module_path = _local_module(tmp_path / "shared.yaml")
    published = publish_module_to_oci_layout(module_path, output_dir=tmp_path / "dist")
    layout_dir = Path(published["layout_dir"])
    # Re-derive the digests so Fix 1 (config-digest verification) passes and the
    # root_file type check is what rejects the module.
    _rewrite_config_field(layout_dir, "root_file", ["evil.yaml"])

    with _OCIRegistry(layout_dir, repo="acme/shared") as registry:
        _write(
            tmp_path / "raes-trust.yaml",
            f"""
            schema_version: raes-trust/v1
            registries:
              "127.0.0.1:{registry.port}":
                require_signatures: false
                allow_insecure_http: true
            """,
        )
        root = _root_import(
            tmp_path / "root-oci.yaml",
            f"source: oci:127.0.0.1:{registry.port}/acme/shared\n            namespace: shared\n            version: 1.2.3",
        )
        with pytest.raises(SDLParseError, match="non-string root_file"):
            parse_sdl_file(root)


def test_oci_signature_over_legacy_payload_without_root_file_is_rejected():
    """A signature computed over the pre-#14 payload (which omitted ``root_file``)
    fails closed under ``require_signatures`` — no compatibility fallback."""
    descriptor = module_registry.ModuleDescriptor(id="acme/shared", version="1.2.3", exports={"nodes": ["vm"]})
    content_digest = "sha256:" + "0" * 64
    legacy_payload = json.dumps(
        {
            "module_id": descriptor.id,
            "module_version": descriptor.version,
            "exports": descriptor.exports,
            "content_digest": content_digest,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    signature = base64.b64encode(private_key.sign(legacy_payload)).decode("utf-8")
    policy = module_registry.RegistryTrustPolicy(
        require_signatures=True,
        trusted_signers={"test-signer": base64.b64encode(public_key).decode("utf-8")},
    )
    with pytest.raises(SDLParseError, match="No valid trusted signer signature found"):
        module_registry._verify_signatures(
            signatures=[{"signer_id": "test-signer", "signature": signature}],
            trust_policy=policy,
            module_descriptor=descriptor,
            content_digest=content_digest,
            root_file="module.yaml",
        )


def test_oci_signature_binds_root_file():
    """The canonical signing payload includes ``root_file`` so a differing
    ``root_file`` produces a different signable payload (issue #14, fix 2)."""
    descriptor = module_registry.ModuleDescriptor(id="acme/shared", version="1.2.3", exports={"nodes": ["vm"]})
    content_digest = "sha256:" + "0" * 64
    payload_a = module_registry._signable_payload(descriptor, content_digest=content_digest, root_file="module.yaml")
    payload_b = module_registry._signable_payload(descriptor, content_digest=content_digest, root_file="other.yaml")
    assert payload_a != payload_b
    assert b"root_file" in payload_a
