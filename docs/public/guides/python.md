# Validate SDL from Python

Use `parse_sdl_file` when your app stores a scenario as a file:

```python
from pathlib import Path

from raes import parse_sdl_file

scenario = parse_sdl_file(Path("first-scenario.sdl.yaml"))
print(scenario.name)
```

Use `parse_sdl` when you already have SDL text:

```python
from raes import parse_sdl

scenario = parse_sdl(sdl_text)
```

Both functions check the file shape and its meaning by default. Treat parse
errors as authoring failures. Show the error message to the author. Keep
semantic checks on unless your workflow has a clear reason to inspect the file
shape alone.

See the [API reference](../api/sdl.rst) for signatures and model details.
