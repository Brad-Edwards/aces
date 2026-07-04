# Issue 670 — Rename paper-* identifiers to functional names

Date: 2026-07-05

Issue: #670.

Requirement: none. Mechanical rename + relocation; the GitHub issue is the contract.

## Context

The reference scenario and its evidence/corpus surfaces (issues #598/#614/#615/#600)
were named `paper-*`. That is a problem for an open-source repo: there is more than
one paper in the research program, and "paper" is meaningless to a downstream
consumer. These are reusable ACES capabilities — a reference enterprise scenario, a
per-backend evidence-run producer, and a cross-backend invariant-ledger/corpus
builder — not artifacts of a single publication. Research framing lives in the
research program; the ACES repo should name the mechanism by what it does.

## Decision

- Rename `paper-*` to functional names across code, tests, the scenario, artifact
  envelope ids, and the CLI. See the issue for the full name map. Key results:
  scenario `enterprise-participant-evidence-loop`; producer
  `aces_operations.libvirt_evidence_run` → `aces.libvirt.scenario-evidence-run/v1`;
  corpus `aces_operations.cross_backend_corpus` → `aces.cross-backend-evidence-corpus/v1`;
  CLI `aces libvirt evidence validate` (`aces corpus build` unchanged).
- No published `contracts/schemas/` are touched; the two envelope ids are local
  artifact wrappers, not published contracts.
- Historical decision notes (`issue-598/600/615-*-preflight.md`) keep their dated
  filenames as records; only their live references were left pointing at the real
  paths.
- Move the *research result* out of ACES: the committed demonstration corpus is
  removed; ACES keeps the producer, and the canonical published corpus lives in the
  public `Brad-Edwards/research` repo (`aoe/aces/a11-research-instrument/`). The
  drift test becomes a build-determinism smoke test.

## Non-goals

- No behavior change to the producers or the ledger computation.
- No new published schema, and no renaming of the historical decision-note files.
