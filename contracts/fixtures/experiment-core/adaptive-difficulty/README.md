# Adaptive-difficulty nested contract fixtures

These fixtures exercise the SCE-003 policy and resolver models nested in
`experiment-authoring-input-v1` and `experiment-run-v1`. They are fragment
fixtures rather than an additional top-level contract.

- `positive.json` selects the declared harder follow-up at the exact threshold.
- `boundary.json` reaches the declared intervention-count terminal boundary.
- `unsupported.json` names a digest-bound evaluator profile the reference
  resolver does not implement and must not silently replace.
- `policy-violation.json` points a threshold rule at an undeclared action and
  must fail closed during model validation.
