"""Typed-model traversal for reference source paths and owner links."""

from __future__ import annotations

import types
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Annotated, Union, get_args, get_origin

from pydantic import BaseModel
from raes.scenario import Scenario

from tools.sdl_catalog_parity._paths import _MARKDOWN_LINK_RE, REFERENCES_PATH


def _annotation_members(annotation: object) -> tuple[object, ...]:
    if get_origin(annotation) is Annotated:
        return _annotation_members(get_args(annotation)[0])
    if get_origin(annotation) in (Union, types.UnionType):
        return tuple(member for option in get_args(annotation) for member in _annotation_members(option))
    return (annotation,)


def _unwrap_reference_container(annotation: object) -> tuple[object, ...]:
    members: list[object] = []
    for option in _annotation_members(annotation):
        origin = get_origin(option)
        if not isinstance(origin, type):
            continue
        arguments = get_args(option)
        if issubclass(origin, Mapping) and len(arguments) == 2:
            members.append(arguments[1])
        elif issubclass(origin, Sequence) and origin is not str and arguments:
            members.append(arguments[0])
    return tuple(members)


def _model_field_annotations(annotation: object, field_name: str) -> tuple[object, ...]:
    annotations: list[object] = []
    for option in _annotation_members(annotation):
        if not isinstance(option, type) or not issubclass(option, BaseModel):
            continue
        for model_name, field in option.model_fields.items():
            aliases = {model_name}
            for alias in (field.alias, field.serialization_alias):
                if isinstance(alias, str):
                    aliases.add(alias)
            if field_name in aliases:
                annotations.append(field.annotation)
    return tuple(annotations)


def _advance_annotations(annotations: tuple[object, ...], segment: str) -> tuple[object, ...]:
    """Step one path segment through the typed model's field annotations."""

    if segment == "*":
        return tuple(member for annotation in annotations for member in _unwrap_reference_container(annotation))
    is_collection = segment.endswith("[]")
    field_name = segment[:-2] if is_collection else segment
    advanced = tuple(
        member for annotation in annotations for member in _model_field_annotations(annotation, field_name)
    )
    if is_collection:
        advanced = tuple(member for annotation in advanced for member in _unwrap_reference_container(annotation))
    return advanced


def _reference_source_path_exists(source_path: str) -> bool:
    annotations: tuple[object, ...] = (Scenario,)
    segments = source_path.split(".")
    for index, segment in enumerate(segments):
        if segment == "$key":
            return index == len(segments) - 1 and index > 0 and segments[index - 1] == "*"
        annotations = _advance_annotations(annotations, segment)
        if not annotations:
            return False
    return True


def _link_target_relative_path(target: str, repo_root: Path) -> str | None:
    relative: str | None = None
    if target.startswith("#"):
        relative = REFERENCES_PATH
    elif not target.startswith(("http:", "https:", "mailto:")):
        target_path = target.split("#", 1)[0]
        root = repo_root.resolve()
        resolved = (root / Path(REFERENCES_PATH).parent / target_path).resolve()
        try:
            relative = resolved.relative_to(root).as_posix()
        except ValueError:
            relative = None
    return relative


def _is_normative_reference_owner(owner: str, repo_root: Path) -> bool:
    targets = [match.group("target").strip() for match in _MARKDOWN_LINK_RE.finditer(owner)]
    if len(targets) != 1:
        return False
    relative = _link_target_relative_path(targets[0], repo_root)
    return relative is not None and relative.startswith(("specs/", "docs/decisions/adrs/"))
