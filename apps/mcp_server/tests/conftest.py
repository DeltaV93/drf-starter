from django.conf import settings

# The app is not in INSTALLED_APPS when the flag is off, so importing anything
# from it would fail at collection rather than at run time.
_ignore = [] if settings.MCP_SERVER_ENABLED else ['test_*.py']

# The boundary tests need a concrete credential to make assertions with, and
# they use an API key. That is a dependency of the *tests*, not of the server:
# apps/mcp_server forwards whatever Authorization header it is given and never
# imports apps.api_keys, so it works just as well with a session cookie or the
# OAuth bearer token that replaces both. Skipping the file rather than the
# feature keeps the two flags genuinely independent.
if not settings.API_KEYS_ENABLED:
    _ignore.append('test_tool_boundaries.py')

collect_ignore_glob = _ignore
