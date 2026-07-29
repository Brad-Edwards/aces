"""OCI-layout publishing for local SDL module graphs."""

from __future__ import annotations

import base64
import io
import json
import tarfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .._errors import SDLParseError
from ..scenario import ImportDecl
from ._constants import (
    OCI_BUNDLE_MEDIA_TYPE,
    OCI_CONFIG_MEDIA_TYPE,
    OCI_LAYOUT_MEDIA_TYPE,
    OCI_LAYOUT_SCHEMA_VERSION,
)
from ._digests import _descriptor_digest
from .models import _scenario_module_descriptor


def _collect_local_bundle_files(
    root_path: Path,
    *,
    seen: set[Path] | None = None,
) -> dict[Path, bytes]:
    from ..parser import _load_normalized_data, read_sdl_source

    seen = set() if seen is None else set(seen)
    resolved = root_path.resolve()
    if resolved in seen:
        raise SDLParseError(f"Import cycle detected at {resolved}")
    seen.add(resolved)
    root_source = read_sdl_source(root_path)
    payload = _load_normalized_data(root_source.text, path=root_path)
    files = {resolved: root_source.raw_bytes}
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
    from ..parser import parse_sdl_file

    # Resolve the private digest/signature seams through the package facade so a
    # test that patches raes.module_registry._sha256_digest / _signable_payload
    # replaces the binding these production calls use, exactly as the pre-split
    # single-file module did.
    from . import _sha256_digest, _signable_payload

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
            "io.raes.module.id": descriptor.id,
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
                            "io.raes.module.id": descriptor.id,
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
