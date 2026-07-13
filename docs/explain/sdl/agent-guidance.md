# Agent Guidance Profile

ACES exposes a machine-readable guidance profile for agents and operators. The
profile gives agents stable rule ids for scope boundaries, invariants, review
priorities, and safe-operating expectations.

The canonical artifact is
`specs/agent-guidance/agent-guidance.yaml`. The MCP tool
`aces_agent_guidance` returns that profile as JSON so an agent can consume it
without scraping prose.

## What Users Get

Before this profile, agent guidance was split across repository instructions,
MCP tool descriptions, ADRs, policy files, and explanatory docs. An agent could
read those sources, but it had no single structured payload that said what
boundaries and review rules apply before authoring or operating against ACES
SDL.

With the guidance profile, users get:

- stable ids for scope and safety rules agents can cite in plans or reviews
- a shared contributor/operator vocabulary for what ACES tools can and cannot
  do
- source references back to the docs, ADRs, policy files, and code that ground
  each rule
- an audience filter for contributor-focused and operator-focused guidance
- an explicit rule that valid SDL is only the valid-fragment completeness
  profile, not evidence of deployability or scientific adequacy

The profile is not a permission system and does not execute SDL. It is a
read-only guidance surface.

## MCP Tool

Call `aces_agent_guidance` after `aces_tool_surface` and before an agent starts
authoring, dry-run planning, or making claims about a scenario.

The tool accepts:

- `audience`: `all`, `contributor`, or `operator`

It returns JSON with:

- `scope_boundaries`
- `invariants`
- `review_priorities`
- `safe_operating_expectations`

Each entry has a stable `id`, an `audience`, a list of `surfaces`, a
`statement`, and `source_refs`.

Example response shape:

```json
{
  "status": "ok",
  "audience": "operator",
  "profile": "aces-agent-guidance",
  "version": 1,
  "requirement_refs": ["AUT-811"],
  "guidance": {
    "scope_boundaries": [
      {
        "id": "sdl-authoring-not-execution",
        "audience": ["contributor", "operator"],
        "surfaces": ["mcp", "sdl", "processor"],
        "statement": "...",
        "source_refs": ["..."]
      }
    ]
  }
}
```

## Operating Loop

A conservative agent workflow is:

1. Call `aces_tool_surface` to discover the available tool families.
2. Call `aces_agent_guidance` for current boundaries and review priorities.
3. Call `aces_intended_use_profiles` to select the intended claim scope and
   inspect current ACES delivery blockers.
4. Use `sdl_overview` and `sdl_section_reference` for SDL structure.
5. Use language-service tools for small edits and diagnostics.
6. Use `sdl_validate`, `sdl_design_assessment`, `sdl_plan`, and
   `sdl_claims_assessment` before returning claims about readiness,
   portability, execution, or evidence.

The guidance profile keeps the "what should I check?" part of that loop
machine-readable, while the existing SDL tools perform parsing, validation,
formatting, dry-run planning, and claim assessment.

## Validation

`tools/check_agent_guidance.py` validates the profile shape. The policy gate
runs it through the nox policy graph, so CI fails if the profile drops a
required category, uses an unknown audience, duplicates an id, or omits source
references.

This checker is structural. It does not prove every rule is complete. It keeps
the profile consumable and prevents prompt-only guidance drift.
