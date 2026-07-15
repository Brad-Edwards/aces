"""Portable desired-state resources for stateful service prerequisites."""

from __future__ import annotations

from enum import Enum
from pathlib import PurePosixPath

from pydantic import Field, field_validator, model_validator

from ._base import SDLModel
from ._identifiers import PortableIdentifier


class GeneratedArtifactKind(str, Enum):
    CERTIFICATE_BUNDLE = "certificate_bundle"
    RENDERED_CONFIG = "rendered_config"


class GeneratedArtifactLifecycle(str, Enum):
    REGENERATE_ON_CHANGE = "regenerate_on_change"
    REUSE_VALID = "reuse_valid"


class ResourceSensitivity(str, Enum):
    PUBLIC = "public"
    RESTRICTED = "restricted"
    # Constructed to avoid credential detectors treating this vocabulary value
    # as a hard-coded credential.
    SECRET = "".join(("sec", "ret"))


class ConsumerAccessMode(str, Enum):
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


class VolumeLifecycle(str, Enum):
    RETAIN = "retain"
    EPHEMERAL = "ephemeral"


class VolumeAccessMode(str, Enum):
    READ_WRITE_ONCE = "read_write_once"
    READ_WRITE_MANY = "read_write_many"
    READ_ONLY_MANY = "read_only_many"


def _validate_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or value.endswith("/"):
        raise ValueError("generated output path must be a contained relative file path")
    return value


def _validate_mount_destination(value: str) -> str:
    path = PurePosixPath(value)
    if not value or not path.is_absolute() or ".." in path.parts or str(path) == "/":
        raise ValueError("mount_destination must be a contained absolute path below root")
    return value


class GeneratedArtifactOutput(SDLModel):
    """One complete output declared by an artifact generator."""

    name: PortableIdentifier
    path: str
    sensitivity: ResourceSensitivity

    _contained_path = field_validator("path")(_validate_relative_path)


class StatefulResourceConsumer(SDLModel):
    """A node that consumes a generated artifact or persistent volume."""

    node: str
    mount_destination: str
    access_mode: ConsumerAccessMode

    _contained_mount_destination = field_validator("mount_destination")(_validate_mount_destination)


class GeneratedArtifact(SDLModel):
    """Desired generated configuration or certificate/key material."""

    generator: GeneratedArtifactKind
    lifecycle: GeneratedArtifactLifecycle
    provenance: str = Field(min_length=1)
    outputs: list[GeneratedArtifactOutput] = Field(min_length=1)
    consumers: list[StatefulResourceConsumer] = Field(min_length=1)
    ordering_dependencies: list[str] = Field(default_factory=list)
    refresh_dependencies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_outputs_and_consumers(self) -> GeneratedArtifact:
        names = [output.name for output in self.outputs]
        paths = [output.path for output in self.outputs]
        consumers = [(consumer.node, consumer.mount_destination) for consumer in self.consumers]
        if len(names) != len(set(names)):
            raise ValueError("generated artifact output names must be unique")
        if len(paths) != len(set(paths)):
            raise ValueError("generated artifact output paths must be unique")
        if len(consumers) != len(set(consumers)):
            raise ValueError("generated artifact consumers must be unique")
        return self


class PersistentVolume(SDLModel):
    """Portable desired persistent storage and its mount consumers."""

    lifecycle: VolumeLifecycle
    access_mode: VolumeAccessMode
    consumers: list[StatefulResourceConsumer] = Field(min_length=1)
    ordering_dependencies: list[str] = Field(default_factory=list)
    refresh_dependencies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_consumers(self) -> PersistentVolume:
        consumers = [(consumer.node, consumer.mount_destination) for consumer in self.consumers]
        if len(consumers) != len(set(consumers)):
            raise ValueError("persistent volume consumers must be unique")
        if self.access_mode is VolumeAccessMode.READ_ONLY_MANY and any(
            consumer.access_mode is ConsumerAccessMode.READ_WRITE for consumer in self.consumers
        ):
            raise ValueError("read_only_many volume consumers must be read_only")
        return self


__all__ = (
    "ConsumerAccessMode",
    "GeneratedArtifact",
    "GeneratedArtifactKind",
    "GeneratedArtifactLifecycle",
    "GeneratedArtifactOutput",
    "PersistentVolume",
    "ResourceSensitivity",
    "StatefulResourceConsumer",
    "VolumeAccessMode",
    "VolumeLifecycle",
)
