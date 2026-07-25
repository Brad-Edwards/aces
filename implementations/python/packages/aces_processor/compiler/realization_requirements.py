"""Realization-requirement compilation (SEM-218)."""

from aces_sdl.explicitness import ExplicitnessClass, ExplicitnessProvenance
from aces_sdl.identifiers import QualifiedName
from aces_sdl.nodes import NodeType
from aces_sdl.realization_designation import resolve_realization_designation
from aces_sdl.scenario import InstantiatedScenario
from aces_sdl.semantics.domain_topology import (
    DomainTopologyAnalysis,
)

from ..semantics.realization import (
    REALIZATION_DOMAIN,
    CompiledRealizationRequirement,
    registered_realization_concerns,
)
from .addresses import (
    _account_address,
    _content_address,
    _domain_controller_address,
    _generated_artifact_address,
    _network_address,
    _node_address,
    _persistent_volume_address,
)


def _realization_requirement_address(
    scenario: InstantiatedScenario,
    *,
    section_name: str,
    declaration_name: str,
) -> str:
    """Resolve the compiled resource address for a realization-concern path."""

    if section_name == "nodes" and declaration_name in scenario.nodes:
        node = scenario.nodes[declaration_name]
        return _network_address(declaration_name) if node.type == NodeType.SWITCH else _node_address(declaration_name)
    if section_name == "content" and declaration_name in scenario.content:
        return _content_address(declaration_name)
    raise ValueError("realization concern must resolve to one compiled resource address")


def _append_domain_topology_requirements(
    requirements: list[CompiledRealizationRequirement],
    domain_analysis: DomainTopologyAnalysis,
) -> None:
    """Append processor-derived requirements for domain-bound resources."""

    domain_carriers = [
        *(
            (_node_address(node_name), binding.domain_name)
            for node_name, binding in domain_analysis.node_bindings.items()
        ),
        *(
            (_account_address(account_name), binding.domain_name)
            for account_name, binding in domain_analysis.account_bindings.items()
        ),
        *(
            (_domain_controller_address(node_name, binding.domain_name), binding.domain_name)
            for node_name, binding in domain_analysis.node_bindings.items()
            if binding.role.value == "controller"
        ),
    ]
    for address, domain_name in domain_carriers:
        requirements.append(
            CompiledRealizationRequirement(
                field_path=f"identity_domains.{domain_name}.topology",
                address=address,
                domain=REALIZATION_DOMAIN,
                requirement_kind="domain-topology",
                explicitness=ExplicitnessClass.EXACT,
                provenance=ExplicitnessProvenance.PROCESSOR_DERIVED,
            )
        )


def _append_stateful_resource_requirements(
    requirements: list[CompiledRealizationRequirement],
    scenario: InstantiatedScenario,
) -> None:
    """Append exact requirements for authored stateful resources."""

    for section_name, resources, address_factory, requirement_kind in (
        (
            "generated_artifacts",
            scenario.generated_artifacts,
            _generated_artifact_address,
            "generated-artifact",
        ),
        (
            "persistent_volumes",
            scenario.persistent_volumes,
            _persistent_volume_address,
            "persistent-volume",
        ),
    ):
        for name in resources:
            requirements.append(
                CompiledRealizationRequirement(
                    field_path=f"{section_name}.{name}",
                    address=address_factory(name),
                    domain=REALIZATION_DOMAIN,
                    requirement_kind=requirement_kind,
                    explicitness=ExplicitnessClass.EXACT,
                    provenance=ExplicitnessProvenance.AUTHOR_DECLARED,
                    governing_scope=f"#/{section_name}/{name}",
                )
            )


def _append_service_materialization_requirements(
    requirements: list[CompiledRealizationRequirement],
    scenario: InstantiatedScenario,
) -> None:
    for name, content in scenario.content.items():
        if content.service_materialization is None:
            continue
        requirements.append(
            CompiledRealizationRequirement(
                field_path=f"content.{name}.service_materialization",
                address=_content_address(name),
                domain=REALIZATION_DOMAIN,
                requirement_kind="service-content-materialization",
                explicitness=ExplicitnessClass.EXACT,
                provenance=ExplicitnessProvenance.AUTHOR_DECLARED,
                governing_scope=f"#/content/{name}/service_materialization",
            )
        )


def _compile_realization_requirements(
    scenario: InstantiatedScenario,
    domain_analysis: DomainTopologyAnalysis,
) -> tuple[CompiledRealizationRequirement, ...]:
    """SEM-218 typed compiler emission: lower each authored realization concern
    into a compiled requirement carrying its classifier explicitness class.

    Explicit leaves always win. Missing admitted concerns are lowered through
    the typed lexical designation cascade; omitted designation preserves the
    legacy closed fallback while explicit root delegation remains typed.
    """

    requirements: list[CompiledRealizationRequirement] = []
    explicitness = scenario.explicitness
    for section_name, declaration_name, field_name, concern_kind in registered_realization_concerns(
        declaration_names={"nodes": scenario.nodes, "content": scenario.content}
    ):
        field_path = f"{section_name}.{declaration_name}.{field_name}"
        encoded_name = declaration_name.replace("~", "~0").replace("/", "~1")
        field_pointer = f"/{section_name}/{encoded_name}/{field_name}"
        owner_namespace = QualifiedName.parse(declaration_name).parts[:-1]
        record = explicitness.get(field_path)
        if record is None:
            resolution = resolve_realization_designation(
                scenario.instantiation_provenance.realization_designations,
                field_pointer=field_pointer,
                owner_namespace=owner_namespace,
            )
            if resolution.source == "legacy-default" or (
                resolution.closure is not None
                and resolution.closure.value == "closed-world"
                and not resolution.delegated
            ):
                continue
            requirement_explicitness = (
                ExplicitnessClass.OPEN
                if resolution.closure is not None and resolution.closure.value == "open-world"
                else None
            )
            provenance = ExplicitnessProvenance.AUTHOR_DECLARED
            governing_scope = resolution.governing_scope
            delegated = resolution.delegated
        else:
            requirement_explicitness = record.classification
            provenance = record.provenance
            governing_scope = f"#{field_pointer}"
            delegated = False
        requirements.append(
            CompiledRealizationRequirement(
                field_path=field_path,
                address=_realization_requirement_address(
                    scenario,
                    section_name=section_name,
                    declaration_name=declaration_name,
                ),
                domain=REALIZATION_DOMAIN,
                requirement_kind=concern_kind,
                explicitness=requirement_explicitness,
                provenance=provenance,
                governing_scope=governing_scope,
                delegated=delegated,
            )
        )
    _append_domain_topology_requirements(requirements, domain_analysis)
    _append_stateful_resource_requirements(requirements, scenario)
    _append_service_materialization_requirements(requirements, scenario)
    return tuple(requirements)
