# Stateful realization resources

`generated_artifacts` and `persistent_volumes` are portable provisioning
desired state. They describe prerequisites a stateful service consumes; they
are not observations of mounts already present on a running node and they are
not provider-specific Compose fragments.

Every declaration has a user-defined identifier and compiles to one stable
provisioning address:

- `generated_artifacts.<id>` becomes
  `provision.generated-artifact.<id>`;
- `persistent_volumes.<id>` becomes
  `provision.persistent-volume.<id>`.

## Generated artifacts

A generated artifact declares a `certificate_bundle` or `rendered_config`
generator, its regeneration lifecycle, non-secret provenance, the complete
output set, and every consumer. Each output carries a contained relative path
and a sensitivity class (`public`, `restricted`, or `secret`). The contract
contains desired metadata only; secret values and rendered bytes never enter
SDL, plans, diagnostics, or provenance.

## Persistent volumes

A persistent volume declares `retain` or `ephemeral` lifecycle, portable
single/multi-writer access semantics, and every consumer. Consumers name a
declared node, an absolute mount destination below `/`, and read-only or
read-write access.

## Graph and realization rules

Both resource kinds may carry addressable `ordering_dependencies` and
`refresh_dependencies`. References must resolve across the combined stateful
resource set. Ordering dependencies must be acyclic. Reference and graph
validation completes before provisioning operations are dispatched.

The compiler preserves each declaration as an exact SEM-218 realization
requirement and emits its typed payload into the provisioning plan. Backends
must either honor the complete declared resource or reject the plan; silently
substituting an observed mount, generic content placement, or provider-private
configuration is not conformant.
