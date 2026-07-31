# Inspect and format a scenario

Build on the quickstart file and use the CLI to inspect its current structure.

## Prepare the repository environment

Clone the repository when you want the CLI and complete example library:

```console
git clone https://github.com/RAESystem/rae.git
cd rae
uv sync --project implementations/python --all-extras --frozen
```

`uv` creates the environment from the checked-in lock file.

## Check the file format

Run the formatter in check mode:

```console
uv run --project implementations/python raes sdl format \
  --check docs/public/_static/examples/first-scenario.sdl.yaml
```

Exit code `0` means the file parses and already uses the canonical format.
The command does not provision the scenario.

## Inspect the admitted declarations

Use the read-only semantic surface to validate the scenario and inspect its
canonical declaration index:

```console
uv run --project implementations/python raes semantic inspect \
  docs/public/_static/examples/first-scenario.sdl.yaml \
  --contract sdl-yaml/v1 --output json
```

The result records the effective source, migration, normalization, and
validation profiles. It does not acquire modules, write a lockfile or cache,
invoke a backend, or provision infrastructure.

## Explore a larger scenario

The [scenario collection](https://github.com/RAESystem/rae/tree/main/examples/scenarios)
contains authored examples with participants, behaviors, objectives, and
evidence requirements. Check each example's notes before treating it as a
backend-ready deployment.
