from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Tight limit on credential-guessing endpoints (login, register)."""

    scope = 'login'


class PasswordResetRateThrottle(AnonRateThrottle):
    """Tight limit on endpoints that send email to an address the caller supplies."""

    scope = 'password_reset'
