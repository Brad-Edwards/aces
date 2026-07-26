# Participant-Discoverable Asset Inventory Methodology

This is the RAES-owned methodology for participant-discoverable asset
inventory capture. It was first validated against the TechVault
`shuffle-backend` asset during APTL issue #353, with later APTL asset
captures used as downstream proof work. The companion assurance report
`docs/raes/inventory/methodology-assurance-report.md` records the DevOps,
supply-chain, reproducible-research, and verification/validation basis for the
methodology. The method has one inclusion rule:

> If a participant or agent could discover a fact from inside the range,
> capture it and attempt to specify it in RAES.

There is no relevance filter during capture, no accidental-versus-deliberate
filter, and no early split that sends facts to backend evidence merely because
they came from Docker or another realization layer. RAES is the methodology and
specification authority. A downstream runtime such as APTL can provide
reference reality for a proof pass, but it does not own the inclusion rule.
The participant-discoverable rule is the evidence boundary for inventory
capture; it is not the semantic frame for extending the SDL. Backend and
provenance evidence explain how the configuration was realized and how the
claim was captured; they do not shrink the set of facts that must be attempted
in RAES.

## Scope and Claim Boundary

The method captures steady-state asset configuration facts within the
participant-discoverable boundary: network facts, services, versions, packages,
files, data, connections, processes, mounts, credentials, configuration, trust
surfaces, and any other fact an in-range participant or agent could discover.
It also captures provenance and assurance artifacts so the discovery claim can
be audited.

It does not claim byte-identical rebuildability, independent replication of
scenario outcomes, or dynamic behavior coverage. For the first TechVault
validation pass, this was best described as an asset configuration inventory
plus a reproducible evidence bundle. In digital twin terms, it is a digital
model or digital shadow. It is not a live digital twin because the inventory is
not continuously synchronized with the running system and does not provide a
closed feedback loop.

The practical reproducibility standard is therefore:

- another maintainer can identify every captured participant-discoverable
  fact, its discovery vantage, and the evidence that supports it;
- every captured fact has either an RAES specification mapping or an RAES
  issue for the expressivity gap;
- the capture can be rerun with non-commercial tooling on a local lab;
- limits, time-sensitive scanner output, mutable tags, operator/out-of-scenario
  withholding, and skipped steps are recorded plainly.

This follows the computational reproducibility framing in Peng (2011),
Goodman, Fanelli, and Ioannidis (2016), and Boettiger (2015): preserve
the code, environment, parameters, and artifacts needed to assess a
computational claim, without overstating that the result is an independent
scientific replication.

## Requirement Alignment

This methodology is support for the RAES requirements that govern apparatus,
provenance, realized-form disclosure, replay, and realization honesty. It does
not replace those requirements or define final SDL syntax. Its role is to make
the evidence and gap trail explicit enough for those requirement surfaces to
consume:

- `EXP-704` apparatus context: record discovery vantages, tool agents, backend
  identity, runtime identities, and capture limits.
- `EXP-712` reproducibility and replay: preserve rerunnable commands,
  immutable artifact identifiers, scanner/tool versions, checksums, and known
  non-claims.
- `EXP-720` canonical run provenance: separate entities, activities, agents,
  and evidence artifacts so later run records can cite the inventory.
- `EXP-722` realized-form disclosure: capture realized runtime state even when
  it differs from authored intent or backend defaults.
- `ASR-519` realization honesty: force explicit mappings, caveats, and gap
  issues instead of silent approximation or evidence-only claims.
- `DSL-115` and follow-on DSL gap work: route missing SDL expressivity to RAES
  issue records with evidence and checked surfaces.

The reusable downstream issue skeleton for applying this method lives in
`docs/raes/inventory/asset-inventory-issue-template.md`.

## Evidence Model

Each asset is described across five layers:

| Layer | Meaning | Typical evidence |
| --- | --- | --- |
| Discovery vantage | Where an in-range participant or agent could learn the fact. | Kali/red-agent shell, compromised app shell, blue console, service API, filesystem, network scan. |
| Captured configuration fact | The discovered fact itself, with no intent/relevance filtering. | IPs, DNS names, routes, ports, banners, versions, files, packages, env names/values visible in-range, processes, mounts, data, credentials. |
| RAES specification mapping | The SDL element or RAES contract that represents the fact. | `nodes`, `infrastructure`, `services`, `features`, `content`, `accounts`, `relationships`, `agents`, `objectives`, variables, or a cited RAES issue. |
| Provenance | Where the realized artifact came from and which immutable identifiers were observed. | Image digest, image history, Dockerfile or upstream absence, source lockfiles, scanner/tool versions. |
| Assurance products | Derived artifacts used for audit, comparison, and gap filing. | CycloneDX or SPDX SBOM, vulnerability JSON, package list, filesystem hashes, evidence checksums. |

This mirrors the W3C PROV separation between entities, activities, and
agents: a document should not merely say "shuffle-backend exists"; it
should identify the authored source, the capture activity, the tool agent,
and the resulting evidence artifacts.

## Capture and Specification Recipe

Skip a step only when it does not make sense for the asset class, and
record the skip in the per-asset note. For example, an upstream image with
no in-repo Dockerfile should record the image digest and image history
instead of pretending a local build recipe exists.

1. Define in-range discovery vantage points.

   Identify the participant and agent positions that can discover facts:
   red-agent host, blue console, compromised container shell, exposed service
   API, web UI, database session, directory service, SIEM/SOAR console, and
   any other in-range position the scenario makes possible. Host-side Docker
   commands are supporting evidence, not the primary inclusion criterion.

2. Capture every participant-discoverable fact.

   From the relevant vantage points, capture network topology, IPs, DNS,
   routes, ARP/neighbors, open ports, banners, TLS certificates, HTTP
   headers, service versions, application pages, API metadata, auth behavior,
   files, directories, package versions, OS details, processes, listeners,
   mounts, environment variables, readable secrets, data stores, workflows,
   logs, relationships, credentials, trust surfaces, and connections.
   Capture first; do not filter for intent, portability, elegance, or
   accidentalness.

3. Classify the asset for provenance and rerun support.

   Record service name, container name, source class, owning profile or
   family target, upstream/custom status, expected network identity, data
   volumes, secrets policy, and steady-state boundary. Classify source as
   `custom-build`, `upstream-image`, or `runtime-composed`.

4. Capture source provenance.

   Preserve the Compose service slice, relevant downstream runtime
   configuration references, Dockerfile or source package paths when present,
   image ID, repo digest,
   rootfs layers, image history, build labels, and language lockfiles.
   Mutable tags such as `latest` are never enough; pair them with the
   observed digest. For container images, also check for registry-visible
   attestations and record the result in the ledger provenance block. For
   first-party custom builds, prefer BuildKit/Docker build attestations that
   emit SBOM and provenance at build time, and preserve in-toto/SLSA predicate
   type, builder identity, and verification result when available.

5. Capture realized runtime state.

   Preserve container inspect, network inspect, volume inspect, process
   list, listeners, mounts, OS release, users/groups, working directory,
   command/entrypoint, exposed ports, restart policy, resource limits, bind
   mounts, and scenario-target secrets. Participant-discoverable target
   credentials, password hashes, private keys, bearer tokens, generated service
   secrets, config secrets, and other credential-shaped values are capture
   facts and must not be redacted from source inventory bundles. For example,
   Wazuh/OpenSearch Security `internal_users.yml` bcrypt hashes are target
   configuration facts; replacing them with `<REDACTED-...>` corrupts the
   inventory and prevents later RAES/APTL mapping from seeing the realized
   system.

   Operator/out-of-scenario secrets remain outside the capture boundary:
   host SSH keys, cloud or CI tokens, maintainer credentials, local
   control-plane secrets, workstation secrets, unrelated prior-run
   transcripts, and accidental adjacent-environment material are not scenario
   facts. Exclude them, or record the withheld scope and reason as a
   first-class `capture-limits.txt` entry. Sanitized publication/export
   bundles are separate derived views; they must not replace the authoritative
   source inventory bundle.

6. Capture package and dependency inventory.

   Prefer a standards-backed SBOM. CycloneDX JSON is the default for this
   spike because Trivy can emit it directly; SPDX is acceptable when a
   downstream consumer needs SPDX profiles. Also capture OS package-manager
   output and language manifests or lockfiles visible inside the container.
   Any SBOM minification or normalization must be deterministic, scripted in
   the bundle, and recorded in `capture-limits.txt`. For Syft CycloneDX output,
   a repository-size-safe package/component SBOM may disable file catalogers and
   strip `syft:location:*` component properties only when the package/component
   identity fields remain intact and separate filesystem evidence is captured
   or explicitly declined. The exact command and jq transform are part of the
   reproducibility record, not an analyst-only cleanup step.

7. Capture patch and vulnerability state.

   Run an open vulnerability scanner such as Trivy or Grype against the
   immutable image digest. Store full machine-readable results, a severity
   count summary, scanner version, and any scanner image digest. Treat
   vulnerability data as time-sensitive evidence, not as a permanent truth
   about the asset.

8. Capture filesystem integrity for load-bearing paths.

   Hash application and configuration paths that matter to scenario
   behavior. Exclude virtual filesystems and high-churn paths such as
   `/proc`, `/sys`, `/dev`, `/run`, caches, logs, and temp directories.
   For larger assets, replace ad hoc `sha256sum` output with a stable
   manifest tool such as `mtree`, AIDE, or Tripwire.

9. Capture relationships and trust surfaces.

   Record inbound consumers, outbound dependencies, trust boundaries,
   authentication surfaces, privileged binds, exposed listeners, data
   volumes, and implicit backend requirements. This is where Docker socket
   binds, service DNS names, static IPs, and healthcheck dependencies
   become visible.

10. Attempt maximal RAES mapping without silently promoting evidence.

   For every participant-discoverable fact, identify the most specific RAES
   carrier. First preserve the exact observation in the source evidence bundle
   and `mapping-ledger.yaml`. Then decide whether it is authored/defaulted
   contract state, a planned or realized choice, an observation, or a derived
   interpretation. Schema compatibility alone does not authorize copying a
   captured value into SDL.

   Attempt to represent deliberate scenario requirements in RAES SDL.
   Use the most specific existing SDL surface available: nodes,
   infrastructure, services, features, content, accounts, relationships,
   agents, objectives, workflows, variables, or a contract surface if one
   already exists. The questions at this stage are "where can RAES preserve
   this fact exactly?" and, separately, "does the scenario author intend to
   require it?" Generated Docker network/endpoint IDs, generated DNS
   identities, health results, and scanner version/database/time/findings
   remain evidence by default. A deliberate promotion into SDL makes the value
   ordinary exact, constrained, or open contract state.
   Record the result in `mapping-ledger.yaml` instead of relying on prose.
   Each captured fact must have one of these dispositions:

   - `encoded` when current RAES can represent the fact directly;
   - `encoded_with_caveat` when current RAES can represent the fact but the
     later encoding issue must preserve a stated limitation;
   - `blocked_by_raes_gap` when RAES lacks a semantically correct surface;
   - `blocked_by_aptl_gap` when RAES can express the fact but APTL cannot yet
     realize or consume that SDL;
   - `needs_gap_triage` only as a temporary local state before filing or
     linking the required issue.

   The ledger itself is a schema-governed artifact. The current reference
   implementation is APTL's `aptl raes-inventory` CLI: `aptl raes-inventory
   schema` prints the current JSON Schema generated from the Pydantic model,
   and `aptl raes-inventory validate <asset-dir>` fails schema, evidence-path,
   and mapping-accountability violations.

11. Handle RAES gaps immediately.

   When a captured participant-discoverable fact cannot be fully expressed in
   RAES, search the RAES issue tracker for an existing issue that covers the
   missing expressivity. If an issue exists, record the evidence path and
   stop for discussion. If none exists, create a new RAES issue with:

   - the discovered fact or class of facts;
   - the in-range vantage point that can discover it;
   - the evidence path in the downstream bundle;
   - the RAES surfaces that were checked;
   - why those surfaces are insufficient;
   - the proposed RAES expressivity requirement.

   After linking or creating the issue, stop and discuss before continuing
   with additional gaps.

12. Publish a reproducibility bundle.

    The per-asset directory should include a README, `mapping-ledger.yaml`,
    raw evidence, the capture commands or script used to produce it, evidence
    checksums, focused tests that parse the evidence, and explicit notes on
    skipped or normalized steps. This supports ACM-style artifact review
    thinking: make the artifact available and evaluable, then be precise about
    which result claims it validates.

13. Plan correspondence checks.

    Methodology issues do not have to finish the RAES encoding, but they must
    define how later issues will prove correspondence between encoded RAES
    surfaces and realized downstream state. Record these checks in the
    ledger's `correspondence_checks` section. A check names the source surface,
    captured
    evidence, ledger fact IDs, method, status, and limit. Later encoding issues
    should turn planned checks into implemented checks that compare the encoded
    SDL/source package against fresh runtime evidence with explicit tolerances.
    This is the verification-and-validation layer for the inventory method: the
    ledger verifies evidence and mappings now, while later checks validate that
    the encoded model corresponds to the realized scenario asset.

## Tooling Baseline

The baseline intentionally avoids commercial and cloud-provider services.

Required local tools:

- Docker and Docker Compose for image, container, network, and volume
  inspection.
- `jq` and `yq` for structured JSON/YAML extraction.
- `sha256sum` or equivalent coreutils for evidence checksums.
- Trivy for image scanning, CycloneDX SBOM output, and vulnerability JSON.
- A downstream ledger validator. The current reference implementation is
  `aptl raes-inventory validate <asset-dir>` to validate the mapping ledger
  and its evidence references.
- `aptl raes-inventory gaps <asset-dir>` to list the RAES and downstream
  implementation issues later encoding work must resolve or consume.
- `aptl raes-inventory schema` to inspect the reference ledger schema.
- Docker Buildx `imagetools inspect`, build-time `--sbom`, and `--provenance`
  or equivalent in-toto/SLSA attestation tooling for provenance capture.

Useful optional tools:

- Syft for SBOM generation and Grype for an independent vulnerability scan.
- CycloneDX CLI or SPDX tooling for validating or converting SBOMs.
- Digest-pinned scanner container images when host binaries are absent or when
  a capture needs rerunnable tool identity independent of local package state.
- Cosign, notation, Rekor, or registry-native signature tooling when upstream
  images publish verifiable signatures/attestations.
- `osquery` for richer live asset inventory when containers include enough
  host support.
- `mtree`, AIDE, or Tripwire for stable filesystem manifests on larger
  assets.
- SCAP/OVAL tooling when the asset needs policy compliance checks instead
  of only package and vulnerability inventory.
- Reactor's citation MCP and Zotero translation-server for resolving
  primary literature by DOI during methodology work.

## Tested TechVault Validation Pass

The first proof pass captured `aptl-shuffle-backend` under
APTL's `docs/raes/inventory/shuffle-backend/`. It used an already-running
local lab rather than a destructive clean lab reset, so the output is method
evidence, not final SCN-010 acceptance evidence.

The pass proved that the method can capture an upstream-image asset with:

- immutable image identity and rootfs layer evidence;
- Compose service intent, static network identity, volume and bind-mount
  surfaces, and runtime process/listener baseline;
- OS package inventory and Go module manifests visible in the image;
- CycloneDX SBOM and Trivy vulnerability output;
- evidence checksums and pytest validation for capture-boundary handling,
  digest identity, SBOM structure, and severity-count consistency.

This proof pass is not yet a full maximal-discovery pass because it mostly
uses host-side Docker evidence plus a container runtime baseline. The next
pass must add in-range participant/agent discovery commands and then attempt
maximal RAES specification from the discovered facts.

Known limits are first-class methodology data, not prose footnotes. The
shuffle-backend ledger records that registry-visible in-toto/SLSA provenance
was captured but not cryptographically verified, that scanner output is
time-sensitive, and that correspondence checks are planned rather than
implemented in this methodology issue.

## Issue Breakdown Implication

APTL #330, #331, #332, and #353 were useful as a downstream per-asset
validation queue, but they should not define RAES methodology ownership or
drive cloning/spec/capture order by themselves. The method should land in RAES
first, then one upstream-image asset and one custom-build asset should exercise
it before a wave of RAES or downstream implementation gap issues is filed.

In practice:

- APTL #353 (`shuffle-backend`) is the first upstream-image proof case.
- APTL #331 (`db`) is a second upstream-image comparison point.
- APTL #330 (`webapp`) and #332 (`ad`) are custom-build cases that should
  decide whether source package capture needs more structure.
- RAES SDL encoding should happen as soon as a participant-discoverable fact
  is captured. Where RAES cannot express the fact, create or link the RAES
  gap issue and stop for discussion.

If those captures show that cloning/spec/capture need a different split,
the correction should be discussed before filing many downstream gap
issues.

## References

Primary literature:

- Yamin, Katt, and Gkioulos, "Cyber ranges and security testbeds:
  Scenarios, functions, tools and architecture", Computers & Security,
  2020. https://doi.org/10.1016/j.cose.2019.101636
- Peng, "Reproducible Research in Computational Science", Science, 2011.
  https://doi.org/10.1126/science.1213847
- Goodman, Fanelli, and Ioannidis, "What does research reproducibility
  mean?", Science Translational Medicine, 2016.
  https://doi.org/10.1126/scitranslmed.aaf5027
- Boettiger, "An introduction to Docker for reproducible research",
  ACM SIGOPS Operating Systems Review, 2015.
  https://doi.org/10.1145/2723872.2723882
- Grieves and Vickers, "Digital Twin: Mitigating Unpredictable,
  Undesirable Emergent Behavior in Complex Systems", 2017.
  https://doi.org/10.1007/978-3-319-38756-7_4
- Kritzinger et al., "Digital Twin in manufacturing: A categorical
  literature review and classification", IFAC-PapersOnLine, 2018.
  https://doi.org/10.1016/j.ifacol.2018.08.474

Open specifications and tool references:

- W3C PROV-DM: https://www.w3.org/TR/prov-dm/
- CycloneDX 1.6 JSON reference: https://cyclonedx.org/docs/1.6/json/
- SPDX specifications: https://spdx.dev/use/specifications/
- SLSA specification: https://slsa.dev/spec/latest/
- in-toto specification: https://github.com/in-toto/specification
- NIST SCAP releases and SP 800-126: https://csrc.nist.gov/projects/security-content-automation-protocol/scap-releases
- Trivy SBOM documentation: https://trivy.dev/docs/latest/guide/target/sbom/
- ACM artifact review and badging: https://www.acm.org/publications/policies/artifact-review-and-badging-current
