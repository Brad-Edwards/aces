Runtime Layer
=============

The ``aces_runtime`` package owns live runtime control: runtime targets,
backend registry integration, manager lifecycle execution, control-plane
submission and observation, operation persistence, security, and backend
result-contract validation helpers.

Runtime APIs consume neutral DTOs from ``aces_contracts`` at backend and
control-plane boundaries. Header-based control-plane identity is disabled by
default and requires an explicit ``ControlPlaneSecurityConfig`` with
``trust_proxy_identity_headers=True``.

.. currentmodule:: aces_runtime

Public API
----------

.. automodule:: aces_runtime
   :members:
   :undoc-members:

Runtime Manager
---------------

.. automodule:: aces_runtime.manager
   :members:

Backend Registry
----------------

.. automodule:: aces_runtime.registry
   :members:

Control Plane
-------------

.. automodule:: aces_runtime.control_plane
   :members:

Control Plane API
-----------------

.. automodule:: aces_runtime.control_plane_api
   :members:

Control Plane Store
-------------------

.. automodule:: aces_runtime.control_plane_store
   :members:

Control Plane Security
----------------------

.. automodule:: aces_runtime.control_plane_security
   :members:

Result Contracts
----------------

.. automodule:: aces_runtime.result_contracts
   :members:
