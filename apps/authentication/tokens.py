"""Token generator for email verification links.

Django's ``default_token_generator`` is fine for password resets -- its hash
includes the password, so the link dies once the password changes. Email
verification needs its own generator whose hash includes the verification
state and the address, so a link stops working the moment it is used or the
address changes.
"""

from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f'{user.pk}{timestamp}{user.email}{user.email_verified}'


email_verification_token_generator = EmailVerificationTokenGenerator()
