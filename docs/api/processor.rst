Processor Layer
===============

The ``aces_processor`` package provides SDL processing: instantiation-aware
compilation, reconciliation planning, support determination, manifest
authority, and compiled processor runtime models. Per ADR-036, live runtime
control lives in ``aces_runtime`` and cross-package runtime/backend DTOs live
in ``aces_contracts``.

.. currentmodule:: aces_processor

Public API
----------

.. automodule:: aces_processor
   :members:
   :undoc-members:

Compiler
--------

.. automodule:: aces_processor.compiler
   :members:

Processor Models
----------------

The runtime data models live in the ``aces_processor.models`` package; its
``__init__`` re-exports the full public surface, and the classes and functions
are documented here from the subdomain modules that define them.

.. automodule:: aces_processor.models.resources
   :members:

.. automodule:: aces_processor.models.behavior_resources
   :members:

.. automodule:: aces_processor.models.action_results
   :members:

.. automodule:: aces_processor.models.attribution
   :members:

.. automodule:: aces_processor.models.outcome
   :members:

.. automodule:: aces_processor.models.outcome_interpretation_validation
   :members:

.. automodule:: aces_processor.models.temporal
   :members:

.. automodule:: aces_processor.models.history_event
   :members:

.. automodule:: aces_processor.models.behavior_history_violations
   :members:

.. automodule:: aces_processor.models.runtime_model
   :members:

Manifest Authority
------------------

.. automodule:: aces_processor.manifest
   :members:

Planner
-------

.. automodule:: aces_processor.planner
   :members:

Capabilities
------------

.. automodule:: aces_processor.capabilities
   :members:
