"""SDL authoring tools — validate, scaffold, and instantiate scenarios.

These tools let agents write SDL from scratch, check it for errors,
build up scenarios incrementally, and instantiate parameterized
scenarios with concrete values.

This package is a thin facade over cohesive subdomains:

* :mod:`.tools` - the ``register`` entry point and its ``@mcp.tool`` definitions.
* :mod:`._templates` - the scaffold example documents.
* :mod:`._helpers` - the section-summary helper shared by the tools.

The submodule import below is the package's public re-export surface. It is
deliberately NOT narrowed by an ``__all__`` (the pre-split module had none, so
adding one would change ``import *`` semantics). F401 is ignored for this facade
in pyproject.toml - the "unused import" claim is false for a re-export.
"""

from .tools import register
