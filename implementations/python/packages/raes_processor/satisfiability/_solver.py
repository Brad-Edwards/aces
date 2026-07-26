"""Pinned deterministic Z3 adapter for normalized finite-domain models."""

from __future__ import annotations

from dataclasses import dataclass

import z3
from raes_contracts.satisfiability import NormalizedConstraintModel, SatisfiabilityOutcome


class SolverOperationalError(RuntimeError):
    """The pinned adapter could not produce a completed governed outcome."""


@dataclass(frozen=True)
class SolverResult:
    outcome: SatisfiabilityOutcome
    assignment: dict[str, str | int | bool] | None = None
    core: tuple[str, ...] | None = None


def solve_model(model: NormalizedConstraintModel) -> SolverResult:
    """Solve one normalized model and select deterministic portable evidence."""

    all_clause_ids = tuple(clause.clause_id for clause in model.clauses)
    status = _check(model, all_clause_ids, {})
    if status == z3.sat:
        return SolverResult(
            outcome=SatisfiabilityOutcome.SATISFIABLE,
            assignment=_select_witness(model, all_clause_ids),
        )
    if status == z3.unsat:
        return SolverResult(
            outcome=SatisfiabilityOutcome.UNSATISFIABLE,
            core=_reduce_unsat_core(model, all_clause_ids),
        )
    raise SolverOperationalError("solver returned an incomplete result")


def _select_witness(
    model: NormalizedConstraintModel,
    all_clause_ids: tuple[str, ...],
) -> dict[str, str | int | bool]:
    fixed: dict[str, int] = {}
    assignment: dict[str, str | int | bool] = {}
    for symbol in model.symbols:
        for index, value in enumerate(symbol.domain):
            candidate = {**fixed, symbol.symbol_id: index}
            if _check(model, all_clause_ids, candidate) == z3.sat:
                fixed[symbol.symbol_id] = index
                assignment[symbol.variable] = value
                break
        else:
            # This is guarded by the initial satisfiable result.
            raise SolverOperationalError("deterministic witness selection failed")
    return assignment


def _reduce_unsat_core(
    model: NormalizedConstraintModel,
    all_clause_ids: tuple[str, ...],
) -> tuple[str, ...]:
    core = list(all_clause_ids)
    for clause_id in all_clause_ids:
        candidate = tuple(item for item in core if item != clause_id)
        if _check(model, candidate, {}) == z3.unsat:
            core = list(candidate)
    return tuple(sorted(core))


def _check(
    model: NormalizedConstraintModel,
    clause_ids: tuple[str, ...],
    fixed: dict[str, int],
) -> z3.CheckSatResult:
    solver = z3.SolverFor("QF_LIA")
    solver.set(
        random_seed=0,
        timeout=5000,
        threads=1,
        auto_config=False,
        model=True,
        unsat_core=True,
    )
    variables = {symbol.symbol_id: z3.Int(_z3_name(symbol.symbol_id)) for symbol in model.symbols}
    clauses = {item.clause_id: item for item in model.clauses}
    symbols = {item.symbol_id: item for item in model.symbols}
    for clause_id in clause_ids:
        clause = clauses[clause_id]
        symbol = symbols[clause.symbol_id]
        indexes = [
            index
            for index, value in enumerate(symbol.domain)
            if any(_scalar_equal(value, allowed) for allowed in clause.allowed_values)
        ]
        expression = z3.Or(*(variables[symbol.symbol_id] == index for index in indexes))
        solver.assert_and_track(expression, z3.Bool(_z3_name(clause_id)))
    for symbol_id, index in fixed.items():
        solver.add(variables[symbol_id] == index)
    return solver.check()


def _scalar_equal(left: object, right: object) -> bool:
    return type(left) is type(right) and left == right


def _z3_name(value: str) -> str:
    return "aces_" + value.encode("utf-8").hex()
