---
id: GOV-943
title: "Concept-Authority Companion-Spec Extraction (Ground Control Convergence)"
status: DRAFT
type: FUNCTIONAL
priority: SHOULD
wave: 3
created_at: 2026-07-17T15:30:00.027755Z
updated_at: 2026-07-17T15:30:00.027755Z
---

# GOV-943 — Concept-Authority Companion-Spec Extraction (Ground Control Convergence)

## Statement

When ACES SEM-200 (Shared Semantic Integrity) reaches ACTIVE and both ACES and Ground Control operate their concept-family sets, the shared concept-authority metamodel — concept families, artifact bindings, provenance classes (declared/derived/observed), the closed external-effect vocabulary (annotates/aligns/refines/constrains), typed declared-vs-observed reconciliation deltas, and evidence-versus-derived-measure semantics — shall be extracted into a companion specification that both products consume as domain packs, such that catalog convergence is a merge of catalogs rather than a rewrite. This requirement remains DRAFT until SEM-200 is ACTIVE; the SEM-200 ACTIVE transition is the explicit gate for undertaking the extraction, and no companion-spec extraction is undertaken before that gate.

## Rationale

Ground Control ADR-084 §4 records the align-now/converge-later decision with ACES: a versioned ACES concept-family crosswalk ships now on the Ground Control side (GC issue #1310, contracts/ontology/crosswalks/aces-concept-families-v1.json, pinned to aces-sdl==0.23.0 under the closed effect vocabulary), with companion-spec extraction as the stated trajectory gated on SEM-200 reaching ACTIVE. Filing the convergence target in the aces-sdl requirements graph makes the trajectory visible on both sides. This extends the existing ACES concept-authority governance — external knowledge binding governance (GOV-907), cross-artifact concept binding (GOV-918), extension discipline over shared concept authorities (GOV-919), and controlled vocabularies (GOV-922) — toward a shared metamodel both products consume, rather than restating any of them.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `835` (GOV-943 companion-spec extraction / GC convergence (aces #835))
