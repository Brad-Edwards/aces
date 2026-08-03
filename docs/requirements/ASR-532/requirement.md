---
id: ASR-532
title: "Adversarial Backend Conformance Targets"
status: DRAFT
type: NON_FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-05-18T04:25:47.598518Z
updated_at: 2026-05-18T04:25:47.598518Z
---

# ASR-532 — Adversarial Backend Conformance Targets

## Statement

The backend conformance suite shall include adversarial and dishonest-backend targets that deliberately overclaim, underperform, omit required state, return malformed envelopes, ignore supported operations, or publish conflicting manifest/profile declarations, and the suite shall require specific diagnostics for each failure class.

## Rationale

Evidence gate #158 tests whether conformance falsifies dishonest or incomplete backend claims. Existing ASR-502 conformance coverage provides the fixture corpus and runner foundation, but the gap analysis found no explicit requirement that conformance include adversarial backend implementations and false-positive prevention cases beyond schema/profile fixture validation.
