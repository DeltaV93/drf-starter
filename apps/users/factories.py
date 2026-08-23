"""Shared test factories.

Kept out of the test modules so every app's tests build users the same way.
"""

import factory
from django.contrib.auth import get_user_model

User = get_user_model()

DEFAULT_PASSWORD = 'testpass123!'


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = 'Test'
    last_name = 'User'
    email_verified = True
    password = factory.PostGenerationMethodCall('set_password', DEFAULT_PASSWORD)

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        # set_password only mutates the instance, so persist it.
        if create and results:
            instance.save()
