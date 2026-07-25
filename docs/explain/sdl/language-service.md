# SDL Language-Service Tools

RAES exposes SDL-aware language-service helpers for agents and editor-like
authoring surfaces. These helpers sit above raw YAML editing: they reuse the
same parser, normalizer, semantic validator, and SDL symbol model as the rest
of the repository.

The result is an authoring loop where an agent can ask what is valid at a
location, make a path-addressed edit, reformat the document, and inspect
structured diagnostics before handing the SDL back to a user.

## What Users Get

Before these helpers, agents could read SDL reference material, edit YAML text,
and run validation afterward. They had to infer reference targets and rewrite
larger YAML blocks by hand.

With the language-service surface, agents can:

- request valid section keys, field names, and cross-reference candidates
- find where an SDL symbol is defined and where it is used
- format SDL through the repository's normalized YAML shape
- receive parse and semantic errors as structured diagnostic records
- apply `set`, `delete`, and `append` edits by JSON pointer and immediately
  revalidate the result

This does not make the agent a production backend or scenario generator. It
gives the agent safer primitives for authoring and repairing SDL documents.

## MCP Tools

The MCP server exposes these operations as the `language_service` tool family.
Start with `raes_tool_surface` to discover the full server workflow, then use
these tools while authoring:

| Tool | Use it for |
|------|------------|
| `sdl_completions` | Suggest top-level SDL keys, section fields, or reference targets at a JSON-pointer-like location. |
| `sdl_references` | Locate definitions and occurrences for a bare or qualified SDL symbol. |
| `sdl_format` | Normalize SDL YAML formatting and return diagnostics from the formatted content. |
| `sdl_diagnostics` | Return parse, structural, and semantic validation errors as structured JSON records. |
| `sdl_apply_edit` | Apply a `set`, `delete`, or `append` edit at a JSON pointer and return revalidated SDL. |

The tools return JSON strings so agents can consume the result without scraping
human prose.

## Authoring Workflow

A typical agent workflow is:

1. Use `sdl_completions` before adding or changing a reference-heavy field.
2. Use `sdl_apply_edit` for a minimal path-addressed mutation.
3. Use `sdl_diagnostics` to check parse and semantic validity.
4. Use `sdl_format` before returning or storing the SDL.
5. Use `sdl_references` before renames or reference-sensitive edits.

For example, if a user asks an agent to connect `web` to `net2`, the agent can
append `net2` to `/infrastructure/web/links`, revalidate, and format the SDL
instead of rewriting the whole `infrastructure` block.

## Completions

`sdl_completions` accepts:

- `sdl_content`: the SDL YAML string
- `cursor_path`: a JSON-pointer-like location such as `/`,
  `/nodes/web/features`, or `/objectives/red-access/success/conditions`
- `prefix`: an optional label prefix filter

Completion contexts include:

- top-level SDL keys
- known fields for SDL sections
- reference targets such as features, conditions, entities,
  accounts, objectives, and workflow steps
- generic target fields that can refer to more than one section

Example MCP call:

```json
{
  "sdl_content": "name: demo\nfeatures:\n  app: {type: Service, source: webapp}\nnodes:\n  web: {type: VM, os: linux, resources: {ram: 2 GiB, cpu: 1}}\n",
  "cursor_path": "/nodes/web/features",
  "prefix": "a"
}
```

The response has this shape:

```json
{
  "status": "ok",
  "context": "reference:features",
  "items": [
    {
      "label": "app",
      "kind": "reference",
      "detail": "features.app",
      "insert_text": "app"
    }
  ]
}
```

## References

`sdl_references` accepts a bare symbol such as `app` or a qualified symbol such
as `features.app`.

Use qualified symbols when two sections use the same name. For example,
`features.app` should match the feature definition and feature references, not
an unrelated `conditions.app` definition.

The response includes:

- `definitions`: symbol definitions with qualified names, paths, and ranges
- `occurrences`: mapping-key or scalar occurrences with paths and ranges

## Formatting

`sdl_format` parses SDL, applies the repository's normalization rules, emits
YAML with stable key ordering, and then returns diagnostics from the formatted
content.

Formatting can return:

- `formatted` when the formatted document has no diagnostics
- `formatted_with_diagnostics` when formatting succeeded but semantic
  diagnostics remain
- `invalid` when the original SDL cannot be parsed

## Diagnostics

`sdl_diagnostics` returns structured diagnostic records:

```json
{
  "status": "invalid",
  "stage": "semantic_validation",
  "diagnostics": [
    {
      "stage": "semantic_validation",
      "severity": "error",
      "code": "sdl.semantic",
      "message": "..."
    }
  ]
}
```

Common codes include:

- `sdl.parse` for YAML, normalization, or structural model errors
- `sdl.semantic` for cross-reference and semantic validator errors
- `sdl.input_too_large` when the SDL payload exceeds the language-service
  input limit
- `sdl.edit` for invalid structured edit requests

Set `semantic_validation` to `false` when an agent needs parse-only feedback
during early drafting. Parse-only success does not mean the SDL is semantically
valid.

## Structured Edits

`sdl_apply_edit` applies one JSON-pointer-addressed edit, serializes the result,
and returns diagnostics from the edited SDL.

Supported operations:

| Operation | Behavior |
|-----------|----------|
| `set` | Replace a value at the pointer. Missing mapping segments are created. The empty pointer replaces the whole document. |
| `delete` | Delete a mapping key or list item. |
| `append` | Append a value to the list at the pointer. |

The MCP tool receives `value_json` for `set` and `append`, so string values must
be JSON strings:

```json
{
  "sdl_content": "...",
  "operation": "append",
  "pointer": "/infrastructure/web/links",
  "value_json": "\"net2\""
}
```

The Python helper receives the already-decoded `value`:

```python
from aces_sdl.language_service import apply_structured_edit

result = apply_structured_edit(
    sdl_content,
    operation="append",
    pointer="/infrastructure/web/links",
    value="net2",
)
```

Structured edits are intentionally small. For broad scenario rewrites, make a
sequence of small edits and validate after each meaningful step.

## Python Helpers

The MCP tools wrap the editor-agnostic helpers in
`aces_sdl.language_service`:

```python
from aces_sdl.language_service import (
    apply_structured_edit,
    language_completions,
    language_diagnostics,
    language_format,
    language_references,
)
```

These helpers return plain dictionaries so CLIs, MCP tools, and future editor
adapters can share the same behavior.
