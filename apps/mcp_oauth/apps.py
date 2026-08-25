from django.apps import AppConfig


class McpOauthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.mcp_oauth'
    verbose_name = 'MCP OAuth'

    def ready(self):
        # Registering the schema extension is a side effect of the import.
        from . import schema  # noqa: F401
