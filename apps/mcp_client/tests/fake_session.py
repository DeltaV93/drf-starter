"""A stand-in MCP session, for the cases a real server cannot easily produce.

Most of the local transport is tested against this project's *own* MCP server
over the real transport -- see test_local_end_to_end.py. This exists for the
handful of behaviours that need a server misbehaving on cue: a tool that
raises, a model that never stops asking.
"""

from types import SimpleNamespace


def tool(name, description='', schema=None):
    return SimpleNamespace(
        name=name,
        description=description,
        input_schema=schema or {'type': 'object', 'properties': {}},
    )


class FakeSession:
    def __init__(self, tools=(), results=None, raises=None):
        self._tools = list(tools)
        self._results = results or {}
        self._raises = raises or {}
        self.calls = []

    async def list_tools(self):
        return SimpleNamespace(tools=self._tools)

    async def call_tool(self, name, arguments=None):
        self.calls.append((name, arguments))
        if name in self._raises:
            raise self._raises[name]
        content, is_error = self._results.get(name, ('ok', False))
        return SimpleNamespace(
            content=[SimpleNamespace(type='text', text=content)],
            structured_content=None,
            is_error=is_error,
        )


def tool_use(use_id, name, arguments=None):
    return SimpleNamespace(type='tool_use', id=use_id, name=name, input=arguments or {})


def text(value):
    return SimpleNamespace(type='text', text=value)


def turn(*blocks):
    return SimpleNamespace(content=list(blocks))


class ScriptedModel:
    """An Anthropic stand-in that replies with a fixed sequence of turns.

    The last turn repeats, so a test can say "keep asking for a tool forever"
    without writing it out.
    """

    def __init__(self, *turns):
        self._turns = list(turns)
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        index = min(len(self.calls) - 1, len(self._turns) - 1)
        return self._turns[index]

    @property
    def last(self):
        return self.calls[-1]
