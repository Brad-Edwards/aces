# Schema publication records

The root `contracts/schema-publication-manifest.json` is a stable index. Each
published contract owns one record under `entries/`; removals own independent
records under `tombstones/`. A schema change updates only its contract record,
so unrelated schema changes on concurrent branches do not rewrite a shared
catalog array.

Record filenames match the contract identifier (or removed schema filename),
and the repository policy checker assembles and validates the complete catalog
deterministically.
