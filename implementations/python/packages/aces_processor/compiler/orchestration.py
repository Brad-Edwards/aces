"""Orchestration-domain compilation: injects, events, scripts, stories."""

from aces_sdl.nodes import NodeType
from aces_sdl.scenario import InstantiatedScenario

from ..models import (
    AssertionRuntime,
    Diagnostic,
    EventRuntime,
    InjectBinding,
    InjectRuntime,
    RuntimeTemplate,
    ScriptRuntime,
    StoryRuntime,
)
from .addresses import (
    _assertion_address,
    _event_address,
    _inject_address,
    _inject_binding_address,
    _node_address,
    _script_address,
    _story_address,
)
from .ref_resolution import _resolve_named_refs, _resolve_resource_refs
from .support import _dedupe, _dump


def _compile_inject_runtimes(inject_templates: dict[str, RuntimeTemplate]) -> dict[str, InjectRuntime]:
    return {
        _inject_address(name): InjectRuntime(address=_inject_address(name), name=name, spec=template.spec)
        for name, template in inject_templates.items()
    }


def _compile_inject_bindings(
    scenario: InstantiatedScenario,
    inject_templates: dict[str, RuntimeTemplate],
    diagnostics: list[Diagnostic],
) -> dict[str, InjectBinding]:
    inject_bindings: dict[str, InjectBinding] = {}
    for node_name, node in scenario.nodes.items():
        if node.type != NodeType.VM:
            continue
        node_addr = _node_address(node_name)
        for inject_name, role_name in node.injects.items():
            template = inject_templates.get(inject_name)
            if template is None:
                diagnostics.append(
                    Diagnostic(
                        code="orchestration.inject-template-ref-unbound",
                        domain="orchestration",
                        address=node_addr,
                        message=(
                            f"Inject binding '{inject_name}' on node '{node_name}' "
                            "does not resolve to a declared inject template."
                        ),
                    )
                )
                continue
            inject_address = _inject_address(inject_name)
            address = _inject_binding_address(node_name, inject_name)
            inject_bindings[address] = InjectBinding(
                address=address,
                name=inject_name,
                node_name=node_name,
                node_address=node_addr,
                inject_name=inject_name,
                template_address=template.address,
                role_name=role_name,
                ordering_dependencies=(inject_address,),
                refresh_dependencies=(node_addr, inject_address),
                spec={"binding": {"node": node_name, "role": role_name}, "inject_address": inject_address},
            )
    return inject_bindings


def _compile_events(
    scenario: InstantiatedScenario,
    assertions: dict[str, AssertionRuntime],
    injects: dict[str, InjectRuntime],
    inject_bindings: dict[str, InjectBinding],
    diagnostics: list[Diagnostic],
) -> dict[str, EventRuntime]:
    events: dict[str, EventRuntime] = {}
    for name, event in scenario.events.items():
        event_address = _event_address(name)
        assertion_names = list(event.assertions)
        inject_names = list(event.injects)
        assertion_addresses, assertion_diagnostics = _resolve_named_refs(
            ref_names=assertion_names,
            available_names={assertion.name for assertion in assertions.values()},
            address_builder=_assertion_address,
            owner_address=event_address,
            domain="orchestration",
            code_prefix="orchestration.assertion-ref",
            resource_label="assertion",
        )
        inject_addresses, inject_diagnostics = _resolve_resource_refs(
            injects,
            ref_names=inject_names,
            owner_address=event_address,
            domain="orchestration",
            code_prefix="orchestration.inject-ref",
            resource_label="inject",
        )
        diagnostics.extend(assertion_diagnostics)
        diagnostics.extend(inject_diagnostics)
        inject_binding_ordering_dependencies = [
            address for address, binding in inject_bindings.items() if binding.inject_name in inject_names
        ]
        events[event_address] = EventRuntime(
            address=event_address,
            name=name,
            assertion_names=tuple(assertion_names),
            assertion_addresses=assertion_addresses,
            inject_names=tuple(inject_names),
            inject_addresses=inject_addresses,
            ordering_dependencies=_dedupe([*inject_addresses, *inject_binding_ordering_dependencies]),
            refresh_dependencies=_dedupe(
                [*assertion_addresses, *inject_addresses, *inject_binding_ordering_dependencies]
            ),
            spec=_dump(event),
        )
    return events


def _compile_scripts(
    scenario: InstantiatedScenario,
    diagnostics: list[Diagnostic],
) -> dict[str, ScriptRuntime]:
    scripts: dict[str, ScriptRuntime] = {}
    for name, script in scenario.scripts.items():
        script_address = _script_address(name)
        event_addresses, script_diagnostics = _resolve_named_refs(
            ref_names=list(script.events),
            available_names=set(scenario.events),
            address_builder=_event_address,
            owner_address=script_address,
            domain="orchestration",
            code_prefix="orchestration.event-ref",
            resource_label="event",
        )
        diagnostics.extend(script_diagnostics)
        scripts[script_address] = ScriptRuntime(
            address=script_address,
            name=name,
            event_addresses=event_addresses,
            ordering_dependencies=event_addresses,
            refresh_dependencies=event_addresses,
            spec=_dump(script),
        )
    return scripts


def _compile_stories(
    scenario: InstantiatedScenario,
    diagnostics: list[Diagnostic],
) -> dict[str, StoryRuntime]:
    stories: dict[str, StoryRuntime] = {}
    for name, story in scenario.stories.items():
        story_address = _story_address(name)
        script_addresses, story_diagnostics = _resolve_named_refs(
            ref_names=list(story.scripts),
            available_names=set(scenario.scripts),
            address_builder=_script_address,
            owner_address=story_address,
            domain="orchestration",
            code_prefix="orchestration.script-ref",
            resource_label="script",
        )
        diagnostics.extend(story_diagnostics)
        stories[story_address] = StoryRuntime(
            address=story_address,
            name=name,
            script_addresses=script_addresses,
            ordering_dependencies=script_addresses,
            refresh_dependencies=script_addresses,
            spec=_dump(story),
        )
    return stories
