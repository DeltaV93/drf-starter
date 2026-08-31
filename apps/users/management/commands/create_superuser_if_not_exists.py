"""Idempotently create a superuser from the environment.

Intended for automated environments (CI, a fresh container) where running
`createsuperuser` interactively is not possible. It is a no-op unless both
DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD are set, so nothing is
ever created with a default password. DJANGO_SUPERUSER_USERNAME is optional,
like the field it fills.
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

        if not all([email, password]):
            self.stdout.write(
                self.style.WARNING(
                    'Skipping: set DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD '
                    'to create a superuser automatically '
                    '(DJANGO_SUPERUSER_USERNAME is optional).'
                )
            )
            return

        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(
                self.style.WARNING(f'A user with email "{email}" already exists.')
            )
            return

        if username and User.objects.filter(username__iexact=username).exists():
            self.stdout.write(self.style.WARNING(f'Username "{username}" is already taken.'))
            return

        User.objects.create_superuser(
            email=email,
            password=password,
            username=username or None,
            email_verified=True,
        )
        self.stdout.write(self.style.SUCCESS(f'Created superuser "{email}".'))
