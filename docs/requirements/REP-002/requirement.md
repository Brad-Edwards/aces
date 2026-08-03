---
id: REP-002
title: "Adapters monorepo standup with Ground Control onboarding and strict SonarCloud"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 4
created_at: 2026-07-01T17:48:10.308769Z
updated_at: 2026-07-04T02:32:46.085890Z
---

# REP-002 — Adapters monorepo standup with Ground Control onboarding and strict SonarCloud

## Statement

The adapters-monorepo repository shall be established as a monorepo of isolated per-simulator adapter projects (each with its own lockfile/environment) plus a shared sim-adapter base package and backend conformance harness, with a per-adapter CI matrix so incompatible simulator dependency stacks cannot gate one another. The repository shall be fully onboarded to Ground Control: .ground-control.yaml (project registration, workflow/verify/lint/format commands, sonarcloud config, requirement governance), ADR directory, towncrier changelog, nox verify graph, pre-commit hooks, and main+dev branch protection. It shall be configured with a strict SonarCloud quality profile mirroring the raes raes-strict gate (fails on any new issue; qualitygate.wait enabled; new-code coverage, duplication, rating, and security-hotspot conditions), using the raes repository itself as the reference configuration.

## Rationale

Amortizes the expensive Ground Control onboarding and strict-Sonar setup across all future sim adapters (CybORG first, others later) in one governed repo, while keeping per-adapter dependency isolation. Mandated standup issue.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `636` (REP-002 — Adapters monorepo standup with Ground Control onboarding and strict SonarCloud)
