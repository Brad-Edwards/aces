"""Fixture-corpus conformance suite runner."""

from __future__ import annotations

from pathlib import Path

from raes_contracts.contracts import schema_bundle
from raes_contracts.diagnostics import Diagnostic

from raes_conformance.conformance.diagnostics import _diagnostic, _load_json
from raes_conformance.conformance.profiles import (
    BackendProfileSelector,
    _fixture_contract_root,
    _resolve_required_contracts,
    _to_profile_id,
    fixtures_root,
)
from raes_conformance.conformance.report import (
    BackendConformanceReport,
    ConformanceCaseResult,
    _bounded_conformance_claim,
)
from raes_conformance.conformance.semantics import _fixture_case_diagnostics


def run_fixture_suite(
    *,
    profile: BackendProfileSelector,
    root: Path | None = None,
    profiles_root: Path | None = None,
) -> BackendConformanceReport:
    """Run the checked-in fixture corpus for a backend profile.

    ``root`` overrides the fixtures tree (defaults to ``contracts/fixtures``);
    ``profiles_root`` overrides the backend profile tree (defaults to
    ``contracts/profiles/backend``). Both default to the canonical
    ``contracts/`` paths so the published artifacts remain the authority.
    """

    root = fixtures_root() if root is None else root
    bundle = schema_bundle()
    required, profile_diagnostics = _resolve_required_contracts(profile, profiles_root=profiles_root)
    cases: list[ConformanceCaseResult] = []
    diagnostics: list[Diagnostic] = list(profile_diagnostics)

    for contract_name in sorted(required):
        contract_root = _fixture_contract_root(root, contract_name)
        valid_dir = contract_root / "valid"
        invalid_dir = contract_root / "invalid"
        if not valid_dir.exists():
            diagnostics.append(
                _diagnostic(
                    "conformance.fixture-missing",
                    contract_name,
                    f"Missing valid fixture directory for {contract_name}.",
                )
            )
            continue

        for path in sorted(valid_dir.glob("*.json")):
            payload = _load_json(path)
            case_diagnostics = _fixture_case_diagnostics(contract_name, payload)
            cases.append(
                ConformanceCaseResult(
                    name=path.stem,
                    contract_name=contract_name,
                    valid=True,
                    passed=not case_diagnostics,
                    diagnostics=tuple(case_diagnostics),
                )
            )

        if invalid_dir.exists():
            for path in sorted(invalid_dir.glob("*.json")):
                payload = _load_json(path)
                case_diagnostics = _fixture_case_diagnostics(contract_name, payload)
                cases.append(
                    ConformanceCaseResult(
                        name=path.stem,
                        contract_name=contract_name,
                        valid=False,
                        passed=bool(case_diagnostics),
                        diagnostics=tuple(case_diagnostics),
                    )
                )

    profile_id = _to_profile_id(profile)
    case_tuple = tuple(cases)
    return BackendConformanceReport(
        profile=profile_id,
        passed=not diagnostics and all(case.passed for case in cases),
        claim=_bounded_conformance_claim(
            profile=profile_id,
            cases=case_tuple,
            left_carrier_ref=f"conformance-fixture-suite:{profile_id}",
        ),
        cases=case_tuple,
        contract_versions={name: str(schema.get("title", name)) for name, schema in bundle.items() if name in required},
        diagnostics=tuple(diagnostics),
    )
