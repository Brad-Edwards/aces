# `sdl-yaml/v1` Conformance Corpus

This directory is the normative example corpus for the raw SDL YAML source
profile defined by `specs/sdl/document-model.md`.

- `valid/` documents must pass strict source decoding.
- `invalid/` documents must fail strict source decoding.
- `migration/` documents must fail strict decoding, then pass only when an
  explicit migration policy is selected and must produce at least one
  source-ranged warning.

These files test YAML presentation rules that JSON Schema cannot express. The
separate `contracts/schemas/sdl/sdl-authoring-input-v1.json` artifact validates
the normalized authoring object after decoding and typed normalization.
