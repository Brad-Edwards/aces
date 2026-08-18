# Issue 1110 Required Real-Container Release Gate

Date: 2026-08-12

Issue: #1110. Requirements: GOV-928 and RUN-314.

## Gap Claim

RUN-314 claims a reference backend that realizes scenarios against real
infrastructure, but ordinary canonical verification is deliberately hermetic.
The only Docker integration job in CI is optional, `continue-on-error`, and
skips when the runtime or integration image is unavailable. A release could
therefore publish even though the exact release commit had never completed a
real container lifecycle.

## Existing Surface Audit And Lineage

- `.github/workflows/canonical-verification.yml` runs the proof-bearing
  repository verification graph at an exact SHA. Making Docker a prerequisite
  there would break its portable PR/branch contract.
- `.github/workflows/ci.yml` and `nox -s integration_docker` provide the existing
  RUN-314 real-runtime lane, but intentionally preserve optional local and PR
  behavior.
- `test_reference_backend_docker_integration.py`, the OCI driver, ADR-063, and
  issue #197 own the established reference-backend realization family. The
  release gate must exercise that family, not add a second container harness or
  Docker-specific SDL surface.
- Issue #684 and GOV-928 already bind verification, artifacts, and publication
  to one release SHA. The missing gate belongs in that same dependency graph.

## Alternatives

1. Keep the optional CI observation. Rejected because a skip or tolerated
   failure is not release evidence.
2. Add Docker to the reusable canonical verifier. Rejected because that changes
   a hermetic cross-context gate into a runner-dependent one for every PR.
3. Add a release-only, read-only exact-SHA job after canonical verification and
   before build. Selected because it makes real-container evidence mandatory at
   the publication boundary without weakening ordinary development portability.

## Chosen Architecture

The release job checks out the resolved 40-character release SHA, proves that
`HEAD` matches it, and runs the existing `integration_docker` nox session with
`RAES_DOCKER_INTEGRATION_REQUIRED=1`. Required mode converts missing
Docker/Podman and image-pull failures from skips to test failures. The scenario
pins Alpine to the reviewed multiarch digest
`sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc`
rather than resolving a mutable tag.

The job writes pytest JUnit evidence and independently rejects zero collected
tests or any skipped case. `build-release` and `publish-pypi` require this job's
explicit `success`; it has only `contents: read` and no environment, release
write, secret, or OIDC authority. Optional CI/local execution keeps its prior
skip behavior.

## Boundaries And Verification

This gate proves the reviewed image can be pulled and that the exact release
code completes the current reference-backend real-container tests on the
GitHub-hosted runner. It does not establish support for every OCI runtime,
architecture, registry, or production topology, and a digest pin is not an
SBOM or provenance attestation.

Policy tests assert the exact-SHA checkout, required-mode environment, digest,
no-skip/zero-test JUnit checks, build/publication dependencies, and unchanged
optional CI behavior. Fixture tests cover optional skip, required failure,
image unavailability, invalid mode, and successful admission.
