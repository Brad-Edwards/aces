"""SDL inspection tools — analyze, query, and summarize parsed scenarios.

These tools work on SDL YAML that has already been written.  They let
agents understand the structure of a scenario, look up individual
elements, trace cross-references, and get high-level summaries.

This package is a thin facade over cohesive subdomains:

* :mod:`.tools` - the ``register`` entry point and its ``@mcp.tool`` definitions.
* :mod:`._common` - shared constants and the bounded canonical parse path.
* :mod:`._summary` - scenario summary rendering.
* :mod:`._elements` - element listing and detail rendering.
* :mod:`._references` - cross-reference analysis and ASCII topology rendering.

The submodule import below is the package's public re-export surface. It is
deliberately NOT narrowed by an ``__all__`` (the pre-split module had none, so
adding one would change ``import *`` semantics). F401 is ignored for this facade
in pyproject.toml - the "unused import" claim is false for a re-export.
"""

from .tools import register
