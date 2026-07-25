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
verifiers, hidden assets, and trajectories. Behavioral-relation semantics are
now implemented as `aces-behavioral-relations@rev1`, while the stronger formal
relations it defines retain their honest unproved or future assurance states.

These profiles are scope contracts, not validators that silently strengthen
ordinary SDL parsing. They also do not certify a backend, an experiment result,
reproducibility, or behavioral equivalence.

## Use Through MCP

Agents using `raes-mcp` should call `raes_intended_use_profiles` before
authoring or making readiness claims. With no argument, the tool lists the five
profiles and their computed RAES delivery outcomes. Passing `profile_id`
returns the required concerns, current delivery status, evidence references,
limitations, blocking issue references, explicit nonclaims, and the existing
authoring tools relevant to that intended use.

For example:

```json
{"profile_id": "controlled-experiment-scenario"}
```

The result is an assessment of **what the current RAES ecosystem delivers**.
It deliberately reports `scenario_assessment.status` as `not-assessed`: the
tool does not inspect or certify a particular SDL document, experiment spec,
backend, or run. Authors use the result to choose the appropriate SDL and
`experiment_*` tools and to see which stronger claims remain blocked.
