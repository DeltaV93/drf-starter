from django.conf import settings

collect_ignore_glob = [] if settings.MCP_CLIENT_ENABLED else ['test_*.py']
