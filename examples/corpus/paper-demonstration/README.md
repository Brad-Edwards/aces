# Paper Demonstration Corpus (n=2 backend participant evidence)

This corpus is the ACES paper's **n=2 backend demonstration**: the same authored
reference scenario, `examples/scenarios/paper-agent-loop.sdl.yaml`
(`paper-enterprise-participant-evidence-loop`), realized on two independent
emulation backends — the **ACES libvirt reference backend** and **APTL** — compared
through an inspectable **cross-backend invariant ledger**.

The claim is a system-boundary claim, not a performance claim: authored SDL,
processor output, backend realization, participant runtime, episode/observation
history, evaluator/Wazuh evidence, and outcome interpretation stay separable and
auditable across backends. It is not a leaderboard, a benchmark, or an equivalence
proof.

## Artifact

- `paper-demonstration-corpus.json` — schema `aces.paper-demonstration-corpus/v1`.
  A thin **local** corpus artifact (not a published contract) composed from existing
  ACES surfaces. It records, for each backend run, the authored scenario
  identity/digest, compiled ACES address sets, backend id + capability profile,
  topology basis + network-attachment matrix, per-surface evidence coverage, and
  disclosed limitations; then it derives the four-section invariant ledger.

### Invariant ledger sections

- `preserved_invariants` — facts held identical across both backends (authored
  scenario `sha256:` digest, compiled ACES address sets, recorded evidence
  surfaces), each annotated with the per-backend **basis** so an external summary is
  never shown as an independently verified fact.
- `realization_differences` — where the realizations legitimately differ (substrate:
  libvirt VM/network appliances vs. APTL Docker/Compose containers; participant
  proof: deterministic-structural vs. live; defensive evidence; evidence provenance;
  evidence-source mode).
- `unsupported_or_degraded_surfaces` — per-backend capability gaps / degradations.
- `evidence_limitations` — the union of both runs' disclosed limitations.

## The two backend runs

- **libvirt-reference** (`evidence_provenance: generated-in-repo`): a real
  `aces.libvirt.paper-evidence-run/v1` run (issue #615), consumed through the
  existing producer/validator in **deterministic** mode (no libvirt daemon; the CI
  default). Only portable, timestamp-free fields cross into the corpus, so this
  committed corpus is byte-stable; the full timestamped evidence lives in the
  regenerable libvirt run archive.
- **aptl-docker** (`evidence_provenance: external-summarized`): a bounded summary of
  the publicly documented APTL realization plus a link to the APTL evidence issue
  `Brad-Edwards/aptl#558`. **The in-repo APTL entry is a summary, not the literal
  APTL run** — APTL lives in a separate repository and ACES imports no APTL-private
  schemas, container ids, Compose names, Docker inspect payloads, or raw Wazuh rule
  bodies. Byte-level confirmation of the shared scenario digest against the APTL
  export is external to this repository.

  To finalize the pairing with the **real** APTL evidence, supply the aptl#558 export
  (or its redacted portable projection) via `--aptl-evidence`; the producer reads
  only allowlisted portable fields (scenario digest, compiled address sets,
  evidence-source mode, limitations) and marks the entry `external-artifact-summarized`.
  A supplied export whose scenario digest differs from the authored scenario fails
  the build (the pairing would not be n=2 over the same authored scenario).

## Regenerating

```sh
# Default (documented-shape APTL summary + link), from the repo root:
aces corpus build

# With a real operator-supplied APTL evidence export:
aces corpus build --aptl-evidence /path/to/aptl-558-export.json
```

The build is deterministic; `tests/test_paper_corpus.py::test_committed_corpus_matches_fresh_build`
guards this committed artifact against drift.

## Non-claims

- No autonomous-agent capability benchmark claim.
- No claim that Wazuh detection quality is evaluated.
- No model-defense robustness claim.
- No full semantic equivalence across backends beyond the checked invariant ledger.

## Links

- Issue: `Brad-Edwards/aces#600`
- Authored scenario: `Brad-Edwards/aces#598` (`examples/scenarios/paper-agent-loop.sdl.yaml`)
- Libvirt participant runtime: `Brad-Edwards/aces#614`
- Libvirt paper evidence: `Brad-Edwards/aces#615`
- APTL evidence: `Brad-Edwards/aptl#558`
- Design guardrails: `docs/decisions/issue-600-paper-demonstration-corpus-preflight.md`
