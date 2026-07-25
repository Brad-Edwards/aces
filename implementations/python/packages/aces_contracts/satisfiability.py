"""Portable contracts for governed whole-scenario satisfiability evidence."""

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Annotated, Literal

import rfc8785
from pydantic import Field, model_validator
from raes.canonical import (
    INSTANTIATED_SNAPSHOT_PROFILE,
    InstantiatedScenarioSnapshot,
    canonical_instantiated_sdl_digest,
)
from raes.phase_contracts import ResolvedImportProvenance, SemanticDigest

from .contracts.base import ContractModel, PrefixedDigestString
from .diagnostics import DiagnosticModel

JSONScalar = str | int | bool
ClauseId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9._:-]*$", max_length=256)]
SymbolId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9._:-]*$", max_length=256)]


class ConstraintSort(str, Enum):
    """Closed scalar sorts admitted by the v1 finite-domain theory."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"


class ConstraintClauseKind(str, Enum):
    """Meaning of a normalized finite-domain membership clause."""

    DECLARED_DOMAIN = "declared-domain"
    TARGET_DOMAIN = "target-domain"


class SatisfiabilityOutcome(str, Enum):
    """Completed outcomes exposed by the governed analysis boundary."""

    SATISFIABLE = "satisfiable"
    UNSATISFIABLE = "unsatisfiable"
    UNSUPPORTED = "unsupported"


class SourceArtifactIdentityModel(ContractModel):
    """Portable identity and exact-byte digest for the root SDL source."""

    source_id: str = Field(min_length=1, max_length=256, pattern=r"^[^\r\n]+$")
    byte_digest: PrefixedDigestString

    @model_validator(mode="after")
    def _reject_host_paths(self) -> SourceArtifactIdentityModel:
        if self.source_id.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", self.source_id):
            raise ValueError("source_id must be portable rather than an absolute host path")
        if ".." in self.source_id.replace("\\", "/").split("/"):
            raise ValueError("source_id must not contain parent traversal")
        return self


class ConstraintSymbolModel(ContractModel):
    """One canonically ordered finite-domain symbol."""

    symbol_id: SymbolId
    variable: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$", max_length=128)
    sort: ConstraintSort
    domain: tuple[JSONScalar, ...] = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def _validate_domain(self) -> ConstraintSymbolModel:
        expected = {
            ConstraintSort.STRING: lambda value: isinstance(value, str),
            ConstraintSort.INTEGER: lambda value: isinstance(value, int) and not isinstance(value, bool),
            ConstraintSort.BOOLEAN: lambda value: isinstance(value, bool),
        }[self.sort]
        if not all(expected(value) for value in self.domain):
            raise ValueError("every domain member must match the symbol sort")
        if len({_scalar_key(value) for value in self.domain}) != len(self.domain):
            raise ValueError("symbol domains must not contain duplicates")
        if tuple(sorted(self.domain, key=_scalar_key)) != self.domain:
            raise ValueError("symbol domains must use canonical order")
        return self


class ConstraintClauseModel(ContractModel):
    """One named finite-domain membership clause."""

    clause_id: ClauseId
    kind: ConstraintClauseKind
    symbol_id: SymbolId
    source_address: str = Field(pattern=r"^(?:/(?:[^~/]|~[01])*)*$", max_length=4096)
    allowed_values: tuple[JSONScalar, ...] = Field(max_length=256)

    @model_validator(mode="after")
    def _validate_values(self) -> ConstraintClauseModel:
        if len({_scalar_key(value) for value in self.allowed_values}) != len(self.allowed_values):
            raise ValueError("clause allowed_values must not contain duplicates")
        if tuple(sorted(self.allowed_values, key=_scalar_key)) != self.allowed_values:
            raise ValueError("clause allowed_values must use canonical order")
        return self


class NormalizedConstraintModel(ContractModel):
    """Solver-neutral normalized ACES finite-domain constraint model."""

    profile: Literal["aces-finite-domain-constraints/v1"]
    theory_profile: Literal["aces-finite-domain-theory/v1"]
    translation_profile: Literal["aces-sdl-authoring-translation/v1"]
    source_digest: PrefixedDigestString
    authored_digest: SemanticDigest
    symbols: tuple[ConstraintSymbolModel, ...] = Field(max_length=128)
    clauses: tuple[ConstraintClauseModel, ...] = Field(max_length=512)

    @model_validator(mode="after")
    def _validate_graph(self) -> NormalizedConstraintModel:
        symbol_ids = [item.symbol_id for item in self.symbols]
        clause_ids = [item.clause_id for item in self.clauses]
        if symbol_ids != sorted(symbol_ids) or len(symbol_ids) != len(set(symbol_ids)):
            raise ValueError("symbols must be uniquely ordered by symbol_id")
        if clause_ids != sorted(clause_ids) or len(clause_ids) != len(set(clause_ids)):
            raise ValueError("clauses must be uniquely ordered by clause_id")
        symbols = {item.symbol_id: item for item in self.symbols}
        for clause in self.clauses:
            symbol = symbols.get(clause.symbol_id)
            if symbol is None:
                raise ValueError("every clause must reference a declared symbol")
            domain = {_scalar_key(value) for value in symbol.domain}
            if any(_scalar_key(value) not in domain for value in clause.allowed_values):
                raise ValueError("clause values must be members of the referenced symbol domain")
        return self


class SolverConfigurationModel(ContractModel):
    """Complete output-affecting configuration for the pinned v1 Z3 adapter."""

    profile: Literal["aces-z3-finite-domain/v1"]
    engine: Literal["z3"]
    package: Literal["z3-solver"]
    package_version: Literal["4.16.0.0"]  # NOSONAR -- pinned package version, not an IP address
    engine_version: Literal["4.16.0"]
    logic: Literal["QF_LIA"]
    random_seed: Literal[0]
    timeout_ms: Literal[5000]
    threads: Literal[1]
    auto_config: Literal[False]
    model: Literal[True]
    unsat_core: Literal[True]
    witness_selection: Literal["canonical-lexicographic/v1"]
    core_reduction: Literal["sorted-deletion-subset-minimal/v1"]


class SatisfiableWitnessModel(ContractModel):
    """Independently admitted canonical instantiation witness."""

    profile: Literal["aces-satisfiability-witness/v1"]
    snapshot: InstantiatedScenarioSnapshot
    snapshot_digest: PrefixedDigestString

    @model_validator(mode="after")
    def _validate_snapshot(self) -> SatisfiableWitnessModel:
        if self.snapshot.profile != INSTANTIATED_SNAPSHOT_PROFILE:
            raise ValueError("witness must use the canonical instantiated snapshot profile")
        actual = canonical_instantiated_sdl_digest(self.snapshot.scenario).value
        if self.snapshot_digest != actual:
            raise ValueError("snapshot_digest must bind the canonical instantiated snapshot")
        return self


class UnsatisfiableCoreModel(ContractModel):
    """Governed subset-minimal clause set, not a proof certificate."""

    profile: Literal["aces-unsatisfiable-core/v1"]
    clause_ids: tuple[ClauseId, ...] = Field(min_length=1, max_length=512)
    minimality: Literal["subset-minimal"]

    @model_validator(mode="after")
    def _validate_order(self) -> UnsatisfiableCoreModel:
        if self.clause_ids != tuple(sorted(set(self.clause_ids))):
            raise ValueError("unsatisfiable core clause ids must be unique and sorted")
        return self


class UnsupportedAnalysisModel(ContractModel):
    """Stable fail-closed reason set for an unsupported analysis."""

    profile: Literal["aces-satisfiability-unsupported/v1"]
    reason_codes: tuple[str, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def _validate_reasons(self) -> UnsupportedAnalysisModel:
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("unsupported reason codes must be unique and sorted")
        return self


class ScenarioSatisfiabilityEvidenceModel(ContractModel):
    """Closed evidence envelope binding source, model, solver, and result."""

    profile: Literal["scenario-satisfiability-evidence/v1"]
    analysis_profile: Literal["aces-finite-domain-satisfiability-v1"]
    source: SourceArtifactIdentityModel
    authored_digest: SemanticDigest
    imports: tuple[ResolvedImportProvenance, ...] = ()
    normalized_model: NormalizedConstraintModel
    normalized_model_digest: PrefixedDigestString
    solver_configuration: SolverConfigurationModel
    solver_configuration_digest: PrefixedDigestString
    outcome: SatisfiabilityOutcome
    diagnostics: tuple[DiagnosticModel, ...] = Field(max_length=64)
    witness: SatisfiableWitnessModel | None = None
    unsat_core: UnsatisfiableCoreModel | None = None
    unsupported: UnsupportedAnalysisModel | None = None

    @model_validator(mode="after")
    def _validate_evidence_joins(self) -> ScenarioSatisfiabilityEvidenceModel:
        _validate_evidence_digests(self)
        _validate_outcome_payload(self)
        _validate_unsatisfiable_core(self)
        _validate_unsupported_reasons(self)
        return self


def _validate_evidence_digests(evidence: ScenarioSatisfiabilityEvidenceModel) -> None:
    """Validate the source, authored, normalized-model, and solver joins."""

    if evidence.source.byte_digest != evidence.normalized_model.source_digest:
        raise ValueError("normalized model source digest must match the root source")
    if evidence.authored_digest != evidence.normalized_model.authored_digest:
        raise ValueError("normalized model authored digest must match the evidence")
    if evidence.normalized_model_digest != canonical_contract_digest(evidence.normalized_model):
        raise ValueError("normalized_model_digest must bind the normalized model")
    if evidence.solver_configuration_digest != canonical_contract_digest(evidence.solver_configuration):
        raise ValueError("solver_configuration_digest must bind the solver configuration")


def _validate_outcome_payload(evidence: ScenarioSatisfiabilityEvidenceModel) -> None:
    payloads = {
        SatisfiabilityOutcome.SATISFIABLE: evidence.witness,
        SatisfiabilityOutcome.UNSATISFIABLE: evidence.unsat_core,
        SatisfiabilityOutcome.UNSUPPORTED: evidence.unsupported,
    }
    if payloads[evidence.outcome] is None or sum(item is not None for item in payloads.values()) != 1:
        raise ValueError("outcome must select exactly one matching payload")


def _validate_unsatisfiable_core(evidence: ScenarioSatisfiabilityEvidenceModel) -> None:
    if evidence.unsat_core is None:
        return
    clause_ids = {item.clause_id for item in evidence.normalized_model.clauses}
    if any(item not in clause_ids for item in evidence.unsat_core.clause_ids):
        raise ValueError("unsatisfiable core must reference normalized model clauses")


def _validate_unsupported_reasons(evidence: ScenarioSatisfiabilityEvidenceModel) -> None:
    if evidence.unsupported is None:
        return
    diagnostic_codes = tuple(sorted({item.code for item in evidence.diagnostics}))
    if evidence.unsupported.reason_codes != diagnostic_codes:
        raise ValueError("unsupported reason codes must match diagnostic codes")


def canonical_contract_digest(model: ContractModel) -> str:
    """Return a JCS SHA-256 digest for one closed contract model."""

    payload = rfc8785.dumps(model.model_dump(mode="json"))
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _scalar_key(value: JSONScalar) -> bytes:
    return rfc8785.dumps(value)


__all__ = (
    "ConstraintClauseKind",
    "ConstraintClauseModel",
    "ConstraintSort",
    "ConstraintSymbolModel",
    "NormalizedConstraintModel",
    "ScenarioSatisfiabilityEvidenceModel",
    "SatisfiabilityOutcome",
    "SatisfiableWitnessModel",
    "SolverConfigurationModel",
    "SourceArtifactIdentityModel",
    "UnsatisfiableCoreModel",
    "UnsupportedAnalysisModel",
    "canonical_contract_digest",
)
