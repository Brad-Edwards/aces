---
name: aces-asset-inventory-capture
description: Run the ACES asset inventory methodology as an agent-runnable capture workflow from either Claude Code or Codex. Use when asked to inventory a target image, container, host, or asset into a methodology-conformant evidence bundle with mapping-ledger.yaml, explicit capture-limits.txt declinations, scanner/SBOM evidence, and ACES/APTL gap triage.
---

# ACES Asset Inventory Capture

This skill runs from either Claude Code or Codex. Use it as the canonical
agent entry point for the participant-discoverable asset inventory
methodology: capture evidence first, map facts to ACES only when the mapping is
semantically correct, and leave every omission as durable evidence.

The ACES methodology remains the authority. Read
`docs/aces/inventory/asset-inventory-methodology.md` from the ACES repo before
capture; when working in a downstream checkout, use that ACES document as the
canonical source. This skill operationalizes that prose; it does not define a
second ledger schema or a second secret taxonomy.

For Docker/Compose/container-image captures, start by copying
`scripts/capture-container-evidence-template.sh` and
`scripts/normalize-syft-cyclonedx.jq` into the target bundle as runnable capture
resources, then tailor the copied script for asset-specific source paths,
filesystem manifests, and redaction names. Keep every evidence-affecting
normalization in the script or a referenced jq file.

## Inputs

Before running commands, identify:

- target asset id, scenario, and owning issue numbers;
- asset kind: image, running container, VM/host, or composed service;
- immutable target reference where possible, such as image digest or container
  id;
- output bundle directory, usually `docs/aces/inventory/<asset-id>/`;
- allowed discovery vantages inside the realized range.

If any input is missing, infer it from the repo and target runtime when safe.
Ask the user only before destructive lab resets, privileged host inspection, or
commands that may expose secrets.

## Bundle Contract

Produce a bundle that validates with the current APTL reference ledger tooling:

- `README.md` that states scope, target identity, verification commands, and
  known limits;
- `capture-evidence.sh` or equivalent committed capture commands, derived from
  the template for Docker/Compose assets when applicable;
- `mapping-ledger.yaml` using the current reference ledger schema;
- `evidence/` with raw or redacted evidence files;
- `evidence/capture-limits.txt` with one first-class limit for every skipped
  required step, declined useful-optional step, contamination boundary, or
  redaction that changes what was captured;
- `evidence/captured-at-utc.txt`;
- `evidence/evidence-sha256sums.txt` covering committed evidence files.

Every evidence file must be referenced from `mapping-ledger.yaml` through a
fact, provenance entry, correspondence check, or limit fact. Do not rely on an
unreferenced checksum file as accountability. If `capture-limits.txt` is
non-empty, add at least one ledger fact or correspondence check that references
it.

Run these before returning:

```shell
aptl aces-inventory schema
aptl aces-inventory validate <asset-dir>
aptl aces-inventory gaps <asset-dir>
```

No `needs_gap_triage` row may remain at review time.

## Capture Workflow

1. Define discovery vantages.

   Capture what a participant or in-range agent can discover. Host-side Docker
   evidence can support provenance, but it does not shrink the inclusion
   boundary.

2. Capture runtime and provenance evidence.

   Record Docker/Compose inspect output, immutable image identity, rootfs
   layers, image history, service configuration, network/volume state,
   process/listener state, OS release, users/groups, mounts, entrypoint,
   command, exposed ports, restart policy, resource limits, and source
   manifests where present. Use `jq` and `yq` for structured extraction.
   For containerized targets, copy and adapt
   `scripts/capture-container-evidence-template.sh` instead of rebuilding this
   command sequence from memory.

3. Run the required scanner baseline.

   Required unless explicitly declined in `capture-limits.txt`:

   - Trivy CycloneDX SBOM;
   - Trivy vulnerability JSON.

   Store tool versions and scanner target identity. Treat vulnerability output
   as time-sensitive evidence, not a permanent property of the asset.

4. Attempt the useful-optional baseline by default.

   Run these when available and applicable; otherwise record a first-class
   limit with the reason:

   - Syft CycloneDX SBOM;
   - osquery tables: `installed_applications`, `programs`, `apt_sources`,
     `processes`, `listening_ports`, `docker_containers`, and `docker_images`;
   - filesystem manifest tooling for the asset scope: `mtree`, AIDE, or
     Tripwire.

   If Syft CycloneDX output must be reduced for repository size, use
   `scripts/normalize-syft-cyclonedx.jq`. The only built-in allowed transform is
   stripping component properties named `syft:location:*` and deleting empty
   `properties` arrays. This is allowed only when component identity remains
   intact and separate filesystem provenance is captured or the omission is
   recorded in `capture-limits.txt`.

5. Hash and redact before committing.

   Follow ADR-029 redaction discipline. Do not place credentials, bearer
   tokens, private keys, generated service secrets, cookies, session ids, or
   operator-only values in evidence, logs, argv, tracebacks, issue comments, or
   `mapping-ledger.yaml`. Participant-visible fixture secrets may be retained
   only through the repo-approved secret-fixture classification.

6. Build the ledger fact-by-fact.

   Each captured fact needs evidence and an ACES/APTL mapping disposition:
   `encoded`, `encoded_with_caveat`, `blocked_by_aces_gap`,
   `blocked_by_aptl_gap`, or temporary `needs_gap_triage`. Before review,
   replace every `needs_gap_triage` with an encoded mapping or a linked gap.

7. Plan correspondence checks.

   Add `correspondence_checks` for later encoding work. Each check names the
   source surface, realized evidence, ledger fact ids, method, status, and
   limit.

## Semantic Gates

Apply these gates to every candidate fact before mapping it.

**Scenario-vs-delivery gate.** Ask: is this state on a range node that
participants can interact with? If yes, it is scenario state even when it looks
like Docker, Compose, Linux capability, seccomp, `/etc/hosts`, init wrapper, or
volume vocabulary. The delivery infrastructure boundary is the orchestrator,
host kernel, backend runtime, and control-plane machinery outside the
participant range.

**No-smuggling gate.** Apply this no-smuggling rule: do not hide a missing
typed field in a nearby free-text field. Package version evidence is not typed
application identity just because both mention software versions.

**No-force-fit gate.** Apply this no-force-fit rule: do not encode non-HTTP
CLI commands as fake URL paths, collapse flags into
`parameters[].location: other`, or otherwise choose the shallowest
schema-passing representation. A fact that requires reinterpretation of the
surface is a gap.

**Lineage-before-gap gate.** Before reporting an ACES expressivity gap, read
`docs/explain/sdl/lineage.md`, `docs/explain/sdl/precedents.md`, relevant
ADRs, and primary literature for the affected semantic family. The gap report
must state the captured fact, checked surfaces, lineage/prior-art treatment,
and why current surfaces are insufficient.

**No-solution-design gate.** Apply this no-solution-design rule: at the
gap-reporting boundary, stop after the grounded problem statement. Do not
propose a new normative surface, field name, or schema design unless the user
explicitly asks for upstream design work.

## Gap Handling

When current ACES cannot express a participant-discoverable fact:

1. Search existing ACES and APTL issues.
2. If a matching issue exists, link it in `mapping-ledger.yaml`.
3. If none exists, file or draft a gap with evidence path, discovery vantage,
   checked ACES surfaces, lineage/prior-art notes, and why the surfaces are
   insufficient.
4. Stop for discussion before continuing through additional gaps when the
   methodology or issue asks for that pause.

Do not use APTL backend consumption gaps as a substitute for ACES SDL
expression. Do not use ACES schema shape as the authority for what was
discovered.

## Completion Checklist

Before returning:

- required Trivy CycloneDX SBOM and Trivy vulnerability JSON are present, or
  each declined command has a `capture-limits.txt` entry and ledger reference;
- Syft, osquery, and filesystem-manifest attempts are present or explicitly
  declined;
- Syft normalization, when used, is deterministic, scripted, records the
  `syft:location:*` rule, and is paired with filesystem provenance or a
  first-class limit;
- every evidence file is referenced from `mapping-ledger.yaml`;
- `capture-limits.txt` records skipped methodology steps as first-class
  limits;
- no raw secrets or operator-only values are committed;
- `aptl aces-inventory validate <asset-dir>` passes;
- `aptl aces-inventory gaps <asset-dir>` has no unresolved
  `needs_gap_triage`;
- any methodology document in the target checkout references this skill as the
  canonical agent entry point.
