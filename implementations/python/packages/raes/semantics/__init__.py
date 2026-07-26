"""SDL-language semantic rules (objective windows, workflow step contracts).

Per ADR-015, these helpers live with the SDL package: the ``raes.validator``
package uses them, and they have no processor-runtime dependencies. The processor's
own reconciliation helpers stay at ``raes_processor.semantics.planner``.
"""
