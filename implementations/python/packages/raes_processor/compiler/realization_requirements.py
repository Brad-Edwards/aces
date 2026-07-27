"""Realization-requirement compilation (SEM-218)."""

from raes.explicitness import ExplicitnessClass, ExplicitnessProvenance
from raes.identifiers import QualifiedName
from raes.nodes import NodeType
from raes.realization_designation import resolve_realization_designation
from raes.scenario import InstantiatedScenario
from raes.semantics.domain_topology import (
    DomainTopologyAnalysis,
)

from ..semantics.realization import (
    REALIZATION_DOMAIN,
    CompiledRealizationRequirement,
    registered_realization_concerns,
)
from .addresses import (
    _account_address,
    _condition_binding_address,
    _content_address,
    _domain_controller_address,
    _event_address,
    _feature_binding_address,
    _generated_artifact_address,
    _inject_address,
    _network_address,
    _node_address,
    _persistent_volume_address,
)


def _append_source_artifact_requirement(
    requirements: list[CompiledRealizationRequirement],
    *,
    source: object,
    field_path: str,
    address: str,
    governing_scope: str,
) -> None:
    artifact_requirement = getattr(source, "artifact_requirement", None)
    if artifact_requirement is None:
        return
    requirements.append(
        CompiledRealizationRequirement(
            field_path=field_path,
            address=address,
            domain=REALIZATION_DOMAIN,
            requirement_kind="source-artifact",
            explicitness=artifact_requirement.explicitness,
            provenance=ExplicitnessProvenance.AUTHOR_DECLARED,
            governing_scope=governing_scope,
            artifact_requirement=artifact_requirement,
        )
    )


def _append_source_artifact_requirements(
    requirements: list[CompiledRealizationRequirement],
    scenario: InstantiatedScenario,
) -> None:
    """Lower every realized ``Source`` carrier into the existing demand graph."""

    for name, node in scenario.nodes.items():
        if node.source is not None:
            _append_source_artifact_requirement(
                requirements,
                source=node.source,
                field_path=f"nodes.{name}.source.artifact_requirement",
                address=_network_address(name) if node.type == NodeType.SWITCH else _node_address(name),
                governing_scope=f"#/nodes/{name}/source/artifact_requirement",
            )
    for name, content in scenario.content.items():
        if content.source is not None:
            _append_source_artifact_requirement(
                requirements,
                source=content.source,
                field_path=f"content.{name}.source.artifact_requirement",
                address=_content_address(name),
                governing_scope=f"#/content/{name}/source/artifact_requirement",
            )
    for node_name, node in scenario.nodes.items():
        for feature_name in node.features:
            feature = scenario.features.get(feature_name)
            if feature is not None and feature.source is not None:
                _append_source_artifact_requirement(
                    requirements,
                    source=feature.source,
                    field_path=f"features.{feature_name}.source.artifact_requirement",
                    address=_feature_binding_address(node_name, feature_name),
                    governing_scope=f"#/features/{feature_name}/source/artifact_requirement",
                )
        for condition_name in node.conditions:
            condition = scenario.conditions.get(condition_name)
            if condition is not None and condition.source is not None:
                _append_source_artifact_requirement(
                    requirements,
                    source=condition.source,
                    field_path=f"conditions.{condition_name}.source.artifact_requirement",
                    address=_condition_binding_address(node_name, condition_name),
                    governing_scope=f"#/conditions/{condition_name}/source/artifact_requirement",
                )
    for section, declarations, address_factory in (
        ("injects", scenario.injects, _inject_address),
        ("events", scenario.events, _event_address),
    ):
        for name, declaration in declarations.items():
            if declaration.source is not None:
                _append_source_artifact_requirement(
                    requirements,
                    source=declaration.source,
                    field_path=f"{section}.{name}.source.artifact_requirement",
                    address=address_factory(name),
                    governing_scope=f"#/{section}/{name}/source/artifact_requirement",
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
    _append_source_artifact_requirements(requirements, scenario)
    return tuple(requirements)
