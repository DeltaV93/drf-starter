from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a superuser if none exists'

    def handle(self, *args, **kwargs):
        user = get_user_model()
        if not user.objects.filter(email="admin@example.com").exists():
            user.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin'
            )
            self.stdout.write(self.style.SUCCESS('Successfully created new superuser'))
        else:
            self.stdout.write(self.style.WARNING('Superuser already exists'))
