"""What the oldest usable build of each mobile client is.

A row here is a decision to stop supporting something: below `minimum_version`
the app refuses to run. That is a heavy thing to be able to do, and the reason
it lives in the database rather than in settings is that the moment you need it
is an incident -- a build that corrupts data, or leaks something, or calls an
endpoint that had to be withdrawn. Waiting on a deploy to change an environment
variable is the wrong shape for that.

An empty table means no constraint, which is the correct default: a fresh
deployment must not gate anyone. `docs/mobile.md` describes when to use it.
"""

from django.core.exceptions import ValidationError
from django.db import models

from .versions import Requirement, is_at_least, parse, requirement_for


def validate_version(value: str) -> None:
    if parse(value) is None:
        raise ValidationError(
            f'{value!r} does not start with a number. '
            'Use the version as the store shows it, like 1.4.0.'
        )


class AppRelease(models.Model):
    """The version floor for one platform.

    Two floors, not one, because "you must upgrade" and "you should upgrade"
    are different messages and only one of them should ever block someone:

    - `minimum_version` blocks. The app shows a screen it cannot be dismissed
      from, and nothing else in the app is reachable.
    - `recommended_version` nudges. A dismissible prompt, shown once per app
      launch, that the user can decline and carry on.

    Setting only the recommended one is the ordinary case. Reach for the
    minimum when leaving the old build running is worse than the interruption.
    """

    class Platform(models.TextChoices):
        IOS = 'ios', 'iOS'
        ANDROID = 'android', 'Android'

    platform = models.CharField(max_length=16, choices=Platform.choices, unique=True)

    minimum_version = models.CharField(
        max_length=32,
        blank=True,
        default='',
        validators=[validate_version],
        help_text='Builds older than this cannot be used at all. Leave empty for no block.',
    )

    recommended_version = models.CharField(
        max_length=32,
        blank=True,
        default='',
        validators=[validate_version],
        help_text='Builds older than this see a dismissible prompt. Leave empty for none.',
    )

    # Where "Update" sends someone. Blank is survivable -- the client falls
    # back to explaining rather than linking -- but a block with no way out of
    # it is close to useless, so the admin says so.
    store_url = models.URLField(
        blank=True,
        default='',
        help_text='The App Store or Play listing. Without it a blocked user has nowhere to go.',
    )

    # Shown instead of the generic copy when set. Not translated: whoever
    # writes it in the admin picks the language, and a half-translated
    # incident message is worse than a translated generic one.
    message = models.TextField(
        blank=True,
        default='',
        help_text='Optional. Replaces the default wording, in whatever language you write it.',
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['platform']

    def __str__(self):
        return f'{self.get_platform_display()}: minimum {self.minimum_version or "none"}'

    def clean(self):
        """A recommendation below the floor is a contradiction, not a nuance.

        It reads as "we suggest a version we already refuse to run", and the
        only way to notice is to try it on a device.
        """
        super().clean()
        if (
            self.minimum_version
            and self.recommended_version
            and not is_at_least(self.recommended_version, self.minimum_version)
        ):
            raise ValidationError(
                {
                    'recommended_version': (
                        'This is older than the minimum, so nobody could ever see it. '
                        f'Set it to {self.minimum_version} or newer.'
                    )
                }
            )

    def status_for(self, version: str) -> str:
        """What a client running `version` should do."""
        return requirement_for(version, self.minimum_version, self.recommended_version)


# Re-exported so callers can say `from .models import Requirement` alongside
# the model it describes, without a second definition of the values.
__all__ = ['AppRelease', 'Requirement', 'validate_version']
