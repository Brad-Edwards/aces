"""SDL inspection tool registrations — analyze, query, and summarize parsed scenarios."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ._common import _parse_or_error
from ._elements import _get_element_detail, _list_elements
from ._references import _build_diagram, _element_references, _full_reference_graph
from ._summary import _build_summary


def register(mcp: FastMCP) -> None:
    """Register SDL inspection/query tools on the MCP server."""

    @mcp.tool(
        name="sdl_summarize",
        description=(
            "Parse an SDL YAML scenario and return a structured summary: "
            "scenario name/description, which sections are populated, element "
            "counts, variables defined, entities hierarchy, and high-level "
            "topology stats (compute count, switch count, network links).  "
            "Useful for getting a quick understanding of an existing scenario."
        ),
    )
    def sdl_summarize(sdl_content: str) -> str:
        scenario = _parse_or_error(sdl_content)
        if isinstance(scenario, str):
            return scenario
        return _build_summary(scenario)

    @mcp.tool(
        name="sdl_list_elements",
        description=(
            "List all named elements in a parsed SDL scenario, optionally "
            "filtered by section.  Returns element names grouped by section.  "
            "Pass `section` to filter (e.g. 'nodes', 'accounts').  "
            "Pass `section='all'` or omit it to list everything."
        ),
    )
    def sdl_list_elements(
        sdl_content: str,
        section: str = "all",
    ) -> str:
        scenario = _parse_or_error(sdl_content)
        if isinstance(scenario, str):
            return scenario
        return _list_elements(scenario, section.lower().strip())

    @mcp.tool(
        name="sdl_get_element",
        description=(
            "Get detailed information about a specific named element in a "
            "scenario.  Use a bare name like 'web-server' or a qualified "
            "ref like 'nodes.web-server'.  Returns all fields, references "
            "to/from this element, and related context."
        ),
    )
    def sdl_get_element(
        sdl_content: str,
        element_name: str,
    ) -> str:
        scenario = _parse_or_error(sdl_content)
        if isinstance(scenario, str):
            return scenario
        return _get_element_detail(scenario, element_name.strip())

    @mcp.tool(
        name="sdl_check_references",
        description=(
            "Analyze cross-references in a scenario.  For a given element "
            "name, shows what it references (outgoing) and what references "
            "it (incoming).  Helps understand dependency chains and "
            "connectivity.  If no element_name is given, returns a full "
            "reference graph summary."
        ),
    )
    def sdl_check_references(
        sdl_content: str,
        element_name: str = "",
    ) -> str:
        scenario = _parse_or_error(sdl_content)
        if isinstance(scenario, str):
            return scenario
        if element_name.strip():
            return _element_references(scenario, element_name.strip())
        return _full_reference_graph(scenario)

    @mcp.tool(
        name="sdl_diagram",
        description=(
            "Generate an ASCII topology diagram of the scenario's network "
            "layout showing switches, compute nodes connected to each switch, and "
            "inter-node dependencies.  Useful for visualizing the scenario "
            "structure."
        ),
    )
    def sdl_diagram(sdl_content: str) -> str:
        scenario = _parse_or_error(sdl_content)
        if isinstance(scenario, str):
            return scenario
        return _build_diagram(scenario)
