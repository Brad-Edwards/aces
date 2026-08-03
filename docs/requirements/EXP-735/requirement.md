---
id: EXP-735
title: "Fidelity Mode And Transferability Disclosure"
status: DRAFT
type: NON_FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-05-18T04:25:36.059277Z
updated_at: 2026-05-18T04:25:36.059277Z
---

# EXP-735 — Fidelity Mode And Transferability Disclosure

## Statement

The ecosystem shall define machine-readable fidelity-mode and transferability-disclosure surfaces that distinguish simulated, emulated, live, synthetic, real-observed, augmented, and mixed evidence or execution modes for scenarios, backends, runs, observations, and benchmark claims.

## Rationale

Evidence gate #165 tests whether fidelity and sim-to-real transfer claims are evidence-bound. Existing provenance, realization, observability, and time requirements provide adjacent surfaces, but none explicitly requires a governed fidelity-mode taxonomy or transferability disclosure sufficient to prevent backend-specific or synthetic evidence from being promoted as live-realistic evaluation evidence.
