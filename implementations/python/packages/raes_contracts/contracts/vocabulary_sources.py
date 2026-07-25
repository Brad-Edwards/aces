"""Controlled-vocabulary and ATT&CK/ATLAS tactics-source contracts."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from ..versions import (
    ATLAS_TACTICS_SOURCE_SCHEMA_VERSION,
    ATTACK_ENTERPRISE_TACTICS_SOURCE_SCHEMA_VERSION,
    CONTROLLED_VOCABULARIES_SCHEMA_VERSION,
    NIST_CSF_DEFENSIVE_CATEGORIES_SOURCE_SCHEMA_VERSION,
)
from .base import (
    _CONTROLLED_VOCABULARY_GOVERNED_SCOPES,
    CalendarDateString,
    ContractModel,
    ControlledVocabularyTermId,
    NonEmptyString,
    PositiveInteger,
    PrefixedDigestString,
)


class ControlledVocabularySourceModel(ContractModel):
    provenance: Literal["adopted", "adapted"]
    authority: NonEmptyString
    authority_version: NonEmptyString
    source_artifact_ref: NonEmptyString
    source_url: NonEmptyString
    source_digest: PrefixedDigestString
    citation_urls: list[NonEmptyString] = Field(min_length=1)
    license_url: NonEmptyString
    license_notice: NonEmptyString


class ControlledVocabularyTermModel(ContractModel):
    title: NonEmptyString
    description: NonEmptyString
    source_id: NonEmptyString | None = None
    source_url: NonEmptyString | None = None


class ControlledVocabularyDefinitionModel(ContractModel):
    title: NonEmptyString
    description: NonEmptyString
    source: ControlledVocabularySourceModel | None = None
    kind: Literal["enumeration", "vocabulary"]
    governed_scopes: list[NonEmptyString] = Field(default_factory=list)
    extension_policy: Literal["closed", "governed-extension"]
    extension_pattern: NonEmptyString | None = None
    terms: dict[ControlledVocabularyTermId, ControlledVocabularyTermModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_vocabulary_definition(self) -> ControlledVocabularyDefinitionModel:
        unknown_scopes = set(self.governed_scopes) - _CONTROLLED_VOCABULARY_GOVERNED_SCOPES
        if unknown_scopes:
            unknown = ", ".join(sorted(unknown_scopes))
            raise ValueError(f"controlled vocabulary includes unknown governed scopes: {unknown}")

        if len(self.governed_scopes) != len(set(self.governed_scopes)):
            raise ValueError("controlled vocabulary governed_scopes must not contain duplicates")

        if self.kind == "enumeration" and self.extension_policy != "closed":
            raise ValueError("enumeration controlled vocabularies must use extension_policy='closed'")

        if self.extension_policy == "closed":
            if self.extension_pattern is not None:
                raise ValueError("closed controlled vocabularies must not declare extension_pattern")
            return self

        if not self.governed_scopes:
            raise ValueError("governed-extension controlled vocabularies must declare governed_scopes")
        if self.extension_pattern is None:
            raise ValueError("governed-extension controlled vocabularies must declare extension_pattern")
        try:
            re.compile(self.extension_pattern)
        except re.error as exc:
            raise ValueError("controlled vocabulary extension_pattern must be a valid regex") from exc
        return self


class ControlledVocabularyCatalogModel(ContractModel):
    schema_version: Literal[CONTROLLED_VOCABULARIES_SCHEMA_VERSION] = CONTROLLED_VOCABULARIES_SCHEMA_VERSION
    vocabularies: dict[NonEmptyString, ControlledVocabularyDefinitionModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_vocabulary_catalog(self) -> ControlledVocabularyCatalogModel:
        scope_to_vocabulary: dict[str, str] = {}
        for vocabulary_id, definition in self.vocabularies.items():
            for scope in definition.governed_scopes:
                previous = scope_to_vocabulary.setdefault(scope, vocabulary_id)
                if previous != vocabulary_id:
                    raise ValueError(
                        f"governed scope '{scope}' is declared by multiple vocabularies: {previous}, {vocabulary_id}"
                    )
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        vocabularies_schema = json_schema.get("properties", {}).get("vocabularies")
        if isinstance(vocabularies_schema, dict):
            vocabularies_schema.setdefault("propertyNames", {"minLength": 1})
        return json_schema


class AttackEnterpriseTacticSourceTermModel(ContractModel):
    tactic_id: Annotated[str, Field(pattern=r"^TA[0-9]{4}$")]
    shortname: ControlledVocabularyTermId
    name: NonEmptyString
    description: NonEmptyString
    url: NonEmptyString
    stix_id: NonEmptyString


class AttackEnterpriseTacticsSourceModel(ContractModel):
    schema_version: Literal[ATTACK_ENTERPRISE_TACTICS_SOURCE_SCHEMA_VERSION] = (
        ATTACK_ENTERPRISE_TACTICS_SOURCE_SCHEMA_VERSION
    )
    source_authority: Literal["MITRE ATT&CK"]
    source_domain: Literal["enterprise-attack"]
    source_version: NonEmptyString
    source_url: NonEmptyString
    source_digest: PrefixedDigestString
    citation_urls: list[NonEmptyString] = Field(min_length=1)
    retrieved_at: CalendarDateString
    license_url: NonEmptyString
    license_notice: NonEmptyString
    tactics: list[AttackEnterpriseTacticSourceTermModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_attack_tactics_source(self) -> AttackEnterpriseTacticsSourceModel:
        tactic_ids = [tactic.tactic_id for tactic in self.tactics]
        if len(tactic_ids) != len(set(tactic_ids)):
            raise ValueError("ATT&CK Enterprise tactic source must not contain duplicate tactic_id values")

        shortnames = [tactic.shortname for tactic in self.tactics]
        if len(shortnames) != len(set(shortnames)):
            raise ValueError("ATT&CK Enterprise tactic source must not contain duplicate shortname values")
        return self


class AtlasTacticSourceTermModel(ContractModel):
    tactic_id: Annotated[str, Field(pattern=r"^AML\.TA[0-9]{4}$")]
    shortname: ControlledVocabularyTermId
    name: NonEmptyString
    description: NonEmptyString
    url: NonEmptyString
    position: PositiveInteger
    uuid: NonEmptyString
    created_date: CalendarDateString
    modified_date: CalendarDateString
    attack_reference_id: NonEmptyString | None = None
    attack_reference_url: NonEmptyString | None = None


class AtlasTacticsSourceModel(ContractModel):
    schema_version: Literal[ATLAS_TACTICS_SOURCE_SCHEMA_VERSION] = ATLAS_TACTICS_SOURCE_SCHEMA_VERSION
    source_authority: Literal["MITRE ATLAS"]
    source_version: NonEmptyString
    source_format_version: NonEmptyString
    source_url: NonEmptyString
    source_digest: PrefixedDigestString
    citation_urls: list[NonEmptyString] = Field(min_length=1)
    retrieved_at: CalendarDateString
    license_url: NonEmptyString
    license_notice: NonEmptyString
    collection_id: Literal["ATLAS-collection"]
    matrix_id: Literal["ATLAS-matrix"]
    tactics: list[AtlasTacticSourceTermModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_atlas_tactics_source(self) -> AtlasTacticsSourceModel:
        tactic_ids = [tactic.tactic_id for tactic in self.tactics]
        if len(tactic_ids) != len(set(tactic_ids)):
            raise ValueError("ATLAS tactic source must not contain duplicate tactic_id values")

        shortnames = [tactic.shortname for tactic in self.tactics]
        if len(shortnames) != len(set(shortnames)):
            raise ValueError("ATLAS tactic source must not contain duplicate shortname values")

        positions = [tactic.position for tactic in self.tactics]
        if len(positions) != len(set(positions)):
            raise ValueError("ATLAS tactic source must not contain duplicate position values")
        if positions != sorted(positions):
            raise ValueError("ATLAS tactic source tactics must be ordered by matrix position")
        return self


class NistCsfDefensiveCategorySourceTermModel(ContractModel):
    category_id: Annotated[str, Field(pattern=r"^(?:DE|RS|RC)\.[A-Z]{2}$")]
    term_id: ControlledVocabularyTermId
    title: NonEmptyString
    description: NonEmptyString
    function: Literal["Detect", "Respond", "Recover"]


class NistCsfDefensiveCategorySourceModel(ContractModel):
    schema_version: Literal[NIST_CSF_DEFENSIVE_CATEGORIES_SOURCE_SCHEMA_VERSION] = (
        NIST_CSF_DEFENSIVE_CATEGORIES_SOURCE_SCHEMA_VERSION
    )
    source_authority: Literal["NIST Cybersecurity Framework"]
    source_version: Literal["2.0"]
    source_url: NonEmptyString
    source_digest: PrefixedDigestString
    citation_urls: list[NonEmptyString] = Field(min_length=1)
    retrieved_at: CalendarDateString
    license_url: NonEmptyString
    license_notice: NonEmptyString
    categories: list[NistCsfDefensiveCategorySourceTermModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_defensive_categories_source(self) -> NistCsfDefensiveCategorySourceModel:
        category_ids = [category.category_id for category in self.categories]
        if len(category_ids) != len(set(category_ids)):
            raise ValueError("NIST CSF defensive category source must not contain duplicate category_id values")

        term_ids = [category.term_id for category in self.categories]
        if len(term_ids) != len(set(term_ids)):
            raise ValueError("NIST CSF defensive category source must not contain duplicate term_id values")
        return self
