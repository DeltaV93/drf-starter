"""Idempotently create a superuser from the environment.

Intended for automated environments (CI, a fresh container) where running
`createsuperuser` interactively is not possible. It is a no-op unless all
three DJANGO_SUPERUSER_* variables are set, so nothing is ever created with
a default password.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a superuser from DJANGO_SUPERUSER_* env vars if one does not exist'

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not all([username, email, password]):
            self.stdout.write(
                self.style.WARNING(
                    'Skipping: set DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL '
                    'and DJANGO_SUPERUSER_PASSWORD to create a superuser automatically.'
                )
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Superuser "{username}" already exists.'))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'A user with email "{email}" already exists.')
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            email_verified=True,
        )
        self.stdout.write(self.style.SUCCESS(f'Created superuser "{username}".'))
