# Developer package and artifact management

This is the design set for [issue #1168](https://github.com/OpenRAE/rae/issues/1168)
and [milestone 69](https://github.com/OpenRAE/rae/milestone/69). It is proposed
for maintainer acceptance. It does not claim that its migration is implemented.

Read the documents in this order:

1. [ADR-105: architecture decision](../adrs/adr-105-developer-package-and-artifact-management.md)
   and [ADR-106: promotion and release admission](../adrs/adr-106-artifact-promotion-and-release-admission.md).
2. [Repository inventory](inventory.md): concrete sources, gaps, owners and boundaries.
3. [Decision matrix](decision-matrix.md): solution classes and selection rationale.
4. [Architecture](architecture.md): authority, clients, profiles, trust and state models.
5. [Operations and acceptance](operations.md): qualification, recovery and ownership.
6. [Migration and issue graph](migration.md): implementation order and incumbent disposition.

The inventory was taken at `5d2f738f`, the `dev` tip on 2026-09-05. GitHub issue
and PR states were read that day. Existing code is evidence of current
behavior; statements using “must” describe the proposed target. Acceptance of
the design and completion of the implementation program are separate events.

The design concerns repository development, verification and publication.
It does not redefine SDL, reusable scenario/module semantics, or backend
workload acquisition. Existing GOV-913 supply-chain and GOV-928 release
governance inform the design without transferring runtime semantic authority
to a development lockfile.
