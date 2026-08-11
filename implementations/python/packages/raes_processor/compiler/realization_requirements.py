"""Realization-requirement compilation (SEM-218)."""

from raes.explicitness import ExplicitnessClass, ExplicitnessProvenance
from raes.identifiers import QualifiedName
from raes.nodes import NodeType
from raes.realization_designation import resolve_realization_designation
from raes.runtime_resource_limits import (
    RuntimeProcessResourceLimit,
    process_resource_limit_identity_digest,
)
from raes.scenario import InstantiatedScenario
from raes.semantics.domain_topology import (
    DomainTopologyAnalysis,
)
from raes_contracts.planning import RealizationAuthorityMode, RealizationResolutionSource
from raes_contracts.vocabulary import ProcessResourceLimitScope

from ..semantics.realization import (
    REALIZATION_DOMAIN,
    CompiledRealizationAuthority,
    CompiledRealizationRequirement,
    ProcessResourceLimitDemand,
    RealizationValueConstraint,
    registered_realization_concern_descriptors,
)
from ..semantics.realization_concerns import CONCERN_PAYLOAD_PATH, RegisteredRealizationConcern
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

    _append_resource_source_artifact_requirements(requirements, scenario)
    _append_bound_source_artifact_requirements(requirements, scenario)
    _append_action_source_artifact_requirements(requirements, scenario)


def _append_resource_source_artifact_requirements(
    requirements: list[CompiledRealizationRequirement],
    scenario: InstantiatedScenario,
) -> None:
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


def _append_bound_source_artifact_requirements(
    requirements: list[CompiledRealizationRequirement],
    scenario: InstantiatedScenario,
) -> None:
    for node_name, node in scenario.nodes.items():
        _append_feature_source_artifact_requirements(requirements, scenario, node_name, node.features)
        _append_condition_source_artifact_requirements(requirements, scenario, node_name, node.conditions)


def _append_feature_source_artifact_requirements(
    requirements: list[CompiledRealizationRequirement],
    scenario: InstantiatedScenario,
    node_name: str,
    feature_names: list[str],
) -> None:
    for feature_name in feature_names:
        feature = scenario.features.get(feature_name)
        if feature is not None and feature.source is not None:
            _append_source_artifact_requirement(
                requirements,
                source=feature.source,
                field_path=f"features.{feature_name}.source.artifact_requirement",
                address=_feature_binding_address(node_name, feature_name),
                governing_scope=f"#/features/{feature_name}/source/artifact_requirement",
            )


def _append_condition_source_artifact_requirements(
    requirements: list[CompiledRealizationRequirement],
    scenario: InstantiatedScenario,
    node_name: str,
    condition_names: list[str],
) -> None:
    for condition_name in condition_names:
        condition = scenario.conditions.get(condition_name)
        if condition is not None and condition.source is not None:
            _append_source_artifact_requirement(
                requirements,
                source=condition.source,
                field_path=f"conditions.{condition_name}.source.artifact_requirement",
                address=_condition_binding_address(node_name, condition_name),
                governing_scope=f"#/conditions/{condition_name}/source/artifact_requirement",
            )


def _append_action_source_artifact_requirements(
    requirements: list[CompiledRealizationRequirement],
    scenario: InstantiatedScenario,
) -> None:
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


def _nested_authored_value(source: object, path: tuple[str, ...]) -> object:
    current = source
    for token in path:
        if current is None:
            return None
        current = getattr(current, token, None)
    return current


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
        binding = content.service_materialization
        if binding is None:
            continue
        requirement_kind = (
            "service-search-index-schema-materialization"
            if binding.interface_profile == "service-search-index-schema"
            else "service-content-materialization"
        )
        requirements.append(
            CompiledRealizationRequirement(
                field_path=f"content.{name}.service_materialization",
                address=_content_address(name),
                domain=REALIZATION_DOMAIN,
                requirement_kind=requirement_kind,
                explicitness=ExplicitnessClass.EXACT,
                provenance=ExplicitnessProvenance.AUTHOR_DECLARED,
                governing_scope=f"#/content/{name}/service_materialization",
            )
        )


def _compiled_registered_realization(
    scenario: InstantiatedScenario,
    registered: RegisteredRealizationConcern,
) -> tuple[CompiledRealizationRequirement | None, CompiledRealizationAuthority | None]:
    descriptor = registered.descriptor
    section_name = descriptor.section
    declaration_name = registered.declaration_name
    encoded_name = declaration_name.replace("~", "~0").replace("/", "~1")
    field_pointer = f"/{section_name}/{encoded_name}/{'/'.join(descriptor.authored_path)}"
    record = scenario.explicitness.get(registered.field_path)
    declarations = getattr(scenario, section_name)
    authored_value = _nested_authored_value(
        declarations[declaration_name],
        descriptor.authored_path,
    )
    value_constraints: tuple[RealizationValueConstraint, ...] = ()
    process_resource_limits: tuple[ProcessResourceLimitDemand, ...] = ()
    if descriptor.concern_kind == "process-resource-limits":
        value_constraints, process_resource_limits = _compiled_process_resource_limits(
            scenario,
            field_pointer=field_pointer,
            authored_value=authored_value,
        )
    if record is not None and not descriptor.includes_authored_value(authored_value):
        return None, None
    if record is not None:
        explicitness = record.classification
        provenance = record.provenance
        governing_scope = f"#{field_pointer}"
        delegated = False
        mode = RealizationAuthorityMode(explicitness.value)
        source = (
            RealizationResolutionSource.PROCESSOR_DERIVED
            if provenance is ExplicitnessProvenance.PROCESSOR_DERIVED
            else RealizationResolutionSource.AUTHORED_LEAF
        )
    else:
        resolution = resolve_realization_designation(
            scenario.instantiation_provenance.realization_designations,
            field_pointer=field_pointer,
            owner_namespace=QualifiedName.parse(declaration_name).parts[:-1],
        )
        closed = resolution.closure is not None and resolution.closure.value == "closed-world"
        explicitness = (
            ExplicitnessClass.OPEN
            if resolution.closure is not None and resolution.closure.value == "open-world"
            else None
        )
        provenance = ExplicitnessProvenance.AUTHOR_DECLARED
        governing_scope = resolution.governing_scope
        delegated = resolution.delegated
        mode = RealizationAuthorityMode.CLOSED if closed else RealizationAuthorityMode.OPEN
        source = {
            "scope": RealizationResolutionSource.AUTHORED_SCOPE,
            "apparatus-default": RealizationResolutionSource.APPARATUS_DEFAULT,
            "legacy-default": RealizationResolutionSource.LEGACY_DEFAULT,
        }[resolution.source]
    address = _realization_requirement_address(
        scenario,
        section_name=section_name,
        declaration_name=declaration_name,
    )
    authority = CompiledRealizationAuthority(
        field_path=registered.field_path,
        address=address,
        domain=REALIZATION_DOMAIN,
        requirement_kind=descriptor.concern_kind,
        payload_path=descriptor.payload_path,
        mode=mode,
        source=source,
        provenance=provenance,
        governing_scope=governing_scope,
        delegated=delegated,
        verification_scope=descriptor.required_verification_scope(authored_value),
        required_observation_strength=descriptor.required_observation_strength(),
    )
    if explicitness is None and not delegated:
        return None, authority
    requirement = CompiledRealizationRequirement(
        field_path=registered.field_path,
        address=address,
        domain=REALIZATION_DOMAIN,
        requirement_kind=descriptor.concern_kind,
        explicitness=explicitness,
        provenance=provenance,
        governing_scope=governing_scope,
        delegated=delegated,
        verification_scope=descriptor.required_verification_scope(authored_value),
        required_observation_strength=descriptor.required_observation_strength(),
        value_constraints=value_constraints,
        process_resource_limits=process_resource_limits,
    )
    return requirement, authority


def _compiled_process_resource_limits(
    scenario: InstantiatedScenario,
    *,
    field_pointer: str,
    authored_value: object,
) -> tuple[tuple[RealizationValueConstraint, ...], tuple[ProcessResourceLimitDemand, ...]]:
    limits = tuple(authored_value) if isinstance(authored_value, list) else ()
    typed_limits = tuple(
        value if isinstance(value, RuntimeProcessResourceLimit) else RuntimeProcessResourceLimit.model_validate(value)
        for value in limits
    )
    constraints: list[RealizationValueConstraint] = []
    prefix = f"{field_pointer}/"
    for constraint in scenario.instantiation_provenance.capability_constraints:
        if not constraint.field_pointer.startswith(prefix):
            continue
        suffix = constraint.field_pointer.removeprefix(prefix).split("/")
        if len(suffix) != 2 or not suffix[0].isdigit() or suffix[1] not in {"soft", "hard"}:
            continue
        index = int(suffix[0])
        if index >= len(typed_limits):
            continue
        constraints.append(
            RealizationValueConstraint(
                identity_digest=process_resource_limit_identity_digest(typed_limits[index]),
                leaf=suffix[1],
                parameter=constraint.parameter,
                allowed_values=constraint.allowed_values,
            )
        )
    demands = tuple(
        ProcessResourceLimitDemand(
            identity_digest=process_resource_limit_identity_digest(value),
            resource=value.resource,
            scope=ProcessResourceLimitScope(value.scope.value),
            soft=value.soft,
            hard=value.hard,
        )
        for value in typed_limits
    )
    return tuple(constraints), demands


def _compile_realization(
    scenario: InstantiatedScenario,
    domain_analysis: DomainTopologyAnalysis,
) -> tuple[tuple[CompiledRealizationRequirement, ...], tuple[CompiledRealizationAuthority, ...]]:
    """SEM-218 typed compiler emission: lower each authored realization concern
    into a compiled requirement carrying its classifier explicitness class.

    Explicit leaves always win. Missing admitted concerns are lowered through
    the typed lexical designation cascade; omitted designation preserves the
    legacy closed fallback while explicit root delegation remains typed.
    """

    requirements: list[CompiledRealizationRequirement] = []
    authority: list[CompiledRealizationAuthority] = []
    for registered in registered_realization_concern_descriptors(
        declaration_names={"nodes": scenario.nodes, "content": scenario.content}
    ):
        requirement, authority_entry = _compiled_registered_realization(scenario, registered)
        if requirement is not None:
            requirements.append(requirement)
        if authority_entry is not None:
            authority.append(authority_entry)
    _append_domain_topology_requirements(requirements, domain_analysis)
    _append_stateful_resource_requirements(requirements, scenario)
    _append_service_materialization_requirements(requirements, scenario)
    _append_source_artifact_requirements(requirements, scenario)
    existing = {(entry.address, entry.field_path, entry.requirement_kind) for entry in authority}
    authority.extend(
        CompiledRealizationAuthority(
            field_path=requirement.field_path,
            address=requirement.address,
            domain=requirement.domain,
            requirement_kind=requirement.requirement_kind,
            payload_path=CONCERN_PAYLOAD_PATH[requirement.requirement_kind],
            mode=RealizationAuthorityMode.EXACT,
            source=RealizationResolutionSource.PROCESSOR_DERIVED,
            provenance=requirement.provenance,
            governing_scope=requirement.governing_scope,
            verification_scope=requirement.verification_scope,
            required_observation_strength=requirement.required_observation_strength,
        )
        for requirement in requirements
        if requirement.requirement_kind in CONCERN_PAYLOAD_PATH
        if (requirement.address, requirement.field_path, requirement.requirement_kind) not in existing
    )
    return tuple(requirements), tuple(authority)


def _compile_realization_requirements(
    scenario: InstantiatedScenario,
    domain_analysis: DomainTopologyAnalysis,
) -> tuple[CompiledRealizationRequirement, ...]:
    """Compatibility view over the SEM-218 realization demand graph."""

    return _compile_realization(scenario, domain_analysis)[0]
