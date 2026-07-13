# Related-Work Comparison

The frozen comparison supports no overall winner. ACES has the strongest
expressive-breadth result inside the scenario-authoring stratum, while VSDL and
CRACK have stronger formal-analysis evidence, OCR SDL has stronger deployed
authoring maturity evidence, CybORG has stronger executed participant-modeling
evidence, and CACAO and Cyber FOM have stronger standards governance in their
respective scopes.

This result is a reproducible research snapshot, not a marketing ranking. It
distinguishes breadth from quality, implementation maturity, standardization,
and community governance. It also retains ACES features that are partial,
missing, external to SDL, or deliberately excluded.

## Reproduction Bundle

The comparison is split into independently revisioned artifacts:

- [`protocol-v1.json`](../../research/related-work-comparison/protocol-v1.json)
  pre-registers the corpus, scope strata, twelve axes, rubrics, authoring tasks,
  negative cases, source rules, and analysis rules.
- [`extraction-snapshot-2026-07-13.json`](../../research/related-work-comparison/extraction-snapshot-2026-07-13.json)
  freezes every source identity and records every system-axis cell and
  system-case walkthrough with exact primary-source locators.
- [`analysis-v1.json`](../../research/related-work-comparison/analysis-v1.json)
  records scope-qualified Pareto frontiers, predeclared weight profiles, ranking
  reversals, and bounded public claims.

The systems remain independent observations. Cyber DEM is not merged with
Cyber FOM, and CRACK is not merged with VSDL. Systems with unlike purposes stay
in separate scope strata; `out of scope` is not treated as a zero.

## Evidence Matrix And Findings

The block below is generated from the frozen artifacts and checked by
`tools/check_related_work_comparison.py`. Each ordinal level follows its
axis-specific rubric. It is not an interval measurement and cannot be summed
into a universal quality score.

<!-- related-work-comparison:start -->
Frozen snapshot: `snapshot-2026-07-13` under protocol `protocol-v1`.
Scores are axis-specific ordinal evidence levels: 0 absent, 1 limited, 2 substantial, 3 strong;
`oos` means the axis is outside the system's declared scope and is never treated as zero.

| Axis | ACES | OCR SDL | CybORG | CACAO 2.0 | Cyber DEM | Cyber FOM | CRACK | VSDL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Expressive breadth | 3 | 2 | 2 | 1 | 2 | 2 | 2 | 2 |
| Semantic precision | 3 | 1 | 2 | 3 | 3 | 3 | 3 | 3 |
| Formal analyzability | 1 | 0 | 1 | 1 | 1 | 2 | 3 | 3 |
| Concrete-syntax soundness | 3 | 2 | 2 | 3 | 2 | 3 | 2 | 2 |
| Composition and versioning | 3 | 1 | 2 | 3 | 2 | 3 | 2 | 3 |
| Experiment design | 2 | 1 | 3 | oos | oos | oos | 0 | 0 |
| Participant modeling | 2 | 1 | 3 | oos | oos | oos | 1 | 1 |
| Provenance and evidence | 3 | 1 | 1 | 3 | 1 | 1 | 0 | 0 |
| Interoperability | 2 | 1 | 2 | 3 | 3 | 3 | 0 | 0 |
| Usability | 1 | 2 | 2 | 2 | 1 | 1 | 1 | 1 |
| Implementation maturity | 1 | 2 | 3 | 3 | 2 | 3 | 1 | 1 |
| Governance and community | 1 | 1 | 2 | 3 | 3 | 3 | 0 | 0 |

### Evidence-bounded findings

- **No Overall Winner.** Evidence status: `partial`. No overall winner is supported: the four declared scope strata are analyzed separately, and the scenario-authoring first-ranked system changes across the four declared weight profiles.
- **Scope Qualified Breadth.** Evidence status: `partial`. Within the four-system scenario-authoring stratum and this frozen rubric, ACES is the sole expressive-breadth leader at level 3. This is the broadest combined surface observed in this corpus; `highest quality` is not supported, and standardization or maturity do not follow from breadth.
- **Maturity Governance.** Evidence status: `partial`. Against ACES's recorded level 1, CACAO 2.0 and Cyber FOM each record level 3 for governance and community, while CybORG records level 3 and OCR SDL level 2 for implementation maturity. These are axis-specific evidence comparisons, not cross-scope overall rankings or adoption claims.
- **Sensitivity.** Evidence status: `partial`. Across the declared scenario-authoring profiles, breadth and composition ranks ACES first, formal rigor ranks VSDL first, and maturity and governance ranks OCR SDL first; this observed reversal prohibits a weight-independent winner claim.

### Sensitivity of scenario-authoring rankings

| Weight profile | First-ranked system | Recorded totals |
| --- | --- | --- |
| `equal-evidence` | ACES | ACES=25, VSDL=16, CRACK=15, OCR SDL=15 |
| `breadth-and-composition` | ACES | ACES=42, OCR SDL=21, VSDL=21, CRACK=18 |
| `formal-rigor` | VSDL | VSDL=39, CRACK=37, ACES=32, OCR SDL=12 |
| `maturity-and-governance` | OCR SDL | OCR SDL=26, ACES=22, CRACK=10, VSDL=10 |

### ACES delivery limits retained in the matrix

- **Formal analyzability (1).** Full solver-backed whole-scenario verification remains outside the current implementation.
- **Experiment design (2).** Controlled allocation and factor/study concerns live in experiment contracts, and several delivery rows remain external or incomplete.
- **Participant modeling (2).** Participant budgets, reference trajectories, hidden benchmark assets, and verifier/adjudication remain missing or partial.
- **Interoperability (2).** Published profiles exist, but independent multi-vendor conformance and substitution evidence remains limited.
- **Usability (1).** No independent author population, completion-time, effort, or error study is frozen in this corpus.
- **Implementation maturity (1).** The delivery assessment retains partial, missing, external-contract, and deliberately-excluded concerns; formal prose is not counted as shipped behavior.
- **Governance and community (1).** Governance is explicit but project-led; standardization and independent adoption are not claimed.

Cell rationales, exact source locators, task walkthroughs, and source digests are in the
[frozen extraction snapshot](../../research/related-work-comparison/extraction-snapshot-2026-07-13.json).
<!-- related-work-comparison:end -->

## Interpretation Boundaries

The matrix is only one view over the extraction snapshot. A level of `3` means
strong evidence against that axis's own rubric; it does not mean that the
system is better overall. `Usability` remains at most `2` because this corpus
contains documentation and source walkthroughs, not an independent author
study with disclosed population, effort, completion, and error measurements.

The sensitivity table deliberately shows reversals. Weighting formal rigor
places VSDL first; weighting maturity and governance places OCR SDL first;
weighting breadth and composition places ACES first. Selecting a weighting
after seeing those results would violate the protocol.

The source walkthroughs do not execute third-party code. Normal verification
is offline and checks the archived metadata, digests, evidence references,
rectangular coverage, recomputed analysis, and this page's generated block.

## Reproduce The Checks

From the repository root:

```bash
implementations/python/.venv/bin/python tools/check_related_work_comparison.py
implementations/python/.venv/bin/python -m pytest \
  implementations/python/tests/test_related_work_comparison.py
```

The research [index](../../research/related-work-comparison/index.md) describes
the extraction workflow. The [search log](../../research/related-work-comparison/search-log.md)
records the frozen source set and retrieval decisions.

## Related Material

- [Design Precedents](precedents.md) maps individual ACES concepts to lineage.
- [Lineage and Prior Work](lineage.md) gives the narrative source map.
- [Scientific Scenario Completeness](scientific-scenario-completeness.md)
  separates intended-use profiles from current delivery status.
- [Documentation Style Guide](../reference/documentation-style-guide.md)
  defines the accuracy, citation, and current-state rules used here.
