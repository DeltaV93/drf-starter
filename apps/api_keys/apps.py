from django.apps import AppConfig


class ApiKeysConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api_keys'
    verbose_name = 'API keys'

    def ready(self):
        # Registering the schema extension is a side effect of the import.
        from . import schema  # noqa: F401
