from rest_framework.throttling import UserRateThrottle


class APIKeyRateThrottle(UserRateThrottle):
    """A separate budget for machine traffic.

    Integrations are legitimately noisier than a person clicking around, and
    they should not spend the interactive user's allowance -- nor should a
    runaway script exhaust it.
    """

    scope = 'api_key'

    def get_cache_key(self, request, view):
        from .models import APIKey

        if not isinstance(request.auth, APIKey):
            return None  # Not a key-authenticated request; not ours to limit.
        return self.cache_format % {'scope': self.scope, 'ident': request.auth.prefix}
