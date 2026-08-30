from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.authentication'

    def ready(self):
        # Registers the OpenAPI security scheme for the bearer credential.
        # Importing it for the side effect is how drf-spectacular's extension
        # registry works; without it `spectacular --fail-on-warn` fails on
        # every view that accepts the token.
        from . import schema  # noqa: F401
