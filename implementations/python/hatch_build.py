"""Hatchling hooks for the aces-sdl package (#537, #684).

Two things this package needs live *outside* this Python project directory, at
the repository root, and are pulled in at build time:

* the published contract corpus (``<repo>/contracts``) — bundled into the wheel
  as package data by the build hook below; and
* the project ``README.md`` (``<repo>/README.md``) — injected as the PyPI long
  description by the metadata hook below, so there is a single README source and
  no duplicate copy under ``implementations/python``.

Both reach ``../..`` in a source checkout and fall back to a copy vendored into
the sdist, so the ``uv build`` sdist→wheel path also resolves them: the sdist
force-includes ``../../contracts`` as ``_corpus/`` and ``../../README.md`` as
``README.md`` (see ``[tool.hatch.build.targets.sdist.force-include]``).
"""

from __future__ import annotations

from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.metadata.plugin.interface import MetadataHookInterface

_WHEEL_DESTINATION = "aces_contracts/_corpus"


class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        source_checkout_corpus = (root.parent.parent / "contracts").resolve()
        vendored_sdist_corpus = (root / "_corpus").resolve()

        if source_checkout_corpus.is_dir():
            corpus = source_checkout_corpus
        elif vendored_sdist_corpus.is_dir():
            corpus = vendored_sdist_corpus
        else:
            raise FileNotFoundError(
                "contract corpus not found for packaging: looked for "
                f"{source_checkout_corpus} (source checkout) and "
                f"{vendored_sdist_corpus} (sdist). The wheel cannot ship "
                "without the corpus."
            )

        build_data.setdefault("force_include", {})[str(corpus)] = _WHEEL_DESTINATION


class ReadmeMetadataHook(MetadataHookInterface):
    """Inject the repo-root README.md as the package's PyPI long description.

    The Python package lives in ``implementations/python`` but the canonical
    README is at the repo root (the repo is spec-first; the root README covers
    the whole project). Rather than maintain a duplicate package README, this
    hook sets ``readme`` from the root README at build time;
    ``[project] dynamic = ["readme"]`` delegates the field to it.
    """

    PLUGIN_NAME = "custom"

    def update(self, metadata: dict) -> None:
        root = Path(self.root)
        source_checkout_readme = (root.parent.parent / "README.md").resolve()
        vendored_sdist_readme = (root / "README.md").resolve()

        if source_checkout_readme.is_file():
            readme = source_checkout_readme
        elif vendored_sdist_readme.is_file():
            readme = vendored_sdist_readme
        else:
            raise FileNotFoundError(
                "project README not found for packaging: looked for "
                f"{source_checkout_readme} (source checkout) and "
                f"{vendored_sdist_readme} (sdist)."
            )

        metadata["readme"] = {
            "content-type": "text/markdown",
            "text": readme.read_text(encoding="utf-8"),
        }
