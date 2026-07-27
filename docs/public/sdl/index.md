# Author RAES SDL

Use RAES SDL to describe scenario intent without tying the document to one
deployment backend.

Start with four parts:

1. Give the scenario a stable `name`.
2. Declare resources under `nodes`.
3. Set requested counts and links under `infrastructure`.
4. Parse the file and address validation errors before adding more sections.

The [quickstart](../quickstart.md) shows all four parts. Larger scenarios can
add services, identities, participants, behaviors, objectives, workflows,
variation, and evidence requirements.

The published schemas and normative specifications remain the authority for
accepted fields and meaning:

- [SDL schema](https://github.com/RAESystem/rae/tree/main/contracts/schemas/sdl)
- [Normative SDL specification](https://github.com/RAESystem/rae/tree/main/specs)
- [Worked examples](https://github.com/RAESystem/rae/tree/main/examples/scenarios)

Read [current limits](../limitations.md) before assuming that a backend can
realize every valid authored section.
