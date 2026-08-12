# Issue 1137: Bounded CI Release-Download Retries

Date: 2026-08-12

Issue: #1137. Requirement: GOV-913.

## Context And Gap

OpenRAE's required verification lanes acquire pinned Conftest, Vale, Gitleaks,
and OSV Scanner artifacts from their canonical GitHub Releases repositories.
The owning installers validate checksums before executing or extracting those
artifacts. During review of several independent pull requests, GitHub returned
temporary disconnects and HTTP 503 responses while acquiring all four tool
families. A single such response failed the lane before it could inspect the
pull request's code; rerunning the unchanged commit succeeded once the release
service recovered.

The integrity checks were behaving correctly, but acquisition had no bounded
transient-failure policy. This note defines that missing reliability boundary.
It changes neither the verification graph nor the meaning of a passing gate.

## Existing-Surface Review

The review covered the four repository-local installers, their version pins,
checksum sources, archive extraction, cache paths, nox callers, and required CI
jobs. The installers previously used separate direct `urllib` calls. There was
no shared release-acquisition helper to extend. Runtime OCI/module downloads,
vocabulary-source refreshes, Isabelle's separately governed official-mirror
policy, and GitHub Actions artifact transfer are different trust or ownership
boundaries and remain out of scope.

PR #1121 independently hardens OSV Scanner's cache type, identity, digest,
atomic-install, and size checks. The retry helper composes below that work: it
only returns bounded bytes from the already approved OSV release origin, while
the OSV installer remains the sole owner of cache and checksum validation.

## Chosen Policy

All four installers bind their existing `urlopen` seam to one internal helper.
The initial request accepts only exact HTTPS paths under these GitHub Release
families:

- `errata-ai/vale`;
- `gitleaks/gitleaks`;
- `google/osv-scanner`; and
- `open-policy-agent/conftest`.

Redirects are handled explicitly instead of delegated to `urllib`. A request
may follow at most three hops, and each transition must be one of the current
GitHub-controlled release paths: the exact `errata-ai/vale` to `vale-cli/vale`
repository relocation with an unchanged release suffix, or an approved GitHub
release URL to an exact `release-assets.githubusercontent.com` production-asset
path. Only that final asset URL may contain GitHub's ephemeral signed query;
the query is never included in a diagnostic, and the asset host cannot redirect
again. Relative, HTTP, cross-origin, credential-bearing, ambiguous, cyclic,
oversized, and other unapproved locations fail without retry. Redirect response
bodies are closed without being read.

The helper performs at most three attempts. Every connection hop and every
bounded body read receives a finite 60-second socket timeout capped by the
remaining 190-second total deadline. Exponential delays are deterministic and
capped, and a deadline-aware socket reader reapplies the remaining bound to
every status-line, header, chunk-framing, and body buffer fill. No read,
redirect hop, sleep, or new attempt may continue after the deadline. Declared
response lengths are checked before and after streaming; ambiguous framing and
oversized bodies fail immediately, while an early EOF is classified as a
retryable incomplete transfer. Each response is bounded to 256 MiB before it
is returned to an installer. There is no jitter, alternate mirror, unpinned
version, credential, or redirect-selection fallback.

Only these failures are retryable:

- HTTP 408 and 429;
- HTTP 500 through 599; and
- timeouts, remote disconnects, incomplete responses, and connection failures.

`Retry-After` delta-seconds and HTTP-date values are honored, but an individual
value is capped at ten seconds and can never extend the total deadline. All
other HTTP and URL failures stop after the first attempt. Final diagnostics
include only the approved URL path, attempt count, and stable failure class;
they omit response bodies and exception text. Malformed HTTP status, header,
and framing exceptions are normalized to one non-retryable diagnostic rather
than reflecting upstream text.

The helper buffers a successful bounded response and then returns control to
the owning installer. Consequently, checksum mismatch, signature failure,
archive/type rejection, cache identity failure, and extraction failure happen
outside the retry loop and cannot cause a second download. Required lanes still
fail closed when every transient attempt fails.

## Alternatives Rejected

- **Retry each installer independently.** This would create four subtly
  different status lists, delays, deadlines, and diagnostics that could drift.
- **Retry every `URLError` or every HTTP failure.** Certificate, DNS-policy,
  authorization, missing-asset, and malformed-request failures are not evidence
  of a safe transient event. Retrying them obscures configuration or trust
  failures.
- **Retry after checksum or extraction failure.** A successful transfer of
  invalid bytes is an integrity event, not availability noise. Retrying could
  conceal unstable or malicious upstream content.
- **Use a mirror or latest-version fallback.** This would bypass the reviewed
  origin, version, and digest boundary.
- **Rely on manual workflow reruns.** Manual reruns provide no deterministic
  attempt/time bound and consume reviewer attention without increasing
  assurance.

## Verification And Nonclaims

Deterministic tests cover every approved origin and redirect transition,
ambiguous URL and response-framing rejection, redirect cycles and hop bounds,
success after transient HTTP and transport failures, incomplete declared
responses, delta and HTTP-date `Retry-After`, read/backoff/deadline caps, exact
exhaustion, non-retryable HTTP and URL failures, response-size rejection,
sanitized diagnostics, and no second request after checksum or archive-type
failure. Local scripted HTTP servers verify that an early EOF never returns
partial bytes, redirect bodies are not drained, and a trickling body cannot
extend the total deadline. The same scripted transport verifies that trickled
redirect headers and chunk trailers cannot extend that deadline and that a
malformed status line cannot leak upstream text. A binding test ensures all
four installers continue to share the helper, and clean-cache smoke tests
exercise the live current GitHub redirect chain for all four pinned tools.

This policy does not make GitHub availability hermetic, validate remote bytes,
or replace the installers' pins, checksums, signatures, archive rules, cache
hardening, or execution gates. It only absorbs a small, explicitly classified
window of transient release-service failure.
