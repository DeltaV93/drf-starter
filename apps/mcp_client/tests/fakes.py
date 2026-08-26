"""A stand-in for the Anthropic SDK.

Records the request rather than sending it, so tests can assert on the exact
body the connector builds. That body is the thing worth pinning: the API needs
both `mcp_servers` and a matching `mcp_toolset`, and sending one without the
other is a validation error rather than a request that quietly does nothing.
"""

from types import SimpleNamespace


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.calls = []
        self._response = response
        self._error = error

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response if self._response is not None else block_response()

    @property
    def last(self):
        return self.calls[-1]


class FakeAnthropic:
    def __init__(self, response=None, error=None):
        self.messages = FakeMessages(response=response, error=error)
        self.beta = SimpleNamespace(messages=self.messages)


def text_block(text):
    return SimpleNamespace(type='text', text=text)


def tool_use_block(use_id, name, arguments, server='example'):
    return SimpleNamespace(
        type='mcp_tool_use',
        id=use_id,
        name=name,
        server_name=server,
        input=arguments,
    )


def tool_result_block(use_id, content, is_error=False):
    return SimpleNamespace(
        type='mcp_tool_result',
        tool_use_id=use_id,
        content=content,
        is_error=is_error,
    )


def block_response(*blocks):
    return SimpleNamespace(content=list(blocks) or [text_block('')])
