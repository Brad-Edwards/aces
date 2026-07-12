# Scientific-Scenario Completeness

An SDL document can be valid without being ready for deployment or scientific
use. REV1 makes that distinction inspectable through five intended-use
profiles, from a valid fragment through a reproducible benchmark/study input.

The normative
{download}`scientific-scenario completeness specification <../../../specs/sdl/scientific-scenario-completeness.md>`
defines the computation and links the canonical taxonomy and delivery
assessment. The complete concern matrix lives in those machine-readable
artifacts rather than being copied into this guide.

The current assessment is deliberately conservative. Only
`valid-sdl-fragment` is complete. The four stronger profiles expose their
blocking concerns directly, including authored/observed-state binding,
specificity, teardown, credentials, time and clocks, participant budgets,
verifiers, hidden assets, trajectories, and behavioral-relation semantics.

These profiles are scope contracts, not validators that silently strengthen
ordinary SDL parsing. They also do not certify a backend, an experiment result,
reproducibility, or behavioral equivalence.
