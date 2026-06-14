"""Hatchling build hook that bundles the published contract corpus (#537).

The corpus is the ADR-009 normative authority at the repository-root
``contracts/`` tree, which lives *outside* this Python project directory. A
static ``force-include`` of ``../../contracts`` works when the wheel is built
directly from the source checkout, but breaks when the wheel is built from an
unpacked sdist — the ``../../contracts`` parent path is not present inside the
sdist, so ``uv build`` (which builds the wheel from the sdist) fails with
``Forced include not found``.

This hook resolves the corpus from whichever layout is being built and
force-includes it into the wheel at ``aces_contracts/_corpus``:

* **source checkout** — the corpus is the authority at ``<repo>/contracts``;
* **sdist** — the sdist target vendors the corpus at top-level ``_corpus/``
  (see ``[tool.hatch.build.targets.sdist.force-include]``), so a wheel built
  from the sdist still finds it.

The runtime resolver (``aces_contracts.corpus``) reads the bundled corpus via
``importlib.resources``; this hook only governs what lands in the wheel.
"""

from __future__ import annotations

from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

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
