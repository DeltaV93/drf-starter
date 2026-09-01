"""Lowercase the addresses already in the table.

New writes are normalized by `CustomUser.save()`, but rows created before
that -- by the admin, by an import, by a signup predating this template's
`validate_email` -- can hold any casing, which leaves the column half
normalized and every lookup obliged to stay case-insensitive forever.

Rows whose lowercase form is already taken by *another* row are left exactly
as they are. That case is two accounts for one person, and picking which one
survives is a decision for whoever owns the data, not for a migration that
would otherwise fail on the unique constraint mid-deploy. Sign-in still finds
them: `EmailOrUsernameBackend` matches case-insensitively and deterministically.
"""

from django.db import migrations
from django.db.models.functions import Lower


def lowercase_emails(apps, schema_editor):
    User = apps.get_model('users', 'CustomUser')

    skipped = []
    # Only the rows that are not already lowercase, which on most deployments
    # is none of them.
    for user in User.objects.exclude(email=Lower('email')):
        lowered = user.email.strip().lower()

        if User.objects.filter(email=lowered).exclude(pk=user.pk).exists():
            skipped.append(user.email)
            continue

        User.objects.filter(pk=user.pk).update(email=lowered)

    if skipped:
        print(
            f'\n  users.0003: left {len(skipped)} address(es) as they were -- the '
            f'lowercase form belongs to another account: {", ".join(sorted(skipped))}'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_optional_username'),
    ]

    operations = [
        # The backwards pass is a no-op rather than missing: the original
        # casing is not recorded anywhere, so there is nothing to restore,
        # and nothing depends on it.
        migrations.RunPython(lowercase_emails, migrations.RunPython.noop),
    ]
