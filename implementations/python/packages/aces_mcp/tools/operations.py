"""Agent-facing SDL operation and claim-assessment tools.

These tools expose the parser, processor, planning, and claim-discipline
surfaces through MCP without requiring agents to import repository-local code.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from aces_mcp.tools.operation_support import (
    claim_assessment,
    compile_pipeline,
    design_notes,
    diagnostics,
    execution_plan_summary,
    has_errors,
    json_response,
    manifest_summary,
    runtime_model_summary,
    section_counts,
    size_error_payload,
    stage_error,
    stage_ok,
    text_diagnostics,
)


def register(mcp: FastMCP) -> None:
    """Register operation, assessment, and claim tools on the MCP server."""

    @mcp.tool(
        name="aces_tool_surface",
        description=(
            "Describe the ACES SDL MCP tool surface, recommended agent workflow, "
            "and safety boundaries. Start here when deciding which tool to call."
        ),
    )
    def aces_tool_surface() -> str:
        return json_response(
            {
                "surface": "aces-sdl",
                "intent": (
                    "Author, parse, validate, inspect, assess, and dry-run "
                    "ACES scenarios for researchers and range designers."
                ),
                "recommended_workflow": [
                    "sdl_overview",
                    "sdl_section_reference",
                    "sdl_scaffold or user-authored SDL",
                    "sdl_parse",
                    "sdl_validate",
                    "sdl_design_assessment",
                    "sdl_compile",
                    "sdl_plan",
                    "sdl_claims_assessment",
                ],
                "tool_families": {
                    "reference": [
                        "sdl_overview",
                        "sdl_section_reference",
                        "sdl_get_example",
                        "sdl_parser_reference",
                        "sdl_validation_reference",
                    ],
                    "authoring": [
                        "sdl_scaffold",
                        "sdl_validate",
                        "sdl_validate_section",
                        "sdl_instantiate",
                    ],
                    "parsing": ["sdl_parse"],
                    "inspection": [
                        "sdl_summarize",
                        "sdl_list_elements",
                        "sdl_get_element",
                        "sdl_check_references",
                        "sdl_diagram",
                    ],
                    "experiment_operations": [
                        "sdl_compile",
                        "sdl_plan",
                        "aces_reference_manifests",
                    ],
                    "assessment": [
                        "sdl_design_assessment",
                        "sdl_claims_assessment",
                    ],
                },
                "boundaries": [
                    (
                        "This surface helps design and assess scenarios; it does "
                        "not expose participant cyber actions such as scan, exploit, "
                        "SSH, command execution, or hidden-state access."
                    ),
                    (
                        "Planning is a dry-run against declared manifests. Actual "
                        "run claims require runtime results, evidence, and provenance."
                    ),
                    (
                        "Participant skill, causality, visibility, and evidence "
                        "claims require participant contracts and run evidence beyond "
                        "basic SDL validity."
                    ),
                ],
            }
        )

    @mcp.tool(
        name="sdl_parse",
        description=(
            "Parse SDL YAML and return a machine-readable JSON summary of the "
            "normalized scenario shape, populated sections, advisories, and "
            "optional semantic-validation status. This is useful before editing "
            "or deeper validation."
        ),
    )
    def sdl_parse(
        sdl_content: str,
        semantic_validation: bool = False,
    ) -> str:
        size_error = size_error_payload(sdl_content)
        if size_error is not None:
            return size_error

        from aces_sdl import SDLParseError, SDLValidationError, parse_sdl

        try:
            scenario = parse_sdl(
                sdl_content,
                skip_semantic_validation=not semantic_validation,
            )
        except SDLParseError as exc:
            return json_response(stage_error("parse", exc.details))
        except SDLValidationError as exc:
            return json_response(
                {
                    "status": "invalid",
                    "stage": "semantic_validation",
                    "diagnostics": text_diagnostics(
                        "semantic_validation",
                        exc.errors,
                        severity="error",
                    ),
                }
            )

        return json_response(
            {
                "status": "parsed",
                "semantic_validation": "performed" if semantic_validation else "skipped",
                "scenario": {
                    "name": scenario.name,
                    "description_present": bool(scenario.description),
                    "version": scenario.version,
                    "populated_sections": section_counts(scenario),
                    "advisories": list(scenario.advisories),
                },
            }
        )

    @mcp.tool(
        name="sdl_compile",
        description=(
            "Parse, semantically validate, instantiate, and compile SDL YAML "
            "into the ACES runtime model. Returns JSON with domain counts, "
            "participant-contract counts, and structured compiler diagnostics."
        ),
    )
    def sdl_compile(
        sdl_content: str,
        parameters_json: str = "{}",
    ) -> str:
        pipeline = compile_pipeline(sdl_content, parameters_json)
        if pipeline["error"] is not None:
            return json_response(pipeline["error"])

        model = pipeline["model"]
        return json_response(
            {
                "status": "compiled" if not has_errors(model.diagnostics) else "compiled_with_errors",
                "stages": pipeline["stages"],
                "scenario": {
                    "name": model.scenario_name,
                    "instantiation_parameters": pipeline["instantiation_parameters"],
                },
                "runtime_model": runtime_model_summary(model),
                "diagnostics": diagnostics(model.diagnostics, stage="compilation"),
            }
        )

    @mcp.tool(
        name="sdl_plan",
        description=(
            "Dry-run an ACES execution plan by parsing, validating, "
            "instantiating, compiling, and planning the scenario against the "
            "reference stub backend manifest. Returns JSON with resource and "
            "operation counts, capability diagnostics, and manifest identity. "
            "This does not start a live range."
        ),
    )
    def sdl_plan(
        sdl_content: str,
        parameters_json: str = "{}",
    ) -> str:
        pipeline = compile_pipeline(sdl_content, parameters_json)
        if pipeline["error"] is not None:
            return json_response(pipeline["error"])

        from aces_backend_stubs.stubs import create_stub_manifest
        from aces_processor.planner import plan

        manifest = create_stub_manifest()
        execution_plan = plan(pipeline["model"], manifest)
        return json_response(
            {
                "status": "planned" if execution_plan.is_valid else "planned_with_errors",
                "stages": [*pipeline["stages"], stage_ok("planning")],
                "scenario": {
                    "name": execution_plan.scenario_name,
                    "instantiation_parameters": pipeline["instantiation_parameters"],
                },
                "manifest": {
                    "backend": manifest.identity.name,
                    "version": manifest.identity.version,
                    "supported_contract_versions": sorted(manifest.supported_contract_versions),
                },
                "plan": execution_plan_summary(execution_plan),
                "diagnostics": diagnostics(execution_plan.diagnostics, stage="planning"),
                "claim_boundary": (
                    "This is a reference-manifest dry run. It supports capability "
                    "and planning claims, not claims that a live range actually ran."
                ),
            }
        )

    @mcp.tool(
        name="aces_reference_manifests",
        description=(
            "Return JSON summaries of the reference ACES processor manifest and "
            "reference stub backend manifest used by the MCP dry-run planning "
            "tools."
        ),
    )
    def aces_reference_manifests() -> str:
        from aces_backend_protocols.manifest import backend_manifest_payload
        from aces_backend_stubs.stubs import create_stub_manifest
        from aces_processor.manifest import reference_processor_manifest_payload

        backend = backend_manifest_payload(create_stub_manifest())
        processor = reference_processor_manifest_payload()
        return json_response(
            {
                "status": "ok",
                "processor": manifest_summary(processor),
                "backend": manifest_summary(backend),
            }
        )

    @mcp.tool(
        name="sdl_design_assessment",
        description=(
            "Assess a scenario design across authoring, validation, "
            "instantiation, compilation, and reference planning. Returns JSON "
            "with stage status, design notes, diagnostics, and next-step "
            "guidance for researchers and range designers."
        ),
    )
    def sdl_design_assessment(
        sdl_content: str,
        parameters_json: str = "{}",
    ) -> str:
        pipeline = compile_pipeline(sdl_content, parameters_json)
        if pipeline["error"] is not None:
            return json_response(pipeline["error"])

        from aces_backend_stubs.stubs import create_stub_manifest
        from aces_processor.planner import plan

        scenario = pipeline["scenario"]
        model = pipeline["model"]
        execution_plan = plan(model, create_stub_manifest())
        plan_diagnostics = execution_plan.diagnostics
        return json_response(
            {
                "status": "ready_for_review" if not has_errors(plan_diagnostics) else "needs_attention",
                "stages": [*pipeline["stages"], stage_ok("planning", detail="reference backend dry-run")],
                "scenario": {
                    "name": scenario.name,
                    "populated_sections": section_counts(scenario),
                    "instantiation_parameters": pipeline["instantiation_parameters"],
                },
                "runtime_model": runtime_model_summary(model),
                "plan": execution_plan_summary(execution_plan),
                "design_notes": design_notes(scenario, model, execution_plan),
                "diagnostics": diagnostics(plan_diagnostics, stage="assessment"),
            }
        )

    @mcp.tool(
        name="sdl_claims_assessment",
        description=(
            "Evaluate what claims a scenario can and cannot support. Returns "
            "JSON with supported claims, conditional claims, unsupported claims, "
            "and missing evidence/provenance needed for stronger research or "
            "range-design claims."
        ),
    )
    def sdl_claims_assessment(
        sdl_content: str,
        parameters_json: str = "{}",
    ) -> str:
        pipeline = compile_pipeline(sdl_content, parameters_json)
        if pipeline["error"] is not None:
            return json_response(pipeline["error"])

        from aces_backend_stubs.stubs import create_stub_manifest
        from aces_processor.planner import plan

        scenario = pipeline["scenario"]
        model = pipeline["model"]
        execution_plan = plan(model, create_stub_manifest())
        return json_response(
            {
                "status": "assessed",
                "scenario": {
                    "name": scenario.name,
                    "populated_sections": section_counts(scenario),
                },
                "claims": claim_assessment(scenario, model, execution_plan),
                "diagnostics": diagnostics(execution_plan.diagnostics, stage="claims"),
            }
        )
