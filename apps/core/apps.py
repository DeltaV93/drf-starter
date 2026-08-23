from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        # Registered here rather than at import time: the optional apps'
        # models are only importable once the registry is populated, and only
        # when their flag is on.
        from utils.gdpr_export import register_optional_collectors

        register_optional_collectors()
