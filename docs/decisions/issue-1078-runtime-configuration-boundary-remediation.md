# Issue 1078 Runtime-Configuration Boundary Remediation

Date: 2026-09-03

Status: implemented on the issue branch; backend realization remains
capability-gated.

## Gap Claim

`RuntimeConfiguration` exposes 32 top-level authoring dimensions, but the
canonical SEM-218 concern registry previously covered four roots and three
partial roots. An author could therefore assign posture to a valid runtime
field without that posture reaching compiled requirements, resolved plan
authority, backend admission, observation, or persistence.

The complete field and ownership audit is recorded in
`issue-1078-runtime-configuration-boundary-coverage-preflight.md`. This
remediation makes that inventory executable and fails import if a future
top-level runtime field lacks a disposition.

## Decision

Keep `RealizationConcernDescriptor` as the single concern registry. Register
each portable runtime family or independently governed leaf there, using the
existing typed Pydantic annotation as its closed observation contract. Split
mixed objects where admission or observation semantics differ:

- restart, node capacity, and process resource limits remain separate;
- container launch, namespace, security, device, resolver, and engine choices
  have independent concern paths;
- hostname, domain name, endpoint attachment, and published ports remain
  separate network concerns; and
- configuration is projected separately from run state, readiness, live
  counts, loaded state, status text, realized children, and evidence metadata.

Every registered runtime concern now carries a non-null verification scope and
an independent observation-strength floor. Exact admission requires both the
existing generic exact capability and the concern-kind token, plus a matching
observation capability. Constrained and open admission continue through the
same support-declaration and envelope paths. A returned plan echo without a
matching concern observation is rejected before snapshot persistence.

The executable inventory records the canonical concern owner, delegated paths,
observation-only paths, and enforcement status for all 32 fields. Volume and
image mounts retain their stateful-resource/content owners. The
`environment_files` field synchronized from issue #1074 remains delegated to
the generated-artifact concern and its exact environment-consumer delivery
binding instead of duplicating that authority as a runtime concern. Native process,
package, file, account, unit, dependency, and apparatus inventory remains
outside a concern unless the backend selects the scenario-significant managed
subset for that concern.

## Projection And Secret Boundary

Generic runtime projections validate against the owning closed SDL type,
canonicalize keyed collections, preserve ordered command-like sequences, and
remove non-realization annotations and family-specific outcomes. Stable record
identity, rather than array position, domains sensitive-value commitments, so
permuting a keyed collection does not change its comparison value.

Raw `redacted` and `operator_secret` values remain forbidden. Deliberately
authored `secret_fixture` values use the existing domain-separated canonical
JSON commitment; observed fixtures must return that commitment rather than raw
material. Presence markers and commitments are validated as a closed wire
shape, and only the safe projection can cross the snapshot boundary.

## Alternatives Considered

1. Leave unregistered fields as documentation-only inventory. Rejected because
   valid author posture would still disappear before planning.
2. Add one `runtime-configuration` aggregate concern. Rejected because the
   weakest child would govern unrelated families and because collection
   identity, admission, and observation differ materially.
3. Let each backend interpret runtime posture locally. Rejected because it
   would duplicate SEM-218, allow backend drift, and bypass the resolved
   authority handoff.
4. Extend the incumbent registry with typed profiles and keep unsupported
   backends honest. Selected because it preserves the existing compiler,
   planner, plan schema, runtime gate, and persistence seam.

## Standards And Lineage

This change completes SEM-218 and the plan-authority handoff from issue #1067;
it does not introduce a second policy carrier. The inventory and projection
choices also retain the asset/service ownership established by ADR-033 and the
runtime-family ADRs cited in the preflight.

The package/component/manifest distinction follows the SPDX 3.0.1 scope and
model rather than treating an SBOM as installed-state proof:
<https://spdx.github.io/spdx-spec/v3.0.1/scope/>. CycloneDX remains an evidence
and interchange source, not a runtime realization backend:
<https://cyclonedx.org/specification/overview/>. Scheduled-job cadence keeps
the existing portable POSIX cron surface while execution outcomes remain
observation data: <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/crontab.html>.

## Backend And Downstream Boundary

Reference and libvirt manifests are intentionally not widened. They cannot
claim a newly registered kind until their adapters materialize the complete
safe projection and independently disclose the required readback. Downstream
APTL consumes the published plan authority and concern tokens; it must not
parse scenario designation or build a parallel posture table.

No public schema changes are required: concern kinds are already opaque,
non-empty strings, resolved authority already carries payload pointers and
observation bars, and observation disclosures already identify concern kind,
scope, and strength.

## Verification Contract

Conformance tests assert the 32-field partition, unique paths and kinds,
exact/constrained/open capability behavior for every generic runtime concern,
closed-authority excess rejection, observation-only explicitness isolation,
closed observed shapes, stable collection ordering, sensitive-value
commitments, total plan authority, and compatibility with the established
SEM-218, process-limit, forwarding, and authority-handoff suites.
