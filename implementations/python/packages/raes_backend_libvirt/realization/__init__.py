"""Pure interpretation of provisioning plans for the libvirt backend.

Maps an RAES :class:`ProvisioningPlan` into a driver-neutral :class:`Realization`
of portable network/domain specs. Node resources become libvirt domains; network
resources become libvirt networks; and placement resources are bound to their
target domains. Content, account, and feature placements contribute to cloud-init:

- ``account-placement`` → cloud-init ``users`` (groups, shell, home, disabled,
  auth_method) plus ``/etc/aliases.d`` (mail) and ``/etc/raes/spn`` (spn) files;
- ``content-placement`` → cloud-init ``write_files`` (file/text) or ``runcmd``
  and a descriptor file (dataset/directory/source-backed);
- ``feature-binding`` → cloud-init ``packages``/``runcmd`` (service) or a
  descriptor file (artifact/configuration).

The module is pure (no driver, no IO): the provisioner validates a plan without
realizing it, and the driver renders seed media from the same data.
"""

from __future__ import annotations

from ._common import _resource_name as _resource_name
from ._plan import Realization as Realization
from ._plan import interpret_provisioning_plan as interpret_provisioning_plan
from ._specs import _image_ref as _image_ref
from ._specs import _infrastructure_spec as _infrastructure_spec
from ._specs import _memory_mib as _memory_mib
from ._specs import _node_resources as _node_resources
from ._specs import _services as _services
from ._specs import _vcpus as _vcpus
