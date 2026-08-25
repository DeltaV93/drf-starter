from django.conf import settings

# The app is not in INSTALLED_APPS when the flag is off, and its settings do
# not exist either -- so importing these modules would fail at collection
# rather than at run time.
collect_ignore_glob = [] if settings.MCP_OAUTH_ENABLED else ['test_*.py']
