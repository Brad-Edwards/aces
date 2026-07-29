"""Lockfile, trust-policy, and OCI-layout names and schema versions."""

from __future__ import annotations

LOCKFILE_NAME = "raes.lock.json"
TRUST_POLICY_NAME = "raes-trust.yaml"
OCI_LAYOUT_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
OCI_CONFIG_MEDIA_TYPE = "application/vnd.raes.module.config.v1+json"
OCI_BUNDLE_MEDIA_TYPE = "application/vnd.raes.module.bundle.v1+tar+gzip"
LOCKFILE_SCHEMA_VERSION = "raes-lock/v1"
TRUST_POLICY_SCHEMA_VERSION = "raes-trust/v1"
OCI_LAYOUT_SCHEMA_VERSION = "raes-module-oci/v1"
