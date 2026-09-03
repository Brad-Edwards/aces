# Issue 1105 / RUN-314 Guest Service Protocol Certification

Date: 2026-08-11

Issue: #1105. Requirements: RUN-314 and ASR-519. Related: #714 and #717.

## Decision

Guest-certified libvirt realization admits only TCP service placements until a
native UDP implementation and probe are available. Admission rejects every
other protocol before native mutation. The admitted `tcp` value is then carried
through the runtime-domain projection, deterministic guest artifact, listener
startup and inspection, line-oriented guest fact, parsed observation, and
plan-derived expected projection.

Certification compares name, protocol, port, listener state, and process state.
Missing or different protocol evidence is a mismatch; a TCP listener cannot
stand in for requested UDP behavior. This keeps the implementation honest while
preserving the incumbent default-TCP authoring behavior.

## Nonclaims and Alternatives

This change does not implement or claim UDP service realization. Treating a
generic `netstat` port match as protocol evidence was rejected because TCP and
UDP can share a port. Inferring protocol solely from the plan was rejected
because certification must bind the plan to an independently reported guest
fact.

## Verification

Tests cover UDP admission rejection, default and explicit TCP admission,
protocol-preserving runtime projection and boot payload, strict guest-fact
parsing, TCP-specific listener inspection, exact observation matching, and
wrong or missing protocol evidence. The focused guest-certified, TechVault
honesty, and native prerequisite suites remain required.
