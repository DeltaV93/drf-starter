"""One module per MCP server this application may talk to.

A module here defines a module-level `SERVER = ServerDefinition(...)` and
nothing else. `registry.py` finds it by walking this package, so adding a
connection is adding a file and removing one is deleting a file -- there is no
list to keep in step.

Modules whose name starts with an underscore are skipped, so shared helpers
can live here too.

`example.py` is kept deliberately: it is the documentation for this directory,
and it is disabled by default so it costs a deployment nothing.
"""
