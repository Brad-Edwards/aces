Processor Layer
===============

The ``raes_processor`` package provides SDL processing: instantiation-aware
compilation, reconciliation planning, support determination, manifest
authority, and compiled processor runtime models. Per ADR-036, live runtime
control lives in ``raes_runtime`` and cross-package runtime/backend DTOs live
in ``raes_contracts``.

.. currentmodule:: raes_processor

Public API
----------

.. automodule:: raes_processor
   :members:
   :undoc-members:

Compiler
--------

.. automodule:: raes_processor.compiler
   :members:

Processor Models
----------------

The runtime data models live in the ``raes_processor.models`` package; its
``__init__`` re-exports the full public surface, and the classes and functions
are documented here from the subdomain modules that define them.

.. automodule:: raes_processor.models.resources
   :members:

.. automodule:: raes_processor.models.behavior_resources
   :members:

.. automodule:: raes_processor.models.action_results
   :members:

.. automodule:: raes_processor.models.attribution
   :members:

.. automodule:: raes_processor.models.outcome
   :members:

.. automodule:: raes_processor.models.outcome_interpretation_validation
   :members:

.. automodule:: raes_processor.models.temporal
   :members:

.. automodule:: raes_processor.models.history_event
   :members:

.. automodule:: raes_processor.models.behavior_history_violations
   :members:

.. automodule:: raes_processor.models.runtime_model
   :members:

Manifest Authority
------------------

.. automodule:: raes_processor.manifest
   :members:

Planner
-------

.. automodule:: raes_processor.planner
   :members:

Capabilities
------------

.. automodule:: raes_processor.capabilities
   :members:

Exploit-Path Analysis
---------------------

.. automodule:: raes_processor.exploit_path
   :members:
