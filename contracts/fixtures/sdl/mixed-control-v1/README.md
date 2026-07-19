# Mixed-Control SDL Fixture Corpus

This directory provides portable ACT-617 mixed-control authoring evidence.

- `valid/` documents must pass strict source decoding and semantic validation.
- `invalid/` documents must pass strict source decoding but fail mixed-control
  semantic validation for the boundary named by the fixture.

These fixtures complement the presentation-only `sdl-yaml-v1` corpus, whose
invalid documents fail before semantic validation.
