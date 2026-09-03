# Issue 1040 Expanded Scenario Parent Remediation

Date: 2026-08-11

Issue: #1040. Requirement: none; the issue acceptance criteria and the
incumbent associated-artifact contract are authoritative.

## Gap Claim

`parse_sdl_file()` returns a semantically validated `ExpandedScenario` for a
file-backed module composition, and `canonical_sdl_digest()` accepts that
authoring phase. Associated-artifact snapshot matching accepted only
`Scenario`, so an exact expanded semantic parent could never validate.

## Existing Surface Audit

- `Scenario`, `ExpandedScenario`, and `InstantiatedScenario` are closed phase
  types sharing `ScenarioContent`.
- Canonical SDL authoring identity accepts validated `Scenario` and
  `ExpandedScenario`, rejects unvalidated objects, and rejects instantiated
  artifacts.
- Generic `scenario` association is intentionally id-only and historically
  accepts a `Scenario` without consulting canonical identity.
- Snapshot matching already checks optional version and digest after its
  overly narrow type test. The manifest schema needs no change.
- The parser's public return annotation incorrectly hid its expanded return
  phase even though the runtime behavior and phase tests already expose it.

## Lineage And Precedent

ADR-077 and `specs/supply-chain/associated-artifact-manifests.md` define a
scenario snapshot as a binding to incumbent canonical SDL identity. ADR-078
and `raes.canonical` own phase-correct semantic identity. The artifact validator
must delegate phase admission to that incumbent boundary rather than create a
narrower authoring-phase list.

## Literature And Practice

The repository's supply-chain lineage separates logical references, canonical
content identity, byte integrity, and authenticity. This fix preserves that
separation: it broadens only which canonical authoring phase may supply the
already-defined snapshot digest.

## Alternatives Considered

1. **Do nothing or require callers to reconstruct `Scenario`.** Rejected
   because reconstruction discards composition phase identity and encourages
   mutation of private validation state.
2. **Accept every `ScenarioContent`.** Rejected because instantiated and
   unvalidated objects do not have canonical authoring identity.
3. **Call `canonical_sdl_digest()` and catch every failure.** Rejected because
   explicit phase/type admission gives a clearer contract and avoids exception
   control flow.
4. **Accept validated `Scenario | ExpandedScenario` for snapshots only.**
   Chosen; it exactly matches canonical authoring identity while preserving
   generic association behavior.

## Chosen Architecture

For `scenario-snapshot`, the parent matcher requires a semantically validated
`Scenario` or `ExpandedScenario`, then applies the unchanged id, version, and
canonical digest comparisons. `InstantiatedScenario` is explicitly outside
the accepted set. For generic `scenario`, the incumbent `Scenario` id-only rule
is unchanged. Parser annotations and docstrings now disclose the actual union
return type.

## Documentation Defense

The normative associated-artifact specification names both accepted authoring
phases and the validation requirement. No contract schema, canonicalization
profile, or set-digest projection changes.

## Verification Plan

- Parse a root with a local module import and validate its exact expanded
  parent id, version, digest, and artifact bytes.
- Mutate the declared digest and require `associated-artifact.parent-mismatch`.
- Reject reconstructed unvalidated normalized/expanded objects and an
  instantiated object as snapshot parents.
- Lock the legacy generic scenario id-only behavior with a regression test.
