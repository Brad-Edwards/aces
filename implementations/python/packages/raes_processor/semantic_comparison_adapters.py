"""Trusted owner adapters for semantic comparison."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from pydantic import BaseModel
from raes.phase_contracts import ResolvedImportProvenance
from raes.scenario import Scenario
from raes_contracts.canonical import canonical_json_digest
from raes_contracts.contracts import (
    ExperimentCaptureSpecModel,
    ExperimentRunModel,
    ExperimentStudyModel,
    ExperimentTaskModel,
    ExternalConceptBindingDocumentModel,
)
from raes_contracts.semantic_comparison import (
    ArtifactCoordinate,
    EvidenceSpecificationCoordinateModel,
    ExactRepresentationModel,
    ExternalConceptBindingsCoordinateModel,
    ImpactClosureStatus,
    ImpactScopeModel,
    ModuleCoordinateModel,
    RunCoordinateModel,
    ScenarioCoordinateModel,
    SemanticComparisonProfileModel,
    StudyCoordinateModel,
    TaskCoordinateModel,
    canonical_impact_scope_digest,
)

from .semantic_comparison_projections import (
    _owner_semantic_payload,
    _owner_structural_payload,
    _study_member_semantics,
    _without_editorial_description,
)

AdmittedArtifact: TypeAlias = (
    Scenario
    | ResolvedImportProvenance
    | ExperimentTaskModel
    | ExperimentRunModel
    | ExperimentCaptureSpecModel
    | ExperimentStudyModel
    | ExternalConceptBindingDocumentModel
)


@dataclass(frozen=True)
class _Subject:
    identity: str
    representation_digest: str | None
    structural_digest: str | None
    semantic_digest: str | None
    structural_profile: str
    semantic_profile: str


@dataclass(frozen=True)
class _Dependency:
    dependent_identity: str
    dependency_identity: str
    rule_id: str
    provenance_digest: str


@dataclass(frozen=True)
class _Projection:
    coordinate: ArtifactCoordinate
    subjects: tuple[_Subject, ...]
    dependencies: tuple[_Dependency, ...]


def coordinate_for_artifact(
    artifact: AdmittedArtifact,
    *,
    exact_representation: ExactRepresentationModel | None = None,
) -> ArtifactCoordinate:
    """Derive a closed owner-specific coordinate from an admitted typed artifact."""

    digest = _artifact_digest(artifact)
    common = {
        "canonical_digest": digest,
        "exact_representation": exact_representation,
    }
    if type(artifact) is Scenario:
        return ScenarioCoordinateModel(
            canonical_identity=f"scenario:{artifact.name}",
            canonicalization_profile="raes-canonical-sdl/v1",
            scenario_id=artifact.name,
            scenario_version=artifact.version,
            **common,
        )
    if type(artifact) is ResolvedImportProvenance:
        return ModuleCoordinateModel(
            canonical_identity=f"module:{artifact.module_id}",
            canonicalization_profile="rfc8785-jcs-sha256/v1",
            module_id=artifact.module_id,
            module_version=artifact.module_version,
            **common,
        )
    if type(artifact) is ExperimentTaskModel:
        return TaskCoordinateModel(
            canonical_identity=f"task:{artifact.task_id}",
            canonicalization_profile="rfc8785-jcs-sha256/v1",
            task_id=artifact.task_id,
            task_version=artifact.task_version,
            **common,
        )
    if type(artifact) is ExperimentRunModel:
        return RunCoordinateModel(
            canonical_identity=f"run:{artifact.run_id}",
            canonicalization_profile="rfc8785-jcs-sha256/v1",
            run_id=artifact.run_id,
            run_version=artifact.run_version,
            **common,
        )
    if type(artifact) is ExperimentCaptureSpecModel:
        return EvidenceSpecificationCoordinateModel(
            canonical_identity=f"capture-spec:{artifact.capture_spec_id}",
            canonicalization_profile="rfc8785-jcs-sha256/v1",
            capture_spec_id=artifact.capture_spec_id,
            spec_version=artifact.spec_version,
            **common,
        )
    if type(artifact) is ExperimentStudyModel:
        return StudyCoordinateModel(
            canonical_identity=f"study:{artifact.study_id}",
            canonicalization_profile="rfc8785-jcs-sha256/v1",
            study_id=artifact.study_id,
            study_version=artifact.study_version,
            **common,
        )
    if type(artifact) is ExternalConceptBindingDocumentModel:
        return ExternalConceptBindingsCoordinateModel(
            canonical_identity=f"external-concept-bindings:{artifact.binding_set_id}",
            canonicalization_profile="rfc8785-jcs-sha256/v1",
            binding_set_id=artifact.binding_set_id,
            binding_set_version=artifact.binding_set_version,
            **common,
        )
    raise TypeError("semantic comparison requires an admitted RAES artifact model")


def build_impact_scope(
    before_artifacts: tuple[AdmittedArtifact, ...],
    after_artifacts: tuple[AdmittedArtifact, ...],
    *,
    traversal_roots: tuple[str, ...],
    closure_status: ImpactClosureStatus,
    scope_id: str = "comparison-scope",
) -> ImpactScopeModel:
    """Build a canonical digest-bound scope from actual admitted artifacts."""

    before = tuple(sorted((coordinate_for_artifact(item) for item in before_artifacts), key=_coordinate_key))
    after = tuple(sorted((coordinate_for_artifact(item) for item in after_artifacts), key=_coordinate_key))
    unsigned = ImpactScopeModel.model_construct(
        scope_id=scope_id,
        closure_policy="declared-exact-artifact-set/v1",
        closure_status=closure_status,
        traversal_roots=tuple(sorted(set(traversal_roots))),
        before_artifacts=before,
        after_artifacts=after,
        scope_digest="sha256:" + "0" * 64,
    )
    return ImpactScopeModel.model_validate(
        unsigned.model_copy(update={"scope_digest": canonical_impact_scope_digest(unsigned)}).model_dump(mode="json")
    )


def _artifact_digest(artifact: AdmittedArtifact) -> str:
    if not isinstance(artifact, BaseModel):
        raise TypeError("semantic comparison requires an admitted RAES artifact model")
    return canonical_json_digest(artifact.model_dump(mode="json"))


def project_artifact(
    profile: SemanticComparisonProfileModel,
    artifact: AdmittedArtifact,
    expected: ArtifactCoordinate,
) -> _Projection:
    coordinate = coordinate_for_artifact(artifact, exact_representation=expected.exact_representation)
    if coordinate != expected:
        raise ValueError("admitted artifact does not match its declared owner-specific coordinate")
    projection_version = profile.owner_projection_versions[coordinate.artifact_kind]
    structural_profile = f"{coordinate.artifact_kind.value}-structural-projection/v{projection_version}"
    semantic_profile = f"{coordinate.artifact_kind.value}-semantic-projection/v{projection_version}"
    root = _Subject(
        identity=coordinate.canonical_identity,
        representation_digest=(expected.exact_representation.byte_digest if expected.exact_representation else None),
        structural_digest=canonical_json_digest(_owner_structural_payload(artifact)),
        semantic_digest=canonical_json_digest(_owner_semantic_payload(artifact)),
        structural_profile=structural_profile,
        semantic_profile=semantic_profile,
    )
    subjects = [root]
    if type(artifact) is Scenario:
        subjects.extend(_scenario_subjects(artifact, structural_profile, semantic_profile))
    elif type(artifact) is ExperimentStudyModel:
        subjects.extend(_study_subjects(artifact, structural_profile, semantic_profile))
    elif type(artifact) is ExternalConceptBindingDocumentModel:
        subjects.extend(_external_binding_subjects(artifact, structural_profile, semantic_profile))
    return _Projection(
        coordinate=coordinate,
        subjects=tuple(sorted(subjects, key=lambda item: item.identity)),
        dependencies=tuple(sorted(_dependencies(artifact), key=_dependency_key)),
    )


def _scenario_subjects(
    scenario: Scenario,
    structural_profile: str,
    semantic_profile: str,
) -> list[_Subject]:
    result: list[_Subject] = []
    for field_name in scenario.__class__.model_fields:
        value = getattr(scenario, field_name)
        if not isinstance(value, dict):
            continue
        for key, child in value.items():
            payload = child.model_dump(mode="json") if isinstance(child, BaseModel) else child
            result.append(
                _Subject(
                    identity=f"scenario:{scenario.name}/{field_name}:{key}",
                    representation_digest=None,
                    structural_digest=canonical_json_digest(
                        {
                            "declaration_family": field_name,
                            "model_type": type(child).__name__,
                            "present_fields": sorted(payload),
                        }
                    ),
                    semantic_digest=canonical_json_digest(_without_editorial_description(payload)),
                    structural_profile=structural_profile,
                    semantic_profile=semantic_profile,
                )
            )
    return result


def _study_subjects(
    study: ExperimentStudyModel,
    structural_profile: str,
    semantic_profile: str,
) -> list[_Subject]:
    return [
        _Subject(
            identity=f"study-member:{key}",
            representation_digest=None,
            structural_digest=canonical_json_digest(
                {
                    "role": member.role,
                    "target_kind": member.target_ref.ref_kind,
                    "has_grouping": member.grouping is not None,
                }
            ),
            semantic_digest=canonical_json_digest(_study_member_semantics(member)),
            structural_profile=structural_profile,
            semantic_profile=semantic_profile,
        )
        for key, member in study.membership.items()
    ]


def _external_binding_subjects(
    document: ExternalConceptBindingDocumentModel,
    structural_profile: str,
    semantic_profile: str,
) -> list[_Subject]:
    return [
        _Subject(
            identity=f"external-binding:{key}",
            representation_digest=None,
            structural_digest=canonical_json_digest(
                {
                    "relationship_kind": binding.assertion.relationship_kind,
                    "subject_kind": binding.subject.subject_kind,
                    "lifecycle_phase": binding.subject.lifecycle_phase,
                }
            ),
            semantic_digest=canonical_json_digest(binding.model_dump(mode="json")),
            structural_profile=structural_profile,
            semantic_profile=semantic_profile,
        )
        for key, binding in document.bindings.items()
    ]


def _dependencies(artifact: AdmittedArtifact) -> list[_Dependency]:
    dependent = coordinate_for_artifact(artifact).canonical_identity
    if type(artifact) is Scenario:
        return [
            _dependency(dependent, f"module:{item.namespace}", "scenario-import", item) for item in artifact.imports
        ]
    if type(artifact) is ExperimentTaskModel:
        return [
            _dependency(
                dependent,
                f"scenario:{artifact.scenario_ref.ref_id}",
                "experiment-task-scenario-reference",
                artifact.scenario_ref,
            )
        ]
    if type(artifact) is ExperimentRunModel:
        return [
            _dependency(
                dependent, f"task:{artifact.task_ref.ref_id}", "experiment-run-task-reference", artifact.task_ref
            ),
            _dependency(
                dependent,
                f"scenario:{artifact.scenario_snapshot_ref.ref_id}",
                "experiment-run-scenario-snapshot-reference",
                artifact.scenario_snapshot_ref,
            ),
        ]
    if type(artifact) is ExperimentCaptureSpecModel:
        return [
            _dependency(
                dependent,
                _reference_identity(item.ref_kind, item.ref_id),
                "experiment-capture-scope-reference",
                item,
            )
            for item in artifact.scope_refs
        ]
    if type(artifact) is ExperimentStudyModel:
        return [
            _dependency(
                dependent,
                _reference_identity(member.target_ref.ref_kind, member.target_ref.ref_id),
                "experiment-study-membership",
                member,
            )
            for member in artifact.membership.values()
        ]
    if type(artifact) is ExternalConceptBindingDocumentModel:
        return [
            _dependency(
                dependent,
                binding.subject.canonical_ref,
                "external-concept-subject",
                binding.subject,
            )
            for binding in artifact.bindings.values()
        ]
    return []


def _dependency(dependent: str, dependency: str, rule: str, evidence: BaseModel) -> _Dependency:
    return _Dependency(
        dependent_identity=dependent,
        dependency_identity=dependency,
        rule_id=rule,
        provenance_digest=canonical_json_digest(evidence.model_dump(mode="json")),
    )


def _reference_identity(kind: str, identity: str) -> str:
    prefixes = {"scenario-snapshot": "scenario", "capture-spec": "capture-spec"}
    return f"{prefixes.get(kind, kind)}:{identity}"


def _dependency_key(dependency: _Dependency) -> tuple[str, str, str, str]:
    return (
        dependency.dependent_identity,
        dependency.rule_id,
        dependency.dependency_identity,
        dependency.provenance_digest,
    )


def _coordinate_key(coordinate: ArtifactCoordinate) -> tuple[str, str, str]:
    return (coordinate.artifact_kind.value, coordinate.canonical_identity, coordinate.canonical_digest)


__all__ = [
    "AdmittedArtifact",
    "build_impact_scope",
    "coordinate_for_artifact",
    "project_artifact",
]
