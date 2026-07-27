# Work with SDL from the command line

Use the CLI to format, resolve imports, verify imports, and publish an authored
scenario.

From a repository checkout:

```console
uv run --project implementations/python raes sdl --help
```

Common commands include:

```console
uv run --project implementations/python raes sdl format --check scenario.sdl.yaml
uv run --project implementations/python raes sdl verify-imports scenario.sdl.yaml
uv run --project implementations/python raes sdl resolve scenario.sdl.yaml
```

`format --check` parses the document and checks its canonical formatting.
`verify-imports` checks referenced modules. `resolve` prints the composed
scenario. None of these commands provisions infrastructure.

Use `raes processor --help` and `raes conformance --help` for the processor and
backend-contract surfaces. The [CLI API reference](../api/cli.rst) lists the
current command implementation.
