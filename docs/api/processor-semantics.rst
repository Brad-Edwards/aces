Processor Semantics
===================

The ``raes_processor.semantics`` subpackage holds processor-runtime
reconciliation helpers — dependency-graph construction over compiled
resources, topological ordering, and resource-action reconciliation between
compiled resources and runtime snapshots.

Per ADR-015, the SDL-language semantic helpers (objective windows, the
workflow step-type contract, branch closure, the workflow step-result
validator) live under ``raes.semantics`` and are documented in
:doc:`sdl-semantics`.

.. currentmodule:: raes_processor.semantics

Planner Semantics
-----------------

.. automodule:: raes_processor.semantics.planner
   :members:
