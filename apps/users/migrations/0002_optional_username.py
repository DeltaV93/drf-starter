"""Make `username` optional.

The account is identified by its email address from here on. Nothing needs
backfilling for that -- email was already unique and required -- but the
column has to admit NULL, and any row that reached the old schema with an
empty username has to become NULL rather than '': only one row may hold ''
in a unique column, so the second account without a handle would collide.
"""

import apps.users.managers
import django.contrib.auth.validators
from django.db import migrations, models


def blank_usernames_to_null(apps, schema_editor):
    User = apps.get_model('users', 'CustomUser')
    User.objects.filter(username='').update(username=None)


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='customuser',
            managers=[
                ('objects', apps.users.managers.CustomUserManager()),
            ],
        ),
        migrations.AlterField(
            model_name='customuser',
            name='username',
            field=models.CharField(
                blank=True,
                default=None,
                error_messages={'unique': 'A user with that username already exists.'},
                help_text=(
                    'Optional. 150 characters or fewer. Letters, digits and @/./+/-/_ only. '
                    'Sign-in uses the email address; a username is an alternative for it.'
                ),
                max_length=150,
                null=True,
                unique=True,
                validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                verbose_name='username',
            ),
        ),
        migrations.RunPython(blank_usernames_to_null, migrations.RunPython.noop),
    ]
