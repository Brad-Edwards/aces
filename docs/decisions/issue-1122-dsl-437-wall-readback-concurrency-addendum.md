# Issue 1122 Wall-Readback Concurrency Addendum

Date: 2026-08-12

Issue: #1122. Requirement: DSL-437. Related: #861.

## Gap And Existing Surface

The DSL-437 wall-driver regression assumed that a real-time clock remained at
absolute tick zero after `RuntimeManager.apply()` started its driver. Under
contention, the driver may validly advance before a reader acquires the shared
participant-execution lock. The incumbent lock, time-runtime readback, snapshot,
and wall-driver surfaces are sufficient; this is a test-oracle defect, not a
new runtime semantic or public contract.

## Decision

A blocked-read concurrency check binds its result to the full predecessor
`TimeCoordinateModel` captured for that critical section. The test holds the
runtime read inside the shared lock, captures the predecessor snapshot, waits
longer than one wall tick, and proves that the manager snapshot remains
unchanged. After release, the returned segment, tick, and microstep must equal
the captured predecessor coordinate.

This evidence does not assert absolute tick zero. A valid wall advance before
the blocked read is outside the critical section being tested and cannot make
the result fail. An advance during the read still changes the snapshot or
returned coordinate and fails deterministically.

## Alternatives And Verification

Retaining `tick == 0` was rejected because scheduler contention can invalidate
that unrelated timing assumption. Sleeping less or increasing the tick period
only changes the race probability. Injecting a private test clock was rejected
because the existing predecessor snapshot is the canonical shared-time state
cut and no runtime hook is required.

Verification runs the focused blocked-read test repeatedly under CPython 3.14
free-threaded contention, the surrounding DSL-437 wall-driver tests, Ruff, and
the DSL-437 requirement and repository policy gates.
