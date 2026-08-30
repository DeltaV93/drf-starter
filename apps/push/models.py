"""Which devices to send a push notification to.

Scoped to a user, like every other optional feature, so this app holds no
foreign key into any of the others.

This app is a registry and nothing more. It stores the tokens and keeps them
honest; it does not talk to Apple, Google or Expo, because which of those a
project uses is a decision the template should not make for it. See
`docs/configuration.md` for where to hook a sender in.
"""

from django.conf import settings
from django.db import models


class Device(models.Model):
    """One installation of the app, on one device, signed in as one user.

    The token is the identity, not the (user, device) pair. A push token
    identifies an *installation*, and the operating system reissues it freely
    -- on reinstall, on restore to a new handset, and sometimes for no visible
    reason. Two consequences shape this model:

    - `token` is unique across the table, and registering an existing token
      moves it to whoever is registering it. Someone signing in on a
      colleague's phone must not leave that phone receiving their
      notifications, and a token left pointing at the previous owner is
      exactly that.
    - Nothing here is trusted to be current. `last_seen_at` is what lets a
      sender skip installations that have not checked in for months, which is
      the only defence against a table that grows forever.
    """

    class Platform(models.TextChoices):
        IOS = 'ios', 'iOS'
        ANDROID = 'android', 'Android'
        WEB = 'web', 'Web'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_devices'
    )

    # Long, because the shape differs per service: an APNs token is 64 hex
    # characters, an FCM registration token is around 160, and an Expo token
    # wraps one of those in `ExponentPushToken[...]`.
    token = models.CharField(max_length=512, unique=True)

    platform = models.CharField(max_length=16, choices=Platform.choices)

    # For display in an account's device list -- "Alex's iPhone". Supplied by
    # the client, so never used for anything but showing to its owner.
    device_name = models.CharField(max_length=128, blank=True, default='')

    # Set to false when a push service reports the token as gone. Kept rather
    # than deleted so a later re-registration of the same token is an update
    # instead of a row that has to be recreated.
    is_active = models.BooleanField(default=True)

    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_seen_at']
        indexes = [models.Index(fields=['user', 'is_active'])]

    def __str__(self):
        return f'{self.get_platform_display()} device for {self.user}'
