"""SDL authoring tool registrations — validate, scaffold, and instantiate scenarios."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ._helpers import _section_summary
from ._templates import _SCAFFOLD_FULL, _SCAFFOLD_MINIMAL, _SCAFFOLD_STANDARD

# Maximum input size to prevent resource exhaustion via YAML bombs or
# extremely large payloads.  64 KiB accommodates the largest bundled
# example (~750 lines / ~25 KiB) with generous headroom.
_MAX_INPUT_BYTES = 64 * 1024


def register(mcp: FastMCP) -> None:
    """Register SDL authoring tools on the MCP server."""

    @mcp.tool(
        name="sdl_validate",
        description=(
            "Parse and validate SDL YAML content.  Returns either a success "
            "confirmation (with advisories if any) or a structured list of "
            "every error found — parse errors, structural errors, and semantic "
            "validation errors.  All errors are collected before reporting so "
            "you see every issue at once.\n\n"
            "Pass the full YAML scenario text as `sdl_content`.  Optionally "
            "set `structural_only=true` to skip semantic cross-reference "
            "checks (useful for work-in-progress fragments that aren't "
            "complete yet). Set `accept_migration_syntax=true` only when "
            "migrating legacy field spellings; canonical validation is strict."
        ),
    )
    def sdl_validate(
        sdl_content: str,
        structural_only: bool = False,
        accept_migration_syntax: bool = False,
    ) -> str:
        if len(sdl_content.encode("utf-8", errors="replace")) > _MAX_INPUT_BYTES:
            return f"INPUT TOO LARGE — limit is {_MAX_INPUT_BYTES} bytes."

        from raes import (
            SDLMigrationPolicy,
            SDLParseError,
            SDLValidationError,
            parse_sdl,
        )

        try:
            scenario = parse_sdl(
                sdl_content,
                skip_semantic_validation=structural_only,
                migration_policy=(SDLMigrationPolicy.ACCEPT if accept_migration_syntax else SDLMigrationPolicy.REJECT),
            )
        except SDLParseError as exc:
            return (
                "PARSE ERROR — the YAML could not be loaded or the "
                "structure does not match the SDL schema.\n\n"
                f"Details:\n{exc.details}"
            )
        except SDLValidationError as exc:
            header = (
                f"VALIDATION ERRORS — {len(exc.errors)} semantic issue{'s' if len(exc.errors) != 1 else ''} found.\n\n"
            )
            bullets = "\n".join(f"  - {e}" for e in exc.errors)
            return header + bullets

        # Success path
        parts = [f"VALID — scenario '{scenario.name}' parsed successfully."]

        # Summary
        section_counts = _section_summary(scenario)
        if section_counts:
            parts.append("\nSections populated:")
            for sec, count in section_counts:
                parts.append(f"  {sec}: {count} element{'s' if count != 1 else ''}")

        if scenario.advisories:
            parts.append(f"\nAdvisories ({len(scenario.advisories)}):")
            for adv in scenario.advisories:
                parts.append(f"  - {adv}")

        if scenario.source_diagnostics:
            parts.append(f"\nSource migration advisories ({len(scenario.source_diagnostics)}):")
            for diagnostic in scenario.source_diagnostics:
                start = diagnostic.primary_range.start
                parts.append(f"  - [{diagnostic.code}] line {start.line}, column {start.column}: {diagnostic.message}")

        if structural_only:
            parts.append(
                "\nNote: semantic validation was skipped. Run without "
                "`structural_only` for full cross-reference checking."
            )

        return "\n".join(parts)

    @mcp.tool(
        name="sdl_validate_section",
        description=(
            "Validate a single SDL section fragment by wrapping it in a "
            "minimal scenario context.  Useful when you are building a "
            "scenario piece by piece and want to check one section's syntax "
            "before assembling the whole document.\n\n"
            "Pass the section name (e.g. 'nodes', 'features') and the YAML "
            "content for that section.  Optionally provide `context_yaml` — "
            "additional SDL YAML sections needed to satisfy cross-references "
            "(e.g. nodes referenced by infrastructure).  Structural "
            "validation is always performed; semantic validation runs only "
            "when `context_yaml` is provided."
        ),
    )
    def sdl_validate_section(
        section: str,
        section_yaml: str,
        context_yaml: str = "",
    ) -> str:
        combined_size = len(section_yaml.encode("utf-8", errors="replace")) + len(
            context_yaml.encode("utf-8", errors="replace")
        )
        if combined_size > _MAX_INPUT_BYTES:
            return f"INPUT TOO LARGE — limit is {_MAX_INPUT_BYTES} bytes."

        import yaml as _yaml
        from raes import SDLParseError, SDLValidationError, load_sdl_fragment, parse_sdl

        section = section.strip().lower().replace("-", "_")
        valid_sections = {
            "nodes",
            "infrastructure",
            "features",
            "conditions",
            "vulnerabilities",
            "entities",
            "injects",
            "events",
            "scripts",
            "stories",
            "content",
            "accounts",
            "relationships",
            "agents",
            "objectives",
            "workflows",
            "variables",
        }
        if section not in valid_sections:
            return f"Unknown section '{section}'. Valid sections: {', '.join(sorted(valid_sections))}"

        # Build a minimal valid wrapper
        try:
            section_data = load_sdl_fragment(
                section_yaml,
                mapping_keys="literal",
                base_pointer=f"/{section}",
            )
        except SDLParseError as exc:
            label = "PARSE ERROR" if any(item.code != "sdl.parse" for item in exc.diagnostics) else "YAML ERROR"
            return f"{label} in section content:\n{exc.details}"

        wrapper: dict = {}
        if context_yaml:
            try:
                ctx = load_sdl_fragment(context_yaml)
                if isinstance(ctx, dict):
                    wrapper.update(ctx)
            except SDLParseError as exc:
                label = "PARSE ERROR" if any(item.code != "sdl.parse" for item in exc.diagnostics) else "YAML ERROR"
                return f"{label} in context_yaml:\n{exc.details}"

        # Force a safe synthetic name — always last so context_yaml cannot
        # override it and cause confusing error messages.
        wrapper["name"] = "mcp-validation-fragment"
        wrapper[section] = section_data
        combined = _yaml.dump(wrapper, default_flow_style=False, sort_keys=False)

        skip_semantic = not bool(context_yaml)
        try:
            parse_sdl(combined, skip_semantic_validation=skip_semantic)
        except SDLParseError as exc:
            return f"PARSE ERROR in '{section}' section:\n{exc.details}"
        except SDLValidationError as exc:
            header = f"VALIDATION ERRORS in '{section}' section ({len(exc.errors)}):\n"
            bullets = "\n".join(f"  - {e}" for e in exc.errors)
            return header + bullets

        mode = "structural" if skip_semantic else "structural + semantic"
        return f"VALID — '{section}' section passes {mode} validation."

    @mcp.tool(
        name="sdl_scaffold",
        description=(
            "Generate a starter SDL scenario skeleton.  Choose a complexity "
            "level: 'minimal' (topology + features only), 'standard' "
            "(adds objectives, entities, accounts), or 'full' (all sections "
            "with placeholder structure).  Optionally provide a scenario name "
            "and description.  The output is valid SDL YAML you can edit."
        ),
    )
    def sdl_scaffold(
        complexity: str = "standard",
        scenario_name: str = "my-scenario",
        description: str = "A new SDL scenario",
    ) -> str:
        key = complexity.lower().strip()
        if key not in ("minimal", "standard", "full"):
            return "Invalid complexity. Choose: 'minimal', 'standard', or 'full'."

        templates = {
            "minimal": _SCAFFOLD_MINIMAL,
            "standard": _SCAFFOLD_STANDARD,
            "full": _SCAFFOLD_FULL,
        }
        # Use Template-style substitution instead of str.format() to
        # avoid crashes or unexpected behaviour when user-provided
        # scenario_name/description contain { or } characters.
        return templates[key].replace("{name}", scenario_name).replace("{desc}", description)

    @mcp.tool(
        name="sdl_instantiate",
        description=(
            "Instantiate a parameterized SDL scenario by substituting "
            "concrete values for ${var} placeholders.  Pass the SDL YAML and "
            "a JSON-formatted dictionary of parameter values.  Returns the "
            "fully resolved scenario summary or detailed errors if "
            "instantiation fails."
        ),
    )
    def sdl_instantiate(
        sdl_content: str,
        parameters_json: str = "{}",
    ) -> str:
        combined_size = len(sdl_content.encode("utf-8", errors="replace")) + len(
            parameters_json.encode("utf-8", errors="replace")
        )
        if combined_size > _MAX_INPUT_BYTES:
            return f"INPUT TOO LARGE — limit is {_MAX_INPUT_BYTES} bytes."

        import json

        from raes import (
            SDLInstantiationError,
            SDLParseError,
            SDLValidationError,
            instantiate_scenario,
            parse_sdl,
        )

        try:
            params = json.loads(parameters_json)
        except json.JSONDecodeError as exc:
            return f"Invalid JSON in parameters_json: {exc}"
        if not isinstance(params, dict):
            return "parameters_json must be a JSON object (dictionary)."

        try:
            scenario = parse_sdl(sdl_content)
        except SDLParseError as exc:
            return f"PARSE ERROR:\n{exc.details}"
        except SDLValidationError as exc:
            bullets = "\n".join(f"  - {e}" for e in exc.errors)
            return f"VALIDATION ERRORS:\n{bullets}"

        try:
            concrete = instantiate_scenario(scenario, parameters=params)
        except SDLInstantiationError as exc:
            bullets = "\n".join(f"  - {e}" for e in exc.errors)
            return f"INSTANTIATION ERRORS ({len(exc.errors)}):\n{bullets}"

        binding_count = len(concrete.instantiation_provenance.bindings) + sum(
            len(item.bindings) for item in concrete.instantiation_provenance.imports
        )
        parts = [
            f"INSTANTIATED - scenario '{concrete.name}' fully resolved.",
            f"Bindings resolved: {binding_count}",
        ]
        section_counts = _section_summary(concrete)
        if section_counts:
            parts.append("\nSections:")
            for sec, count in section_counts:
                parts.append(f"  {sec}: {count}")
        return "\n".join(parts)
