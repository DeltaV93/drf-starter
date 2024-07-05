from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ACCOUNT_TYPE_CHOICES = [
        ('TYPE_1', 'Account Type 1'),
        ('TYPE_2', 'Account Type 2'),
    ]
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('USER', 'User'),
        ('HOST', 'Host'),
    ]

    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPE_CHOICES)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='USER')
    add_on_1 = models.BooleanField(default=False)
    add_on_2 = models.BooleanField(default=False)

    def __str__(self):
        return self.username